"""Năm xung đột kinh điển khi truy xuất đồng thời.

Mỗi xung đột có hai kịch bản chạy trên cùng dữ liệu, cùng thứ tự đan xen:
  * SAI : cách làm khiến xung đột xảy ra;
  * ĐÚNG: thay đổi tối thiểu (một mệnh đề, một mức cô lập, một thứ tự khóa)
          đủ để ngăn xung đột đó.

Kịch bản được chạy trên MySQL thật bằng bộ điều phối hai phiên của phòng thí
nghiệm. Sau mỗi bước, trạng thái dữ liệu (đã commit / mới nhất) và bảng khóa
được chụp lại để giao diện phát lại dưới dạng hoạt hình.
"""
import re

from .phongthinghiem import (
    GHE_BAN_DAU, SQL_DOC_GHE, Buoc, _bi_chan, _dg_bong_ma_doc_khoa, _dg_doc_khong_lap_lai,
    _dg_doc_rac, _dg_mat_cap_nhat, _ghi_tru_mot, _loi, dat_du_lieu_lab, thuc_thi_hai_phien,
)


# ------------------------------------------------------- ký hiệu lịch giao tác
# Viết mỗi thao tác theo ký hiệu của giáo trình "giao tác và lịch giao tác":
#   r₁(X) đọc X, w₁(X) ghi X, xl₁(X) xin khóa ghi X, c₁ commit, a₁ hủy (abort)
#   chỉ số 1 = phiên A (T₁), 2 = phiên B (T₂)
_CHI_SO = {"A": "₁", "B": "₂"}


def _doi_tuong(sql: str) -> str:
    """Đơn vị dữ liệu mà câu lệnh đụng tới, đặt tên ngắn X / Y / P."""
    m = re.search(r"\bMA_GHE = (\d+)", sql)
    if " GHE " in f" {sql} " or sql.startswith("UPDATE GHE"):
        return {"1": "X", "2": "Y"}.get(m[1], "?") if m else "X,Y"
    if "FROM VE" in sql or "INTO VE" in sql:
        return "P"   # tập vé của một chuyến bay – một "vị từ" chứ không phải một dòng
    return "X"


def ky_hieu_lich(sql: str, phien: str) -> str:
    i = _CHI_SO[phien]
    s = " ".join(sql.upper().split())
    if s.startswith("COMMIT"):
        return f"c{i}"
    if s.startswith("ROLLBACK"):
        return f"a{i}"
    if s.startswith(("START", "SET")):
        return ""
    x = _doi_tuong(s)
    if s.startswith("SELECT"):
        return f"xl{i}({x}) r{i}({x})" if "FOR UPDATE" in s else f"r{i}({x})"
    if s.startswith(("UPDATE", "INSERT", "DELETE")):
        return f"w{i}({x})"
    return ""


# ------------------------------------------------------------------ deadlock
def _giu_ghe(phien: str, ma_ghe: int) -> str:
    return (f"UPDATE ghe SET trang_thai = 'dang_giu', nguoi_giu = '{phien}' "
            f"WHERE ma_ghe = {ma_ghe} AND trang_thai = 'trong'")


SQL_XEM_GHE = "SELECT so_ghe, trang_thai, nguoi_giu FROM ghe ORDER BY ma_ghe"


