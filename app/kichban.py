"""Các kịch bản truy xuất đồng thời và bộ ghi lại diễn biến để vẽ biểu đồ.

Ý tưởng: mỗi 'khách hàng' là một luồng (thread) có kết nối MySQL riêng.
Mọi câu lệnh SQL đều được bấm giờ bắt đầu / kết thúc, nhờ đó ta vẽ lại
được đúng những gì xảy ra bên trong CSDL: lúc nào đọc, lúc nào bị chặn
vì chờ khóa, lúc nào commit, lúc nào bị cuộn ngược vì deadlock.
"""
import random
import statistics
import threading
import time
from dataclasses import dataclass, field

import pymysql

from . import csdl

MA_LOI_DEADLOCK = 1213
MA_LOI_HET_GIO_CHO_KHOA = 1205

# Một câu lệnh chạy lâu hơn ngưỡng này gần như chắc chắn là đã phải chờ khóa
# (trên bảng vài dòng, câu lệnh bình thường chỉ mất vài mili giây).
NGUONG_CHO_KHOA_MS = 80

SO_LAN_THU_TOI_DA = 8

CHE_DO = {
    "khong_khoa": "Không dùng khóa (đọc rồi ghi đè)",
    "bi_quan": "Khóa bi quan – SELECT … FOR UPDATE",
    "lac_quan": "Khóa lạc quan – kiểm tra cột version",
    "nguyen_tu": "Một câu UPDATE nguyên tử có điều kiện",
    "deadlock": "Kịch bản cố ý gây deadlock",
}
CHE_DO_DAT_VE = ("khong_khoa", "bi_quan", "lac_quan", "nguyen_tu")


# ---------------------------------------------------------------- ghi sự kiện
@dataclass
class BoGhi:
    """Thu thập sự kiện từ nhiều luồng, mốc thời gian tính bằng mili giây."""

    goc: float = field(default_factory=time.perf_counter)
    su_kien: list = field(default_factory=list)
    _khoa: threading.Lock = field(default_factory=threading.Lock)

    def moc(self) -> float:
        return (time.perf_counter() - self.goc) * 1000

    def them(self, luong, loai, nhan, bat_dau, ket_thuc=None, sql="", ghi_chu=""):
        sk = {
            "luong": luong,
            "loai": loai,
            "nhan": nhan,
            "bat_dau": round(bat_dau, 2),
            "ket_thuc": round(ket_thuc if ket_thuc is not None else bat_dau, 2),
            "sql": " ".join(sql.split()),
            "ghi_chu": ghi_chu,
            "bi_chan_boi": [],
            "xep_hang_sau": [],
        }
        with self._khoa:
            self.su_kien.append(sk)
        return sk

    def danh_sach(self):
        return sorted(self.su_kien, key=lambda e: (e["bat_dau"], e["ket_thuc"]))


