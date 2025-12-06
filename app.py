# app.py
import streamlit as st
import os
import pandas as pd
import textwrap
import streamlit.components.v1 as components # Nhớ import cái này
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from streamlit_agraph import agraph, Node, Edge, Config


# Import các module nội bộ (giữ nguyên)
from modules.query_helpers import (
    get_vb_by_id, get_thay_the_chain, get_sdbs, 
    get_vbhn,
    get_huong_dan, get_multi_huong_dan, build_tree_graph_data
)
from modules.document_viewer import render_document_viewer
from import_content_vb_docx_html_mucluc import import_docx_to_db
from build_SQL_database import PhapLuat

# 1. Cấu hình trang (Phải đặt đầu tiên)
st.set_page_config(
    page_title="Tra cứu Pháp luật",  # <-- Thay đổi tên Tab tại đây
    page_icon="⚖️",                  # <-- Thay đổi Icon (Dùng Emoji hoặc đường dẫn file ảnh)
    layout="wide",                   # Giữ nguyên layout wide
    initial_sidebar_state="expanded" # (Tùy chọn) Mặc định mở Sidebar
)

def set_tab_title(title):
    """Hàm đổi tên Tab trình duyệt bằng JavaScript"""
    # Xử lý ký tự đặc biệt để tránh lỗi JS (ví dụ dấu ngoặc kép)
    safe_title = title.replace('"', '\\"').replace("'", "\\'")
    
    # Chạy lệnh JS để đổi tiêu đề trang
    js = f"""
    <script>
        window.parent.document.title = "{safe_title} - Tra cứu Pháp luật";
    </script>
    """
    # height=0 để ẩn khung iframe đi
    components.html(js, height=0)

