"""Kiểm thử các kịch bản đặt vé đồng thời (tab 1)."""
import pytest

from app import kichban

CHE_DO_DUNG = ["bi_quan", "lac_quan", "nguyen_tu"]


def _theo_luong(su_kien):
    nhom = {}
    for e in su_kien:
        nhom.setdefault(e["luong"], []).append(e)
    return nhom


def _kiem_tra_dong_thoi_gian(kq):
    """Bất biến của biểu đồ diễn biến: trong một luồng các sự kiện không chồng lên nhau,
    luôn mở đầu bằng START TRANSACTION và kết thúc bằng COMMIT/ROLLBACK."""
    for luong, ds in _theo_luong(kq["su_kien"]).items():
        ds = sorted(ds, key=lambda e: e["bat_dau"])
        assert ds[0]["loai"] == "begin", f"{luong} không mở đầu bằng START TRANSACTION"
        assert ds[-1]["loai"] in ("commit", "rollback"), f"{luong} không kết thúc giao tác"
        for e in ds:
            assert 0 <= e["bat_dau"] <= e["ket_thuc"]
        for truoc, sau in zip(ds, ds[1:]):
            assert truoc["ket_thuc"] <= sau["bat_dau"] + 0.05, f"{luong}: sự kiện chồng lên nhau"


# ------------------------------------------------------------------ không khóa
def test_khong_khoa_gay_mat_cap_nhat_va_ban_vuot():
    kq = kichban.chay_kich_ban("khong_khoa", so_khach=12, ton_kho=5, think_ms=150)
    t = kq["tom_tat"]
    assert t["ban_vuot"] > 0
    assert not t["nhat_quan"]
    assert t["so_ve_da_ban"] == 12          # ai cũng tưởng mình mua được
    # bằng chứng của mất cập nhật: nhiều khách đọc được CÙNG một giá trị
    doc = [e["ghi_chu"].split(" – ")[0] for e in kq["su_kien"] if e["nhan"].startswith("đọc số ghế")]
    assert len(doc) == 12
    assert len(set(doc)) < len(doc)
    _kiem_tra_dong_thoi_gian(kq)


def test_khong_khoa_o_read_uncommitted_van_sai():
    t = kichban.chay_kich_ban("khong_khoa", 10, 5, 120, "READ UNCOMMITTED")["tom_tat"]
    assert t["ban_vuot"] > 0


def test_khong_khoa_o_serializable_thi_dung_nhung_sinh_deadlock():
    """SERIALIZABLE biến SELECT thường thành đọc có khóa S. Nhiều giao tác cùng giữ S
    rồi cùng xin nâng lên X -> deadlock, InnoDB hủy bớt, dữ liệu vẫn đúng."""
    t = kichban.chay_kich_ban("khong_khoa", 10, 5, 80, "SERIALIZABLE")["tom_tat"]
    assert t["nhat_quan"]
    assert t["ban_vuot"] == 0
    assert t["so_deadlock"] >= 1


# --------------------------------------------------------- ba cách đúng
@pytest.mark.parametrize("che_do", CHE_DO_DUNG)
@pytest.mark.parametrize("so_khach,ton_kho", [(12, 5), (4, 10), (1, 1), (6, 6)])
def test_cach_dung_luon_nhat_quan(che_do, so_khach, ton_kho):
    kq = kichban.chay_kich_ban(che_do, so_khach, ton_kho, think_ms=40)
    t = kq["tom_tat"]
    assert t["nhat_quan"], t
    assert t["ban_vuot"] == 0
    assert t["so_ve_da_ban"] == min(so_khach, ton_kho)
    assert t["so_thanh_cong"] == min(so_khach, ton_kho)
    assert t["so_het_ve"] == max(0, so_khach - ton_kho)
    assert t["so_loi"] == t["so_het_gio"] == t["so_bo_cuoc"] == t["so_deadlock"] == 0
    _kiem_tra_dong_thoi_gian(kq)


def test_theo_doi_khoa_khong_doc_anh_chup_cu():
    """Hồi quy: information_schema.innodb_trx chỉ làm mới bộ đệm khi đã >0,1 s không ai đọc.
    Nếu luồng theo dõi dùng bảng đó và đọc liên tục, nó sẽ mãi thấy ảnh chụp lúc chưa có
    giao tác nào. Ở đây ta cho luồng theo dõi chạy không một lúc rồi mới tạo cảnh chờ khóa."""
    import threading
    import time
    from app import csdl

    kichban.dat_lai_du_lieu(5)
    bo_ghi = kichban.BoGhi()
    theo_doi = kichban.TheoDoiKhoa(bo_ghi)
    theo_doi.start()
    theo_doi.san_sang.wait(5)
    time.sleep(0.4)                                   # ~15 lần đọc khi chưa có ai giữ khóa
    a = csdl.ket_noi(tu_dong_commit=False)
    b = csdl.ket_noi(tu_dong_commit=False)
    try:
        ma_a, ma_b = csdl.ma_ket_noi(a), csdl.ma_ket_noi(b)
        a.cursor().execute("SELECT * FROM chuyen_bay WHERE ma_chuyen = 1 FOR UPDATE")
        t = threading.Thread(target=lambda: b.cursor().execute(
            "SELECT * FROM chuyen_bay WHERE ma_chuyen = 1 FOR UPDATE"))
        t.start()
        time.sleep(0.4)
        assert any(c["conn_cho"] == ma_b and c["conn_giu"] == ma_a and c["dang_giu"]
                   for c in theo_doi.cho_khoa), \
            "luồng theo dõi không thấy cảnh chờ khóa đang diễn ra"
        a.rollback()
        t.join(5)
    finally:
        theo_doi.dung.set()
        theo_doi.join(2)
        b.rollback(); a.close(); b.close()


