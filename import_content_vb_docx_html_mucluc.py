import os
import mammoth
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text

# Lấy DATABASE_URL từ env; nếu chạy local thì dùng config_local.py
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    from config_local import DATABASE_URL


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
    - Thêm id cho các heading (h2, h3, h4)
    - Sinh list mục lục (toc) dạng:
        [
          {"heading_id": "h2_1", "level": 2, "title": "Chương I ..."},
          ...
        ]
    """
    soup = BeautifulSoup(raw_html, "html.parser")

    toc = []
    counters = {"h2": 0, "h3": 0, "h4": 0}

    for h in soup.find_all(["h2", "h3", "h4"]):
        tag_name = h.name  # h2 / h3 / h4
        counters[tag_name] += 1

        hid = h.get("id")
        if not hid:
            hid = f"{tag_name}_{counters[tag_name]}"
            h["id"] = hid

        title = h.get_text(strip=True)
        level = int(tag_name[1])  # "h2" -> 2

        toc.append(
            {
                "heading_id": hid,
                "level": level,
                "title": title,
            }
        )

    html_with_ids = str(soup)
    print(f"[INFO] Tổng số heading lấy được: {len(toc)}")
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
        for order_no, item in enumerate(toc, start=1):
            conn.execute(
                text(
                    """
                    INSERT INTO muc_luc_van_ban (vb_id, heading_id, level, title, order_no)
                    VALUES (:vb_id, :heading_id, :level, :title, :order_no)
                    """
                ),
                {
                    "vb_id": vb_id,
                    "heading_id": item["heading_id"],
                    "level": item["level"],
                    "title": item["title"],
                    "order_no": order_no,
                },
            )

        print(f"[DB] Đã insert {len(toc)} dòng vào muc_luc_van_ban.")


def import_docx_to_db(docx_file, vb_id: int) -> int:
    """
    Pipeline dùng cho Streamlit:
      - docx_file: uploaded_file (file-like object)
      - vb_id: id văn bản trong phap_luat
    Trả về: số heading trong mục lục.
    """
    raw_html = convert_docx_to_html_file(docx_file)
    html_with_ids, toc = build_html_with_ids_and_toc(raw_html)
    save_html_and_toc_to_db(html_with_ids, toc, vb_id)
    return len(toc)


# Tuỳ chọn: vẫn cho chạy local kiểu cũ bằng đường dẫn và VB_ID cố định
if __name__ == "__main__":
    DOCX_PATH = r"C:\LawDocs\Luat_thue_TNCN_update_27_08_2025.docx"
    VB_ID = 164973

    raw_html = convert_docx_to_html_path(DOCX_PATH)
    html_with_ids, toc = build_html_with_ids_and_toc(raw_html)
    save_html_and_toc_to_db(html_with_ids, toc, VB_ID)
    print("✅ HOÀN TẤT import văn bản vào phap_luat + muc_luc_van_ban.")
