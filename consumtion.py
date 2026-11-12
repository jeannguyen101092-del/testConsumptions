import streamlit as st
import pandas as pd

st.set_page_config(page_title="Dự đoán định mức vải - Full POM", page_icon="🧵", layout="wide")

CATEGORIES = {
    "Quần short": {
        "specs": [
            ("Outseam - Dài quần ngoài", "length"),
            ("Inseam - Dài quần trong", "length"),
            ("Waist - Vòng eo / Lưng quần", "width"),
            ("Hip - Vòng mông", "width"),
            ("Thigh - Rộng đùi", "width"),
            ("Leg Opening - Rộng ống", "width"),
            ("Front Rise - Cao đáy trước", "rise"),
            ("Back Rise - Cao đáy sau", "rise"),
            ("Waistband Height - Cao bản lưng / cạp", "detail"),
            ("Fly Length - Dài moi / dây kéo", "detail"),
            ("Fly Width - Rộng moi", "detail"),
            ("Belt Loop Length - Dài đỉa quần", "detail"),
            ("Belt Loop Width - Rộng đỉa quần", "detail"),
            ("Front Pocket Opening - Miệng túi trước", "detail"),
            ("Front Pocket Bag Length - Dài lót túi trước", "detail"),
            ("Front Pocket Bag Width - Rộng lót túi trước", "detail"),
            ("Coin Pocket Width - Rộng túi đồng hồ", "detail"),
            ("Coin Pocket Height - Cao túi đồng hồ", "detail"),
            ("Back Pocket Width - Rộng túi sau", "detail"),
            ("Back Pocket Height - Cao túi sau", "detail"),
            ("Back Pocket Flap Width - Rộng nắp túi sau", "detail"),
            ("Back Pocket Flap Height - Cao nắp túi sau", "detail"),
            ("Cargo Pocket Width - Rộng túi hộp bên hông", "detail"),
            ("Cargo Pocket Height - Cao túi hộp bên hông", "detail"),
            ("Cargo Flap Width - Rộng nắp túi hộp", "detail"),
            ("Cargo Flap Height - Cao nắp túi hộp", "detail"),
            ("Hem Turn-up - Bản gấu / lai quần", "detail"),
        ],
        "defaults": {
            "Outseam - Dài quần ngoài": (14.750, 14.500),
            "Waist - Vòng eo / Lưng quần": (16.500, 16.250),
            "Hip - Vòng mông": (21.000, 20.250),
            "Thigh - Rộng đùi": (14.250, 13.625),
            "Leg Opening - Rộng ống": (13.625, 13.375),
            "Front Rise - Cao đáy trước": (11.250, 12.125),
            "Back Rise - Cao đáy sau": (16.250, 16.000),
        },
    },
    "Quần jean dài": {
        "specs": [
            ("Outseam - Dài quần ngoài", "length"),
            ("Inseam - Dài quần trong", "length"),
            ("Waist - Vòng eo / Lưng quần", "width"),
            ("Hip - Vòng mông", "width"),
            ("Thigh - Rộng đùi", "width"),
            ("Knee - Rộng gối", "width"),
            ("Leg Opening - Rộng ống", "width"),
            ("Front Rise - Cao đáy trước", "rise"),
            ("Back Rise - Cao đáy sau", "rise"),
            ("Back Yoke Height - Cao đô sau", "detail"),
            ("Waistband Height - Cao bản lưng / cạp", "detail"),
            ("Fly Length - Dài moi / dây kéo", "detail"),
            ("Fly Width - Rộng moi", "detail"),
            ("Belt Loop Length - Dài đỉa quần", "detail"),
            ("Belt Loop Width - Rộng đỉa quần", "detail"),
            ("Front Pocket Opening - Miệng túi trước", "detail"),
            ("Front Pocket Bag Length - Dài lót túi trước", "detail"),
            ("Front Pocket Bag Width - Rộng lót túi trước", "detail"),
            ("Coin Pocket Width - Rộng túi đồng hồ", "detail"),
            ("Coin Pocket Height - Cao túi đồng hồ", "detail"),
            ("Back Pocket Width - Rộng túi sau", "detail"),
            ("Back Pocket Height - Cao túi sau", "detail"),
            ("Back Pocket Flap Width - Rộng nắp túi sau", "detail"),
            ("Back Pocket Flap Height - Cao nắp túi sau", "detail"),
            ("Cargo Pocket Width - Rộng túi hộp", "detail"),
            ("Cargo Pocket Height - Cao túi hộp", "detail"),
            ("Cargo Flap Width - Rộng nắp túi hộp", "detail"),
            ("Cargo Flap Height - Cao nắp túi hộp", "detail"),
            ("Hem Turn-up - Bản gấu / lai quần", "detail"),
        ],
        "defaults": {},
    },
    "Quần kaki / quần dài": {
        "specs": [
            ("Outseam - Dài quần ngoài", "length"),
            ("Inseam - Dài quần trong", "length"),
            ("Waist - Vòng eo / Lưng quần", "width"),
            ("Hip - Vòng mông", "width"),
            ("Thigh - Rộng đùi", "width"),
            ("Knee - Rộng gối", "width"),
            ("Leg Opening - Rộng ống", "width"),
            ("Front Rise - Cao đáy trước", "rise"),
            ("Back Rise - Cao đáy sau", "rise"),
            ("Waistband Height - Cao bản lưng / cạp", "detail"),
            ("Fly Length - Dài moi / dây kéo", "detail"),
            ("Fly Width - Rộng moi", "detail"),
            ("Belt Loop Length - Dài đỉa quần", "detail"),
            ("Belt Loop Width - Rộng đỉa quần", "detail"),
            ("Front Pocket Opening - Miệng túi trước", "detail"),
            ("Front Pocket Bag Length - Dài lót túi trước", "detail"),
            ("Front Pocket Bag Width - Rộng lót túi trước", "detail"),
            ("Back Welt Pocket Width - Rộng miệng túi hậu mổ", "detail"),
            ("Back Pocket Bag Length - Dài lót túi hậu", "detail"),
            ("Back Pocket Flap Width - Rộng nắp túi sau", "detail"),
            ("Back Pocket Flap Height - Cao nắp túi sau", "detail"),
            ("Cargo Pocket Width - Rộng túi hộp", "detail"),
            ("Cargo Pocket Height - Cao túi hộp", "detail"),
            ("Cargo Flap Width - Rộng nắp túi hộp", "detail"),
            ("Cargo Flap Height - Cao nắp túi hộp", "detail"),
            ("Pleat Depth - Độ sâu ly quần", "detail"),
            ("Hem Turn-up - Bản gấu / lai quần", "detail"),
        ],
        "defaults": {},
    },
    "Áo sơ mi": {
        "specs": [
            ("Body Length Front - Dài áo trước", "length"),
            ("Body Length Back - Dài áo sau", "length"),
            ("Chest - Vòng ngực", "width"),
            ("Waist - Vòng eo áo", "width"),
            ("Hem Width - Rộng lai áo", "width"),
            ("Shoulder - Ngang vai", "width"),
            ("Back Yoke Height - Cao đô sau", "detail"),
            ("Armhole - Vòng nách", "detail"),
            ("Bicep - Rộng bắp tay", "width"),
            ("Sleeve Length - Dài tay dài", "length"),
            ("Short Sleeve Length - Dài tay ngắn", "length"),
            ("Sleeve Opening - Rộng cửa tay ngắn", "width"),
            ("Collar Length - Dài lá cổ", "detail"),
            ("Collar Point - Dài mũi cổ", "detail"),
            ("Collar Band Height - Cao chân cổ", "detail"),
            ("Front Placket Width - Rộng nẹp áo trước", "detail"),
            ("Cuff Height - Cao măng sét", "detail"),
            ("Cuff Width - Rộng măng sét", "detail"),
            ("Sleeve Placket Length - Dài nẹp trụ tay", "detail"),
            ("Chest Pocket Width - Rộng túi ngực", "detail"),
            ("Chest Pocket Height - Cao túi ngực", "detail"),
            ("Chest Pocket Flap Width - Rộng nắp túi ngực", "detail"),
            ("Chest Pocket Flap Height - Cao nắp túi ngực", "detail"),
        ],
        "defaults": {},
    },
    "T-shirt / Polo": {
        "specs": [
            ("Body Length - Dài áo", "length"),
            ("Chest - Vòng ngực", "width"),
            ("Waist - Vòng eo áo", "width"),
            ("Hem Width - Rộng lai áo", "width"),
            ("Shoulder - Ngang vai", "width"),
            ("Armhole - Vòng nách", "detail"),
            ("Bicep - Rộng bắp tay", "width"),
            ("Sleeve Length - Dài tay", "length"),
            ("Sleeve Opening - Rộng cửa tay", "width"),
            ("Neck Width - Rộng ngang cổ", "detail"),
            ("Front Neck Drop - Sâu cổ trước", "detail"),
            ("Back Neck Drop - Sâu cổ sau", "detail"),
            ("Collar Rib Height - Cao bo cổ", "detail"),
            ("Placket Length - Dài nẹp trụ Polo", "detail"),
            ("Placket Width - Rộng nẹp trụ Polo", "detail"),
            ("Cuff Rib Height - Cao bo tay", "detail"),
            ("Chest Pocket Width - Rộng túi ngực", "detail"),
            ("Chest Pocket Height - Cao túi ngực", "detail"),
            ("Chest Pocket Flap Width - Rộng nắp túi ngực", "detail"),
            ("Chest Pocket Flap Height - Cao nắp túi ngực", "detail"),
            ("Side Slit Length - Dài xẻ tà", "detail"),
        ],
        "defaults": {},
    },
    "Hoodie / Sweatshirt": {
        "specs": [
            ("Body Length - Dài áo", "length"),
            ("Chest - Vòng ngực", "width"),
            ("Hem Width - Rộng lai áo", "width"),
            ("Shoulder - Ngang vai", "width"),
            ("Armhole - Vòng nách", "detail"),
            ("Bicep - Rộng bắp tay", "width"),
            ("Sleeve Length - Dài tay", "length"),
            ("Cuff Rib Height - Cao bo tay", "detail"),
            ("Cuff Opening - Rộng cửa tay", "width"),
            ("Bottom Rib Height - Cao bo lai", "detail"),
            ("Neck Width - Rộng ngang cổ", "detail"),
            ("Hood Height - Cao mũ / nón", "detail"),
            ("Hood Width - Rộng mũ / nón", "detail"),
            ("Front Zipper Length - Dài dây kéo thân trước", "detail"),
            ("Kangaroo Pocket Width - Rộng túi bụng Kangaroo", "detail"),
            ("Kangaroo Pocket Height - Cao túi bụng Kangaroo", "detail"),
            ("Side Pocket Opening - Miệng túi sườn", "detail"),
            ("Sleeve Pocket Width - Rộng túi tay áo", "detail"),
            ("Sleeve Pocket Height - Cao túi tay áo", "detail"),
            ("Pocket Flap Width - Rộng nắp túi", "detail"),
            ("Pocket Flap Height - Cao nắp túi", "detail"),
        ],
        "defaults": {},
    },
    "Jacket": {
        "specs": [
            ("Body Length Front - Dài áo trước", "length"),
            ("Body Length Back - Dài áo sau", "length"),
            ("Chest - Vòng ngực", "width"),
            ("Waist - Vòng eo áo", "width"),
            ("Hem Width - Rộng lai áo", "width"),
            ("Shoulder - Ngang vai", "width"),
            ("Back Yoke Height - Cao đô sau", "detail"),
            ("Armhole - Vòng nách", "detail"),
            ("Bicep - Rộng bắp tay", "width"),
            ("Sleeve Length - Dài tay", "length"),
            ("Cuff Height - Cao măng sét / bo tay", "detail"),
            ("Cuff Opening - Rộng cửa tay", "width"),
            ("Collar Height - Cao cổ áo", "detail"),
            ("Collar Length - Dài lá cổ", "detail"),
            ("Hood Height - Cao mũ / nón rời hoặc liền", "detail"),
            ("Hood Width - Rộng mũ / nón", "detail"),
            ("Storm Flap Width - Rộng nẹp che dây kéo", "detail"),
            ("Chest Pocket Width - Rộng túi ngực", "detail"),
            ("Chest Pocket Height - Cao túi ngực", "detail"),
            ("Chest Flap Width - Rộng nắp túi ngực", "detail"),
            ("Chest Flap Height - Cao nắp túi ngực", "detail"),
            ("Lower Pocket Width - Rộng túi dưới", "detail"),
            ("Lower Pocket Height - Cao túi dưới", "detail"),
            ("Lower Flap Width - Rộng nắp túi dưới", "detail"),
            ("Lower Flap Height - Cao nắp túi dưới", "detail"),
            ("Inside Pocket Width - Rộng túi trong lót", "detail"),
            ("Inside Pocket Height - Cao túi trong lót", "detail"),
            ("Sleeve Pocket Width - Rộng túi tay áo", "detail"),
            ("Sleeve Pocket Height - Cao túi tay áo", "detail"),
        ],
        "defaults": {},
    },
    "Váy / đầm": {
        "specs": [
            ("Body Length - Dài váy / đầm", "length"),
            ("Chest - Vòng ngực", "width"),
            ("Waist - Vòng eo", "width"),
            ("Hip - Vòng mông", "width"),
            ("Hem Width - Rộng lai váy", "width"),
            ("Shoulder - Ngang vai", "width"),
            ("Armhole - Vòng nách", "detail"),
            ("Sleeve Length - Dài tay", "length"),
            ("Sleeve Opening - Rộng cửa tay", "width"),
            ("Neck Width - Rộng ngang cổ", "detail"),
            ("Front Neck Drop - Sâu cổ trước", "detail"),
            ("Back Neck Drop - Sâu cổ sau", "detail"),
            ("Waistband Height - Cao bản cạp váy", "detail"),
            ("Zipper Length - Dài dây kéo giọt lệ / sườn", "detail"),
            ("Side Pocket Opening - Miệng túi sườn", "detail"),
            ("Patch Pocket Width - Rộng túi đắp", "detail"),
            ("Patch Pocket Height - Cao túi đắp", "detail"),
            ("Pocket Flap Width - Rộng nắp túi", "detail"),
            ("Pocket Flap Height - Cao nắp túi", "detail"),
            ("Slit Length - Dài xẻ tà váy", "detail"),
            ("Ruffle / Flounce Height - Cao bèo nhún", "detail"),
        ],
        "defaults": {},
    },
}
def parse_number(value):
    if value is None or pd.isna(value):
        return 0.0
    s = str(value).strip().replace(" ", "")
    if not s:
        return 0.0
    if "," in s and "." in s:
        if s.rfind(",") < s.rfind("."):
            s = s.replace(",", "")
        else:
            s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    return float(s)

