"""Kiểm thử 5 xung đột × 2 kịch bản (tab 1) và dữ liệu chụp từng bước cho hoạt hình."""
import pytest
from fastapi.testclient import TestClient

from app import xungdot as xd
from app.main import app

TAT_CA = [(ma, loai) for ma in xd.XUNG_DOT for loai in xd.LOAI_KICH_BAN]


@pytest.fixture(scope="module")
def ket_qua():
    """Chạy mỗi kịch bản một lần rồi dùng chung cho các test bên dưới."""
    return {(ma, loai): xd.chay_xung_dot(ma, loai) for ma, loai in TAT_CA}


def _su_kien(r, ma_buoc, loai=None):
    return next(e for e in r["nhat_ky"] if e["ma"] == ma_buoc and (loai is None or e["loai"] == loai))


def _dong(r, e, bang, khoa_chinh_gt, goc="moi_nhat"):
    t = e["trang_thai"][bang]
    return next((d for d in t[goc] if d[t["khoa_chinh"]] == khoa_chinh_gt), None)


# ----------------------------------------------------------- kết quả từng kịch bản
@pytest.mark.parametrize("ma,loai", TAT_CA)
def test_kich_ban_sai_xay_ra_kich_ban_dung_thi_khong(ket_qua, ma, loai):
    r = ket_qua[(ma, loai)]
    assert r["xay_ra"] is (loai == "sai"), r["giai_thich"]
    assert r["dung_ky_vong"]
    assert r["giai_thich"]


@pytest.mark.parametrize("ma,loai", TAT_CA)
def test_moi_su_kien_deu_co_anh_chup(ket_qua, ma, loai):
    """Hoạt hình cần trạng thái dữ liệu + bảng khóa sau MỖI sự kiện."""
    r = ket_qua[(ma, loai)]
    assert set(r["trang_thai_dau"]) == set(r["bang"])
    for e in r["nhat_ky"]:
        assert set(e["trang_thai"]) == set(r["bang"])
        assert "khoa" in e and "cho" in e
        for t in e["trang_thai"].values():
            assert t["da_commit"] and t["moi_nhat"]


@pytest.mark.parametrize("ma,loai", TAT_CA)
def test_dieu_phoi_hai_phien(ket_qua, ma, loai):
    r = ket_qua[(ma, loai)]
    buoc = xd.XUNG_DOT[ma]["kich_ban"][loai]["buoc"]
    xong = [e for e in r["nhat_ky"] if e["loai"] in ("xong", "xong_sau_chan", "bo_qua")]
    assert sorted(e["ma"] for e in xong) == sorted(b.ma for b in buoc)
    for p in "AB":
        assert [e["ma"] for e in xong if e["phien"] == p] == [b.ma for b in buoc if b.phien == p]
    assert sorted(e["ma"] for e in r["nhat_ky"] if e["loai"] == "bi_chan") == \
        sorted(e["ma"] for e in r["nhat_ky"] if e["loai"] == "xong_sau_chan")


@pytest.mark.parametrize("ma,loai", TAT_CA)
def test_dong_chua_commit_co_dung_mot_chu_khoa(ket_qua, ma, loai):
    """Bất biến: một dòng đang bị SỬA mà chưa commit thì phải có đúng một phiên giữ khóa X trên nó.
    (Dòng mới INSERT được bỏ qua: InnoDB chỉ đặt khóa ngầm, data_locks không liệt kê.)"""
    r = ket_qua[(ma, loai)]
    for e in r["nhat_ky"]:
        for bang, t in e["trang_thai"].items():
            pk = t["khoa_chinh"]
            commit = {str(d[pk]): d for d in t["da_commit"]}
            for d in t["moi_nhat"]:
                c = commit.get(str(d[pk]))
                if c is None or c == d:
                    continue
                chu = {k["phien"] for k in e["khoa"]
                       if k["bang"] == bang and k["trang_thai"] == "GRANTED" and k["loai_khoa"] == "RECORD"
                       and k["che_do_khoa"].startswith("X")
                       and str(k["du_lieu"]).split(", ")[-1] == str(d[pk])}
                assert len(chu) == 1, f"bước {e['thu_tu']} ({e['ma']}): dòng {d} có chủ khóa {chu}"


