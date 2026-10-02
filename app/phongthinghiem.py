"""Phòng thí nghiệm mức cô lập.

Hai phiên A và B (hai kết nối MySQL riêng) thực hiện xen kẽ một kịch bản
có sẵn, đúng như khi mở hai cửa sổ dòng lệnh mysql cạnh nhau.

Điểm khó là một câu lệnh có thể bị InnoDB CHẶN vì chờ khóa. Khi đó phiên
đó treo, còn phiên kia vẫn phải chạy tiếp được. Vì vậy mỗi phiên có một
luồng thực thi riêng, và bộ điều phối làm như sau:

  * gửi câu lệnh, đợi tối đa CHO_CHAN_MS;
  * nếu chưa xong -> ghi nhận "bị chặn", chụp bảng khóa ngay lúc đó,
    rồi chuyển sang bước tiếp theo của kịch bản;
  * bước nào thuộc về phiên đang bị chặn thì phải HOÃN lại, vì một kết nối
    không thể gửi câu lệnh mới khi câu trước chưa trả về;
  * khi câu bị chặn chạy xong (do phiên kia commit/rollback, hoặc do InnoDB
    phá deadlock) thì ghi nhận kết quả và chạy nốt các bước đã hoãn.
"""
import datetime
import decimal
import queue
import re
import threading
import time
from dataclasses import dataclass
from typing import Callable

import pymysql

from . import csdl
from .kichban import MA_LOI_DEADLOCK, MA_LOI_HET_GIO_CHO_KHOA, doc_khoa_hien_tai

CHO_CHAN_MS = 700
HAN_CHO_KHOA_GIAY = 5
CAC_MUC = csdl.MUC_CO_LAP_HOP_LE

# Với UPDATE, MySQL trả về chuỗi thông tin "Rows matched: 1  Changed: 0  Warnings: 0".
# Số "dòng bị tác động" mặc định chỉ đếm dòng THỰC SỰ đổi giá trị, nên ghi một giá trị
# trùng giá trị cũ sẽ báo 0 dòng – dù câu lệnh vẫn khớp và ghi lên dòng đó.
_MAU_THONG_TIN = re.compile(r"Rows matched: (\d+)\s+Changed: (\d+)")


@dataclass
class Buoc:
    ma: str
    phien: str
    sql: str | Callable[[dict], str | None]
    mo_ta: str
    sql_mau: str = ""  # hiển thị trước khi chạy, cho các câu phụ thuộc kết quả trước
    diem_khac: bool = False  # dòng then chốt làm nên khác biệt giữa kịch bản sai và đúng

    def sql_hien_thi(self) -> str:
        return self.sql if isinstance(self.sql, str) else self.sql_mau


# ------------------------------------------------------------ thực thi 1 phiên
class CongViec:
    def __init__(self, sql: str):
        self.sql = sql
        self.xong = threading.Event()
        self.dong: list = []
        self.so_dong = 0
        self.loi: pymysql.err.MySQLError | None = None
        self.khop: int | None = None
        self.doi: int | None = None
        self.t_gui = time.perf_counter()
        self.t_xong: float | None = None


class PhienLab:
    """Một kết nối MySQL + một luồng riêng để câu lệnh bị chặn không làm treo cả kịch bản."""

    def __init__(self, ten: str, muc_co_lap: str):
        self.ten = ten
        self.conn = csdl.ket_noi(tu_dong_commit=False, muc_co_lap=muc_co_lap,
                                 han_cho_khoa=HAN_CHO_KHOA_GIAY)
        self.ma_conn = csdl.ma_ket_noi(self.conn)
        self._hang_doi: queue.Queue = queue.Queue()
        self._luong = threading.Thread(target=self._vong_lap, daemon=True)
        self._luong.start()

    def _vong_lap(self):
        cur = self.conn.cursor()
        while True:
            cv = self._hang_doi.get()
            if cv is None:
                break
            try:
                cv.so_dong = cur.execute(cv.sql)
                if cur.description:
                    cv.dong = list(cur.fetchall())
                thong_tin = getattr(getattr(cur, "_result", None), "message", None) or b""
                if isinstance(thong_tin, bytes):
                    thong_tin = thong_tin.decode("utf-8", "replace")
                m = _MAU_THONG_TIN.search(thong_tin)
                if m:
                    cv.khop, cv.doi = int(m[1]), int(m[2])
            except pymysql.err.MySQLError as e:
                cv.loi = e
            cv.t_xong = time.perf_counter()
            cv.xong.set()
        cur.close()

    def gui(self, sql: str) -> CongViec:
        cv = CongViec(sql)
        self._hang_doi.put(cv)
        return cv

    def dong(self):
        self._hang_doi.put(None)
        self._luong.join(timeout=HAN_CHO_KHOA_GIAY + 2)
        try:
            self.conn.rollback()
        except Exception:  # noqa: BLE001
            pass
        try:
            self.conn.close()
        except Exception:  # noqa: BLE001
            pass


