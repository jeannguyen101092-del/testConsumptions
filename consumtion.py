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
    
    /* Lưới thông tin Metadata bọc khung xám nhẹ */
    .metric-grid-box {
        display: flex; gap: 25px; background: #F8FAFC; padding: 14px 20px; border-radius: 10px; border: 1px solid #E2E8F0; margin-bottom: 20px;
    }
    .metric-label { font-size: 11px; font-weight: 700; color: #64748B; margin: 0; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-value { font-size: 14px; font-weight: 700; color: #1E3A8A; margin: 3px 0 0 0; }
    
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
SB_URL = "https://ewqqodsfvlvnrzsylawy.supabase.co"
SB_KEY = st.secrets.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV3cXFvZHNmdmx2bnJ6c3lsYXd5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUxMTkyOTAsImV4cCI6MjA5MDY5NTI5MH0.BWPxOsyswBT5CLrZgluRC1F2x5EpU06oexUFyakGhyc")

def get_secure_gemini_key():
    """Hàm bảo mật trích xuất Token API chìa khóa phân tích từ bộ Secrets"""
    if "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"].strip()
    return None
def save_to_supabase_techpack_table(payload_data, raw_file_bytes=None, file_name=""):
    """
    Hàm xử lý đồng bộ dữ liệu nạp kho của Chức năng 1.
    ✨ ĐÃ SỬA LỖI ĐẨY ẢNH STORAGE: Khai báo chính xác tham số headers=storage_headers 
    để ép Supabase Storage chấp nhận tệp ảnh Jpeg, dọn sạch bucket trống trơn.
    """
    try:
        style_name_db = payload_data.get("style_number_parsed", "").strip()
        if not style_name_db: 
            style_name_db = "UNKNOWN_STYLE"
            
        sketch_b64 = payload_data.get("sketch_image", "")
        public_image_url = ""
        image_data = None

        # 1. Luồng trích xuất dữ liệu hình ảnh phẳng (Sketch) từ tệp PDF bản vẽ kỹ thuật
        if raw_file_bytes and file_name.lower().endswith('.pdf'):
            try:
                import pdfplumber
                info_pdf = pdfinfo_from_bytes(raw_file_bytes)
                total_p = int(info_pdf.get("Pages", 1))
                pdf_images = convert_from_bytes(raw_file_bytes, dpi=90, first_page=1, last_page=total_p)
                
                detected_idx = int(payload_data.get("sketch_page_index_detected", 0))
                best_idx = detected_idx
                
                with pdfplumber.open(io.BytesIO(raw_file_bytes)) as pdf:
                    if 0 <= detected_idx < len(pdf.pages):
                        page_text = pdf.pages[detected_idx].extract_text() or ""
                        tech_words = ["WAIST", "HIP", "INSEAM", "THIGH", "RISE", "SPEC", "TARGET", "TOLERANCE", "SIZE"]
                        word_count = sum(1 for w in tech_words if w in page_text.upper())
                        
                        if word_count >= 4 or len(page_text) > 400:
                            min_text_len = 99999
                            for i in range(min(4, len(pdf.pages))):
                                txt = pdf.pages[i].extract_text() or ""
                                c_count = sum(1 for w in tech_words if w in txt.upper())
                                if c_count < 3 and len(txt) < min_text_len:
                                    min_text_len = len(txt)
                                    best_idx = i
                
                if 0 <= best_idx < len(pdf_images):
                    img_buf = io.BytesIO()
                    pdf_images[best_idx].convert("RGB").save(img_buf, format="JPEG", quality=85)
                    image_data = img_buf.getvalue()
            except Exception as img_err:
                print(f"[IMAGE EXTRACT ERROR]: {str(img_err)}")
                image_data = None

        if not image_data and sketch_b64:
            try:
                import base64
                image_data = base64.b64decode(sketch_b64)
            except Exception:
                pass

        # 2. Đẩy tập tin hình ảnh sản phẩm lên Supabase Storage kho_anh (Đã sửa lỗi định vị headers)
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
                
                # SỬA LỖI MẤU CHỐT: Thêm chữ headers= bọc ngoài cấu trúc tiêu đề xác thực
                upload_res = requests.post(storage_url, headers=storage_headers, data=image_data, timeout=20)
                if 200 <= upload_res.status_code <= 299:
                    public_image_url = f"{SB_URL.rstrip('/')}/storage/v1/object/public/kho_anh/{clean_filename}.jpg"
            except Exception: 
                pass

        # 3. LUỒNG KÍCH HOẠT MẮT THẦN AI VISION: TRÍCH XUẤT CHUỖI ĐẶC TRƯNG HÌNH HỌC
        measurements_raw = payload_data.get("measurements", {})
        visual_description_str = f"GARMENT TYPE: {payload_data.get('category', 'Garment Pants')}. Specs profile summary: " + ", ".join([f"{k}:{v}" for k, v in list(measurements_raw.items())[:6]])
        
        if image_data:
            gemini_key = get_secure_gemini_key()
            if gemini_key:
                try:
                    from google import genai
                    from google.genai import types
                    
                    client_db = genai.Client(api_key=gemini_key)
                    vision_prompt = """
                    Analyze this technical garment flat sketch in detail.
                    List all unique geometric attributes, structural silhouette, waistband closure type, front/back pockets layout, panel shapes, and stitch lines.
                    Output a single dense string of these visual characteristics for apparel similarity vector matching.
                    Do not include greetings, just return the raw dense characteristic description string.
                    """
                    vision_res = client_db.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[
                            types.Part.from_bytes(data=image_data, mime_type='image/jpeg'),
                            vision_prompt
                        ]
                    )
                    if vision_res and vision_res.text:
                        visual_description_str = vision_res.text.strip()
                except Exception as ai_vision_err:
                    print(f"[AI VISION RE-EXTRACT ERROR]: {str(ai_vision_err)}")

        # 4. Đẩy gói dữ liệu sạch đồng bộ lên bảng thong_so_techpack của Supabase
        headers = {
            "apikey": SB_KEY, 
            "Authorization": f"Bearer {SB_KEY}",
            "Content-Type": "application/json", 
            "Prefer": "resolution=merge-duplicates"
        }
        insert_url = f"{SB_URL.rstrip('/')}/rest/v1/thong_so_techpack"
        clean_dict = {str(k).strip(): str(v).strip() for k, v in dict(measurements_raw).items()}

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
        return 200 <= response.status_code <= 299
    except Exception as e:
        st.sidebar.error(f"Lỗi xử lý hệ thống nạp kho: {str(e)}")
        return False






def get_historical_fabric_consumption_from_db(search_keyword=None):
    """
    Hàm tra cứu kho dữ liệu san_pham lịch sử nâng cao.
    ✨ ĐÃ SỬA LỖI TRỐNG BẢNG BOM: Áp dụng tìm kiếm mờ chuỗi lõi, không chia cắt chữ/số làm mất hậu tố wash dệt may.
    """
    try:
        headers = {
            "apikey": SB_KEY, 
            "Authorization": f"Bearer {SB_KEY}"
        }
        url = f"{SB_URL.rstrip('/')}/rest/v1/san_pham"
        
        query_params = {
            "select": "style_name,article_name,consumption_type,material_size,uom,consumption_value,notes",
            "limit": 1000
        }
        
        if search_keyword:
            kw_raw = str(search_keyword).strip().upper()
            # Làm sạch ký tự đặc biệt nhưng giữ nguyên vẹn chuỗi dài mã hàng để Supabase quét chính xác
            kw_clean = re.sub(r'[^A-Z0-9]', '', kw_raw)
            
            if len(kw_clean) >= 5:
                # Tìm kiếm mờ thông minh bao quát cả mã gốc lẫn các biến thể wash rách rập phân xưởng
                or_filter = f"(style_name.ilike.*{kw_clean}*,article_name.ilike.*{kw_clean}*)"
            else:
                or_filter = f"(style_name.ilike.*{kw_raw}*,article_name.ilike.*{kw_raw}*)"
                
            query_params["or"] = or_filter
        
        response = requests.get(url, headers=headers, params=query_params, timeout=15)
        return response.json() if response.status_code == 200 else []
    except Exception: 
        return []


