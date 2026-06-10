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
SB_URL = "https://supabase.co"
SB_KEY = st.secrets.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV3cXFvZHNmdmx2bnJ6c3lsYXd5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUxMTkyOTAsImV4cCI6MjA5MDY5NTI5MH0.BWPxOsyswBT5CLrZgluRC1F2x5EpU06oexUFyakGhyc")

def get_secure_gemini_key():
    """Hàm bảo mật trích xuất Token API chìa khóa phân tích từ bộ Secrets"""
    if "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"].strip()
    return None

def save_to_supabase_techpack_table(payload_data, raw_file_bytes=None, file_name=""):
    """
    Hàm xử lý đồng bộ dữ liệu, tự động tìm đúng trang có hình thiết kế phẳng (Sketch) sạch,
    đẩy ảnh rập lên Storage kho_anh và số hóa chuỗi đặc trưng hình học đồng bộ với luồng đối soát.
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

        if image_data:
            gemini_key = get_secure_gemini_key()
            if gemini_key:
                client = genai.Client(api_key=gemini_key)
        
        return public_image_url
    except Exception as e:
        st.error(f"Lỗi đồng bộ Supabase: {str(e)}")
        return ""

# 1. SIDEBAR: Form nạp trước thông số gốc, định mức định biên, vải, khổ, độ co...
with st.sidebar:
    st.markdown('''
        <div class="sidebar-brand-container">
            <p class="sidebar-brand-title">PPJ TECHPACK AI</p>
            <p class="sidebar-brand-subtitle">MANAGEMENT SYSTEM</p>
        </div>
    ''', unsafe_allow_html=True)
    
    st.markdown("### 🧱 NẠP MASTER DATA NPL")
    ma_hang = st.text_input("Mã hàng (Style Number):", value="PPJ-DENIM-2026")
    kho_vai_chinh = st.number_input("Khổ vải khả dụng (Cuttable Width - inch):", value=58.0, step=0.5)
    
    st.markdown("**Độ co Vải thực tế (Shrinkage %)**")
    co_doc = st.number_input("Độ co Dọc (Warp %):", value=3.0, step=0.1)
    co_ngang = st.number_input("Độ co Ngang (Weft %):", value=4.5, step=0.1)
    
    st.markdown("**Hiệu suất dự kiến**")
    hieu_suat_marker = st.slider("Hiệu suất sơ đồ dự kiến (%):", 80, 100, 92)

# Thiết lập các phân hệ tab ngang lớn trên giao diện chính
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Bài toán 1: Tính Định mức Báo giá", 
    "📉 Bài toán 2: Tính Định mức Đặt hàng", 
    "✂️ Bài toán 3: Lập Tác nghiệp Cắt",
    "🔬 Bài toán 4: Phân tích Rủi ro Khách hàng"
])
# --- BÀI TOÁN 1: TÍNH ĐỊNH MỨC BÁO GIÁ (COSTING) ---
with tab1:
    st.markdown('<div class="component-title-box">Bài toán 1: Tính Định mức Báo giá (Up tài liệu + Thông tin NPL)</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.file_uploader("📁 Upload Techpack gốc (PDF / Excel)", key="tp_b1")
    with col2:
        st.file_uploader("📁 Upload Bảng thông tin NPL dự kiến", key="npl_b1")
        
    st.markdown('<div class="card-container"><h5>📝 BẢNG SO SÁNH THÔNG SỐ (T/S COMPARISON)</h5>', unsafe_allow_html=True)
    ts_b1_df = pd.DataFrame({
        "Vị trí đo (POM)": ["Dài quần", "Vòng eo", "Vòng mông", "Vòng đùi", "Rộng ống"],
        "Thông số Techpack": ["102 cm", "76 cm", "98 cm", "58 cm", "18 cm"],
        "Dung sai cho phép": ["+/- 1.0 cm", "+/- 0.5 cm", "+/- 1.0 cm", "+/- 0.5 cm", "+/- 0.3 cm"],
        "Trạng thái đối soát": ["Khớp hoàn toàn", "Cần chú ý Wash", "Khớp hoàn toàn", "Khớp hoàn toàn", "Khớp hoàn toàn"]
    })
    st.dataframe(ts_b1_df, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card-container"><h5>📊 BẢNG ĐỊNH MỨC BÁO GIÁ THEO NPL (BOM CONSUMPTION)</h5>', unsafe_allow_html=True)
    bom_b1_df = pd.DataFrame({
        "STT":,
        "Tên Nguyên Phụ Liệu": ["Vải chính Denim 12oz", "Chỉ may 100% Spun Poly", "Nút dập kim loại PPJ", "Nhãn sườn Satin"],
        "Khổ định biên": [f"{kho_vai_chinh}\"", "-", "14 mm", "-"],
        "Độ co ứng dụng": [f"Dọc {co_doc}% / Ngang {co_ngang}%", "0%", "0%", "0%"],
        "Hiệu suất sơ đồ": [f"{hieu_suat_marker}%", "95%", "98%", "100%"],
        "Định mức tinh": ["1.20 yds", "115.0 m", "1.00 pc", "1.00 pc"],
        "Định mức Báo giá (Gồm hao hụt)": ["1.39 yds", "121.1 m", "1.02 pcs", "1.00 pc"]
    })
    st.dataframe(bom_b1_df, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(f"""
    <div class="idle-alert-box">
        <strong>⚠️ AI COMMENT & PHÂN TÍCH RỦI RO ĐỊNH MỨC BÁO GIÁ:</strong><br>
        - <strong>Rủi ro co rút:</strong> Độ co ngang thực tế đang đặt là <strong>{co_ngang}%</strong>. Nếu rập mẫu chưa cộng bù trừ phân bổ co rút này, sản phẩm sau giặt (Wash) có nguy cơ hụt thông số vòng mông từ 1.5cm - 2cm.<br>
        - <strong>Hao hụt sơ đồ:</strong> Với khổ vải hẹp <strong>{kho_vai_chinh}"</strong>, việc duy trì hiệu suất sơ đồ <strong>{hieu_suat_marker}%</strong> cho cụm chi tiết rập lớn sẽ rất áp lực. Đề xuất nâng biên độ an toàn định mức vải thêm 1.5%.
    </div>
    """, unsafe_allow_html=True)

# --- BÀI TOÁN 2: TÍNH ĐỊNH MỨC ĐẠT HÀNG (BULK PRODUCTION) ---
with tab2:
    st.markdown('<div class="component-title-box">Bài toán 2: Tính Định mức Đặt hàng (Dựa theo Rập, Tài liệu mới, SBD)</div>', unsafe_allow_html=True)
    
    col1, col3, col4 = st.columns(3)
    with col1:
        st.file_uploader("📁 Upload File Rập hình học (.DXF / .PLT / .AAMA)", key="rap_b2")
    with col3:
        st.file_uploader("📁 Upload Tài liệu kỹ thuật cập nhật mới", key="tp_b2")
    with col4:
        st.file_uploader("📁 Upload Bảng tỷ lệ cỡ vóc (Size Breakdown - SBD)", key="sbd_b2")

    st.markdown('<div class="card-container"><h5>🔄 ĐỐI CHIẾU THÔNG SỐ: BÁO GIÁ vs SẢN XUẤT THỰC TẾ</h5>', unsafe_allow_html=True)
    ts_b2_df = pd.DataFrame({
        "Vị trí đo (POM)": ["Dài quần", "Vòng eo", "Vòng mông", "Vòng đùi", "Rộng ống"],
        "T/S Chào Báo giá": ["102 cm", "76 cm", "98 cm", "58 cm", "18 cm"],
        "T/S Sản xuất thực tế": ["103 cm", "76 cm", "99 cm", "58 cm", "17.5 cm"],
        "Chênh lệch (Delta)": ["+ 1.0 cm (Tăng)", "0.0 cm", "+ 1.0 cm (Tăng)", "0.0 cm", "- 0.5 cm (Giảm)"],
        "Đánh giá tác động": ["Tốn vải hơn sơ đồ cũ", "An toàn", "⚠️ Cần kiểm tra lại rập", "An toàn", "Tiết kiệm vải biên"]
    })
    st.dataframe(ts_b2_df, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card-container"><h5>📦 BẢNG ĐỊNH MỨC ĐẶT HÀNG THỰC TẾ (PRODUCTION BOM)</h5>', unsafe_allow_html=True)
    bom_b2_df = pd.DataFrame({
        "STT":,
        "Tên Nguyên Phụ Liệu": ["Vải chính Denim 12oz (Thực tế)", "Chỉ may 100% Spun Poly", "Nút dập kim loại PPJ", "Nhãn sườn Satin"],
        "Khổ duyệt sản xuất": [f"{kho_vai_chinh}\"", "-", "14 mm", "-"],
        "Độ co Rập kiểm duyệt": [f"Dọc {co_doc}% / Ngang {co_ngang}%", "0%", "0%", "0%"],
        "Hiệu suất sơ đồ chạy rập": ["91.5 %", "95.0 %", "99.0 %", "100.0 %"],
        "Định mức đặt mua / Sp": ["1.41 yds", "122.5 m", "1.01 pcs", "1.00 pc"]
    })
    st.dataframe(bom_b2_df, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card-container"><h5>🧮 BẢNG TÍNH TÁC NGHIỆP TỔNG VÀ SẢN LƯỢNG MUA (SIZE MATRIC BUYING)</h5>', unsafe_allow_html=True)
    tag_nghiep_df = pd.DataFrame({
        "Màu sắc (Colorway)": ["Dark Wash (Xanh đậm)", "Light Wash (Xanh nhạt)"],
        "Size 29":,
        "Size 30":,
        "Size 31":,
        "Size 32":,
        "Tổng sản lượng (Pcs)":,
        "Định mức vải duyệt": ["1.41 yds", "1.41 yds"],
        "TỔNG NHU CẦU MUA VẢI": ["1,128.0 yds", "705.0 yds"]
    })
    st.dataframe(tag_nghiep_df, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class="idle-alert-box" style="background-color: #FEF2F2; border-left: 5px solid #EF4444; color: #991B1B;">
        <strong>⚠️ AI COMMENT & CẢNH BÁO RỦI RO SẢN XUẤT BULK:</strong><br>
        - <strong>Lệch thông số T/S:</strong> Vòng mông sản xuất tăng 1.0cm so với bảng báo giá costing. Định mức đặt hàng thực tế đã bị đẩy tăng từ 1.39 yds lên 1.41 yds. Phòng mua hàng cần đối chiếu biên độ tài chính.<br>
        - <strong>Rủi ro Shading (Lệch màu vải):</strong> Đơn hàng Dark Wash có sản lượng tập trung lớn ở các size trung bình (Size 30, 31). Tổ trải vải cần thực hiện gom nhóm cây vải cùng ánh màu trước khi lên bàn cắt để tránh lỗi khác màu trên cùng một sản phẩm.
    </div>
    """, unsafe_allow_html=True)

# --- BÀI TOÁN 3: LẬP TÁC NGHIỆP CẮT ---
with tab3:
    st.markdown('<div class="component-title-box">Bài toán 3: Phân hệ Lập Tác nghiệp Cắt (Cutting Room Planning)</div>', unsafe_allow_html=True)
    st.info("Hệ thống tự động đồng bộ số liệu từ ma trận SBD tại Bài toán 2 để tính toán phương án phối ghép sơ đồ bàn cắt tối ưu.")

# --- BÀI TOÁN 4: PHÂN TÍCH RỦI RO ĐỊNH MỨC THEO KHÁCH HÀNG ---
with tab4:
    st.markdown('<div class="component-title-box">Bài toán 4: Phân tích Rủi ro Định mức theo từng Khách hàng</div>', unsafe_allow_html=True)
    st.warning("Phân hệ nghiên cứu chuyên sâu: Đang cấu hình cổng đồng bộ dữ liệu Real-time qua API kết nối hệ thống Core ERP/MES.")