class PhienLamViec:
    """Bọc một kết nối MySQL, tự động bấm giờ và ghi lại mọi câu lệnh."""

    def __init__(self, ten: str, bo_ghi: BoGhi, muc_co_lap: str | None = None):
        self.ten = ten
        self.bo_ghi = bo_ghi
        self.conn = csdl.ket_noi(tu_dong_commit=False, muc_co_lap=muc_co_lap)
        self.ma_ket_noi = csdl.ma_ket_noi(self.conn)
        self.cur = self.conn.cursor()
        # Sự kiện gần nhất của CHÍNH phiên này (không dùng bo_ghi.su_kien[-1]
        # vì đó có thể là sự kiện của luồng khác đang chạy song song)
        self.sk_cuoi = None

    def chay(self, loai, nhan, sql, tham_so=(), ghi_chu=""):
        t0 = self.bo_ghi.moc()
        loi = None
        dong = None
        so_dong = 0
        try:
            so_dong = self.cur.execute(sql, tham_so)
            if sql.lstrip().upper().startswith("SELECT"):
                dong = self.cur.fetchone()
        except pymysql.err.MySQLError as e:
            loi = e
        t1 = self.bo_ghi.moc()
        sql_hien = self.cur.mogrify(sql, tham_so) if tham_so else sql

        if loi is not None:
            ma = loi.args[0] if loi.args else 0
            loai_sk = {MA_LOI_DEADLOCK: "deadlock", MA_LOI_HET_GIO_CHO_KHOA: "het_gio"}.get(ma, "loi")
            thong_diep = loi.args[1] if len(loi.args) > 1 else str(loi)
            self.bo_ghi.them(self.ten, loai_sk, nhan, t0, t1, sql_hien,
                             f"MySQL trả lỗi {ma}: {thong_diep}")
            raise loi

        self.sk_cuoi = self.bo_ghi.them(self.ten, loai, nhan, t0, t1, sql_hien, ghi_chu)
        return dong, so_dong

    def bat_dau_giao_tac(self):
        t0 = self.bo_ghi.moc()
        self.conn.begin()
        self.bo_ghi.them(self.ten, "begin", "START TRANSACTION", t0, self.bo_ghi.moc(),
                         "START TRANSACTION")

    def commit(self, ghi_chu=""):
        t0 = self.bo_ghi.moc()
        self.conn.commit()
        self.bo_ghi.them(self.ten, "commit", "COMMIT", t0, self.bo_ghi.moc(), "COMMIT", ghi_chu)

    def rollback(self, nhan="ROLLBACK", ghi_chu=""):
        t0 = self.bo_ghi.moc()
        try:
            self.conn.rollback()
        except pymysql.err.MySQLError:
            pass
        self.bo_ghi.them(self.ten, "rollback", nhan, t0, self.bo_ghi.moc(), "ROLLBACK", ghi_chu)

    def suy_nghi(self, mili_giay: int, nhan="khách đang cân nhắc"):
        """Kéo dài khoảng thời gian giữa đọc và ghi – nơi tranh chấp xảy ra."""
        if mili_giay <= 0:
            return
        t0 = self.bo_ghi.moc()
        time.sleep(mili_giay / 1000)
        self.bo_ghi.them(self.ten, "cho", nhan, t0, self.bo_ghi.moc(), "",
                         "giao tác vẫn đang mở, chưa commit")

    def dong(self):
        try:
            self.cur.close()
            self.conn.close()
        except Exception:  # noqa: BLE001
            pass


# ------------------------------------------------------------- theo dõi khóa
# CHÚ Ý: không dùng information_schema.innodb_trx để ánh xạ giao tác -> kết nối.
# Bảng đó được phục vụ từ một bộ đệm trung gian, chỉ làm mới khi đã hơn 0,1 giây
# không ai đọc. Luồng theo dõi đọc mỗi 25 ms nên bộ đệm không bao giờ được làm mới
# và mãi trả về ảnh chụp cũ. performance_schema.threads thì được đọc trực tiếp.
#
# data_lock_waits liệt kê MỌI khóa xung đột với yêu cầu đang chờ, kể cả yêu cầu của
# những giao tác khác cũng đang xếp hàng phía trước (LOCK_STATUS = 'WAITING'). Chỉ khóa
# 'GRANTED' mới là người thực sự đang giữ, nên phải ghép thêm data_locks để phân biệt.
#
# Thêm một cái bẫy: THREAD_ID của data_locks là luồng đã TẠO cấu trúc khóa, chưa chắc là
# chủ sở hữu. Ví dụ khi B bị hủy vì deadlock, chính luồng của B trao khóa đang chờ cho A,
# nên khóa của A lại mang THREAD_ID của B. Chủ sở hữu thật là ENGINE_TRANSACTION_ID.
SQL_CHO_KHOA = """
    SELECT tr.PROCESSLIST_ID AS conn_cho,
           tb.PROCESSLIST_ID AS conn_giu,
           w.REQUESTING_ENGINE_TRANSACTION_ID AS trx_cho,
           w.BLOCKING_ENGINE_TRANSACTION_ID   AS trx_giu,
           lb.LOCK_STATUS    AS trang_thai_giu
    FROM performance_schema.data_lock_waits w
    JOIN performance_schema.data_locks lb
      ON lb.ENGINE_LOCK_ID = w.BLOCKING_ENGINE_LOCK_ID AND lb.ENGINE = w.ENGINE
    JOIN performance_schema.threads tr ON tr.THREAD_ID = w.REQUESTING_THREAD_ID
    JOIN performance_schema.threads tb ON tb.THREAD_ID = w.BLOCKING_THREAD_ID
"""

SQL_KHOA = """
    SELECT t.PROCESSLIST_ID AS ma_conn,
           l.ENGINE_TRANSACTION_ID AS trx,
           l.OBJECT_NAME  AS bang,
           l.INDEX_NAME   AS chi_muc,
           l.LOCK_TYPE    AS loai_khoa,
           l.LOCK_MODE    AS che_do_khoa,
           l.LOCK_STATUS  AS trang_thai,
           l.LOCK_DATA    AS du_lieu
    FROM performance_schema.data_locks l
    JOIN performance_schema.threads t ON t.THREAD_ID = l.THREAD_ID
    WHERE l.OBJECT_SCHEMA = DATABASE()
"""


