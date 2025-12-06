# modules/query_helpers.py
from sqlalchemy.orm import Session
from streamlit_agraph import Node, Edge
import sys, os

# Thêm đường dẫn để import được từ thư mục gốc
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import đầy đủ các class từ file database của bạn
from build_SQL_database import (
    PhapLuat, 
    VanBanThayThe, 
    VanBanSuadoiBoSung, 
    VanBanHuongDan, 
    VanBanHopNhat  # Class này đã có trong file bạn gửi
)

def get_vb_by_id(session: Session, vb_id: int):
    return session.query(PhapLuat).filter(PhapLuat.id == vb_id).first()


def get_thay_the_chain(session, vb_id):
    chain = []
    current_id = vb_id
    while True:
        record = session.query(VanBanThayThe).filter(
            VanBanThayThe.van_ban_bi_thay_the_id == current_id
        ).first()
        if not record:
            break
        replaced_vb = get_vb_by_id(session, record.van_ban_thay_the_id)
        if replaced_vb:
            chain.append(replaced_vb)
            current_id = replaced_vb.id
        else:
            break
    return chain


def get_sdbs(session, vb_id):
    records = session.query(VanBanSuadoiBoSung).filter(
        VanBanSuadoiBoSung.van_ban_bi_sua_doi_bo_sung_id == vb_id
    ).all()
    return [get_vb_by_id(session, r.van_ban_sua_doi_bo_sung_id) for r in records]


# --- HÀM MỚI BỔ SUNG: LẤY VĂN BẢN HỢP NHẤT ---
def get_vbhn(session, vb_id):
    """
    Lấy danh sách văn bản hợp nhất của văn bản gốc (vb_id)
    Dựa trên bảng VanBanHopNhat trong file database bạn gửi
    """
    records = session.query(VanBanHopNhat).filter(
        VanBanHopNhat.van_ban_duoc_hop_nhat_id == vb_id
    ).all()
    # Trả về các văn bản kết quả hợp nhất
    return [get_vb_by_id(session, r.van_ban_hop_nhat_id) for r in records]


def get_huong_dan(session, vb_id):
    records = session.query(VanBanHuongDan).filter(
        VanBanHuongDan.van_ban_duoc_huong_dan_id == vb_id
    ).all()
    # LƯU Ý: Trong DB của bạn cột này tên là 'Van_ban_huong_dan_id' (chữ V hoa)
    return [get_vb_by_id(session, r.Van_ban_huong_dan_id) for r in records]


def get_multi_huong_dan(session, vb_ids, depth=5):
    result = []
    current_ids = vb_ids
    for _ in range(depth):
        next_vbs = []
        layer = []
        for vb_id in current_ids:
            huong_dans = get_huong_dan(session, vb_id)
            layer.append(huong_dans)
            next_vbs.extend([vb.id for vb in huong_dans if vb])
        if not next_vbs:
            break
        result.append(layer)
        current_ids = next_vbs
    return result


def build_tree_graph_data(session, center_id):
    center_vb = get_vb_by_id(session, center_id)
    if not center_vb:
        return [], []

    nodes = []
    edges = []
    seen_ids = set()

    def add_node(vb):
        if vb and vb.id not in seen_ids:
            seen_ids.add(vb.id)
            color = "red" if vb.id == center_id else "green"
            # Cắt ngắn tên văn bản cho đỡ rối
            label = vb.ten_van_ban[:40] + "..." if len(vb.ten_van_ban) > 40 else vb.ten_van_ban
            nodes.append(Node(id=str(vb.id), label=label, color=color))

    def add_edge(source_id, target_id, label):
        edges.append(Edge(source=str(source_id), target=str(target_id), label=label))

    # Gốc
    add_node(center_vb)

    # Thay thế
    for vb in get_thay_the_chain(session, center_id):
        add_node(vb)
        add_edge(center_id, vb.id, "thay thế")

    # SDBS
    for vb in get_sdbs(session, center_id):
        add_node(vb)
        add_edge(center_id, vb.id, "sửa đổi")
    
    # [MỚI] Thêm node Hợp nhất vào Graph
    for vb in get_vbhn(session, center_id):
        add_node(vb)
        add_edge(center_id, vb.id, "hợp nhất")

    # Hướng dẫn đệ quy
    stack = [(center_id, 0)]
    while stack:
        current_id, level = stack.pop()
        for vb in get_huong_dan(session, current_id):
            if vb and vb.id not in seen_ids:
                add_node(vb)
                add_edge(current_id, vb.id, f"hướng dẫn {level+1}")
                stack.append((vb.id, level + 1))

    return nodes, edges