# ----------------------------------------------------------- chi tiết từng xung đột
def test_mat_cap_nhat(ket_qua):
    sai, dung = ket_qua[("mat_cap_nhat", "sai")], ket_qua[("mat_cap_nhat", "dung")]
    assert sai["ket_qua"]["K1"]["dong"] == [{"so_ghe_trong": 6}]
    assert not sai["tong_ket"]["so_lan_bi_chan"]
    assert dung["ket_qua"]["B2"]["bi_chan"], "FOR UPDATE của B phải chờ A"
    assert dung["ket_qua"]["B2"]["dong"] == [{"so_ghe_trong": 6}], "B phải đọc được giá trị mới sau khi A commit"
    assert dung["ket_qua"]["K1"]["dong"] == [{"so_ghe_trong": 5}]
    cho = _su_kien(dung, "B2", "bi_chan")["cho"]
    assert cho == [{"phien_cho": "B", "phien_giu": "A"}]


def test_doc_rac_hai_goc_nhin(ket_qua):
    """Khi B đã sửa nhưng chưa commit: bản đã commit vẫn là 7, bản mới nhất là 0."""
    for loai in ("sai", "dung"):
        r = ket_qua[("doc_rac", loai)]
        e = _su_kien(r, "B2")
        assert _dong(r, e, "chuyen_bay", 1, "da_commit")["so_ghe_trong"] == 7
        assert _dong(r, e, "chuyen_bay", 1, "moi_nhat")["so_ghe_trong"] == 0
    assert ket_qua[("doc_rac", "sai")]["ket_qua"]["A2"]["dong"] == [{"so_ghe_trong": 0}]
    assert ket_qua[("doc_rac", "dung")]["ket_qua"]["A2"]["dong"] == [{"so_ghe_trong": 7}]
    # sau khi B rollback, hai góc nhìn khớp lại
    e = _su_kien(ket_qua[("doc_rac", "sai")], "B3")
    t = e["trang_thai"]["chuyen_bay"]
    assert t["da_commit"] == t["moi_nhat"]


def test_doc_khong_lap_lai(ket_qua):
    gt = lambda r, m: r["ket_qua"][m]["dong"][0]["so_ghe_trong"]  # noqa: E731
    sai, dung = ket_qua[("doc_khong_lap_lai", "sai")], ket_qua[("doc_khong_lap_lai", "dung")]
    assert (gt(sai, "A2"), gt(sai, "A3")) == (7, 6)
    assert (gt(dung, "A2"), gt(dung, "A3")) == (7, 7)
    assert not dung["tong_ket"]["so_lan_bi_chan"], "REPEATABLE READ dùng MVCC, không ai phải chờ"


def test_bong_ma_gap_lock_va_dong_chen_do(ket_qua):
    sai, dung = ket_qua[("bong_ma", "sai")], ket_qua[("bong_ma", "dung")]
    assert len(sai["ket_qua"]["A3"]["dong"]) == 4 and not sai["tong_ket"]["so_lan_bi_chan"]
    assert len(dung["ket_qua"]["A3"]["dong"]) == 3
    e = _su_kien(dung, "B2", "bi_chan")
    a_gap = [k for k in e["khoa"] if k["phien"] == "A" and k["che_do_khoa"] == "X,GAP"]
    b_chen = [k for k in e["khoa"] if k["phien"] == "B" and "INSERT_INTENTION" in k["che_do_khoa"]
              and k["trang_thai"] == "WAITING"]
    assert a_gap and b_chen and a_gap[0]["du_lieu"] == b_chen[0]["du_lieu"]
    # INSERT đã vào chỉ mục chính (thấy ở READ UNCOMMITTED) dù đang kẹt ở chỉ mục phụ
    assert _dong(dung, e, "ve", 6, "moi_nhat") is not None
    assert _dong(dung, e, "ve", 6, "da_commit") is None


