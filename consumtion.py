import io
import re
import difflib
import streamlit as st
import pandas as pd

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

st.set_page_config(page_title="Dự đoán định mức vải - Full POM", page_icon="🧵", layout="wide")

# ==============================================================================
# 1. DANH MỤC 8 DÒNG HÀNG & BỘ THÔNG SỐ POM CHUẨN
# ==============================================================================
CATEGORIES = {
    "Quần short": {
        "specs": [
            ("Outseam - Dài quần ngoài", "length"),
            ("Inseam - Dài quần trong", "length"),
            ("Waist - Vòng eo / Lưng quần", "width"),
            ("Hip - Vòng mông", "width"),
            ("Thigh - Rộng đùi", "width"),
            ("Leg Opening - Rộng ống", "width"),
            ("Front Rise - Cao đáy trước", "rise"),
            ("Back Rise - Cao đáy sau", "rise"),
            ("Waistband Height - Cao bản lưng / cạp", "detail"),
            ("Fly Length - Dài moi / dây kéo", "detail"),
            ("Fly Width - Rộng moi", "detail"),
            ("Belt Loop Length - Dài đỉa quần", "detail"),
            ("Belt Loop Width - Rộng đỉa quần", "detail"),
            ("Front Pocket Opening - Miệng túi trước", "detail"),
            ("Front Pocket Bag Length - Dài lót túi trước", "detail"),
            ("Front Pocket Bag Width - Rộng lót túi trước", "detail"),
            ("Coin Pocket Width - Rộng túi đồng hồ", "detail"),
            ("Coin Pocket Height - Cao túi đồng hồ", "detail"),
            ("Back Pocket Width - Rộng túi sau", "detail"),
            ("Back Pocket Height - Cao túi sau", "detail"),
            ("Back Pocket Flap Width - Rộng nắp túi sau", "detail"),
            ("Back Pocket Flap Height - Cao nắp túi sau", "detail"),
            ("Cargo Pocket Width - Rộng túi hộp bên hông", "detail"),
            ("Cargo Pocket Height - Cao túi hộp bên hông", "detail"),
            ("Cargo Flap Width - Rộng nắp túi hộp", "detail"),
            ("Cargo Flap Height - Cao nắp túi hộp", "detail"),
            ("Hem Turn-up - Bản gấu / lai quần", "detail"),
        ],
        "defaults": {
            "Outseam - Dài quần ngoài": (14.750, 14.500),
            "Inseam - Dài quần trong": (6.500, 4.000),
            "Waist - Vòng eo / Lưng quần": (16.500, 16.250),
            "Hip - Vòng mông": (21.000, 20.250),
            "Thigh - Rộng đùi": (14.250, 13.625),
            "Leg Opening - Rộng ống": (13.625, 13.375),
            "Front Rise - Cao đáy trước": (11.250, 12.125),
            "Back Rise - Cao đáy sau": (16.250, 16.000),
        },
    },
    "Quần jean dài": {
        "specs": [
            ("Outseam - Dài quần ngoài", "length"),
            ("Inseam - Dài quần trong", "length"),
            ("Waist - Vòng eo / Lưng quần", "width"),
            ("Hip - Vòng mông", "width"),
            ("Thigh - Rộng đùi", "width"),
            ("Knee - Rộng gối", "width"),
            ("Leg Opening - Rộng ống", "width"),
            ("Front Rise - Cao đáy trước", "rise"),
            ("Back Rise - Cao đáy sau", "rise"),
            ("Back Yoke Height - Cao đô sau", "detail"),
            ("Waistband Height - Cao bản lưng / cạp", "detail"),
            ("Fly Length - Dài moi / dây kéo", "detail"),
            ("Fly Width - Rộng moi", "detail"),
            ("Belt Loop Length - Dài đỉa quần", "detail"),
            ("Belt Loop Width - Rộng đỉa quần", "detail"),
            ("Front Pocket Opening - Miệng túi trước", "detail"),
            ("Front Pocket Bag Length - Dài lót túi trước", "detail"),
            ("Front Pocket Bag Width - Rộng lót túi trước", "detail"),
            ("Coin Pocket Width - Rộng túi đồng hồ", "detail"),
            ("Coin Pocket Height - Cao túi đồng hồ", "detail"),
            ("Back Pocket Width - Rộng túi sau", "detail"),
            ("Back Pocket Height - Cao túi sau", "detail"),
            ("Back Pocket Flap Width - Rộng nắp túi sau", "detail"),
            ("Back Pocket Flap Height - Cao nắp túi sau", "detail"),
            ("Cargo Pocket Width - Rộng túi hộp", "detail"),
            ("Cargo Pocket Height - Cao túi hộp", "detail"),
            ("Cargo Flap Width - Rộng nắp túi hộp", "detail"),
            ("Cargo Flap Height - Cao nắp túi hộp", "detail"),
            ("Hem Turn-up - Bản gấu / lai quần", "detail"),
        ],
        "defaults": {},
    },
    "Quần kaki / quần dài": {
        "specs": [
            ("Outseam - Dài quần ngoài", "length"),
            ("Inseam - Dài quần trong", "length"),
            ("Waist - Vòng eo / Lưng quần", "width"),
            ("Hip - Vòng mông", "width"),
            ("Thigh - Rộng đùi", "width"),
            ("Knee - Rộng gối", "width"),
            ("Leg Opening - Rộng ống", "width"),
            ("Front Rise - Cao đáy trước", "rise"),
            ("Back Rise - Cao đáy sau", "rise"),
            ("Waistband Height - Cao bản lưng / cạp", "detail"),
            ("Fly Length - Dài moi / dây kéo", "detail"),
            ("Fly Width - Rộng moi", "detail"),
            ("Belt Loop Length - Dài đỉa quần", "detail"),
            ("Belt Loop Width - Rộng đỉa quần", "detail"),
            ("Front Pocket Opening - Miệng túi trước", "detail"),
            ("Front Pocket Bag Length - Dài lót túi trước", "detail"),
            ("Front Pocket Bag Width - Rộng lót túi trước", "detail"),
            ("Back Welt Pocket Width - Rộng miệng túi hậu mổ", "detail"),
            ("Back Pocket Bag Length - Dài lót túi hậu", "detail"),
            ("Back Pocket Flap Width - Rộng nắp túi sau", "detail"),
            ("Back Pocket Flap Height - Cao nắp túi sau", "detail"),
            ("Cargo Pocket Width - Rộng túi hộp", "detail"),
            ("Cargo Pocket Height - Cao túi hộp", "detail"),
            ("Cargo Flap Width - Rộng nắp túi hộp", "detail"),
            ("Cargo Flap Height - Cao nắp túi hộp", "detail"),
            ("Pleat Depth - Độ sâu ly quần", "detail"),
            ("Hem Turn-up - Bản gấu / lai quần", "detail"),
        ],
        "defaults": {},
    },
    "Áo sơ mi": {
        "specs": [
            ("Body Length Front - Dài áo trước", "length"),
            ("Body Length Back - Dài áo sau", "length"),
            ("Chest - Vòng ngực", "width"),
            ("Waist - Vòng eo áo", "width"),
            ("Hem Width - Rộng lai áo", "width"),
            ("Shoulder - Ngang vai", "width"),
            ("Back Yoke Height - Cao đô sau", "detail"),
            ("Armhole - Vòng nách", "detail"),
            ("Bicep - Rộng bắp tay", "width"),
            ("Sleeve Length - Dài tay dài", "length"),
            ("Short Sleeve Length - Dài tay ngắn", "length"),
            ("Sleeve Opening - Rộng cửa tay ngắn", "width"),
            ("Collar Length - Dài lá cổ", "detail"),
            ("Collar Point - Dài mũi cổ", "detail"),
            ("Collar Band Height - Cao chân cổ", "detail"),
            ("Front Placket Width - Rộng nẹp áo trước", "detail"),
            ("Cuff Height - Cao măng sét", "detail"),
            ("Cuff Width - Rộng măng sét", "detail"),
            ("Sleeve Placket Length - Dài nẹp trụ tay", "detail"),
            ("Chest Pocket Width - Rộng túi ngực", "detail"),
            ("Chest Pocket Height - Cao túi ngực", "detail"),
            ("Chest Pocket Flap Width - Rộng nắp túi ngực", "detail"),
            ("Chest Pocket Flap Height - Cao nắp túi ngực", "detail"),
        ],
        "defaults": {},
    },
    "T-shirt / Polo": {
        "specs": [
            ("Body Length - Dài áo", "length"),
            ("Chest - Vòng ngực", "width"),
            ("Waist - Vòng eo áo", "width"),
            ("Hem Width - Rộng lai áo", "width"),
            ("Shoulder - Ngang vai", "width"),
            ("Armhole - Vòng nách", "detail"),
            ("Bicep - Rộng bắp tay", "width"),
            ("Sleeve Length - Dài tay", "length"),
            ("Sleeve Opening - Rộng cửa tay", "width"),
            ("Neck Width - Rộng ngang cổ", "detail"),
            ("Front Neck Drop - Sâu cổ trước", "detail"),
            ("Back Neck Drop - Sâu cổ sau", "detail"),
            ("Collar Rib Height - Cao bo cổ", "detail"),
            ("Placket Length - Dài nẹp trụ Polo", "detail"),
            ("Placket Width - Rộng nẹp trụ Polo", "detail"),
            ("Cuff Rib Height - Cao bo tay", "detail"),
            ("Chest Pocket Width - Rộng túi ngực", "detail"),
            ("Chest Pocket Height - Cao túi ngực", "detail"),
            ("Chest Pocket Flap Width - Rộng nắp túi ngực", "detail"),
            ("Chest Pocket Flap Height - Cao nắp túi ngực", "detail"),
        ],
        "defaults": {},
    },
    "Hoodie": {
        "specs": [
            ("Body Length - Dài áo", "length"),
            ("Chest - Vòng ngực", "width"),
            ("Waist - Vòng eo áo", "width"),
            ("Hem Width - Rộng lai áo", "width"),
            ("Shoulder - Ngang vai", "width"),
            ("Armhole - Vòng nách", "detail"),
            ("Bicep - Rộng bắp tay", "width"),
            ("Sleeve Length - Dài tay", "length"),
            ("Cuff Rib Height - Cao bo tay", "detail"),
            ("Cuff Opening - Rộng cửa tay", "width"),
            ("Bottom Rib Height - Cao bo lai", "detail"),
            ("Neck Width - Rộng ngang cổ", "detail"),
            ("Hood Height - Cao mũ / nón", "detail"),
            ("Hood Width - Rộng mũ / nón", "detail"),
            ("Front Zipper Length - Dài dây kéo thân trước", "detail"),
            ("Kangaroo Pocket Width - Rộng túi bụng Kangaroo", "detail"),
            ("Kangaroo Pocket Height - Cao túi bụng Kangaroo", "detail"),
            ("Side Pocket Opening - Miệng túi sườn", "detail"),
            ("Sleeve Pocket Width - Rộng túi túi tay áo", "detail"),
            ("Sleeve Pocket Height - Cao túi tay áo", "detail"),
            ("Pocket Flap Width - Rộng nắp túi", "detail"),
            ("Pocket Flap Height - Cao nắp túi", "detail"),
        ],
        "defaults": {},
    },
    "Jacket": {
        "specs": [
            ("Body Length Front - Dài áo trước", "length"),
            ("Body Length Back - Dài áo sau", "length"),
            ("Chest - Vòng ngực", "width"),
            ("Waist - Vòng eo áo", "width"),
            ("Hem Width - Rộng lai áo", "width"),
            ("Shoulder - Ngang vai", "width"),
            ("Back Yoke Height - Cao đô sau", "detail"),
            ("Armhole - Vòng nách", "detail"),
            ("Bicep - Rộng bắp tay", "width"),
            ("Sleeve Length - Dài tay", "length"),
            ("Cuff Height - Cao măng sét / bo tay", "detail"),
            ("Cuff Opening - Rộng cửa tay", "width"),
            ("Collar Height - Cao cổ áo", "detail"),
            ("Collar Length - Dài lá cổ", "detail"),
            ("Hood Height - Cao mũ / nón rời hoặc liền", "detail"),
            ("Hood Width - Rộng mũ / nón", "detail"),
            ("Storm Flap Width - Rộng nẹp che dây kéo", "detail"),
            ("Chest Pocket Width - Rộng túi ngực", "detail"),
            ("Chest Pocket Height - Cao túi ngực", "detail"),
            ("Chest Flap Width - Rộng nắp túi ngực", "detail"),
            ("Chest Flap Height - Cao nắp túi ngực", "detail"),
            ("Lower Pocket Width - Rộng túi dưới", "detail"),
            ("Lower Pocket Height - Cao túi dưới", "detail"),
            ("Lower Flap Width - Rộng nắp túi dưới", "detail"),
            ("Lower Flap Height - Cao nắp túi dưới", "detail"),
            ("Inside Pocket Width - Rộng túi trong lót", "detail"),
            ("Inside Pocket Height - Cao túi trong lót", "detail"),
            ("Sleeve Pocket Width - Rộng túi tay áo", "detail"),
            ("Sleeve Pocket Height - Cao túi tay áo", "detail"),
        ],
        "defaults": {},
    },
    "Váy / đầm": {
        "specs": [
            ("Body Length - Dài váy / đầm", "length"),
            ("Chest - Vòng ngực", "width"),
            ("Waist - Vòng eo", "width"),
            ("Hip - Vòng mông", "width"),
            ("Hem Width - Rộng lai váy", "width"),
            ("Shoulder - Ngang vai", "width"),
            ("Armhole - Vòng nách", "detail"),
            ("Sleeve Length - Dài tay", "length"),
            ("Sleeve Opening - Rộng cửa tay", "width"),
            ("Neck Width - Rộng ngang cổ", "detail"),
            ("Front Neck Drop - Sâu cổ trước", "detail"),
            ("Back Neck Drop - Sâu cổ sau", "detail"),
            ("Waistband Height - Cao bản cạp váy", "detail"),
            ("Zipper Length - Dài dây kéo giọt lệ / sườn", "detail"),
            ("Side Pocket Opening - Miệng túi sườn", "detail"),
            ("Patch Pocket Width - Rộng túi đắp", "detail"),
            ("Patch Pocket Height - Cao túi đắp", "detail"),
            ("Pocket Flap Width - Rộng nắp túi", "detail"),
            ("Pocket Flap Height - Cao nắp túi", "detail"),
            ("Slit Length - Dài xẻ tà váy", "detail"),
            ("Ruffle / Flounce Height - Cao bèo nhún", "detail"),
        ],
        "defaults": {},
    },
}

