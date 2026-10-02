"""Vẽ các sơ đồ minh họa cho báo cáo bằng SVG rồi xuất ra PNG qua Chrome (bao-cao/hinh/so_do_*.png).

Chạy: python so_do.py
"""
import html
import math
import tempfile
from pathlib import Path

from trinh_duyet import Chrome

HINH = Path(__file__).resolve().parent.parent / "hinh"
FONT = "Segoe UI, Arial, sans-serif"
MONO = "Consolas, monospace"

# bảng màu
XANH, XANH_NHAT = "#1d4ed8", "#eff6ff"
TROI, TROI_NHAT = "#0284c7", "#e0f2fe"
CAM, CAM_NHAT = "#d97706", "#fef3c7"
DO, DO_NHAT = "#dc2626", "#fee2e2"
LUC, LUC_NHAT = "#15803d", "#dcfce7"
TIM, TIM_NHAT = "#7c3aed", "#ede9fe"
XAM, XAM_NHAT = "#475569", "#f1f5f9"
CHU = "#0f172a"


class SVG:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.phan = []

    # ---------------------------------------------------------------- hình cơ bản
    def hop(self, x, y, w, h, dong=(), nen=XANH_NHAT, vien=XANH, bo=10, co=15, dam_dong_dau=True,
            mau_chu=CHU, can="giua", day=1.6, net_dut=False, font=FONT):
        dash = ' stroke-dasharray="6 4"' if net_dut else ""
        self.phan.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{bo}" fill="{nen}" '
                         f'stroke="{vien}" stroke-width="{day}"{dash}/>')
        if isinstance(dong, str):
            dong = [dong]
        if dong:
            cao_dong = co * 1.35
            y0 = y + h / 2 - (len(dong) - 1) * cao_dong / 2 + co * 0.35
            for i, d in enumerate(dong):
                dam = dam_dong_dau and i == 0
                if can == "giua":
                    self.chu(x + w / 2, y0 + i * cao_dong, d, co=co if i == 0 else co - 1.5, dam=dam,
                             mau=mau_chu, neo="middle", font=font)
                else:
                    self.chu(x + 14, y0 + i * cao_dong, d, co=co if i == 0 else co - 1.5, dam=dam,
                             mau=mau_chu, neo="start", font=font)

    def chu(self, x, y, s, co=14, dam=False, mau=CHU, neo="middle", nghieng=False, font=FONT):
        w = ' font-weight="700"' if dam else ""
        it = ' font-style="italic"' if nghieng else ""
        self.phan.append(f'<text x="{x}" y="{y}" font-family="{font}" font-size="{co}"{w}{it} fill="{mau}" '
                         f'text-anchor="{neo}">{html.escape(s)}</text>')

    def mui_ten(self, x1, y1, x2, y2, mau=XAM, nhan="", net_dut=False, day=1.8, lech_nhan=(0, -8), co=13,
                hai_dau=False, cong=0):
        """Mũi tên thẳng (cong=0) hoặc cong bậc hai (cong = độ lệch điểm điều khiển)."""
        id_ = f"m{len(self.phan)}"
        dash = ' stroke-dasharray="7 5"' if net_dut else ""
        self.phan.append(
            f'<defs><marker id="{id_}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{mau}"/></marker></defs>')
        dau = f' marker-start="url(#{id_})"' if hai_dau else ""
        if cong:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            dx, dy = x2 - x1, y2 - y1
            d = math.hypot(dx, dy) or 1
            cx, cy = mx - dy / d * cong, my + dx / d * cong
            self.phan.append(f'<path d="M{x1},{y1} Q{cx},{cy} {x2},{y2}" fill="none" stroke="{mau}" '
                             f'stroke-width="{day}"{dash} marker-end="url(#{id_})"{dau}/>')
            nx, ny = (x1 + 2 * cx + x2) / 4, (y1 + 2 * cy + y2) / 4
        else:
            self.phan.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{mau}" stroke-width="{day}"'
                             f'{dash} marker-end="url(#{id_})"{dau}/>')
            nx, ny = (x1 + x2) / 2, (y1 + y2) / 2
        if nhan:
            for i, dong in enumerate(nhan.split("\n")):
                self.chu(nx + lech_nhan[0], ny + lech_nhan[1] + i * (co + 3), dong, co=co, mau=mau,
                         dam=False)

    def duong(self, diem, mau=XAM, day=1.6, net_dut=False):
        dash = ' stroke-dasharray="7 5"' if net_dut else ""
        d = " ".join(f"{x},{y}" for x, y in diem)
        self.phan.append(f'<polyline points="{d}" fill="none" stroke="{mau}" stroke-width="{day}"{dash}/>')

    def elip(self, cx, cy, rx, ry, dong, nen=XANH_NHAT, vien=XANH, co=14):
        self.phan.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{nen}" stroke="{vien}" '
                         f'stroke-width="1.6"/>')
        if isinstance(dong, str):
            dong = [dong]
        for i, d in enumerate(dong):
            self.chu(cx, cy + co * 0.35 + (i - (len(dong) - 1) / 2) * co * 1.3, d, co=co)

    def nguoi(self, cx, cy, ten, mau=XANH):
        """Hình tác nhân (actor) của sơ đồ use case."""
        self.phan.append(
            f'<circle cx="{cx}" cy="{cy - 46}" r="14" fill="white" stroke="{mau}" stroke-width="2"/>'
            f'<line x1="{cx}" y1="{cy - 32}" x2="{cx}" y2="{cy + 6}" stroke="{mau}" stroke-width="2"/>'
            f'<line x1="{cx - 22}" y1="{cy - 20}" x2="{cx + 22}" y2="{cy - 20}" stroke="{mau}" stroke-width="2"/>'
            f'<line x1="{cx}" y1="{cy + 6}" x2="{cx - 18}" y2="{cy + 34}" stroke="{mau}" stroke-width="2"/>'
            f'<line x1="{cx}" y1="{cy + 6}" x2="{cx + 18}" y2="{cy + 34}" stroke="{mau}" stroke-width="2"/>')
        for i, d in enumerate(ten.split("\n")):
            self.chu(cx, cy + 58 + i * 18, d, co=14, dam=True)

    def raw(self, s):
        self.phan.append(s)

    def xuat(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}"><rect width="100%" height="100%" fill="white"/>'
                + "".join(self.phan) + "</svg>")