def test_deadlock(ket_qua):
    sai, dung = ket_qua[("deadlock", "sai")], ket_qua[("deadlock", "dung")]
    assert sai["tong_ket"]["loi"] == ["1213 deadlock"]
    nan_nhan = [m for m, r in sai["ket_qua"].items() if (r.get("loi") or {}).get("ten") == "deadlock"]
    assert len(nan_nhan) == 1
    nguoi_thang = "B" if nan_nhan[0][0] == "A" else "A"
    assert all(g["nguoi_giu"] == nguoi_thang for g in sai["ket_qua"]["K1"]["dong"])

    assert dung["tong_ket"]["loi"] == []
    assert dung["ket_qua"]["B2"]["bi_chan"]
    assert dung["ket_qua"]["B2"]["so_dong_khop"] == 0, "B chờ xong thì ghế đã có người giữ"
    assert all(g["nguoi_giu"] == "A" for g in dung["ket_qua"]["K1"]["dong"])


def test_khoa_quy_ve_dung_chu_so_huu_sau_deadlock(ket_qua):
    """Hồi quy: sau khi B bị hủy, khóa InnoDB trao cho A mang THREAD_ID của B.
    Phải quy khóa theo ENGINE_TRANSACTION_ID thì mới ra đúng chủ là A."""
    r = ket_qua[("deadlock", "sai")]
    nan_nhan = next(m for m, x in r["ket_qua"].items() if (x.get("loi") or {}).get("ten") == "deadlock")
    e = _su_kien(r, nan_nhan)
    nguoi_thang = "B" if nan_nhan[0] == "A" else "A"
    giu = {k["du_lieu"]: k["phien"] for k in e["khoa"]
           if k["loai_khoa"] == "RECORD" and k["trang_thai"] == "GRANTED"}
    if giu:  # người thắng đã được trao khóa ngay khi nạn nhân bị hủy
        assert set(giu.values()) == {nguoi_thang}


# ----------------------------------------------------------- ký hiệu lịch giao tác
LICH_KY_VONG = {
    # các lịch kinh điển trong giáo trình
    ("mat_cap_nhat", "sai"): "r₁(X) r₂(X) w₁(X) c₁ w₂(X) c₂",
    ("doc_rac", "sai"): "w₂(X) r₁(X) a₂ r₁(X) c₁",
    ("doc_khong_lap_lai", "sai"): "r₁(X) w₂(X) c₂ r₁(X) c₁",
    # bản đúng: B phải xin khóa và chờ (xl₂ bị chặn) rồi mới đọc
    ("mat_cap_nhat", "dung"): "xl₁(X) r₁(X) xl₂(X) w₁(X) c₁ r₂(X) w₂(X) c₂",
    ("deadlock", "dung"): "w₁(X) xl₂(X) w₁(Y) c₁ w₂(X) w₂(Y) c₂",
}


@pytest.mark.parametrize("ma,loai", list(LICH_KY_VONG))
def test_lich_ky_hieu_kinh_dien(ket_qua, ma, loai):
    r = ket_qua[(ma, loai)]
    assert " ".join(l["ky_hieu"] for l in r["lich"]) == LICH_KY_VONG[(ma, loai)]


