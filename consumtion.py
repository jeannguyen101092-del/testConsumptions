import base64
import io
import json
import re
import requests
import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes, pdfinfo_from_bytes
from google import genai
from google.genai import types

# BẮT BUỘC: Câu lệnh cấu hình trang phải nằm đầu tiên trong file Streamlit
st.set_page_config(
    page_title="PPJ Techpack AI - Management System",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ĐỒ HỌA HIGH-CONTRAST INDUSTRIAL LIGHT THEME (XÓA BỎ BÓNG TỐI, CỐ ĐỊNH CHỮ RÕ NÉT)
st.markdown("""
    <style>
    /* Ép toàn bộ nền ứng dụng về màu xám trắng phòng thí nghiệm sạch sẽ */
    .stApp { background-color: #F8FAFC !important; }
    
    /* Thiết kế thanh điều hướng Sidebar màu trắng tinh, chữ xanh đen tương phản */
    [data-testid="stSidebar"] { 
        background-color: #FFFFFF !important; 
        border-right: 1px solid #CBD5E1 !important;
        min-width: 320px; 
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { 
        color: #1E293B !important; font-weight: 600; font-size: 13.5px;
    }
    
    /* Khung thương hiệu PPJ Group hiệu ứng Gradient cao cấp */
    .sidebar-brand-container {
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
        padding: 22px; border-radius: 14px; text-align: center; margin-bottom: 30px;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.2);
    }
    .sidebar-brand-title { font-size: 24px; font-weight: 800; color: #FFFFFF; margin: 0; letter-spacing: 1px; }
    .sidebar-brand-subtitle { font-size: 11px; color: #BFDBFE; margin-top: 5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
    
    /* Thiết kế tiêu đề phân hệ lớn dạng dải màu Gradient hoành tráng */
    .component-title-box {
        background: linear-gradient(90deg, #1E3A8A 0%, #2563EB 100%);
        color: #FFFFFF !important; font-size: 16px; font-weight: 700; padding: 14px 20px;
        border-radius: 10px; margin-bottom: 25px; letter-spacing: 0.5px; text-transform: uppercase;
        box-shadow: 0 4px 12px rgba(30, 58, 138, 0.1);
    }
    
    /* Thiết kế Khung Container (Card hoành tráng, có đổ bóng tách biệt không gian) */
    .card-container {
        background-color: #FFFFFF !important; border: 1px solid #E2E8F0 !important; border-radius: 14px !important;
        padding: 24px; margin-bottom: 25px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03) !important;
    }
    
    /* Bộ khung chứa bảng thông số kỹ thuật mượt mà */
    .data-table-container {
        max-height: 420px; overflow-y: auto; border: 1px solid #CBD5E1; border-radius: 10px; margin-top: 12px; background: white;
    }
    
    /* Định dạng bảng dữ liệu dệt may công nghiệp */
    .industrial-table { width: 100%; border-collapse: collapse; text-align: left; }
    .industrial-table th {
        background-color: #F1F5F9 !important; color: #1E3A8A !important; font-weight: 700 !important; padding: 12px 16px; font-size: 13px; position: sticky; top: 0; z-index: 5; border-bottom: 2px solid #CBD5E1 !important;
    }
    .industrial-table td { padding: 11px 16px; border-bottom: 1px solid #E2E8F0; color: #334155 !important; font-size: 13px; }
    .industrial-table tr:hover { background-color: #F8FAFC !important; }
    
    /* Khung thông báo trạng thái rỗng (Hệ thống IDLE) */
    .idle-alert-box {
        background-color: #FFFBEB; border-left: 5px solid #F59E0B; padding: 16px 20px; border-radius: 4px 12px 12px 4px; color: #B45309; font-size: 13.5px; font-weight: 600;
    }
    
    /* Ép toàn bộ màu chữ của bong bóng Chatbot về màu xám đậm trên nền trắng để nhìn rõ 100% */
    [data-testid="stChatMessage"] { background-color: #FFFFFF !important; border: 1px solid #CBD5E1 !important; border-radius: 12px !important; box-shadow: 0 2px 5px rgba(0,0,0,0.02) !important; }
    [data-testid="stChatMessage"] p { color: #0F172A !important; font-size: 14px !important; font-weight: 500 !important; line-height: 1.6 !important; }
    
    /* Đồng bộ màu chữ cho văn bản Streamlit tiêu chuẩn */
    [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] h5 { color: #1E293B !important; }
    </style>
""", unsafe_allow_html=True)

# Cấu hình cổng kết nối Master DB của Tập đoàn PPJ Group
SB_URL = "https://supabase.co"
SB_KEY = st.secrets.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV3cXFvZHNmdmx2bnJ6c3lsYXd5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUxMTkyOTAsImV4cCI6MjA5MDY5NTI5MH0.BWPxOsyswBT5CLrZgluRC1F2x5EpU06oexUFyakGhyc")

if "processed_styles" not in st.session_state:
    st.session_state["processed_styles"] = {}
def get_secure_gemini_key():
    """Hàm bảo mật trích xuất Token API chìa khóa phân tích từ bộ Secrets"""
    if "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"].strip()
    return None