# ============================================================== Chương 2
def trang_thai_giao_tac():
    s = SVG(980, 380)
    W, H = 200, 64
    s.hop(40, 160, W, H, ["Hoạt động", "(Active)"], XANH_NHAT, XANH)
    s.hop(350, 60, W, H, ["Ủy thác một phần", "(Partially committed)"], TROI_NHAT, TROI)
    s.hop(720, 60, W, H, ["Đã ủy thác", "(Committed)"], LUC_NHAT, LUC)
    s.hop(350, 260, W, H, ["Thất bại", "(Failed)"], CAM_NHAT, CAM)
    s.hop(720, 260, W, H, ["Đã hủy bỏ", "(Aborted)"], DO_NHAT, DO)
    s.mui_ten(240, 175, 350, 100, XAM, "thực hiện xong\nlệnh cuối", lech_nhan=(-40, -16))
    s.mui_ten(240, 210, 350, 285, XAM, "gặp lỗi /\nbị hủy", lech_nhan=(-40, 18))
    s.mui_ten(550, 92, 720, 92, LUC, "ghi log thành công", lech_nhan=(0, -12), co=12.5)
    s.mui_ten(450, 124, 450, 260, CAM, "lỗi khi ghi", lech_nhan=(46, 0))
    s.mui_ten(550, 292, 720, 292, DO, "ROLLBACK – hoàn tác", lech_nhan=(0, -12), co=12.5)
    s.chu(490, 30, "Các trạng thái của một giao tác", co=17, dam=True)
    return s

