import io
import os
import re
import json
import base64
from urllib.parse import urlparse

import pandas as pd
import requests
import streamlit as st
from PIL import Image

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    from pdf2image import convert_from_bytes
except ImportError:
    convert_from_bytes = None

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

# =============================================================================
# PPJ TECHPACK AI + GTAS SKETCH SIMILARITY
# =============================================================================
st.set_page_config(
    page_title="PPJ Techpack AI - GTAS Sketch Match",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# IMPORTANT: Paste the correct GTAS API host supplied by company IT.
# Example format only: https://your-gtas-host.company.com
GTAS_BASE_URL = ""  # <-- DÁN ĐỊA CHỈ API GTAS ĐÚNG VÀO ĐÂY, KHÔNG THÊM /items/... 
GTAS_TOKEN = ""      # <-- DÁN TOKEN ĐƯỢC IT CẤP; nên chuyển sang st.secrets khi chạy thật
GTAS_SKETCH_ENDPOINT = "/items/stylepatternpkt"
GTAS_BOM_ENDPOINT = "/items/manual_pattern7"
GTAS_POM_ENDPOINT = ""  # <-- DÁN endpoint POM filter1/search đã được IT xác nhận
GEMINI_API_KEY = ""     # <-- DÁN Gemini API key hoặc cấu hình GEMINI_API_KEY trong secrets
GEMINI_MODEL = "gemini-2.5-flash"

# Read Streamlit secrets/environment if set; otherwise use values above.
def config_value(name, fallback=""):
    try:
        value = st.secrets.get(name, None)
        if value is not None and str(value).strip():
            return str(value).strip()
    except Exception:
        pass
    env = os.getenv(name, "").strip()
    return env or str(fallback or "").strip()

GTAS_BASE_URL = config_value("GTAS_API_URL", GTAS_BASE_URL).rstrip("/")
GTAS_TOKEN = config_value("GTAS_TOKEN", GTAS_TOKEN)
GTAS_POM_ENDPOINT = config_value("GTAS_POM_ENDPOINT", GTAS_POM_ENDPOINT)
GEMINI_API_KEY = config_value("GEMINI_API_KEY", GEMINI_API_KEY)
GEMINI_MODEL = config_value("GEMINI_MODEL", GEMINI_MODEL)

# =============================================================================
# API CLIENT
# =============================================================================
class GTASClient:
    def __init__(self, base_url, token=""):
        self.base_url = (base_url or "").strip().rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def get(self, endpoint, params=None):
        if not self.base_url:
            return {"ok": False, "status": None, "data": None,
                    "error": "Chưa điền GTAS_BASE_URL ở đầu file hoặc GTAS_API_URL trong secrets."}
        parsed_base = urlparse(self.base_url)
        if parsed_base.scheme not in ("https", "http") or not parsed_base.netloc:
            return {"ok": False, "status": None, "data": None,
                    "error": "GTAS_BASE_URL không hợp lệ. Dùng URL máy chủ, ví dụ https://host-cong-ty."}
        if not endpoint.startswith("/") or endpoint.startswith("//"):
            return {"ok": False, "status": None, "data": None,
                    "error": "Endpoint phải là đường dẫn tương đối bắt đầu bằng /."}
        url = self.base_url + endpoint
        try:
            response = self.session.get(url, params=params or {}, timeout=(8, 45))
            if response.status_code != 200:
                messages = {
                    401: "HTTP 401: token thiếu, sai hoặc hết hạn.",
                    403: "HTTP 403: tài khoản/token không có quyền đọc collection hoặc trường.",
                    404: "HTTP 404: sai URL hoặc collection không tồn tại.",
                    429: "HTTP 429: máy chủ giới hạn tần suất truy vấn.",
                }
                return {"ok": False, "status": response.status_code, "data": None,
                        "error": messages.get(response.status_code,
                            f"GTAS trả HTTP {response.status_code}: {response.text[:600]}")}
            try:
                payload = response.json()
            except ValueError:
                return {"ok": False, "status": 200, "data": None,
                        "error": "HTTP 200 nhưng phản hồi không phải JSON."}
            data = payload.get("data", payload) if isinstance(payload, dict) else payload
            return {"ok": True, "status": 200, "data": data, "error": None}
        except requests.exceptions.Timeout:
            return {"ok": False, "status": None, "data": None, "error": "Kết nối GTAS bị timeout."}
        except requests.exceptions.RequestException as exc:
            return {"ok": False, "status": None, "data": None, "error": f"Lỗi mạng/API: {exc}"}

    def list_collection(self, endpoint, limit=100, offset=0, keyword=""):
        params = {"limit": int(limit), "offset": int(offset)}
        if keyword.strip():
            params["search"] = keyword.strip()
        return self.get(endpoint, params)

    def fetch_image(self, image_value):
        """Resolve an image URL, a Directus file UUID, or an object containing id/url."""
        if image_value is None or image_value == "":
            return None, "Trường ảnh rỗng"
        if isinstance(image_value, dict):
            for key in ("url", "download_url", "src", "href"):
                if image_value.get(key):
                    image_value = image_value[key]
                    break
            else:
                image_value = image_value.get("id") or image_value.get("uuid") or image_value.get("file")
        if isinstance(image_value, list):
            if not image_value:
                return None, "Danh sách ảnh rỗng"
            image_value = image_value[0]
            if isinstance(image_value, dict):
                return self.fetch_image(image_value)
        value = str(image_value).strip()
        if not value:
            return None, "Không nhận diện được giá trị ảnh"
        parsed = urlparse(value)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            # Avoid forwarding GTAS Authorization to a different host.
            if parsed.netloc.lower() == urlparse(self.base_url).netloc.lower():
                url = value
                headers = dict(self.session.headers)
            else:
                url = value
                headers = {"Accept": "image/*"}
        else:
            # Directus standard file asset endpoint; confirm with IT if GTAS differs.
            url = f"{self.base_url}/assets/{value}"
            headers = dict(self.session.headers)
        try:
            resp = requests.get(url, headers=headers, timeout=(8, 45))
            if resp.status_code == 200 and resp.content:
                try:
                    Image.open(io.BytesIO(resp.content)).verify()
                    return resp.content, None
                except Exception:
                    return None, f"Giá trị ảnh không trả về file hình hợp lệ (HTTP {resp.status_code})"
            return None, f"Không tải được ảnh (HTTP {resp.status_code})"
        except requests.RequestException as exc:
            return None, f"Lỗi tải ảnh: {exc}"


# =============================================================================
# HELPERS
# =============================================================================
def records_from(data):
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def extract_text_and_code(uploaded):
    name = uploaded.name
    raw = uploaded.getvalue()
    code = ""
    if name.lower().endswith(".pdf") and pdfplumber:
        try:
            with pdfplumber.open(io.BytesIO(raw)) as pdf:
                for page in pdf.pages[:4]:
                    txt = page.extract_text() or ""
                    m = re.search(r"(?:Style|Style\s*No\.?|Mã\s*hàng|Cut\s*No|PO)\s*#?\s*:?\s*([A-Za-z0-9_-]{3,})", txt, re.I)
                    if m:
                        code = m.group(1).upper()
                        break
        except Exception:
            pass
    if not code:
        stem = name.rsplit(".", 1)[0]
        m = re.match(r"([A-Za-z0-9][A-Za-z0-9_-]{2,})", stem)
        code = m.group(1).upper() if m else stem.upper()
    return raw, code


def make_query_image(uploaded, pdf_page=0):
    raw = uploaded.getvalue()
    name = uploaded.name.lower()
    if name.endswith(".pdf"):
        if not convert_from_bytes:
            raise RuntimeError("Thiếu pdf2image. Cài: pip install pdf2image; máy Windows cần Poppler.")
        images = convert_from_bytes(raw, first_page=pdf_page + 1, last_page=pdf_page + 1, dpi=120)
        if not images:
            raise RuntimeError("Không trích xuất được trang PDF đã chọn.")
        buf = io.BytesIO()
        images[0].convert("RGB").save(buf, format="JPEG", quality=88)
        return buf.getvalue(), "image/jpeg"
    image = Image.open(io.BytesIO(raw)).convert("RGB")
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=88)
    return buf.getvalue(), "image/jpeg"


