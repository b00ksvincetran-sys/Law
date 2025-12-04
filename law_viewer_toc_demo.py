import os

import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from streamlit_quill import st_quill

# ====== KẾT NỐI DATABASE ======
# Ưu tiên lấy từ st.secrets, nếu không có thì lấy từ biến môi trường

st.set_page_config(layout="wide")

st.markdown("""
    <style>
    .block-container {
        padding-top: 0.25rem !important;
        padding-bottom: 0rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100% !important;
    }
    header[data-testid="stHeader"] {
        background: transparent;
    }
    /* Giảm margin dưới của tiêu đề chính */
    .block-container h3 {
        margin-bottom: 0.25rem !important;
    }
    /* ======= CHẾ ĐỘ CHỈNH SỬA: QUILL EDITOR ======= */

    /* Thanh toolbar Quill: dính cố định trên cửa sổ */
    .ql-toolbar.ql-snow {
        position: fixed !important;
        top: 150px !important;          /* 👈 số này bạn có thể tăng/giảm cho vừa mắt */
        left: 0;
        right: 0;
        padding-left: 0.5rem;
        padding-right: 0.5rem;
        background: #ffffff !important;
        z-index: 1000 !important;
        border-bottom: 1px solid #ddd;
    }

    /* Phần nội dung editor: đẩy xuống dưới toolbar một đoạn,
       để chữ không bị toolbar che */
    .ql-container.ql-snow {
        margin-top: 60px !important;    /* ~ chiều cao toolbar, chỉnh theo top ở trên */
        min-height: 400px !important;
    }
    </style>
""", unsafe_allow_html=True)

# ====== KẾT NỐI DATABASE (THEO CÁCH BẠN ĐANG DÙNG) ======
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Chỉ dùng local: lấy từ config_local.py
    from config_local import DATABASE_URL

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()


# ====== HÀM XÂY MỤC LỤC (SIDEBAR) ======
def build_nav_html(toc_rows):
    """Tạo HTML cho sidebar mục lục từ bảng muc_luc_van_ban."""
    items = []
    for row in toc_rows:
        # thụt lề theo level: 1 = chương, 2 = điều, 3 = mục...
        indent = (row.level - 1) * 16
        items.append(
            f'<div style="margin-left:{indent}px;margin-bottom:4px;">'
            f'<a href="#{row.heading_id}" class="toc-link">{row.title}</a>'
            f'</div>'
        )
    return "\n".join(items)


# ====== HÀM GÓP TOÀN BỘ HTML (SIDEBAR + CONTENT + SEARCH) ======
def build_full_page_html(content_html: str, nav_html: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
  body {{
    margin: 0;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }}
  .container {{
    display: flex;
    flex-direction: row;
    height: 100vh;
    box-sizing: border-box;
    overflow: hidden;
  }}
  .sidebar {{
    width: 280px;              /* chiều rộng khởi đầu */
    min-width: 180px;
    max-width: 600px;
    border-right: 1px solid #ddd;
    padding: 8px 12px;
    overflow-y: auto;
    font-size: 13px;
    box-sizing: border-box;
  }}
  .divider {{
    width: 5px;
    cursor: col-resize;
    background-color: #eee;
    border-right: 1px solid #ddd;
    box-sizing: border-box;
  }}
  .divider:hover {{
    background-color: #ddd;
  }}
  .content {{
    flex: 1;
    padding: 0 24px 16px 24px;   /* bỏ padding-top, toolbar sẽ nằm sát trên */
    overflow-y: auto;
    font-size: 14px;  /* cỡ chữ mặc định */
    line-height: 1.5;
    box-sizing: border-box;
  }}
  .toolbar {{
    position: sticky;
    top: 0;
    z-index: 10;
    background: #fff;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
    border-bottom: 1px solid #eee;
    margin-bottom: 8px;
  }}
  #contentInner {{
    padding-top: 4px;
  }}

  /* 👇 Thêm đoạn này để khi scroll tới heading, nó dừng thấp hơn toolbar một chút */
  .content [id] {{
    scroll-margin-top: 40px;  /* có thể tăng/giảm 32–56 tuỳ mắt nhìn */
  }}
  
  .toolbar button {{
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 2px 8px;
    background: #f7f7f7;
    cursor: pointer;
    font-size: 13px;
  }}
  .toolbar button:hover {{
    background: #e9e9e9;
  }}
  .toolbar span {{
    font-size: 13px;
    color: #555;
  }}
  .search-box {{
    width: 100%;
    padding: 6px 8px;
    margin-bottom: 8px;
    box-sizing: border-box;
  }}
  .toc-link {{
    text-decoration: none;
    color: #0366d6;
  }}
  .toc-link:hover {{
    text-decoration: underline;
  }}
  mark {{ background-color: yellow; }}