# ==============================================================================
# 2. TỪ ĐIỂN NHẬN DIỆN POM & BỘ LỌC NGƯỠNG TỐI THIỂU / VẢI LÓT BOM
# ==============================================================================
POM_RULES = {
    # --- NHÓM QUẦN ---
    "Outseam - Dài quần ngoài": (["outseam", "side seam", "side length", "total length", "leg 015"], ["pocket", "flap", "inseam", "opening", "slit", "fm", "from"]),
    "Inseam - Dài quần trong": (["inseam", "inside leg", "crotch to hem", "leg 012"], ["pocket", "outseam", "opening", "leg 015"]),
    "Waist - Vòng eo / Lưng quần": (["waist width", "waist"], ["band", "pocket", "drop", "elastic", "loop", "level", "below", "edge", "stitch", "seam", "placement", "plcmnt", "position", "pitch"]),
    "Hip - Vòng mông": (["low hip width", "hip width", "high hip width", "hip", "seat"], ["level", "pocket", "flap", "placement", "plcmnt", "below", "seam"]),
    "Thigh - Rộng đùi": (["thigh width", "thigh"], ["pocket", "level", "below", "seam"]),
    "Knee - Rộng gối": (["knee width", "knee"], ["pocket", "level", "below", "seam"]),
    "Leg Opening - Rộng ống": (["leg opening", "bottom opening", "hem opening"], ["pocket", "height", "turn"]),
    "Front Rise - Cao đáy trước": (["front rise", "cf rise"], ["crotch", "seam"]),
    "Back Rise - Cao đáy sau": (["back rise", "cb rise"], ["crotch", "seam"]),
    "Waistband Height - Cao bản lưng / cạp": (["waistband width", "waistband height", "waistband"], ["pocket", "length"]),
    "Fly Length - Dài moi / dây kéo": (["fly length", "zipper length", "j stitch length"], ["width"]),
    "Fly Width - Rộng moi": (["fly width", "j stitch width"], ["length"]),

    # --- TÚI & NẮP TÚI ---
    "Front Pocket Opening - Miệng túi trước": (["front pocket opening", "pocket opening"], ["coin", "back", "side pocket"]),
    "Front Pocket Bag Length - Dài lót túi trước": (["front pocket height", "front pocket length", "front pocket bag length"], ["width", "opening", "placement", "plcmnt", "fm"]),
    "Front Pocket Bag Width - Rộng lót túi trước": (["front pocket width", "front pocket bag width"], ["height", "length", "opening", "placement", "plcmnt", "fm"]),
    "Coin Pocket Width - Rộng túi đồng hồ": (["coin pocket width"], ["height", "length"]),
    "Coin Pocket Height - Cao túi đồng hồ": (["coin pocket height", "coin pocket length"], ["width"]),
    "Back Pocket Width - Rộng túi sau": (["back pocket width"], ["flap", "height", "placement", "plcmnt", "fm"]),
    "Back Welt Pocket Width - Rộng miệng túi hậu mổ": (["back pocket width", "back welt pocket"], ["flap", "height", "placement", "plcmnt", "fm"]),
    "Back Pocket Height - Cao túi sau": (["back pocket height", "back pocket length"], ["flap", "width", "placement", "plcmnt", "fm"]),
    "Back Pocket Bag Length - Dài lót túi hậu": (["back pocket height", "back pocket length"], ["flap", "width", "placement", "plcmnt", "fm"]),
    "Back Pocket Flap Width - Rộng nắp túi sau": (["back pocket flap width", "flap width"], ["height"]),
    "Back Pocket Flap Height - Cao nắp túi sau": (["back pocket flap height", "flap height"], ["width"]),

    # --- NHÓM ÁO & VÁY / ĐẦM ---
    "Body Length Front - Dài áo trước": (["front length", "cf length", "body length front"], ["pocket", "zipper", "placket", "drop"]),
    "Body Length Back - Dài áo sau": (["back length", "cb length", "body length back"], ["pocket", "zipper", "placket", "drop"]),
    "Body Length - Dài áo": (["body length", "hps length", "total length", "front length"], ["pocket", "zipper", "placket", "sleeve"]),
    "Body Length - Dài váy / đầm": (["body length", "dress length", "skirt length", "hps length"], ["pocket", "zipper", "sleeve", "slit"]),
    "Chest - Vòng ngực": (["chest width", "chest", "bust width", "bust"], ["pocket", "placement", "below", "armhole"]),
    "Waist - Vòng eo áo": (["waist width", "waist"], ["band", "pocket", "placement", "below"]),
    "Waist - Vòng eo": (["waist width", "waist"], ["band", "pocket", "placement", "below"]),
    "Hem Width - Rộng lai áo": (["hem width", "bottom width", "sweep"], ["height", "turn", "rib"]),
    "Hem Width - Rộng lai váy": (["hem width", "bottom width", "sweep"], ["height", "turn"]),
    "Shoulder - Ngang vai": (["across shoulder", "shoulder width", "shoulder to shoulder"], ["slope", "drop", "seam", "pocket"]),
    "Bicep - Rộng bắp tay": (["bicep", "muscle width", "upper arm"], ["below"]),
    "Sleeve Length - Dài tay": (["sleeve length", "long sleeve length"], ["opening", "placket", "pocket", "short"]),
    "Sleeve Length - Dài tay dài": (["sleeve length", "long sleeve length"], ["opening", "placket", "pocket", "short"]),
    "Short Sleeve Length - Dài tay ngắn": (["short sleeve length"], ["opening", "placket"]),
    "Sleeve Opening - Rộng cửa tay": (["sleeve opening", "cuff opening"], ["height", "length"]),
    "Sleeve Opening - Rộng cửa tay ngắn": (["sleeve opening", "short sleeve opening"], ["height", "length"]),
    "Cuff Opening - Rộng cửa tay": (["cuff opening", "sleeve opening"], ["height", "length"]),
    "Hood Height - Cao mũ / nón": (["hood height", "hood length"], ["width"]),
    "Hood Width - Rộng mũ / nón": (["hood width", "hood depth"], ["height", "length"]),
    "Kangaroo Pocket Width - Rộng túi bụng Kangaroo": (["kangaroo pocket width", "pouch pocket width"], ["height", "length"]),
    "Kangaroo Pocket Height - Cao túi bụng Kangaroo": (["kangaroo pocket height", "pouch pocket height"], ["width"]),
}

