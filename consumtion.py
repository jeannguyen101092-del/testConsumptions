
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Test dự đoán định mức",
    page_icon="🧵",
    layout="wide"
)

st.title("🧵 DỰ ĐOÁN ĐỊNH MỨC VẢI – QUẦN SHORT")
st.caption(
    "Mô hình thử nghiệm: phân nhóm thông số, "
    "tính mức thay đổi có trọng số và hiệu chỉnh bằng K."
)

# =========================================================
# 1. CẤU HÌNH MÔ HÌNH THỬ NGHIỆM
# =========================================================

DEFAULT_K = 0.65

# Trọng số giữa 3 nhóm, tổng = 1.00
GROUP_WEIGHTS = {
    "Chiều dài": 0.35,
    "Chiều rộng thân quần": 0.45,
    "Độ sâu đáy": 0.20,
}

# Trọng số bên trong nhóm chiều rộng, tổng = 1.00
WIDTH_WEIGHTS = {
    "Waist - Vòng eo": 0.15,
    "Hip - Vòng mông": 0.35,
    "Thigh - Rộng đùi": 0.30,
    "Leg Opening - Rộng ống": 0.20,
}

SPEC_GROUPS = {
    "Chiều dài": [
        "Outseam - Dài quần ngoài",
    ],
    "Chiều rộng thân quần": [
        "Waist - Vòng eo",
        "Hip - Vòng mông",
        "Thigh - Rộng đùi",
        "Leg Opening - Rộng ống",
    ],
    "Độ sâu đáy": [
        "Front Rise - Cao đáy trước",
        "Back Rise - Cao đáy sau",
    ],
}

DEFAULTS = {
    "Outseam - Dài quần ngoài": ("14.750", "14.500"),
    "Waist - Vòng eo": ("16.500", "16.250"),
    "Hip - Vòng mông": ("21.000", "20.250"),
    "Thigh - Rộng đùi": ("14.250", "13.625"),
    "Leg Opening - Rộng ống": ("13.625", "13.375"),
    "Front Rise - Cao đáy trước": ("11.250", "12.125"),
    "Back Rise - Cao đáy sau": ("16.250", "16.000"),
}

# =========================================================
# 2. HÀM XỬ LÝ
# =========================================================

def parse_number(value):
    """Chấp nhận số thập phân dùng dấu chấm hoặc dấu phẩy."""
    value = str(value).strip().replace(" ", "")

    if not value:
        raise ValueError("Chưa nhập giá trị.")

    # Ví dụ: 14,750 -> 14.750
    if "," in value and "." not in value:
        value = value.replace(",", ".")
    elif "," in value and "." in value:
        # Ví dụ: 1,234.56 -> 1234.56
        if value.rfind(",") < value.rfind("."):
            value = value.replace(",", "")
        # Ví dụ: 1.234,56 -> 1234.56
        else:
            value = value.replace(".", "").replace(",", ".")

    return float(value)


def pct_change(old, new):
    if old == 0:
        raise ValueError("Thông số cũ không được bằng 0.")
    return (new - old) / old * 100


def weighted_average(values, weights):
    """values và weights dùng chung khóa."""
    total_weight = sum(weights.values())
    if total_weight == 0:
        raise ValueError("Tổng trọng số không được bằng 0.")

    return sum(
        values[key] * weights[key]
        for key in weights
    ) / total_weight


# =========================================================
# 3. THÔNG TIN MÃ HÀNG
# =========================================================

c1, c2, c3 = st.columns(3)

with c1:
    old_code = st.text_input("Mã hàng cũ", "R06-494141")

with c2:
    new_code = st.text_input("Mã hàng mới", "R06-494148")

with c3:
    old_dm = st.number_input(
        "ĐM cũ (yd/pcs)",
        min_value=0.0001,
        value=0.8240,
        step=0.0010,
        format="%.4f"
    )

st.divider()

# =========================================================
# 4. NHẬP THÔNG SỐ
# =========================================================