def _dg_deadlock(kq):
    ghe = (kq.get("K1") or {}).get("dong") or []
    cuoi = ", ".join(f"ghế {g['so_ghe']} – {g['nguoi_giu'] or 'trống'}" for g in ghe) or "không rõ"
    nan_nhan = [m for m in ("A2", "A3", "B2", "B3") if _loi(kq, m) == "deadlock"]
    if nan_nhan:
        p = nan_nhan[0][0]
        con_lai = "B" if p == "A" else "A"
        return True, (
            "A giữ ghế 12A rồi xin ghế 12B, còn B giữ ghế 12B rồi xin ghế 12A: mỗi bên đang giữ đúng "
            "thứ bên kia cần, hai bên chờ nhau thành vòng tròn. InnoDB phát hiện vòng chờ NGAY "
            f"(không đợi hết innodb_lock_wait_timeout), chọn {p} làm nạn nhân và ROLLBACK toàn bộ "
            f"giao tác của {p} với lỗi 1213. Nhờ vậy {con_lai} chạy tiếp được. "
            f"Kết quả cuối: {cuoi}. Ứng dụng phía {p} bắt buộc phải bắt lỗi và chạy lại giao tác."
        ), nan_nhan + ["K1"]
    if any(_loi(kq, m) for m in kq):
        return None, "Có lỗi khác ngoài deadlock, không kết luận được.", list(kq)
    if _bi_chan(kq, "B2"):
        b2 = kq.get("B2") or {}
        return False, (
            "Cả A và B đều xin ghế 12A trước rồi mới tới ghế 12B. B phải chờ A ở ghế 12A, nhưng A không "
            "cần thứ gì B đang giữ nên KHÔNG có vòng chờ – chỉ là xếp hàng bình thường. A giữ xong "
            "cả hai ghế và commit; B được chạy tiếp, đọc lại dòng mới nhất và thấy ghế đã có người "
            f"giữ (Rows matched: {b2.get('so_dong_khop', 0)}) nên không giữ được ghế nào – đúng "
            f"nghiệp vụ, không có lỗi. Kết quả cuối: {cuoi}."
        ), ["B2", "K1"]
    return False, f"Không xảy ra deadlock. Kết quả cuối: {cuoi}.", ["K1"]


