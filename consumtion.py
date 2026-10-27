import streamlit as st
import pandas as pd

st.set_page_config(page_title="Test dự đoán định mức vải", page_icon="🧵", layout="wide")

# =========================================================
# 1. DANH MỤC DÒNG HÀNG - CHỌN ĐƯỢC TẤT CẢ CÁC DÒNG
# =========================================================
CATEGORIES = {
    "Quần short": {
        "K": 2.00,
        "specs": [
            ("Outseam - Dài quần ngoài", "length"),
            ("Waist - Vòng eo", "width"),
            ("Hip - Vòng mông", "width"),
            ("Thigh - Rộng đùi", "width"),
            ("Leg Opening - Rộng ống", "width"),
            ("Front Rise - Cao đáy trước", "rise"),
            ("Back Rise - Cao đáy sau", "rise"),
        ],
        "defaults": {
            "Outseam - Dài quần ngoài": (14.750, 14.500),
            "Waist - Vòng eo": (16.500, 16.250),
            "Hip - Vòng mông": (21.000, 20.250),
            "Thigh - Rộng đùi": (14.250, 13.625),
            "Leg Opening - Rộng ống": (13.625, 13.375),
            "Front Rise - Cao đáy trước": (11.250, 12.125),
            "Back Rise - Cao đáy sau": (16.250, 16.000),
        },
    },
    "Quần jean dài": {
        "K": 0.75,
        "specs": [
            ("Outseam - Dài quần ngoài", "length"),
            ("Inseam - Dài trong", "length"),
            ("Waist - Vòng eo", "width"),
            ("Hip - Vòng mông", "width"),
            ("Thigh - Rộng đùi", "width"),
            ("Knee - Rộng gối", "width"),
            ("Leg Opening - Rộng ống", "width"),
            ("Front Rise - Cao đáy trước", "rise"),
            ("Back Rise - Cao đáy sau", "rise"),
        ],
        "defaults": {},
    },
    "Quần kaki / quần dài": {
        "K": 0.75,
        "specs": [
            ("Outseam - Dài quần ngoài", "length"),
            ("Inseam - Dài trong", "length"),
            ("Waist - Vòng eo", "width"),
            ("Hip - Vòng mông", "width"),
            ("Thigh - Rộng đùi", "width"),
            ("Knee - Rộng gối", "width"),
            ("Leg Opening - Rộng ống", "width"),
            ("Front Rise - Cao đáy trước", "rise"),
            ("Back Rise - Cao đáy sau", "rise"),
        ],
        "defaults": {},
    },
    "Áo sơ mi": {
        "K": 0.75,
        "specs": [
            ("Body Length - Dài áo", "length"),
            ("Chest - Vòng ngực", "width"),
            ("Shoulder - Ngang vai", "width"),
            ("Sleeve Length - Dài tay", "length"),
            ("Hem Width - Rộng lai", "width"),
        ],
        "defaults": {},
    },
    "T-shirt / Polo": {
        "K": 0.75,
        "specs": [
            ("Body Length - Dài áo", "length"),
            ("Chest - Vòng ngực", "width"),
            ("Shoulder - Ngang vai", "width"),
            ("Sleeve Length - Dài tay", "length"),
            ("Hem Width - Rộng lai", "width"),
        ],
        "defaults": {},
    },
    "Hoodie / Sweatshirt": {
        "K": 0.75,
        "specs": [
            ("Body Length - Dài áo", "length"),
            ("Chest - Vòng ngực", "width"),
            ("Shoulder - Ngang vai", "width"),
            ("Sleeve Length - Dài tay", "length"),
            ("Hem Width - Rộng lai", "width"),
        ],
        "defaults": {},
    },
    "Jacket": {
        "K": 0.75,
        "specs": [
            ("Body Length - Dài áo", "length"),
            ("Chest - Vòng ngực", "width"),
            ("Shoulder - Ngang vai", "width"),
            ("Sleeve Length - Dài tay", "length"),
            ("Hem Width - Rộng lai", "width"),
        ],
        "defaults": {},
    },
    "Váy / đầm": {
        "K": 0.75,
        "specs": [
            ("Body Length - Dài váy", "length"),
            ("Chest - Vòng ngực", "width"),
            ("Waist - Vòng eo", "width"),
            ("Hip - Vòng mông", "width"),
            ("Hem Width - Rộng lai", "width"),
        ],
        "defaults": {},
    },
}

