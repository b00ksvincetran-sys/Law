# modules/document_viewer.py
import streamlit as st
from sqlalchemy import text
from streamlit_quill import st_quill
import streamlit.components.v1 as components
import textwrap

def get_viewer_html(content_html, nav_html, page_title):
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<title>{page_title}</title>

<script>
    (function() {{
        var targetTitle = "📖 {page_title}";
        
        // 1. Đổi tên ngay lập tức
        try {{
            window.parent.document.title = targetTitle;
        }} catch(e) {{}}

        // 2. Tạo "Vệ sĩ" canh gác (MutationObserver)
        // Nếu Streamlit cố tình đổi lại tên cũ, "vệ sĩ" sẽ đổi lại tên mới ngay
        var observer = new MutationObserver(function(mutations) {{
            if (window.parent.document.title !== targetTitle) {{
                window.parent.document.title = targetTitle;
            }}
        }});

        // Bắt đầu canh gác thẻ <title> của cửa sổ cha
        try {{
            var titleElement = window.parent.document.querySelector('title');
            if (titleElement) {{
                observer.observe(titleElement, {{ childList: true, subtree: true }});
            }}
        }} catch(e) {{
            console.log("Không thể gán Observer cho title cha: " + e);
        }}
    }})();
</script>

<style>
  /* ... (GIỮ NGUYÊN CSS CŨ CỦA BẠN - KHÔNG ĐỔI) ... */
  html, body {{ 
      margin: 0; 
      padding: 0; 
      font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; 
      height: 100vh; 
      width: 100vw;
      overflow: hidden; 
      background-color: #ffffff;
  }}
  .app-container {{ display: flex; height: 100%; width: 100%; position: relative; }}
  .sidebar {{ width: 280px; min-width: 200px; max-width: 600px; background: #f8f9fa; border-right: 1px solid #e5e7eb; display: flex; flex-direction: column; height: 100%; z-index: 20; }}
  .sidebar-header {{ padding: 12px; border-bottom: 1px solid #e5e7eb; background: #f1f5f9; display: flex; flex-direction: column; gap: 8px; flex-shrink: 0; }}
  .sidebar-content {{ flex: 1; overflow-y: auto; padding: 10px; }}
  .resizer {{ width: 5px; cursor: col-resize; background: transparent; z-index: 30; flex-shrink: 0; border-left: 1px solid #e5e7eb; }}
  .resizer:hover {{ background: #3b82f6; }}
  .main-panel {{ flex: 1; display: flex; flex-direction: column; height: 100%; min-width: 0; position: relative; }}
  .toolbar {{ height: 48px; min-height: 48px; background: #ffffff; border-bottom: 1px solid #e5e7eb; display: flex; align-items: center; padding: 0 16px; gap: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); z-index: 10; flex-shrink: 0; }}
  .doc-viewer {{ flex: 1; height: calc(100% - 48px); overflow-y: auto; padding: 20px 50px; scroll-behavior: smooth; position: relative; }}
  #contentInner {{ width: 100%; font-size: 16px; line-height: 1.8; color: #1f2937; text-align: justify; }}
  .search-container {{ display: flex; align-items: center; gap: 4px; background: #fff; border: 1px solid #d1d5db; border-radius: 6px; padding: 2px; }}
  #searchBox {{ flex: 1; border: none; outline: none; padding: 6px 8px; font-size: 13px; min-width: 0; }}
  .search-btn {{ padding: 4px 8px; cursor: pointer; background: #f3f4f6; border: 1px solid #e5e7eb; border-radius: 4px; font-size: 12px; color: #374151; user-select: none; }}
  .search-btn:hover {{ background: #e5e7eb; }}
  #searchCount {{ font-size: 11px; color: #6b7280; padding: 0 4px; min-width: 35px; text-align: center; }}
  mark {{ background-color: #fde047; padding: 2px 0; }}
  mark.current {{ background-color: #f97316; color: white; }}
  ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
  ::-webkit-scrollbar-thumb {{ background: #d1d5db; border-radius: 4px; }}
  .toc-link {{ text-decoration: none; color: #4b5563; display: block; padding: 5px 8px; border-radius: 4px; font-size: 13px; }}
  .toc-link:hover {{ background: #eff6ff; color: #2563eb; }}
  .toc-link.active {{ background: #dbeafe; color: #1e40af; font-weight: 600; border-left: 3px solid #2563eb; }}
  .toc-item.level-1 {{ font-weight: 700; margin-top: 8px; }}
  .toc-item.level-2 {{ margin-left: 10px; }}
  .toc-item.level-3 {{ margin-left: 20px; }}
</style>
</head>
<body>

<div class="app-container">
  <div class="sidebar" id="sidebar">
    <div class="sidebar-header">
       <div style="font-weight:700; color:#374151;">📚 MỤC LỤC</div>
       <div class="search-container">
         <input type="text" id="searchBox" placeholder="Tìm kiếm..." title="Nhập từ khóa và nhấn Enter">
         <span id="searchCount">0/0</span>
         <div class="search-btn" onclick="nextMatch(-1)" title="Trước">▲</div>
         <div class="search-btn" onclick="nextMatch(1)" title="Sau">▼</div>
       </div>
    </div>
    <div class="sidebar-content">
        {nav_html}
    </div>
  </div>
  <div class="resizer" id="resizer"></div>
  <div class="main-panel">
    <div class="toolbar">
        <button class="search-btn" onclick="changeSize(-1)">A-</button>
        <button class="search-btn" onclick="changeSize(1)">A+</button>
        <button class="search-btn" onclick="resetSize()">Reset</button>
        <div style="flex:1"></div>
        <span style="font-size:12px; color:#9ca3af;">Cuộn chuột để đọc</span>
    </div>
    <div class="doc-viewer" id="docViewer">
        <div id="contentInner">
            {content_html}
        </div>
        <div style="height: 300px;"></div>
    </div>
  </div>
</div>

<script>
    function scrollToElement(element) {{ if (!element) return; const container = document.getElementById('docViewer'); const topPos = element.offsetTop; container.scrollTo({{ top: topPos - 20, behavior: 'smooth' }}); }}
    let matches = []; let currentMatchIndex = -1; const contentDiv = document.getElementById('contentInner'); const originalContent = contentDiv.innerHTML; const searchCountSpan = document.getElementById('searchCount');
    document.getElementById('searchBox').addEventListener('keyup', function(e) {{ if (e.key === 'Enter') performSearch(this.value); }});
    function performSearch(keyword) {{ contentDiv.innerHTML = originalContent; matches = []; currentMatchIndex = -1; searchCountSpan.innerText = "0/0"; if (!keyword || keyword.trim().length < 2) return; const walker = document.createTreeWalker(contentDiv, NodeFilter.SHOW_TEXT, null, false); const textNodes = []; while(walker.nextNode()) textNodes.push(walker.currentNode); const regex = new RegExp('(' + keyword.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&') + ')', 'gi'); let foundAny = false; for (let i = textNodes.length - 1; i >= 0; i--) {{ const node = textNodes[i]; const text = node.nodeValue; if (regex.test(text)) {{ const span = document.createElement('span'); span.innerHTML = text.replace(regex, '<mark>$1</mark>'); node.parentNode.replaceChild(span, node); foundAny = true; }} }} if (foundAny) {{ matches = document.querySelectorAll('mark'); if (matches.length > 0) {{ currentMatchIndex = 0; updateSearchNav(); }} }} }}
    function nextMatch(direction) {{ if (matches.length === 0) return; currentMatchIndex += direction; if (currentMatchIndex >= matches.length) currentMatchIndex = 0; if (currentMatchIndex < 0) currentMatchIndex = matches.length - 1; updateSearchNav(); }}
    function updateSearchNav() {{ searchCountSpan.innerText = (currentMatchIndex + 1) + '/' + matches.length; document.querySelectorAll('mark.current').forEach(m => m.classList.remove('current')); const target = matches[currentMatchIndex]; target.classList.add('current'); scrollToElement(target); }}
    document.querySelectorAll('.toc-link').forEach(a => {{ a.addEventListener('click', function(e) {{ e.preventDefault(); document.querySelectorAll('.toc-link').forEach(l => l.classList.remove('active')); this.classList.add('active'); var id = this.getAttribute('href').substring(1); var el = document.getElementById(id); scrollToElement(el); }}); }});
    const resizer = document.getElementById('resizer'); const sidebar = document.getElementById('sidebar'); let isResizing = false; resizer.addEventListener('mousedown', () => {{ isResizing = true; document.body.style.cursor = 'col-resize'; }}); document.addEventListener('mousemove', (e) => {{ if (!isResizing) return; if (e.clientX > 150 && e.clientX < 800) sidebar.style.width = e.clientX + 'px'; }}); document.addEventListener('mouseup', () => {{ isResizing = false; document.body.style.cursor = 'default'; }});
    var currentSize = 16; function changeSize(d) {{ currentSize += d; if(currentSize < 12) currentSize=12; if(currentSize>32) currentSize=32; document.getElementById('contentInner').style.fontSize = currentSize + 'px'; }} function resetSize() {{ currentSize = 16; document.getElementById('contentInner').style.fontSize = '16px'; }}
</script>
</body>
</html>
    """

def build_nav_html(toc_rows):
    items = []
    for row in toc_rows:
        title = row.title or "(Không có tiêu đề)"
        items.append(
            f'<div class="toc-item level-{row.level}">'
            f'<a href="#{row.heading_id}" class="toc-link">{title}</a>'
            f'</div>'
        )
    return "\n".join(items)

def render_document_viewer(session, vb_id, ten_vb):
    """Hàm hiển thị Viewer trong Streamlit"""
    
    # 1. Lấy nội dung
    row = session.execute(
        text("SELECT content_html, content_html_edited FROM phap_luat WHERE id = :id"), 
        {"id": vb_id}
    ).fetchone()
    
    if not row or not row.content_html:
        st.warning("⚠️ Văn bản này chưa có nội dung số hóa.")
        return

    content = row.content_html_edited or row.content_html

    # 2. Lấy mục lục
    toc_rows = session.execute(
        text("SELECT heading_id, level, title FROM muc_luc_van_ban WHERE vb_id = :id ORDER BY order_no"), 
        {"id": vb_id}
    ).fetchall()
    
    nav_html = build_nav_html(toc_rows) if toc_rows else "<div style='padding:10px; color:#999;'>Chưa có mục lục</div>"

    # 3. Hiển thị UI
    if st.button("⬅️ Trở về danh sách", key="back_btn_top"):
        st.query_params["view_doc_id"] = None
        st.rerun()

    st.markdown(f"#### 📖 {ten_vb}")

    # [BƯỚC QUAN TRỌNG] Xử lý tên để tránh lỗi Javascript (ví dụ có dấu ngoặc kép)
    safe_title = ten_vb.replace('"', '\\"').replace("'", "\\'")

    tab_view, tab_edit = st.tabs(["👁️ Chế độ Đọc (Tối ưu)", "✏️ Chỉnh sửa"])
    
    with tab_view:
        # [THAY ĐỔI Ở ĐÂY] Truyền safe_title vào hàm
        full_html = get_viewer_html(content, nav_html, safe_title)
        
        components.html(full_html, height=850, scrolling=False)
        
    with tab_edit:
        st.info("Chỉnh sửa nội dung...")
        new_content = st_quill(value=content, html=True, key=f"quill_{vb_id}")
        if st.button("Lưu thay đổi", key=f"save_{vb_id}"):
            session.execute(
                text("UPDATE phap_luat SET content_html_edited = :h WHERE id = :id"), 
                {"h": new_content, "id": vb_id}
            )
            session.commit()
            st.success("Đã lưu!")
            st.rerun()