# 2. CSS tùy chỉnh
st.markdown(
    """
    <style>
    .main .block-container {
        padding-top: 0rem;
        padding-bottom: 0.2rem;
    }
    
    /* Hiệu ứng khi rê chuột vào thẻ văn bản */
    .vb-card:hover {
        transform: translateY(-3px); /* Nhấc thẻ lên 3px */
        box-shadow: 0 4px 6px rgba(0,0,0,0.15) !important; /* Đổ bóng đậm hơn */
        cursor: pointer; /* Con trỏ chuột biến thành bàn tay */
        border-color: #3b82f6 !important; /* Viền chuyển màu xanh khi hover */
    }
    /* --- CSS MỚI CHO THẺ KẾT QUẢ TÌM KIẾM --- */
    .search-card {
        padding: 12px 16px;       /* Giảm độ dày đệm trên dưới */
        border-radius: 8px;
        margin-bottom: 8px;       /* Giảm khoảng cách giữa các thẻ */
        border: 1px solid transparent; 
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        transition: all 0.2s ease-in-out;
        display: flex;
        flex-direction: column;
        gap: 4px;                 /* Khoảng cách giữa Tiêu đề và Thông tin phụ cực nhỏ */
    }

    /* Hiệu ứng hover: Nổi lên nhẹ */
    .search-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        cursor: pointer;
        filter: brightness(0.98); /* Tối đi 1 chút xíu để tạo cảm giác bấm */
    }

    /* Badge trạng thái hiệu lực nhỏ gọn */
    .status-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 500;
    }
    
    /* Tiêu đề văn bản */
    .search-title {
        font-size: 15px;          /* Chữ vừa phải, không quá to */
        font-weight: 700;
        color: #1f2937;
        line-height: 1.4;
    }

    /* Thông tin phụ: Nhỏ, gọn, cùng một dòng */
    .meta-info {
        font-size: 12.5px;
        color: #4b5563;
        display: flex;
        flex-wrap: wrap;          /* Cho phép xuống dòng nếu màn hình bé */
        gap: 12px;                /* Khoảng cách giữa các mục thông tin */
        align-items: center;
    }
    
    /* CSS cho thẻ Detail cũ (giữ nguyên để không mất hiệu ứng cũ) */
    .vb-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.15) !important;
        cursor: pointer;
        border-color: #3b82f6 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 3. Quản lý kết nối Database (TỐI ƯU HÓA)
# Sử dụng cache_resource để không phải kết nối lại DB mỗi lần user tương tác
@st.cache_resource
def get_db_engine():
    # Lấy DATABASE_URL
    url = os.getenv("DATABASE_URL")
    if not url:
        try:
            from config_local import DATABASE_URL as local_url
            url = local_url
        except ImportError:
            st.error("Không tìm thấy biến môi trường DATABASE_URL hoặc file config_local.py")
            st.stop()
    
    # Tạo engine với pool_pre_ping=True để tự động check kết nối sống
    return create_engine(url, pool_pre_ping=True)

# Khởi tạo Engine và Session Factory
engine = get_db_engine()
SessionLocal = sessionmaker(bind=engine)


# 4. Hàm hỗ trợ hiển thị (Helper function)
def render_search_results(ket_qua_search):
    """Hiển thị kết quả tìm kiếm dạng Thẻ (Card) Compact & Colorful."""
    st.markdown("#### 🔎 Kết quả tìm kiếm")

    if not ket_qua_search:
        st.info("Không có kết quả.")
        return
    
    st.caption(f"Đang hiển thị {len(ket_qua_search)} văn bản")

    for i, vb in enumerate(ket_qua_search, start=1):
        # 1. Xử lý màu sắc NỀN và VIỀN
        tinh_trang = (vb.tinh_trang or "").lower()
        
        if "còn hiệu lực" in tinh_trang:
            # Màu Xanh lá nhạt (Pastel)
            bg_color = "#ecfdf5" 
            border_left = "4px solid #10b981" # Viền trái xanh đậm
            status_text = "✅ Còn hiệu lực"
            text_color = "#064e3b" # Chữ xanh đậm
            
        elif "hết hiệu lực" in tinh_trang or "ngừng hiệu lực" in tinh_trang:
            # Màu Đỏ nhạt / Xám
            bg_color = "#fef2f2" 
            border_left = "4px solid #ef4444" # Viền trái đỏ
            status_text = f"⛔ {vb.tinh_trang}"
            text_color = "#7f1d1d"
            
        elif "chưa có hiệu lực" in tinh_trang:
            # Màu Vàng nhạt
            bg_color = "#fefce8"
            border_left = "4px solid #eab308"
            status_text = f"⚠️ {vb.tinh_trang}"
            text_color = "#713f12"
            
        else:
            # Màu Xanh dương nhạt
            bg_color = "#eff6ff"
            border_left = "4px solid #3b82f6"
            status_text = "ℹ️ Không rõ"
            text_color = "#1e3a8a"

        # 2. Xử lý dữ liệu
        ten_vb = vb.ten_van_ban or "Không có tiêu đề"
        so_hieu = vb.so_hieu or "---"
        loai_vb = vb.loai_van_ban or "VB"
        ngay_bh = vb.ngay_ban_hanh or ""
        ngay_hl = vb.ngay_hieu_luc or ""
        
        date_display = f"Hiệu lực: {ngay_hl}" if ngay_hl else f"Ban hành: {ngay_bh}"
        detail_url = f"?vb_id={vb.id}"

        # 3. Tạo HTML Card (Dạng nối chuỗi an toàn)
        html_card = (
            f'<a href="{detail_url}" target="_blank" style="text-decoration: none; color: inherit; display: block;">'
            # Áp dụng background-color và border-left trực tiếp vào card
            f'<div class="search-card" style="background-color: {bg_color}; border-left: {border_left};">'
            
            # Dòng 1: Tiêu đề
            f'  <div class="search-title">'
            f'    <span style="font-weight: 400; opacity: 0.7;">#{i}.</span> {ten_vb}'
            f'  </div>'
            
            # Dòng 2: Thông tin meta (Nằm sát nhau)
            f'  <div class="meta-info" style="color: {text_color}">'
            f'    <span style="font-weight: 700;">{status_text}</span>'
            f'    <span style="opacity: 0.4;">|</span>'
            f'    <span>{loai_vb} <b>{so_hieu}</b></span>'
            f'    <span style="opacity: 0.4;">|</span>'
            f'    <span>📅 {date_display}</span>'
            f'  </div>'
            f'</div>'
            f'</a>'
        )

        st.markdown(html_card, unsafe_allow_html=True)

def parse_date_safe(date_str):
    """Hàm phụ trợ parse ngày tháng an toàn"""
    try:
        return datetime.strptime(date_str, "%d/%m/%Y")
    except:
        return datetime.min

# 5. Hàm chính (Main Logic)
def main():
    
    # Kiểm tra xem người dùng có đang muốn ĐỌC văn bản nào không
    params = st.query_params
    view_doc_id = params.get("view_doc_id", None)
    
    # [FIX LỖI] Kiểm tra kỹ: Nếu là chuỗi "None" thì coi như không có
    if view_doc_id == "None":
        view_doc_id = None

    # 2. LOGIC HIỂN THỊ TRÌNH ĐỌC (VIEWER)
    if view_doc_id:
        try:
            doc_id = int(view_doc_id)
            
            # Giao diện Viewer
            # Nút Quay lại: Xóa hoàn toàn key khỏi query params
            if st.button("⬅️ Quay lại tra cứu"):
                if "view_doc_id" in st.query_params:
                    del st.query_params["view_doc_id"] # Xóa key thay vì gán None
                st.rerun()
                
            with SessionLocal() as session:
                vb = get_vb_by_id(session, doc_id)
                if vb:
                    # [THÊM DÒNG NÀY] Đổi tên Tab thành tên văn bản đang đọc
                    set_tab_title(f"📖 {vb.ten_van_ban}")
                    render_document_viewer(session, doc_id, vb.ten_van_ban)
                else:
                    st.error("Không tìm thấy văn bản trong CSDL.")
                    
        except ValueError:
            # Nếu view_doc_id bị lỗi format (vd: text linh tinh), xóa nó đi và load lại trang chủ
            if "view_doc_id" in st.query_params:
                del st.query_params["view_doc_id"]
            st.rerun()
            
        return # DỪNG HÀM MAIN TẠI ĐÂY
    
    # ================== SESSION STATE ==================
    if "selected_vb_id" not in st.session_state:
        st.session_state["selected_vb_id"] = None

    # Đọc tham số vb_id từ URL
    params = st.query_params
    raw_vb = params.get("vb_id", None)
    is_detail_only = raw_vb is not None

    if raw_vb:
        if isinstance(raw_vb, list):
            raw_vb = raw_vb[0]
        try:
            st.session_state["selected_vb_id"] = int(raw_vb)
        except Exception:
            pass

    # ================== GIAO DIỆN ĐIỀU KHIỂN ==================
    if is_detail_only:
        view_mode = "Dạng cột"
        search_term = ""
    else:
        st.title("📚 Tra cứu văn bản pháp luật")
        view_mode = st.radio("Chọn chế độ hiển thị:", ["Dạng cột", "Sơ đồ cây quan hệ"])
        search_term = st.text_input("🔍 Tìm kiếm tên văn bản")

    selected_vb_id = st.session_state["selected_vb_id"]
    ket_qua_search = []

    # BẮT ĐẦU KHỐI QUẢN LÝ SESSION DATABASE AN TOÀN
    # Toàn bộ code tương tác DB nằm trong khối 'with' này
    with SessionLocal() as session:
        
        # --- LOGIC TÌM KIẾM ---
        if not is_detail_only:
            if search_term:
                term_clean = search_term.strip()
                if len(term_clean) < 3:
                    st.info("Vui lòng nhập tối thiểu 3 ký tự để tìm kiếm.")
                else:
                    base_query = session.query(PhapLuat).filter(
                        PhapLuat.ten_van_ban.ilike(f"%{term_clean}%"),
                        or_(
                            PhapLuat.loai_van_ban.ilike("%Luật%"),
                            PhapLuat.loai_van_ban.ilike("%Nghị định%"),
                            PhapLuat.loai_van_ban.ilike("%Thông tư%"),
                        )
                    )

                    total_matches = base_query.count()

                    if total_matches == 0:
                        st.warning("Không tìm thấy văn bản nào khớp với từ khóa tìm kiếm.")
                    else:
                        max_rows = st.number_input(
                            "Giới hạn số kết quả hiển thị",
                            min_value=20, max_value=500, value=200, step=20,
                        )
                        
                        ket_qua_raw = base_query.limit(int(max_rows)).all()

                        # Sắp xếp theo độ khớp
                        term_norm = term_clean.lower()
                        def relevance(vb):
                            name = (vb.ten_van_ban or "").lower()
                            if name == term_norm: base = 3
                            elif name.startswith(term_norm): base = 2
                            elif term_norm in name: base = 1
                            else: base = 0
                            return (base, -len(name))

                        ket_qua_search = sorted(ket_qua_raw, key=relevance, reverse=True)

                        st.caption(f"Đã tìm thấy {total_matches} văn bản – đang hiển thị tối đa {min(len(ket_qua_search), int(max_rows))} kết quả.")
                        
                        render_search_results(ket_qua_search)
                        
                        # Cập nhật lại selected_vb_id trong trường hợp user bấm nút xem
                        selected_vb_id = st.session_state["selected_vb_id"]
            else:
                ket_qua_search = []

        # --- LOGIC HIỂN THỊ CHI TIẾT ---
        if selected_vb_id:
            center_vb = get_vb_by_id(session, selected_vb_id)
            if not center_vb:
                st.error("Không tìm thấy văn bản")
                # Dùng st.stop() ở đây vẫn an toàn vì đang nằm trong khối 'with'
                st.stop()
            # [THÊM DÒNG NÀY] Đổi tên Tab thành tên văn bản đang xem sơ đồ
            set_tab_title(f"🔍 {center_vb.ten_van_ban}")

            if view_mode == "Dạng cột":
                st.subheader("🌟 Văn bản trung tâm")
                st.markdown(f"<b>{center_vb.ten_van_ban}</b> ({center_vb.loai_van_ban}) – Hiệu lực: {center_vb.tinh_trang or 'Không rõ'}", unsafe_allow_html=True)

                # --- KHỐI IMPORT DOCX ---
                with st.expander("📥 Import / cập nhật nội dung văn bản từ file .docx"):
                    st.write(f"Văn bản đang chọn: **{center_vb.ten_van_ban}** (ID: `{center_vb.id}`)")
                    
                    uploaded_file = st.file_uploader(
                        "Chọn file .docx của văn bản này",
                        type=["docx"],
                        key=f"upload_docx_{center_vb.id}",
                    )

                    if st.button("🚀 Import nội dung vào DB", key=f"btn_import_{center_vb.id}"):
                        if uploaded_file is None:
                            st.warning("Bạn chưa chọn file .docx.")
                        else:
                            try:
                                with st.spinner("Đang xử lý file .docx và cập nhật vào DB..."):
                                    # Lưu ý: import_docx_to_db có thể tự tạo session riêng hoặc cần điều chỉnh
                                    # Nhưng theo code cũ của bạn thì hàm này hoạt động độc lập, nên giữ nguyên.
                                    num_headings = import_docx_to_db(uploaded_file, center_vb.id)
                                st.success(f"Đã import xong! Mục lục có {num_headings} heading.")
                                st.info("Bạn có thể mở trang viewer hoặc reload để xem nội dung mới.")
                            except Exception as e:
                                st.error(f"Đã xảy ra lỗi khi import: {e}")

                # --- CHUẨN BỊ DỮ LIỆU CỘT ---
                columns_data = []
                thay_the_chain = [center_vb] + get_thay_the_chain(session, center_vb.id)
                columns_data.append(("🟢 Thay thế", thay_the_chain))

                # ----------------- ĐOẠN CẦN SỬA LÀ ĐÂY -----------------
                # 1. Gọi hàm lấy Sửa đổi bổ sung
                sdbs_list = get_sdbs(session, center_vb.id) or []
                
                # 2. Gọi hàm get_vbhn (Hàm đang bị màu xám) <-- QUAN TRỌNG
                vbhn_list = get_vbhn(session, center_vb.id) or [] 
                
                # 3. Gộp 2 danh sách lại
                combined_sua_doi = sdbs_list + vbhn_list
                
                # 4. Đưa vào danh sách hiển thị
                if combined_sua_doi:
                    columns_data.append(("🟡 Sửa đổi bổ sung & 🟣 Hợp nhất", combined_sua_doi))
                # -------------------------------------------------------

                huongdan1 = get_huong_dan(session, center_vb.id)
                if huongdan1:
                    columns_data.append(("🔵 Hướng dẫn", huongdan1))

                # Phần này có thể nặng, nếu cần tối ưu sau này có thể tách ra
                multi_hd = get_multi_huong_dan(session, [vb.id for vb in huongdan1], depth=5) if huongdan1 else []
                for idx, layer in enumerate(multi_hd):
                    vbs_flat = []
                    for sublist in layer:
                        vbs_flat.extend(sublist)
                    if vbs_flat:
                        columns_data.append((f"🟣 Hướng dẫn cấp {idx+2}", vbs_flat))

                # --- RENDER CÁC CỘT ---
                cols = st.columns(len(columns_data))

                def render_column(col, title, vb_list):
                    with col:
                        st.write(f"**{title}**")
                        
                        # Logic sắp xếp
                        def get_sort_date(vb):
                            is_vbhn = "hợp nhất" in (vb.loai_van_ban or "").lower()
                            date_str = vb.ngay_ban_hanh if is_vbhn else vb.ngay_hieu_luc
                            return parse_date_safe(date_str)

                        vb_list_sorted = sorted(vb_list, key=get_sort_date, reverse=True)

                        for vb in vb_list_sorted:
                            if not vb: continue

                            is_center = vb.id == selected_vb_id
                            border_style = "2px solid #ff4b4b" if is_center else "1px solid rgba(0,0,0,0.1)"
                            
                            loai_vb_lower = (vb.loai_van_ban or "").lower()
                            tinh_trang = (vb.tinh_trang or '').lower()
                            
                            # --- LOGIC MÀU SẮC ---
                            if "hợp nhất" in loai_vb_lower:
                                bg_color = "#F3E8FF" # Tím
                                status_color = "#6B21A8"
                                ngay_bh = vb.ngay_ban_hanh or "Chưa rõ"
                                ghi_chu = f"Ngày ban hành: {ngay_bh}"
                                
                            elif "còn hiệu lực" in tinh_trang:
                                bg_color = "#d1fae5" # Xanh lá
                                status_color = "#065f46"
                                ghi_chu = f"Còn hiệu lực từ {vb.ngay_hieu_luc or '?'}"
                                
                            elif "hết hiệu lực" in tinh_trang or "ngừng hiệu lực" in tinh_trang:
                                bg_color = "#f3f4f6" # Xám
                                status_color = "#4b5563"
                                ghi_chu = vb.tinh_trang
                                
                            elif "chưa có hiệu lực" in tinh_trang:
                                bg_color = "#fef9c3" # Vàng
                                status_color = "#854d0e"
                                ghi_chu = f"Chưa có hiệu lực – từ {vb.ngay_hieu_luc or '?'}"
                                
                            else:
                                bg_color = "#e0f2fe" # Xanh dương
                                status_color = "#075985"
                                ghi_chu = vb.tinh_trang or 'Không rõ'

                            # Link
                            relation_url = f"?vb_id={vb.id}"
                            read_url = f"?view_doc_id={vb.id}"
                            
                            # --- HTML AN TOÀN TUYỆT ĐỐI ---
                            # Dùng f-string bình thường nhưng sau đó dùng .replace để xóa hết xuống dòng
                            # Cách này đảm bảo Streamlit nhận diện đây là HTML thuần, không phải Code Block
                            raw_html = f"""
                            <div class="vb-card" style="background-color: {bg_color}; border: {border_style}; border-radius: 8px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden; transition: transform 0.2s;">
                                <a href="{relation_url}" target="_blank" style="text-decoration: none; color: inherit; display: block; padding: 12px 12px 8px 12px;">
                                    <div style="font-weight: 600; font-size: 14px; margin-bottom: 4px; color: #1f2937; line-height: 1.4;">{vb.ten_van_ban}</div>
                                    <div style="font-size: 12px; color: {status_color}; font-style: italic;">{ghi_chu}</div>
                                </a>
                                <a href="{read_url}" target="_self" style="text-decoration: none;">
                                    <div style="background-color: rgba(255,255,255,0.6); border-top: 1px solid rgba(0,0,0,0.05); padding: 6px; text-align: center; font-size: 12px; font-weight: 600; color: {status_color}; transition: background 0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.9)'" onmouseout="this.style.background='rgba(255,255,255,0.6)'">
                                        📖 Đọc nội dung văn bản
                                    </div>
                                </a>
                            </div>
                            """
                            
                            # [QUAN TRỌNG NHẤT] Xóa sạch ký tự xuống dòng trước khi render
                            clean_html = raw_html.replace("\n", "").strip()
                            
                            st.markdown(clean_html, unsafe_allow_html=True)

                for col, (title, vbs) in zip(cols, columns_data):
                    render_column(col, title, vbs)

            elif view_mode == "Sơ đồ cây quan hệ":
                nodes, edges = build_tree_graph_data(session, selected_vb_id)
                config = Config(width=1100, height=600, directed=True, physics=True)
                agraph(nodes=nodes, edges=edges, config=config)

    # KẾT THÚC KHỐI WITH -> Session tự động đóng tại đây (ngay cả khi có lỗi)

# Chạy ứng dụng
if __name__ == "__main__":
    main()