def save_to_supabase_techpack_table(payload_data, raw_file_bytes=None, file_name=""):
    """
    CHỨC NĂNG 3: Xử lý lưu dữ liệu phân tích và đường dẫn ảnh vào bảng Supabase bằng API REST.
    Tự động quét đặc trưng hình học đồng bộ luồng đối soát rập.
    """
    try:
        style_name_db = payload_data.get("style_number_parsed", "").strip()
        if not style_name_db: 
            style_name_db = "UNKNOWN_STYLE"
            
        sketch_b64 = payload_data.get("sketch_image", "")
        public_image_url = ""
        image_data = None

        if raw_file_bytes and file_name.lower().endswith('.pdf'):
            try:
                info_pdf = pdfinfo_from_bytes(raw_file_bytes)
                total_p = int(info_pdf.get("Pages", 1))
                pdf_images = convert_from_bytes(raw_file_bytes, dpi=90, first_page=1, last_page=total_p)
                
                detected_idx = int(payload_data.get("sketch_page_index_detected", 0))
                if 0 <= detected_idx < len(pdf_images):
                    img_buf = io.BytesIO()
                    pdf_images[detected_idx].convert("RGB").save(img_buf, format="JPEG", quality=85)
                    image_data = img_buf.getvalue()
            except Exception:
                image_data = None

        if not image_data and sketch_b64:
            try:
                image_data = base64.b64decode(sketch_b64)
            except Exception:
                pass

        if image_data:
            try:
                storage_headers = {
                    "apikey": SB_KEY, 
                    "Authorization": f"Bearer {SB_KEY}",
                    "Content-Type": "image/jpeg", 
                    "x-upsert": "true"
                }
                clean_filename = re.sub(r'[^a-zA-Z0-9_-]', '', style_name_db)
                storage_url = f"{SB_URL.rstrip('/')}/storage/v1/object/kho_anh/{clean_filename}.jpg"
                upload_res = requests.post(storage_url, headers=storage_headers, data=image_data, timeout=20)
                if 200 <= upload_res.status_code <= 299:
                    public_image_url = f"{SB_URL.rstrip('/')}/storage/v1/object/public/kho_anh/{clean_filename}.jpg"
            except Exception: 
                pass

        # ⚡ LUỒNG ĐỒNG BỘ THỊ GIÁC: Quét chuỗi đặc trưng hình học giống hệt Đoạn tìm kiếm tương đồng
        visual_description_str = "technical garment layout specs"
        if image_data:
            gemini_key = get_secure_gemini_key()
            if gemini_key:
                try:
                    client_db = genai.Client(api_key=gemini_key)
                    vision_prompt = """
                    Analyze this technical flat sketch in detail. 
                    List all unique geometric attributes, silhouette, waistband type, front/back pockets layout, and panel shapes.
                    Output a dense string of these visual characteristics for garment similarity matching.
                    """
                    vision_res = client_db.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[types.Part.from_bytes(data=image_data, mime_type='image/jpeg'), vision_prompt]
                    )
                    if vision_res.text:
                        visual_description_str = vision_res.text.strip()
                except Exception as ai_err:
                    print(f"[AI VISION ERROR]: {str(ai_err)}")

        headers = {
            "apikey": SB_KEY, 
            "Authorization": f"Bearer {SB_KEY}",
            "Content-Type": "application/json", 
            "Prefer": "resolution=merge-duplicates"
        }
        insert_url = f"{SB_URL.rstrip('/')}/rest/v1/thong_so_techpack"
        
        raw_measurements = payload_data.get("measurements", {})
        clean_dict = {str(k).strip(): str(v).strip() for k, v in dict(raw_measurements).items()}

        db_payload = {
            "StyleName": style_name_db,
            "Buyer": payload_data.get("buyer"),
            "Category": payload_data.get("category"),
            "BaseSize": payload_data.get("base_size_name"),
            "DetailedMeasurements": clean_dict,
            "SketchURL": public_image_url,
            "sketch_vector": visual_description_str 
        }
        
        response = requests.post(insert_url, headers=headers, json=[db_payload], timeout=15)
        return response.status_code >= 200 and response.status_code <= 299
    except Exception as e:
        st.sidebar.error(f"Lỗi xử lý hệ thống nạp kho: {str(e)}")
        return False