# --------------------------------------------------------- các xung đột
XUNG_DOT = {
    "mat_cap_nhat": {
        "so": 1,
        "ten": "Mất cập nhật",
        "ten_en": "Lost update",
        "van_de": "Hai giao tác cùng đọc một giá trị, cùng tự tính rồi cùng ghi đè. Thay đổi của "
                  "người ghi trước bị người ghi sau xóa mất – bán 2 vé nhưng số ghế chỉ giảm 1.",
        "doi_tuong": {"X": "số ghế trống của chuyến VN-808 (cột so_ghe_trong, dòng ma_chuyen = 1)"},
        "bang": ["chuyen_bay"],
        "danh_gia": _dg_mat_cap_nhat,
        "cau_hinh_la_diem_khac": False,
        "khac_biet": "Chỉ thêm FOR UPDATE vào câu SELECT, mức cô lập giữ nguyên REPEATABLE READ. "
                     "Điều này cho thấy mức cô lập mặc định của MySQL không tự chống được mất cập nhật.",
        "kich_ban": {
            "sai": {
                "tieu_de": "Đọc thường rồi ghi đè",
                "muc": "REPEATABLE READ",
                "cach_lam": "SELECT thường không đặt khóa nào. Cả hai cùng đọc được 7, cùng ghi 6.",
                "buoc": [
                    Buoc("A1", "A", "START TRANSACTION", "A mở giao tác"),
                    Buoc("B1", "B", "START TRANSACTION", "B mở giao tác"),
                    Buoc("A2", "A", SQL_DOC_GHE, "A đọc số ghế còn – đọc thường, không khóa",
                         diem_khac=True),
                    Buoc("B2", "B", SQL_DOC_GHE, "B cũng đọc số ghế còn", diem_khac=True),
                    Buoc("A3", "A", _ghi_tru_mot("A2"), "A bán 1 vé: ghi lại giá trị đã đọc − 1",
                         "UPDATE chuyen_bay SET so_ghe_trong = <A đọc được − 1> WHERE ma_chuyen = 1"),
                    Buoc("A4", "A", "COMMIT", "A commit"),
                    Buoc("B3", "B", _ghi_tru_mot("B2"), "B bán 1 vé: ghi lại giá trị đã đọc − 1",
                         "UPDATE chuyen_bay SET so_ghe_trong = <B đọc được − 1> WHERE ma_chuyen = 1"),
                    Buoc("B4", "B", "COMMIT", "B commit"),
                    Buoc("K1", "A", SQL_DOC_GHE, "Kiểm tra: lẽ ra phải còn 5 ghế"),
                ],
            },
            "dung": {
                "tieu_de": "Khóa dòng ngay khi đọc – SELECT … FOR UPDATE",
                "muc": "REPEATABLE READ",
                "cach_lam": "FOR UPDATE đặt khóa X ngay lúc đọc. Người đọc sau phải chờ người trước "
                            "commit rồi mới đọc được giá trị mới.",
                "buoc": [
                    Buoc("A1", "A", "START TRANSACTION", "A mở giao tác"),
                    Buoc("B1", "B", "START TRANSACTION", "B mở giao tác"),
                    Buoc("A2", "A", SQL_DOC_GHE + " FOR UPDATE", "A đọc và KHÓA dòng chuyến bay",
                         diem_khac=True),
                    Buoc("B2", "B", SQL_DOC_GHE + " FOR UPDATE", "B cũng muốn đọc và khóa dòng đó",
                         diem_khac=True),
                    Buoc("A3", "A", _ghi_tru_mot("A2"), "A bán 1 vé: ghi lại giá trị đã đọc − 1",
                         "UPDATE chuyen_bay SET so_ghe_trong = <A đọc được − 1> WHERE ma_chuyen = 1"),
                    Buoc("A4", "A", "COMMIT", "A commit – nhả khóa"),
                    Buoc("B3", "B", _ghi_tru_mot("B2"), "B bán 1 vé: ghi lại giá trị đã đọc − 1",
                         "UPDATE chuyen_bay SET so_ghe_trong = <B đọc được − 1> WHERE ma_chuyen = 1"),
                    Buoc("B4", "B", "COMMIT", "B commit"),
                    Buoc("K1", "A", SQL_DOC_GHE, "Kiểm tra: phải còn 5 ghế"),
                ],
            },
        },
    },
    "doc_rac": {
        "so": 2,
        "ten": "Đọc dữ liệu rác",
        "ten_en": "Dirty read",
        "van_de": "A đọc được thay đổi mà B chưa commit. Sau đó B hủy bỏ, nên A đã dựa vào một "
                  "dữ liệu chưa từng tồn tại chính thức.",
        "doi_tuong": {"X": "số ghế trống của chuyến VN-808 (cột so_ghe_trong, dòng ma_chuyen = 1)"},
        "bang": ["chuyen_bay"],
        "danh_gia": _dg_doc_rac,
        "cau_hinh_la_diem_khac": True,
        "khac_biet": "Câu lệnh giống hệt nhau, chỉ đổi mức cô lập từ READ UNCOMMITTED lên READ COMMITTED. "
                     "InnoDB dựng lại bản đã commit từ undo log (MVCC) nên A không phải chờ B.",
        "kich_ban": {},
    },
    "doc_khong_lap_lai": {
        "so": 3,
        "ten": "Đọc không lặp lại",
        "ten_en": "Non-repeatable read",
        "van_de": "Trong cùng một giao tác, A đọc một dòng hai lần nhưng ra hai giá trị khác nhau "
                  "vì giữa hai lần đọc B đã sửa và commit.",
        "doi_tuong": {"X": "số ghế trống của chuyến VN-808 (cột so_ghe_trong, dòng ma_chuyen = 1)"},
        "bang": ["chuyen_bay"],
        "danh_gia": _dg_doc_khong_lap_lai,
        "cau_hinh_la_diem_khac": True,
        "khac_biet": "Câu lệnh giống hệt nhau, chỉ đổi từ READ COMMITTED lên REPEATABLE READ. "
                     "A dùng lại một snapshot suốt giao tác, B vẫn sửa và commit bình thường, không ai phải chờ.",
        "kich_ban": {},
    },
    "bong_ma": {
        "so": 4,
        "ten": "Bóng ma",
        "ten_en": "Phantom read",
        "van_de": "A đã khóa toàn bộ vé của chuyến VN-808, vậy mà B vẫn chèn được một vé mới vào đúng "
                  "chuyến đó. Lần khóa sau, A thấy xuất hiện thêm một dòng 'bóng ma'.",
        "doi_tuong": {"P": "tập vé của chuyến VN-808 (mọi dòng ve có ma_chuyen = 1, kể cả dòng sắp được chèn)"},
        "bang": ["ve"],
        "danh_gia": _dg_bong_ma_doc_khoa,
        "cau_hinh_la_diem_khac": True,
        "khac_biet": "Câu lệnh giống hệt nhau. Ở READ COMMITTED, InnoDB chỉ khóa các dòng đang có; "
                     "ở REPEATABLE READ nó khóa cả khoảng trống giữa các dòng (gap lock), nên B không chèn được.",
        "kich_ban": {},
    },
    "deadlock": {
        "so": 5,
        "ten": "Khóa chết",
        "ten_en": "Deadlock",
        "van_de": "Hai giao tác mỗi bên giữ một tài nguyên và chờ tài nguyên bên kia đang giữ. "
                  "Không ai nhường ai, nên InnoDB buộc phải hủy một giao tác.",
        "doi_tuong": {"X": "ghế 12A (dòng ghe có ma_ghe = 1)", "Y": "ghế 12B (dòng ghe có ma_ghe = 2)"},
        "bang": ["ghe"],
        "danh_gia": _dg_deadlock,
        "cau_hinh_la_diem_khac": False,
        "khac_biet": "Chỉ đổi THỨ TỰ khóa của B: luôn khóa ghế có mã nhỏ trước. Khi mọi giao tác khóa "
                     "tài nguyên theo cùng một thứ tự thì không thể hình thành vòng chờ.",
        "kich_ban": {
            "sai": {
                "tieu_de": "Hai bên khóa ghế theo thứ tự ngược nhau",
                "muc": "REPEATABLE READ",
                "cach_lam": "A giữ ghế 12A rồi xin 12B, B giữ ghế 12B rồi xin 12A.",
                "buoc": [
                    Buoc("A1", "A", "START TRANSACTION", "A mở giao tác"),
                    Buoc("B1", "B", "START TRANSACTION", "B mở giao tác"),
                    Buoc("A2", "A", _giu_ghe("A", 1), "A giữ ghế 12A"),
                    Buoc("B2", "B", _giu_ghe("B", 2), "B giữ ghế 12B trước", diem_khac=True),
                    Buoc("A3", "A", _giu_ghe("A", 2), "A xin thêm ghế 12B (B đang giữ)"),
                    Buoc("B3", "B", _giu_ghe("B", 1), "B xin thêm ghế 12A (A đang giữ)",
                         diem_khac=True),
                    Buoc("A4", "A", "COMMIT", "A commit"),
                    Buoc("B4", "B", "COMMIT", "B commit"),
                    Buoc("K1", "A", SQL_XEM_GHE, "Kiểm tra ai giữ ghế nào"),
                ],
            },
            "dung": {
                "tieu_de": "Mọi giao tác khóa ghế theo cùng một thứ tự",
                "muc": "REPEATABLE READ",
                "cach_lam": "Cả A và B đều khóa ghế 12A trước rồi mới tới 12B.",
                "buoc": [
                    Buoc("A1", "A", "START TRANSACTION", "A mở giao tác"),
                    Buoc("B1", "B", "START TRANSACTION", "B mở giao tác"),
                    Buoc("A2", "A", _giu_ghe("A", 1), "A giữ ghế 12A"),
                    Buoc("B2", "B", _giu_ghe("B", 1), "B cũng bắt đầu từ ghế 12A", diem_khac=True),
                    Buoc("A3", "A", _giu_ghe("A", 2), "A giữ tiếp ghế 12B"),
                    Buoc("A4", "A", "COMMIT", "A commit – nhả khóa"),
                    Buoc("B3", "B", _giu_ghe("B", 2), "B xin tiếp ghế 12B", diem_khac=True),
                    Buoc("B4", "B", "COMMIT", "B commit"),
                    Buoc("K1", "A", SQL_XEM_GHE, "Kiểm tra ai giữ ghế nào"),
                ],
            },
        },
    },
}