</style>
</head>
<body>
<div class="container">
  <div class="sidebar" id="sidebar">
    <input id="searchBox" class="search-box" placeholder="Tìm trong văn bản..." />
    <div id="toc">
      {nav_html}
    </div>
  </div>
  <div class="divider" id="divider"></div>
  <div class="content" id="content">
    <div class="toolbar">
      <span>Size chữ:</span>
      <button id="fontSmaller">A-</button>
      <button id="fontReset">A</button>
      <button id="fontBigger">A+</button>
    </div>
    <div id="contentInner">
      {content_html}
    </div>
  </div>
</div>

<script>
// ========== RESIZABLE SIDEBAR ==========
(function() {{
  var sidebar = document.getElementById('sidebar');
  var divider = document.getElementById('divider');
  var isResizing = false;

  divider.addEventListener('mousedown', function(e) {{
    isResizing = true;
    document.body.style.cursor = 'col-resize';
    e.preventDefault();
  }});

  document.addEventListener('mousemove', function(e) {{
    if (!isResizing) return;
    var newWidth = e.clientX; // toạ độ X của chuột so với viewport

    // Giới hạn min/max giống CSS
    if (newWidth < 180) newWidth = 180;
    if (newWidth > 600) newWidth = 600;

    sidebar.style.width = newWidth + 'px';
  }});

  document.addEventListener('mouseup', function(e) {{
    if (isResizing) {{
      isResizing = false;
      document.body.style.cursor = 'default';
    }}
  }});
}})();


// ========== FONT SIZE CONTROLS ==========
(function() {{
  var content = document.getElementById('content');
  var currentFontSize = 14;   // px, khởi đầu trùng với CSS
  var minFontSize = 10;
  var maxFontSize = 24;

  function applyFontSize() {{
    content.style.fontSize = currentFontSize + 'px';
  }}

  document.getElementById('fontSmaller').addEventListener('click', function() {{
    if (currentFontSize > minFontSize) {{
      currentFontSize -= 1;
      applyFontSize();
    }}
  }});

  document.getElementById('fontBigger').addEventListener('click', function() {{
    if (currentFontSize < maxFontSize) {{
      currentFontSize += 1;
      applyFontSize();
    }}
  }});

  document.getElementById('fontReset').addEventListener('click', function() {{
    currentFontSize = 14;
    applyFontSize();
  }});
}})();


// ========== SCROLL TỚI HEADING KHI CLICK MỤC LỤC ==========
document.querySelectorAll('.toc-link').forEach(function(a) {{
  a.addEventListener('click', function(e) {{
    e.preventDefault();
    var id = this.getAttribute('href').substring(1);
    var el = document.getElementById(id);
    if (el) {{
      el.scrollIntoView({{behavior: 'smooth', block: 'start'}});
    }}
  }});
}});


// ========== SEARCH: HIGHLIGHT + SCROLL ==========
var lastMarks = [];
function clearMarks() {{
  lastMarks.forEach(function(m) {{
    var parent = m.parentNode;
    parent.replaceChild(document.createTextNode(m.textContent), m);
    parent.normalize();
  }});
  lastMarks = [];
}}