def doc_khoa_hien_tai(cur) -> tuple[list[dict], list[dict]]:
    """Đọc bảng khóa và các cặp chờ khóa, quy mỗi khóa về đúng kết nối SỞ HỮU.

    Khóa ý định mức bảng (IX/IS) luôn do chính giao tác sở hữu tự đặt trước khi khóa
    bất kỳ dòng nào, nên dùng nó để ánh xạ ENGINE_TRANSACTION_ID -> kết nối.
    """
    cur.execute(SQL_KHOA)
    khoa = list(cur.fetchall())
    chu = {k["trx"]: k["ma_conn"] for k in khoa if k["loai_khoa"] == "TABLE"}
    for k in khoa:
        k["ma_conn"] = chu.get(k["trx"], k["ma_conn"])
    cur.execute(SQL_CHO_KHOA)
    cho = list(cur.fetchall())
    for c in cho:
        c["conn_cho"] = chu.get(c["trx_cho"], c["conn_cho"])
        c["conn_giu"] = chu.get(c["trx_giu"], c["conn_giu"])
    return khoa, cho


class TheoDoiKhoa(threading.Thread):
    """Lấy mẫu bảng khóa của InnoDB trong lúc kịch bản đang chạy.

    Đọc từ performance_schema.data_locks và data_lock_waits – đây là
    bằng chứng trực tiếp cho phần lý thuyết về record lock / gap lock.
    """

    def __init__(self, bo_ghi: BoGhi, chu_ky_ms: int = 25):
        super().__init__(daemon=True)
        self.bo_ghi = bo_ghi
        self.chu_ky = chu_ky_ms / 1000
        self.dung = threading.Event()
        self.san_sang = threading.Event()
        self.cho_khoa = []
        self.khoa = {}

    def run(self):
        try:
            conn = csdl.ket_noi(tu_dong_commit=True)
        except Exception:  # noqa: BLE001
            self.san_sang.set()
            return
        self.san_sang.set()
        try:
            with conn.cursor() as cur:
                while not self.dung.is_set():
                    moc = self.bo_ghi.moc()
                    try:
                        cac_khoa, cac_cho = doc_khoa_hien_tai(cur)
                        for d in cac_cho:
                            self.cho_khoa.append({
                                "moc": round(moc, 2),
                                "conn_cho": d["conn_cho"],
                                "conn_giu": d["conn_giu"],
                                "dang_giu": d["trang_thai_giu"] == "GRANTED",
                            })
                        for d in cac_khoa:
                            khoa_chinh = tuple(d[k] for k in (
                                "ma_conn", "bang", "chi_muc", "loai_khoa",
                                "che_do_khoa", "trang_thai", "du_lieu"))
                            if khoa_chinh not in self.khoa:
                                self.khoa[khoa_chinh] = {**d, "moc": round(moc, 2)}
                    except pymysql.err.MySQLError:
                        pass
                    time.sleep(self.chu_ky)
        finally:
            conn.close()

    def ket_qua(self, ten_theo_conn: dict):
        ten = lambda c: ten_theo_conn.get(c, f"kết nối {c}")  # noqa: E731
        cho = [{**c, "ten_cho": ten(c["conn_cho"]), "ten_giu": ten(c["conn_giu"])}
               for c in self.cho_khoa]
        khoa = [{
            "moc": d["moc"], "ten": ten(d["ma_conn"]), "bang": d["bang"],
            "chi_muc": d["chi_muc"], "loai_khoa": d["loai_khoa"],
            "che_do_khoa": d["che_do_khoa"], "trang_thai": d["trang_thai"],
            "du_lieu": d["du_lieu"],
        } for d in self.khoa.values()]
        # Khóa đang chờ lên đầu, rồi tới khóa dòng; khóa ý định mức bảng (IX/IS) để cuối
        uu_tien = lambda k: (k["trang_thai"] != "WAITING", k["loai_khoa"] != "RECORD", k["moc"])  # noqa: E731
        return cho, sorted(khoa, key=uu_tien)