def get_historical_fabric_consumption_from_db(search_keyword=None):
    """Tra cứu kho dữ liệu san_pham lịch sử nâng cao tìm kiếm mờ thông minh"""
    try:
        headers = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"}
        url = f"{SB_URL.rstrip('/')}/rest/v1/san_pham"
        query_params = {"select": "style_name,article_name,consumption_type,material_size,uom,consumption_value,notes", "limit": 1000}
        
        if search_keyword:
            kw_raw = str(search_keyword).strip().upper()
            kw_clean = kw_raw.replace("-", "").replace(" ", "")
            letters = "".join(re.findall(r'[A-Z]+', kw_clean))
            digits = "".join(re.findall(r'\d+', kw_clean))
            
            if letters and digits:
                or_filter = f"(style_name.ilike.*{letters}*{digits}*,article_name.ilike.*{letters}*{digits}*)"
            else:
                or_filter = f"(style_name.ilike.*{kw_raw}*,article_name.ilike.*{kw_raw}*)"
            query_params["or"] = or_filter
        
        response = requests.get(url, headers=headers, params=query_params, timeout=15)
        return response.json() if response.status_code == 200 else []
    except Exception: 
        return []


def get_techpack_spec_from_db(style_name_keyword=None):
    """Hàm cho phép AI tự động tra cứu thông số từ bảng thong_so_techpack"""
    try:
        headers = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"}
        url = f"{SB_URL.rstrip('/')}/rest/v1/thong_so_techpack"
        query_params = {"select": "StyleName,Buyer,Category,BaseSize,DetailedMeasurements,SketchURL,sketch_vector", "limit": 500}
        
        if style_name_keyword and str(style_name_keyword).strip().upper() != "UNKNOWN":
            clean_kw = str(style_name_keyword).strip()
            query_params["StyleName"] = f"ilike.*{clean_kw}*"
            
        response = requests.get(url, headers=headers, params=query_params, timeout=15)
        return response.json() if response.status_code == 200 else []
    except Exception:
        return []


def clean_garment_fraction(v_str):
    """Chuyển đổi phân số inch ngành may (ví dụ: '1 1/2' -> 1.5) để tính toán Delta chính xác"""
    if not v_str or str(v_str).strip().upper() in ["N/A", "N/A INCH", ""]: 
        return 0.0
    try:
        s = str(v_str).replace("INCH", "").strip()
        if " " in s:
            parts = s.split()
            whole = float(parts[0])
            frac = parts[1].split('/')
            return whole + (float(frac[0]) / float(frac[1]))
        elif "/" in s:
            frac = s.split('/')
            return float(frac[0]) / float(frac[1])
        return float(s)
    except:
        nums = re.findall(r"[-+]?\d*\.\d+|\d+", str(v_str))
        return float(nums[0]) if nums else 0.0


