"""Kiểm thử phòng thí nghiệm mức cô lập (tab 2).

Bảng KY_VONG là hành vi đã được ghi trong tài liệu chính thức của MySQL 8/9
(mục "Transaction Isolation Levels" và "Locks Set by Different SQL Statements").
"""
import pytest

from app import phongthinghiem as pt

RU, RC, RR, S = pt.CAC_MUC

KY_VONG = {
    #                   RU     RC     RR     S
    "doc_rac":           (True, False, False, False),
    "doc_khong_lap_lai": (True, True,  False, False),
    "bong_ma":           (True, True,  False, False),
    "bong_ma_doc_khoa":  (True, True,  False, False),
    "mat_cap_nhat":      (True, True,  True,  False),
    "doc_nhat_quan":     (False, False, True, False),
}


def _kiem_tra_dieu_phoi(r):
    """Bất biến của bộ điều phối hai phiên."""
    ma_cac_buoc = [b.ma for b in pt.THI_NGHIEM[r["ma"]]["buoc"]]
    ket_thuc = [e for e in r["nhat_ky"] if e["loai"] in ("xong", "xong_sau_chan", "bo_qua")]
    # 1. mỗi bước của kịch bản được thực hiện đúng một lần
    assert sorted(e["ma"] for e in ket_thuc) == sorted(ma_cac_buoc)
    # 2. trong mỗi phiên, các bước xong theo đúng thứ tự kịch bản
    for p in "AB":
        ky_vong = [b.ma for b in pt.THI_NGHIEM[r["ma"]]["buoc"] if b.phien == p]
        thuc_te = [e["ma"] for e in ket_thuc if e["phien"] == p]
        assert thuc_te == ky_vong, f"phiên {p} chạy sai thứ tự"
    # 3. không bước nào phải đợi tới hết giờ chờ khóa – nếu có là bộ điều phối bị kẹt
    for ma, kq in r["ket_qua"].items():
        assert (kq.get("loi") or {}).get("ten") != "het_gio", f"bước {ma} bị hết giờ chờ khóa"
    # 4. câu nào bị chặn thì sau đó phải được chạy tiếp
    bi_chan = [e["ma"] for e in r["nhat_ky"] if e["loai"] == "bi_chan"]
    xong_sau = [e["ma"] for e in r["nhat_ky"] if e["loai"] == "xong_sau_chan"]
    assert sorted(bi_chan) == sorted(xong_sau)
    # 5. bước bị hoãn thì phải được chạy bù
    hoan = [e["ma"] for e in r["nhat_ky"] if e["loai"] == "hoan"]
    chay_bu = [e["ma"] for e in r["nhat_ky"] if e.get("chay_bu") and e["loai"] != "hoan"]
    assert sorted(hoan) == sorted(chay_bu)


@pytest.mark.parametrize("ma", list(KY_VONG))
@pytest.mark.parametrize("vi_tri,muc", list(enumerate(pt.CAC_MUC)))
def test_ma_tran_khop_hanh_vi_mysql(ma, vi_tri, muc):
    r = pt.chay_thi_nghiem(ma, muc)
    assert r["xay_ra"] is KY_VONG[ma][vi_tri], r["giai_thich"]
    assert r["giai_thich"]
    _kiem_tra_dieu_phoi(r)


def test_serializable_chan_doc_rac_bang_cach_bat_cho():
    r = pt.chay_thi_nghiem("doc_rac", S)
    assert r["ket_qua"]["A2"]["bi_chan"]
    assert r["ket_qua"]["A2"]["dong"] == [{"so_ghe_trong": 7}]


def test_read_committed_khong_bi_chan_khi_doc():
    """MVCC: đọc thường không bao giờ phải chờ khóa ghi ở RC/RR."""
    for muc in (RC, RR):
        r = pt.chay_thi_nghiem("doc_rac", muc)
        assert not r["co_chan"]