def width_weights(width_names):
    raw = {}
    for name in width_names:
        low = name.lower()
        if "hip" in low or "ngực" in low or "chest" in low:
            raw[name] = 0.35
        elif "thigh" in low or "đùi" in low:
            raw[name] = 0.30
        elif "opening" in low or "gối" in low or "knee" in low or "lai" in low:
            raw[name] = 0.20
        else:
            raw[name] = 0.15
    total = sum(raw.values()) or 1.0
    return {k: v / total for k, v in raw.items()}

def calculate_full_poms(df_input, specs, old_dm, group_weights):
    spec_map = dict(specs)
    detail_rows = []
    valid_changes, valid_old, valid_new, grouped_valid = {}, {}, {}, {}

    for _, row in df_input.iterrows():
        pom = str(row.get("Tên POM", "")).strip()
        if not pom or pom == "None":
            continue

        old_val = parse_number(row.get("Mã cũ", 0.0))
        new_val = parse_number(row.get("Mã mới", 0.0))
        group = spec_map.get(pom, "detail")

        if old_val == 0 and new_val == 0:
            status, pct_str = "Không có ở cả 2 mã (Bỏ qua)", "—"
        elif old_val == 0 or new_val == 0:
            status, pct_str = "1 bên = 0 (Không so sánh)", "Không so sánh"
        else:
            status = "✅ Đưa vào so sánh"
            pct = (new_val / old_val - 1) * 100
            pct_str = f"{pct:+.2f}%"
            valid_changes[pom] = pct
            valid_old[pom] = old_val
            valid_new[pom] = new_val
            grouped_valid.setdefault(group, []).append(pom)

        detail_rows.append({
            "Nhóm": group,
            "Tên POM": pom,
            "Mã cũ": old_val,
            "Mã mới": new_val,
            "Chênh lệch": round(new_val - old_val, 3),
            "Thay đổi (%)": pct_str,
            "Trạng thái": status,
        })
    if not valid_changes:
        raise ValueError("Cần ít nhất 1 thông số POM có giá trị > 0 ở cả Mã cũ và Mã mới để tính tỷ lệ thay đổi.")

    change_m1 = sum(valid_changes.values()) / len(valid_changes)

    group_changes = {}
    for grp, names in grouped_valid.items():
        if grp == "width":
            ww = width_weights(names)
            group_changes[grp] = sum(valid_changes[n] * ww[n] for n in names)
        else:
            group_changes[grp] = sum(valid_changes[n] for n in names) / len(names)

    active_w = {g: group_weights.get(g, 0.1) for g in group_changes}
    total_w = sum(active_w.values()) or 1.0
    change_m2 = sum(group_changes[g] * active_w[g] for g in group_changes) / total_w

    def group_ratio(grp_key):
        names = grouped_valid.get(grp_key, [])
        if not names:
            return 1.0
        o_avg = sum(valid_old[n] for n in names) / len(names)
        n_avg = sum(valid_new[n] for n in names) / len(names)
        return (n_avg / o_avg) if o_avg > 0 else 1.0

    change_m3 = (group_ratio("length") * group_ratio("width") - 1) * 100

    summary_rows = []
    for model_name, pct in [
        ("Mô hình 1 - Trung bình toàn bộ POM hợp lệ", change_m1),
        ("Mô hình 2 - Phân nhóm trọng số (Thân + Chi tiết phụ)", change_m2),
        ("Mô hình 3 - Tỷ lệ Dài × Rộng tổng hợp (Khuyên dùng)", change_m3),
    ]:
        pred_dm = old_dm * (1 + pct / 100)
        summary_rows.append({
            "Phương pháp tính": model_name,
            "Số POM so sánh": len(valid_changes),
            "Tỷ lệ thay đổi tổng hợp (%)": round(pct, 2),
            "ĐM cũ (yd/pcs)": round(old_dm, 4),
            "ĐM dự đoán mới (yd/pcs)": round(pred_dm, 4),
            "Chênh lệch ĐM (yd/pcs)": round(pred_dm - old_dm, 4),
        })

    return pd.DataFrame(summary_rows), pd.DataFrame(detail_rows)
