# app.py
import streamlit as st
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from modules.query_helpers import (
    get_vb_by_id, get_thay_the_chain, get_sdbs, get_huong_dan,
    get_multi_huong_dan, build_tree_graph_data
)
from streamlit_agraph import agraph, Node, Edge, Config

st.set_page_config(layout="wide")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    from config_local import DATABASE_URL  # chạy local sẽ dùng file này

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

st.title("📚 Tra cứu văn bản pháp luật")

view_mode = st.radio("Chọn chế độ hiển thị:", ["Dạng cột", "Sơ đồ cây quan hệ"])

search_term = st.text_input("🔍 Tìm kiếm tên văn bản")

ket_qua_search = []
if search_term:
    from build_SQL_database import PhapLuat
    ket_qua_search = session.query(PhapLuat).filter(
        PhapLuat.ten_van_ban.ilike(f"%{search_term}%")
    ).all()

selected_vb_id = None
if ket_qua_search:
    options = {f"{vb.ten_van_ban} (Hiệu lực: {vb.tinh_trang})": vb.id for vb in ket_qua_search}
    selected_label = st.selectbox("Chọn văn bản:", list(options.keys()))
    selected_vb_id = options[selected_label]

if selected_vb_id:
    center_vb = get_vb_by_id(session, selected_vb_id)
    if not center_vb:
        st.error("Không tìm thấy văn bản")
        st.stop()

    if view_mode == "Dạng cột":
        st.subheader("🌟 Văn bản trung tâm")
        st.markdown(f"<b>{center_vb.ten_van_ban}</b> ({center_vb.loai_van_ban}) – Hiệu lực: {center_vb.tinh_trang or 'Không rõ'}", unsafe_allow_html=True)

        columns_data = []
        thay_the_chain = [center_vb] + get_thay_the_chain(session, center_vb.id)
        columns_data.append(("🟢 Thay thế", thay_the_chain))

        sdbs = get_sdbs(session, center_vb.id)
        if sdbs:
            columns_data.append(("🟡 Sửa đổi bổ sung", sdbs))

        huongdan1 = get_huong_dan(session, center_vb.id)
        if huongdan1:
            columns_data.append(("🔵 Hướng dẫn", huongdan1))

        multi_hd = get_multi_huong_dan(session, [vb.id for vb in huongdan1], depth=5) if huongdan1 else []
        for idx, layer in enumerate(multi_hd):
            vbs_flat = []
            for sublist in layer:
                vbs_flat.extend(sublist)
            if vbs_flat:
                columns_data.append((f"🟣 Hướng dẫn cấp {idx+2}", vbs_flat))

        cols = st.columns(len(columns_data))
        
        
        def render_column(col, title, vb_list):
            from datetime import datetime

            with col:
                st.write(f"{title}")

                def parse_date_safe(date_str):
                    try:
                        return datetime.strptime(date_str, "%d/%m/%Y")
                    except:
                        return datetime.min

                vb_list_sorted = sorted(
                    vb_list,
                    key=lambda vb: parse_date_safe(vb.ngay_hieu_luc) if vb and vb.ngay_hieu_luc else datetime.min,
                    reverse=True
                )

                for vb in vb_list_sorted:
                    if not vb:
                        continue

                    is_center = vb.id == selected_vb_id
                    border_style = "3px solid red" if is_center else "none"

                    tinh_trang = (vb.tinh_trang or '').lower()
                    ngay_hieu_luc = vb.ngay_hieu_luc or "Không rõ"

                    if "còn hiệu lực" in tinh_trang:
                        color = "#90EE90"
                        ghi_chu = f"<i>Còn hiệu lực từ {ngay_hieu_luc}</i>"
                    elif "hết hiệu lực" in tinh_trang or "ngừng hiệu lực" in tinh_trang:
                        color = "#A9A9A9"
                        ghi_chu = f"<i>{vb.tinh_trang}</i>"
                    elif "chưa có hiệu lực" in tinh_trang:
                        color = "#FFD700"
                        ghi_chu = f"<i>Chưa có hiệu lực – hiệu lực từ {ngay_hieu_luc}</i>"
                    else:
                        color = "#ADD8E6"
                        ghi_chu = f"<i>Tình trạng: {vb.tinh_trang or 'Không rõ'}</i>"

                    st.markdown(
                        f"""
                        <div style='
                            background-color:{color};
                            margin-bottom:10px;
                            padding:10px;
                            border-radius:8px;
                            text-align:center;
                            font-size:14px;
                            border:{border_style};
                        '>
                            <b>{vb.ten_van_ban}</b><br>
                            {ghi_chu}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )



        for col, (title, vbs) in zip(cols, columns_data):
            render_column(col, title, vbs)

    elif view_mode == "Sơ đồ cây quan hệ":
        nodes, edges = build_tree_graph_data(session, selected_vb_id)
        config = Config(width=1100, height=600, directed=True, physics=True)
        agraph(nodes=nodes, edges=edges, config=config)

session.close()
