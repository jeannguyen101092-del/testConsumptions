import os
from urllib.parse import urlparse

import pandas as pd
import requests
import streamlit as st

APP_BUILD_ID = "GTAS-PATTERN-ONLY-20261022-D"
DEFAULT_BASE_URL = "https://cms.ppj-international.com"
PATTERN_ENDPOINT = "/items/PATTERN"  # Giai đoạn 1: CHỈ gọi collection này

st.set_page_config(
    page_title="PPJ Techpack AI - GTAS PATTERN",
    page_icon="🧵",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.block-container {padding-top: 1.3rem; padding-bottom: 2rem;}
.main-title {font-size: 1.65rem; font-weight: 750; color: #17365D; margin-bottom: .2rem;}
.section-title {background:#17365D;color:white;padding: .65rem .9rem;border-radius:7px;font-weight:700;margin:1rem 0 .6rem 0;}
</style>
""", unsafe_allow_html=True)


def config_value(name, fallback=""):
    try:
        value = st.secrets.get(name, None)
        if value is not None and str(value).strip():
            return str(value).strip()
    except Exception:
        pass
    value = os.getenv(name, "").strip()
    return value or str(fallback or "").strip()


base_default = config_value("GTAS_API_URL", DEFAULT_BASE_URL).rstrip("/")
token_default = config_value("GTAS_TOKEN", "")

st.markdown('<div class="main-title">🧵 PPJ Techpack AI — Kết nối GTAS PATTERN</div>', unsafe_allow_html=True)
st.caption(f"Giai đoạn 1 — chỉ đọc /items/PATTERN; không gọi Styles Lib, BOM, POM hoặc endpoint khác. | Build: {APP_BUILD_ID}")
st.info("Mục tiêu bước này là xác nhận ứng dụng đang chạy có kết nối được đúng API PATTERN hay không. Lỗi TLS sẽ được báo riêng; không tắt xác minh SSL.")

with st.sidebar:
    st.markdown("### Cấu hình kết nối")
    base_url_input = st.text_input("GTAS API host", value=base_default, help="Chỉ nhập host, ví dụ https://cms.ppj-international.com")
    token_input = st.text_input("GTAS token (nếu IT cấp)", value=token_default, type="password")
    st.caption("Endpoint được khóa cố định trong code: /items/PATTERN")

left, right = st.columns([1, 1])
with left:
    limit = st.selectbox("Số bản ghi", [1, 10, 25, 50, 100], index=1)
with right:
    offset = st.number_input("Bỏ qua bản ghi đầu", min_value=0, value=0, step=10)
keyword = st.text_input("Từ khóa tìm kiếm (không bắt buộc)", value="", placeholder="Nhập mã hàng hoặc từ khóa nếu API hỗ trợ search")

if st.button("🔌 KẾT NỐI VÀ ĐỌC PATTERN", type="primary", use_container_width=True):
    base_url = (base_url_input or "").strip().rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        st.error("Host không hợp lệ. Nhập dạng https://cms.ppj-international.com")
    elif parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        st.error("Chỉ nhập host, không nhập endpoint hoặc query ở ô GTAS API host.")
    else:
        # Only request made by this app in this phase:
        # GET https://cms.ppj-international.com/items/PATTERN?limit=...&offset=...
        url = base_url + PATTERN_ENDPOINT
        params = {"limit": int(limit), "offset": int(offset)}
        if keyword.strip():
            params["search"] = keyword.strip()
        headers = {"Accept": "application/json"}
        if token_input.strip():
            headers["Authorization"] = f"Bearer {token_input.strip()}"
        st.markdown('<div class="section-title">Thông tin request thực tế</div>', unsafe_allow_html=True)
        st.code(requests.Request("GET", url, params=params).prepare().url, language="text")
        try:
            with st.spinner("Đang gọi GTAS PATTERN..."):
                response = requests.get(url, params=params, headers=headers, timeout=(8, 30))
            st.write(f"**HTTP status:** {response.status_code}")
            st.write(f"**URL cuối cùng:** `{response.url}`")
            if response.status_code != 200:
                st.error(f"GTAS trả HTTP {response.status_code}.")
                st.code(response.text[:3000] or "Phản hồi rỗng", language="text")
                if response.status_code in (401, 403):
                    st.warning("Máy chủ đã phản hồi nhưng từ chối quyền. Nhờ IT xác nhận quyền đọc collection PATTERN và token.")
                elif response.status_code == 404:
                    st.warning("Máy chủ đã phản hồi nhưng không tìm thấy endpoint. Xác nhận collection /items/PATTERN với IT.")
            else:
                try:
                    payload = response.json()
                except ValueError:
                    st.error("HTTP 200 nhưng nội dung trả về không phải JSON.")
                    st.code(response.text[:3000], language="text")
                else:
                    records = payload.get("data", payload) if isinstance(payload, dict) else payload
                    if isinstance(records, dict):
                        records = [records]
                    if not isinstance(records, list):
                        records = []
                    records = [r for r in records if isinstance(r, dict)]
                    st.success(f"Kết nối thành công — HTTP 200. Nhận được {len(records)} bản ghi PATTERN trong lượt này.")
                    st.session_state["pattern_records_phase1"] = records
                    st.session_state["pattern_url_phase1"] = response.url
                    if records:
                        df = pd.json_normalize(records, sep=".")
                        st.markdown('<div class="section-title">Bảng dữ liệu PATTERN</div>', unsafe_allow_html=True)
                        st.caption(f"Số trường nhận được: {len(df.columns)}. Các trường hiển thị là dữ liệu API trả về, chưa tự suy đoán ý nghĩa trường.")
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        st.download_button(
                            "⬇️ Tải dữ liệu PATTERN dạng CSV",
                            data=df.to_csv(index=False).encode("utf-8-sig"),
                            file_name="GTAS_PATTERN.csv",
                            mime="text/csv",
                            use_container_width=True,
                        )
                        with st.expander("Xem JSON gốc", expanded=False):
                            st.json(records[:20])
                    else:
                        st.warning("API kết nối thành công nhưng lượt truy vấn không có bản ghi. Thử bỏ từ khóa hoặc đặt Bỏ qua bản ghi đầu = 0.")
        except requests.exceptions.SSLError as exc:
            st.error("Lỗi TLS/SSL: ứng dụng không hoàn tất được bắt tay HTTPS nên chưa nhận HTTP status từ GTAS.")
            st.write("**Endpoint đã gọi:**")
            st.code(url, language="text")
            st.write("**Chi tiết lỗi:**")
            st.code(str(exc), language="text")
            st.warning("Nếu mở URL được trong trình duyệt công ty nhưng app vẫn gặp lỗi này, cần kiểm tra môi trường chạy Streamlit, proxy/firewall hoặc cấu hình TLS của máy chủ. Không nên dùng verify=False để né lỗi.")
        except requests.exceptions.Timeout as exc:
            st.error("Kết nối bị timeout — app chưa nhận được phản hồi trong thời gian chờ.")
            st.code(str(exc), language="text")
        except requests.exceptions.RequestException as exc:
            st.error("Lỗi mạng khi gọi GTAS — chưa nhận được HTTP status.")
            st.code(str(exc), language="text")

if st.session_state.get("pattern_records_phase1"):
    st.caption(f"Dữ liệu PATTERN đã nhận trong phiên này: {len(st.session_state['pattern_records_phase1'])} bản ghi. URL: {st.session_state.get('pattern_url_phase1', base_default + PATTERN_ENDPOINT)}")

st.markdown("---")
st.caption("Build D chỉ có một lệnh gọi API: GET /items/PATTERN. Các chức năng Styles Lib, BOM, POM, tải ảnh và so sánh chưa được bật trong giai đoạn kiểm tra kết nối.")
