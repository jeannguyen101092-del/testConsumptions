
import requests
import streamlit as st

BASE_URL = "https://cms.ppj-international.com"


def get_headers():
    """Đọc token từ Streamlit Secrets."""
    token = st.secrets.get("GTAS_API_TOKEN", "")

    if not token:
        raise ValueError(
            "Chưa cấu hình GTAS_API_TOKEN trong Streamlit Secrets."
        )

    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


def get_styles(search=None, filters=None, limit=20):
    """
    Lấy danh sách style từ CMS PPJ.
    filters: các điều kiện lọc theo cấu trúc API hỗ trợ.
    """
    url = f"{BASE_URL}/items/stylepatternpkt"

    params = {"limit": limit}

    if search:
        params["search"] = search

    if filters:
        params.update(filters)

    try:
        response = requests.get(
            url,
            headers=get_headers(),
            params=params,
            timeout=30,
        )

        if response.status_code == 401:
            return {
                "ok": False,
                "error": "401: Token thiếu, sai hoặc đã hết hạn."
            }

        if response.status_code == 403:
            return {
                "ok": False,
                "error": (
                    "403: Tài khoản chưa có quyền đọc collection "
                    "stylepatternpkt, hoặc quyền truy cập bị giới hạn."
                )
            }

        response.raise_for_status()

        return {
            "ok": True,
            "data": response.json()
        }

    except requests.RequestException as exc:
        return {
            "ok": False,
            "error": f"Lỗi kết nối API: {exc}"
        }


def render_style_search():
    st.subheader("Tra cứu mã hàng trên CMS PPJ")

    keyword = st.text_input(
        "Nhập mã hàng hoặc từ khóa",
        placeholder="Nhập style code..."
    )

    if st.button("Tìm mã hàng"):
        with st.spinner("Đang truy vấn CMS..."):
            result = get_styles(search=keyword)

        if result["ok"]:
            payload = result["data"]
            rows = payload.get("data", [])

            st.success(f"Nhận được {len(rows)} bản ghi.")
            st.json(rows)
        else:
            st.error(result["error"])