def kien_truc_mysql():
    s = SVG(980, 640)
    s.hop(40, 30, 900, 64, ["Ứng dụng khách", "mysql CLI · phpMyAdmin · ứng dụng Python (PyMySQL) – mỗi phiên là một kết nối"],
          XAM_NHAT, XAM)
    s.mui_ten(490, 94, 490, 124, XAM)
    s.hop(40, 124, 900, 150, [], "#f8fafc", XANH, bo=14)
    s.chu(70, 152, "Tầng máy chủ MySQL (SQL layer)", co=16, dam=True, neo="start", mau=XANH)
    for i, (t, m) in enumerate([("Quản lý kết nối", "một luồng / phiên"), ("Bộ phân tích cú pháp", "parser"),
                                ("Bộ tối ưu hóa", "optimizer"), ("Bộ thực thi", "executor")]):
        s.hop(70 + i * 215, 170, 195, 80, [t, m], XANH_NHAT, XANH, co=14)
    s.mui_ten(490, 274, 490, 304, XAM, "API lưu trữ (handler API)", lech_nhan=(110, 4))
    s.hop(40, 304, 900, 230, [], "#fffbeb", CAM, bo=14)
    s.chu(70, 332, "Storage engine InnoDB (mặc định – hỗ trợ giao tác ACID và khóa dòng)", co=16, dam=True,
          neo="start", mau=CAM)
    khoi = [("Buffer pool", "trang dữ liệu & chỉ mục\ntrong bộ nhớ"),
            ("Hệ thống khóa", "record / gap / next-key\nphát hiện deadlock"),
            ("MVCC – undo log", "phiên bản cũ của dòng\nphục vụ đọc nhất quán"),
            ("Redo log", "ghi trước (WAL)\nbảo đảm bền vững")]
    for i, (t, m) in enumerate(khoi):
        s.hop(70 + i * 215, 350, 195, 120, [t] + m.split("\n"), CAM_NHAT, CAM, co=14)
    s.chu(490, 505, "performance_schema.data_locks / data_lock_waits cho phép quan sát khóa đang giữ và đang chờ",
          co=13, nghieng=True, mau=XAM)
    s.mui_ten(490, 534, 490, 564, XAM)
    s.hop(40, 564, 900, 56, ["Đĩa: tablespace (.ibd) · tệp redo log · undo tablespace"], XAM_NHAT, XAM)
    return s


def mvcc():
    s = SVG(980, 470)
    s.chu(490, 30, "Dòng chuyen_bay (ma_chuyen = 1) khi giao tác B đã UPDATE nhưng CHƯA COMMIT", co=16, dam=True)
    # bản mới nhất
    s.hop(60, 70, 380, 120, ["Bản mới nhất (trong trang dữ liệu)", "so_ghe_trong = 0",
                             "DB_TRX_ID = T_B (chưa commit)", "DB_ROLL_PTR → undo log"],
          CAM_NHAT, CAM, co=14)
    s.hop(60, 270, 380, 110, ["Bản cũ (dựng lại từ undo log)", "so_ghe_trong = 7",
                              "DB_TRX_ID = T₀ (đã commit)"], LUC_NHAT, LUC, co=14)
    s.mui_ten(250, 190, 250, 270, CAM, "con trỏ hoàn tác\n(roll pointer)", lech_nhan=(78, -6))
    # các bên đọc
    s.hop(560, 70, 380, 90, ["A đọc ở READ UNCOMMITTED", "đọc thẳng bản mới nhất → thấy 0",
                             "(đọc dữ liệu rác)"], DO_NHAT, DO, co=14)
    s.hop(560, 190, 380, 100, ["A đọc ở READ COMMITTED / REPEATABLE READ",
                               "read view: T_B chưa commit → không thấy",
                               "→ lần theo undo log, đọc được 7"], LUC_NHAT, LUC, co=14)
    s.hop(560, 320, 380, 90, ["A đọc có khóa (FOR UPDATE)", "đọc hiện hành → phải chờ khóa X của B"],
          TIM_NHAT, TIM, co=14)
    s.mui_ten(560, 115, 440, 120, DO)
    s.mui_ten(560, 245, 440, 320, LUC)
    s.mui_ten(560, 365, 440, 150, TIM, net_dut=True)
    s.chu(490, 450, "Nhờ nhiều phiên bản, người đọc không phải chờ người ghi (trừ khi đọc có khóa).",
          co=14, nghieng=True, mau=XAM)
    return s