def _gan_bang_chung_cho_khoa(su_kien: list, cho_khoa: list):
    """Đánh dấu câu lệnh nào thực sự bị chặn, và bị ai chặn.

    Ưu tiên bằng chứng từ data_lock_waits; nếu lần lấy mẫu bỏ lỡ (chờ quá
    ngắn) thì dùng thời gian chạy vượt ngưỡng làm dấu hiệu thay thế.
    """
    theo_luong: dict[str, list] = {}
    for c in cho_khoa:
        theo_luong.setdefault(c["ten_cho"], []).append(c)

    for sk in su_kien:
        if sk["loai"] not in ("doc", "ghi", "deadlock", "het_gio"):
            continue
        mau = [c for c in theo_luong.get(sk["luong"], [])
               if sk["bat_dau"] - 1 <= c["moc"] <= sk["ket_thuc"] + 1]
        if mau:
            # Chỉ người đang GIỮ khóa mới là người chặn; người xếp hàng phía trước chỉ là
            # đối thủ cùng chờ. Giữ đúng thứ tự thời gian để thấy hàng đợi tiến lên.
            giu = [c["ten_giu"] for c in sorted(mau, key=lambda c: c["moc"]) if c["dang_giu"]]
            sk["bi_chan_boi"] = list(dict.fromkeys(giu))
            sk["xep_hang_sau"] = sorted({c["ten_giu"] for c in mau if not c["dang_giu"]}
                                        - set(sk["bi_chan_boi"]))
        thoi_gian = sk["ket_thuc"] - sk["bat_dau"]
        if sk["loai"] in ("doc", "ghi") and (mau or thoi_gian > NGUONG_CHO_KHOA_MS):
            sk["loai_goc"] = sk["loai"]
            sk["loai"] = "cho_khoa"
            ds = sk["bi_chan_boi"]
            if not ds:
                ai = "giao tác khác đang giữ"
            elif len(ds) == 1:
                ai = f"{ds[0]} đang giữ"
            else:
                ai = "lần lượt " + " → ".join(ds) + " giữ"
            them = f"bị chặn {thoi_gian:.0f} ms vì chờ khóa do {ai}"
            if sk["xep_hang_sau"]:
                them += f" (xếp hàng cùng {', '.join(sk['xep_hang_sau'])})"
            sk["ghi_chu"] = f"{them} · {sk['ghi_chu']}" if sk["ghi_chu"] else them