st.title("🧵 APP DỰ ĐOÁN ĐỊNH MỨC VẢI (FULL POM CHI TIẾT)")
st.caption("Danh sách đầy đủ tất cả chi tiết (thân chính, túi, nắp túi, cạp, cổ, măng sét, nón...). Mã nào không có để = 0 sẽ tự động không đưa vào so sánh.")

st.subheader("1. THÔNG TIN MÃ HÀNG")
col_cat, col_old, col_new, col_dm = st.columns([1.2, 1, 1, 1])
with col_cat:
    category = st.selectbox("Chủng loại sản phẩm", options=list(CATEGORIES.keys()), index=0)
with col_old:
    old_code = st.text_input("Mã hàng cũ", "R06-494141")
with col_new:
    new_code = st.text_input("Mã hàng mới", "R06-494148")
with col_dm:
    old_dm = st.number_input("ĐM cũ (yd/pcs)", min_value=0.0001, value=0.8240, step=0.001, format="%.4f")

cfg = CATEGORIES[category]
st.subheader("2. NHẬP THÔNG SỐ POM (ĐỂ = 0 NẾU KHÔNG CÓ CHI TIẾT ĐÓ)")

init_rows = [
    {"Nhóm": grp, "Tên POM": spec_name, "Mã cũ": cfg["defaults"].get(spec_name, (0.0, 0.0))[0], "Mã mới": cfg["defaults"].get(spec_name, (0.0, 0.0))[1]}
    for spec_name, grp in cfg["specs"]
]