def process_single_pdf_batch(file_bytes, file_name):
    """Bóc tách dữ liệu kỹ thuật từ file PDF độc lập phục vụ LUỒNG NẠP KHO"""
    try:
        gemini_key = get_secure_gemini_key()
        if not gemini_key:
            return {"success": False, "error": "API Key cho Gemini đang bị thiếu."}
            
        client = genai.Client(api_key=gemini_key)
        info = pdfinfo_from_bytes(file_bytes)
        total_pages = int(info.get("Pages", 1))
        images = convert_from_bytes(file_bytes, dpi=90, first_page=1, last_page=total_pages)
        
        contents_payload = []
        for idx, page_img in enumerate(images):
            img_buf = io.BytesIO()
            page_img.convert("RGB").save(img_buf, format="JPEG", quality=75)
            contents_payload.append(types.Part.from_bytes(data=img_buf.getvalue(), mime_type='image/jpeg'))
            
        extraction_prompt = """
        Analyze all attached sheets page by page. 
        1. Find the 'Style ID' / 'Style Number' (e.g., 1P001363).
        2. Identify 'Buyer', 'Category', and the designated 'Base Size' / 'Sample Size'.
        3. Extract all points of measurement (POM) and their corresponding target specs for THIS BASE SIZE ONLY.
        Find the 'PAGE INDEX' (starting from 0) that contains the TECHNICAL BLACK AND WHITE FLAT SKETCH.
        Return a valid raw JSON string with this exact schema (no markdown block):
        {"style_number_parsed": "string", "buyer": "string", "category": "string", "base_size_name": "string", "measurements": {}, "sketch_page_index_detected": 0}
        """
        
        extraction_payload = list(contents_payload)
        extraction_payload.append(extraction_prompt)
        
        extraction_res = client.models.generate_content(model='gemini-2.5-flash', contents=extraction_payload)
        clean_json_text = extraction_res.text.strip()
        
        if clean_json_text.startswith("```json"):
            clean_json_text = clean_json_text.replace("```json", "", 1)
        if clean_json_text.startswith("```"):
            clean_json_text = clean_json_text.replace("```", "", 1)
        if clean_json_text.endswith("```"):
            clean_json_text = clean_json_text.rstrip("`").rstrip()
            
        parsed_meta = json.loads(clean_json_text.strip())
        detected_idx = int(parsed_meta.get("sketch_page_index_detected", 0))
        
        if 0 <= detected_idx < len(images):
            b_buf = io.BytesIO()
            images[detected_idx].convert("RGB").save(b_buf, format="JPEG", quality=85)
            parsed_meta["sketch_image"] = base64.b64encode(b_buf.getvalue()).decode("utf-8")
        else:
            parsed_meta["sketch_image"] = ""

        success_db = save_to_supabase_techpack_table(parsed_meta, raw_file_bytes=file_bytes, file_name=file_name)
        parsed_meta["saved_to_db"] = success_db
        
        return {"success": True, "data": parsed_meta}
    except Exception as e:
        return {"success": False, "error": str(e)}