def khoa_chi_muc():
    s = SVG(1000, 520)
    s.chu(500, 30, "Chỉ mục fk_ve_chuyen (ma_chuyen, ma_ve) của bảng ve – A chạy: "
                   "SELECT … FROM ve WHERE ma_chuyen = 1 FOR UPDATE", co=15, dam=True)
    khoa = ["(1, 1)", "(1, 2)", "(1, 3)", "(2, 4)", "(2, 5)"]
    x0, dx, y = 120, 170, 110
    s.duong([(40, y + 25), (960, y + 25)], XAM, 2)
    s.chu(40, y + 60, "−∞", co=14, neo="start", mau=XAM)
    s.chu(960, y + 60, "+∞", co=14, neo="end", mau=XAM)
    for i, k in enumerate(khoa):
        nen, vien = (CAM_NHAT, CAM) if i < 3 else (XAM_NHAT, XAM)
        s.hop(x0 + i * dx, y, 110, 50, [k], nen, vien, co=15)
    # REPEATABLE READ
    yr = 210
    s.chu(40, yr, "REPEATABLE READ:", co=15, dam=True, neo="start", mau=LUC)
    for i in range(3):
        xa = x0 + i * dx - (60 if i == 0 else 60)
        s.hop(xa - (0 if i else 0), yr + 14, 170, 34, ["next-key lock"], LUC_NHAT, LUC, co=13)
    s.hop(x0 + 3 * dx - 60, yr + 14, 60, 34, ["gap"], LUC_NHAT, LUC, co=13)
    s.chu(40, yr + 80, "→ khóa cả 3 dòng VÀ các khoảng trống trước chúng, kể cả khoảng ((1, 3), (2, 4)).",
          co=14, neo="start")
    s.chu(40, yr + 104, "B chèn vé (ma_chuyen = 1) → vị trí mới rơi vào khoảng đã bị khóa "
                        "→ chờ khóa INSERT_INTENTION → BỊ CHẶN, không có bóng ma.", co=14, neo="start", mau=LUC)
    # READ COMMITTED
    yc = 360
    s.chu(40, yc, "READ COMMITTED:", co=15, dam=True, neo="start", mau=DO)
    for i in range(3):
        s.hop(x0 + i * dx, yc + 14, 110, 34, ["record lock"], DO_NHAT, DO, co=13)
    s.chu(40, yc + 80, "→ chỉ khóa đúng 3 bản ghi đang tồn tại, KHÔNG khóa khoảng trống.", co=14, neo="start")
    s.chu(40, yc + 104, "B chèn vé mới vào sau (1, 3) thành công → lần khóa sau A thấy thêm một dòng "
                        "\"bóng ma\".", co=14, neo="start", mau=DO)
    # vị trí chèn
    xi = x0 + 2 * dx + 110 + 30
    s.mui_ten(xi, 74, xi, y - 4, TIM, "", day=2)
    s.chu(xi, 66, "B chèn (1, 6)", co=13, dam=True, mau=TIM)
    return s


def do_thi_cho():
    s = SVG(900, 400)
    s.chu(450, 32, "Đồ thị chờ (wait-for graph) của kịch bản deadlock", co=17, dam=True)
    s.elip(200, 200, 110, 60, ["T₁ – phiên A", "giữ X trên ghế 12A"], XANH_NHAT, XANH)
    s.elip(700, 200, 110, 60, ["T₂ – phiên B", "giữ X trên ghế 12B"], TIM_NHAT, TIM)
    s.mui_ten(300, 170, 600, 170, DO, "T₁ chờ khóa ghế 12B do T₂ giữ", cong=-50, lech_nhan=(0, -14), day=2.2)
    s.mui_ten(600, 230, 300, 230, DO, "T₂ chờ khóa ghế 12A do T₁ giữ", cong=-50, lech_nhan=(0, 28), day=2.2)
    s.hop(230, 320, 440, 56, ["Có chu trình T₁ → T₂ → T₁ ⇒ deadlock",
                              "InnoDB hủy một giao tác (lỗi 1213) để phá vòng"], DO_NHAT, DO, co=14)
    return s