def test_gap_lock_o_repeatable_read():
    r = pt.chay_thi_nghiem("bong_ma_doc_khoa", RR)
    chan = [e for e in r["nhat_ky"] if e["loai"] == "bi_chan"]
    assert [e["ma"] for e in chan] == ["B2"], "chỉ lệnh INSERT của B bị chặn"
    khoa = chan[0]["khoa"]
    # A giữ gap lock trên chỉ mục ma_chuyen, B chờ khóa insert intention vào đúng khoảng đó
    a_gap = [k for k in khoa if k["phien"] == "A" and k["chi_muc"] == "fk_ve_chuyen"
             and "GAP" in k["che_do_khoa"] and k["trang_thai"] == "GRANTED"]
    b_cho = [k for k in khoa if k["phien"] == "B" and "INSERT_INTENTION" in k["che_do_khoa"]
             and k["trang_thai"] == "WAITING"]
    assert a_gap and b_cho
    assert a_gap[0]["du_lieu"] == b_cho[0]["du_lieu"], "cùng một khoảng trống"
    assert chan[0]["cho"] == [{"phien_cho": "B", "phien_giu": "A"}]


def test_read_committed_khong_co_gap_lock():
    r = pt.chay_thi_nghiem("bong_ma_doc_khoa", RC)
    assert not r["co_chan"], "ở READ COMMITTED InnoDB không khóa khoảng trống nên INSERT không bị chặn"
    assert len(r["ket_qua"]["A3"]["dong"]) == 4


def test_serializable_pha_mat_cap_nhat_bang_deadlock():
    r = pt.chay_thi_nghiem("mat_cap_nhat", S)
    assert r["co_deadlock"]
    loi = [m for m in ("A3", "B3") if (r["ket_qua"][m].get("loi") or {}).get("ten") == "deadlock"]
    assert len(loi) == 1, "đúng một bên bị InnoDB chọn làm nạn nhân"
    assert r["ket_qua"]["K1"]["dong"] == [{"so_ghe_trong": 6}]


def test_repeatable_read_van_mat_cap_nhat():
    r = pt.chay_thi_nghiem("mat_cap_nhat", RR)
    assert r["xay_ra"] and r["khac_ly_thuyet"]
    a3, b3 = r["ket_qua"]["A3"], r["ket_qua"]["B3"]
    assert a3["loi"] is None and b3["loi"] is None, "cả hai UPDATE đều 'thành công'"
    # A đổi 7 -> 6. B ghi 6 đè lên 6: khớp 1 dòng nhưng MySQL báo 0 dòng thay đổi,
    # nên ứng dụng của B không có cách nào biết mình vừa làm mất cập nhật của A.
    assert (a3["so_dong_khop"], a3["so_dong_doi"]) == (1, 1)
    assert (b3["so_dong_khop"], b3["so_dong_doi"]) == (1, 0)
    assert b3["so_dong"] == 0
    assert "Changed: 0" in r["giai_thich"]
    assert r["ket_qua"]["K1"]["dong"] == [{"so_ghe_trong": 6}]


def test_cac_o_khac_ly_thuyet_deu_co_ghi_chu():
    for (ma, muc), ghi_chu in pt.GHI_CHU_MYSQL.items():
        r = pt.chay_thi_nghiem(ma, muc)
        assert r["khac_ly_thuyet"], f"{ma}@{muc} được ghi chú là khác lý thuyết nhưng thực tế lại khớp"
        assert r["ghi_chu_mysql"] == ghi_chu


def test_du_lieu_duoc_dat_lai_moi_lan():
    pt.chay_thi_nghiem("bong_ma", RC)             # lần này B chèn thêm một vé
    r = pt.chay_thi_nghiem("bong_ma", RC)
    assert r["ket_qua"]["A2"]["dong"] == [{"so_ve": 3}]


def test_buoc_phu_thuoc_bi_bo_qua_khi_thieu_du_lieu():
    tao_sql = pt._ghi_tru_mot("A2")
    assert tao_sql({}) is None
    assert tao_sql({"A2": {"dong": [{"so_ghe_trong": 7}], "loi": None}}) == \
        "UPDATE chuyen_bay SET so_ghe_trong = 6 WHERE ma_chuyen = 1"


def test_danh_sach_thi_nghiem():
    ds = pt.danh_sach_thi_nghiem()
    assert set(ds) == set(KY_VONG)
    for tn in ds.values():
        assert tn["buoc"] and all(b["sql"] for b in tn["buoc"])
        assert {b["phien"] for b in tn["buoc"]} == {"A", "B"}


@pytest.mark.parametrize("ma,muc", [("khong_co", RC), ("doc_rac", "SNAPSHOT"), ("doc_rac", "")])
def test_tham_so_sai(ma, muc):
    with pytest.raises(ValueError):
        pt.chay_thi_nghiem(ma, muc)
