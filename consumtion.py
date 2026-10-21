import io
import os
import re
from urllib.parse import urlparse

import pandas as pd
import pdfplumber
import requests
import streamlit as st

# =========================================================================
# PPJ TECHPACK AI - GTAS CONNECTOR
# =========================================================================
st.set_page_config(
    page_title="PPJ Techpack AI - GTAS Integrated System",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================================
# CONFIGURATION
# =========================================================================
def get_secret(key, default=""):
    try:
        value = st.secrets.get(key, None)
        if value is not None and str(value).strip():
            return str(value).strip()
    except Exception:
        pass
    return os.getenv(key, default).strip()


GTAS_BASE_URL = get_secret(
    "GTAS_API_URL", "https://cms.ppj-international.com"
).rstrip("/")
GTAS_TOKEN = get_secret("GTAS_TOKEN")
GTAS_POM_ENDPOINT = get_secret("GTAS_POM_ENDPOINT", "")

# Endpoints supplied by the user
API_GET_SKETCH = "/items/stylepatternpkt"
API_GET_BOM = "/items/manual_pattern7"

# =========================================================================
# API CLIENT
# =========================================================================
class GTASClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        if GTAS_TOKEN:
            self.session.headers["Authorization"] = f"Bearer {GTAS_TOKEN}"

    def get(self, endpoint, params=None):
        if not GTAS_TOKEN:
            return {
                "ok": False, "status": None, "data": None,
                "error": "Chưa cấu hình GTAS_TOKEN trong Streamlit Secrets hoặc biến môi trường."
            }

        parsed_base = urlparse(GTAS_BASE_URL)
        parsed_endpoint = urlparse(endpoint)
        if parsed_endpoint.scheme or parsed_endpoint.netloc:
            return {
                "ok": False, "status": None, "data": None,
                "error": "Endpoint phải là đường dẫn tương đối."
            }
        if not parsed_base.scheme or not parsed_base.netloc:
            return {
                "ok": False, "status": None, "data": None,
                "error": "GTAS_API_URL không hợp lệ."
            }

        url = f"{GTAS_BASE_URL}/{endpoint.lstrip('/')}"
        try:
            response = self.session.get(
                url, params=params or {}, timeout=(5, 30)
            )
            if response.status_code != 200:
                errors = {
                    401: "Token không hợp lệ hoặc đã hết hạn.",
                    403: "Tài khoản API không có quyền đọc collection/trường dữ liệu.",
                    404: "Không tìm thấy endpoint hoặc collection.",
                    429: "GTAS đang giới hạn số lượng yêu cầu.",
                }
                return {
                    "ok": False,
                    "status": response.status_code,
                    "data": None,
                    "error": errors.get(
                        response.status_code,
                        f"GTAS trả HTTP {response.status_code}: {response.text[:300]}"
                    ),
                }

            try:
                payload = response.json()
            except ValueError:
                return {
                    "ok": False, "status": 200, "data": None,
                    "error": "GTAS không trả về JSON hợp lệ."
                }

            data = payload.get("data", payload) if isinstance(payload, dict) else payload
            return {"ok": True, "status": 200, "data": data, "error": None}

        except requests.exceptions.Timeout:
            return {
                "ok": False, "status": None, "data": None,
                "error": "GTAS phản hồi quá thời gian chờ."
            }
        except requests.exceptions.RequestException as exc:
            return {
                "ok": False, "status": None, "data": None,
                "error": f"Lỗi kết nối GTAS: {exc}"
            }

    def search_collection(self, endpoint, keyword, limit=50):
        # Generic Directus-style search. Exact matching field still needs schema confirmation.
        return self.get(
            endpoint,
            {"search": keyword, "limit": limit, "page": 1}
        )

    def get_pom(self, style_code):
        if not GTAS_POM_ENDPOINT:
            return {
                "ok": False, "status": None, "data": None,
                "error": "Chưa cấu hình GTAS_POM_ENDPOINT; cần xác minh URL filter1/search thực tế."
            }
        return self.get(GTAS_POM_ENDPOINT, {"search": style_code})


gtas_client = GTASClient()


# =========================================================================
# HELPERS
# =========================================================================
def internal_clean_float(value):
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().replace(",", ".")
    try:
        return float(text)
    except (TypeError, ValueError):
        mixed = re.search(r"(\d+)\s+(\d+)/(\d+)", text)
        if mixed and int(mixed.group(3)) != 0:
            return float(mixed.group(1)) + float(mixed.group(2)) / float(mixed.group(3))
        fraction = re.search(r"(\d+)/(\d+)", text)
        if fraction and int(fraction.group(2)) != 0:
            return float(fraction.group(1)) / float(fraction.group(2))
        number = re.search(r"[-+]?\d*\.?\d+", text)
        return float(number.group(0)) if number else 0.0


def normalize_records(data):
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        # Directus data may occasionally be a single object
        return [data]
    return []


def detect_style_from_pdf(file_bytes):
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages[:3]:
                page_text = page.extract_text() or ""
                match = re.search(
                    r"(?:Style|Mã\s*hàng|PO|Cut\s*No)\s*#?\s*:?\s*([A-Za-z0-9_-]+)",
                    page_text,
                    re.IGNORECASE,
                )
                if match:
                    return match.group(1).strip().upper()
    except Exception:
        pass
    return ""


def detect_style_from_filename(filename):
    base = str(filename).rsplit(".", 1)[0].strip()
    # Prefer code-like prefix before dash/space, e.g. F25R09-490416
    match = re.match(r"^([A-Za-z0-9]+)", base)
    return match.group(1).upper() if match else base.upper()


def extract_bom_rows(records):
    """
    Normalize only recognized BOM fields.
    Unknown schema is shown for inspection instead of silently fabricated.
    """
    rows = []
    for record in records:
        ctype = None
        qty = None

        for key in (
            "consumption_type", "type", "material_type",
            "Phân loại vật tư (Type)", "material", "fabric_type"
        ):
            if record.get(key) not in (None, ""):
                ctype = record.get(key)
                break

        for key in (
            "consumption_value", "consumption", "quantity",
            "Định mức (DM)", "consumption_qty", "qty", "value"
        ):
            if record.get(key) not in (None, ""):
                qty = record.get(key)
                break

        if ctype is not None and qty is not None:
            qty_float = internal_clean_float(qty)
            if qty_float > 0:
                rows.append({
                    "consumption_type": str(ctype).strip().upper(),
                    "consumption_value": qty_float,
                    "_source": record,
                })
    return rows


# =========================================================================
# THEME - PRESERVED INDUSTRIAL LIGHT UI
# =========================================================================
st.markdown(
    """
    <style>
    .stApp { background-color: #F8FAFC !important; }
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #CBD5E1 !important;
        min-width: 320px;
    }
    .sidebar-brand-container {
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
        padding: 22px; border-radius: 14px; text-align: center; margin-bottom: 30px;
    }
    .sidebar-brand-title { font-size: 24px; font-weight: 800; color: #FFFFFF; margin: 0; }
    .component-title-box {
        background: linear-gradient(90deg, #1E3A8A 0%, #2563EB 100%);
        color: #FFFFFF !important; font-size: 16px; font-weight: 700;
        padding: 14px 20px; border-radius: 10px; margin-bottom: 25px;
    }
    .card-container {
        background-color: #FFFFFF !important; border: 1px solid #E2E8F0 !important;
        border-radius: 14px !important; padding: 24px; margin-bottom: 25px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    """
    <div class="sidebar-brand-container">
        <div class="sidebar-brand-title">PPJ GROUP</div>
        <div style="color:#BFDBFE;font-size:11px;font-weight:700;">GTAS AI ENGINE</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================================================================
# INPUTS
# =========================================================================
style_input = st.sidebar.text_input(
    "🔍 Mã hàng đối chứng hệ thống đang xử lý:", ""
).strip().upper()

st.markdown(
    "<div class='component-title-box'>📁 TIẾP NHẬN TÀI LIỆU KỸ THUẬT (UP FILE TECHPACK)</div>",
    unsafe_allow_html=True,
)
uploaded_file = st.file_uploader(
    "Tải Techpack PDF hoặc hình ảnh Sketch:",
    type=["pdf", "png", "jpg", "jpeg"],
)

if "avg_area_growth_pct" not in st.session_state:
    st.session_state["avg_area_growth_pct"] = 0.0

if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    file_name = uploaded_file.name
    st.info(f"📂 Đã tải lên: **{file_name}** ({len(file_bytes) / 1024:.2f} KB)")

    if not style_input:
        if file_name.lower().endswith(".pdf"):
            detected_style = detect_style_from_pdf(file_bytes)
        else:
            detected_style = ""

        if not detected_style:
            detected_style = detect_style_from_filename(file_name)

        if detected_style:
            style_input = detected_style
            st.sidebar.success(f"Nhận diện mã từ tài liệu/tên file: {style_input}")

# =========================================================================
# QUERY GTAS
# =========================================================================
if style_input:
    st.session_state["matched_style_name"] = style_input

    # Fetch once per style; changing style clears stale records
    if st.session_state.get("gtas_loaded_style") != style_input:
        with st.spinner(f"Đang truy vấn GTAS cho mã {style_input}..."):
            bom_result = gtas_client.search_collection(
                API_GET_BOM, style_input, limit=100
            )
            sketch_result = gtas_client.search_collection(
                API_GET_SKETCH, style_input, limit=20
            )
            pom_result = gtas_client.get_pom(style_input)

        st.session_state["gtas_loaded_style"] = style_input
        st.session_state["gtas_bom_result"] = bom_result
        st.session_state["gtas_sketch_result"] = sketch_result
        st.session_state["gtas_pom_result"] = pom_result

        st.session_state["bom_records"] = (
            normalize_records(bom_result["data"])
            if bom_result["ok"] else []
        )

    bom_result = st.session_state.get("gtas_bom_result", {})
    sketch_result = st.session_state.get("gtas_sketch_result", {})
    pom_result = st.session_state.get("gtas_pom_result", {})

    st.markdown(
        "<div class='component-title-box'>🔗 TRẠNG THÁI KẾT NỐI GTAS</div>",
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)

    with c1:
        if bom_result.get("ok"):
            st.success("BOM API: HTTP 200")
        else:
            st.error(f"BOM API: {bom_result.get('error', 'Không có dữ liệu')}")

    with c2:
        if sketch_result.get("ok"):
            st.success("Styles Lib API: HTTP 200")
        else:
            st.warning(
                f"Styles Lib: {sketch_result.get('error', 'Chưa có dữ liệu')}"
            )

    with c3:
        if pom_result.get("ok"):
            st.success("POM API: HTTP 200")
        else:
            st.warning(
                f"POM: {pom_result.get('error', 'Chưa có dữ liệu')}"
            )

    with st.expander("Xem JSON phản hồi GTAS để xác định schema"):
        st.write("BOM — /items/manual_pattern7")
        st.json(bom_result.get("data") if bom_result.get("ok") else {
            "error": bom_result.get("error"),
            "status": bom_result.get("status"),
        })
        st.write("Styles Lib — /items/stylepatternpkt")
        st.json(sketch_result.get("data") if sketch_result.get("ok") else {
            "error": sketch_result.get("error"),
            "status": sketch_result.get("status"),
        })
        st.write("POM — filter1/search")
        st.json(pom_result.get("data") if pom_result.get("ok") else {
            "error": pom_result.get("error"),
            "status": pom_result.get("status"),
        })

    # =========================================================================
    # BOM NORMALIZATION AND PROJECTION
    # =========================================================================
    raw_bom_records = st.session_state.get("bom_records", [])
    bom_records = extract_bom_rows(raw_bom_records)

    if not bom_result.get("ok"):
        st.error(
            "Không truy cập được BOM GTAS. Hệ thống không dùng BOM giả "
            "và không tính định mức chính thức."
        )
        st.stop()

    if not bom_records:
        st.warning(
            "GTAS có phản hồi nhưng chưa nhận diện được trường loại vật tư "
            "và định mức. Mở phần JSON ở trên để xác định schema rồi ánh xạ trường."
        )
        if raw_bom_records:
            st.dataframe(
                pd.json_normalize(raw_bom_records),
                use_container_width=True,
                hide_index=True,
            )
        st.stop()

    st.markdown(
        "<div class='component-title-box'>🔮 AI CONSUMPTION PROJECTION ENGINE</div>",
        unsafe_allow_html=True,
    )
    st.success(
        f"Đã nhận diện {len(bom_records)} dòng BOM có loại vật tư và định mức."
    )

    # Average old consumption by material type
    sums = {}
    counts = {}
    for record in bom_records:
        ctype = record["consumption_type"]
        qty = record["consumption_value"]
        sums[ctype] = sums.get(ctype, 0.0) + qty
        counts[ctype] = counts.get(ctype, 0) + 1

    final_old_bom_summary = {
        key: round(sums[key] / counts[key], 4)
        for key in sums if counts.get(key, 0) > 0
    }

    style_name_upper = str(
        st.session_state.get("matched_style_name", "")
    ).upper()

    # Product class heuristic: only uses detected style text; user can edit factor.
    default_fabric_factor = 0.65
    product_type_label = "Tiêu chuẩn (mặc định)"

    if any(k in style_name_upper for k in ["LONG PANT", "TROUSER", "JEAN", "QUAN DAI"]):
        default_fabric_factor = 0.85
        product_type_label = "Quần dài"
    elif any(k in style_name_upper for k in ["SHORT", "QUAN NGON", "QUAN DUI"]):
        default_fabric_factor = 0.45
        product_type_label = "Quần short"
    elif any(k in style_name_upper for k in ["JACKET", "COAT", "AO KHOAC", "BLAZER", "VEST"]):
        default_fabric_factor = 0.75
        product_type_label = "Áo khoác / Vest"
    elif any(k in style_name_upper for k in ["TEE", "SHIRT", "POLO", "AO THUN", "AO SOMI"]):
        default_fabric_factor = 0.55
        product_type_label = "Áo thun / Áo sơ mi"
    elif any(k in style_name_upper for k in ["SKIRT", "DRESS", "VAY", "DAM"]):
        default_fabric_factor = 0.70
        product_type_label = "Váy / Đầm"

    st.markdown("<div class='card-container'>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        shape_factor = st.number_input(
            "Độ biến thiên thông số POM trung bình (%)",
            min_value=-100.0,
            max_value=500.0,
            value=float(st.session_state.get("avg_area_growth_pct", 0.0)),
            step=0.1,
        )
    with col2:
        fabric_growth_factor = st.number_input(
            f"Hệ số thực nghiệm vải ({product_type_label})",
            min_value=0.0,
            max_value=2.0,
            value=float(default_fabric_factor),
            step=0.05,
        )
    with col3:
        wastage_buffer = st.number_input(
            "Hao hụt sản xuất cấu hình thêm (%)",
            min_value=0.0,
            max_value=100.0,
            value=0.0,
            step=0.5,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    projection_rows = []

    for ctype, avg_old_qty in final_old_bom_summary.items():
        ctype_upper = ctype.upper()

        if any(k in ctype_upper for k in ["MAIN", "FABRIC", "BODY", "SHELL"]):
            actual_fabric_factor = fabric_growth_factor
            if shape_factor > 10.0:
                actual_fabric_factor = max(0.88, fabric_growth_factor)

            adjusted_shape_factor = shape_factor * actual_fabric_factor
            base_projected = avg_old_qty * (1 + adjusted_shape_factor / 100)
            projected_dm = base_projected * (1 + wastage_buffer / 100)

            if shape_factor >= 15.0 and projected_dm < 1.05:
                projected_dm = max(projected_dm, avg_old_qty * 1.05)

            note = (
                f"Vải chính: hệ số {actual_fabric_factor:.2f} × "
                f"biến thiên POM {shape_factor:.2f}%"
            )

        elif any(k in ctype_upper for k in [
            "LINING", "RIB", "COMBINATION", "POCKET",
            "INTERLINING", "POCKETING"
        ]):
            base_projected = avg_old_qty * (1 + shape_factor / 100)
            projected_dm = base_projected * (1 + wastage_buffer / 100)
            note = f"Vải lót/phụ: điều chỉnh theo POM {shape_factor:.2f}%"

        else:
            projected_dm = avg_old_qty * (1 + wastage_buffer / 100)
            note = "Vật tư khác: giữ định mức gốc, chỉ cộng hao hụt cấu hình"

        projection_rows.append({
            "Phân loại vật tư (Type)": ctype,
            "ĐM Trung bình mã cũ (GTAS Kho)": round(avg_old_qty, 4),
            "ĐM Dự phóng mẫu mới (AI)": round(projected_dm, 4),
            "Ghi chú thuật toán": note,
        })

    df_projection = pd.DataFrame(projection_rows)
    st.write("### BẢNG ĐỐI CHIẾU VÀ DỰ PHÓNG ĐỊNH MỨC")
    st.dataframe(df_projection, use_container_width=True, hide_index=True)

    csv_data = df_projection.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Tải bảng dự phóng CSV",
        data=csv_data,
        file_name=f"GTAS_projection_{style_input}.csv",
        mime="text/csv",
    )

else:
    st.info(
        "Nhập mã hàng ở Sidebar hoặc tải Techpack PDF để nhận diện mã hàng "
        "và truy vấn GTAS."
    )
