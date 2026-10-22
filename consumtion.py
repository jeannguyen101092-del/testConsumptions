
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Test định mức vải",
    page_icon="🧵",
    layout="wide"
)

st.title("🧵 TEST DỰ ĐOÁN ĐỊNH MỨC VẢI")
st.caption("So sánh thông số cơ bản của mã hàng cũ và mã hàng mới.")

st.info(
    "Cách tính: % chênh lệch trung bình của các thông số cơ bản "
    "→ áp dụng vào định mức cũ. Đây là mô hình thử nghiệm."
)

# =====================================================
# 1. THÔNG TIN MÃ HÀNG
# =====================================================
st.subheader("1. Thông tin mã hàng")

c1, c2 = st.columns(2)

with c1:
    old_style = st.text_input("Mã hàng cũ", "JEAN_OLD")
    old_dm = st.number_input(
        "Định mức vải cũ (yard/pcs)",
        min_value=0.001,
        value=1.800,
        step=0.01,
        format="%.4f"
    )

with c2:
    new_style = st.text_input("Mã hàng mới", "JEAN_NEW")
    new_dm_actual = st.number_input(
        "Định mức thực tế mã mới (nếu đã biết)",
        min_value=0.0,
        value=0.0,
        step=0.01,
        format="%.4f",
        help="Để 0 nếu chưa có định mức thực tế."
    )

# =====================================================
# 2. CHỌN NHÓM THÔNG SỐ CƠ BẢN
# =====================================================
st.subheader("2. Thông số cơ bản")

product_type = st.selectbox(
    "Loại sản phẩm",
    ["Quần dài / Jean", "Quần short", "Áo sơ mi", "T-shirt / Polo", "Jacket"]
)

# Chỉ các thông số chính được đưa vào phép tính
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

spec_names = spec_groups[product_type]

st.caption(
    "Nhập cùng đơn vị cho thông số cũ và mới. "
    "Không nhập thông số túi, passant, vị trí may hoặc chi tiết nhỏ."
)

# Dữ liệu mẫu được đổi theo loại sản phẩm
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

rows = []

for i, name in enumerate(spec_names):
    old_default, new_default = defaults[name]

    c1, c2, c3 = st.columns([2, 2, 2])

    c1.markdown(f"**{name}**")

    old_value = c2.number_input(
        "Mã cũ",
        min_value=0.0,
        value=float(old_default),
        key=f"old_{i}_{product_type}",
        format="%.3f"
    )

    new_value = c3.number_input(
        "Mã mới",
        min_value=0.0,
        value=float(new_default),
        key=f"new_{i}_{product_type}",
        format="%.3f"
    )

    rows.append({
        "Thông số": name,
        "Giá trị cũ": old_value,
        "Giá trị mới": new_value
    })

# =====================================================
# 3. TÙY CHỌN CÁCH TÍNH
# =====================================================
st.subheader("3. Phương pháp tính")

method = st.radio(
    "Cách tính phần trăm",
    [
        "Trung bình % chênh lệch có dấu (tăng +, giảm -)",
        "Trung bình % chênh lệch tuyệt đối (chỉ xem độ lớn)"
    ],
    index=0
)

st.caption(
    "Nên chọn cách có dấu nếu muốn phần tăng và giảm bù trừ nhau. "
    "Cách tuyệt đối không cho phép hai chiều triệt tiêu nhau."
)

# =====================================================
# 4. TÍNH KẾT QUẢ
# =====================================================
if st.button("🧮 TÍNH ĐỊNH MỨC MỚI", type="primary",
             use_container_width=True):

    detail = []
    valid_changes = []

    for row in rows:
        old = row["Giá trị cũ"]
        new = row["Giá trị mới"]

        if old <= 0 or new <= 0:
            change = None
            status = "Bỏ qua: thiếu số đo hợp lệ"
        else:
            change = (new - old) / old * 100
            valid_changes.append(change)
            status = "Đã tính"

        detail.append({
            "Thông số": row["Thông số"],
            "Mã cũ": old,
            "Mã mới": new,
            "Chênh lệch (%)": (
                round(change, 3) if change is not None else None
            ),
            "Trạng thái": status
        })

    if not valid_changes:
        st.error("Không có thông số hợp lệ để tính.")
    else:
        if "tuyệt đối" in method:
            avg_change = sum(abs(x) for x in valid_changes) / len(valid_changes)
        else:
            avg_change = sum(valid_changes) / len(valid_changes)

        predicted_dm = old_dm * (1 + avg_change / 100)

        st.divider()
        st.subheader("4. Kết quả dự đoán")

        c1, c2, c3 = st.columns(3)

        c1.metric("Định mức cũ", f"{old_dm:.4f} yd/pcs")
        c2.metric("% chênh lệch trung bình", f"{avg_change:+.2f}%")
        c3.metric("Định mức mới dự đoán", f"{predicted_dm:.4f} yd/pcs")

        st.write("**Bảng kiểm tra chênh lệch từng thông số**")
        st.dataframe(
            pd.DataFrame(detail),
            use_container_width=True,
            hide_index=True
        )

        st.write(f"**Số thông số được tính:** {len(valid_changes)}")

        if new_dm_actual > 0:
            error_pct = (
                (predicted_dm - new_dm_actual) / new_dm_actual * 100
            )

            st.subheader("5. So sánh với định mức thực tế")
            c1, c2, c3 = st.columns(3)

            c1.metric("ĐM dự đoán", f"{predicted_dm:.4f}")
            c2.metric("ĐM thực tế", f"{new_dm_actual:.4f}")
            c3.metric("Sai lệch dự đoán", f"{error_pct:+.2f}%")

            if abs(error_pct) <= 3:
                st.success("Sai lệch nằm trong ±3% ở lần kiểm tra này.")
            else:
                st.warning(
                    "Sai lệch vượt ±3%. Cần xem lại cách tính "
                    "hoặc các yếu tố cấu trúc và sơ đồ cắt."
                )

        st.warning(
            "Kết quả là ước tính thử nghiệm, không đảm bảo định mức "
            "thực tế thay đổi cùng tỷ lệ với thông số thành phẩm. "
            "Chưa tính khổ vải, hiệu suất marker, cấu trúc chi tiết "
            "hoặc thay đổi chất liệu."
        )
