"""Chụp ảnh giao diện ứng dụng demo để đưa vào báo cáo (lưu vào bao-cao/hinh/).

Yêu cầu: ứng dụng đang chạy ở http://localhost:8010 (khoi-dong.bat).
Chạy:  python chup_giao_dien.py            # chụp tất cả
       python chup_giao_dien.py xungdot    # chỉ một nhóm: tongquan | xungdot | datve | colap | sosanh
Mọi kịch bản đều chạy thật trên MySQL nên số liệu trong ảnh là số liệu đo được lúc chụp.
"""
import json
import sys
import time
from pathlib import Path

from trinh_duyet import Chrome

URL = "http://localhost:8010"
HINH = Path(__file__).resolve().parent.parent / "hinh"
DU_LIEU = Path(__file__).resolve().parent.parent / "du-lieu"   # JSON đúng của lần chạy đã chụp


def luu_json(c, duoi_url, ten):
    DU_LIEU.mkdir(exist_ok=True)
    (DU_LIEU / ten).write_text(json.dumps(c.lay_json(duoi_url), ensure_ascii=False, indent=1), encoding="utf-8")
TI_LE = 1.5

# (mã xung đột, loại kịch bản, bước then chốt cần chụp – theo thanh tiến độ t1, t2, …)
BUOC_THEN_CHOT = [
    ("mat_cap_nhat", "sai", 9),         # kiểm tra cuối: còn 6 ghế thay vì 5
    ("mat_cap_nhat", "dung", 4),        # B bị chặn vì A đang giữ khóa X
    ("doc_rac", "sai", 4),              # A đọc được 0 – bản nháp chưa commit của B
    ("doc_rac", "dung", 4),             # A đọc được 7 – bản đã commit
    ("doc_khong_lap_lai", "sai", 6),    # lần đọc 2 ra 6
    ("doc_khong_lap_lai", "dung", 6),   # lần đọc 2 vẫn ra 7
    ("bong_ma", "sai", 6),              # lần khóa 2 thấy thêm dòng bóng ma
    ("bong_ma", "dung", 4),             # INSERT của B bị gap lock chặn
    ("deadlock", "sai", 6),             # InnoDB phát hiện vòng chờ, lỗi 1213
    ("deadlock", "dung", 4),            # B xếp hàng chờ ghế 12A, không có vòng chờ
]


def an_thanh_tren(c: Chrome):
    """Ẩn thanh tiêu đề dính ở đầu trang và nút 'Hiện thanh trên' để ảnh không bị che."""
    c.js("datAnDau(true)")
    c.js("""(() => { const s = document.createElement('style');
        s.textContent = '#nut-hien-dau{display:none!important}'; document.head.appendChild(s); })()""")


def vung_hop(c: Chrome, cac_sel, le=10):
    """Hình chữ nhật bao quanh nhiều phần tử."""
    return c.js(f"""(() => {{
        const r = {json.dumps(cac_sel)}.map(s => document.querySelector(s)).filter(Boolean)
                  .map(e => e.getBoundingClientRect()).filter(b => b.height > 0);
        const x0 = Math.min(...r.map(b => b.left)), y0 = Math.min(...r.map(b => b.top));
        const x1 = Math.max(...r.map(b => b.right)), y1 = Math.max(...r.map(b => b.bottom));
        return {{x: x0 + scrollX - {le}, y: y0 + scrollY - {le}, w: x1 - x0 + 2 * {le}, h: y1 - y0 + 2 * {le}}};
    }})()""")


def chup_hop(c: Chrome, ten, cac_sel, le=10):
    c.js("window.scrollTo(0, 0)")
    time.sleep(0.3)
    v = vung_hop(c, cac_sel, le)
    tep = c.chup(HINH / ten, max(0, v["x"]), max(0, v["y"]), v["w"], v["h"])
    print("Đã chụp", tep.name, f"({round(v['w'])}×{round(v['h'])} px CSS)")
    return tep


def cho_chay_xong(c: Chrome, nut_chay, toi_da=120):
    """Đợi nút chạy được mở khóa trở lại (kịch bản đã chạy xong)."""
    time.sleep(0.5)
    c.cho(f"!document.querySelector({json.dumps(nut_chay)}).disabled", toi_da)
    time.sleep(0.8)