edited_df = st.data_editor(
    pd.DataFrame(init_rows),
    num_rows="dynamic",
    use_container_width=True,
    height=520,
    column_config={
        "Nhóm": st.column_config.SelectboxColumn("Nhóm", options=["length", "width", "rise", "detail"], required=True),
        "Tên POM": st.column_config.TextColumn("Tên POM (Chi tiết đo)", width="large"),
        "Mã cũ": st.column_config.NumberColumn("Mã cũ", min_value=0.0, format="%.3f"),
        "Mã mới": st.column_config.NumberColumn("Mã mới", min_value=0.0, format="%.3f"),
    },
    key=f"full_pom_editor_{category}",
)

with st.expander("Tùy chỉnh trọng số nhóm (dùng cho Mô hình 2)", expanded=False):
    w1, w2, w3, w4 = st.columns(4)
    w_len = w1.number_input("Nhóm Dài (length)", value=0.40, step=0.05)
    w_wid = w2.number_input("Nhóm Rộng (width)", value=0.40, step=0.05)
    w_ris = w3.number_input("Nhóm Đáy (rise)", value=0.10, step=0.05)
    w_det = w4.number_input("Nhóm Chi tiết phụ (detail)", value=0.10, step=0.05)

if st.button("🚀 Tính toán & Dự đoán định mức mới", type="primary"):
    try:
        group_weights = {"length": w_len, "width": w_wid, "rise": w_ris, "detail": w_det}
        df_summary, df_details = calculate_full_poms(edited_df, cfg["specs"], old_dm, group_weights)

        st.subheader("3. KẾT QUẢ DỰ ĐOÁN ĐỊNH MỨC MỚI")
        st.dataframe(df_summary, use_container_width=True, hide_index=True)

        st.subheader("4. BẢNG ĐỐI CHIẾU FULL POM")
        filter_opt = st.radio(
            "Hiển thị dòng POM:",
            options=["Tất cả POM", "Chỉ hiện các POM có đưa vào so sánh (> 0 cả 2 bên)", "Chỉ hiện các POM có nhập dữ liệu (> 0 ít nhất 1 bên)"],
            horizontal=True,
        )
        if filter_opt == "Chỉ hiện các POM có đưa vào so sánh (> 0 cả 2 bên)":
            df_show = df_details[(df_details["Mã cũ"] > 0) & (df_details["Mã mới"] > 0)]
        elif filter_opt == "Chỉ hiện các POM có nhập dữ liệu (> 0 ít nhất 1 bên)":
            df_show = df_details[(df_details["Mã cũ"] > 0) | (df_details["Mã mới"] > 0)]
        else:
            df_show = df_details

        st.dataframe(df_show, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Lỗi tính toán: {e}")