document.getElementById('searchBox').addEventListener('keyup', function(e) {{
  var q = this.value.trim();
  clearMarks();
  if (!q) return;

  var contentInner = document.getElementById('contentInner');
  var walker = document.createTreeWalker(contentInner, NodeFilter.SHOW_TEXT, null, false);
  var firstMatch = null;
  while (walker.nextNode()) {{
    var node = walker.currentNode;
    var idx = node.nodeValue.toLowerCase().indexOf(q.toLowerCase());
    if (idx !== -1) {{
      var span = document.createElement('mark');
      var range = document.createRange();
      range.setStart(node, idx);
      range.setEnd(node, idx + q.length);
      range.surroundContents(span);
      lastMarks.push(span);
      if (!firstMatch) {{
        firstMatch = span;
      }}
    }}
  }}
  if (firstMatch) {{
    firstMatch.scrollIntoView({{behavior: 'smooth', block: 'center'}});
  }}
}});
</script>
</body>
</html>
    """

# ====== UI STREAMLIT ======
st.markdown("### 📚 nội dung văn bản")
# 1. Lấy danh sách văn bản đã có content_html
rows = session.execute(text("""
    SELECT id, ten_van_ban
    FROM phap_luat
    WHERE content_html IS NOT NULL
    ORDER BY ten_van_ban
""")).fetchall()

if not rows:
    st.warning("Chưa có văn bản nào có content_html. Hãy import từ .docx trước.")
else:
    # Chọn văn bản
    vb_map = {f"{r.ten_van_ban} (id {r.id})": r.id for r in rows}
    choice = st.selectbox("Chọn văn bản", list(vb_map.keys()))
    vb_id = vb_map[choice]

    # Chọn chế độ hiển thị
    mode = st.radio(
        "Chế độ",
        ["Đọc", "Chỉnh sửa"],
        horizontal=True,
    )

    # Lấy nội dung gốc & đã chỉnh sửa
    row_raw = session.execute(
        text("""
            SELECT content_html, content_html_edited
            FROM phap_luat
            WHERE id = :id
        """),
        {"id": vb_id},
    ).fetchone()

    content_goc = row_raw.content_html or ""
    content_edited = row_raw.content_html_edited

    # HTML dùng cho chế độ ĐỌC: ưu tiên bản đã chỉnh sửa
    content_for_view = content_edited or content_goc

    # Lấy mục lục
    toc_rows = session.execute(
        text("""
            SELECT heading_id, level, title
            FROM muc_luc_van_ban
            WHERE vb_id = :vb_id
            ORDER BY order_no
        """),
        {"vb_id": vb_id},
    ).fetchall()

    if not toc_rows:
        st.warning("Văn bản này chưa có mục lục trong bảng muc_luc_van_ban.")
    else:
        if mode == "Đọc":
            # ========== CHẾ ĐỘ ĐỌC ==========
            # GIỮ NGUYÊN viewer hiện tại: sidebar + search + zoom + kéo vách
            nav_html = build_nav_html(toc_rows)
            full_html = build_full_page_html(content_for_view, nav_html)
            st.components.v1.html(full_html, height=900, scrolling=False)

        else:
            # ========== CHẾ ĐỘ CHỈNH SỬA ==========
            st.subheader("✏️ Chỉnh sửa / highlight văn bản")

            st.write(
                "Đang chỉnh sửa dựa trên bản "
                + ("**đã chỉnh sửa trước đó**." if content_edited else "**gốc**.")
            )

            # Base cho editor: nếu đã từng chỉnh thì dùng bản chỉnh, không thì dùng bản gốc
            base_html = content_edited or content_goc

            editor_html = st_quill(
                value=base_html,
                html=True,
                key=f"editor_{vb_id}",
            )

            col1, col2 = st.columns(2)

            with col1:
                if st.button("💾 Lưu chỉnh sửa", key=f"save_{vb_id}"):
                    if editor_html:
                        with engine.begin() as conn:
                            conn.execute(
                                text("""
                                    UPDATE phap_luat
                                    SET content_html_edited = :html
                                    WHERE id = :vb_id
                                """),
                                {"html": editor_html, "vb_id": vb_id},
                            )
                        st.success("Đã lưu chỉnh sửa. Chuyển sang chế độ 'Đọc' để xem trên viewer.")

            with col2:
                if st.button("🔄 Reset về bản gốc", key=f"reset_{vb_id}"):
                    with engine.begin() as conn:
                        conn.execute(
                            text("""
                                UPDATE phap_luat
                                SET content_html_edited = NULL
                                WHERE id = :vb_id
                            """),
                            {"vb_id": vb_id},
                        )
                    st.success("Đã xoá bản chỉnh sửa. Lần sau chế độ 'Đọc' sẽ dùng lại content_html gốc.")