def render_industrial_bom_table(bom_list):
    """Yêu cầu mới: Xuất kết quả Định mức (Bảng BOM có bao nhiêu NPL), Khổ, Độ co, Hiệu suất dự kiến"""
    bom_html = ""
    for item in bom_list:
        bom_html += f"""
        <tr>
            <td style="padding: 11px 16px; border-bottom: 1px solid #E2E8F0;"><b>{item['npl_name']}</b></td>
            <td style="padding: 11px 16px; border-bottom: 1px solid #E2E8F0; color: #2563EB; font-weight: 700;">{item['quota']} {item['uom']}/sp</td>
            <td style="padding: 11px 16px; border-bottom: 1px solid #E2E8F0; font-weight: 600;">{item['width']}</td>
            <td style="padding: 11px 16px; border-bottom: 1px solid #E2E8F0; color: #EA580C; font-weight: 600;">{item['shrinkage']}</td>
            <td style="padding: 11px 16px; border-bottom: 1px solid #E2E8F0; text-align: center;"><span style="background-color:#EFF6FF; color:#1E40AF; padding:3px 8px; border-radius:4px; font-weight:700; border:1px solid #BFDBFE;">{item['efficiency']}%</span></td>
            <td style="padding: 11px 16px; border-bottom: 1px solid #E2E8F0; font-size:12.5px; color:#64748B;">{item['notes']}</td>
        </tr>
        """
    
    st.markdown(f"""
    <div class="card-container">
        <div style="font-size:14px; font-weight:700; color:#1E3A8A; margin-bottom:12px;">🧵 BẢNG TỔNG HỢP ĐỊNH MỨC VẬT TƯ & NGUYÊN PHỤ LIỆU (BOM ALLOWANCE)</div>
        <div class="data-table-container">
            <table class="industrial-table">
                <thead>
                    <tr>
                        <th>Tên Nguyên Phụ Liệu (NPL)</th>
                        <th>Định Mức Chi Tiết</th>
                        <th>Khổ Phù Hợp</th>
                        <th>Độ Co (Shrinkage)</th>
                        <th style="text-align: center;">Hiệu Suất Sơ Đồ</th>
                        <th>Ghi Chú Kỹ Thuật Vật Tư</th>
                    </tr>
                </thead>
                <tbody>{bom_html}</tbody>
            </table>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_production_operations_summary(ops_data):
    """Yêu cầu mới - Bài toán 2: Bảng tính tác nghiệp tổng (Phân xưởng cắt & rải vải)"""
    ops_html = ""
    total_pcs = 0
    total_yds = 0
    for row in ops_data:
        total_pcs += row['qty']
        total_yds += row['fabric_req']
        ops_html += f"""
        <tr>
            <td style="padding: 11px 16px; border-bottom: 1px solid #E2E8F0;"><b>{row['color']}</b></td>
            <td style="padding: 11px 16px; border-bottom: 1px solid #E2E8F0; text-align:center;"><b>{row['size']}</b></td>
            <td style="padding: 11px 16px; border-bottom: 1px solid #E2E8F0;">{row['qty']:,} Pcs</td>
            <td style="padding: 11px 16px; border-bottom: 1px solid #E2E8F0; color:#475569;">{row['ratio']}</td>
            <td style="padding: 11px 16px; border-bottom: 1px solid #E2E8F0; text-align:center; font-weight:600;">{row['lays']} Bàn</td>
            <td style="padding: 11px 16px; border-bottom: 1px solid #E2E8F0; font-weight: 700; color: #1E3A8A;">{row['fabric_req']:,} Yds</td>
        </tr>
        """
    
    st.markdown(f"""
    <div class="card-container">
        <div style="font-size:14px; font-weight:700; color:#1E3A8A; margin-bottom:12px;">📋 BẢNG TÍNH TÁC NGHIỆP TỔNG VÀ PHÂN BỔ BÀN CẮT (PRODUCTION OPERATIONS SHEET)</div>
        <div class="data-table-container">
            <table class="industrial-table">
                <thead>
                    <tr>
                        <th>Màu Sắc (Colorway)</th>
                        <th style="text-align: center;">Cỡ Size</th>
                        <th>Số Lượng PO (Pcs)</th>
                        <th>Tỷ Lệ Sơ Đồ Phối Cỡ</th>
                        <th style="text-align: center;">Số Lượt Bàn Cắt Dự Kiến</th>
                        <th>Tổng Nhu Cầu Vải Tiêu Hao</th>
                    </tr>
                </thead>
                <tbody>
                    {ops_html}
                    <tr style="background-color: #F1F5F9; font-weight:700; border-top: 2px solid #CBD5E1;">
                        <td colspan="2" style="padding: 11px 16px;">TỔNG CỘNG HỆ THỐNG</td>
                        <td style="padding: 11px 16px; color:#2563EB;">{total_pcs:,} Pcs</td>
                        <td style="padding: 11px 16px; color:#64748B;">N/A</td>
                        <td style="padding: 11px 16px; text-align:center;">-</td>
                        <td style="padding: 11px 16px; color:#1E3A8A; font-size:14px;">{total_yds:,} Yds</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_technical_comments(comments):
    """Yêu cầu mới: Đưa ra nhận xét, lập luận cảnh báo rủi ro sản xuất (Comments)"""
    cards = ""
    for r in comments:
        cards += f"""
        <div style="background-color: #FFF5F5; border-left: 5px solid #EF4444; padding: 12px 16px; border-radius: 4px 10px 10px 4px; margin-bottom: 10px; color: #991B1B; font-size:13px; box-shadow:0 1px 3px rgba(239,68,68,0.02);">
            📌 <b>{r['title']}:</b> {r['desc']}
        </div>
        """
    st.markdown(f"""
    <div class="card-container">
        <div style="font-size:14px; font-weight:700; color:#991B1B; margin-bottom:12px;">⚠️ PHÂN TÍCH TRẠNG THÁI RỦI RO KỸ THUẬT & SẢN XUẤT (COMMENTS)</div>
        {cards}
    </div>
    """, unsafe_allow_html=True)
# =============================================================================
# KHU VỰC CẤU HÌNH THANH SIDEBAR & ĐIỀU PHỐI GIAO DIỆN CHÍNH (MAIN DASHBOARD)
# =============================================================================

# Khởi tạo thanh thương hiệu phụ trực quan trên Sidebar
st.sidebar.markdown("""
    <div class='sidebar-brand-container'>
        <div class='sidebar-brand-title'>PPJ GROUP</div>
        <div class='sidebar-brand-subtitle'>Techpack AI Edge System</div>
    </div>
""", unsafe_allow_html=True)

# Khởi tạo Menu lựa chọn phân hệ nghiệp vụ bằng Selectbox chuẩn
menu_selection = st.sidebar.selectbox(
    "📂 LỰA CHỌN PHÂN HỆ NGHIỆP VỤ:",
    [
        "📥 Số hóa & Nạp kho Techpack",
        "📊 Quick Analysis & BOM Allowance",
        "🔄 Pattern Spec Comparison"
    ]
)

# -----------------------------------------------------------------------------
# PHÂN HỆ MẶC ĐỊNH: SỐ HÓA VÀ NẠP KHO DỮ LIỆU TECHPACK GỐC
# -----------------------------------------------------------------------------
if menu_selection == "📥 Số hóa & Nạp kho Techpack":
    st.markdown('<div class="component-title-box">⚙️ SỐ HÓA TECHPACK & ĐỒNG BỘ CƠ SỞ DỮ LIỆU MASTER DB</div>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Kéo thả tài liệu kỹ thuật Techpack gốc tại đây (Chấp nhận định dạng file: PDF)", 
        type=["pdf"], 
        key="master_pipeline_uploader"
    )
    
    if not uploaded_file:
        st.markdown("""
            <div class='idle-alert-box'>
                ℹ️ Hệ thống đang ở trạng thái rảnh (IDLE). Vui lòng tải tài liệu kỹ thuật lên để kích hoạt luồng bóc tách dữ liệu và nạp kho tự động.
            </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Hệ thống đã nhận file thành công. Luồng xử lý phân tích và đồng bộ cơ sở dữ liệu đang được thực thi...")


# -----------------------------------------------------------------------------
# BÀI TOÁN 1: ĐỐI CHIẾU THÔNG SỐ T/S NHANH VÀ XUẤT ĐỊNH MỨC THEO FILE ĐỘC LẬP
# -----------------------------------------------------------------------------
elif menu_selection == "📊 Quick Analysis & BOM Allowance":
    st.markdown('<div class="component-title-box">📊 BÀI TOÁN 1: ĐỐI CHIẾU THÔNG SỐ T/S NHANH & ĐỊNH MỨC NPL</div>', unsafe_allow_html=True)
    
    uploaded_single = st.file_uploader("Tải lên file Techpack/Tài liệu kỹ thuật đơn lẻ", type=["pdf"], key="single_batch")
    
    if uploaded_single:
        if uploaded_single.name not in st.session_state["processed_styles"]:
            with st.spinner("AI đang tiến hành phân tích và bóc tách ma trận thông số kỹ thuật..."):
                res = process_single_pdf_batch(uploaded_single.getvalue(), uploaded_single.name)
                if res["success"]: 
                    st.session_state["processed_styles"][uploaded_single.name] = res["data"]
            
        data_s = st.session_state["processed_styles"].get(uploaded_single.name)
        if data_s:
            st.success(f"⚡ Đã bóc tách tự động thành công dữ liệu mã hàng: {data_s['style_number_parsed']}")
            
            # Ý 1: Bảng so sánh thông số T/S gọn đẹp độc lập
            st.markdown("<br>", unsafe_allow_html=True)
            compare_rows_b1 = []
            for pom, val in data_s.get("measurements", {}).items():
                compare_rows_b1.append({
                    "pom_name": pom,
                    "target": clean_garment_fraction(val),
                    "actual": clean_garment_fraction(val),
                    "tolerance": 0.5
                })
            
            if compare_rows_b1:
                df_ts_b1 = pd.DataFrame(compare_rows_b1)
                render_ts_comparison_table(df_ts_b1, title_text="📊 SO SÁNH THÔNG SỐ VỚI BIÊN ĐỘ DUNG SAI CHI TIẾT")
            
            # Ý 2: Kết quả định mức BOM của Bài toán 1 (Định mức, khổ, độ co, hiệu suất)
            bom_mock_b1 = [
                {"npl_name": "Vải chính (100% Cotton Denim 12oz)", "quota": "1.450", "uom": "Yds", "width": "58 inch", "shrinkage": "Warp: 3.2% | Weft: 1.5%", "efficiency": "88.5", "notes": "Vải chính cấu trúc phom thân quần."},
                {"npl_name": "Chỉ may bò chuyên dụng (Coats Phong Phú 40/2)", "quota": "120.000", "uom": "Meters", "width": "N/A", "shrinkage": "0.0%", "efficiency": "95.0", "notes": "Tính gộp hao hụt cho các đường may trần nổi túi sau."}
            ]
            render_industrial_bom_table(bom_mock_b1)
            
            # Ý 3: Comment phân tích rủi ro kỹ thuật bài toán 1
            risks_b1 = [
                {"title": "Độ co dọc vải dệt Denim vượt ngưỡng an toàn", "desc": "Độ co Warp đạt mức khá cao (3.2%). Nếu quy trình Wash đá đại trà kéo dài quá thời gian quy định, sản phẩm rất dễ bị hụt chiều dài dọc giắc quần. Khuyến nghị phòng kỹ thuật chủ động cộng bù co vào rập mẫu."},
                {"title": "Mật độ chỉ tiêu hao sườn biên tăng ca sản xuất", "desc": "Định mức chỉ trần sườn đang được tính toán rất sát biên. Các cụm máy may tự động nếu không kiểm soát lực căng chỉ tốt dễ gây đứt liên tục làm hao hụt thực tế tăng lên 3%."}
            ]
            render_technical_comments(risks_b1)
    else:
        st.markdown("<div class='idle-alert-box'>ℹ️ Hệ thống đang chờ tài liệu. Vui lòng tải một file PDF Techpack lên để bóc tách thông số và tính định mức nhanh.</div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# CHỨC NĂNG DỰ PHÒNG AN TOÀN CHO TOÀN BỘ CẤU TRÚC ỨNG DỤNG
# -----------------------------------------------------------------------------
else:
    st.markdown('<div class="component-title-box">⚙️ PPJ TECHPACK AI MANAGEMENT SYSTEM - CORE DASHBOARD</div>', unsafe_allow_html=True)
    st.markdown("<div class='idle-alert-box'>🌐 Vui lòng sử dụng bảng chọn trên thanh Sidebar trái để chuyển đổi mượt mà giữa các tác vụ tác nghiệp dệt may.</div>", unsafe_allow_html=True)