# ============================================================== Chương 3
def use_case():
    uc = ["Xem 5 xung đột: kịch bản SAI và ĐÚNG", "Phát hoạt hình lịch giao tác từng bước",
          "Chạy lại kịch bản trên MySQL thật", "Mô phỏng nhiều khách đặt vé đồng thời",
          "Xem bảng khóa InnoDB (data_locks)", "Chạy ma trận 6 hiện tượng × 4 mức cô lập",
          "So sánh hiệu năng 4 cách xử lý", "Khảo sát chịu tải theo số khách"]
    s = SVG(900, 110 + len(uc) * 66)
    s.hop(300, 20, 580, 70 + len(uc) * 66, [], "#f8fafc", XANH, bo=16)
    s.chu(590, 50, "Ứng dụng demo điều khiển truy xuất đồng thời", co=16, dam=True, mau=XANH)
    tam_y = 20 + (70 + len(uc) * 66) / 2
    s.nguoi(130, tam_y, "Người học /\nGiảng viên")
    for i, ten in enumerate(uc):
        cy = 100 + i * 66
        s.duong([(156, tam_y - 24), (395, cy)], XAM, 1.2)
        s.elip(590, cy, 200, 27, [ten], XANH_NHAT, XANH, co=14)
    return s

def kien_truc_he_thong():
    s = SVG(1000, 640)
    s.hop(30, 30, 260, 300, [], XAM_NHAT, XAM, bo=14)
    s.chu(160, 58, "Trình duyệt", co=16, dam=True)
    for i, t in enumerate(["Tab 1 – 5 xung đột", "Tab 2 – Nhiều khách", "Tab 3 – Ma trận cô lập",
                           "Tab 4 – So sánh hiệu năng"]):
        s.hop(50, 76 + i * 58, 220, 46, [t], "white", XAM, co=13.5, dam_dong_dau=False)
    s.chu(160, 318, "HTML · CSS · JavaScript", co=12.5, nghieng=True, mau=XAM)
    s.mui_ten(290, 170, 370, 170, XANH, "HTTP / JSON", hai_dau=True, lech_nhan=(0, -10))
    # container ứng dụng
    s.hop(370, 30, 600, 300, [], "#f8fafc", XANH, bo=14, net_dut=True)
    s.chu(670, 56, "Container demo_dongthoi_app – Python 3.13 · FastAPI · Uvicorn", co=14.5, dam=True, mau=XANH)
    mo = [("main.py", "API REST"), ("xungdot.py", "5 xung đột × sai/đúng"),
          ("phongthinghiem.py", "bộ điều phối 2 phiên"), ("kichban.py", "nhiều khách + theo dõi khóa"),
          ("csdl.py", "kết nối, mức cô lập")]
    for i, (t, m) in enumerate(mo):
        cot, hang = i % 3, i // 3
        s.hop(390 + cot * 195, 76 + hang * 120, 180, 96, [t, m], XANH_NHAT, XANH, co=14, font=FONT)
    s.mui_ten(670, 330, 670, 410, CAM, "PyMySQL – nhiều kết nối song song:\nphiên A, phiên B, khách 1…60,\n"
                                       "kết nối theo dõi khóa", lech_nhan=(-190, -20), hai_dau=True, co=12.5)
    s.hop(370, 410, 600, 200, [], "#fffbeb", CAM, bo=14, net_dut=True)
    s.chu(670, 436, "Container demo_dongthoi_mysql – MySQL 9.6 (cổng 3310)", co=14.5, dam=True, mau=CAM)
    s.hop(390, 456, 270, 130, ["CSDL demo_dongthoi", "chuyen_bay · ve · ghe", "ENGINE = InnoDB"],
          CAM_NHAT, CAM, co=14)
    s.hop(680, 456, 270, 130, ["performance_schema", "data_locks", "data_lock_waits · threads"],
          CAM_NHAT, CAM, co=14)
    s.hop(30, 410, 300, 200, ["Docker Compose", "khoi-dong.bat · chay-test.bat · dung.bat",
                              "volume mysql_data giữ dữ liệu", "schema.sql tự tạo bảng"], XAM_NHAT, XAM, co=13.5)
    return s