MIN_POM_VALUES = {
    "Outseam": 8.0,
    "Body Length": 10.0,
    "Waist": 8.0,
    "Hip": 10.0,
    "Chest": 10.0,
    "Thigh": 6.0,
    "Shoulder": 8.0,
    "Front Rise": 5.0,
    "Back Rise": 7.0,
}

# Các chi tiết mặc định thường thuộc Vải lót / Bo Rib theo BOM (có thể tick lại nếu dùng vải chính)
NON_SHELL_KEYWORDS = [
    "pocket bag", "lót túi", "inside pocket", "túi trong lót", "lining", "rib height", "cao bo"
]

# ==============================================================================
# 3. CÁC HÀM XỬ LÝ DỮ LIỆU TECHPACK & ĐỌC SỐ
# ==============================================================================
def parse_number(value):
    if value is None or isinstance(value, (list, tuple, dict)):
        return 0.0
    try:
        if pd.isna(value):
            return 0.0
    except Exception:
        pass
    raw_str = str(value).strip()
    if not raw_str:
        return 0.0

    frac_match = re.match(r"^(\d+)\s+(\d+)/(\d+)$", raw_str)
    if frac_match:
        return float(frac_match.group(1)) + float(frac_match.group(2)) / float(frac_match.group(3))
    only_frac = re.match(r"^(\d+)/(\d+)$", raw_str)
    if only_frac and float(only_frac.group(2)) != 0:
        return float(only_frac.group(1)) / float(only_frac.group(2))

    s = raw_str.replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(",", "") if s.rfind(",") < s.rfind(".") else s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    return float(s)


