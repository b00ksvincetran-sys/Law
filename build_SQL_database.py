from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import DateTime
import os

# KẾT NỐI CƠ SỞ DỮ LIỆU POSTGRES (SUPABASE)
# Ưu tiên lấy từ biến môi trường (dùng khi deploy lên Streamlit Cloud)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Khi chạy local, dùng config_local.py (file này KHÔNG đưa lên GitHub)
    from config_local import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False)
Base = declarative_base()

# Bảng cha: PhapLuat
class PhapLuat(Base):
    __tablename__ = 'phap_luat'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ten_van_ban = Column(String, nullable=False)
    so_hieu = Column(String, nullable=True)
    loai_van_ban = Column(String, nullable=False)
    ngay_ban_hanh = Column(String, nullable=True)
    ngay_hieu_luc = Column(String, nullable=True)
    tinh_trang = Column(String, nullable=True)
    noi_ban_hanh = Column(String, nullable=True)
    nguoi_ky = Column(String, nullable=True)
    link = Column(String, nullable=False, unique=True)
    van_ban_duoc_huong_dan = Column(String, nullable=True)
    van_ban_duoc_hop_nhat = Column(String, nullable=True)
    van_ban_bi_sua_doi_bo_sung = Column(String, nullable=True)
    van_ban_bi_dinh_chinh = Column(String, nullable=True)
    van_ban_bi_thay_the = Column(String, nullable=True)
    van_ban_duoc_dan_chieu = Column(String, nullable=True)
    van_ban_duoc_can_cu = Column(String, nullable=True)
    van_ban_thay_the = Column(String, nullable=True)
    van_ban_sua_doi_bo_sung = Column(String, nullable=True)
    van_ban_hop_nhat = Column(String, nullable=True)
    van_ban_huong_dan = Column(String, nullable=True)
    last_updated = Column(DateTime, nullable=True)


class VanBanHuongDan(Base):
    __tablename__ = 'van_ban_huong_dan'
    id = Column(Integer, primary_key=True, autoincrement=True)
    van_ban_duoc_huong_dan_id = Column(Integer, ForeignKey('phap_luat.id'), nullable=False)
    Van_ban_huong_dan_id = Column(Integer, ForeignKey('phap_luat.id'), nullable=False)

class VanBanSuadoiBoSung(Base):
    __tablename__ = 'van_ban_sua_doi_bo_sung'
    id = Column(Integer, primary_key=True, autoincrement=True)
    van_ban_bi_sua_doi_bo_sung_id = Column(Integer, ForeignKey('phap_luat.id'), nullable=False)
    van_ban_sua_doi_bo_sung_id = Column(Integer, ForeignKey('phap_luat.id'), nullable=False)

class VanBanHopNhat(Base):
    __tablename__ = 'van_ban_hop_nhat'
    id = Column(Integer, primary_key=True, autoincrement=True)
    van_ban_duoc_hop_nhat_id = Column(Integer, ForeignKey('phap_luat.id'), nullable=False)
    van_ban_hop_nhat_id = Column(Integer, ForeignKey('phap_luat.id'), nullable=False)

class VanBanThayThe(Base):
    __tablename__ = 'van_ban_thay_the'
    id = Column(Integer, primary_key=True, autoincrement=True)
    van_ban_bi_thay_the_id = Column(Integer, ForeignKey('phap_luat.id'), nullable=False)
    van_ban_thay_the_id = Column(Integer, ForeignKey('phap_luat.id'), nullable=False)

class VanBanDinhChinh(Base):
    __tablename__ = 'van_ban_dinh_chinh'
    id = Column(Integer, primary_key=True, autoincrement=True)
    van_ban_duoc_dinh_chinh_id = Column(Integer, ForeignKey('phap_luat.id'), nullable=False)
    van_ban_dinh_chinh_id = Column(Integer, ForeignKey('phap_luat.id'), nullable=False)

class VanBanDanChieu(Base):
    __tablename__ = 'van_ban_duoc_dan_chieu'
    id = Column(Integer, primary_key=True, autoincrement=True)
    van_ban_dan_chieu_id = Column(Integer, ForeignKey('phap_luat.id'), nullable=False)
    van_ban_duoc_dan_chieu_id = Column(Integer, ForeignKey('phap_luat.id'), nullable=False)

class VanBanCanCu(Base):
    __tablename__ = 'van_ban_can_cu'
    id = Column(Integer, primary_key=True, autoincrement=True)
    van_ban_can_cu_id = Column(Integer, ForeignKey('phap_luat.id'), nullable=False)
    van_ban_duoc_can_cu_id = Column(Integer, ForeignKey('phap_luat.id'), nullable=False)

# Tạo Session
Session = sessionmaker(bind=engine)
session = Session()