def image_field_to_value(record, field_path):
    value = record
    for part in field_path.split("."):
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value


def get_nested_field(record, field_path):
    value = record
    for part in field_path.split("."):
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return "" if value is None else str(value)


def compare_sketches_gemini(query_bytes, candidate_images, style_field, detail_field, api_key, model):
    """Compare one query sketch to candidate images with Gemini Vision in a single batch."""
    if not api_key:
        raise RuntimeError("Chưa cấu hình GEMINI_API_KEY. Cần Gemini API key để so sánh hình ảnh thật.")
    if genai is None or types is None:
        raise RuntimeError("Thiếu thư viện google-genai. Cài: pip install google-genai")
    if not candidate_images:
        return []
    client = genai.Client(api_key=api_key)
    parts = [types.Part.from_bytes(data=query_bytes, mime_type="image/jpeg")]
    instructions = [
        "Bạn là chuyên gia so sánh sketch kỹ thuật may mặc.",
        "So sánh hình Sketch đầu vào với từng ảnh đối chứng được đánh số.",
        "Chấm điểm tương đồng hình ảnh từ 0 đến 100 dựa trên silhouette/phom, cấu trúc thân, cổ, tay, túi, đường ráp, chi tiết thiết kế.",
        "Không dùng tên mã hàng để tăng điểm; không suy đoán thông tin không nhìn thấy.",
        "Nếu ảnh không phải Sketch hoặc ảnh lỗi, hãy giảm điểm và ghi chú.",
        "Chỉ trả JSON hợp lệ theo dạng: {\"results\":[{\"index\":1,\"score\":0,\"reason\":\"...\"}]}.",
        "Ảnh đầu tiên là Sketch cần tìm. Các ảnh sau lần lượt là ứng viên.",
    ]
    for i, item in enumerate(candidate_images, start=1):
        parts.append(types.Part.from_bytes(data=item["image_bytes"], mime_type="image/jpeg"))
        instructions.append(f"Ứng viên {i}: mã {item['style_code']}; thông tin phụ: {item.get('detail', '')[:300]}")
    parts.insert(0, types.Part.from_text(text="\n".join(instructions)))
    response = client.models.generate_content(
        model=model,
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )
    text = getattr(response, "text", None) or ""
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise RuntimeError(f"Gemini không trả JSON đúng định dạng: {text[:500]}")
    parsed = json.loads(match.group(0))
    results = parsed.get("results", [])
    output = []
    for row in results:
        try:
            idx = int(row.get("index", 0)) - 1
            if 0 <= idx < len(candidate_images):
                score = max(0, min(100, float(row.get("score", 0))))
                output.append({
                    **candidate_images[idx],
                    "similarity_score": round(score, 1),
                    "similarity_reason": str(row.get("reason", "")),
                })
        except (ValueError, TypeError):
            continue
    return sorted(output, key=lambda x: x["similarity_score"], reverse=True)