# ------------------------------------------------------------------ tiện ích
def _gia_tri_json(v):
    if isinstance(v, decimal.Decimal):
        return int(v) if v == v.to_integral_value() else float(v)
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.isoformat()
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    return v


def _lam_sach(dong: list, toi_da: int = 20) -> list:
    return [{k: _gia_tri_json(v) for k, v in d.items()} for d in dong[:toi_da]]


def _gt(kq: dict, ma: str, cot: str):
    """Giá trị một cột ở dòng đầu tiên của kết quả bước `ma` (None nếu lỗi/không có)."""
    r = kq.get(ma)
    if not r or r.get("loi") or r.get("bo_qua") or not r.get("dong"):
        return None
    return r["dong"][0].get(cot)


def _so_dong(kq: dict, ma: str):
    r = kq.get(ma)
    if not r or r.get("loi") or r.get("bo_qua"):
        return None
    return len(r["dong"])


def _bi_chan(kq: dict, ma: str) -> bool:
    return bool(kq.get(ma, {}).get("bi_chan"))


def _loi(kq: dict, ma: str) -> str | None:
    loi = (kq.get(ma) or {}).get("loi")
    return loi["ten"] if loi else None


def _chup_khoa(conn, ten_theo_conn: dict):
    ten = lambda c: ten_theo_conn.get(c, f"kết nối {c}")  # noqa: E731
    with conn.cursor() as cur:
        cac_khoa, cac_cho = doc_khoa_hien_tai(cur)
    khoa = [{
        "phien": ten(d["ma_conn"]), "bang": d["bang"], "chi_muc": d["chi_muc"],
        "loai_khoa": d["loai_khoa"], "che_do_khoa": d["che_do_khoa"],
        "trang_thai": d["trang_thai"], "du_lieu": d["du_lieu"],
    } for d in cac_khoa]
    cho = [{"phien_cho": ten(d["conn_cho"]), "phien_giu": ten(d["conn_giu"])}
           for d in cac_cho if d["trang_thai_giu"] == "GRANTED"]
    khoa.sort(key=lambda k: (k["phien"], k["bang"], k["chi_muc"] or "", str(k["du_lieu"])))
    return khoa, cho


# Các bảng có thể hiển thị trong hoạt hình: (câu truy vấn, khóa chính)
BANG_HIEN_THI = {
    "chuyen_bay": ("SELECT ma_chuyen, so_hieu, so_ghe_trong FROM chuyen_bay ORDER BY ma_chuyen", "ma_chuyen"),
    "ve": ("SELECT ma_ve, ma_chuyen, hanh_khach FROM ve ORDER BY ma_ve", "ma_ve"),
    "ghe": ("SELECT ma_ghe, so_ghe, trang_thai, nguoi_giu FROM ghe ORDER BY ma_ghe", "ma_ghe"),
}


class MayChupDuLieu:
    """Chụp nội dung bảng theo hai góc nhìn sau mỗi bước của kịch bản.

    * da_commit: đọc ở READ COMMITTED – thứ mà mọi giao tác khác được phép thấy;
    * moi_nhat : đọc ở READ UNCOMMITTED – bản mới nhất trong InnoDB, kể cả thay đổi
                 chưa commit đang nằm trong giao tác của A hoặc B.
    Cả hai đều là đọc không khóa nên không bao giờ bị chặn và không làm thay đổi kịch bản.
    """

    def __init__(self, cac_bang):
        self.cac_bang = [b for b in cac_bang if b in BANG_HIEN_THI]
        self.conn_commit = csdl.ket_noi(tu_dong_commit=True, muc_co_lap="READ COMMITTED")
        self.conn_moi = csdl.ket_noi(tu_dong_commit=True, muc_co_lap="READ UNCOMMITTED")

    def chup(self) -> dict:
        kq = {}
        for ten in self.cac_bang:
            sql, khoa_chinh = BANG_HIEN_THI[ten]
            with self.conn_commit.cursor() as c:
                c.execute(sql)
                da_commit = _lam_sach(c.fetchall(), 50)
            with self.conn_moi.cursor() as c:
                c.execute(sql)
                moi_nhat = _lam_sach(c.fetchall(), 50)
            kq[ten] = {"khoa_chinh": khoa_chinh, "da_commit": da_commit, "moi_nhat": moi_nhat}
        return kq

    def dong(self):
        for c in (self.conn_commit, self.conn_moi):
            try:
                c.close()
            except Exception:  # noqa: BLE001
                pass


# ------------------------------------------------------------ dữ liệu ban đầu
DU_LIEU_BAN_DAU = {
    "chuyen_bay": [(1, "VN-808", 10, 7), (2, "VN-216", 10, 8)],
    "ve": [(1, 1, "An"), (2, 1, "Bình"), (3, 1, "Chi"), (4, 2, "Dũng"), (5, 2, "Giang")],
    "ghe": [(1, 1, "12A"), (2, 1, "12B")],
}