def luoc_do_csdl():
    s = SVG(980, 470)

    def bang(x, y, ten, cot, mau, nen):
        h = 44 + len(cot) * 30
        s.hop(x, y, 270, h, [], "white", mau, bo=8)
        s.raw(f'<rect x="{x}" y="{y}" width="270" height="40" rx="8" fill="{nen}" stroke="{mau}" stroke-width="1.6"/>')
        s.chu(x + 135, y + 26, ten, co=16, dam=True, mau=mau)
        for i, (c, kieu, kh) in enumerate(cot):
            yy = y + 66 + i * 30
            s.chu(x + 16, yy, c, co=14, dam=bool(kh), neo="start",
                  mau=CHU if kh != "FK" else TROI, font=MONO)
            s.chu(x + 254, yy, kieu + (f"  {kh}" if kh else ""), co=12.5, neo="end", mau=XAM, font=MONO)
        return h

    bang(355, 30, "chuyen_bay", [("ma_chuyen", "INT", "PK"), ("so_hieu", "VARCHAR(100)", ""),
                                 ("tong_ghe", "INT", ""), ("so_ghe_trong", "INT", ""),
                                 ("version", "INT", "")], XANH, XANH_NHAT)
    bang(30, 220, "ve", [("ma_ve", "INT AI", "PK"), ("ma_chuyen", "INT", "FK"),
                         ("hanh_khach", "VARCHAR(50)", ""), ("thoi_diem", "DATETIME(6)", "")], TROI, TROI_NHAT)
    bang(680, 220, "ghe", [("ma_ghe", "INT", "PK"), ("ma_chuyen", "INT", "FK"),
                           ("so_ghe", "VARCHAR(10)", ""), ("trang_thai", "VARCHAR(20)", ""),
                           ("nguoi_giu", "VARCHAR(50)", "")], TIM, TIM_NHAT)
    # khóa ngoại ma_chuyen (dòng thứ 2 của ve/ghe) trỏ tới khóa chính ma_chuyen của chuyen_bay
    s.duong([(300, 312), (325, 312), (325, 92)], TROI, 1.8)
    s.mui_ten(325, 92, 355, 92, TROI, day=1.8)
    s.chu(318, 200, "N", co=14, dam=True, mau=TROI, neo="end")
    s.chu(340, 84, "1", co=14, dam=True, mau=TROI)
    s.duong([(680, 312), (655, 312), (655, 92)], TIM, 1.8)
    s.mui_ten(655, 92, 625, 92, TIM, day=1.8)
    s.chu(662, 200, "N", co=14, dam=True, mau=TIM, neo="start")
    s.chu(640, 84, "1", co=14, dam=True, mau=TIM)
    s.chu(490, 455, "Mọi bảng dùng ENGINE = InnoDB; so_ghe_trong là điểm tranh chấp chính, "
                    "version phục vụ khóa lạc quan.", co=13.5, nghieng=True, mau=XAM)
    return s