# Ba xung đột chỉ khác nhau ở mức cô lập: dùng chung kịch bản của phòng thí nghiệm
def _theo_muc(buoc_goc, tieu_de_sai, muc_sai, cach_sai, tieu_de_dung, muc_dung, cach_dung):
    return {
        "sai": {"tieu_de": tieu_de_sai, "muc": muc_sai, "cach_lam": cach_sai, "buoc": buoc_goc},
        "dung": {"tieu_de": tieu_de_dung, "muc": muc_dung, "cach_lam": cach_dung, "buoc": buoc_goc},
    }


def _nap_kich_ban_theo_muc():
    from .phongthinghiem import THI_NGHIEM
    XUNG_DOT["doc_rac"]["kich_ban"] = _theo_muc(
        THI_NGHIEM["doc_rac"]["buoc"],
        "READ UNCOMMITTED", "READ UNCOMMITTED",
        "Ở mức này, SELECT đọc thẳng bản mới nhất trong InnoDB, kể cả bản chưa commit.",
        "READ COMMITTED", "READ COMMITTED",
        "Mỗi SELECT chỉ thấy dữ liệu đã commit, dựng lại từ undo log nếu cần.",
    )
    XUNG_DOT["doc_khong_lap_lai"]["kich_ban"] = _theo_muc(
        THI_NGHIEM["doc_khong_lap_lai"]["buoc"],
        "READ COMMITTED", "READ COMMITTED",
        "Mỗi câu SELECT lấy một snapshot MỚI, nên thấy được thay đổi B vừa commit.",
        "REPEATABLE READ", "REPEATABLE READ",
        "Snapshot tạo ở lần đọc đầu tiên được dùng lại suốt giao tác.",
    )
    XUNG_DOT["bong_ma"]["kich_ban"] = _theo_muc(
        THI_NGHIEM["bong_ma_doc_khoa"]["buoc"],
        "READ COMMITTED – chỉ khóa dòng", "READ COMMITTED",
        "FOR UPDATE chỉ khóa các dòng đang tồn tại, khoảng trống giữa chúng vẫn mở.",
        "REPEATABLE READ – khóa cả khoảng trống", "REPEATABLE READ",
        "FOR UPDATE đặt next-key lock: khóa dòng + khoảng trống, chặn mọi lệnh chèn vào vùng đó.",
    )