def dat_du_lieu_lab():
    conn = csdl.ket_noi(tu_dong_commit=True)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM ve")
            cur.execute("DELETE FROM ghe")
            cur.execute("DELETE FROM chuyen_bay")
            for ma, ten, tong, con in DU_LIEU_BAN_DAU["chuyen_bay"]:
                cur.execute(
                    "INSERT INTO chuyen_bay (ma_chuyen, so_hieu, tong_ghe, so_ghe_trong, version)"
                    " VALUES (%s, %s, %s, %s, 0)", (ma, ten, tong, con))
            for ma_ve, ma_chuyen, nguoi in DU_LIEU_BAN_DAU["ve"]:
                cur.execute("INSERT INTO ve (ma_ve, ma_chuyen, hanh_khach) VALUES (%s, %s, %s)",
                            (ma_ve, ma_chuyen, nguoi))
            for ma_ghe, ma_chuyen, so_ghe in DU_LIEU_BAN_DAU["ghe"]:
                cur.execute("INSERT INTO ghe (ma_ghe, ma_chuyen, so_ghe) VALUES (%s, %s, %s)",
                            (ma_ghe, ma_chuyen, so_ghe))
            cur.execute("ALTER TABLE ve AUTO_INCREMENT = 6")
    finally:
        conn.close()


# --------------------------------------------------------------- đánh giá
SQL_DOC_GHE = "SELECT so_ghe_trong FROM chuyen_bay WHERE ma_chuyen = 1"
GHE_BAN_DAU = 7
VE_BAN_DAU = 3


def _dg_doc_rac(kq):
    v = _gt(kq, "A2", "so_ghe_trong")
    if v is None:
        return None, f"Bước A2 không đọc được dữ liệu ({_loi(kq, 'A2')}).", ["A2"]
    if v == 0:
        return True, (
            "A đọc được 0 – con số B vừa ghi nhưng CHƯA commit. Sau đó B rollback, "
            f"nên giá trị thật vẫn là {GHE_BAN_DAU}. A đã dựa vào một dữ liệu chưa từng "
            "tồn tại chính thức: đó là đọc dữ liệu rác."), ["A2", "B3"]
    if _bi_chan(kq, "A2"):
        return False, (
            "Câu đọc của A bị chặn cho tới khi B rollback: ở SERIALIZABLE, SELECT thường "
            "cũng phải xin khóa S, mà B đang giữ khóa X trên dòng đó. "
            f"Khi được chạy, A đọc được {v} – giá trị đúng."), ["A2", "B3"]
    return False, (
        f"A đọc được {v} – bản đã commit gần nhất. InnoDB dựng lại bản cũ từ undo log "
        "(MVCC) nên A không thấy thay đổi dở dang của B, và cũng không phải chờ."), ["A2"]


def _dg_doc_khong_lap_lai(kq):
    v1, v2 = _gt(kq, "A2", "so_ghe_trong"), _gt(kq, "A3", "so_ghe_trong")
    if v1 is None or v2 is None:
        return None, "Không đủ dữ liệu để kết luận.", ["A2", "A3"]
    if v1 != v2:
        return True, (
            f"Trong CÙNG một giao tác, A đọc cùng một dòng hai lần nhưng ra {v1} rồi {v2}, "
            "vì giữa hai lần đọc B đã sửa và commit. Mỗi câu SELECT ở mức này "
            "lấy một snapshot mới."), ["A2", "A3"]
    if _bi_chan(kq, "B2"):
        return False, (
            f"A đọc hai lần đều ra {v1}. Lệnh UPDATE của B bị chặn cho tới khi A commit, "
            "vì A đang giữ khóa S trên dòng này (SERIALIZABLE biến SELECT thành đọc có khóa)."
        ), ["A2", "A3", "B2"]
    return False, (
        f"A đọc hai lần đều ra {v1}, dù B đã commit giá trị mới. Ở REPEATABLE READ, "
        "snapshot được tạo ở lần đọc đầu tiên và dùng lại suốt giao tác (MVCC), "
        "B không hề bị chặn."), ["A2", "A3"]


def _dg_bong_ma(kq):
    n1, n2 = _gt(kq, "A2", "so_ve"), _gt(kq, "A3", "so_ve")
    if n1 is None or n2 is None:
        return None, "Không đủ dữ liệu để kết luận.", ["A2", "A3"]
    if n1 != n2:
        return True, (
            f"A đếm hai lần trong cùng giao tác: {n1} vé rồi {n2} vé. Dòng vé B vừa chèn "
            "hiện ra như một 'bóng ma' ở lần đếm thứ hai."), ["A2", "A3"]
    if _bi_chan(kq, "B2"):
        return False, (
            f"A đếm hai lần đều ra {n1}. Lệnh INSERT của B bị chặn: SERIALIZABLE biến câu "
            "đếm của A thành đọc có khóa, InnoDB đặt next-key lock lên cả khoảng chỉ mục "
            "ma_chuyen = 1, nên không ai chèn thêm vào khoảng đó được."), ["A2", "A3", "B2"]
    return False, (
        f"A đếm hai lần đều ra {n1} dù B đã chèn và commit. Chuẩn SQL cho phép bóng ma ở "
        "REPEATABLE READ, nhưng InnoDB đọc trên snapshot (MVCC) nên dòng mới không hiện ra."
    ), ["A2", "A3"]


