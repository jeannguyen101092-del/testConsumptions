
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Test hệ số tiêu hao",
    page_icon="🧵",
    layout="wide"
)

st.title("🧵 TEST ĐỊNH MỨC VẢI THEO HỆ SỐ THỰC TẾ")

st.write(
    "Hệ số K được ước lượng từ dữ liệu các cặp mã hàng lịch sử. "
    "Không tự gán hệ số cố định."
)

# =====================================================
# 1. CHỌN DÒNG HÀNG
# =====================================================
product_type = st.selectbox(
    "Dòng hàng đang kiểm tra",
    [
        "Quần jean dài",
        "Quần kaki / quần dài",
        "Quần short",
        "Áo sơ mi",
        "T-shirt / Polo",
        "Hoodie / Sweatshirt",
        "Jacket",
        "Váy / đầm"
    ]
)

# =====================================================
# 2. NHẬP CẶP MÃ LỊCH SỬ
# =====================================================
st.subheader("A. Dữ liệu lịch sử để học hệ số K")

st.caption(
    "Mỗi dòng là một cặp mã cùng dòng hàng. "
    "Nhập % chênh lệch thông số trung bình có dấu, "
    "ĐM cũ và ĐM mới thực tế."
)

initial_history = pd.DataFrame({
    "Ma_cu": ["", "", "", "", ""],
    "Ma_moi": ["", "", "", "", ""],
    "Chenh_lech_TS_pct": [None, None, None, None, None],
    "DM_cu": [None, None, None, None, None],
    "DM_moi_thuc_te": [None, None, None, None, None],
})

history = st.data_editor(
    initial_history,
    num_rows="dynamic",
    use_container_width=True,
    key="history_data",
    column_config={
        "Ma_cu": st.column_config.TextColumn("Mã cũ"),
        "Ma_moi": st.column_config.TextColumn("Mã mới"),
        "Chenh_lech_TS_pct": st.column_config.NumberColumn(
            "% chênh lệch TS TB",
            help="Ví dụ tăng 2% nhập 2; giảm 3% nhập -3"
        ),
        "DM_cu": st.column_config.NumberColumn(
            "ĐM cũ (yd/pcs)",
            min_value=0.0
        ),
        "DM_moi_thuc_te": st.column_config.NumberColumn(
            "ĐM mới thực tế (yd/pcs)",
            min_value=0.0
        )
    }
)

# =====================================================
# 3. TÍNH HỆ SỐ K TỪ LỊCH SỬ
# =====================================================
valid = history.dropna(
    subset=[
        "Chenh_lech_TS_pct",
        "DM_cu",
        "DM_moi_thuc_te"
    ]
).copy()

valid = valid[
    (valid["DM_cu"] > 0)
    & (valid["DM_moi_thuc_te"] > 0)
]

if len(valid) > 0:
    valid["Thay_doi_DM_pct"] = (
        (valid["DM_moi_thuc_te"] - valid["DM_cu"])
        / valid["DM_cu"] * 100
    )

    x = valid["Chenh_lech_TS_pct"].astype(float).to_numpy()
    y = valid["Thay_doi_DM_pct"].astype(float).to_numpy()

    denominator = float(np.sum(x ** 2))

    if denominator > 0:
        K = float(np.sum(x * y) / denominator)

        valid["Du_doan_pct"] = K * x
        valid["Sai_so_pct"] = (
            valid["Thay_doi_DM_pct"] - valid["Du_doan_pct"]
        )

        st.subheader("Kết quả học hệ số")

        c1, c2, c3 = st.columns(3)
        c1.metric("Dòng hàng", product_type)
        c2.metric("Số cặp dữ liệu", str(len(valid)))
        c3.metric("Hệ số K ước lượng", f"{K:.4f}")

        st.dataframe(
            valid[
                [
                    "Ma_cu",
                    "Ma_moi",
                    "Chenh_lech_TS_pct",
                    "Thay_doi_DM_pct",
                    "Du_doan_pct",
                    "Sai_so_pct"
                ]
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Ma_cu": "Mã cũ",
                "Ma_moi": "Mã mới",
                "Chenh_lech_TS_pct": "% chênh lệch TS",
                "Thay_doi_DM_pct": "% ĐM thực tế",
                "Du_doan_pct": "% ĐM theo K",
                "Sai_so_pct": "Sai số (điểm %)"
            }
        )

        if len(valid) < 5:
            st.warning(
                "Dữ liệu còn ít. K hiện tại chỉ để thử nghiệm; "
                "nên thu thập thêm các cặp mã tương đồng."
            )

        # Cảnh báo nếu hệ số bất thường
        if K < 0:
            st.warning(
                "K âm: dữ liệu đang cho thấy thông số tăng nhưng "
                "định mức có xu hướng giảm, hoặc ngược lại. "
                "Hãy kiểm tra cặp mã, khổ vải, cấu trúc và dữ liệu."
            )

    else:
        K = None
        st.warning(
            "Không thể học K vì tất cả % chênh lệch thông số "
            "đều bằng 0. Hãy nhập các cặp mã có thay đổi thông số."
        )
else:
    K = None
    st.info(
        "Chưa có dữ liệu lịch sử hợp lệ. Nhập ít nhất một cặp mã "
        "có % chênh lệch thông số khác 0 và đủ hai định mức thực tế."
    )

# =====================================================
# 4. DỰ ĐOÁN MÃ HÀNG MỚI
# =====================================================
st.divider()
st.subheader("B. Dự đoán định mức mã hàng cần kiểm tra")

c1, c2 = st.columns(2)