def normalize_text(s):
    s = str(s).lower()
    s = re.sub(r"[^a-z0-9àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def extract_table_rows_from_file(uploaded_file):
    if uploaded_file is None:
        return []
    fname = uploaded_file.name.lower()
    rows_to_process = []

    if fname.endswith((".xlsx", ".xls")):
        xls = pd.ExcelFile(uploaded_file)
        for sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet, header=None)
            rows_to_process.extend(df.values.tolist())
    elif fname.endswith(".pdf"):
        if pdfplumber is None:
            st.warning("Chưa cài thư viện pdfplumber để đọc file PDF.")
            return []
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for tbl in tables:
                    if tbl:
                        rows_to_process.extend(tbl)

    extracted = []
    for row in rows_to_process:
        cells = [str(c).replace("
", " ").strip() for c in row if c is not None and str(c).strip() != ""]
        if len(cells) < 2:
            continue

        if re.match(r"^\d{1,2}[.)]?$", cells[0]):
            cells = cells[1:]

        text_cols, size_nums = [], []
        for c in cells:
            if any(sym in c for sym in ["±", "+/-", "+-", "%"]):
                continue
            try:
                val = parse_number(c)
                if 0.1 <= val <= 150:
                    size_nums.append(val)
            except Exception:
                clean_txt = re.sub(r"[^a-zA-ZÀ-ỹ0-9\-\s]", "", c).strip()
                if len(clean_txt) >= 3:
                    text_cols.append(c)

        if len(size_nums) >= 3 and size_nums[0] <= 0.75 and size_nums[1] > size_nums[0] * 2:
            size_nums = size_nums[1:]

        if text_cols and size_nums:
            full_label = " - ".join(text_cols[:2]) if len(text_cols) >= 2 else text_cols[0]
            extracted.append((full_label, size_nums))

    return extracted


def match_tp_to_full_poms(uploaded_file, specs, size_col_idx=0):
    raw_rows = extract_table_rows_from_file(uploaded_file)
    matched = {}
    debug_rows = []
    if not raw_rows:
        return matched, debug_rows

    for raw_label, num_list in raw_rows:
        norm_label = normalize_text(raw_label)
        idx = min(size_col_idx, len(num_list) - 1)
        chosen_val = float(num_list[idx])

        best_pom, best_score = None, 0.0
        for full_name, _ in specs:
            if full_name in POM_RULES:
                inc_kws, exc_kws = POM_RULES[full_name]
                if any(ex in norm_label for ex in exc_kws):
                    continue
                if any(inc in norm_label for inc in inc_kws):
                    score = 0.98
                else:
                    score = 0.0
            else:
                parts = [normalize_text(p) for p in full_name.split("-") if normalize_text(p)]
                score = max((difflib.SequenceMatcher(None, kw, norm_label).ratio() for kw in parts), default=0.0)

            if score > best_score:
                best_score, best_pom = score, full_name

        is_too_small = False
        if best_pom:
            for key_prefix, min_val in MIN_POM_VALUES.items():
                if key_prefix in best_pom and chosen_val < min_val:
                    is_too_small = True
                    break

        if is_too_small:
            debug_rows.append({
                "Dòng đọc từ Techpack": raw_label,
                "Các Size (đã bỏ Dung sai)": str(num_list),
                "Số đã lấy": chosen_val,
                "Trạng thái": f"⚠️ Bỏ qua (Số {chosen_val} quá nhỏ cho {best_pom})",
            })
            continue

        status_str = f"✅ {best_pom}" if (best_pom and best_score >= 0.75) else "❌ Bỏ qua"
        debug_rows.append({
            "Dòng đọc từ Techpack": raw_label,
            "Các Size (đã bỏ Dung sai)": str(num_list),
            "Số đã lấy": chosen_val,
            "Trạng thái": status_str,
        })

        if best_pom and best_score >= 0.75 and best_pom not in matched:
            matched[best_pom] = chosen_val

    return matched, debug_rows

# ==============================================================================
# 4. HÀM TRỌNG SỐ CHIỀU RỘNG & TÍNH ĐỊNH MỨC (ĐỒNG BỘ TÀI LIỆU V8.0)
# ==============================================================================
def width_weights(width_names):
    raw = {}
    for name in width_names:
        low = name.lower()
        if "hip" in low or "mông" in low or "chest" in low or "ngực" in low:
            raw[name] = 0.45      # Vùng rộng nhất quyết định sơ đồ (Mông / Ngực)
        elif "thigh" in low or "đùi" in low or "shoulder" in low or "vai" in low:
            raw[name] = 0.35      # Vùng bản rập lớn thứ hai (Đùi / Vai)
        elif "waist" in low or "eo" in low or "knee" in low or "gối" in low:
            raw[name] = 0.15      # Vùng trung gian (Eo / Gối)
        elif "opening" in low or "ống" in low or "cửa tay" in low or "hem" in low or "lai" in low:
            raw[name] = 0.05      # Rộng ống / cửa tay ít tốn vải khi lồng sơ đồ đầu-đuôi
        else:
            raw[name] = 0.10
    total = sum(raw.values()) or 1.0
    return {k: v / total for k, v in raw.items()}


def calculate_full_poms(df_input, specs, old_dm):
    spec_map = dict(specs)
    detail_rows = []
    valid_changes, valid_old, valid_new, grouped_valid = {}, {}, {}, {}
    new_only_count = 0

    for _, row in df_input.iterrows():
        pom = str(row.get("Tên POM", "")).strip()
        if not pom or pom == "None":
            continue

        old_val = parse_number(row.get("Mã cũ", 0.0))
        new_val = parse_number(row.get("Mã mới", 0.0))
        group = str(row.get("Nhóm", "")).strip() or spec_map.get(pom, "detail")
        is_shell = bool(row.get("Vải chính?", True))

        # Lọc theo BOM: Bỏ qua các chi tiết là Vải lót / Vải phối / Bo Rib
        if not is_shell:
            status = "🚫 Vải lót / Vải phối (Loại trừ theo BOM)"
            pct_str = "—"
        elif old_val == 0 and new_val == 0:
            status, pct_str = "Không có ở cả 2 mã (Bỏ qua)", "—"
        elif old_val == 0 or new_val == 0:
            status, pct_str = "1 bên = 0 (Không so sánh)", "Không so sánh"
            if old_val == 0 and new_val > 0:
                new_only_count += 1
        else:
            status = "✅ Đưa vào so sánh (Vải chính)"
            pct = (new_val / old_val - 1) * 100
            pct_str = f"{pct:+.2f}%"
            valid_changes[pom] = pct
            valid_old[pom] = old_val
            valid_new[pom] = new_val
            grouped_valid.setdefault(group, []).append(pom)

        detail_rows.append({
            "Vải chính?": is_shell,
            "Nhóm": group,
            "Tên POM": pom,
            "Mã cũ": old_val,
            "Mã mới": new_val,
            "Chênh lệch": round(new_val - old_val, 3),
            "Thay đổi (%)": pct_str,
            "Trạng thái": status,
        })

    if not valid_changes:
        raise ValueError("Cần ít nhất 1 thông số POM Vải chính có giá trị > 0 ở cả Mã cũ và Mã mới.")

    extra_detail_pct = new_only_count * 0.8

    def group_active_avg(grp_name):
        names = grouped_valid.get(grp_name, [])
        if not names:
            return 0.0
        active_vals = [valid_changes[n] for n in names if abs(valid_changes[n]) > 0.01]
        if not active_vals:
            return 0.0
        return sum(active_vals) / len(active_vals)

    # 1. Tính tỷ lệ thay đổi Chiều dài (Xử lý Quần short, Quần dài & Áo)
    len_names = grouped_valid.get("length", [])
    rise_names = grouped_valid.get("rise", [])
    has_out = "Outseam - Dài quần ngoài" in len_names
    has_in = "Inseam - Dài quần trong" in len_names

    if has_out and has_in:
        o_out, n_out = valid_old["Outseam - Dài quần ngoài"], valid_new["Outseam - Dài quần ngoài"]
        o_in, n_in = valid_old["Inseam - Dài quần trong"], valid_new["Inseam - Dài quần trong"]
        pct_out = (n_out / o_out - 1) * 100
        pct_in = (n_in / o_in - 1) * 100
        if o_in < 15.0:
            len_pct = (pct_out + pct_in) / 2
        else:
            len_pct = pct_out
    elif has_out:
        o_out = valid_old["Outseam - Dài quần ngoài"]
        n_out = valid_new["Outseam - Dài quần ngoài"]
        len_pct = (n_out / o_out - 1) * 100
    elif has_in:
        o_in = valid_old["Inseam - Dài quần trong"]
        n_in = valid_new["Inseam - Dài quần trong"]
        if rise_names:
            avg_rise_old = sum(valid_old[r] for r in rise_names) / len(rise_names)
            avg_rise_new = sum(valid_new[r] for r in rise_names) / len(rise_names)
            len_pct = ((avg_rise_new + n_in) / (avg_rise_old + o_in) - 1) * 100
        else:
            len_pct = (n_in / o_in - 1) * 100
    else:
        len_pct = group_active_avg("length")

    # 2. Tính tỷ lệ thay đổi Chiều rộng CÓ TRỌNG SỐ
    active_widths = [n for n in grouped_valid.get("width", []) if abs(valid_changes[n]) > 0.01]
    if active_widths:
        w_map = width_weights(active_widths)
        wid_pct = sum(valid_changes[n] * w_map[n] for n in active_widths)
    else:
        wid_pct = 0.0

    rise_pct = group_active_avg("rise")

    # 3. Công thức thích ứng 2 chế độ (Bước 1: Tính ĐM mới trên nền Khổ cũ & Độ co cũ)
    if abs(len_pct) > 25.0:
        len_weight = 0.85
        harmony_factor = 1.00
    else:
        len_weight = 0.65
        harmony_factor = 0.75

    raw_pct = (len_pct * len_weight) + wid_pct + (rise_pct * 0.5) + extra_detail_pct
    final_pct = raw_pct * harmony_factor
    pred_dm_old_width = old_dm * (1 + final_pct / 100)

    summary_df = pd.DataFrame([{
        "ĐM cũ (yd/pcs)": round(old_dm, 4),
        "Số POM so sánh": len(valid_changes),
        "Biến động POM (%)": round(final_pct, 2),
        "ĐM mới [Khổ cũ] (yd/pcs)": round(pred_dm_old_width, 4),
    }])

    return summary_df, pd.DataFrame(detail_rows)

# ==============================================================================
# 5. GIAO DIỆN STREAMLIT
# ==============================================================================
st.title("🧵 APP DỰ ĐOÁN ĐỊNH MỨC VẢI (FULL POM & QUY ĐỔI KHỔ / ĐỘ CO)")
st.caption("Đối chiếu BOM lọc Vải chính ➔ Chuẩn hóa cách đo POM ➔ Tính ĐM trên khổ cũ ➔ Quy đổi sang khổ vải & độ co mới.")

if "reset_counter" not in st.session_state:
    st.session_state.reset_counter = 0

rc = st.session_state.reset_counter

col_title_up, col_size_sel, col_btn_reset = st.columns([2.8, 1.2, 0.8])
with col_title_up:
    st.subheader("1. UPLOAD FILE TECHPACK & CHỌN CỘT SIZE")
with col_size_sel:
    size_col_idx = st.number_input("Vị trí cột Base Size (0 = cột số đầu tiên)", min_value=0, max_value=15, value=0, step=1)
with col_btn_reset:
    st.write("")
    if st.button("🔄 Làm mới dữ liệu", use_container_width=True):
        st.session_state.reset_counter += 1
        st.rerun()

up1, up2 = st.columns(2)
with up1:
    tp_old_file = st.file_uploader("📄 Upload Techpack Mã cũ", type=["xlsx", "xls", "pdf"], key=f"tp_old_{rc}")
with up2:
    tp_new_file = st.file_uploader("📄 Upload Techpack Mã mới", type=["xlsx", "xls", "pdf"], key=f"tp_new_{rc}")

auto_old_code = tp_old_file.name.rsplit(".", 1)[0] if tp_old_file else "MA-CU-01"
auto_new_code = tp_new_file.name.rsplit(".", 1)[0] if tp_new_file else "MA-MOI-02"

st.subheader("2. THÔNG TIN MÃ HÀNG, KHỔ VẢI & ĐỘ CO")
col_cat, col_old, col_new, col_dm = st.columns([1.2, 1, 1, 1])
with col_cat:
    category = st.selectbox("Chủng loại sản phẩm", options=list(CATEGORIES.keys()), index=0)
with col_old:
    old_code = st.text_input("Mã hàng cũ", value=auto_old_code, key=f"old_code_{auto_old_code}")
with col_new:
    new_code = st.text_input("Mã hàng mới", value=auto_new_code, key=f"new_code_{auto_new_code}")
with col_dm:
    old_dm = st.number_input("ĐM cũ (yd/pcs)", min_value=0.0001, value=0.8250, step=0.001, format="%.4f")

col_w1, col_w2, col_s1, col_s2 = st.columns(4)
with col_w1:
    old_width = st.number_input("Khổ vải cũ (inch)", min_value=10.0, max_value=150.0, value=58.0, step=0.5, format="%.1f")
with col_w2:
    new_width = st.number_input("Khổ vải mới (inch)", min_value=10.0, max_value=150.0, value=58.0, step=0.5, format="%.1f")
with col_s1:
    old_shrink = st.number_input("Độ co vải cũ (%)", min_value=0.0, max_value=30.0, value=2.0, step=0.5, format="%.1f")
with col_s2:
    new_shrink = st.number_input("Độ co vải mới (%)", min_value=0.0, max_value=30.0, value=2.0, step=0.5, format="%.1f")

cfg = CATEGORIES[category]

old_tp_data, old_debug = match_tp_to_full_poms(tp_old_file, cfg["specs"], size_col_idx) if tp_old_file else ({}, [])
new_tp_data, new_debug = match_tp_to_full_poms(tp_new_file, cfg["specs"], size_col_idx) if tp_new_file else ({}, [])

if tp_old_file or tp_new_file:
    st.success(f"✅ Đã nhận diện **{len(old_tp_data)}** POM từ **{old_code}** và **{len(new_tp_data)}** POM từ **{new_code}**.")
    with st.expander("🔍 BẤM VÀO ĐÂY ĐỂ XEM DỮ LIỆU GỐC ĐỌC ĐƯỢC TỪ FILE TECHPACK", expanded=False):
        d1, d2 = st.columns(2)
        with d1:
            st.markdown(f"**Dữ liệu gốc TP Mã cũ ({old_code}):**")
            st.dataframe(pd.DataFrame(old_debug), use_container_width=True, hide_index=True)
        with d2:
            st.markdown(f"**Dữ liệu gốc TP Mã mới ({new_code}):**")
            st.dataframe(pd.DataFrame(new_debug), use_container_width=True, hide_index=True)

st.subheader("3. BẢNG THÔNG SỐ FULL POM (KIỂM TRA VẢI CHÍNH THEO BOM & CHUẨN ĐO)")
st.caption("Lưu ý: Bỏ tích cột 'Vải chính?' đối với các chi tiết dùng vải lót (Pocketing/Lining) hoặc bo Rib trên BOM. Quy chuẩn cách đo (ví dụ: cộng thêm bản lưng nếu đo dưới lưng) trước khi tính.")

has_uploaded = bool(tp_old_file or tp_new_file)
init_rows = []
for spec_name, grp in cfg["specs"]:
    if has_uploaded:
        o_val = float(old_tp_data.get(spec_name, 0.0))
        n_val = float(new_tp_data.get(spec_name, 0.0))
    else:
        o_val, n_val = cfg["defaults"].get(spec_name, (0.0, 0.0))

    default_is_shell = not any(kw in spec_name.lower() for kw in NON_SHELL_KEYWORDS)

    init_rows.append({
        "Vải chính?": default_is_shell,
        "Nhóm": grp,
        "Tên POM": spec_name,
        "Mã cũ": o_val,
        "Mã mới": n_val,
    })

old_fname = f"{tp_old_file.name}_{tp_old_file.size}" if tp_old_file else "no_old"
new_fname = f"{tp_new_file.name}_{tp_new_file.size}" if tp_new_file else "no_new"

edited_df = st.data_editor(
    pd.DataFrame(init_rows),
    num_rows="dynamic",
    use_container_width=True,
    height=500,
    column_config={
        "Vải chính?": st.column_config.CheckboxColumn("Vải chính?", help="Tích chọn nếu chi tiết làm bằng Vải chính (Shell). Bỏ tích nếu là Vải lót/Phối/Bo Rib."),
        "Nhóm": st.column_config.SelectboxColumn("Nhóm", options=["length", "width", "rise", "detail"], required=True),
        "Tên POM": st.column_config.TextColumn("Tên POM (Chi tiết đo)", width="large"),
        "Mã cũ": st.column_config.NumberColumn("Mã cũ", min_value=0.0, format="%.3f"),
        "Mã mới": st.column_config.NumberColumn("Mã mới", min_value=0.0, format="%.3f"),
    },
    key=f"pom_table_{category}_{old_fname}_{new_fname}_{size_col_idx}_{rc}",
)

if st.button("🚀 Tính toán & Dự đoán định mức mới", type="primary"):
    try:
        # BƯỚC 1: Tính định mức mới dựa trên biến động POM (giữ nguyên khổ vải cũ & độ co cũ)
        df_summary, df_details = calculate_full_poms(edited_df, cfg["specs"], old_dm)
        res = df_summary.to_dict(orient="records")[0]
        dm_old_width = res["ĐM mới [Khổ cũ] (yd/pcs)"]

        # BƯỚC 2: Quy đổi sang Khổ vải mới & Độ co mới
        shrink_factor = (1 - old_shrink / 100.0) / (1 - new_shrink / 100.0)
        final_pred_dm = dm_old_width * (old_width / new_width) * shrink_factor
        diff_dm = final_pred_dm - old_dm

        st.subheader("4. KẾT QUẢ DỰ ĐOÁN ĐỊNH MỨC MỚI (2 BƯỚC)")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("ĐM cũ (yd/pcs)", f"{old_dm:.4f}")
        m2.metric("Bước 1: ĐM mới [Khổ cũ]", f"{dm_old_width:.4f}", delta=f"{res['Biến động POM (%)']:+.2f}% POM")
        m3.metric("Bước 2: ĐM dự đoán cuối cùng", f"{final_pred_dm:.4f}", delta=f"{diff_dm:+.4f} yd")
        m4.metric("Số POM Vải chính so sánh", f"{int(res['Số POM so sánh'])} thông số")

        df_summary["Khổ cũ -> Mới"] = f"{old_width}\" -> {new_width}\""
        df_summary["Độ co cũ -> Mới"] = f"{old_shrink}% -> {new_shrink}%"
        df_summary["ĐM dự đoán cuối cùng (yd/pcs)"] = round(final_pred_dm, 4)
        df_summary["Chênh lệch tổng (yd/pcs)"] = round(diff_dm, 4)

        st.subheader("5. BẢNG ĐỐI CHIẾU FULL POM")
        filter_opt = st.radio(
            "Hiển thị dòng POM:",
            options=[
                "Tất cả POM",
                "Chỉ hiện các POM Vải chính đưa vào so sánh (> 0 cả 2 bên)",
                "Chỉ hiện các POM có nhập dữ liệu (> 0 ít nhất 1 bên)",
            ],
            horizontal=True,
        )
        if filter_opt == "Chỉ hiện các POM Vải chính đưa vào so sánh (> 0 cả 2 bên)":
            df_show = df_details[(df_details["Vải chính?"]) & (df_details["Mã cũ"] > 0) & (df_details["Mã mới"] > 0)]
        elif filter_opt == "Chỉ hiện các POM có nhập dữ liệu (> 0 ít nhất 1 bên)":
            df_show = df_details[(df_details["Mã cũ"] > 0) | (df_details["Mã mới"] > 0)]
        else:
            df_show = df_details

        st.dataframe(df_show, use_container_width=True, hide_index=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_summary.to_excel(writer, index=False, sheet_name="Du_doan_Dinh_muc")
            df_details.to_excel(writer, index=False, sheet_name="Doi_chieu_Full_POM")
        st.download_button(
            label="📥 Tải báo cáo đối chiếu & định mức (.xlsx)",
            data=output.getvalue(),
            file_name=f"Dinh_muc_{old_code}_vs_{new_code}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        st.error(f"Lỗi tính toán: {e}")