def _dg_bong_ma_doc_khoa(kq):
    n1, n2 = _so_dong(kq, "A2"), _so_dong(kq, "A3")
    if n1 is None or n2 is None:
        return None, "Không đủ dữ liệu để kết luận.", ["A2", "A3"]
    if n1 != n2:
        return True, (
            f"Lần khóa đầu A giữ {n1} dòng, lần sau ra {n2} dòng. Ở mức này InnoDB chỉ khóa "
            "các dòng đang tồn tại (record lock), KHÔNG khóa khoảng trống giữa chúng, nên B "
            "chèn được dòng mới vào ngay trong vùng A tưởng đã khóa hết."), ["A2", "A3", "B2"]
    if _bi_chan(kq, "B2"):
        return False, (
            f"A khóa hai lần đều ra {n1} dòng. Lệnh INSERT của B bị chặn bởi GAP LOCK: "
            "InnoDB khóa cả khoảng trống sau dòng cuối cùng thỏa ma_chuyen = 1 (next-key lock), "
            "nên B phải chờ tới khi A commit. Xem bảng khóa: B chờ khóa "
            "INSERT_INTENTION, xung đột với khóa GAP của A."), ["A2", "A3", "B2"]
    return False, f"A khóa hai lần đều ra {n1} dòng.", ["A2", "A3"]


def _dg_mat_cap_nhat(kq):
    cuoi = _gt(kq, "K1", "so_ghe_trong")
    if cuoi is None:
        return None, "Không đọc được kết quả cuối cùng.", ["K1"]
    thanh_cong = [m for m in ("A3", "B3") if kq.get(m) and not kq[m].get("loi")
                  and not kq[m].get("bo_qua")]
    ky_vong = GHE_BAN_DAU - len(thanh_cong)
    if len(thanh_cong) == 2 and cuoi != ky_vong:
        b3 = kq.get("B3") or {}
        im_lang = ""
        if b3.get("so_dong_khop") == 1 and b3.get("so_dong_doi") == 0:
            im_lang = (f" Tệ hơn nữa, câu UPDATE của B chỉ nhận về 'Rows matched: 1, Changed: 0' vì nó ghi "
                       f"đúng giá trị {cuoi} mà A đã ghi – ứng dụng không hề nhận được lỗi hay cảnh báo nào.")
        return True, (
            f"Cả A và B đều đọc thấy {GHE_BAN_DAU} ghế, cùng bán 1 vé và cùng commit thành công – "
            f"tổng cộng 2 vé. Nhưng số ghế cuối cùng là {cuoi}, lẽ ra phải là {ky_vong}. "
            "B đã ghi đè lên kết quả của A: đây là mất cập nhật." + im_lang
            + " REPEATABLE READ của MySQL KHÔNG ngăn được hiện tượng này, vì UPDATE luôn ghi lên "
            "bản mới nhất mà không kiểm tra dòng đó đã bị sửa sau snapshot hay chưa."), ["A3", "B3", "K1"]
    if cuoi == ky_vong and len(thanh_cong) < 2:
        nan_nhan = [m for m in ("A3", "B3") if _loi(kq, m) == "deadlock"]
        ai = "A" if nan_nhan == ["A3"] else "B"
        return False, (
            "Cả A và B đều giữ khóa S sau khi đọc, rồi cùng xin nâng lên khóa X để ghi: "
            f"hai bên chờ nhau thành vòng tròn. InnoDB phát hiện deadlock và hủy giao tác "
            f"của {ai}. Chỉ một cập nhật được ghi nhận, số ghế còn {cuoi} – đúng. "
            f"Giao tác của {ai} cần được ứng dụng thử lại."), ["A3", "B3", "K1"]
    v_b = _gt(kq, "B2", "so_ghe_trong")
    if cuoi == ky_vong and _bi_chan(kq, "B2") and v_b is not None:
        return False, (
            f"A khóa dòng ngay lúc đọc bằng FOR UPDATE. Câu đọc của B cũng xin khóa X nên bị chặn "
            f"cho tới khi A commit; khi được chạy tiếp, B đọc được giá trị MỚI {v_b} (không phải "
            f"{GHE_BAN_DAU}) và ghi {v_b - 1}. Hai vé bán ra, số ghế giảm đúng 2: "
            f"{GHE_BAN_DAU} → {cuoi}."), ["A2", "B2", "K1"]
    return False, f"Số ghế cuối cùng là {cuoi}, khớp với {len(thanh_cong)} lần bán thành công.", ["K1"]


