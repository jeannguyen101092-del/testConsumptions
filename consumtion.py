import streamlit as st
import io
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import pdf2image

# --- 1. ĐỊNH NGHĨA STRUCT KHỚP VỚI MỤC TIÊU GIAI ĐOẠN 1 ---
class MaterialItem(BaseModel):
    category: str = Field(description="Main Fabric, Pocketing, Fusing, Lining, etc.")
    description: str
    standard_width_inch: Optional[float] = None

class MeasurementItem(BaseModel):
    pom_code: str
    description: str
    values: Dict[str, float] = Field(description="Key: Size, Value: Số đo")

class POMData(BaseModel):
    size_run: List[str]
    measurements: List[MeasurementItem]

class ProductComponent(BaseModel):
    component_name: str
    material_category: str
    cut_count_per_garment: int
    is_symmetrical: bool

class TechpackExtractionOutput(BaseModel):
    style_number: str
    product_category: str
    base_size: str
    bill_of_materials: List[MaterialItem]
    point_of_measurements: POMData
    product_components: List[ProductComponent]


# --- GIAO DIỆN STREAMLIT HIỆN TẠI CỦA BẠN ---
st.title("AI FABRIC CONSUMPTION")

# Nơi uploader file (Giống cấu hình nút màu xám trên ảnh của bạn)
uploaded_file = st.file_uploader("TECHPACK UPLOADER & PROFILE SUMMARY", type=["pdf"])

if uploaded_file is not None:
    # 1. Hiển thị trạng thái đang quét (Thay cho dòng chữ đỏ trong ảnh)
    with st.spinner("🔄 AI Platform đang quét thông tin đa tầng tài liệu kỹ thuật Techpack..."):
        try:
            # Đọc file pdf từ bộ nhớ
            pdf_bytes = uploaded_file.read()
            
            # Chuyển đổi PDF sang ảnh (Lấy 3 trang đầu để quét thông tin BOM/POM)
            images = pdf2image.convert_from_bytes(pdf_bytes, first_page=1, last_page=3)
            
            # Khởi tạo Gemini Client (Lấy API Key từ Secrets của Streamlit hoặc môi trường)
            # Khuyến khích thiết lập st.secrets["GEMINI_API_KEY"] trên Streamlit Cloud
            client = genai.Client()
            
            # Cấu hình ép JSON Schema đầu ra chuyên nghiệp
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=TechpackExtractionOutput,
                temperature=0.1,
                system_instruction="Bạn là kỹ sư may mặc. Hãy trích xuất chính xác bảng BOM, POM và các linh kiện cắt từ hình ảnh Techpack."
            )
            
            # Chuyển đổi ảnh trang đầu thành bytes phát dữ liệu cho AI
            img_byte_arr = io.BytesIO()
            images[0].save(img_byte_arr, format='JPEG')
            jpeg_bytes = img_byte_arr.getvalue()
            
            # Gọi mô hình Gemini xử lý đa phương thức trực tiếp
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=[
                    types.Part.from_bytes(data=jpeg_bytes, mime_type='image/jpeg'),
                    "Hãy phân tích và bóc tách dữ liệu kỹ thuật từ trang tài liệu này."
                ],
                config=config
            )
            
            # Chuyển chuỗi text JSON nhận được thành Object Python để sử dụng
            final_json = json.loads(response.text)
            
            st.success("✅ Trích xuất dữ liệu Techpack thành công!")
            
            # Lưu dữ liệu vào session_state để truyền cho Module Hình học (Giai đoạn 2)
            st.session_state["techpack_data"] = final_json
            
            # Hiển thị cấu trúc JSON giàu dữ liệu ra màn hình để phòng IE/CAD kiểm tra
            st.json(final_json)
            
        except Exception as e:
            st.error(f"❌ Có lỗi xảy ra khi xử lý: {str(e)}")
