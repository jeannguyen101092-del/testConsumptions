
import streamlit as st

st.set_page_config(
    page_title="Test dự đoán định mức",
    page_icon="🧵",
    layout="wide"
)

st.title("🧵 TEST DỰ ĐOÁN ĐỊNH MỨC VẢI")
st.caption("So sánh thông số mã hàng cũ và mới để ước tính định mức.")

st.info(
    "Công thức thử nghiệm: ĐM mới = ĐM cũ × "
    "(1 + tổng tỷ lệ chênh lệch thông số có trọng số)."
)

# =====================================================
# 1. ĐỊNH MỨC MÃ HÀNG CŨ
# =====================================================
st.subheader("1. Dữ liệu mã hàng cũ")

col1, col2 = st.columns(2)

with col1:
    old_style = st.text_input("Mã hàng cũ", "STYLE_OLD")
    old_dm = st.number_input(
        "Định mức vải cũ (yard/pcs)",
        min_value=0.001,
        value=1.800,
        step=0.01,
        format="%.4f"
    )

with col2:
    new_style = st.text_input("Mã hàng mới", "STYLE_NEW")
    fabric_width_old = st.number_input(
        "Khổ vải mã cũ (inch)",
        min_value=1.0,
        value=58.0,
        step=1.0
    )

# =====================================================
# 2. SO SÁNH THÔNG SỐ
# =====================================================
st.subheader("2. Nhập thông số kỹ thuật")

st.caption(
    "Ví dụ bên dưới dành cho quần. Có thể đổi tên chỉ tiêu "
    "và trọng số theo loại sản phẩm."
)

specs = [
    ("Vòng eo", 80.0, 84.0, 0.20),
    ("Vòng mông", 100.0, 104.0, 0.40),
    ("Dài quần", 100.0, 102.0, 0.25),
    ("Rộng ống", 20.0, 21.0, 0.15),
]

header = st.columns([2, 2, 2, 2])
header[0].markdown("**Thông số**")
header[1].markdown("**Mã cũ**")
header[2].markdown("**Mã mới**")
header[3].markdown("**Trọng số (%)**")

values = []

for i, (name, old_default, new_default, weight_default) in enumerate(specs):
    c1, c2, c3, c4 = st.columns([2, 2, 2, 2])

    c1.write(name)

    old_value = c2.number_input(
        f"Cũ - {name}",
        min_value=0.0,
        value=float(old_default),
        key=f"old_{i}",
        label_visibility="collapsed"
    )

    new_value = c3.number_input(
        f"Mới - {name}",
        min_value=0.0,
        value=float(new_default),
        key=f"new_{i}",
        label_visibility="collapsed"
    )

    weight = c4.number_input(
        f"Trọng số - {name}",
        min_value=0.0,
        max_value=100.0,
        value=float(weight_default * 100),
        step=5.0,
        key=f"weight_{i}",
        label_visibility="collapsed"
    )

    values.append({
        "name": name,
        "old": old_value,
        "new": new_value,
        "weight": weight
    })

fabric_width_new = st.number_input(
    "Khổ vải mã mới (inch)",
    min_value=1.0,
    value=58.0,
    step=1.0
)

# =====================================================
# 3. TÍNH TOÁN
# =====================================================
if st.button("🧮 TÍNH ĐỊNH MỨC MỚI", type="primary",
             use_container_width=True):

    total_weight = sum(x["weight"] for x in values)

    if total_weight <= 0:
        st.error("Tổng trọng số phải lớn hơn 0.")

    elif any(x["old"] <= 0 for x in values):
        st.error("Thông số mã cũ phải lớn hơn 0.")

    else:
        # Tính tỷ lệ chênh lệch từng thông số
        weighted_change = 0.0
        details = []

        for x in values:
            change = (x["new"] - x["old"]) / x["old"]

            # Chuẩn hóa trọng số để tổng bằng 100%
            normalized_weight = x["weight"] / total_weight

            contribution = change * normalized_weight
            weighted_change += contribution

            details.append({
                "Thông số": x["name"],
                "Mã cũ": x["old"],
                "Mã mới": x["new"],
                "Chênh lệch (%)": change * 100,
                "Trọng số chuẩn hóa (%)": normalized_weight * 100,
                "Mức ảnh hưởng (%)": contribution * 100
            })

        # Hiệu chỉnh khổ vải theo giả định đơn giản:
        # khổ mới hẹp hơn thì ĐM tăng tỷ lệ nghịch.
        width_factor = fabric_width_old / fabric_width_new

        # Công thức ước tính thử nghiệm
        predicted_dm = old_dm * (1 + weighted_change) * width_factor

        dm_change = predicted_dm - old_dm
        dm_change_percent = dm_change / old_dm * 100

        st.divider()
        st.subheader("3. Kết quả dự đoán")

        c1, c2, c3 = st.columns(3)

        c1.metric("Định mức cũ", f"{old_dm:.4f} yd/pcs")
        c2.metric("Định mức mới dự đoán", f"{predicted_dm:.4f} yd/pcs")
        c3.metric("Chênh lệch", f"{dm_change:+.4f} yd/pcs",
                  f"{dm_change_percent:+.2f}%")

        st.write("**Chi tiết mức ảnh hưởng của từng thông số:**")
        st.dataframe(
            details,
            use_container_width=True,
            hide_index=True
        )

        st.write("**Thông tin kiểm tra:**")
        st.write(f"- Mã cũ: `{old_style}`")
        st.write(f"- Mã mới: `{new_style}`")
        st.write(f"- Chênh lệch thông số có trọng số: "
                 f"{weighted_change * 100:+.2f}%")
        st.write(f"- Hệ số hiệu chỉnh khổ vải giả định: "
                 f"{width_factor:.4f}")

        st.warning(
            "Đây là mô hình thử nghiệm, chưa phải công thức ĐM sản xuất. "
            "Các thông số không nhất thiết ảnh hưởng tuyến tính đến lượng "
            "vải; khổ vải cũng không thể hiệu chỉnh chính xác chỉ bằng "
            "tỷ lệ nghịch trong mọi trường hợp. Cần đối chiếu với marker "
            "và định mức thực tế trước khi sử dụng."
        )