def _dg_doc_nhat_quan(kq):
    v_thuong, v_khoa = _gt(kq, "A3", "so_ghe_trong"), _gt(kq, "A4", "so_ghe_trong")
    if v_thuong is None or v_khoa is None:
        loi = _loi(kq, "A4") or _loi(kq, "A3")
        if loi == "deadlock":
            return False, (
                "A đang giữ khóa S và xin nâng lên khóa X, trong khi B đang xếp hàng chờ khóa X "
                "trên cùng dòng. Hai bên chờ nhau nên InnoDB phá vòng bằng cách hủy A."
            ), ["A4", "B2"]
        return None, "Không đủ dữ liệu để kết luận.", ["A3", "A4"]
    if v_thuong != v_khoa:
        return True, (
            f"Cùng một giao tác, cùng một dòng: SELECT thường ra {v_thuong} nhưng "
            f"SELECT … FOR UPDATE ra {v_khoa}. Đọc thường là đọc nhất quán trên snapshot cũ "
            "(consistent read), còn đọc có khóa luôn là đọc hiện hành (current read) trên bản "
            "mới nhất. Đây là lý do khóa bi quan phải dùng FOR UPDATE ngay từ lần đọc đầu."
        ), ["A3", "A4"]
    if _bi_chan(kq, "B2"):
        return False, (
            f"Hai cách đọc đều ra {v_thuong}: B bị chặn không sửa được dòng này cho tới khi "
            "A kết thúc."), ["A3", "A4", "B2"]
    return False, (
        f"Hai cách đọc đều ra {v_thuong}: ở mức này mỗi câu SELECT đã lấy snapshot mới "
        "nên đọc thường cũng thấy bản mới nhất."), ["A3", "A4"]


def _ghi_tru_mot(ma_doc: str):
    def tao_sql(kq):
        v = _gt(kq, ma_doc, "so_ghe_trong")
        if v is None:
            return None
        return f"UPDATE chuyen_bay SET so_ghe_trong = {v - 1} WHERE ma_chuyen = 1"
    return tao_sql