# ------------------------------------------------------------------ kịch bản
def _dat_ve(phien: PhienLamViec, che_do: str, ma_chuyen: int, think_ms: int) -> dict:
    """Một khách hàng đặt một vé. Trả về kết quả của riêng khách đó."""
    ten = phien.ten

    if che_do == "nguyen_tu":
        phien.bat_dau_giao_tac()
        _, so_dong = phien.chay(
            "ghi", "trừ ghế có điều kiện",
            "UPDATE chuyen_bay SET so_ghe_trong = so_ghe_trong - 1 "
            "WHERE ma_chuyen = %s AND so_ghe_trong > 0",
            (ma_chuyen,),
            ghi_chu="điều kiện nằm ngay trong câu UPDATE nên không có khe hở giữa đọc và ghi",
        )
        if so_dong == 0:
            phien.rollback("ROLLBACK – hết vé", "UPDATE không tác động dòng nào: đã hết ghế")
            return {"trang_thai": "het_ve", "so_lan_thu": 1}
        phien.chay("ghi", "ghi vé mới",
                   "INSERT INTO ve (ma_chuyen, hanh_khach) VALUES (%s, %s)", (ma_chuyen, ten))
        phien.commit("đặt vé thành công")
        return {"trang_thai": "thanh_cong", "so_lan_thu": 1}

    if che_do == "lac_quan":
        for lan in range(1, SO_LAN_THU_TOI_DA + 1):
            # Mỗi lần thử phải là một giao tác MỚI. Nếu thử lại trong cùng giao
            # tác, ở REPEATABLE READ câu SELECT sẽ đọc lại đúng snapshot cũ và
            # version cũ – vòng lặp sẽ va chạm mãi mãi.
            phien.bat_dau_giao_tac()
            dong, _ = phien.chay(
                "doc", "đọc số ghế còn + version",
                "SELECT so_ghe_trong, version FROM chuyen_bay WHERE ma_chuyen = %s",
                (ma_chuyen,),
            )
            con, ver = dong["so_ghe_trong"], dong["version"]
            phien.sk_cuoi["ghi_chu"] = f"đọc được so_ghe_trong = {con}, version = {ver}"
            if con <= 0:  # thấy hết vé thì rời đi ngay, không cân nhắc nữa
                phien.rollback("ROLLBACK – hết vé", "không còn ghế trống")
                return {"trang_thai": "het_ve", "so_lan_thu": lan}
            phien.suy_nghi(think_ms)
            _, so_dong = phien.chay(
                "ghi", f"ghi nếu version vẫn là {ver}",
                "UPDATE chuyen_bay SET so_ghe_trong = %s, version = version + 1 "
                "WHERE ma_chuyen = %s AND version = %s",
                (con - 1, ma_chuyen, ver),
                ghi_chu="nếu có người khác đã sửa trước thì version đã đổi, số dòng tác động = 0",
            )
            if so_dong == 0:
                phien.rollback("ROLLBACK – va chạm version",
                               f"lần thử {lan}: có người ghi trước, phải đọc lại và thử lại")
                time.sleep(random.uniform(0.004, 0.015) * lan)
                continue
            phien.chay("ghi", "ghi vé mới",
                       "INSERT INTO ve (ma_chuyen, hanh_khach) VALUES (%s, %s)", (ma_chuyen, ten))
            phien.commit("đặt vé thành công")
            return {"trang_thai": "thanh_cong", "so_lan_thu": lan}
        return {"trang_thai": "bo_cuoc", "so_lan_thu": SO_LAN_THU_TOI_DA}

    # khong_khoa và bi_quan dùng chung khung, chỉ khác câu SELECT
    phien.bat_dau_giao_tac()
    if che_do == "bi_quan":
        dong, _ = phien.chay(
            "doc", "đọc và khóa dòng (FOR UPDATE)",
            "SELECT so_ghe_trong FROM chuyen_bay WHERE ma_chuyen = %s FOR UPDATE",
            (ma_chuyen,),
        )
        mo_ta_doc = "đặt khóa X lên dòng, giao tác khác phải xếp hàng"
    else:
        dong, _ = phien.chay(
            "doc", "đọc số ghế còn (không khóa)",
            "SELECT so_ghe_trong FROM chuyen_bay WHERE ma_chuyen = %s",
            (ma_chuyen,),
        )
        mo_ta_doc = "đọc nhất quán theo MVCC, không đặt khóa nào"
    con = dong["so_ghe_trong"]
    phien.sk_cuoi["ghi_chu"] = f"đọc được so_ghe_trong = {con} – {mo_ta_doc}"
    if con <= 0:  # thấy hết vé thì rời đi ngay (và nhả khóa nếu đang giữ)
        phien.rollback("ROLLBACK – hết vé", "không còn ghế trống")
        return {"trang_thai": "het_ve", "so_lan_thu": 1}
    phien.suy_nghi(think_ms)

    phien.chay(
        "ghi", f"ghi đè số ghế = {con - 1}",
        "UPDATE chuyen_bay SET so_ghe_trong = %s WHERE ma_chuyen = %s",
        (con - 1, ma_chuyen),
        ghi_chu=(f"ghi đè bằng giá trị tự tính {con} − 1 = {con - 1}"
                 + (" – nguồn gốc của lost update" if che_do == "khong_khoa" else "")),
    )
    phien.chay("ghi", "ghi vé mới",
               "INSERT INTO ve (ma_chuyen, hanh_khach) VALUES (%s, %s)", (ma_chuyen, ten))
    phien.commit("đặt vé thành công")
    return {"trang_thai": "thanh_cong", "so_lan_thu": 1}


def _giu_ghe_cheo(phien: PhienLamViec, ghe_truoc: int, ghe_sau: int, think_ms: int) -> dict:
    """Kịch bản gây deadlock: hai luồng khóa hai dòng theo thứ tự ngược nhau."""
    phien.bat_dau_giao_tac()
    phien.chay(
        "ghi", f"giữ ghế #{ghe_truoc}",
        "UPDATE ghe SET trang_thai = 'dang_giu', nguoi_giu = %s WHERE ma_ghe = %s",
        (phien.ten, ghe_truoc),
        ghi_chu=f"đặt khóa X lên dòng ghế #{ghe_truoc}",
    )
    phien.suy_nghi(max(think_ms, 60), "đang giữ ghế thứ nhất, chưa commit")
    phien.chay(
        "ghi", f"giữ tiếp ghế #{ghe_sau}",
        "UPDATE ghe SET trang_thai = 'dang_giu', nguoi_giu = %s WHERE ma_ghe = %s",
        (phien.ten, ghe_sau),
        ghi_chu=f"cần khóa X lên ghế #{ghe_sau}",
    )
    phien.commit("giữ được cả hai ghế")
    return {"trang_thai": "thanh_cong", "so_lan_thu": 1}