def test_lich_deadlock_co_dung_mot_lan_huy(ket_qua):
    lich = ket_qua[("deadlock", "sai")]["lich"]
    huy = [l for l in lich if " a" in f" {l['ky_hieu']}"]
    assert len(huy) == 1, "đúng một giao tác bị hủy"
    nan_nhan = huy[0]["phien"]
    nguoi_thang = "B" if nan_nhan == "A" else "A"
    i = {"A": "₁", "B": "₂"}
    assert any(l["loai"] == "bi_chan" for l in lich), "phải có một bên bị chặn trước khi deadlock"
    assert not any(l["ky_hieu"] == f"c{i[nan_nhan]}" for l in lich), "giao tác đã hủy không được commit"
    assert lich[-1]["ky_hieu"] == f"c{i[nguoi_thang]}"


def test_ky_hieu_trong_ma_nguon():
    for x in xd.danh_sach_xung_dot().values():
        for kb in x["kich_ban"].values():
            for p in "AB":
                for d in kb["ma_nguon"][p]:
                    if d["la_cau_hinh"] or d["kiem_tra"] or d["sql"].startswith("START"):
                        assert d["ky_hieu"] == ""
                    else:
                        assert d["ky_hieu"], f"{d['ma']} thiếu ký hiệu"
                        so = "₁" if p == "A" else "₂"
                        assert so in d["ky_hieu"]
        assert x["doi_tuong"], "phải giải thích X / Y / P là gì"


# ----------------------------------------------------------- mã nguồn + API
def test_ma_nguon_moi_phien():
    ds = xd.danh_sach_xung_dot()
    assert [x["so"] for x in ds.values()] == [1, 2, 3, 4, 5]
    for ma, x in ds.items():
        assert set(x["kich_ban"]) == {"sai", "dung"}
        for loai, kb in x["kich_ban"].items():
            for p in "AB":
                dong = kb["ma_nguon"][p]
                assert dong[0]["la_cau_hinh"] and kb["muc_co_lap"] in dong[0]["sql"]
                assert len(dong) > 2
            # phải chỉ ra được chỗ khác biệt giữa sai và đúng
            co_diem_khac = any(d["diem_khac"] for p in "AB" for d in kb["ma_nguon"][p])
            assert co_diem_khac, f"{ma}/{loai} không đánh dấu dòng then chốt"


def test_cap_sai_dung_chi_khac_dung_cho_can_thiet():
    """Kịch bản đúng chỉ được khác kịch bản sai ở dòng then chốt (hoặc ở mức cô lập)."""
    for ma, x in xd.XUNG_DOT.items():
        sai, dung = x["kich_ban"]["sai"], x["kich_ban"]["dung"]
        if x["cau_hinh_la_diem_khac"]:
            assert sai["buoc"] is dung["buoc"] and sai["muc"] != dung["muc"]
        else:
            assert sai["muc"] == dung["muc"]
            assert {b.ma for b in sai["buoc"]} == {b.ma for b in dung["buoc"]}
            sai_theo_ma = {b.ma: b for b in sai["buoc"]}
            so_cho_khac = 0
            for b in dung["buoc"]:
                a = sai_theo_ma[b.ma]
                if a.sql_hien_thi() != b.sql_hien_thi():
                    so_cho_khac += 1
                    assert a.diem_khac and b.diem_khac, f"{ma}: bước {b.ma} khác nhau mà không được đánh dấu"
            assert so_cho_khac >= 1


def test_api_xung_dot():
    client = TestClient(app)
    d = client.get("/api/xung-dot").json()
    assert len(d["xung_dot"]) == 5
    r = client.post("/api/xung-dot/chay", json={"ma": "doc_rac", "loai": "sai"})
    assert r.status_code == 200 and r.json()["xay_ra"] is True
    assert client.post("/api/xung-dot/chay", json={"ma": "khong_co", "loai": "sai"}).status_code == 400
    assert client.post("/api/xung-dot/chay", json={"ma": "doc_rac", "loai": "tam_tam"}).status_code == 400
    assert client.post("/api/xung-dot/chay", json={"ma": "doc_rac"}).status_code == 422
    assert client.get("/static/tab-xungdot.js").status_code == 200