def parse_number(value):
    s = str(value).strip().replace(" ", "")
    if not s:
        raise ValueError("Có thông số chưa nhập.")
    if "," in s and "." in s:
        if s.rfind(",") < s.rfind("."):
            s = s.replace(",", "")
        else:
            s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    return float(s)

def pct_change(old, new):
    if old <= 0 or new <= 0:
        raise ValueError("Thông số phải lớn hơn 0.")
    return (new / old - 1) * 100

def weighted_mean(values, weights):
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("Tổng trọng số phải lớn hơn 0.")
    return sum(values[k] * weights[k] for k in weights) / total

def width_weights(specs):
    names = [name for name, group in specs if group == "width"]
    raw = {}
    for name in names:
        low = name.lower()
        if "hip" in low or "ngực" in low or "chest" in low:
            raw[name] = 0.35
        elif "thigh" in low or "đùi" in low:
            raw[name] = 0.30
        elif "opening" in low or "gối" in low or "knee" in low or "lai" in low:
            raw[name] = 0.20
        else:
            raw[name] = 0.15
    total = sum(raw.values()) or 1
    return {k: v / total for k, v in raw.items()}

def calculate(old_values, new_values, specs, old_dm, k, group_weights):
    changes = {name: pct_change(old_values[name], new_values[name]) for name, _ in specs}
    model1 = sum(changes.values()) / len(changes)

    grouped = {}
    for name, group in specs:
        grouped.setdefault(group, []).append(name)

    group_changes = {}
    for group, names in grouped.items():
        if group == "width":
            ww = width_weights(specs)
            group_changes[group] = weighted_mean(
                {n: changes[n] for n in names},
                {n: ww[n] for n in names}
            )
        else:
            group_changes[group] = sum(changes[n] for n in names) / len(names)

    active_weights = {g: group_weights[g] for g in group_changes}
    model2 = weighted_mean(group_changes, active_weights)

    def ratio(names):
        if not names:
            return 1.0
        old_avg = sum(old_values[n] for n in names) / len(names)
        new_avg = sum(new_values[n] for n in names) / len(names)
        return new_avg / old_avg

    length_names = [n for n, g in specs if g == "length"]
    width_names = [n for n, g in specs if g == "width"]
    model3 = (ratio(length_names) * ratio(width_names) - 1) * 100

    rows = []
    for name, change in [
        ("Mô hình 1 - Trung bình thông số", model1),
        ("Mô hình 2 - Phân nhóm trọng số", model2),
        ("Mô hình 3 - Kích thước tổng hợp", model3),
    ]:
        adjusted = change * k
        rows.append({
            "Mô hình": name,
            "Thay đổi trước K (%)": change,
            "Điều chỉnh sau K (%)": adjusted,
            "ĐM dự đoán (yd/pcs)": old_dm * (1 + adjusted / 100),
        })

    details = pd.DataFrame([
        {
            "Nhóm": group,
            "Thông số": name,
            "Mã cũ": old_values[name],
            "Mã mới": new_values[name],
            "Thay đổi (%)": changes[name],
        }
        for name, group in specs
    ])
    return pd.DataFrame(rows), details

st.title("🧵 APP TEST DỰ ĐOÁN ĐỊNH MỨC VẢI")
st.caption("Chọn dòng hàng, nhập thông số chính và so sánh 3 mô hình dự đoán.")

if "history" not in st.session_state:
    st.session_state.history = []