class CongXuatPhat:
    """Giữ mọi khách ở vạch xuất phát cho tới khi tất cả đã mở xong kết nối.

    Nếu không, khách mở kết nối sớm sẽ chạy xong trước khi khách sau kịp
    vào cuộc – khi đó chẳng có tranh chấp nào để quan sát.
    """

    def __init__(self, so_khach: int):
        self.so_khach = so_khach
        self.da_san_sang = 0
        self._khoa = threading.Lock()
        self._du_nguoi = threading.Event()
        self._phat_lenh = threading.Event()

    def bao_san_sang(self):
        with self._khoa:
            self.da_san_sang += 1
            if self.da_san_sang >= self.so_khach:
                self._du_nguoi.set()

    def cho_du_nguoi(self, toi_da_giay: float) -> bool:
        return self._du_nguoi.wait(toi_da_giay)

    def phat_lenh(self):
        self._phat_lenh.set()

    def cho_lenh(self, toi_da_giay: float = 15):
        self._phat_lenh.wait(toi_da_giay)


def _mot_khach(ten, che_do, ma_chuyen, think_ms, muc_co_lap, bo_ghi, ket_qua, cap_ghe,
               cong: CongXuatPhat):
    phien = None
    try:
        try:
            phien = PhienLamViec(ten, bo_ghi, muc_co_lap)
        finally:
            cong.bao_san_sang()  # kể cả khi kết nối lỗi, để không bắt cả nhóm chờ
        cong.cho_lenh()
        kq = (
            _giu_ghe_cheo(phien, cap_ghe[0], cap_ghe[1], think_ms)
            if che_do == "deadlock"
            else _dat_ve(phien, che_do, ma_chuyen, think_ms)
        )
        ket_qua[ten] = {**kq, "ma_ket_noi": phien.ma_ket_noi}
    except pymysql.err.MySQLError as e:
        ma = e.args[0] if e.args else 0
        loai = {MA_LOI_DEADLOCK: "deadlock", MA_LOI_HET_GIO_CHO_KHOA: "het_gio"}.get(ma, "loi")
        if phien is not None:
            phien.rollback(
                "ROLLBACK (InnoDB tự hủy)" if loai == "deadlock" else "ROLLBACK",
                "InnoDB phát hiện vòng chờ và chọn giao tác này làm nạn nhân"
                if loai == "deadlock" else "giao tác bị hủy",
            )
            ket_qua[ten] = {"trang_thai": loai, "so_lan_thu": 1,
                            "ma_ket_noi": phien.ma_ket_noi, "loi": str(e)}
        else:
            ket_qua[ten] = {"trang_thai": loai, "so_lan_thu": 0, "loi": str(e)}
    except Exception as e:  # noqa: BLE001
        ket_qua[ten] = {"trang_thai": "loi", "so_lan_thu": 0, "loi": str(e)}
    finally:
        if phien is not None:
            phien.dong()


# ------------------------------------------------------------- điều phối chung
def dat_lai_du_lieu(ton_kho: int, ma_chuyen: int = 1):
    conn = csdl.ket_noi(tu_dong_commit=True)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM ve")
            cur.execute("DELETE FROM ghe")
            cur.execute("DELETE FROM chuyen_bay")
            cur.execute("ALTER TABLE ve AUTO_INCREMENT = 1")
            cur.execute(
                "INSERT INTO chuyen_bay (ma_chuyen, so_hieu, tong_ghe, so_ghe_trong, version)"
                " VALUES (%s, %s, %s, %s, 0)",
                (ma_chuyen, "Chuyến bay VN-808 (Hà Nội - TP.HCM)", ton_kho, ton_kho),
            )
            for i in range(1, 3):
                cur.execute(
                    "INSERT INTO ghe (ma_ghe, ma_chuyen, so_ghe) VALUES (%s, %s, %s)",
                    (i, ma_chuyen, f"12{'AB'[i - 1]}"),
                )
    finally:
        conn.close()