# --------------------------------------------------------- danh sách thí nghiệm
THI_NGHIEM = {
    "doc_rac": {
        "ten": "Đọc dữ liệu rác (Dirty read)",
        "tom_tat": "A đọc thay đổi B chưa commit, rồi B hủy bỏ thay đổi đó.",
        "la_loi": True,
        "ly_thuyet": {"READ UNCOMMITTED": True, "READ COMMITTED": False,
                      "REPEATABLE READ": False, "SERIALIZABLE": False},
        "buoc": [
            Buoc("A1", "A", "START TRANSACTION", "A mở giao tác"),
            Buoc("B1", "B", "START TRANSACTION", "B mở giao tác"),
            Buoc("B2", "B", "UPDATE chuyen_bay SET so_ghe_trong = 0 WHERE ma_chuyen = 1",
                 "B sửa số ghế còn thành 0 nhưng chưa commit"),
            Buoc("A2", "A", SQL_DOC_GHE, "A đọc số ghế còn"),
            Buoc("B3", "B", "ROLLBACK", "B hủy bỏ thay đổi"),
            Buoc("A3", "A", SQL_DOC_GHE, "A đọc lại sau khi B hủy"),
            Buoc("A4", "A", "COMMIT", "A kết thúc giao tác"),
        ],
        "danh_gia": _dg_doc_rac,
    },
    "doc_khong_lap_lai": {
        "ten": "Đọc không lặp lại (Non-repeatable read)",
        "tom_tat": "A đọc một dòng hai lần, giữa hai lần B sửa và commit dòng đó.",
        "la_loi": True,
        "ly_thuyet": {"READ UNCOMMITTED": True, "READ COMMITTED": True,
                      "REPEATABLE READ": False, "SERIALIZABLE": False},
        "buoc": [
            Buoc("A1", "A", "START TRANSACTION", "A mở giao tác"),
            Buoc("A2", "A", SQL_DOC_GHE, "A đọc số ghế còn lần 1"),
            Buoc("B1", "B", "START TRANSACTION", "B mở giao tác"),
            Buoc("B2", "B", "UPDATE chuyen_bay SET so_ghe_trong = 6 WHERE ma_chuyen = 1",
                 "B bán 1 vé: số ghế còn = 6"),
            Buoc("B3", "B", "COMMIT", "B commit"),
            Buoc("A3", "A", SQL_DOC_GHE, "A đọc số ghế còn lần 2"),
            Buoc("A4", "A", "COMMIT", "A kết thúc giao tác"),
        ],
        "danh_gia": _dg_doc_khong_lap_lai,
    },
    "bong_ma": {
        "ten": "Bóng ma – đọc thường (Phantom read)",
        "tom_tat": "A đếm số vé hai lần, giữa hai lần B chèn thêm một vé mới và commit.",
        "la_loi": True,
        "ly_thuyet": {"READ UNCOMMITTED": True, "READ COMMITTED": True,
                      "REPEATABLE READ": True, "SERIALIZABLE": False},
        "buoc": [
            Buoc("A1", "A", "START TRANSACTION", "A mở giao tác"),
            Buoc("A2", "A", "SELECT COUNT(*) AS so_ve FROM ve WHERE ma_chuyen = 1",
                 "A đếm vé của chuyến VN-808 lần 1"),
            Buoc("B1", "B", "START TRANSACTION", "B mở giao tác"),
            Buoc("B2", "B", "INSERT INTO ve (ma_chuyen, hanh_khach) VALUES (1, 'Hoa')",
                 "B bán thêm một vé cho chuyến VN-808"),
            Buoc("B3", "B", "COMMIT", "B commit"),
            Buoc("A3", "A", "SELECT COUNT(*) AS so_ve FROM ve WHERE ma_chuyen = 1",
                 "A đếm vé lần 2"),
            Buoc("A4", "A", "COMMIT", "A kết thúc giao tác"),
        ],
        "danh_gia": _dg_bong_ma,
    },
    "bong_ma_doc_khoa": {
        "ten": "Bóng ma – đọc có khóa (Gap lock)",
        "tom_tat": "A khóa mọi vé của chuyến VN-808 bằng FOR UPDATE, B cố chèn thêm vé vào chuyến đó.",
        "la_loi": True,
        "ly_thuyet": {"READ UNCOMMITTED": True, "READ COMMITTED": True,
                      "REPEATABLE READ": True, "SERIALIZABLE": False},
        "buoc": [
            Buoc("A1", "A", "START TRANSACTION", "A mở giao tác"),
            Buoc("A2", "A", "SELECT ma_ve, hanh_khach FROM ve WHERE ma_chuyen = 1 FOR UPDATE",
                 "A khóa toàn bộ vé của chuyến VN-808"),
            Buoc("B1", "B", "START TRANSACTION", "B mở giao tác"),
            Buoc("B2", "B", "INSERT INTO ve (ma_chuyen, hanh_khach) VALUES (1, 'Hoa')",
                 "B chèn vé mới vào chuyến VN-808"),
            Buoc("B3", "B", "COMMIT", "B commit"),
            Buoc("A3", "A", "SELECT ma_ve, hanh_khach FROM ve WHERE ma_chuyen = 1 FOR UPDATE",
                 "A khóa lại vé của chuyến VN-808"),
            Buoc("A4", "A", "COMMIT", "A kết thúc giao tác"),
        ],
        "danh_gia": _dg_bong_ma_doc_khoa,
    },
    "mat_cap_nhat": {
        "ten": "Mất cập nhật (Lost update)",
        "tom_tat": "A và B cùng đọc số ghế, cùng tự tính trừ 1 rồi ghi đè.",
        "la_loi": True,
        # Chuẩn SQL-92 không định nghĩa hiện tượng này; theo Berenson và cộng sự (1995),
        # REPEATABLE READ cài đặt bằng khóa sẽ ngăn được nó.
        "ly_thuyet": {"READ UNCOMMITTED": True, "READ COMMITTED": True,
                      "REPEATABLE READ": False, "SERIALIZABLE": False},
        "buoc": [
            Buoc("A1", "A", "START TRANSACTION", "A mở giao tác"),
            Buoc("B1", "B", "START TRANSACTION", "B mở giao tác"),
            Buoc("A2", "A", SQL_DOC_GHE, "A đọc số ghế còn"),
            Buoc("B2", "B", SQL_DOC_GHE, "B đọc số ghế còn"),
            Buoc("A3", "A", _ghi_tru_mot("A2"), "A ghi: số ghế = giá trị A đọc được − 1",
                 "UPDATE chuyen_bay SET so_ghe_trong = <A đọc được − 1> WHERE ma_chuyen = 1"),
            Buoc("A4", "A", "COMMIT", "A commit"),
            Buoc("B3", "B", _ghi_tru_mot("B2"), "B ghi: số ghế = giá trị B đọc được − 1",
                 "UPDATE chuyen_bay SET so_ghe_trong = <B đọc được − 1> WHERE ma_chuyen = 1"),
            Buoc("B4", "B", "COMMIT", "B commit"),
            Buoc("K1", "A", SQL_DOC_GHE, "Kiểm tra số ghế cuối cùng"),
        ],
        "danh_gia": _dg_mat_cap_nhat,
    },
    "doc_nhat_quan": {
        "ten": "Đọc nhất quán và đọc hiện hành (MVCC)",
        "tom_tat": "Trong cùng giao tác, so sánh SELECT thường với SELECT … FOR UPDATE.",
        "la_loi": False,
        "ly_thuyet": None,
        "buoc": [
            Buoc("A1", "A", "START TRANSACTION", "A mở giao tác"),
            Buoc("A2", "A", SQL_DOC_GHE, "A đọc lần đầu (tạo snapshot)"),
            Buoc("B1", "B", "START TRANSACTION", "B mở giao tác"),
            Buoc("B2", "B", "UPDATE chuyen_bay SET so_ghe_trong = 2 WHERE ma_chuyen = 1",
                 "B sửa số ghế còn thành 2"),
            Buoc("B3", "B", "COMMIT", "B commit"),
            Buoc("A3", "A", SQL_DOC_GHE, "A đọc thường (consistent read)"),
            Buoc("A4", "A", SQL_DOC_GHE + " FOR UPDATE", "A đọc có khóa (current read)"),
            Buoc("A5", "A", "COMMIT", "A kết thúc giao tác"),
        ],
        "danh_gia": _dg_doc_nhat_quan,
    },
}