_nap_kich_ban_theo_muc()
LOAI_KICH_BAN = ("sai", "dung")


def _ma_nguon(xd: dict, kb: dict) -> dict:
    """Mã SQL của từng phiên, theo đúng thứ tự phiên đó gửi đi."""
    kq = {}
    for p in "AB":
        kq[p] = [{
            "ma": f"{p}0", "sql": f"SET SESSION TRANSACTION ISOLATION LEVEL {kb['muc']}",
            "mo_ta": "cấu hình mức cô lập cho phiên", "la_cau_hinh": True,
            "diem_khac": xd["cau_hinh_la_diem_khac"], "kiem_tra": False, "ky_hieu": "",
        }] + [{
            "ma": b.ma, "sql": b.sql_hien_thi(), "mo_ta": b.mo_ta, "la_cau_hinh": False,
            "diem_khac": b.diem_khac, "kiem_tra": b.ma.startswith("K"),
            "ky_hieu": "" if b.ma.startswith("K") else ky_hieu_lich(b.sql_hien_thi(), p),
        } for b in kb["buoc"] if b.phien == p]
    return kq


def _gan_ky_hieu(nhat_ky: list) -> list:
    """Gắn ký hiệu lịch cho từng sự kiện và trả về lịch thực thi thật (theo đúng thứ tự xảy ra).

    * bị chặn       -> chỉ mới XIN khóa: xl₂(X), thao tác chính chưa diễn ra
    * chạy tiếp     -> khóa đã được cấp, giờ mới thực hiện thao tác chính: r₂(X) / w₂(X)
    * lỗi deadlock  -> xin khóa rồi bị InnoDB hủy: xl₂(X) a₂
    * COMMIT của giao tác đã bị hủy không còn ý nghĩa nên bỏ qua
    * các bước kiểm tra (K…) không thuộc giao tác nên không đưa vào lịch
    """
    da_huy = set()
    lich = []
    for e in nhat_ky:
        kh = ""
        if not e["ma"].startswith("K") and e["loai"] not in ("hoan", "bo_qua"):
            day_du = ky_hieu_lich(e["sql"], e["phien"])
            i = _CHI_SO[e["phien"]]
            x = _doi_tuong(" ".join(e["sql"].upper().split()))
            if not day_du:
                kh = ""
            elif e["loai"] == "bi_chan":
                kh = f"xl{i}({x})"
            elif (e.get("ket_qua") or {}).get("loi"):
                kh = f"xl{i}({x}) a{i}"
                da_huy.add(e["phien"])
            elif e["loai"] == "xong_sau_chan":
                kh = day_du.split(" ")[-1]
            elif day_du.startswith("c") and e["phien"] in da_huy:
                kh = ""
            else:
                kh = day_du
        e["ky_hieu"] = kh
        if kh:
            lich.append({"thu_tu": e["thu_tu"], "phien": e["phien"], "ky_hieu": kh, "loai": e["loai"]})
    return lich