def trang_thai_hien_tai(ma_chuyen: int = 1) -> dict:
    conn = csdl.ket_noi(tu_dong_commit=True)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM chuyen_bay WHERE ma_chuyen = %s", (ma_chuyen,))
            chuyen = cur.fetchone()
            cur.execute("SELECT COUNT(*) AS n FROM ve WHERE ma_chuyen = %s", (ma_chuyen,))
            so_ve = cur.fetchone()["n"]
            cur.execute("SELECT ma_ghe, so_ghe, trang_thai, nguoi_giu FROM ghe ORDER BY ma_ghe")
            ghe = cur.fetchall()
        return {"chuyen_bay": chuyen, "so_ve_ban": so_ve, "ghe": ghe}
    finally:
        conn.close()


def kiem_tra_tham_so(che_do: str, so_khach: int, ton_kho: int, think_ms: int, muc_co_lap):
    if che_do not in CHE_DO:
        raise ValueError(f"Chế độ không hợp lệ: {che_do}")
    if not 1 <= so_khach <= 60:
        raise ValueError("Số khách phải từ 1 đến 60")
    if not 1 <= ton_kho <= 500:
        raise ValueError("Số ghế phải từ 1 đến 500")
    if not 0 <= think_ms <= 2000:
        raise ValueError("Thời gian cân nhắc phải từ 0 đến 2000 ms")
    return csdl.chuan_hoa_muc_co_lap(muc_co_lap)


def chay_kich_ban(che_do: str, so_khach: int, ton_kho: int,
                  think_ms: int = 80, muc_co_lap: str | None = None,
                  ma_chuyen: int = 1) -> dict:
    muc_co_lap = kiem_tra_tham_so(che_do, so_khach, ton_kho, think_ms, muc_co_lap)

    dat_lai_du_lieu(ton_kho, ma_chuyen)

    bo_ghi = BoGhi()
    ket_qua: dict = {}
    theo_doi = TheoDoiKhoa(bo_ghi)
    theo_doi.start()
    theo_doi.san_sang.wait(timeout=5)

    cong = CongXuatPhat(so_khach)
    luong = []
    for i in range(so_khach):
        ten = f"Khách {i + 1}"
        cap_ghe = (1, 2) if i % 2 == 0 else (2, 1)
        luong.append(threading.Thread(
            target=_mot_khach,
            args=(ten, che_do, ma_chuyen, think_ms, muc_co_lap, bo_ghi, ket_qua, cap_ghe, cong),
            daemon=True,
        ))

    for t in luong:
        t.start()
    cong.cho_du_nguoi(toi_da_giay=10)
    bo_ghi.goc = time.perf_counter()  # mốc 0 ms = lúc phát lệnh xuất phát
    t0 = time.perf_counter()
    cong.phat_lenh()
    for t in luong:
        t.join(timeout=60)
    tong_thoi_gian = (time.perf_counter() - t0) * 1000

    theo_doi.dung.set()
    theo_doi.join(timeout=2)

    ten_theo_conn = {kq["ma_ket_noi"]: ten for ten, kq in ket_qua.items() if kq.get("ma_ket_noi")}
    cho_khoa, khoa = theo_doi.ket_qua(ten_theo_conn)
    # Mẫu lấy trước lúc xuất phát (mốc âm) không thuộc về lần chạy này
    cho_khoa = [c for c in cho_khoa if c["moc"] >= 0]
    khoa = [k for k in khoa if k["moc"] >= 0]
    su_kien = bo_ghi.danh_sach()
    _gan_bang_chung_cho_khoa(su_kien, cho_khoa)

    sau = trang_thai_hien_tai(ma_chuyen)
    so_ve = sau["so_ve_ban"]
    con_lai = sau["chuyen_bay"]["so_ghe_trong"]
    tong = sau["chuyen_bay"]["tong_ghe"]
    dem = lambda tt: sum(1 for k in ket_qua.values() if k["trang_thai"] == tt)  # noqa: E731
    su_kien_cho = [s for s in su_kien if s["loai"] == "cho_khoa"]

    tom_tat = {
        "che_do": che_do,
        "mo_ta_che_do": CHE_DO[che_do],
        "so_khach": so_khach,
        "tong_ghe": tong,
        "so_ghe_con_lai": con_lai,
        "so_ve_da_ban": so_ve,
        "ban_vuot": max(0, so_ve - tong),
        "nhat_quan": (con_lai + so_ve) == tong,
        "so_thanh_cong": dem("thanh_cong"),
        "so_het_ve": dem("het_ve"),
        "so_deadlock": dem("deadlock"),
        "so_het_gio": dem("het_gio"),
        "so_bo_cuoc": dem("bo_cuoc"),
        "so_loi": dem("loi"),
        "so_lan_thu_lai": sum(max(0, k.get("so_lan_thu", 1) - 1) for k in ket_qua.values()),
        "so_lan_cho_khoa": len(su_kien_cho),
        "tong_thoi_gian_cho_khoa_ms": round(sum(s["ket_thuc"] - s["bat_dau"] for s in su_kien_cho), 1),
        "thoi_gian_ms": round(tong_thoi_gian, 1),
        "muc_co_lap": muc_co_lap or "mặc định (REPEATABLE READ)",
        "think_ms": think_ms,
    }

    return {
        "tom_tat": tom_tat,
        "su_kien": su_kien,
        "ket_qua_khach": ket_qua,
        "cho_khoa": cho_khoa,
        "khoa_quan_sat": khoa,
        "trang_thai_sau": sau,
    }


