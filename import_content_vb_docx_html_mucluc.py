import os
import mammoth
import re  # <--- BẠN ĐANG THIẾU DÒNG QUAN TRỌNG NÀY
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text

# Lấy DATABASE_URL từ env; nếu chạy local thì dùng config_local.py
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    try:
        from config_local import DATABASE_URL
    except ImportError:
        pass

def convert_docx_to_html_file(docx_file) -> str:
    """
    Convert file .docx (file-like object: uploaded_file từ Streamlit)
    thành HTML thô bằng mammoth.
    """
    result = mammoth.convert_to_html(docx_file)
    html = result.value
    messages = result.messages

    print(f"[INFO] Đã convert xong .docx -> HTML, độ dài: {len(html)} ký tự.")
    if messages:
        print("[MAMMOTH MESSAGES]")
        for m in messages:
            print(" -", m)

    return html


def convert_docx_to_html_path(docx_path: str) -> str:
    """
    Dùng khi chạy script local bằng đường dẫn.
    """
    with open(docx_path, "rb") as f:
        return convert_docx_to_html_file(f)


def build_html_with_ids_and_toc(raw_html: str):
    """
    Phân tích HTML để tạo mục lục với bộ lọc Regex CHẶT CHẼ (Strict Mode).
    Chỉ nhận diện là Heading nếu có SỐ đi kèm.
    """
    soup = BeautifulSoup(raw_html, "html.parser")
    toc = []
    counter = 0

    # Quét các thẻ có thể chứa tiêu đề
    tags_to_scan = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p'])

    for tag in tags_to_scan:
        text_content = tag.get_text(strip=True)
        if not text_content:
            continue
        
        # Tiền xử lý: Xóa các ký tự lạ non-breaking space nếu có
        text_clean = text_content.replace('\xa0', ' ')

        level = None
        
        # --- BỘ LỌC REGEX THÔNG MINH ---
        
        # 1. Bắt "Phần" + Số La Mã hoặc chữ "thứ" (VD: Phần I, Phần thứ nhất)
        if re.match(r'^Phần\s+([IVX0-9]+|thứ\s)', text_clean, re.IGNORECASE):
            level = 1
            
        # 2. Bắt "Chương" + Số (VD: Chương I, Chương 1)
        elif re.match(r'^Chương\s+[IVX0-9]+', text_clean, re.IGNORECASE):
            level = 2
            
        # 3. Bắt "Mục" + Số (VD: Mục 1, Mục I)
        elif re.match(r'^Mục\s+[0-9IVX]+', text_clean, re.IGNORECASE):
            level = 3
            
        # 4. Bắt "Tiểu mục" + Số
        elif re.match(r'^Tiểu mục\s+[0-9]+', text_clean, re.IGNORECASE):
            level = 3
            
        # 5. Bắt "Điều" + Số (VD: Điều 1, Điều 20)
        elif re.match(r'^Điều\s+\d+', text_clean, re.IGNORECASE):
            level = 4

        # --- XỬ LÝ NẾU TÌM THẤY HEADING ---
        if level is not None:
            counter += 1
            new_id = f"heading_{counter}"
            
            # Gán ID ngược lại vào thẻ HTML để Viewer cuộn tới được
            tag['id'] = new_id
            
            toc.append({
                "heading_id": new_id,
                "level": level,
                "title": text_clean
            })

    html_with_ids = str(soup)
    print(f"[INFO] Đã quét được {len(toc)} mục (Strict Mode).")
    return html_with_ids, toc


def save_html_and_toc_to_db(html: str, toc: list, vb_id: int):
    """
    - Cập nhật phap_luat.content_html cho vb_id.
    - Xoá mục lục cũ của vb_id trong muc_luc_van_ban.
    - Insert mục lục mới.
    """
    engine = create_engine(DATABASE_URL)

    with engine.begin() as conn:
        # 1. Cập nhật HTML nội dung
        conn.execute(
            text(
                """
                UPDATE phap_luat
                SET content_html = :html
                WHERE id = :vb_id
                """
            ),
            {"html": html, "vb_id": vb_id},
        )
        print(f"[DB] Đã cập nhật content_html cho phap_luat.id = {vb_id}")

        # 2. Xoá mục lục cũ
        conn.execute(
            text("DELETE FROM muc_luc_van_ban WHERE vb_id = :vb_id"),
            {"vb_id": vb_id},
        )
        print(f"[DB] Đã xoá mục lục cũ của vb_id = {vb_id}")

        # 3. Insert mục lục mới
        if toc:
            # Chuẩn bị data để insert batch (nhanh hơn loop từng dòng)
            data_to_insert = [
                {
                    "vb_id": vb_id,
                    "heading_id": item["heading_id"],
                    "level": item["level"],
                    "title": item["title"],
                    "order_no": idx
                }
                for idx, item in enumerate(toc, start=1)
            ]
            
            conn.execute(
                text("""
                    INSERT INTO muc_luc_van_ban (vb_id, heading_id, level, title, order_no)
                    VALUES (:vb_id, :heading_id, :level, :title, :order_no)
                """),
                data_to_insert
            )

        print(f"[DB] Đã insert {len(toc)} dòng vào muc_luc_van_ban.")


def import_docx_to_db(docx_file, vb_id: int) -> int:
    """
    Pipeline dùng cho Streamlit
    """
    raw_html = convert_docx_to_html_file(docx_file)
    html_with_ids, toc = build_html_with_ids_and_toc(raw_html)
    save_html_and_toc_to_db(html_with_ids, toc, vb_id)
    return len(toc)