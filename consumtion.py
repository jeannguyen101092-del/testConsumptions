
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Test định mức vải",
    page_icon="🧵",
    layout="wide"
)

st.title("🧵 DỰ ĐOÁN ĐỊNH MỨC VẢI")
st.caption("So sánh thông số cơ bản và áp dụng hệ số tiêu hao theo dòng hàng.")

# =====================================================
# 1. HỆ SỐ MẶC ĐỊNH ĐỂ TEST
# Có thể thay đổi trực tiếp trên giao diện
# =====================================================
DEFAULT_K = {
    "Quần jean dài": 0.80,
    "Quần kaki / quần dài": 0.75,
    "Quần short": 0.65,
    "Áo sơ mi": 0.70,
    "T-shirt / Polo": 0.65,
    "Hoodie / Sweatshirt": 0.75,
    "Jacket": 0.80,
    "Váy / đầm": 0.75,
}

SPEC_GROUPS = {
    "Quần jean dài": [
        "Inseam - Dài giàng trong",
        "Outseam - Dài quần ngoài",
        "Waist - Vòng eo",
        "Hip - Vòng mông",
        "Thigh - Rộng đùi",
        "Knee - Rộng gối",
        "Leg Opening - Rộng ống",
        "Front Rise - Cao đáy trước",
        "Back Rise - Cao đáy sau",
    ],
    "Quần kaki / quần dài": [
        "Inseam - Dài giàng trong",
        "Outseam - Dài quần ngoài",
        "Waist - Vòng eo",
        "Hip - Vòng mông",
        "Thigh - Rộng đùi",
        "Knee - Rộng gối",
        "Leg Opening - Rộng ống",
        "Front Rise - Cao đáy trước",
        "Back Rise - Cao đáy sau",
    ],
    "Quần short": [
        "Outseam - Dài quần ngoài",
        "Waist - Vòng eo",
        "Hip - Vòng mông",
        "Thigh - Rộng đùi",
        "Leg Opening - Rộng ống",
        "Front Rise - Cao đáy trước",
        "Back Rise - Cao đáy sau",
    ],
    "Áo sơ mi": [
        "Body Length - Dài áo",
        "Chest - Rộng ngực",
        "Shoulder - Rộng vai",
        "Sleeve Length - Dài tay",
        "Hem Width - Rộng lai",
    ],
    "T-shirt / Polo": [
        "Body Length - Dài áo",
        "Chest - Rộng ngực",
        "Shoulder - Rộng vai",
        "Sleeve Length - Dài tay",
        "Hem Width - Rộng lai",
    ],
    "Hoodie / Sweatshirt": [
        "Body Length - Dài áo",
        "Chest - Rộng ngực",
        "Shoulder - Rộng vai",
        "Sleeve Length - Dài tay",
        "Hem Width - Rộng lai",
    ],
    "Jacket": [
        "Body Length - Dài áo",
        "Chest - Rộng ngực",
        "Shoulder - Rộng vai",
        "Sleeve Length - Dài tay",
        "Hem Width - Rộng lai",
    ],
    "Váy / đầm": [
        "Body Length - Dài sản phẩm",
        "Waist - Vòng eo",
        "Hip - Vòng mông",
        "Hem Width - Rộng lai",
    ],
}

DEFAULTS = {
    "Inseam - Dài giàng trong": (30.0, 30.6),
    "Outseam - Dài quần ngoài": (40.0, 40.5),
    "Waist - Vòng eo": (32.0, 32.0),
    "Hip - Vòng mông": (40.0, 38.8),
    "Thigh - Rộng đùi": (20.0, 22.0),
    "Knee - Rộng gối": (16.0, 16.0),
    "Leg Opening - Rộng ống": (14.0, 13.86),
    "Front Rise - Cao đáy trước": (11.0, 11.0),
    "Back Rise - Cao đáy sau": (15.0, 15.0),
    "Body Length - Dài áo": (28.0, 28.5),
    "Chest - Rộng ngực": (22.0, 22.5),
    "Shoulder - Rộng vai": (18.0, 18.0),
    "Sleeve Length - Dài tay": (25.0, 25.5),
    "Hem Width - Rộng lai": (22.0, 22.0),
    "Body Length - Dài sản phẩm": (40.0, 40.5),
}

# =====================================================
# 2. CHỌN DÒNG HÀNG VÀ HỆ SỐ
# =====================================================
st.subheader("1. Chọn dòng hàng")

product_type = st.selectbox(
    "Loại sản phẩm",
    list(DEFAULT_K.keys())
)