def dieu_phoi():
    s = SVG(1000, 720)
    s.chu(500, 30, "Bộ điều phối hai phiên – thuc_thi_hai_phien()", co=17, dam=True)
    s.hop(340, 55, 320, 50, ["Lấy bước tiếp theo của kịch bản"], XAM_NHAT, XAM, co=14)
    s.mui_ten(500, 105, 500, 135, XAM)
    s.raw('<polygon points="500,135 700,185 500,235 300,185" fill="#fef3c7" stroke="#d97706" stroke-width="1.6"/>')
    s.chu(500, 182, "Phiên của bước này đang bị chặn", co=14, dam=True)
    s.chu(500, 200, "hoặc còn bước bị hoãn?", co=14)
    s.mui_ten(700, 185, 790, 185, CAM, "có", lech_nhan=(0, -8))
    s.hop(790, 150, 190, 70, ["HOÃN bước", "xếp vào hàng đợi"], CAM_NHAT, CAM, co=14)
    s.mui_ten(500, 235, 500, 270, XAM, "không", lech_nhan=(30, 4))
    s.hop(310, 270, 380, 56, ["Gửi câu lệnh cho luồng của phiên", "(mỗi phiên = 1 kết nối + 1 luồng riêng)"],
          XANH_NHAT, XANH, co=14)
    s.mui_ten(500, 326, 500, 356, XAM)
    s.raw('<polygon points="500,356 690,406 500,456 310,406" fill="#fef3c7" stroke="#d97706" stroke-width="1.6"/>')
    s.chu(500, 403, "Trả về trong 700 ms?", co=14, dam=True)
    s.chu(500, 421, "(CHO_CHAN_MS)", co=13, mau=XAM)
    s.mui_ten(310, 406, 220, 406, LUC, "có", lech_nhan=(0, -8))
    s.hop(20, 366, 200, 90, ["Ghi kết quả,", "chụp bảng khóa và", "dữ liệu 2 góc nhìn"], LUC_NHAT, LUC, co=13.5)
    s.mui_ten(690, 406, 780, 406, DO, "không", lech_nhan=(0, -8))
    s.hop(780, 366, 200, 90, ["Đánh dấu BỊ CHẶN,", "chụp data_locks và", "data_lock_waits"], DO_NHAT, DO, co=13.5)
    # cả ba nhánh dồn về bước dọn dẹp
    s.duong([(120, 456), (120, 520), (280, 520)], LUC)
    s.mui_ten(280, 520, 300, 520, LUC)
    s.duong([(880, 456), (880, 520), (720, 520)], DO)
    s.mui_ten(720, 520, 700, 520, DO)
    s.duong([(980, 185), (990, 185), (990, 540), (720, 540)], CAM, net_dut=True)
    s.mui_ten(720, 540, 700, 540, CAM)
    s.hop(300, 490, 400, 100, ["Dọn dẹp trước bước kế", "câu bị chặn đã xong (phiên kia commit/rollback",
                               "hoặc InnoDB phá deadlock) → ghi kết quả,", "rồi CHẠY BÙ các bước đã hoãn"],
          TIM_NHAT, TIM, co=13.5)
    s.mui_ten(500, 590, 500, 630, XAM)
    s.hop(330, 630, 340, 50, ["Hết kịch bản → chờ nốt câu đang treo, đóng phiên"], XAM_NHAT, XAM, co=13.5,
          dam_dong_dau=False)
    s.duong([(300, 540), (40, 540), (40, 80), (340, 80)], XAM, net_dut=True)
    s.mui_ten(320, 80, 340, 80, XAM)
    s.chu(46, 300, "lặp", co=13, neo="start", mau=XAM, nghieng=True)
    return s


SO_DO = {
    "so_do_trang_thai_giao_tac": trang_thai_giao_tac,
    "so_do_kien_truc_mysql": kien_truc_mysql,
    "so_do_mvcc": mvcc,
    "so_do_khoa_chi_muc": khoa_chi_muc,
    "so_do_do_thi_cho": do_thi_cho,
    "so_do_use_case": use_case,
    "so_do_kien_truc_he_thong": kien_truc_he_thong,
    "so_do_luoc_do_csdl": luoc_do_csdl,
    "so_do_dieu_phoi": dieu_phoi,
}


def main():
    HINH.mkdir(exist_ok=True)
    tam = Path(tempfile.mkdtemp(prefix="so-do-"))
    c = Chrome(rong=1100, cao=800, ti_le=2)
    try:
        for ten, ham in SO_DO.items():
            s = ham()
            tep = tam / f"{ten}.html"
            tep.write_text(f"<!doctype html><meta charset='utf-8'><body style='margin:0;background:white'>"
                           f"{s.xuat()}</body>", encoding="utf-8")
            c.mo(tep.as_uri())
            c.chup(HINH / f"{ten}.png", 0, 0, s.w, s.h)
            print("Đã vẽ", ten)
    finally:
        c.dong()


if __name__ == "__main__":
    main()