with c1:
    target_old_style = st.text_input("Mã tham chiếu", "JEAN_OLD")
    target_old_dm = st.number_input(
        "ĐM thực tế mã tham chiếu (yd/pcs)",
        min_value=0.001,
        value=1.800,
        step=0.01,
        format="%.4f"
    )

with c2:
    target_new_style = st.text_input("Mã cần dự đoán", "JEAN_NEW")
    target_actual_dm = st.number_input(
        "ĐM thực tế mã mới (nếu đã biết)",
        min_value=0.0,
        value=0.0,
        step=0.01,
        format="%.4f"
    )

st.markdown("**Nhập thông số cơ bản của hai mã**")

spec_groups = {
    "Quần jean dài": [
        "Inseam - Dài giàng trong",
        "Outseam - Dài quần ngoài",
        "Waist - Vòng eo",
        "Hip - Vòng mông",
        "Thigh - Rộng đùi",
        "Knee - Rộng gối",
        "Leg Opening - Rộng ống",
        "Front Rise - Cao đáy trước",
        "Back Rise - Cao đáy sau"
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
        "Back Rise - Cao đáy sau"
    ],
    "Quần short": [
        "Outseam - Dài quần ngoài",
        "Waist - Vòng eo",
        "Hip - Vòng mông",
        "Thigh - Rộng đùi",
        "Leg Opening - Rộng ống",
        "Front Rise - Cao đáy trước",
        "Back Rise - Cao đáy sau"
    ],
    "Áo sơ mi": [
        "Body Length - Dài áo",
        "Chest - Rộng ngực",
        "Shoulder - Rộng vai",
        "Sleeve Length - Dài tay",
        "Hem Width - Rộng lai"
    ],
    "T-shirt / Polo": [
        "Body Length - Dài áo",
        "Chest - Rộng ngực",
        "Shoulder - Rộng vai",
        "Sleeve Length - Dài tay",
        "Hem Width - Rộng lai"
    ],
    "Hoodie / Sweatshirt": [
        "Body Length - Dài áo",
        "Chest - Rộng ngực",
        "Shoulder - Rộng vai",
        "Sleeve Length - Dài tay",
        "Hem Width - Rộng lai"
    ],
    "Jacket": [
        "Body Length - Dài áo",
        "Chest - Rộng ngực",
        "Shoulder - Rộng vai",
        "Sleeve Length - Dài tay",
        "Hem Width - Rộng lai"
    ],
    "Váy / đầm": [
        "Body Length - Dài sản phẩm",
        "Waist - Vòng eo",
        "Hip - Vòng mông",
        "Hem Width - Rộng lai"
    ]
}

spec_defaults = {
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
    "Body Length - Dài sản phẩm": (40.0, 40.5)
}

target_specs = []

for i, name in enumerate(spec_groups[product_type]):
    old_default, new_default = spec_defaults[name]

    c1, c2, c3 = st.columns([2, 1.5, 1.5])
    c1.write(name)

    old_value = c2.number_input(
        "Mã cũ",
        min_value=0.0,
        value=float(old_default),
        key=f"target_old_{product_type}_{i}",
        format="%.3f"
    )

    new_value = c3.number_input(
        "Mã mới",
        min_value=0.0,
        value=float(new_default),
        key=f"target_new_{product_type}_{i}",
        format="%.3f"
    )

    target_specs.append({
        "Thông số": name,
        "Cũ": old_value,
        "Mới": new_value
    })

if st.button(
    "TÍNH ĐỊNH MỨC THEO K ĐÃ HỌC",
    type="primary",
    use_container_width=True
):
    if K is None:
        st.error(
            "Chưa tính được K. Hãy nhập dữ liệu lịch sử hợp lệ ở phần A."
        )
    else:
        changes = []
        target_details = []

        for item in target_specs:
            old = item["Cũ"]
            new = item["Mới"]

            if old <= 0:
                pct = None
                status = "Bỏ qua: số đo cũ không hợp lệ"
            else:
                pct = (new - old) / old * 100
                changes.append(pct)
                status = "Đã tính"

            target_details.append({
                "Thông số": item["Thông số"],
                "Mã cũ": old,
                "Mã mới": new,
                "Chênh lệch (%)": (
                    round(pct, 3) if pct is not None else None
                ),
                "Trạng thái": status
            })

        if not changes:
            st.error("Không có thông số hợp lệ để tính.")
        else:
            avg_change = sum(changes) / len(changes)
            adjusted_change = avg_change * K
            predicted_dm = target_old_dm * (
                1 + adjusted_change / 100
            )

            st.subheader("Kết quả dự đoán")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("ĐM cũ", f"{target_old_dm:.4f}")
            c2.metric("Chênh lệch TS TB", f"{avg_change:+.2f}%")
            c3.metric("K đã học", f"{K:.4f}")
            c4.metric("ĐM mới dự đoán", f"{predicted_dm:.4f}")

            st.write(
                f"% điều chỉnh ĐM sau khi nhân K: "
                f"**{adjusted_change:+.2f}%**"
            )

            st.dataframe(
                pd.DataFrame(target_details),
                use_container_width=True,
                hide_index=True
            )

            if target_actual_dm > 0:
                error = (
                    (predicted_dm - target_actual_dm)
                    / target_actual_dm * 100
                )
                st.metric(
                    "Sai lệch so với ĐM thực tế",
                    f"{error:+.2f}%"
                )

            st.warning(
                "K chỉ đáng tin khi các cặp mã lịch sử cùng dòng hàng "
                "và tương đồng về chất liệu, khổ vải, cấu trúc và cách "
                "tính định mức. Công thức hiện tại chỉ học một hệ số "
                "từ % chênh lệch trung bình, chưa mô hình hóa từng "
                "thông số riêng biệt."
            )