def danh_sach_xung_dot() -> dict:
    return {
        ma: {
            "so": xd["so"], "ten": xd["ten"], "ten_en": xd["ten_en"], "van_de": xd["van_de"],
            "khac_biet": xd["khac_biet"], "bang": xd["bang"], "doi_tuong": xd["doi_tuong"],
            "kich_ban": {
                loai: {"tieu_de": kb["tieu_de"], "muc_co_lap": kb["muc"], "cach_lam": kb["cach_lam"],
                       "ma_nguon": _ma_nguon(xd, kb)}
                for loai, kb in xd["kich_ban"].items()
            },
        }
        for ma, xd in sorted(XUNG_DOT.items(), key=lambda kv: kv[1]["so"])
    }


def chay_xung_dot(ma: str, loai: str) -> dict:
    if ma not in XUNG_DOT:
        raise ValueError(f"Không có xung đột: {ma}")
    if loai not in LOAI_KICH_BAN:
        raise ValueError("Loại kịch bản phải là 'sai' hoặc 'dung'")
    xd = XUNG_DOT[ma]
    kb = xd["kich_ban"][loai]

    dat_du_lieu_lab()
    dien_bien = thuc_thi_hai_phien(kb["buoc"], kb["muc"], xd["bang"], chup_moi_buoc=True)
    xay_ra, giai_thich, noi_bat = xd["danh_gia"](dien_bien["ket_qua"])
    ky_vong = loai == "sai"
    nhat_ky = dien_bien["nhat_ky"]
    lich = _gan_ky_hieu(nhat_ky)
    return {
        "ma": ma,
        "loai": loai,
        "so": xd["so"],
        "ten": xd["ten"],
        "ten_en": xd["ten_en"],
        "van_de": xd["van_de"],
        "khac_biet": xd["khac_biet"],
        "tieu_de": kb["tieu_de"],
        "cach_lam": kb["cach_lam"],
        "muc_co_lap": kb["muc"],
        "bang": xd["bang"],
        "doi_tuong": xd["doi_tuong"],
        "lich": lich,
        "ma_nguon": _ma_nguon(xd, kb),
        "trang_thai_dau": dien_bien["trang_thai_dau"],
        "nhat_ky": nhat_ky,
        "ket_qua": dien_bien["ket_qua"],
        "xay_ra": xay_ra,
        "dung_ky_vong": xay_ra is ky_vong,
        "giai_thich": giai_thich,
        "noi_bat": noi_bat,
        "tong_ket": {
            "so_buoc": len(nhat_ky),
            "so_lan_bi_chan": sum(1 for e in nhat_ky if e["loai"] == "bi_chan"),
            "thoi_gian_cho_ms": round(sum(
                (e.get("ket_qua") or {}).get("thoi_gian_ms", 0)
                for e in nhat_ky if e["loai"] == "xong_sau_chan"), 1),
            "loi": sorted({f"{r['loi']['ma']} {r['loi']['ten']}" for r in dien_bien["ket_qua"].values()
                           if r.get("loi")}),
        },
        "ghe_ban_dau": GHE_BAN_DAU,
    }