# Chọn dòng hàng hiển thị nổi bật ngay đầu app
st.subheader("1. CHỌN DÒNG HÀNG")
category = st.selectbox(
    "Chọn chủng loại sản phẩm:",
    options=list(CATEGORIES.keys()),
    index=0,
    key="product_category",
    help="Bấm vào ô này để chọn Quần short, Quần jean dài, Quần kaki/quần dài, Áo sơ mi, T-shirt/Polo, Hoodie/Sweatshirt, Jacket hoặc Váy/đầm."
)
cfg = CATEGORIES[category]
st.info(f"Đang chọn: **{category}** — Hệ số K mặc định của dòng này: **{cfg['K']:.2f}**")

a, b, c = st.columns(3)
with a:
    old_code = st.text_input("Mã hàng cũ", "R06-494141")
with b:
    new_code = st.text_input("Mã hàng mới", "R06-494148")
with c:
    old_dm = st.number_input("ĐM cũ (yd/pcs)", min_value=0.0001, value=0.8240, step=0.001, format="%.4f")

d, e = st.columns(2)
with d:
    k = st.number_input(
        "Hệ số K áp dụng",
        min_value=0.0, max_value=5.0,
        value=float(cfg["K"]), step=0.05, format="%.2f",
        key=f"k_{category}"
    )
with e:
    actual_str = st.text_input("ĐM thực tế mã mới (để trống nếu chưa có)", "0.7390")

st.divider()
st.subheader("2. NHẬP THÔNG SỐ CŨ VÀ MỚI")
st.caption("Dùng cùng đơn vị cho cả hai mã. Ví dụ 14.750 hoặc 14,750. Chi tiết nhỏ không tính.")

old_values, new_values = {}, {}
specs = cfg["specs"]

for name, group in specs:
    default_old, default_new = cfg["defaults"].get(name, ("", ""))
    x, y, z = st.columns([2.2, 1, 1])
    with x:
        st.write(name)
    with y:
        old_txt = st.text_input(
            "Mã cũ", value=f"{default_old:.3f}" if default_old != "" else "",
            key=f"old_{category}_{name}", label_visibility="collapsed", placeholder="Mã cũ"
        )
    with z:
        new_txt = st.text_input(
            "Mã mới", value=f"{default_new:.3f}" if default_new != "" else "",
            key=f"new_{category}_{name}", label_visibility="collapsed", placeholder="Mã mới"
        )
    try:
        if old_txt.strip() and new_txt.strip():
            old_values[name] = parse_number(old_txt)
            new_values[name] = parse_number(new_txt)
    except ValueError:
        st.error(f"Thông số không hợp lệ: {name}")

st.divider()
st.subheader("3. TRỌNG SỐ MÔ HÌNH PHÂN NHÓM")
with st.expander("Mở để chỉnh trọng số (không bắt buộc)", expanded=False):
    q1, q2, q3 = st.columns(3)
    with q1:
        w_length = st.number_input("Chiều dài", 0.0, 1.0, 0.35, 0.05, key="w_length")
    with q2:
        w_width = st.number_input("Chiều rộng", 0.0, 1.0, 0.45, 0.05, key="w_width")
    with q3:
        w_rise = st.number_input("Độ sâu đáy", 0.0, 1.0, 0.20, 0.05, key="w_rise")
st.caption("Trọng số là giả định để thử nghiệm, chưa phải hệ số chuẩn của nhà máy.")