def test_bi_quan_ghi_nhan_ai_chan_ai():
    kq = kichban.chay_kich_ban("bi_quan", so_khach=8, ton_kho=4, think_ms=100)
    cho = [e for e in kq["su_kien"] if e["loai"] == "cho_khoa"]
    assert len(cho) >= 5, "khóa bi quan phải khiến các khách xếp hàng chờ nhau"
    # lấy mẫu mỗi 25 ms thì mọi lần chờ dài ≥100 ms đều phải có bằng chứng từ data_lock_waits
    cho_dai = [e for e in cho if e["ket_thuc"] - e["bat_dau"] >= 100]
    co_bang_chung = [e for e in cho_dai if e["bi_chan_boi"]]
    assert len(co_bang_chung) >= 0.8 * len(cho_dai), \
        f"chỉ {len(co_bang_chung)}/{len(cho_dai)} lần chờ có bằng chứng"
    # Tính loại trừ của khóa X: tại mỗi thời điểm chỉ MỘT người giữ khóa trên dòng chuyen_bay.
    # Nhưng một câu truy vấn trên performance_schema KHÔNG phải ảnh chụp nguyên tử: nó đọc từng
    # dòng ở những thời điểm hơi lệch nhau. Nếu chạy trúng lúc khóa đang được chuyển giao, một
    # mẫu có thể thấy cả người giữ cũ lẫn người giữ mới. Vì vậy điều kiện đúng là: mẫu nào thấy
    # hai người thì phải đúng là khoảnh khắc chuyển giao giữa người giữ liền trước và liền sau.
    giu_theo_moc = {}
    for c in kq["cho_khoa"]:
        if c["dang_giu"]:
            giu_theo_moc.setdefault(c["moc"], set()).add(c["ten_giu"])
    assert giu_theo_moc, "phải quan sát được người đang giữ khóa"
    cac_mau = [giu_theo_moc[m] for m in sorted(giu_theo_moc)]
    don = [i for i, ds in enumerate(cac_mau) if len(ds) == 1]
    assert len(don) >= 0.8 * len(cac_mau), f"quá nhiều mẫu thấy nhiều người cùng giữ: {giu_theo_moc}"
    for i, ds in enumerate(cac_mau):
        if len(ds) == 1:
            continue
        truoc = next((cac_mau[j] for j in reversed(don) if j < i), set())
        sau = next((cac_mau[j] for j in don if j > i), set())
        assert len(ds) == 2 and ds <= truoc | sau, \
            f"mẫu thứ {i} thấy {ds} cùng giữ khóa X nhưng không phải lúc chuyển giao {truoc} → {sau}"
    # Hàng đợi tiến lên: người giữ khóa thay đổi theo thời gian
    assert len({next(iter(cac_mau[i])) for i in don}) >= 3

    theo_luong = _theo_luong(kq["su_kien"])
    for e in co_bang_chung:
        assert e["luong"] not in e["bi_chan_boi"], "một giao tác không thể tự chặn chính nó"
        # người bị cho là "đang chặn" phải thực sự có giao tác đang mở trong khoảng đó
        for ai in e["bi_chan_boi"]:
            ds = theo_luong[ai]
            mo = min(x["bat_dau"] for x in ds)
            dong = max(x["ket_thuc"] for x in ds)
            assert mo <= e["ket_thuc"] and dong >= e["bat_dau"], \
                f"{ai} được ghi là chặn {e['luong']} nhưng không có giao tác mở lúc đó"
    # bảng khóa phải có khóa X trên dòng chuyen_bay đang được chờ
    assert any(k["bang"] == "chuyen_bay" and k["loai_khoa"] == "RECORD"
               and k["che_do_khoa"].startswith("X") and k["trang_thai"] == "WAITING"
               for k in kq["khoa_quan_sat"])
    # khóa bi quan thì không ai phải thử lại
    assert kq["tom_tat"]["so_lan_thu_lai"] == 0


def test_lac_quan_phai_thu_lai_khi_tranh_chap():
    t = kichban.chay_kich_ban("lac_quan", so_khach=10, ton_kho=5, think_ms=60)["tom_tat"]
    assert t["nhat_quan"]
    assert t["so_lan_thu_lai"] > 0