def get_techpack_spec_from_db(style_name_keyword=None):
    """
    Hàm cho phép AI tự động tra cứu thông số từ bảng thong_so_techpack.
    ✨ ĐÃ CHUẨN HÓA: Đảm bảo đồng bộ chính xác tên các trường dữ liệu để trả về cho Đoạn 3 hiển thị.
    """
    try:
        headers = {
            "apikey": SB_KEY, 
            "Authorization": f"Bearer {SB_KEY}"
        }
        url = f"{SB_URL.rstrip('/')}/rest/v1/thong_so_techpack"
        
        query_params = {
            "select": "StyleName,Buyer,Category,BaseSize,DetailedMeasurements,SketchURL,sketch_vector",
            "limit": 500
        }
        
        if style_name_keyword and str(style_name_keyword).strip().upper() != "UNKNOWN":
            clean_kw = str(style_name_keyword).strip()
            query_params["StyleName"] = f"ilike.*{clean_kw}*"
            
        response = requests.get(url, headers=headers, params=query_params, timeout=15)
        return response.json() if response.status_code == 200 else []
    except Exception:
        return []

def process_single_pdf_batch(file_bytes, file_name):
    """
    Hàm bóc tách dữ liệu kỹ thuật từ một file PDF độc lập.
    ✨ ĐÃ NÂNG CẤP THỊ GIÁC: Ép AI Vision quét toàn bộ các trang để định vị chính xác 100% 
    trang chứa bản vẽ phom dáng tổng thể (Front/Back view), cấm bốc nhầm trang phóng to chi tiết túi lót.
    """
    import time
    try:
        gemini_key = get_secure_gemini_key()
        if not gemini_key:
            return {"success": False, "error": "API Key cho Gemini đang bị thiếu trong Secrets."}
            
        client = genai.Client(api_key=gemini_key)
        info = pdfinfo_from_bytes(file_bytes)
        total_p = int(info.get("Pages", 1))
        
        pdf_parts_payload = []
        chat_images = convert_from_bytes(file_bytes, dpi=90, first_page=1, last_page=total_p)
        for page_img in chat_images:
            img_buf = io.BytesIO()
            page_img.convert("RGB").save(img_buf, format="JPEG", quality=75)
            pdf_parts_payload.append(types.Part.from_bytes(data=img_buf.getvalue(), mime_type='image/jpeg'))
            
        industrial_extraction_prompt = (
            "You are an expert Garment Specification Auditor. Analyze all attached sheets page by page. "
            "1. Identify the core 'Base Size' / 'Sample Size' (e.g., written as 8-, 32, or Size M). "
            "2. Identify the Buyer name and Category. "
            "3. Find the exact 'Style ID' / 'Style Number' (e.g. 5765). "
            "4. FOR FUNCTION 3 (FULL SIZE MATRIX): Scan and extract the entire grading matrix table columns for ALL available sizes. "
            "5. CRITICAL VISUAL FLAT SKETCH LOCATE RULE: Scan all pages. You MUST find the exact PAGE INDEX (0-based) "
            "that contains the FULL BODY GARMENT FLAT SKETCH (showing the entire front and back view of the pant/skort). "
            "STRICTLY FORBIDDEN: Do not select pages showing zoomed-in inner construction details like pocket bags, zippers, or button holes. "
            "Return a completely valid raw JSON string matching this schema (no markdown blocks): "
            "{"
            "  \"style_number_parsed\": \"string\","
            "  \"buyer\": \"string\","
            "  \"category\": \"string\","
            "  \"base_size_name\": \"string\","
            "  \"sketch_page_index_detected\": 0,"
            "  \"measurements\": {\"POM Description\": \"Value\"},"
            "  \"full_size_matrix\": {\"POM Description\": {\"Size_Name\": \"Value\"}}"
            "}"
        )
        
        pdf_parts_payload.append(industrial_extraction_prompt)
        
        response = None
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash', 
                    contents=pdf_parts_payload,
                    config={"response_mime_type": "application/json"}
                )
                if response and response.text: break
            except Exception as ai_err:
                if "503" in str(ai_err) or "UNAVAILABLE" in str(ai_err):
                    time.sleep((attempt + 1) * 2)
                    continue
                else:
                    return {"success": False, "error": f"Lỗi cổng truyền: {str(ai_err)}"}
                    
        if not response or not response.text:
            return {"success": False, "error": "Mô hình không phản hồi văn bản."}
            
        clean_json = response.text.strip().replace("```json", "").replace("```", "").strip()
        parsed_data = json.loads(clean_json)
        
        # Luồng cắt ảnh trích xuất dựa trên chỉ mục cưỡng bức phom dáng tổng thể
        extracted_sketch_bytes = None
        detected_idx = int(parsed_data.get("sketch_page_index_detected", 0))
        if 0 <= detected_idx < len(chat_images):
            b_buf = io.BytesIO()
            chat_images[detected_idx].convert("RGB").save(b_buf, format="JPEG", quality=90)
            extracted_sketch_bytes = b_buf.getvalue()
            
        success_db = save_to_supabase_techpack_table(parsed_data, raw_file_bytes=file_bytes, file_name=file_name)
        
        output_payload = {
            "style_number_parsed": parsed_data.get("style_number_parsed", "UNKNOWN"),
            "buyer": parsed_data.get("buyer", "UNKNOWN BUYER"),
            "category": parsed_data.get("category", "GARMENT"),
            "base_size_name": parsed_data.get("base_size_name", "32"),
            "measurements": parsed_data.get("measurements", {}),
            "full_size_matrix": parsed_data.get("full_size_matrix", {})
        }
        
        return {
            "success": True,
            "data": output_payload, 
            "style_id": output_payload["style_number_parsed"],
            "buyer": output_payload["buyer"],
            "category": output_payload["category"],
            "size": output_payload["base_size_name"],
            "measurements": output_payload["measurements"], 
            "sketch_bytes": extracted_sketch_bytes, 
            "error": None if success_db else "Lỗi ghi đồng bộ dữ liệu lên cơ sở dữ liệu"
        }
    except Exception as e:
        return {"success": False, "error": f"Lỗi bóc tách PDF: {str(e)}"}