def normalize_bom(records, type_field, qty_field):
    rows = []
    for rec in records:
        typ = get_nested_field(rec, type_field).strip() if type_field else ""
        qty_text = get_nested_field(rec, qty_field).strip() if qty_field else ""
        try:
            qty = float(qty_text.replace(",", "."))
        except Exception:
            m = re.search(r"[-+]?\d+(?:[.,]\d+)?", qty_text)
            qty = float(m.group(0).replace(",", ".")) if m else 0.0
        if typ and qty > 0:
            rows.append({"Phân loại vật tư (Type)": typ, "ĐM cũ (GTAS)": qty})
    return rows

# =============================================================================
# POM EXTRACTION / COMPARISON / CONSUMPTION PROJECTION HELPERS
# =============================================================================
def extract_pdf_text(uploaded_file, max_chars=45000):
    if not pdfplumber or not uploaded_file.name.lower().endswith(".pdf"):
        return ""
    try:
        with pdfplumber.open(io.BytesIO(uploaded_file.getvalue())) as pdf:
            chunks = []
            for page_no, page in enumerate(pdf.pages[:35], start=1):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    chunks.append(f"--- PAGE {page_no} ---\n{page_text}")
            return "\n\n".join(chunks)[:max_chars]
    except Exception:
        return ""


def extract_pom_with_gemini(uploaded_file, api_key, model):
    # Extract POM table from searchable PDF text.
    if not api_key:
        raise RuntimeError("Cần Gemini API Key để trích xuất POM từ Techpack.")
    if genai is None or types is None:
        raise RuntimeError("Thiếu thư viện google-genai. Cài: pip install google-genai")
    text_content = extract_pdf_text(uploaded_file)
    if not text_content:
        raise RuntimeError(
            "Không đọc được lớp chữ PDF. Nếu bảng POM là ảnh scan, cần bổ sung OCR/ảnh trang POM."
        )
    client = genai.Client(api_key=api_key)
    prompt = f'''Bạn là chuyên viên kỹ thuật may mặc. Trích xuất bảng POM/measurement từ nội dung Techpack bên dưới.
Chỉ lấy thông số POM thật sự xuất hiện, không tự bịa giá trị. Giữ nguyên tên POM, size, giá trị và đơn vị.
Nếu có nhiều size, trả mỗi size thành một dòng. Chuẩn hóa kết quả thành JSON hợp lệ đúng schema:
{{"measurements":[{{"pom":"Chest","size":"M","value":20.5,"unit":"in","tolerance":"+/-0.5","page":"5"}}]}}
Nếu không có bảng POM, trả {{"measurements":[]}}. Không giải thích ngoài JSON.
NỘI DUNG TECHPACK:
{text_content}'''
    response = client.models.generate_content(
        model=model or "gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.1),
    )
    raw = getattr(response, "text", "") or ""
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise RuntimeError(f"Gemini không trả JSON hợp lệ: {raw[:500]}")
    payload = json.loads(match.group(0))
    rows = payload.get("measurements", [])
    clean = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        pom = str(row.get("pom", "")).strip()
        size = str(row.get("size", "")).strip()
        try:
            value = float(str(row.get("value", "")).replace(",", "."))
        except (ValueError, TypeError):
            continue
        if pom and size:
            clean.append({
                "POM": pom,
                "Size": size,
                "Giá trị mã mới": value,
                "Đơn vị": str(row.get("unit", "")).strip(),
                "Dung sai": str(row.get("tolerance", "")).strip(),
                "Trang": str(row.get("page", "")).strip(),
            })
    return clean, payload