# ----------------------------------------------------------- so sánh / khảo sát
def _thong_ke(cac_lan: list[dict]) -> dict:
    tg = [t["thoi_gian_ms"] for t in cac_lan]
    tb = lambda k: round(statistics.mean(t[k] for t in cac_lan), 2)  # noqa: E731
    return {
        "so_lan_chay": len(cac_lan),
        "thoi_gian_tb": round(statistics.mean(tg), 1),
        "thoi_gian_min": round(min(tg), 1),
        "thoi_gian_max": round(max(tg), 1),
        "ve_ban_tb": tb("so_ve_da_ban"),
        "ban_vuot_tb": tb("ban_vuot"),
        "thu_lai_tb": tb("so_lan_thu_lai"),
        "cho_khoa_tb": tb("so_lan_cho_khoa"),
        "deadlock_tb": tb("so_deadlock"),
        "bo_cuoc_tb": tb("so_bo_cuoc"),
        "so_lan_sai": sum(1 for t in cac_lan if t["ban_vuot"] > 0 or not t["nhat_quan"]),
    }


def so_sanh_che_do(so_khach: int, ton_kho: int, think_ms: int, so_lan: int = 3,
                   muc_co_lap: str | None = None) -> dict:
    """Chạy lần lượt 4 cách đặt vé với cùng điều kiện rồi lấy trung bình."""
    if not 1 <= so_lan <= 10:
        raise ValueError("Số lần lặp phải từ 1 đến 10")
    ket_qua = {}
    for che_do in CHE_DO_DAT_VE:
        cac_lan = [chay_kich_ban(che_do, so_khach, ton_kho, think_ms, muc_co_lap)["tom_tat"]
                   for _ in range(so_lan)]
        ket_qua[che_do] = {"mo_ta": CHE_DO[che_do], **_thong_ke(cac_lan)}
    return {
        "dieu_kien": {"so_khach": so_khach, "ton_kho": ton_kho, "think_ms": think_ms,
                      "so_lan": so_lan, "muc_co_lap": muc_co_lap or "mặc định"},
        "ket_qua": ket_qua,
    }


def khao_sat_theo_so_khach(cac_muc: list[int], think_ms: int) -> dict:
    """Tăng dần số khách, đo thời gian của từng cách. Số ghế = một nửa số khách."""
    cac_muc = sorted({int(m) for m in cac_muc})
    if not cac_muc or cac_muc[0] < 2 or cac_muc[-1] > 60 or len(cac_muc) > 6:
        raise ValueError("Cần 1–6 mức số khách, mỗi mức từ 2 đến 60")
    chuoi = {che_do: [] for che_do in CHE_DO_DAT_VE}
    for so_khach in cac_muc:
        ton_kho = max(1, so_khach // 2)
        for che_do in CHE_DO_DAT_VE:
            t = chay_kich_ban(che_do, so_khach, ton_kho, think_ms)["tom_tat"]
            chuoi[che_do].append({
                "so_khach": so_khach, "ton_kho": ton_kho,
                "thoi_gian_ms": t["thoi_gian_ms"], "ban_vuot": t["ban_vuot"],
                "thu_lai": t["so_lan_thu_lai"], "cho_khoa": t["so_lan_cho_khoa"],
                "bo_cuoc": t["so_bo_cuoc"],
            })
    return {"cac_muc": cac_muc, "think_ms": think_ms,
            "mo_ta": {k: CHE_DO[k] for k in CHE_DO_DAT_VE}, "chuoi": chuoi}