# PHASE 5: USER INTERFACE STRUCTURE & AUTOMATION FACTORY 
# =============================================================================
with st.sidebar:
    st.markdown("""
        <div class="sidebar-brand-container">
            <div class="sidebar-brand-title">PPJ GROUP</div>
            <div class="sidebar-brand-subtitle">TECHPACK MANAGEMENT CORE AI</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<p style='font-size:11px; font-weight:700; color:#64748B; margin: 15px 0 5px 5px; letter-spacing:0.5px;'>🏭 AUTOMATION FACTORY</p>", unsafe_allow_html=True)
    
    # ĐÃ ĐỒNG BỘ: Đảm bảo khớp hoàn toàn các nhãn chức năng
    menu_selection = st.radio(
        label="Chức năng hệ thống",
        options=["📊 Upload Techpack", "🔄 Pattern Spec Comparison", "🧵 BOM & Consumption Matrix","🛒 Purchase Consumption"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.success("DATABASE ACCESS: SECURED")
    st.info("ANALYTICS ENGINE: COMPLY")

if "processed_styles" not in st.session_state:
    st.session_state["processed_styles"] = {}


if menu_selection == "📊 Upload Techpack":
    import base64
    import concurrent.futures

    st.markdown('<div class="component-title-box">📊 MULTI-BATCH GARMENT SPECIFICATION MATRIX</div>', unsafe_allow_html=True)
    
    st.markdown("""<div class="card-container"><div class="card-section-header">📥 INGESTION ENGINE</div>
    <p style="color: #64748B; font-size:13px; margin:0 0 15px 0;">Hệ thống tự động cắt trang, khử nhiễu đồ họa phẳng và gọi API mạng nơ-ron tích hợp để bóc tách thông số hàng loạt.</p></div>""", unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader("Upload Techpack PDFs Here", type=["pdf"], accept_multiple_files=True, key="bulk_techpack_pdf_uploader", label_visibility="collapsed")
    
    if uploaded_files:
        files_to_render = []
        files_need_processing = [f for f in uploaded_files if f.name not in st.session_state["processed_styles"]]
        
        if files_need_processing:
            if st.button(f"🚀 KÍCH HOẠT SỐ HÓA ĐA LUỒNG SONG SONG ({len(files_need_processing)} FILE MỚI)", use_container_width=True, type="primary"):
                status_text = st.empty()
                progress_bar = st.progress(0)
                total_new_files = len(files_need_processing)
                
                def thread_worker(file_obj):
                    try:
                        f_bytes = file_obj.getvalue()
                        res = process_single_pdf_batch(f_bytes, file_obj.name)
                        return {
                            "file_name": file_obj.name, 
                            "success": res.get("success", False), 
                            "style_id": res.get("style_id", "UNKNOWN"),
                            "buyer": res.get("buyer", "UNKNOWN BUYER"),
                            "category": res.get("category", "GARMENT"),
                            "size": res.get("size", "32"),
                            "measurements": res.get("measurements", {}),
                            "sketch_bytes": res.get("sketch_bytes", None),
                            "error": res.get("error", None),
                            "raw_bytes": f_bytes  
                        }
                    except Exception as e:
                        return {"file_name": file_obj.name, "success": False, "error": str(e), "raw_bytes": None}

                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                    future_to_file = {executor.submit(thread_worker, f): f.name for f in files_need_processing}
                    
                    for idx, future in enumerate(concurrent.futures.as_completed(future_to_file)):
                        f_name = future_to_file[future]
                        try:
                            task_res = future.result()
                            if task_res.get("success") == True:
                                # ĐỒNG BỘ TIỀN TỐ ẢNH BASE64: Ép trình duyệt tự động bung hình rập nét mảnh lớn lập tức
                                s_bytes = task_res.get("sketch_bytes")
                                img_base64_str = f"data:image/jpeg;base64,{base64.b64encode(s_bytes).decode('utf-8')}" if s_bytes else ""
                                
                                mock_data = {
                                    "style_number_parsed": task_res.get("style_id"),
                                    "buyer": task_res.get("buyer"), 
                                    "category": task_res.get("category"),
                                    "base_size_name": task_res.get("size"),
                                    "measurements": task_res.get("measurements", {}), 
                                    "sketch_image": img_base64_str, 
                                    "_raw_file_bytes": task_res["raw_bytes"] 
                                }
                                st.session_state["processed_styles"][f_name] = mock_data
                            else:
                                st.error(f"FAIL ENGINE [{f_name}]: {task_res.get('error')}")
                        except Exception as exc:
                            st.error(f"CRITICAL CRASH [{f_name}]: {str(exc)}")
                        
                        completed = idx + 1
                        progress_bar.progress(completed / total_new_files)
                        status_text.text(f"⚡ Core AI đang xử lý: {completed}/{total_new_files} tệp ({f_name})...")
                
                status_text.empty()
                progress_bar.empty()
                st.success("🎉 Số hóa dữ liệu thành công! Hãy kiểm tra bảng thông số bên dưới trước khi bấm lưu.")
        for file in uploaded_files:
            if file.name in st.session_state["processed_styles"]:
                files_to_render.append(file.name)

        if files_to_render:
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("💾 LƯU TOÀN BỘ DỮ LIỆU ĐÃ SỐ HÓA VÀO MASTER DB", key="bulk_save_all_btn", type="primary", use_container_width=True):
                success_count = 0
                with st.spinner("Đang đồng bộ cổng dữ liệu nhị phân hàng loạt lên Supabase Cloud..."):
                    for f_name in files_to_render:
                        style_data = st.session_state["processed_styles"][f_name]
                        raw_bytes_backup = style_data.get("_raw_file_bytes", None)
                        if save_to_supabase_techpack_table(payload_data=style_data, raw_file_bytes=raw_bytes_backup, file_name=f_name): 
                            success_count += 1
                st.success(f"🎉 PATTERN DATA PIPELINE: Đã bóc tách ảnh Sketch sạch và lưu trữ thành công {success_count}/{len(files_to_render)} mã hàng vào Database!")
            
            st.markdown("---")
            st.markdown("### 📋 KẾT QUẢ SỐ HÓA HÌNH HỌC VÀ THÔNG SỐ SẢN XUẤT")

            cols = st.columns(2)
            for idx, f_name in enumerate(files_to_render):
                col_target = cols[idx % 2]
                data = st.session_state["processed_styles"][f_name]
                with col_target:
                    st.markdown(f"""<div class="card-container"><div class="tech-card-header">{data.get('style_number_parsed')}</div>
                        <div class="metric-grid-box"><div><p class="metric-label">BUYER</p><p class="metric-value">{data.get('buyer')}</p></div>
                        <div><p class="metric-label">PRODUCT LINE</p><p class="metric-value">{data.get('category')}</p></div>
                        <div><p class="metric-label">BASE SIZE</p><p class="metric-value">{data.get('base_size_name')}</p></div></div></div>""", unsafe_allow_html=True)
                    
                    sub_col1, sub_col2 = st.columns([1.2, 0.8])
                    with sub_col1:
                        st.markdown("<p style='font-weight:700; font-size:12px; color:#1E293B;'>📋 SPECIFICATION DATA GRID</p>", unsafe_allow_html=True)
                        table_html = '<div class="data-table-container"><table class="industrial-table"><thead><tr><th>Point of Measurement</th><th>Target Spec</th></tr></thead><tbody>'
                        for k, v in data.get("measurements", {}).items():
                            table_html += f"<tr><td>{k}</td><td>{v}</td></tr>"
                        table_html += "</tbody></table></div>"
                        st.markdown(table_html, unsafe_allow_html=True)
                    with sub_col2:
                        st.markdown("<p style='font-weight:700; font-size:12px; color:#1E293B;'>📐 GARMENT FLAT SKETCH</p>", unsafe_allow_html=True)
                        # SỬA TRIỆT ĐỂ: Gọi biến trực tiếp chứa thẻ định vị, xóa hoàn toàn dấu ngoặc kép gây lỗi thô chữ
                        if data.get("sketch_image") and data["sketch_image"] != "":
                            try:
                                st.image(data["sketch_image"], use_container_width=True)
                            except Exception:
                                st.info("Hệ thống đang tải cổng ảnh vẽ phẳng kĩ thuật...")
                    st.markdown("<br><hr style='border-color:#E2E8F0;'><br>", unsafe_allow_html=True)
    else:
        st.markdown('<div class="idle-alert-box">⚠️ INITIALIZATION SYSTEM IDLE: Hiện tại chưa có tệp dữ liệu Techpack nào được nạp vào hệ thống để AI khởi chạy mô hình.</div>', unsafe_allow_html=True)







# -----------------------------------------------------------------------------
# CHỨC NĂNG 2: ĐỐI CHIẾU SO SÁNH HAI MÃ RẬP KHÁC NHAU (PATTERN SPEC COMPARISON)
# -----------------------------------------------------------------------------
elif menu_selection == "🔄 Pattern Spec Comparison":
    st.markdown('<div class="component-title-box">🔄 DIFFERENTIAL GEOMETRY & DELTA SPEC EVALUATOR</div>', unsafe_allow_html=True)
    st.markdown('<div class="card-container"><div class="card-section-header">🔍 CONFIGURATION SELECTION</div><p style="color: #64748B; font-size:13px; margin:0 0 15px 0;">Tải lên hai tệp bản vẽ kỹ thuật dệt may độc lập để tiến hành lập luận so sánh và tính toán toán học các khoảng chênh lệch rập mẫu.</p></div>', unsafe_allow_html=True)
    
    sc1, sc2 = st.columns(2)
    with sc1: file1 = st.file_uploader("Chọn file mẫu Techpack Gốc (File A)", type=["pdf"], key="f1")
    with sc2: file2 = st.file_uploader("Chọn file mẫu Techpack Sửa đổi (File B)", type=["pdf"], key="f2")
    
    if file1 and file2:
        # --- THUẬT TOÁN CÔ LẬP BỘ NHỚ ĐỆM TUYỆT ĐỐI CHỐNG LỆCH CỘT N/A ---
        if st.session_state.get("spec_last_f1") != file1.name or "spec_data_a" not in st.session_state:
            res1 = process_single_pdf_batch(file1.getvalue(), file1.name)
            if res1.get("success") and "data" in res1:
                st.session_state["spec_data_a"] = res1["data"]
                st.session_state["spec_last_f1"] = file1.name
            else:
                st.error(f"❌ Lỗi phân tích File A: {res1.get('error', 'Không có phản hồi')}")
                st.session_state.pop("spec_data_a", None)
                
        if st.session_state.get("spec_last_f2") != file2.name or "spec_data_b" not in st.session_state:
            res2 = process_single_pdf_batch(file2.getvalue(), file2.name)
            if res2.get("success") and "data" in res2:
                st.session_state["spec_data_b"] = res2["data"]
                st.session_state["spec_last_f2"] = file2.name
            else:
                st.error(f"❌ Lỗi phân tích File B: {res2.get('error', 'Không có phản hồi')}")
                st.session_state.pop("spec_data_b", None)
            
        d1 = st.session_state.get("spec_data_a")
        d2 = st.session_state.get("spec_data_b")
        
        if d1 and d2:
            style_a = d1.get('style_number_parsed', 'Mẫu A')
            style_b = d2.get('style_number_parsed', 'Mẫu B')
            
            # Gán nhãn phân biệt thông minh nếu người dùng upload cùng một mã thiết kế
            if style_a == style_b:
                lbl_a = f"Mẫu A ({style_a}-Gốc) [{d1.get('base_size_name','32').strip()}]"
                lbl_b = f"Mẫu B ({style_b}-Sửa) [{d2.get('base_size_name','32').strip()}]"
            else:
                lbl_a = f"Mẫu A ({style_a}) [{d1.get('base_size_name','32').strip()}]"
                lbl_b = f"Mẫu B ({style_b}) [{d2.get('base_size_name','32').strip()}]"
                
            st.info(f"⚙️ **ĐANG ĐỐI CHIẾU MA TRẬN PHÁT TRIỂN:** {lbl_a} ↔️ {lbl_b}")
            
            def clean_num(v):
                if not v or str(v).strip().upper() in ["N/A", ""]: return 0.0
                try:
                    s = str(v).replace("INCH", "").strip()
                    if " " in s:
                        p = s.split()
                        whole = float(p[0])
                        frac = p[1].split('/')
                        return whole + (float(frac[0]) / float(frac[1]))
                    return float(s.split('/')[0]) / float(s.split('/')[1]) if "/" in s else float(s)
                except:
                    import re
                    nums = re.findall(r"[-+]?\d*\.\d+|\d+", str(v))
                    return float(nums[0]) if nums else 0.0

            def extract_pom_code(pom_str):
                import re
                if not pom_str: return ""
                match = re.search(r'([A-Za-z]{2,4}-\d{3})', str(pom_str))
                return match.group(1).upper() if match else str(pom_str).lower().strip()

            df_a = pd.DataFrame(list(d1["measurements"].items()), columns=['raw_pom_a', lbl_a])
            df_b = pd.DataFrame(list(d2["measurements"].items()), columns=['raw_pom_b', lbl_b])
            
            df_a['pom_code'] = df_a['raw_pom_a'].apply(extract_pom_code)
            df_b['pom_code'] = df_b['raw_pom_b'].apply(extract_pom_code)
            
            df_a['seq'] = df_a.groupby('pom_code').cumcount()
            df_b['seq'] = df_b.groupby('pom_code').cumcount()
            
            df_res = pd.merge(df_a, df_b, on=['pom_code', 'seq'], how='outer').fillna("N/A").sort_values(['pom_code', 'seq'])
            table_body_html = ""
            compare_rows_for_df = []
            
            for _, r in df_res.iterrows():
                display_pom = r['raw_pom_a'] if r['raw_pom_a'] != "N/A" else r['raw_pom_b']
                val1, val2 = r[lbl_a], r[lbl_b]
                
                delta = round(clean_num(val2) - clean_num(val1), 3) if val1 != "N/A" and val2 != "N/A" else "N/A"
                compare_rows_for_df.append({"Vị trí đo (POM)": display_pom, lbl_a: val1, lbl_b: val2, "Sai lệch (Delta)": delta})
                
                if delta == "N/A":
                    style, txt = "color:#94A3B8; font-style:italic;", "N/A"
                elif delta > 0:
                    style, txt = "background:rgba(16,185,129,0.15); color:#166534; font-weight:700; padding:2px 8px; border-radius:4px; font-size:12px; border:1px solid #BBF7D0;", f"+{delta}"
                elif delta < 0:
                    style, txt = "background:rgba(239,68,68,0.15); color:#991B1B; font-weight:700; padding:2px 8px; border-radius:4px; font-size:12px; border:1px solid #FECACA;", f"{delta}"
                else:
                    style, txt = "color:#64748B; font-size:12px;", "0.00"
                
                table_body_html += f"<tr style='background:#FFF;'><td style='padding:10px 14px; border-bottom:1px solid #E2E8F0; font-weight:600; color:#1E293B;'>{display_pom}</td><td style='padding:10px 14px; border-bottom:1px solid #E2E8F0; color:#334155;'>{val1}</td><td style='padding:10px 14px; border-bottom:1px solid #E2E8F0; color:#334155;'>{val2}</td><td style='padding:10px 14px; border-bottom:1px solid #E2E8F0; text-align:center;'><span style='{style}'>{txt}</span></td></tr>"
            
            full_table_render = f"""
            <div style="max-height: 460px; overflow-y: auto; border: 1px solid #CBD5E1; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.02); margin-top: 15px;">
                <table style="width: 100%; border-collapse: collapse; text-align: left; font-family: sans-serif;">
                    <thead>
                        <tr style="background: linear-gradient(90deg, #1E3A8A 0%, #2563EB 100%);">
                            <th style="color: #FFFFFF; font-weight: 600; padding: 14px 16px; font-size: 13px; position: sticky; top: 0; z-index: 10;">Vị trí đo (POM Description)</th>
                            <th style="color: #FFFFFF; font-weight: 600; padding: 14px 16px; font-size: 13px; position: sticky; top: 0; z-index: 10;">{lbl_a}</th>
                            <th style="color: #FFFFFF; font-weight: 600; padding: 14px 16px; font-size: 13px; position: sticky; top: 0; z-index: 10;">{lbl_b}</th>
                            <th style="color: #FFFFFF; font-weight: 600; padding: 14px 16px; font-size: 13px; text-align: center; width: 150px; position: sticky; top: 0; z-index: 10;">Sai lệch (Delta)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_body_html}
                    </tbody>
                </table>
            </div>
            """
            st.markdown(full_table_render, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            # --- KHỐI ĐỔ MÀU EXCEL ĐỒNG BỘ GIAO DIỆN ---
            df_xl = pd.DataFrame(compare_rows_for_df)
            towrite = io.BytesIO()
            with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
                df_xl.to_excel(writer, index=False, sheet_name='Spec_Report')
                workbook  = writer.book
                worksheet = writer.sheets['Spec_Report']
                
                header_fmt = workbook.add_format({'bold':True, 'text_wrap':True, 'fg_color':'#1E3A8A', 'font_color':'white', 'border':1, 'align':'center', 'valign':'vcenter'})
                left_fmt   = workbook.add_format({'align':'left', 'valign':'vcenter', 'border':1, 'font_name':'Arial', 'font_size':10})
                center_fmt = workbook.add_format({'align':'center', 'valign':'vcenter', 'border':1, 'font_name':'Arial', 'font_size':10})
                
                green_fmt  = workbook.add_format({'bold':True, 'align':'center', 'valign':'vcenter', 'fg_color':'#E8F5E9', 'font_color':'#166534', 'border':1})
                red_fmt    = workbook.add_format({'bold':True, 'align':'center', 'valign':'vcenter', 'fg_color':'#FFEBEE', 'font_color':'#991B1B', 'border':1})
                na_fmt     = workbook.add_format({'italic':True, 'align':'center', 'valign':'vcenter', 'fg_color':'#F8FAFC', 'font_color':'#94A3B8', 'border':1})
                
                for col_num, title in enumerate(df_xl.columns):
                    worksheet.write(0, col_num, title, header_fmt)
                    max_len = max(df_xl[title].astype(str).map(len).max(), len(title)) + 4
                    worksheet.set_column(col_num, col_num, max_len)
                
                for idx, row in df_xl.iterrows():
                    worksheet.write(idx + 1, 0, row["Vị trí đo (POM)"], left_fmt)
                    worksheet.write(idx + 1, 1, row[lbl_a], center_fmt)
                    worksheet.write(idx + 1, 2, row[lbl_b], center_fmt)
                    
                    d_val = row["Sai lệch (Delta)"]
                    if d_val == "N/A":
                        worksheet.write(idx + 1, 3, "N/A", na_fmt)
                    elif d_val > 0:
                        worksheet.write(idx + 1, 3, f"+{d_val}", green_fmt)
                    elif d_val < 0:
                        worksheet.write(idx + 1, 3, d_val, red_fmt)
                    else:
                        worksheet.write(idx + 1, 3, "0.00", center_fmt)
                        
                worksheet.set_row(0, 26)
                worksheet.freeze_panes(1, 0)
                
            towrite.seek(0)
            st.download_button(label="📥 Tải Báo Cáo Đối Chiếu Có Màu (Excel)", data=towrite, file_name=f"Spec_Comparison_{style_a}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")





import io
import json
import re
import requests
import streamlit as st
import pandas as pd
from urllib.parse import quote
from google import genai
from google.genai import types

try:
    from pdf2image import convert_from_bytes, pdfinfo_from_bytes
except ImportError:
    pass

# 1. Cấu hình thông tin kết nối Cơ sở dữ liệu Supabase
SB_URL = st.secrets.get("SUPABASE_URL", "https://supabase.co").strip()
SB_KEY = st.secrets.get("SUPABASE_KEY", "your-supabase-key").strip()
headers = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"}

# 2. Khởi tạo Client AI Gemini kết nối hệ thống
if "get_secure_gemini_key" in globals():
    gemini_key = get_secure_gemini_key()
else:
    gemini_key = st.secrets.get("GEMINI_API_KEY", "").strip()

if gemini_key:
    client = genai.Client(api_key=gemini_key, http_options=types.HttpOptions(api_version='v1'))

# 3. Khởi tạo các trạng thái lưu trữ session nếu chưa có
if "matched_techpack" not in st.session_state: st.session_state["matched_techpack"] = None
if "bom_records" not in st.session_state: st.session_state["bom_records"] = []
if "consumption_chat_history" not in st.session_state: st.session_state["consumption_chat_history"] = []
def parse_fraction(val_str):
    """Hàm quy đổi phân số ngành may chuẩn sang số thập phân"""
    if not val_str: 
        return 0.0
    val_str = str(val_str).strip().lower()
    val_str = val_str.replace('"', '').replace('inches', '').replace('inch', '').replace('s', '').strip()
    try:
        if ' ' in val_str:
            parts = [p for p in val_str.split(' ') if p.strip()]
            if len(parts) >= 2:
                whole = float(parts[0])
                frac = parts[1]
            else:
                whole = 0.0
                frac = parts[0]
        else:
            whole = 0.0
            frac = val_str
            
        if '/' in frac:
            num, denom = frac.split('/')
            return whole + (float(num) / float(denom))
        return float(val_str) if val_str else 0.0
    except Exception:
        return 0.0

def ai_consumption_analyst_engine(client, user_message, matched_techpack, bom_records, new_style_measurements, target_new_sketch_bytes, detected_size):
    """Bộ não phân tích dữ liệu hình học rập và dự toán định mức vải"""
    style_old_name = matched_techpack.get("StyleName", "N/A") if matched_techpack else "N/A"
    specs_old = matched_techpack.get("DetailedMeasurements", {}) if matched_techpack else {}
    
    bom_summary = ""
    if bom_records:
        bom_summary = "\n".join([f"- Vật tư: {r.get('consumption_type')}, Mã vải: {r.get('article_name')}, Khổ vải gốc: {r.get('material_size')}, ĐM gốc: {r.get('consumption_value')}" for r in bom_records])

    shrinkage_width = re.findall(r'(?:CO RÚT NGANG|NGANG)\s*(\d+(?:\.\d+)?)\s*%', user_message.upper())
    shrinkage_length = re.findall(r'(?:CO RÚT DỌC|DỌC)\s*(\d+(?:\.\d+)?)\s*%', user_message.upper())
    new_fabric_width = re.findall(r'(?:KHỔ VẢI|KHỔ)\s*(\d+)\s*(?:\"|INCH|INCHES)?', user_message.upper())

    w_shrink = float(shrinkage_width[0]) if shrinkage_width else 0.0
    l_shrink = float(shrinkage_length[0]) if shrinkage_length else 0.0
    f_width = float(new_fabric_width[0]) if new_fabric_width else 0.0

    system_instruction = f"""
    You are an expert Garment Engineer and Techpack Costing Analyst at PPJ Group.
    Your mission is to calculate and predict the exact fabric consumption based on technical specs.
    
    CRITICAL DATA FOR CALCULATION:
    1. MATCHED OLD STYLE DATA: Name: {style_old_name}
       - Old Spec (POM): {json.dumps(specs_old)}
       - Old BOM database: {bom_summary}
    2. NEW STYLE TECHPACK DATA:
       - Target Base Size detected: Size {detected_size}
       - New Spec (POM) parsed by vision: {json.dumps(new_style_measurements)}
    3. USER INPUT FABRIC CHANGES:
       - Fabric Width requested: {f_width if f_width > 0 else 'Keep database standard'}
       - Width Shrinkage: {w_shrink}%
       - Length Shrinkage: {l_shrink}%
    """

    chat_contents = [types.Part.from_text(text=system_instruction)]
    for past_chat in st.session_state.get("consumption_chat_history", []):
        chat_contents.append(types.Part.from_text(text=f"User: {past_chat['user']}"))
        chat_contents.append(types.Part.from_text(text=f"AI: {past_chat['ai']}"))
        
    chat_contents.append(types.Part.from_text(text=f"User current request: {user_message}"))
    if target_new_sketch_bytes:
        chat_contents.append(types.Part.from_bytes(data=target_new_sketch_bytes, mime_type='image/jpeg'))

    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=chat_contents)
        ai_reply = response.text if response.text else "Hệ thống AI không thể đưa ra phân tích."
        st.session_state["consumption_chat_history"].append({"user": user_message, "ai": ai_reply})
        return ai_reply
    except Exception as e:
        return f"🚨 Lỗi cổng phân tích định mức: {str(e)}"
new_style_id_detected = "UNKNOWN_STYLE"
new_style_category_detected = ""
new_style_fabric_detected = "UNKNOWN_FABRIC"
new_style_measurements_dict = {}
new_style_base_size = "32"
img_payload = [] 
target_new_sketch_bytes = None 

# Kiểm tra dữ liệu file đầu vào từ giao diện
target_file_object = st.session_state.get('uploaded_file') or st.session_state.get('chat_uploader')

if target_file_object is not None:
    file_bytes = target_file_object.getvalue()
    file_name = target_file_object.name
    if file_name.lower().endswith('.pdf'):
        try:
            info_chat = pdfinfo_from_bytes(file_bytes)
            total_chat_pages = int(info_chat.get("Pages", 1))
            chat_images = convert_from_bytes(file_bytes, dpi=90, first_page=1, last_page=total_chat_pages)
            for idx, page_img in enumerate(chat_images):
                img_buf = io.BytesIO()
                page_img.convert("RGB").save(img_buf, format="JPEG", quality=75)
                img_payload.append(types.Part.from_bytes(data=img_buf.getvalue(), mime_type='image/jpeg'))
            
            extraction_prompt = (
                "You are an expert Garment Specification Auditor at PPJ Group. Analyze all attached sheets page by page. "
                "Return ONLY a raw valid JSON string with no markdown code blocks or wrapper, matching this exact schema: "
                "{\"detected_style_id\": \"string\", \"category\": \"string\", \"fabric_code\": \"string\", \"base_size_detected\": \"string\", \"measurements\": {}, \"sketch_page_index_detected\": 0}"
            )

            extraction_payload = list(img_payload)
            extraction_payload.append(extraction_prompt)
            
            extraction_res = client.models.generate_content(model='gemini-2.5-flash', contents=extraction_payload)
            clean_json_text = extraction_res.text.strip().replace("```json", "").replace("```", "").strip()
            
            parsed_meta = json.loads(clean_json_text)
            new_style_id_detected = parsed_meta.get("detected_style_id", "UNKNOWN_STYLE").strip()
            new_style_category_detected = parsed_meta.get("category", "").strip()
            new_style_fabric_detected = parsed_meta.get("fabric_code", "UNKNOWN_FABRIC").strip()
            new_style_base_size = parsed_meta.get("base_size_detected", "32").strip()
            new_style_measurements_dict = parsed_meta.get("measurements", {})
            detected_idx = int(parsed_meta.get("sketch_page_index_detected", 0))
            
            if 0 <= detected_idx < len(chat_images):
                b_buf = io.BytesIO()
                chat_images[detected_idx].convert("RGB").save(b_buf, format="JPEG")
                target_new_sketch_bytes = b_buf.getvalue()
        except Exception:
            pass
    else:
        target_new_sketch_bytes = file_bytes
# Lấy từ kho dựa trên mã hàng vừa nhận diện từ file
dynamic_keyword = str(new_style_id_detected).strip().upper()
base_sb_url = SB_URL.rstrip('/')

if dynamic_keyword != "UNKNOWN_STYLE":
    try:
        # 1. Truy vấn thông tin tài liệu kỹ thuật tương đồng trong kho
        tp_url = f"{base_sb_url}/rest/v1/techpacks?style_id=eq.{quote(dynamic_keyword)}&select=*"
        tp_res = requests.get(tp_url, headers=headers)
        if tp_res.status_code == 200 and tp_res.json():
            st.session_state["matched_techpack"] = tp_res.json()[0] if isinstance(tp_res.json(), list) else tp_res.json()
            
            # 2. Truy vấn bảng định mức nguyên phụ liệu tương ứng của mã đó
            bom_url = f"{base_sb_url}/rest/v1/bom_records?style_id=eq.{quote(dynamic_keyword)}&select=*"
            bom_res = requests.get(bom_url, headers=headers)
            if bom_res.status_code == 200:
                st.session_state["bom_records"] = bom_res.json()
    except Exception as e:
        st.warning(f"Lỗi truy vấn dữ liệu đồng bộ kho: {e}")
# Đảm bảo biến điều hướng menu tồn tại
if 'menu_selection' not in locals():
    menu_selection = "🧵 BOM & Consumption Matrix"

if menu_selection == "🧵 BOM & Consumption Matrix":
    st.markdown('<div class="component-title-box">🧵 INTELLIGENT BOM & CONSUMPTION MATRIX ENGINE</div>', unsafe_allow_html=True)
    
    # Chia layout thành 2 cột cân đối trên màn hình hiển thị
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🖼️ Hình ảnh mẫu tương đồng (Sketch)")
        if target_new_sketch_bytes:
            st.image(target_new_sketch_bytes, caption=f"Hình ảnh kỹ thuật thiết kế - Mã hàng: {dynamic_keyword}", use_container_width=True)
        else:
            st.info("Chưa nhận dạng được hình ảnh kỹ thuật từ tập tin đầu vào.")
            
    with col2:
        st.subheader("📦 Định mức Nguyên phụ liệu trong kho")
        matched_tp = st.session_state.get("matched_techpack")
        bom_data = st.session_state.get("bom_records")
        
        if matched_tp:
            st.success(f"✅ Đã kết nối mã tương đồng thành công: **{matched_tp.get('style_id')}**")
            if bom_data:
                df_bom = pd.DataFrame(bom_data)
                # Định nghĩa lại các cột để hiển thị tiếng Việt rõ ràng hơn cho nhà máy
                display_cols = {
                    "consumption_type": "Loại vật tư",
                    "article_name": "Mã / Tên vải",
                    "material_size": "Khổ vải gốc",
                    "consumption_value": "Định mức gốc"
                }
                # Lọc và đổi tên cột để hiển thị gọn gàng
                valid_cols = [c for c in display_cols.keys() if c in df_bom.columns]
                if valid_cols:
                    df_filtered = df_bom[valid_cols].rename(columns={k: v for k, v in display_cols.items() if k in valid_cols})
                    st.dataframe(df_filtered, use_container_width=True)
                else:
                    st.dataframe(df_bom, use_container_width=True)
            else:
                st.info("Mã hàng tồn tại trong kho nhưng bảng định mức chi tiết (BOM) trống.")
        else:
            st.warning("⚠️ Không tìm thấy hoặc chưa đồng bộ được dữ liệu định mức của mã này từ kho.")









# -----------------------------------------------------------------------------
# CHỨC NĂNG 3: QUẢN LÝ ĐỊNH MỨC MUA SẮM VÀ ĐẶT HÀNG (PURCHASE CONSUMPTION)
# -----------------------------------------------------------------------------
elif menu_selection == "🛒 Purchase Consumption":
    st.markdown('<div class="component-title-box">🛒 PURCHASE CONSUMPTION & INTELLIGENT PLANNING ENGINE</div>', unsafe_allow_html=True)
    st.markdown("""<div class="card-container"><div class="card-section-header">📦 MULTI-SOURCE INGESTION ENGINE</div>
    <p style="color: #64748B; font-size:13px; margin:0;">Tải lên đồng thời File SBD (Số lượng chi tiết theo Size phẳng) và File Techpack để kích hoạt mạng nơ-ron lập lịch trình đặt hàng vật tư.</p></div>""", unsafe_allow_html=True)
    
    col_left, col_right = st.columns(2)
    with col_left: file_sbd = st.file_uploader("📋 Chọn File SBD Số Lượng (Excel/PDF)", type=["xlsx", "xls", "pdf"], key="purchase_sbd")
    with col_right: file_tp = st.file_uploader("📐 Chọn File Techpack Thông Số (PDF)", type=["pdf"], key="purchase_tp")
        
    if file_sbd and file_tp:
        st.markdown("<br>", unsafe_allow_html=True)
        
        if "purchase_ready" not in st.session_state:
            st.session_state["purchase_ready"] = False
        if "sbd_parsed_data" not in st.session_state:
            st.session_state["sbd_parsed_data"] = {}
        if "pur_tp_parsed_data" not in st.session_state:
            st.session_state["pur_tp_parsed_data"] = {}

        if st.session_state.get("last_sbd_name") != file_sbd.name or st.session_state.get("last_pur_tp_name") != file_tp.name:
            st.session_state["purchase_ready"] = False
            st.session_state["sbd_parsed_data"] = {}
            st.session_state["pur_tp_parsed_data"] = {}

        trigger_btn = st.button("⚡ KÍCH HOẠT SỐ HÓA ĐA LUỒNG SONG SONG", type="primary", use_container_width=True)
        
        if trigger_btn:
            st.session_state["purchase_ready"] = True
            
            # 1. TIẾN HÀNH SỐ HÓA FILE SBD ĐƠN HÀNG (CẤU HÌNH PROMPT QUÉT MA TRẬN PHỨC TẠP CỦA PPJ)
            with st.spinner("🚀 AI đang xử lý ma trận số lượng đơn hàng từ File SBD..."):
                gemini_key = get_secure_gemini_key()
                client_ai = genai.Client(api_key=gemini_key)
                
                sbd_bytes = file_sbd.getvalue()
                sbd_content_str = ""
                sbd_parts_payload = []
                
                if file_sbd.name.lower().endswith(('.xlsx', '.xls')):
                    try:
                        excel_data = pd.read_excel(io.BytesIO(sbd_bytes), sheet_name=None)
                        for sheet_name, df_sheet in excel_data.items():
                            sbd_content_str += f"\n--- SHEET NAME: {sheet_name} ---\n"
                            sbd_content_str += df_sheet.fillna("").to_csv(index=False)
                    except Exception as xl_err:
                        st.error(f"Lỗi đọc cấu trúc tệp Excel: {str(xl_err)}")
                elif file_sbd.name.lower().endswith('.pdf'):
                    sbd_parts_payload.append(types.Part.from_bytes(data=sbd_bytes, mime_type='application/pdf'))
                
                # SIÊU PROMPT DỆT MAY: Ép AI đọc đúng kết cấu bảng cân đối PO thực tế của PPJ Group
                sbd_prompt = f"""
                You are an expert Garment Order Planner. Analyze this raw CSV data converted from an industrial Excel Order Breakdown Sheet (SBD).
                The sheet contains a complex matrix of order quantities distributed across size columns and breakdown summaries.
                
                YOUR DATA EXTRACTION MISSIONS:
                1. Identify the Core Style Number/ID (e.g., look for patterns like '5765-01' or '5765' in the columns).
                2. Find the total order quantity (Total PO) by summing up the quantities.
                3. CRITICAL MATRIX ANALYSIS RULE: 
                   Look for the rows or sections containing size labels (such as 000, 00, 0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24) or sub-tables titled 'INSEAM' / 'TOTAL'.
                   Extract the exact final total order quantities for EACH size. For example, if a size column header is '4' or '4.0' and its total summary cell below is '495', extract that mapping. 
                   Ignore any raw formulas, row indices, or placeholder text. 
                   Only return a flat mapping of "Size_Name": total_quantity_integer for valid sizes that have quantities greater than 0.
                
                Return a strict raw JSON matching this schema:
                {{"style_id": "string", "total_quantity": integer, "size_breakdown": {{"Size Name": integer}}}}
                """
                
                if sbd_content_str:
                    sbd_parts_payload.append(f"Here is the text data extracted from the Excel order sheet:\n{sbd_content_str}")
                
                sbd_parts_payload.append(sbd_prompt)
                
                try:
                    res_sbd = client_ai.models.generate_content(
                        model='gemini-2.5-flash', contents=sbd_parts_payload,
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    raw_text = res_sbd.text.strip().replace("```json", "").replace("```", "").strip()
                    st.session_state["sbd_parsed_data"] = json.loads(raw_text)
                    st.session_state["last_sbd_name"] = file_sbd.name
                except Exception as e:
                    st.error(f"Lỗi AI trích xuất SBD: {str(e)}")
                    st.session_state["sbd_parsed_data"] = {}

            # 2. TIẾN HÀNH SỐ HÓA FILE TECHPACK THÔNG SỐ RẬP MẪU
            with st.spinner("📐 AI đang bóc tách bảng thông số kỹ thuật rập từ bản vẽ Techpack..."):
                res_tp = process_single_pdf_batch(file_tp.getvalue(), file_tp.name)
                if res_tp.get("success") and "data" in res_tp:
                    st.session_state["pur_tp_parsed_data"] = res_tp["data"]
                    st.session_state["last_pur_tp_name"] = file_tp.name
                else:
                    st.error(f"Lỗi AI trích xuất Techpack: {res_tp.get('error')}")
                    st.session_state["pur_tp_parsed_data"] = {}
            st.rerun()

        # --- KHỐI HIỂN THỊ DỮ LIỆU ĐA CHIỀU RA GIAO DIỆN WEB ---
        if st.session_state.get("purchase_ready") is True:
            sbd_raw = st.session_state.get("sbd_parsed_data", {})
            sbd_data = json.loads(sbd_raw) if isinstance(sbd_raw, str) else sbd_raw
            
            tp_raw = st.session_state.get("pur_tp_parsed_data", {})
            tp_data = json.loads(tp_raw) if isinstance(tp_raw, str) else tp_raw
            
            if isinstance(sbd_data, dict) and isinstance(tp_data, dict) and sbd_data and tp_data:
                st.success(f"🎉 Hệ thống số hóa đa nguồn đang sẵn sàng xử lý dữ liệu.")
                tab_sbd, tab_tp = st.tabs(["📋 Ma Trận Số Lượng Đơn Hàng (SBD)", "📐 Bảng Ma Trận Thông Số Toàn Bộ Size (Techpack)"])
                
                with tab_sbd:
                    if sbd_data and "size_breakdown" in sbd_data:
                        st.markdown(f"**Tổng số lượng đơn đặt hàng (Total PO):** `{sbd_data.get('total_quantity', 0):,}` Pcs")
                        df_sbd_show = pd.DataFrame(list(sbd_data.get("size_breakdown", {}).items()), columns=["Kích thước (Size / Nhóm phẳng)", "Số lượng đặt (Pcs)"])
                        st.dataframe(df_sbd_show, use_container_width=True, hide_index=True)
                    else:
                        st.warning("⏳ Đang đợi AI xử lý hoặc tệp dữ liệu SBD rỗng.")
                        
                with tab_tp:
                    matrix_data = tp_data.get("full_size_matrix", {})
                    if not matrix_data:
                        matrix_data = tp_data.get("measurements", {})
                        
                    if matrix_data:
                        st.markdown(f"**Vải chính / Chủng loại:** `{tp_data.get('category', 'N/A')}` | **Size Gốc:** `{tp_data.get('base_size_name', 'N/A')}`")
                        try:
                            df_matrix = pd.DataFrame.from_dict(matrix_data, orient='index')
                            df_matrix.insert(0, "Vị trí mod (POM Description)", df_matrix.index)
                            st.dataframe(df_matrix, use_container_width=True, hide_index=True)
                        except Exception:
                            df_tp_show = pd.DataFrame(list(matrix_data.items()), columns=["POM Description", "Thông số"])
                            st.dataframe(df_tp_show, use_container_width=True, hide_index=True)
                    else:
                        st.warning("⏳ Đang đợi AI xử lý hoặc tệp Techpack rỗng.")

                 # --- 🛠️ KHỐI CHAT AI VÀ CỖ MÁY TOÁN HỌC TÍNH TOÁN ĐẶT HÀNG NÂNG CAO ---
                st.markdown("<br><hr style='border:0.5px solid #E2E8F0;'>", unsafe_allow_html=True)
                
                # Giao diện tiêu đề kết hợp nút Xóa lịch sử Chat bên phải
                chat_title_col, chat_btn_col = st.columns([3, 1])
                with chat_title_col:
                    st.markdown("### 💬 TRỢ LÝ AI TÍNH TOÁN ĐỊNH MỨC TRUNG BÌNH ĐƠN HÀNG")
                    st.caption("Nhập định mức của size cơ bản. AI sẽ phân tích độ lệch thông số (Grading) của toàn bộ dải size để suy ra định mức từng size, từ đó tính ra Định mức trung bình chính xác cho cả đơn hàng.")
                
                with chat_btn_col:
                    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                    if st.button("🗑️ Xóa lịch sử Chat", type="secondary", use_container_width=True):
                        st.session_state["purchase_chat_history"] = []
                        st.rerun()
                
                if "purchase_chat_history" not in st.session_state:
                    st.session_state["purchase_chat_history"] = []
                    
                for msg in st.session_state["purchase_chat_history"]:
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])
                        if "df_result" in msg:
                            st.dataframe(msg["df_result"], use_container_width=True, hide_index=True)
                        if "excel_bytes" in msg:
                            st.download_button(label="📥 Tải Báo Cáo Định Mức Chi Tiết (Excel)", data=msg["excel_bytes"], file_name="AI_Consumption_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                
                if user_instruction := st.chat_input("Nhập định mức size gốc (Ví dụ: Định mức size 8 là 1.04 yds, tính định mức trung bình toàn đơn hàng)..."):
                    with st.chat_message("user"):
                        st.write(user_instruction)
                    st.session_state["purchase_chat_history"].append({"role": "user", "content": user_instruction})
                    
                    with st.chat_message("assistant"):
                        with st.spinner("🤖 AI đang phân tích tỷ lệ nhảy size hình học và tính toán định mức trung bình..."):
                            gemini_key = get_secure_gemini_key()
                            client_ai = genai.Client(api_key=gemini_key)
                            
                            ai_context_prompt = f"""
                            You are an expert Apparel Production Planner and Costing Engineer. 
                            We have parsed two critical source documents for this style:
                            
                            1. FULL SIZE GRADING MATRIX FROM TECHPACK (Thông số hình học các size):
                            {json.dumps(tp_data.get('full_size_matrix', {})) if tp_data else "{}"}
                            Base Size of this Techpack: {tp_data.get('base_size_name', 'N/A')}
                            
                            2. ORDER QUANTITIES MATRIX FROM SBD (Số lượng đặt của từng size):
                            {json.dumps(sbd_data.get('size_breakdown', {})) if sbd_data else "{}"}
                            
                            The user prompt is: "{user_instruction}"
                            
                            YOUR EXPERT MATHEMATICAL & TEXTILE MISSION:
                            1. Extract the base consumption value and its target size from the user input (e.g., 1.04 yds for Size 8).
                            2. Look closely at the FULL SIZE GRADING MATRIX from Techpack. Analyze how key fabric-consuming specs change as the size scales up to size 20 or down to size 000.
                            3. Calculate the proportional geometric fabric surface area difference for EACH size relative to the Base Size. 
                            4. Extrapolate and assign a specific calculated consumption (Định mức phân bổ) for EACH size based on these grading scaling factors.
                            5. Multiply each size's calculated consumption by its respective PO quantity from the SBD data to find the Net Requirement for each size.
                            6. CRITICAL CORE REQUIREMENT: Calculate the OVERALL WEIGHTED AVERAGE CONSUMPTION (Định mức trung bình bình quyền gia quyền của cả đơn hàng) using this formula:
                               Weighted Average Consumption = (Sum of Net Requirements for all sizes) / (Total PO Quantity of all sizes)
                            7. DO NOT add any default 3% wastage allowance. Focus on the raw mathematical consumption.
                            
                            Provide a clear professional markdown text explanation of your logic first in Vietnamese, explicitly stating the calculated Weighted Average Consumption for the order.
                            Then, you MUST output a final raw JSON block at the very end of your response inside a ```json ... ``` container.
                            The JSON schema must be exactly a list of objects like this:
                            ```json
                            [
                              {{"Kích thước (Size/Inseam)": "string", "Số lượng PO (Pcs)": 100, "Định mức phân bổ (Yds/Pcs)": 1.08, "Tổng lượng vải cần (Yds)": 108.0}}
                            ]
                            ```
                            """
                            
                            try:
                                response_ai = client_ai.models.generate_content(
                                    model='gemini-2.5-flash',
                                    contents=ai_context_prompt
                                )
                                
                                ai_text = response_ai.text
                                text_desc = ai_text
                                json_block = ""
                                
                                # --- 🛠️ THUẬT TOÁN SỬA LỖI TÁCH CHUỖI VÀ TRÍCH XUẤT JSON AN TOÀN TUYỆT ĐỐI ---
                                if "```json" in ai_text:
                                    try:
                                        parts = ai_text.split("```json")
                                        text_desc = parts[0] # Đoạn text chữ lập luận tiếng Việt
                                        
                                        # Trích xuất đoạn chứa chuỗi cấu trúc JSON nằm sau từ khóa
                                        json_part_raw = parts[1].split("```")
                                        json_block = json_part_raw[0].strip()
                                    except Exception:
                                        json_block = ""
                                
                                # Giải pháp dự phòng tự động bốc tách bằng Regex nếu AI trả sai cấu trúc Markdown
                                if not json_block:
                                    import re
                                    match_json = re.search(r'\[\s*\{.*\}\s*\]', ai_text, re.DOTALL)
                                    if match_json:
                                        json_block = match_json.group(0).strip()
                                        text_desc = ai_text.replace(json_block, "")
                                    
                                st.write(text_desc)
                                new_msg_data = {"role": "assistant", "content": text_desc}
                                
                                # Nếu trích xuất thành công ma trận mảng, tiến hành vẽ bảng lưới và xuất Excel
                                if json_block:
                                    try:
                                        df_res = pd.read_json(io.StringIO(json_block))
                                        st.dataframe(df_res, use_container_width=True, hide_index=True)
                                        new_msg_data["df_result"] = df_res
                                        
                                        xl_buf = io.BytesIO()
                                        with pd.ExcelWriter(xl_buf, engine='xlsxwriter') as writer:
                                            df_res.to_excel(writer, index=False, sheet_name='Consumption_Plan')
                                            ws = writer.sheets['Consumption_Plan']
                                            for i, col in enumerate(df_res.columns):
                                                ws.set_column(i, i, max(df_res[col].astype(str).map(len).max(), len(col)) + 4)
                                        xl_buf.seek(0)
                                        xl_bytes = xl_buf.getvalue()
                                        
                                        st.download_button(label="📥 Tải Báo Cáo Định Mức Chi Tiết (Excel)", data=xl_bytes, file_name=f"AI_Consumption_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                                        new_msg_data["excel_bytes"] = xl_bytes
                                    except Exception as json_parse_err:
                                        st.warning(f"AI phản hồi văn bản thành công nhưng cấu trúc ma trận bảng tính bị lệch: {str(json_parse_err)}")
                                    
                                st.session_state["purchase_chat_history"].append(new_msg_data)
                                st.rerun()
                                
                            except Exception as chat_err:
                                st.error(f"Cỗ máy toán học AI gặp lỗi khi xử lý dữ liệu: {str(chat_err)}")
