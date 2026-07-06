import streamlit as st
import io
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional
import pdf2image

# ==============================================================================
# 1. ĐỊNH NGHĨA STRUCT PYDANTIC (ĐÃ CẤU HÌNH SỬA LỖI ADDITIONAL PROPERTIES)
# ==============================================================================
class MaterialItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    category: str = Field(description="Main Fabric, Pocketing, Fusing, Lining, etc.")
    description: str
    standard_width_inch: Optional[float] = None

class MeasurementItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    pom_code: str
    description: str
    values: Dict[str, float] = Field(description="Key: Size (ví dụ '30'), Value: Số đo thực tế")

class POMData(BaseModel):
    model_config = ConfigDict(extra="allow")
    size_run: List[str]
    measurements: List[MeasurementItem]

class ProductComponent(BaseModel):
    model_config = ConfigDict(extra="allow")
    component_name: str = Field(description="Ví dụ: Front Leg, Back Pocket, Belt")
    material_category: str
    cut_count_per_garment: int
    is_symmetrical: bool

class TechpackExtractionOutput(BaseModel):
    model_config = ConfigDict(extra="allow")
    style_number: str
    product_category: str
    base_size: str
    bill_of_materials: List[MaterialItem]
    point_of_measurements: POMData
    product_components: List[ProductComponent]


# ==============================================================================
# 2. HÀM CHUẨN HÓA SCHEMA DÀNH CHO GEMINI DEVELOPER API MODE
# ==============================================================================
def get_clean_schema(model) -> dict:
    """Bóc tách hoàn toàn từ khóa additionalProperties để tránh lỗi trên Developer API."""
    schema = model.model_json_schema()
    
    def remove_additional_properties(d):
        if isinstance(d, dict):
            d.pop('additionalProperties', None)
            for k, v in d.items():
                remove_additional_properties(v)
        elif isinstance(d, list):
            for item in d:
                remove_additional_properties(item)
                
    remove_additional_properties(schema)
    return schema


# ==============================================================================
# 3. GIAO DIỆN VÀ LOGIC ỨNG DỤNG STREAMLIT
# ==============================================================================
st.set_page_config(layout="wide")
st.title("AI FABRIC CONSUMPTION")

# Nơi uploader file tài liệu kỹ thuật
uploaded_file = st.file_uploader("TECHPACK UPLOADER & PROFILE SUMMARY", type=["pdf"])

if uploaded_file is not None:
    # Hiển thị trạng thái đang quét xử lý dữ liệu thông minh
    with st.spinner("🔄 AI Platform đang quét thông tin đa tầng tài liệu kỹ thuật Techpack..."):
        try:
            # Đọc dữ liệu nhị phân từ file PDF đã upload
            pdf_bytes = uploaded_file.read()
            
            # Chuyển đổi các trang PDF đầu tiên sang ảnh để mô hình Vision đọc dữ liệu
            images = pdf2image.convert_from_bytes(pdf_bytes, first_page=1, last_page=3)
            
            if not images:
                st.error("❌ Không thể chuyển đổi tệp PDF này thành hình ảnh.")
                st.stop()
            
            # Khởi tạo client kết nối SDK mới của Google
            # (Hệ thống sẽ tự nhận diện biến môi trường GEMINI_API_KEY)
            client = genai.Client()
            
            # Chuẩn bị cấu hình cấu trúc Schema sạch cho Gemini
            clean_json_schema = get_clean_schema(TechpackExtractionOutput)
            
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=clean_json_schema,
                temperature=0.1,  # Đặt mức thấp để đảm bảo độ chính xác dữ liệu thực tế
                system_instruction=(
                    "Bạn là một kỹ sư AI hàng đầu trong ngành may mặc. "
                    "Nhiệm vụ của bạn là đọc các hình ảnh tài liệu Techpack và trích xuất bảng dữ liệu một cách chính xác tuyệt đối. "
                    "Tuyệt đối không tự cấu trúc hoặc bịa ra các số liệu nếu tài liệu không đề cập."
                )
            )
            
            # Chuyển đổi dữ liệu ảnh trang đầu tiên sang bytes định dạng JPEG
            img_byte_arr = io.BytesIO()
            images.save(img_byte_arr, format='JPEG')
            jpeg_bytes = img_byte_arr.getvalue()
            
            # Gọi mô hình xử lý đa phương thức (Multimodal) với ID đã cập nhật ngắn gọn
            response = client.models.generate_content(
                model='gemini-1.5-flash', # Tên model viết chuẩn xác cho bộ SDK mới
                contents=[
                    types.Part.from_bytes(data=jpeg_bytes, mime_type='image/jpeg'),
                    "Hãy phân tích hình ảnh trang Techpack này và trích xuất BOM, POM, và các thành phần cấu tạo sản phẩm theo cấu trúc yêu cầu."
                ],
                config=config
            )
            
            # Parse chuỗi JSON nhận được từ AI thành kiểu cấu trúc Python Dictionary
            final_json = json.loads(response.text)
            
            st.success("✅ Trích xuất dữ liệu Techpack thành công!")
            
            # Lưu trữ dữ liệu vào session_state để tái sử dụng cho các module sau này
            st.session_state["techpack_data"] = final_json
            
            # Hiển thị trực quan cấu trúc cây JSON dữ liệu đã bóc tách lên giao diện web
            st.json(final_json)
            
        except Exception as e:
            st.error(f"❌ Có lỗi xảy ra khi xử lý hệ thống: {str(e)}")