if st.button("🧮 TÍNH VÀ LƯU LẦN TEST", type="primary"):
    try:
        if not old_code.strip() or not new_code.strip():
            raise ValueError("Nhập mã hàng cũ và mã hàng mới.")
        if old_dm <= 0:
            raise ValueError("ĐM cũ phải lớn hơn 0.")
        if len(old_values) != len(specs) or len(new_values) != len(specs):
            raise ValueError("Hãy nhập đủ thông số cũ và mới của dòng hàng đang chọn.")
        gw = {"length": w_length, "width": w_width, "rise": w_rise}
        if sum(gw[g] for g in set(group for _, group in specs)) <= 0:
            raise ValueError("Tổng trọng số các nhóm đang dùng phải lớn hơn 0.")

        results, details = calculate(old_values, new_values, specs, old_dm, k, gw)
        actual = parse_number(actual_str) if actual_str.strip() else None
        if actual is not None and actual <= 0:
            raise ValueError("ĐM thực tế phải lớn hơn 0.")

        if actual is not None:
            results["ĐM thực tế"] = actual
            results["Sai lệch (%)"] = (
                (results["ĐM dự đoán (yd/pcs)"] - actual) / actual * 100
            )

        st.session_state.current_result = {
            "category": category,
            "old_code": old_code,
            "new_code": new_code,
            "old_dm": old_dm,
            "k": k,
            "results": results,
            "details": details,
            "actual": actual,
        }

        for _, row in results.iterrows():
            st.session_state.history.append({
                "Dòng hàng": category,
                "Mã cũ": old_code,
                "Mã mới": new_code,
                "ĐM cũ": old_dm,
                "K": k,
                "Mô hình": row["Mô hình"],
                "Thay đổi trước K (%)": row["Thay đổi trước K (%)"],
                "Điều chỉnh sau K (%)": row["Điều chỉnh sau K (%)"],
                "ĐM dự đoán": row["ĐM dự đoán (yd/pcs)"],
                "ĐM thực tế": actual,
                "Sai lệch (%)": row.get("Sai lệch (%)", None),
            })
    except (ValueError, ZeroDivisionError) as ex:
        st.error(str(ex))

if "current_result" in st.session_state:
    result = st.session_state.current_result
    st.subheader("4. KẾT QUẢ DỰ ĐOÁN")
    st.write(f"**Dòng hàng:** {result['category']}")
    st.write(f"**Mã cũ:** {result['old_code']}  |  **Mã mới:** {result['new_code']}  |  **K:** {result['k']:.2f}")
    st.dataframe(
        result["results"].style.format({
            "Thay đổi trước K (%)": "{:+.2f}%",
            "Điều chỉnh sau K (%)": "{:+.2f}%",
            "ĐM dự đoán (yd/pcs)": "{:.4f}",
            "ĐM thực tế": lambda x: "" if pd.isna(x) else f"{x:.4f}",
            "Sai lệch (%)": lambda x: "" if pd.isna(x) else f"{x:+.2f}%",
        }),
        use_container_width=True, hide_index=True
    )

    st.subheader("5. CHI TIẾT THAY ĐỔI THÔNG SỐ")
    st.dataframe(
        result["details"].style.format({
            "Mã cũ": "{:.3f}", "Mã mới": "{:.3f}", "Thay đổi (%)": "{:+.2f}%"
        }),
        use_container_width=True, hide_index=True
    )

st.subheader("6. LỊCH SỬ CÁC LẦN TEST")
if st.session_state.history:
    hist = pd.DataFrame(st.session_state.history)
    st.dataframe(
        hist.style.format({
            "ĐM cũ": "{:.4f}", "K": "{:.2f}",
            "Thay đổi trước K (%)": "{:+.2f}%",
            "Điều chỉnh sau K (%)": "{:+.2f}%",
            "ĐM dự đoán": "{:.4f}",
            "ĐM thực tế": lambda x: "" if pd.isna(x) else f"{x:.4f}",
            "Sai lệch (%)": lambda x: "" if pd.isna(x) else f"{x:+.2f}%",
        }),
        use_container_width=True, hide_index=True
    )
    st.download_button(
        "⬇️ Tải lịch sử test CSV",
        hist.to_csv(index=False).encode("utf-8-sig"),
        file_name="lich_su_test_dinh_muc.csv",
        mime="text/csv"
    )
    if st.button("Xóa lịch sử test"):
        st.session_state.history = []
        st.rerun()
else:
    st.info("Chưa có lần test nào được lưu. Lịch sử hiện lưu trong phiên chạy app.")

st.warning(
    "K và trọng số là giả định thử nghiệm. Các mô hình chưa tính trực tiếp diện tích rập, "
    "hiệu suất giác hoặc hao hụt sản xuất; cần kiểm tra bằng nhiều cặp mã có ĐM thực tế."
)