GHI_CHU_MYSQL = {
    ("bong_ma", "REPEATABLE READ"):
        "Khác chuẩn SQL: InnoDB dùng MVCC nên đọc thường ở REPEATABLE READ không thấy bóng ma.",
    ("bong_ma_doc_khoa", "REPEATABLE READ"):
        "Khác chuẩn SQL: InnoDB dùng next-key lock (record + gap) nên chặn được bóng ma cả khi đọc có khóa.",
    ("mat_cap_nhat", "REPEATABLE READ"):
        "Khác lý thuyết: REPEATABLE READ của MySQL dựa trên snapshot, UPDATE không kiểm tra "
        "xung đột ghi nên vẫn mất cập nhật. Phải dùng FOR UPDATE, khóa lạc quan hoặc UPDATE nguyên tử.",
}


def danh_sach_thi_nghiem() -> dict:
    return {
        ma: {
            "ten": tn["ten"], "tom_tat": tn["tom_tat"], "la_loi": tn["la_loi"],
            "ly_thuyet": tn["ly_thuyet"],
            "buoc": [{"ma": b.ma, "phien": b.phien, "mo_ta": b.mo_ta, "sql": b.sql_hien_thi()}
                     for b in tn["buoc"]],
        }
        for ma, tn in THI_NGHIEM.items()
    }


# ----------------------------------------------------------------- điều phối
def thuc_thi_hai_phien(cac_buoc: list[Buoc], muc: str, cac_bang=(),
                       chup_moi_buoc: bool = False) -> dict:
    """Chạy kịch bản hai phiên A/B trên MySQL thật, trả về nhật ký diễn biến.

    chup_moi_buoc=True: sau MỖI sự kiện chụp lại bảng khóa và nội dung các bảng trong
    `cac_bang` (đã commit / mới nhất) – dữ liệu để phát lại dạng hoạt hình.
    Người gọi chịu trách nhiệm nạp dữ liệu ban đầu trước khi gọi.
    """
    theo_doi = csdl.ket_noi(tu_dong_commit=True)
    may_chup = None
    phien: dict[str, PhienLab] = {}
    try:
        if chup_moi_buoc:
            may_chup = MayChupDuLieu(cac_bang)
        phien = {"A": PhienLab("A", muc), "B": PhienLab("B", muc)}
    except Exception:
        for p in phien.values():
            p.dong()
        if may_chup:
            may_chup.dong()
        theo_doi.close()
        raise
    ten_theo_conn = {p.ma_conn: p.ten for p in phien.values()}

    goc = time.perf_counter()
    kq: dict = {}
    nhat_ky: list = []
    dang_cho: dict = {"A": None, "B": None}   # phiên -> (bước, sql, công việc) đang bị chặn
    hoan: dict = {"A": [], "B": []}           # phiên -> các bước phải hoãn
    trang_thai_dau = may_chup.chup() if may_chup else None

    def moc():
        return round((time.perf_counter() - goc) * 1000, 1)

    def ghi(buoc: Buoc, loai: str, sql: str | None = None, **them):
        if may_chup:
            if "khoa" not in them:
                them["khoa"], them["cho"] = _chup_khoa(theo_doi, ten_theo_conn)
            them["trang_thai"] = may_chup.chup()
        nhat_ky.append({"thu_tu": len(nhat_ky) + 1, "ma": buoc.ma, "phien": buoc.phien,
                        "mo_ta": buoc.mo_ta, "loai": loai,
                        "sql": sql if sql is not None else buoc.sql_hien_thi(),
                        "moc": moc(), **them})

    def ket_thuc(buoc: Buoc, sql: str, cv: CongViec, sau_chan: bool, chay_bu: bool = False):
        loi = None
        if cv.loi is not None:
            ma_loi = cv.loi.args[0] if cv.loi.args else 0
            loi = {"ma": ma_loi,
                   "ten": {MA_LOI_DEADLOCK: "deadlock",
                           MA_LOI_HET_GIO_CHO_KHOA: "het_gio"}.get(ma_loi, "loi"),
                   "thong_diep": cv.loi.args[1] if len(cv.loi.args) > 1 else str(cv.loi)}
        r = {"dong": _lam_sach(cv.dong), "so_dong": cv.so_dong, "loi": loi,
             "so_dong_khop": cv.khop, "so_dong_doi": cv.doi,
             "bi_chan": sau_chan,
             "thoi_gian_ms": round(((cv.t_xong or time.perf_counter()) - cv.t_gui) * 1000, 1)}
        kq[buoc.ma] = r
        ghi(buoc, "xong_sau_chan" if sau_chan else "xong", sql, ket_qua=r, chay_bu=chay_bu)

    def cho_phien_kia(p: str, giay: float):
        """Sau khi một phiên vừa chạy xong một lệnh (có thể đã nhả khóa, hoặc bị
        InnoDB hủy vì deadlock), cho câu lệnh đang treo ở phiên kia chút thời gian để hoàn tất."""
        for q in "AB":
            if q != p and dang_cho[q]:
                dang_cho[q][2].xong.wait(giay)

    def thuc_thi(buoc: Buoc, chay_bu: bool = False):
        sql = buoc.sql(kq) if callable(buoc.sql) else buoc.sql
        if sql is None:
            kq[buoc.ma] = {"bo_qua": True, "dong": [], "loi": None, "bi_chan": False}
            ghi(buoc, "bo_qua", buoc.sql_hien_thi(), chay_bu=chay_bu,
                ly_do="bước trước đó không có kết quả nên không tính được câu lệnh")
            return
        cv = phien[buoc.phien].gui(sql)
        if cv.xong.wait(CHO_CHAN_MS / 1000):
            ket_thuc(buoc, sql, cv, sau_chan=False, chay_bu=chay_bu)
            cho_phien_kia(buoc.phien, 0.3)
        else:
            khoa, cho = _chup_khoa(theo_doi, ten_theo_conn)
            ghi(buoc, "bi_chan", sql, khoa=khoa, cho=cho, chay_bu=chay_bu)
            dang_cho[buoc.phien] = (buoc, sql, cv)

    def don_dep():
        tien_trien = True
        while tien_trien:
            tien_trien = False
            for p in "AB":
                if dang_cho[p] and dang_cho[p][2].xong.is_set():
                    b, s, cv = dang_cho[p]
                    dang_cho[p] = None
                    ket_thuc(b, s, cv, sau_chan=True)
                    cho_phien_kia(p, 0.3)
                    tien_trien = True
            for p in "AB":
                if dang_cho[p] is None and hoan[p]:
                    thuc_thi(hoan[p].pop(0), chay_bu=True)
                    tien_trien = True

    try:
        for buoc in cac_buoc:
            don_dep()
            if dang_cho[buoc.phien] or hoan[buoc.phien]:
                hoan[buoc.phien].append(buoc)
                ghi(buoc, "hoan", ly_do=f"phiên {buoc.phien} đang bị chặn, "
                                        "chưa thể gửi câu lệnh mới")
                continue
            thuc_thi(buoc)
        han = time.perf_counter() + HAN_CHO_KHOA_GIAY + 2
        while (any(dang_cho.values()) or any(hoan.values())) and time.perf_counter() < han:
            for p in "AB":
                if dang_cho[p]:
                    dang_cho[p][2].xong.wait(0.1)
            don_dep()
    finally:
        for p in phien.values():
            p.dong()
        if may_chup:
            may_chup.dong()
        theo_doi.close()

    return {"nhat_ky": nhat_ky, "ket_qua": kq, "trang_thai_dau": trang_thai_dau}