def test_nguyen_tu_khong_thu_lai_khong_deadlock():
    t = kichban.chay_kich_ban("nguyen_tu", so_khach=20, ton_kho=7, think_ms=0)["tom_tat"]
    assert t["nhat_quan"] and t["so_ve_da_ban"] == 7
    assert t["so_lan_thu_lai"] == 0 and t["so_deadlock"] == 0


def test_so_luong_cuc_dai_60_khach():
    t = kichban.chay_kich_ban("nguyen_tu", so_khach=60, ton_kho=25, think_ms=0)["tom_tat"]
    assert t["nhat_quan"] and t["so_ve_da_ban"] == 25


# ------------------------------------------------------------------ deadlock
def test_deadlock_duoc_innodb_phat_hien_va_pha_vong():
    kq = kichban.chay_kich_ban("deadlock", so_khach=6, ton_kho=5, think_ms=100)
    t = kq["tom_tat"]
    assert t["so_deadlock"] >= 1
    assert t["so_het_gio"] == 0, "InnoDB phải phát hiện ngay chứ không đợi hết giờ chờ khóa"
    assert t["so_thanh_cong"] + t["so_deadlock"] == 6
    loi = [e for e in kq["su_kien"] if e["loai"] == "deadlock"]
    assert loi and all("1213" in e["ghi_chu"] for e in loi)
    # người thắng giữ được cả hai ghế
    ghe = kq["trang_thai_sau"]["ghe"]
    assert all(g["trang_thai"] == "dang_giu" for g in ghe)
    _kiem_tra_dong_thoi_gian(kq)


# ------------------------------------------------------------ kiểm tra tham số
@pytest.mark.parametrize("tham_so", [
    dict(che_do="khong_ton_tai", so_khach=5, ton_kho=5),
    dict(che_do="bi_quan", so_khach=0, ton_kho=5),
    dict(che_do="bi_quan", so_khach=61, ton_kho=5),
    dict(che_do="bi_quan", so_khach=5, ton_kho=0),
    dict(che_do="bi_quan", so_khach=5, ton_kho=5, think_ms=-1),
    dict(che_do="bi_quan", so_khach=5, ton_kho=5, muc_co_lap="SNAPSHOT"),
])
def test_tham_so_sai_bi_tu_choi(tham_so):
    with pytest.raises(ValueError):
        kichban.chay_kich_ban(**tham_so)


@pytest.mark.parametrize("dau_vao,ky_vong", [
    ("read committed", "READ COMMITTED"),
    ("REPEATABLE-READ", "REPEATABLE READ"),
    ("serializable", "SERIALIZABLE"),
    ("", None),
    (None, None),
])
def test_chuan_hoa_muc_co_lap(dau_vao, ky_vong):
    from app import csdl
    assert csdl.chuan_hoa_muc_co_lap(dau_vao) == ky_vong


def test_muc_co_lap_thuc_su_duoc_ap_dung():
    from app import csdl
    for muc in csdl.MUC_CO_LAP_HOP_LE:
        conn = csdl.ket_noi(muc_co_lap=muc)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT @@transaction_isolation AS m")
                assert cur.fetchone()["m"] == muc.replace(" ", "-")
        finally:
            conn.close()


# --------------------------------------------------------- so sánh / khảo sát
def test_so_sanh_che_do():
    d = kichban.so_sanh_che_do(so_khach=10, ton_kho=5, think_ms=100, so_lan=2)
    k = d["ket_qua"]
    assert set(k) == set(kichban.CHE_DO_DAT_VE)
    assert k["khong_khoa"]["so_lan_sai"] >= 1
    for cd in CHE_DO_DUNG:
        assert k[cd]["so_lan_sai"] == 0
        assert k[cd]["thoi_gian_min"] <= k[cd]["thoi_gian_tb"] <= k[cd]["thoi_gian_max"]
    # khóa bi quan tuần tự hóa nên phải chậm hơn UPDATE nguyên tử
    assert k["bi_quan"]["thoi_gian_tb"] > k["nguyen_tu"]["thoi_gian_tb"]


def test_khao_sat_theo_so_khach():
    d = kichban.khao_sat_theo_so_khach([8, 4], think_ms=20)
    assert d["cac_muc"] == [4, 8]
    for cd in kichban.CHE_DO_DAT_VE:
        assert [p["so_khach"] for p in d["chuoi"][cd]] == [4, 8]
        assert [p["ton_kho"] for p in d["chuoi"][cd]] == [2, 4]


@pytest.mark.parametrize("cac_muc", [[], [1], [61], [2, 3, 4, 5, 6, 7, 8]])
def test_khao_sat_tu_choi_muc_sai(cac_muc):
    with pytest.raises(ValueError):
        kichban.khao_sat_theo_so_khach(cac_muc, 10)
