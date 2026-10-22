
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Test định mức vải",
    page_icon="🧵",
    layout="wide"
)

st.title("🧵 TEST DỰ ĐOÁN ĐỊNH MỨC VẢI")
st.write(
    "Công thức: Trung bình % chênh lệch có dấu "
    "(tăng +, giảm -)."
)

st.info(
    "Chỉ tính thông số thành phẩm cơ bản. "
    "Mỗi thông số có trọng số ngang nhau. "
    "Không tính chi tiết nhỏ như vị trí túi, passant, đường may."
)

# =====================================================
# 1. THÔNG TIN MÃ HÀNG
# =====================================================
st.subheader("1. Thông tin mã hàng")

col1, col2 = st.columns(2)

with col1:
    old_style = st.text_input("Mã hàng cũ", "JEAN_OLD")
    old_dm = st.number_input(
        "Định mức cũ (yard/pcs)",
        min_value=0.001,
        value=1.800,
        step=0.01,
        format="%.4f"
    )

with col2:
    new_style = st.text_input("Mã hàng mới", "JEAN_NEW")
    actual_dm = st.number_input(
        "Định mức thực tế mã mới (nếu có)",
        min_value=0.0,
        value=0.0,
        step=0.01,
        format="%.4f",
        help="Nhập 0 nếu chưa biết định mức thực tế."
    )

# =====================================================
# 2. CHỌN LOẠI SẢN PHẨM
# =====================================================
st.subheader("2. Chọn loại sản phẩm")

product_type = st.selectbox(
    "Loại sản phẩm",
    [
        "Quần dài / Jean",
        "Quần short",
        "Áo sơ mi",
        "T-shirt / Polo",
        "Jacket"
    ]
)

spec_groups = {
    "Quần dài / Jean": [
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
    "Jacket": [
        "Body Length - Dài áo",
        "Chest - Rộng ngực",
        "Shoulder - Rộng vai",
        "Sleeve Length - Dài tay",
        "Hem Width - Rộng lai",
    ],
}

# Số liệu mẫu để test nhanh
defaults = {
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
}

spec_names = spec_groups[product_type]

st.caption(
    "Nhập thông số cũ và mới cùng đơn vị. "
    "Thông số cũ phải lớn hơn 0 mới tính được % chênh lệch."
)

rows = []

for i, name in enumerate(spec_names):
    old_default, new_default = defaults[name]

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
# 3. TÍNH ĐỊNH MỨC
# =====================================================
if st.button(
    "🧮 TÍNH ĐỊNH MỨC MỚI",
    type="primary",
    use_container_width=True
):
    details = []
    valid_changes = []

    for row in rows:
        old = row["Mã cũ"]
        new = row["Mã mới"]

        if old <= 0:
            details.append({
                "Thông số": row["Thông số"],
                "Mã cũ": old,
                "Mã mới": new,
                "Chênh lệch (%)": None,
                "Trạng thái": "Bỏ qua: số đo cũ không hợp lệ"
            })
            continue

        # Công thức chênh lệch có dấu
        change_pct = (new - old) / old * 100

        valid_changes.append(change_pct)

        details.append({
            "Thông số": row["Thông số"],
            "Mã cũ": old,
            "Mã mới": new,
            "Chênh lệch (%)": round(change_pct, 3),
            "Trạng thái": "Đã tính"
        })

    if not valid_changes:
        st.error("Không có thông số hợp lệ để tính.")
    else:
        # Trung bình cộng có dấu: tăng dương, giảm âm
        average_change_pct = sum(valid_changes) / len(valid_changes)

        # ĐM mới = ĐM cũ × (1 + % trung bình)
        predicted_dm = old_dm * (1 + average_change_pct / 100)

        st.divider()
        st.subheader("3. Kết quả")

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Định mức cũ",
            f"{old_dm:.4f} yd/pcs"
        )

        c2.metric(
            "% chênh lệch trung bình",
            f"{average_change_pct:+.2f}%"
        )

        c3.metric(
            "Định mức mới dự đoán",
            f"{predicted_dm:.4f} yd/pcs"
        )

        st.write("### Chi tiết chênh lệch từng thông số")

        st.dataframe(
            pd.DataFrame(details),
            use_container_width=True,
            hide_index=True
        )

        st.write(f"**Mã hàng cũ:** {old_style}")
        st.write(f"**Mã hàng mới:** {new_style}")
        st.write(f"**Số thông số được tính:** {len(valid_changes)}")

        if actual_dm > 0:
            error_pct = (
                (predicted_dm - actual_dm) / actual_dm * 100
            )

            st.subheader("4. Đối chiếu định mức thực tế")

            c1, c2, c3 = st.columns(3)

            c1.metric("ĐM dự đoán", f"{predicted_dm:.4f}")
            c2.metric("ĐM thực tế", f"{actual_dm:.4f}")
            c3.metric("Sai lệch", f"{error_pct:+.2f}%")

        st.warning(
            "Đây là công thức thử nghiệm: giả định định mức thay đổi "
            "theo trung bình % chênh lệch thông số cơ bản. "
            "Chưa tính khổ vải, hiệu suất sơ đồ, chất liệu hoặc thay đổi "
            "cấu trúc sản phẩm. Cần kiểm chứng bằng định mức thực tế."
        )