def chay_thi_nghiem(ma: str, muc_co_lap: str) -> dict:
    if ma not in THI_NGHIEM:
        raise ValueError(f"Không có thí nghiệm: {ma}")
    muc = csdl.chuan_hoa_muc_co_lap(muc_co_lap)
    if muc is None:
        raise ValueError("Phải chọn một mức cô lập")
    tn = THI_NGHIEM[ma]

    dat_du_lieu_lab()
    dien_bien = thuc_thi_hai_phien(tn["buoc"], muc)
    nhat_ky, kq = dien_bien["nhat_ky"], dien_bien["ket_qua"]

    xay_ra, giai_thich, noi_bat = tn["danh_gia"](kq)
    ly_thuyet = tn["ly_thuyet"][muc] if tn["ly_thuyet"] else None
    return {
        "ma": ma,
        "ten": tn["ten"],
        "tom_tat": tn["tom_tat"],
        "la_loi": tn["la_loi"],
        "muc_co_lap": muc,
        "xay_ra": xay_ra,
        "ly_thuyet": ly_thuyet,
        "khac_ly_thuyet": ly_thuyet is not None and xay_ra is not None and ly_thuyet != xay_ra,
        "ghi_chu_mysql": GHI_CHU_MYSQL.get((ma, muc), ""),
        "giai_thich": giai_thich,
        "noi_bat": noi_bat,
        "nhat_ky": nhat_ky,
        "ket_qua": kq,
        "du_lieu_ban_dau": DU_LIEU_BAN_DAU,
        "co_chan": any(e["loai"] == "bi_chan" for e in nhat_ky),
        "co_deadlock": any((r.get("loi") or {}).get("ten") == "deadlock" for r in kq.values()),
    }


def chay_ma_tran() -> dict:
    """Chạy mọi thí nghiệm ở cả 4 mức cô lập – kết quả là bảng so sánh với lý thuyết."""
    bang = {}
    for ma in THI_NGHIEM:
        bang[ma] = {}
        for muc in CAC_MUC:
            r = chay_thi_nghiem(ma, muc)
            bang[ma][muc] = {k: r[k] for k in (
                "xay_ra", "ly_thuyet", "khac_ly_thuyet", "ghi_chu_mysql",
                "giai_thich", "co_chan", "co_deadlock")}
    return {
        "cac_muc": list(CAC_MUC),
        "thi_nghiem": {ma: {"ten": tn["ten"], "la_loi": tn["la_loi"]}
                       for ma, tn in THI_NGHIEM.items()},
        "bang": bang,
    }