# ------------------------------------------------------------------ tab 1
def chup_tong_quan(c: Chrome):
    c.mo(URL)
    c.cho("!!document.querySelector('#xd-lich-gt .lgt-dong')")
    c.js("datAnDau(false)")
    time.sleep(1.5)
    c.js("window.scrollTo(0, 0)")
    c.chup(HINH / "giao_dien_tong_quan.png", 0, 0, c.rong, 900)
    print("Đã chụp giao_dien_tong_quan.png")
    # tính năng ẩn thanh trên: cùng một chỗ cuộn, trước và sau khi bấm "Ẩn thanh trên"
    c.js("document.querySelector('#xd-chon-kb button[data-loai=sai]').click()")
    time.sleep(0.5)
    if "Dừng" in c.js("document.querySelector('#xd-phat').textContent"):
        c.js("document.querySelector('#xd-phat').click()")
    c.js("document.querySelector('#xd-tien-do i[data-k=\"5\"]').click()")
    y = c.js("document.querySelector('#xd-san-khau').getBoundingClientRect().top + scrollY - 40")
    c.js(f"window.scrollTo(0, {y})")
    time.sleep(0.8)
    c.chup_khung(HINH / "thanh_tren_dang_hien.png")
    c.js("datAnDau(true)")
    time.sleep(0.8)
    c.chup_khung(HINH / "thanh_tren_da_an.png")
    print("Đã chụp thanh_tren_dang_hien.png, thanh_tren_da_an.png")
    an_thanh_tren(c)
    chup_hop(c, "xd_danh_sach.png", ["#xd-ds"], 12)
    chup_hop(c, "xd_dieu_khien.png", ["#xd-ten", "#xd-chon-kb", "#xd-cach-lam", "#xd-huong-dan",
                                       ".dieu-khien-phat", "#xd-tien-do"], 12)


def mo_kich_ban(c: Chrome, ma, loai):
    if loai == "sai":
        da_chon = c.js(f"document.querySelector('#xd-ds .the-xd[data-ma=\"{ma}\"]')"
                       f".classList.contains('dang-chon')")
        if da_chon:   # thẻ đang chọn bấm lại không chạy – dùng nút "Chạy lại trên MySQL"
            c.js("document.querySelector('#xd-chon-kb button[data-loai=\"sai\"]').click()")
            c.js("document.querySelector('#xd-chay-lai').click()")
        else:
            c.js(f"document.querySelector('#xd-ds .the-xd[data-ma=\"{ma}\"]').click()")
    else:
        c.js("document.querySelector('#xd-chon-kb button[data-loai=\"dung\"]').click()")
    c.cho(f"document.querySelectorAll('#xd-tien-do i').length > 0 && "
          f"document.querySelector('#xd-chon-kb button.dang-chon').dataset.loai === '{loai}' && "
          f"!document.querySelector('#xd-chay-lai').disabled", 60)
    time.sleep(0.6)
    if "Dừng" in c.js("document.querySelector('#xd-phat').textContent"):
        c.js("document.querySelector('#xd-phat').click()")


def chup_xung_dot(c: Chrome):
    c.mo(URL)
    c.cho("!!document.querySelector('#xd-lich-gt .lgt-dong')")
    an_thanh_tren(c)
    luu_json(c, "/api/thong-tin", "thong_tin.json")
    for ma, loai, k in BUOC_THEN_CHOT:
        mo_kich_ban(c, ma, loai)
        luu_json(c, "/api/xung-dot/chay", f"xd_{ma}_{loai}.json")
        c.js(f"document.querySelector('#xd-tien-do i[data-k=\"{k}\"]').click()")
        time.sleep(1.2)
        chup_hop(c, f"xd_{ma}_{loai}.png", ["#xd-loi-dan", "#xd-giai-thich", "#xd-lich", "#xd-san-khau"])
        # tới bước cuối để hiện phần kết luận của kịch bản
        c.js("document.querySelector('#xd-cuoi').click()")
        time.sleep(1.0)
        if c.js("(() => { const e = document.querySelector('#xd-ket-luan'); "
                "return !!e && e.getBoundingClientRect().height > 0; })()"):
            chup_hop(c, f"xd_{ma}_{loai}_ket_luan.png", ["#xd-ket-luan"], 8)
        if loai == "dung" and c.js("(() => { const e = document.querySelector('#xd-the-ss'); "
                                   "return !!e && e.getBoundingClientRect().height > 0; })()"):
            chup_hop(c, f"xd_{ma}_so_sanh.png", ["#xd-the-ss"], 8)


# ------------------------------------------------------------------ tab 2
def chay_dat_ve(c: Chrome, che_do, so_khach=10, ton_kho=5, think=100):
    c.js(f"""(() => {{
        const d = document.querySelector('#dv-che-do'); d.value = '{che_do}'; d.dispatchEvent(new Event('change'));
        for (const [s, v] of [['#dv-so-khach', {so_khach}], ['#dv-ton-kho', {ton_kho}], ['#dv-think', {think}]]) {{
            const e = document.querySelector(s); e.value = v; e.dispatchEvent(new Event('input'));
            e.dispatchEvent(new Event('change')); }}
    }})()""")
    time.sleep(0.4)
    c.js("document.querySelector('#dv-chay').click()")
    cho_chay_xong(c, "#dv-chay")
    # dừng phát lại và tua tới cuối để biểu đồ hiện đủ
    c.js("""(() => { const p = document.querySelector('#dv-phat');
        if (p.textContent.includes('Dừng')) p.click();
        const t = document.querySelector('#dv-tua'); t.value = t.max; t.dispatchEvent(new Event('input')); })()""")
    time.sleep(1.0)