K = st.number_input(
    "Hệ số tiêu hao K (có thể chỉnh để test)",
    min_value=0.0,
    max_value=2.0,
    value=DEFAULT_K[product_type],
    step=0.05,
    format="%.2f",
    help="Hệ số giả định để thử nghiệm, chưa được xác thực bằng dữ liệu nhà máy."
)

# =====================================================
# 3. THÔNG TIN MÃ HÀNG
# =====================================================
st.subheader("2. Thông tin mã hàng")

c1, c2 = st.columns(2)

with c1:
    old_style = st.text_input("Mã hàng cũ", "JEAN_OLD")
    old_dm = st.number_input(
        "Định mức cũ (yard/pcs)",
        min_value=0.001,
        value=1.800,
        step=0.01,
        format="%.4f"
    )

with c2:
    new_style = st.text_input("Mã hàng mới", "JEAN_NEW")
    actual_dm = st.number_input(
        "Định mức thực tế mã mới (nếu biết)",
        min_value=0.0,
        value=0.0,
        step=0.01,
        format="%.4f"
    )

# =====================================================
# 4. THÔNG SỐ CƠ BẢN
# =====================================================
st.subheader("3. Nhập thông số cũ và mới")

st.caption(
    "Chỉ nhập thông số chính. Dùng cùng đơn vị cho mã cũ và mã mới. "
    "Chi tiết nhỏ không tham gia tính."
)

rows = []

for i, name in enumerate(SPEC_GROUPS[product_type]):
    old_default, new_default = DEFAULTS[name]

    c1, c2, c3 = st.columns([2, 1.5, 1.5])
    c1.write(name)

    old_value = c2.number_input(
        "Mã cũ",
        min_value=0.0,
        value=float(old_default),
        key=f"old_{product_type}_{i}",
        format="%.3f"
    )

    new_value = c3.number_input(
        "Mã mới",
        min_value=0.0,
        value=float(new_default),
        key=f"new_{product_type}_{i}",
        format="%.3f"
    )

    rows.append({
        "Thông số": name,
        "Mã cũ": old_value,
        "Mã mới": new_value
    })

# =====================================================
# 5. TÍNH ĐỊNH MỨC
# =====================================================
if st.button("🧮 TÍNH ĐỊNH MỨC MỚI", type="primary",
             use_container_width=True):

    details = []
    changes = []

    for row in rows:
        old = row["Mã cũ"]
        new = row["Mã mới"]

        if old <= 0:
            pct = None
            status = "Bỏ qua: số đo cũ không hợp lệ"
        else:
            pct = (new - old) / old * 100
            changes.append(pct)
            status = "Đã tính"

        details.append({
            "Thông số": row["Thông số"],
            "Mã cũ": old,
            "Mã mới": new,
            "Chênh lệch (%)": round(pct, 3) if pct is not None else None,
            "Trạng thái": status
        })

    if not changes:
        st.error("Không có thông số hợp lệ để tính.")
    else:
        # Trung bình % chênh lệch có dấu
        average_change = sum(changes) / len(changes)

        # Áp dụng hệ số dòng hàng
        adjusted_change = average_change * K

        # Tính định mức mới
        predicted_dm = old_dm * (1 + adjusted_change / 100)

        st.divider()
        st.subheader("4. Kết quả dự đoán")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("ĐM cũ", f"{old_dm:.4f} yd/pcs")
        c2.metric("Chênh lệch TS TB", f"{average_change:+.2f}%")
        c3.metric("Điều chỉnh sau hệ số K", f"{adjusted_change:+.2f}%")
        c4.metric("ĐM mới dự đoán", f"{predicted_dm:.4f} yd/pcs")

        st.write(f"**Mã cũ:** {old_style}")
        st.write(f"**Mã mới:** {new_style}")
        st.write(f"**Dòng hàng:** {product_type}")
        st.write(f"**Hệ số K đang áp dụng:** {K:.2f}")

        st.dataframe(
            pd.DataFrame(details),
            use_container_width=True,
            hide_index=True
        )

        if actual_dm > 0:
            error_pct = (predicted_dm - actual_dm) / actual_dm * 100

            st.subheader("5. So sánh định mức thực tế")

            c1, c2, c3 = st.columns(3)
            c1.metric("ĐM dự đoán", f"{predicted_dm:.4f}")
            c2.metric("ĐM thực tế", f"{actual_dm:.4f}")
            c3.metric("Sai lệch", f"{error_pct:+.2f}%")

        st.warning(
            "Hệ số K hiện tại là giả định để test nhanh, "
            "không phải hệ số đã được xác nhận của nhà máy. "
            "Kết quả chưa tính khổ vải, hiệu suất sơ đồ, chất liệu "
            "và thay đổi cấu trúc sản phẩm."
        )
