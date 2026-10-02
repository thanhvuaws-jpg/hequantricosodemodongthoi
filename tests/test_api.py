"""Kiểm thử lớp API và các tệp giao diện."""
import threading
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_thong_tin_may_chu():
    r = client.get("/api/thong-tin")
    assert r.status_code == 200
    d = r.json()
    assert d["may_chu"]["engine"] == "InnoDB"
    # mọi bảng của đề tài phải dùng InnoDB – MyISAM không có giao tác lẫn khóa dòng
    assert {b["bang"] for b in d["may_chu"]["cac_bang"]} >= {"chuyen_bay", "ve", "ghe"}
    assert all(b["engine"] == "InnoDB" for b in d["may_chu"]["cac_bang"])
    assert len(d["muc_co_lap"]) == 4


@pytest.mark.parametrize("duong_dan", [
    "/", "/static/style.css", "/static/chung.js", "/static/tab-datve.js",
    "/static/tab-colap.js", "/static/tab-sosanh.js",
])
def test_tep_giao_dien(duong_dan):
    r = client.get(duong_dan)
    assert r.status_code == 200
    assert len(r.content) > 500


def test_giao_dien_luon_duoc_kiem_tra_ban_moi():
    """Trình duyệt không được giữ bản JS/CSS cũ sau khi giao diện được cập nhật."""
    for duong_dan in ("/", "/static/tab-xungdot.js", "/static/style.css"):
        assert client.get(duong_dan).headers["cache-control"] == "no-cache"
    assert "cache-control" not in client.get("/api/trang-thai").headers


def test_tu_tao_lai_luoc_do_khi_thieu_bang():
    """Mô phỏng CSDL còn lược đồ cũ / thiếu bảng: ứng dụng phải tự tạo lại từ schema.sql."""
    from app import csdl
    conn = csdl.ket_noi()
    try:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS ve")
    finally:
        conn.close()
    assert csdl.dam_bao_luoc_do() is True
    assert csdl.dam_bao_luoc_do() is False, "lần thứ hai không được tạo lại nữa"
    bang = {b["bang"]: b["engine"] for b in csdl.thong_tin_may_chu()["cac_bang"]}
    assert bang == {"chuyen_bay": "InnoDB", "ve": "InnoDB", "ghe": "InnoDB"}


def test_chay_kich_ban_qua_api():
    r = client.post("/api/chay", json={"che_do": "nguyen_tu", "so_khach": 4, "ton_kho": 2, "think_ms": 0})
    assert r.status_code == 200
    d = r.json()
    assert d["tom_tat"]["so_ve_da_ban"] == 2
    assert {"su_kien", "ket_qua_khach", "cho_khoa", "khoa_quan_sat", "trang_thai_sau"} <= set(d)


@pytest.mark.parametrize("than,ma", [
    ({"che_do": "khong_ton_tai"}, 400),
    ({"che_do": "bi_quan", "muc_co_lap": "SNAPSHOT"}, 400),
    ({"che_do": "bi_quan", "so_khach": 0}, 422),
    ({"che_do": "bi_quan", "so_khach": 61}, 422),
    ({"che_do": "bi_quan", "think_ms": 5000}, 422),
    ({"che_do": "bi_quan", "so_khach": "mười"}, 422),
])
def test_tham_so_sai(than, ma):
    r = client.post("/api/chay", json=than)
    assert r.status_code == ma
    assert r.json()["detail"]


def test_thi_nghiem_qua_api():
    ds = client.get("/api/thi-nghiem").json()
    assert len(ds["thi_nghiem"]) == 6
    r = client.post("/api/thi-nghiem/chay", json={"ma": "doc_rac", "muc_co_lap": "READ UNCOMMITTED"})
    assert r.status_code == 200 and r.json()["xay_ra"] is True
    r = client.post("/api/thi-nghiem/chay", json={"ma": "khong_co", "muc_co_lap": "READ COMMITTED"})
    assert r.status_code == 400


def test_khao_sat_tham_so_sai():
    assert client.post("/api/khao-sat", json={"cac_muc": []}).status_code == 422
    assert client.post("/api/khao-sat", json={"cac_muc": [100]}).status_code == 400


def test_khong_cho_hai_kich_ban_chay_cung_luc():
    """Hai người bấm Chạy cùng lúc: người sau phải nhận 409 thay vì xóa dữ liệu của người trước."""
    ket_qua = {}

    def goi(ten, tre):
        time.sleep(tre)
        ket_qua[ten] = TestClient(app).post(
            "/api/chay", json={"che_do": "bi_quan", "so_khach": 8, "ton_kho": 4, "think_ms": 120}
        )

    t1 = threading.Thread(target=goi, args=("truoc", 0))
    t2 = threading.Thread(target=goi, args=("sau", 0.3))
    t1.start(); t2.start(); t1.join(); t2.join()
    assert ket_qua["truoc"].status_code == 200
    assert ket_qua["truoc"].json()["tom_tat"]["nhat_quan"]
    assert ket_qua["sau"].status_code == 409
    assert "đang có" in ket_qua["sau"].json()["detail"].lower()
    # sau khi lượt trước xong thì chạy lại được bình thường
    assert client.post("/api/chay", json={"che_do": "nguyen_tu", "so_khach": 2, "ton_kho": 1}).status_code == 200