def chup_dat_ve(c: Chrome):
    c.mo(URL + "/#datve")
    c.js("chonTab('datve')")
    an_thanh_tren(c)
    c.cho("document.querySelectorAll('#dv-che-do option').length > 0")
    chup_hop(c, "dv_cau_hinh.png", ["#tab-datve > .the:first-child", "#dv-mo-ta", "#dv-ma"], 10)
    for che_do in ["khong_khoa", "bi_quan", "lac_quan", "nguyen_tu", "deadlock"]:
        chay_dat_ve(c, che_do, so_khach=4 if che_do == "deadlock" else 10)
        luu_json(c, "/api/chay", f"dv_{che_do}.json")
        chup_hop(c, f"dv_{che_do}_ket_qua.png", ["#dv-the-kq"], 8)
        chup_hop(c, f"dv_{che_do}_dong_thoi_gian.png", ["#dv-the-tl"], 8)
        if che_do in ("khong_khoa", "bi_quan"):
            chup_hop(c, f"dv_{che_do}_khoang_ghe.png", ["#dv-the-cabin"], 8)
        if che_do in ("bi_quan", "deadlock"):
            chup_hop(c, f"dv_{che_do}_bang_khoa.png", ["#dv-the-khoa"], 8)
            chup_hop(c, f"dv_{che_do}_nhat_ky.png", ["#dv-the-log"], 8)


# ------------------------------------------------------------------ tab 3
def chup_co_lap(c: Chrome):
    c.mo(URL + "/#colap")
    c.js("chonTab('colap')")
    an_thanh_tren(c)
    c.cho("document.querySelectorAll('#cl-ds .tn').length > 0")
    c.js("document.querySelector('#cl-ma-tran').click()")
    cho_chay_xong(c, "#cl-ma-tran", 180)
    luu_json(c, "/api/thi-nghiem/ma-tran", "cl_ma_tran.json")
    chup_hop(c, "cl_ma_tran.png", ["#cl-the-mt"], 8)
    # một thí nghiệm chi tiết: bóng ma có khóa ở REPEATABLE READ (thấy gap lock)
    c.js("""(() => {
        const tn = [...document.querySelectorAll('#cl-ds .tn')].find(b => b.dataset.ma === 'bong_ma_doc_khoa');
        tn && tn.click();
        const m = [...document.querySelectorAll('#cl-muc button')].find(b => (b.dataset.muc || b.textContent).includes('REPEATABLE'));
        m && m.click(); })()""")
    time.sleep(0.4)
    c.js("document.querySelector('#cl-chay').click()")
    cho_chay_xong(c, "#cl-chay")
    luu_json(c, "/api/thi-nghiem/chay", "cl_bong_ma_rr.json")
    c.js("document.querySelector('#cl-het') && !document.querySelector('#cl-het').disabled && document.querySelector('#cl-het').click()")
    time.sleep(0.8)
    # chỉ lấy từ tiêu đề tới hết bảng khóa ở bước B bị chặn (phần đáng xem nhất), cho vừa một trang báo cáo
    chup_hop(c, "cl_bong_ma_rr.png", ["#cl-the-kq h2", "#cl-the-kq", "#cl-lan tr.dong-khoa"], 8)
    v = vung_hop(c, ["#cl-the-kq"], 8)
    day = c.js("(() => { const r = document.querySelector('#cl-lan tr.dong-khoa').getBoundingClientRect();"
               " return r.bottom + scrollY + 12; })()")
    c.chup(HINH / "cl_bong_ma_rr.png", v["x"], v["y"], v["w"], day - v["y"])
    chup_hop(c, "cl_cau_hinh.png", ["#cl-ds", "#cl-muc", "#cl-chay"], 10)


# ------------------------------------------------------------------ tab 4
def chup_so_sanh(c: Chrome):
    c.mo(URL + "/#sosanh")
    c.js("chonTab('sosanh')")
    an_thanh_tren(c)
    c.js("document.querySelector('#ss-chay').click()")
    cho_chay_xong(c, "#ss-chay", 240)
    luu_json(c, "/api/so-sanh", "ss.json")
    chup_hop(c, "ss_ket_qua.png", ["#ss-kq"], 8)
    c.js("document.querySelector('#ks-chay').click()")
    cho_chay_xong(c, "#ks-chay", 400)
    luu_json(c, "/api/khao-sat", "ks.json")
    chup_hop(c, "ks_ket_qua.png", ["#ks-kq"], 8)


NHOM = {"tongquan": chup_tong_quan, "xungdot": chup_xung_dot, "datve": chup_dat_ve,
        "colap": chup_co_lap, "sosanh": chup_so_sanh}


def main(cac_nhom):
    HINH.mkdir(exist_ok=True)
    c = Chrome(rong=1440, cao=900, ti_le=TI_LE)
    try:
        for ten in cac_nhom:
            print(f"--- {ten}")
            NHOM[ten](c)
        if c.loi_console:
            print("Lỗi console:", c.loi_console)
    finally:
        c.dong()


if __name__ == "__main__":
    main(sys.argv[1:] or list(NHOM))
