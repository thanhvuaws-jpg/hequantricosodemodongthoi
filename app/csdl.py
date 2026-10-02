"""Quản lý kết nối tới MySQL/InnoDB."""
import os
import threading
from contextlib import contextmanager
from pathlib import Path

import pymysql

TEP_LUOC_DO = Path(__file__).resolve().parent.parent / "schema.sql"

CAU_HINH = dict(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", "3310")),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", "demo123"),
    database=os.getenv("DB_NAME", "demo_dongthoi"),
    charset="utf8mb4",
)

MUC_CO_LAP_HOP_LE = (
    "READ UNCOMMITTED",
    "READ COMMITTED",
    "REPEATABLE READ",
    "SERIALIZABLE",
)

# Mọi kịch bản đều xóa và nạp lại dữ liệu, nên tại một thời điểm chỉ được
# chạy một kịch bản. Hai người bấm "Chạy" cùng lúc sẽ ghi đè dữ liệu của nhau.
_KHOA_CHAY = threading.Lock()


class DangBan(Exception):
    """Đang có một kịch bản khác chạy."""


@contextmanager
def giu_quyen_chay():
    if not _KHOA_CHAY.acquire(blocking=False):
        raise DangBan("Đang có một kịch bản khác chạy, hãy đợi nó xong rồi thử lại.")
    try:
        yield
    finally:
        _KHOA_CHAY.release()


def chuan_hoa_muc_co_lap(muc_co_lap: str | None) -> str | None:
    """Trả về tên mức cô lập chuẩn, hoặc None nếu dùng mặc định của máy chủ."""
    if not muc_co_lap:
        return None
    muc = " ".join(muc_co_lap.replace("-", " ").replace("_", " ").upper().split())
    if muc not in MUC_CO_LAP_HOP_LE:
        raise ValueError(f"Mức cô lập không hợp lệ: {muc_co_lap}")
    return muc


def ket_noi(tu_dong_commit: bool = True, muc_co_lap: str | None = None,
            han_cho_khoa: int | None = None):
    """Mở một kết nối mới.

    Mỗi 'khách hàng' trong demo phải có kết nối riêng, vì trong MySQL một
    giao tác gắn liền với một kết nối (session).
    """
    muc = chuan_hoa_muc_co_lap(muc_co_lap)
    conn = pymysql.connect(
        **CAU_HINH,
        autocommit=tu_dong_commit,
        cursorclass=pymysql.cursors.DictCursor,
    )
    with conn.cursor() as cur:
        if muc:
            cur.execute(f"SET SESSION TRANSACTION ISOLATION LEVEL {muc}")
        if han_cho_khoa:
            cur.execute("SET SESSION innodb_lock_wait_timeout = %s", (int(han_cho_khoa),))
    return conn


def dam_bao_luoc_do() -> bool:
    """Tạo lại các bảng từ schema.sql nếu CSDL còn dùng lược đồ cũ hoặc chưa có bảng.

    schema.sql chỉ được MySQL tự chạy khi volume dữ liệu được tạo lần ĐẦU. Khi lược đồ
    thay đổi (ví dụ đổi từ bảng suat_chieu sang chuyen_bay) thì cần chạy lại bằng tay –
    hàm này làm việc đó. Trả về True nếu vừa tạo lại.
    """
    conn = ket_noi(tu_dong_commit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS n FROM information_schema.TABLES"
                " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN ('chuyen_bay', 've', 'ghe')"
            )
            if cur.fetchone()["n"] == 3:
                return False
            dong = [d for d in TEP_LUOC_DO.read_text(encoding="utf-8").splitlines()
                    if not d.strip().startswith("--")]
            for cau in "\n".join(dong).split(";"):   # chú thích '--' giữa dòng do MySQL tự bỏ qua
                if cau.strip():
                    cur.execute(cau)
        return True
    finally:
        conn.close()


def ma_ket_noi(conn) -> int:
    """Lấy CONNECTION_ID() để đối chiếu với bảng theo dõi khóa của InnoDB."""
    with conn.cursor() as cur:
        cur.execute("SELECT CONNECTION_ID() AS ma")
        return cur.fetchone()["ma"]


def thong_tin_may_chu() -> dict:
    conn = ket_noi()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT VERSION() AS phien_ban,"
                " @@default_storage_engine AS engine,"
                " @@transaction_isolation AS muc_co_lap,"
                " @@innodb_lock_wait_timeout AS han_cho_khoa,"
                " @@innodb_deadlock_detect AS phat_hien_deadlock"
            )
            tt = cur.fetchone()
            cur.execute(
                "SELECT TABLE_NAME AS bang, ENGINE AS engine FROM information_schema.TABLES"
                " WHERE TABLE_SCHEMA = %s ORDER BY TABLE_NAME",
                (CAU_HINH["database"],),
            )
            tt["cac_bang"] = cur.fetchall()
            tt["engine_bang"] = next(
                (b["engine"] for b in tt["cac_bang"] if b["bang"] == "chuyen_bay"), None
            )
        return tt
    finally:
        conn.close()