st.subheader("3. Nhập thông số cũ và mới")
st.caption(
    "Chỉ nhập thông số chính. Mã cũ và mã mới phải cùng đơn vị. "
    "Chi tiết nhỏ không tham gia tính."
)

old_values = {}
new_values = {}

for group_name, specs in SPEC_GROUPS.items():
    st.markdown(f"**{group_name}**")

    headers = st.columns([2, 1, 1])

    headers[0].markdown("Thông số")
    headers[1].markdown("Mã cũ")
    headers[2].markdown("Mã mới")

    for spec in specs:
        default_old, default_new = DEFAULTS[spec]
        cols = st.columns([2, 1, 1])

        cols[0].write(spec)

        old_text = cols[1].text_input(
            "Mã cũ",
            value=default_old,
            key=f"old_{spec}",
            label_visibility="collapsed"
        )

        new_text = cols[2].text_input(
            "Mã mới",
            value=default_new,
            key=f"new_{spec}",
            label_visibility="collapsed"
        )

        try:
            old_values[spec] = parse_number(old_text)
            new_values[spec] = parse_number(new_text)
        except ValueError:
            st.error(f"Giá trị không hợp lệ tại: {spec}")

    st.write("")

# =========================================================
# 5. HỆ SỐ VÀ TRỌNG SỐ CÓ THỂ CHỈNH
# =========================================================

with st.expander("⚙️ Cài đặt hệ số và trọng số", expanded=False):
    st.caption(
        "Các trọng số dưới đây là giả định để thử nghiệm, "
        "chưa được xác nhận bằng dữ liệu nhà máy."
    )

    K = st.number_input(
        "Hệ số K",
        min_value=0.0,
        max_value=3.0,
        value=DEFAULT_K,
        step=0.05,
        format="%.2f"
    )

    st.markdown("**Trọng số các nhóm**")

    w_length = st.number_input(
        "Chiều dài",
        0.0, 1.0, 0.35, 0.05,
        format="%.2f"
    )

    w_width = st.number_input(
        "Chiều rộng thân quần",
        0.0, 1.0, 0.45, 0.05,
        format="%.2f"
    )

    w_rise = st.number_input(
        "Độ sâu đáy",
        0.0, 1.0, 0.20, 0.05,
        format="%.2f"
    )

    st.markdown("**Trọng số trong nhóm chiều rộng**")

    ww_waist = st.number_input(
        "Waist",
        0.0, 1.0, 0.15, 0.05,
        format="%.2f"
    )

    ww_hip = st.number_input(
        "Hip",
        0.0, 1.0, 0.35, 0.05,
        format="%.2f"
    )

    ww_thigh = st.number_input(
        "Thigh",
        0.0, 1.0, 0.30, 0.05,
        format="%.2f"
    )

    ww_opening = st.number_input(
        "Leg Opening",
        0.0, 1.0, 0.20, 0.05,
        format="%.2f"
    )

# =========================================================
# 6. TÍNH TOÁN
# =========================================================

st.divider()