def parse_numeric_value(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    raw = str(value).strip().replace(",", ".")
    match = re.search(r"[-+]?\d+(?:\.\d+)?", raw)
    return float(match.group(0)) if match else None


def normalize_pom_records(records, pom_field, size_field, value_field, unit_field=""):
    normalized = []
    for rec in records:
        pom = get_nested_field(rec, pom_field).strip() if pom_field else ""
        size = get_nested_field(rec, size_field).strip() if size_field else ""
        raw_value = get_nested_field(rec, value_field).strip() if value_field else ""
        val = parse_numeric_value(raw_value)
        unit = get_nested_field(rec, unit_field).strip() if unit_field else ""
        if pom and size and val is not None:
            normalized.append({"POM": pom, "Size": size, "Giá trị mã cũ": val, "Đơn vị cũ": unit})
    return normalized


def canonical_pom_name(name):
    return re.sub(r"[^a-z0-9]+", "", str(name).lower())


def build_pom_comparison(old_rows, new_rows, base_size):
    old_lookup = {}
    for row in old_rows:
        if str(row.get("Size", "")).strip().lower() == str(base_size).strip().lower():
            key = canonical_pom_name(row.get("POM", ""))
            if key:
                old_lookup[key] = row
    out = []
    for row in new_rows:
        if str(row.get("Size", "")).strip().lower() != str(base_size).strip().lower():
            continue
        key = canonical_pom_name(row.get("POM", ""))
        old = old_lookup.get(key)
        if not old:
            out.append({
                "POM": row["POM"], "Size": base_size,
                "Giá trị mã cũ": None, "Giá trị mã mới": row.get("Giá trị mã mới"),
                "Chênh lệch": None, "Chênh lệch (%)": None,
                "Đơn vị": row.get("Đơn vị", ""),
                "Trạng thái": "Không tìm thấy POM tương ứng ở mã cũ",
                "Hệ số ảnh hưởng ĐM (%)": 0.0,
            })
            continue
        old_value = parse_numeric_value(old.get("Giá trị mã cũ"))
        new_value = parse_numeric_value(row.get("Giá trị mã mới"))
        delta = (new_value - old_value) if old_value is not None and new_value is not None else None
        pct = (delta / old_value * 100.0) if delta is not None and old_value not in (0, None) else None
        out.append({
            "POM": row["POM"], "Size": base_size,
            "Giá trị mã cũ": old_value, "Giá trị mã mới": new_value,
            "Chênh lệch": round(delta, 4) if delta is not None else None,
            "Chênh lệch (%)": round(pct, 3) if pct is not None else None,
            "Đơn vị": row.get("Đơn vị", "") or old.get("Đơn vị cũ", ""),
            "Trạng thái": "Đã đối chiếu",
            "Hệ số ảnh hưởng ĐM (%)": 0.0,
        })
    return out


def project_bom_from_pom(bom_rows, pom_comparison, wastage_pct=0.0):
    # Project BOM from user-approved POM impact coefficients.
    weighted_delta_pct = 0.0
    used = []
    for row in pom_comparison:
        pct = row.get("Chênh lệch (%)")
        coefficient = parse_numeric_value(row.get("Hệ số ảnh hưởng ĐM (%)")) or 0.0
        if pct is not None and coefficient != 0:
            weighted_delta_pct += float(pct) * coefficient / 100.0
            used.append(row.get("POM", ""))
    projected = []
    for row in bom_rows:
        typ = row.get("Phân loại vật tư (Type)", "Unknown")
        qty = parse_numeric_value(row.get("ĐM cũ (GTAS)"))
        if qty is None or qty <= 0:
            continue
        type_upper = str(typ).upper()
        if any(k in type_upper for k in ("FABRIC", "MAIN", "SHELL", "BODY", "VẢI CHÍNH", "VAI CHINH")):
            delta = weighted_delta_pct
            note = "Điều chỉnh theo POM có hệ số ảnh hưởng do người dùng xác nhận"
        elif any(k in type_upper for k in ("LINING", "POCKET", "INTERLINING", "FUSING", "RIB", "CONTRAST", "LÓT", "LOT")):
            delta = weighted_delta_pct
            note = "Dự phóng theo POM; kỹ thuật viên cần xác nhận vật tư thay đổi theo phom"
        else:
            delta = 0.0
            note = "Giữ định mức gốc; phụ liệu tĩnh chưa tự điều chỉnh theo POM"
        base = qty * (1.0 + delta / 100.0)
        final_qty = base * (1.0 + float(wastage_pct or 0.0) / 100.0)
        projected.append({
            "Phân loại vật tư (Type)": typ,
            "ĐM cũ (GTAS)": round(qty, 4),
            "Biến thiên ĐM áp dụng (%)": round(delta, 3),
            "Hao hụt bổ sung (%)": round(float(wastage_pct or 0.0), 2),
            "ĐM dự phóng mã mới": round(final_qty, 4),
            "Ghi chú": note,
        })
    return projected, round(weighted_delta_pct, 3), used


# =============================================================================
# STYLING
# =============================================================================
st.markdown("""
<style>
.stApp { background-color: #F8FAFC !important; }
[data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #CBD5E1 !important; min-width: 320px; }
.sidebar-brand-container { background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%); padding: 22px; border-radius: 14px; text-align: center; margin-bottom: 24px; }
.sidebar-brand-title { font-size: 24px; font-weight: 800; color: #FFFFFF; margin: 0; }
.component-title-box { background: linear-gradient(90deg, #1E3A8A 0%, #2563EB 100%); color: #FFFFFF !important; font-size: 16px; font-weight: 700; padding: 14px 20px; border-radius: 10px; margin: 16px 0; }
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("""
<div class='sidebar-brand-container'>
  <div class='sidebar-brand-title'>PPJ GROUP</div>
  <div style='color:#BFDBFE;font-size:11px;font-weight:700;'>GTAS AI ENGINE · SKETCH MATCH</div>
</div>
""", unsafe_allow_html=True)

# Sidebar runtime overrides let the user paste host/token without editing code.
with st.sidebar.expander("⚙️ Cấu hình kết nối GTAS", expanded=True):
    base_url_ui = st.text_input("GTAS API URL", value=GTAS_BASE_URL, placeholder="Dán URL API do IT cấp")
    token_ui = st.text_input("GTAS Token", value=GTAS_TOKEN, type="password", help="Không chia sẻ token.")
    sketch_endpoint_ui = st.text_input("Styles Lib endpoint", value=GTAS_SKETCH_ENDPOINT)
    bom_endpoint_ui = st.text_input("BOM endpoint", value=GTAS_BOM_ENDPOINT)
    pom_endpoint_ui = st.text_input("POM endpoint (nếu đã biết)", value=GTAS_POM_ENDPOINT)
    gemini_key_ui = st.text_input("Gemini API Key", value=GEMINI_API_KEY, type="password")
    model_ui = st.text_input("Gemini model", value=GEMINI_MODEL)

client = GTASClient(base_url_ui, token_ui)

st.markdown("<div class='component-title-box'>📁 1. TẢI TECHPACK / SKETCH CẦN TÌM</div>", unsafe_allow_html=True)
uploaded = st.file_uploader("Tải PDF Techpack hoặc hình Sketch (PNG/JPG/JPEG)", type=["pdf", "png", "jpg", "jpeg"])

if uploaded:
    st.info(f"File: **{uploaded.name}** · {len(uploaded.getvalue()) / 1024:.1f} KB")
    if uploaded.name.lower().endswith(".pdf"):
        page_number = st.number_input("Trang PDF có Sketch (số trang bắt đầu từ 1)", min_value=1, value=1, step=1)
        query_page_index = int(page_number) - 1
    else:
        query_page_index = 0
    try:
        query_bytes, query_mime = make_query_image(uploaded, query_page_index)
        st.image(query_bytes, caption="Sketch đầu vào dùng để tìm kiếm", use_container_width=True)
        _, detected_code = extract_text_and_code(uploaded)
        st.caption(f"Mã nhận diện sơ bộ từ PDF/tên file: {detected_code or 'Chưa nhận diện được'}")
    except Exception as exc:
        query_bytes = None
        st.error(f"Không đọc được hình đầu vào: {exc}")
else:
    query_bytes = None
    detected_code = ""

st.markdown("<div class='component-title-box'>🔎 2. TÌM MÃ HÀNG CÓ SKETCH TƯƠNG ĐỒNG TRONG STYLES LIB</div>", unsafe_allow_html=True)
col_a, col_b, col_c = st.columns([1, 1, 1])
with col_a:
    search_keyword = st.text_input("Từ khóa lọc sơ bộ (không bắt buộc)", value="")
with col_b:
    max_records = st.selectbox("Số bản ghi Styles Lib lấy về", [20, 50, 100, 200], index=2)
with col_c:
    compare_count = st.selectbox("Số ảnh đem so sánh Gemini", [3, 5, 8, 10], index=2)

# Field mapping is configurable because actual collection schema has not yet been provided.
with st.expander("🧩 Ánh xạ trường dữ liệu GTAS (cần chọn đúng theo JSON thật)", expanded=True):
    style_field = st.text_input("Tên trường mã hàng trong stylepatternpkt", value="style_code", help="Ví dụ: style_code, style, code... cần khớp JSON thật.")
    image_field = st.text_input("Tên trường ảnh Sketch hoặc file ID", value="sketch", help="Có thể là UUID file, URL hoặc object chứa id/url; hỗ trợ đường dẫn lồng nhau như sketch.id.")
    detail_field = st.text_input("Trường thông tin phụ để hiển thị (không bắt buộc)", value="name")

if st.button("🔌 Kiểm tra kết nối Styles Lib", use_container_width=True):
    test = client.list_collection(sketch_endpoint_ui, limit=1)
    if test["ok"]:
        st.success("Styles Lib phản hồi HTTP 200.")
        st.json(test["data"])
    else:
        st.error(f"HTTP {test['status']}: {test['error']}")

if st.button("🚀 TÌM MÃ HÀNG TƯƠNG ĐỒNG BẰNG SKETCH", type="primary", use_container_width=True):
    if not query_bytes:
        st.error("Hãy tải PDF hoặc hình Sketch trước.")
    elif not base_url_ui.strip():
        st.error("Hãy dán GTAS API URL đúng trong phần Cấu hình kết nối GTAS.")
    elif not gemini_key_ui.strip():
        st.error("Cần Gemini API Key để phân tích hình ảnh. Hãy cấu hình key trong secrets hoặc sidebar.")
    else:
        with st.spinner("Đang lấy danh sách mã hàng từ Styles Lib..."):
            fetched = client.list_collection(sketch_endpoint_ui, limit=max_records, keyword=search_keyword)
        if not fetched["ok"]:
            st.error(f"Không đọc được Styles Lib — HTTP {fetched['status']}: {fetched['error']}")
        else:
            records = records_from(fetched["data"])
            st.write(f"Styles Lib trả về **{len(records)}** bản ghi trong lượt truy vấn này.")
            if not records:
                st.warning("Không có bản ghi. Hãy kiểm tra quyền, endpoint hoặc từ khóa.")
                st.json(fetched["data"])
            else:
                st.caption("Mẫu JSON bản ghi đầu tiên — dùng để xác định đúng tên trường mã hàng và ảnh Sketch:")
                st.json(records[0])
                candidates = []
                image_failures = []
                for rec in records:
                    code = get_nested_field(rec, style_field).strip()
                    img_value = image_field_to_value(rec, image_field)
                    if not code:
                        # Fall back to common identifiers only for display; user should map field correctly.
                        code = str(rec.get("style") or rec.get("code") or rec.get("id") or "").strip()
                    if not code or img_value in (None, ""):
                        continue
                    image_bytes, image_error = client.fetch_image(img_value)
                    if image_bytes:
                        try:
                            im = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                            buf = io.BytesIO()
                            im.thumbnail((1200, 1200))
                            im.save(buf, format="JPEG", quality=85)
                            candidates.append({
                                "style_code": code,
                                "detail": get_nested_field(rec, detail_field),
                                "image_bytes": buf.getvalue(),
                                "source_record": rec,
                            })
                        except Exception as exc:
                            image_failures.append({"style_code": code, "error": str(exc)})
                    else:
                        image_failures.append({"style_code": code, "error": image_error})
                st.write(f"Tải được **{len(candidates)}** ảnh Sketch để so sánh.")
                if image_failures:
                    with st.expander(f"Không tải được {len(image_failures)} ảnh (xem lỗi)"):
                        st.dataframe(pd.DataFrame(image_failures), use_container_width=True)
                if not candidates:
                    st.error("Không có ảnh ứng viên để so sánh. Kiểm tra tên trường ảnh và cách GTAS trả file ID/URL.")
                else:
                    # Limit number of image candidates sent to Gemini; first returned records are used.
                    selected_candidates = candidates[:int(compare_count)]
                    with st.spinner(f"Gemini đang so sánh Sketch với {len(selected_candidates)} ảnh ứng viên..."):
                        try:
                            ranked = compare_sketches_gemini(
                                query_bytes,
                                selected_candidates,
                                style_field,
                                detail_field,
                                gemini_key_ui.strip(),
                                model_ui.strip() or "gemini-2.5-flash",
                            )
                        except Exception as exc:
                            ranked = []
                            st.error(f"Không hoàn thành so sánh ảnh: {exc}")
                    if ranked:
                        st.session_state["gtas_sketch_matches"] = ranked
                        st.session_state["gtas_match_source_code"] = detected_code
                    elif not st.session_state.get("gtas_sketch_matches"):
                        st.warning("Chưa có kết quả xếp hạng. Kiểm tra Gemini API và ảnh đầu vào.")

matches = st.session_state.get("gtas_sketch_matches", [])
if matches:
    st.markdown("<div class='component-title-box'>🏆 3. KẾT QUẢ MÃ HÀNG TƯƠNG ĐỒNG</div>", unsafe_allow_html=True)
    st.warning("Điểm tương đồng là đánh giá thị giác của Gemini, không phải tỷ lệ diện tích rập hoặc xác nhận kỹ thuật cuối cùng. Cần kỹ thuật viên duyệt trước khi dùng định mức.")
    match_rows = []
    for idx, match in enumerate(matches, start=1):
        match_rows.append({
            "Xếp hạng": idx,
            "Mã hàng": match["style_code"],
            "Điểm tương đồng (%)": match["similarity_score"],
            "Nhận xét hình ảnh": match.get("similarity_reason", ""),
        })
    st.dataframe(pd.DataFrame(match_rows), use_container_width=True, hide_index=True)
    for start in range(0, len(matches), 2):
        cols = st.columns(2)
        for col, match in zip(cols, matches[start:start + 2]):
            with col:
                st.image(match["image_bytes"], use_container_width=True)
                st.markdown(f"**{match['style_code']} — {match['similarity_score']:.1f}%**")
                st.caption(match.get("similarity_reason", ""))
                with st.expander("JSON bản ghi GTAS"):
                    st.json(match.get("source_record", {}))

    chosen_code = st.selectbox(
        "Chọn mã hàng tương đồng để lấy BOM/POM lịch sử",
        options=[m["style_code"] for m in matches],
        index=0,
    )
    chosen_match = next((m for m in matches if m["style_code"] == chosen_code), None)
    if chosen_match:
        with st.expander("Sketch mã đối chứng đã chọn", expanded=False):
            st.image(chosen_match["image_bytes"], caption=chosen_code, use_container_width=True)

    st.markdown("<div class='component-title-box'>📚 4. TRÍCH XUẤT BOM VÀ POM CỦA MÃ ĐỐI CHỨNG</div>", unsafe_allow_html=True)
    st.caption("BOM lấy từ manual_pattern7. POM cần endpoint thật do IT xác nhận.")
    pom_col1, pom_col2 = st.columns(2)
    with pom_col1:
        bom_search_field = st.text_input("Trường mã hàng trong BOM (nếu đã biết)", value="")
        bom_type_field = st.text_input("Trường loại vật tư trong BOM", value="consumption_type")
        bom_qty_field = st.text_input("Trường định mức trong BOM", value="consumption_value")
    with pom_col2:
        pom_search_field = st.text_input("Trường mã hàng trong POM (nếu endpoint cần lọc)", value="")
        pom_name_field = st.text_input("Trường tên POM trong API", value="pom")
        pom_size_field = st.text_input("Trường size trong API POM", value="size")
        pom_value_field = st.text_input("Trường giá trị thông số trong API POM", value="value")
        pom_unit_field = st.text_input("Trường đơn vị POM (không bắt buộc)", value="unit")

    load_col1, load_col2 = st.columns(2)
    with load_col1:
        load_bom = st.button("📦 TẢI BOM CŨ TỪ GTAS", use_container_width=True)
    with load_col2:
        load_pom = st.button("📏 TẢI POM CŨ TỪ GTAS", use_container_width=True)

    if load_bom:
        params = {"search": chosen_code, "limit": 100}
        if bom_search_field.strip():
            params = {"filter": {bom_search_field.strip(): {"_eq": chosen_code}}, "limit": 100}
        bom_result = client.get(bom_endpoint_ui, params)
        if not bom_result["ok"]:
            st.error(f"Lỗi BOM HTTP {bom_result['status']}: {bom_result['error']}")
            st.session_state.pop("selected_old_bom_records", None)
        else:
            bom_records_loaded = records_from(bom_result["data"])
            st.session_state["selected_old_bom_records"] = bom_records_loaded
            st.session_state["selected_old_bom_code"] = chosen_code
            st.success(f"GTAS trả về {len(bom_records_loaded)} bản ghi BOM. Hãy kiểm tra JSON và xác nhận đúng mã hàng.")

    if st.session_state.get("selected_old_bom_code") == chosen_code:
        old_bom_records = st.session_state.get("selected_old_bom_records", [])
        if old_bom_records:
            with st.expander("JSON BOM gốc từ GTAS", expanded=False):
                st.json(old_bom_records[:20])
            normalized_bom = normalize_bom(old_bom_records, bom_type_field, bom_qty_field)
            if normalized_bom:
                st.dataframe(pd.DataFrame(normalized_bom), use_container_width=True, hide_index=True)
                st.session_state["normalized_old_bom"] = normalized_bom
            else:
                st.warning("Chưa ánh xạ được trường loại vật tư/định mức. Hãy xem JSON và nhập đúng tên trường.")
        else:
            st.warning("API trả về 0 bản ghi BOM cho mã đã chọn.")

    if load_pom:
        if not pom_endpoint_ui.strip():
            st.error("Chưa có GTAS_POM_ENDPOINT. Dán endpoint filter1/search thực tế do IT cung cấp ở phần cấu hình sidebar.")
        else:
            params = {"search": chosen_code, "limit": 500}
            if pom_search_field.strip():
                params = {"filter": {pom_search_field.strip(): {"_eq": chosen_code}}, "limit": 500}
            pom_result = client.get(pom_endpoint_ui.strip(), params)
            if not pom_result["ok"]:
                st.error(f"Lỗi POM HTTP {pom_result['status']}: {pom_result['error']}")
                st.session_state.pop("selected_old_pom_records", None)
            else:
                old_pom_records = records_from(pom_result["data"])
                st.session_state["selected_old_pom_records"] = old_pom_records
                st.session_state["selected_old_pom_code"] = chosen_code
                st.success(f"GTAS trả về {len(old_pom_records)} bản ghi POM. Kiểm tra ánh xạ trường trước khi so sánh.")

    if st.session_state.get("selected_old_pom_code") == chosen_code:
        old_pom_records = st.session_state.get("selected_old_pom_records", [])
        if old_pom_records:
            with st.expander("JSON POM gốc từ GTAS", expanded=False):
                st.json(old_pom_records[:30])
            old_pom_normalized = normalize_pom_records(
                old_pom_records, pom_name_field, pom_size_field, pom_value_field, pom_unit_field
            )
            if old_pom_normalized:
                st.session_state["normalized_old_pom"] = old_pom_normalized
                st.dataframe(pd.DataFrame(old_pom_normalized), use_container_width=True, hide_index=True)
            else:
                st.warning("Chưa ánh xạ được POM. Hãy sửa tên trường theo JSON thực tế.")

    st.markdown("<div class='component-title-box'>📐 5. TRÍCH XUẤT POM MÃ MỚI VÀ SO SÁNH THÔNG SỐ</div>", unsafe_allow_html=True)
    st.caption("Chọn size cơ sở giống nhau ở cả mã cũ và mã mới. Chỉ so sánh POM cùng tên và cùng đơn vị.")
    base_size = st.text_input("Size cơ sở dùng để so sánh (ví dụ M)", value="M")
    if st.button("🤖 TRÍCH XUẤT POM TỪ TECHPACK MỚI", use_container_width=True):
        if not uploaded:
            st.error("Hãy tải Techpack PDF ở đầu trang trước.")
        elif not gemini_key_ui.strip():
            st.error("Cần Gemini API Key để đọc bảng POM trong Techpack.")
        elif not uploaded.name.lower().endswith(".pdf"):
            st.error("Trích xuất POM tự động hiện yêu cầu Techpack PDF có lớp chữ. Ảnh đơn lẻ chưa đủ dữ liệu bảng POM.")
        else:
            with st.spinner("Gemini đang trích xuất POM từ nội dung Techpack..."):
                try:
                    new_pom_rows, raw_pom = extract_pom_with_gemini(
                        uploaded, gemini_key_ui.strip(), model_ui.strip() or "gemini-2.5-flash"
                    )
                    st.session_state["new_pom_rows"] = new_pom_rows
                    st.session_state["new_pom_raw"] = raw_pom
                    st.success(f"Đã trích xuất {len(new_pom_rows)} dòng POM. Hãy rà soát trước khi tính.")
                except Exception as exc:
                    st.error(f"Không trích xuất được POM: {exc}")

    new_pom_rows = st.session_state.get("new_pom_rows", [])
    if new_pom_rows:
        st.write("**POM mã mới — có thể chỉnh sửa trước khi so sánh**")
        edited_new_pom = st.data_editor(
            pd.DataFrame(new_pom_rows), use_container_width=True, hide_index=True,
            num_rows="dynamic", key="new_pom_editor",
        )
        st.session_state["new_pom_rows_edited"] = edited_new_pom.to_dict(orient="records")
        old_pom_rows = st.session_state.get("normalized_old_pom", [])
        if old_pom_rows:
            comparison_rows = build_pom_comparison(
                old_pom_rows, st.session_state.get("new_pom_rows_edited", new_pom_rows), base_size
            )
            if comparison_rows:
                st.markdown("**Bảng chênh lệch POM — nhập hệ số ảnh hưởng ĐM cho từng thông số**")
                st.caption("Hệ số mặc định bằng 0 để tránh tự giả định. Hệ số 50 nghĩa là POM tăng 1% đóng góp +0,5% vào biến thiên định mức. Kỹ thuật viên cần xác nhận hệ số theo loại POM và cấu trúc rập.")
                edited_comparison = st.data_editor(
                    pd.DataFrame(comparison_rows), use_container_width=True, hide_index=True,
                    disabled=["POM", "Size", "Giá trị mã cũ", "Giá trị mã mới", "Chênh lệch", "Chênh lệch (%)", "Đơn vị", "Trạng thái"],
                    column_config={"Hệ số ảnh hưởng ĐM (%)": st.column_config.NumberColumn(
                        "Hệ số ảnh hưởng ĐM (%)", help="Hệ số do kỹ thuật viên xác nhận; 0 = không dùng POM này.",
                        min_value=-1000.0, max_value=1000.0, step=5.0)},
                    key="pom_comparison_editor",
                )
                st.session_state["pom_comparison_edited"] = edited_comparison.to_dict(orient="records")
                st.session_state["pom_comparison_rows"] = comparison_rows
                st.dataframe(pd.DataFrame(comparison_rows).drop(columns=["Hệ số ảnh hưởng ĐM (%)"]), use_container_width=True, hide_index=True)
            else:
                st.warning(f"Không có POM khớp size {base_size} hoặc tên POM không trùng nhau.")
        else:
            st.info("Chưa có POM mã cũ đã chuẩn hóa. Tải POM GTAS và xác nhận ánh xạ trường trước.")

    st.markdown("<div class='component-title-box'>🧮 6. TÍNH ĐỊNH MỨC DỰ PHÓNG TỪ CHÊNH LỆCH POM</div>", unsafe_allow_html=True)
    st.warning("Đây là định mức dự phóng, không phải định mức rập chính xác. Chênh lệch POM chỉ chuyển thành biến thiên định mức theo hệ số ảnh hưởng do người dùng xác nhận; muốn chính xác hơn cần diện tích rập hoặc marker thực tế.")
    wastage_pct = st.number_input("Hao hụt bổ sung (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
    active_bom = st.session_state.get("normalized_old_bom", [])
    active_comparison = st.session_state.get("pom_comparison_edited", [])
    if st.button("🧮 TÍNH ĐỊNH MỨC MÃ MỚI", type="primary", use_container_width=True):
        if not active_bom:
            st.error("Chưa có BOM cũ đã chuẩn hóa. Hãy tải BOM và ánh xạ đúng trường trước.")
        elif not active_comparison:
            st.error("Chưa có bảng so sánh POM. Cần trích xuất POM mới và tải POM cũ trước.")
        else:
            projected_rows, weighted_delta, used_poms = project_bom_from_pom(
                active_bom, active_comparison, wastage_pct=wastage_pct
            )
            if not used_poms:
                st.error("Chưa có POM nào được gán hệ số ảnh hưởng khác 0. Hãy xác nhận hệ số trong bảng POM.")
            elif projected_rows:
                st.success(f"Đã dự phóng định mức. Biến thiên tổng hợp: {weighted_delta:+.3f}%. POM tham gia: {', '.join(used_poms)}")
                st.dataframe(pd.DataFrame(projected_rows), use_container_width=True, hide_index=True)
                st.session_state["projected_bom_rows"] = projected_rows
                csv_bytes = pd.DataFrame(projected_rows).to_csv(index=False).encode("utf-8-sig")
                st.download_button("⬇️ Tải bảng định mức dự phóng CSV", data=csv_bytes,
                    file_name=f"DM_du_phong_{chosen_code}.csv", mime="text/csv", use_container_width=True)
            else:
                st.error("Không đủ dòng BOM hợp lệ để tính định mức.")

st.markdown("---")
st.caption("GTAS API endpoints theo thông tin hiện có: Styles Lib /items/stylepatternpkt · BOM /items/manual_pattern7. POM chưa được gọi cho đến khi có endpoint filter1/search chính xác.")