if st.button("🧮 TÍNH ĐỊNH MỨC DỰ ĐOÁN", type="primary"):
    try:
        if len(old_values) != 7 or len(new_values) != 7:
            raise ValueError("Vui lòng nhập đầy đủ 7 thông số.")

        changes = {
            spec: pct_change(old_values[spec], new_values[spec])
            for spec in old_values
        }

        width_weights = {
            "Waist - Vòng eo": ww_waist,
            "Hip - Vòng mông": ww_hip,
            "Thigh - Rộng đùi": ww_thigh,
            "Leg Opening - Rộng ống": ww_opening,
        }

        if sum(width_weights.values()) <= 0:
            raise ValueError("Tổng trọng số chiều rộng phải lớn hơn 0.")

        group_changes = {
            "Chiều dài": changes["Outseam - Dài quần ngoài"],

            "Chiều rộng thân quần": weighted_average(
                {
                    spec: changes[spec]
                    for spec in width_weights
                },
                width_weights
            ),

            "Độ sâu đáy": (
                changes["Front Rise - Cao đáy trước"]
                + changes["Back Rise - Cao đáy sau"]
            ) / 2,
        }

        group_weights = {
            "Chiều dài": w_length,
            "Chiều rộng thân quần": w_width,
            "Độ sâu đáy": w_rise,
        }

        if sum(group_weights.values()) <= 0:
            raise ValueError("Tổng trọng số nhóm phải lớn hơn 0.")

        avg_change = weighted_average(
            group_changes,
            group_weights
        )

        adjusted_change = avg_change * K
        predicted_dm = old_dm * (1 + adjusted_change / 100)

        st.subheader("4. Kết quả dự đoán")

        r1, r2, r3 = st.columns(3)

        r1.metric("ĐM cũ", f"{old_dm:.4f} yd/pcs")
        r2.metric("Thay đổi có trọng số", f"{avg_change:+.2f}%")
        r3.metric("Điều chỉnh sau K", f"{adjusted_change:+.2f}%")

        st.success(f"ĐM mới dự đoán: {predicted_dm:.4f} yd/pcs")

        st.markdown("**Chi tiết thay đổi từng thông số**")

        detail_rows = []

        for group_name, specs in SPEC_GROUPS.items():
            for spec in specs:
                detail_rows.append({
                    "Nhóm": group_name,
                    "Thông số": spec,
                    "Mã cũ": old_values[spec],
                    "Mã mới": new_values[spec],
                    "Thay đổi (%)": changes[spec],
                })

        df_detail = pd.DataFrame(detail_rows)
        st.dataframe(
            df_detail.style.format({
                "Mã cũ": "{:.3f}",
                "Mã mới": "{:.3f}",
                "Thay đổi (%)": "{:+.2f}%"
            }),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("**Mức thay đổi theo nhóm**")

        df_groups = pd.DataFrame([
            {
                "Nhóm": name,
                "Trọng số": group_weights[name],
                "Thay đổi nhóm (%)": group_changes[name],
                "Đóng góp vào tổng (%)":
                    group_changes[name]
                    * group_weights[name]
                    / sum(group_weights.values()),
            }
            for name in group_changes
        ])

        st.dataframe(
            df_groups.style.format({
                "Trọng số": "{:.2f}",
                "Thay đổi nhóm (%)": "{:+.2f}%",
                "Đóng góp vào tổng (%)": "{:+.2f}%"
            }),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("**5. So sánh định mức thực tế**")

        actual_text = st.text_input(
            "Nhập ĐM thực tế của mã mới (yd/pcs)",
            value="0.7390",
            key="actual_dm"
        )

        if st.button("So sánh với ĐM thực tế"):
            actual_dm = parse_number(actual_text)

            if actual_dm <= 0:
                st.error("ĐM thực tế phải lớn hơn 0.")
            else:
                error_pct = (
                    (predicted_dm - actual_dm)
                    / actual_dm
                    * 100
                )

                delta = predicted_dm - actual_dm

                a1, a2, a3 = st.columns(3)

                a1.metric(
                    "ĐM dự đoán",
                    f"{predicted_dm:.4f}"
                )

                a2.metric(
                    "ĐM thực tế",
                    f"{actual_dm:.4f}"
                )

                a3.metric(
                    "Sai lệch",
                    f"{error_pct:+.2f}%",
                    delta=f"{delta:+.4f} yd/pcs",
                    delta_color="inverse"
                )

                st.caption(
                    "Sai lệch (%) = (ĐM dự đoán - ĐM thực tế) "
                    "/ ĐM thực tế × 100."
                )

    except ValueError as exc:
        st.error(str(exc))

st.info(
    "Lưu ý: trọng số và K là giả định để kiểm thử. "
    "Mô hình chưa tính trực tiếp diện tích rập, khổ vải, "
    "hiệu suất giác hoặc hao hụt sản xuất."
)
