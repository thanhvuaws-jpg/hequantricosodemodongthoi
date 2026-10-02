"""Dựng báo cáo tiểu luận (.docx) từ chính file format của trường ("format tieu luan.docx").

Giữ nguyên trang bìa, danh sách nhóm, bảng cán bộ chấm thi; điền danh mục viết tắt; thay phần mục lục mẫu
bằng mục lục tự động (TOC) và danh mục bảng/hình tự động; sau đó viết toàn bộ nội dung từ noi_dung_bao_cao.py.
Mục lục và số trang được Word cập nhật ở bước cuối (cap_nhat_word.ps1).

Chạy: python tao_bao_cao.py
"""
import copy
import re
import unicodedata
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from docx.text.paragraph import Paragraph
from PIL import Image

import noi_dung_bao_cao as ND

GOC = Path(__file__).resolve().parent.parent          # demo-dongthoi/bao-cao
MAU = GOC.parent / "format tieu luan.docx"
HINH = GOC / "hinh"
RA = GOC / "BaoCao_TieuLuan_DieuKhienTruyXuatDongThoi.docx"

TNR = "Times New Roman"
RONG_CHU = 16.5          # bề rộng vùng chữ (cm): Letter 21,59 − lề trái 3 − lề phải 2
CAO_HINH_TOI_DA = 20.5   # cm


def chuan(s):
    """So sánh chuỗi tiếng Việt an toàn: cùng dạng Unicode NFC, bỏ khoảng trắng hai đầu."""
    return unicodedata.normalize("NFC", s or "").strip()


# ============================================================== tiện ích XML
def dat_font(run_or_style_font, ten=TNR):
    f = run_or_style_font
    f.name = ten
    rpr = f.element.rPr if hasattr(f, "element") else None
    return rpr


def font_ca_4(elm, ten=TNR):
    """Đặt phông cho cả ascii / hAnsi / eastAsia / cs (để tiếng Việt không bị đổi phông)."""
    rpr = elm.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    for k in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(k), ten)
    for k in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rf.get(qn(k)) is not None:
            del rf.attrib[qn(k)]


def to_nen_o(o, mau):
    tcPr = o._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), mau)
    tcPr.append(shd)


def bo_to_sang(run):
    rpr = run._r.rPr
    if rpr is not None:
        for e in rpr.findall(qn("w:highlight")):
            rpr.remove(e)


def them_truong(p, lenh, chu_tam="Nhấn F9 để cập nhật"):
    """Chèn một trường (field) Word: { lenh }."""
    def r_(kieu=None, text=None, instr=None):
        r = OxmlElement("w:r")
        if kieu:
            fc = OxmlElement("w:fldChar")
            fc.set(qn("w:fldCharType"), kieu)
            if kieu == "begin":
                fc.set(qn("w:dirty"), "true")
            r.append(fc)
        if instr:
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = instr
            r.append(it)
        if text:
            t = OxmlElement("w:t")
            t.set(qn("xml:space"), "preserve")
            t.text = text
            r.append(t)
        return r
    for e in (r_("begin"), r_(instr=f" {lenh} "), r_("separate"), r_(text=chu_tam), r_("end")):
        p._p.append(e)


def muc_dan_y(p, cap):
    """Đặt mức dàn ý cho đoạn (để vào mục lục mà không cần kiểu Heading)."""
    pPr = p._p.get_or_add_pPr()
    o = OxmlElement("w:outlineLvl")
    o.set(qn("w:val"), str(cap))
    pPr.append(o)


def lap_lai_dau_bang(hang):
    trPr = hang._tr.get_or_add_trPr()
    e = OxmlElement("w:tblHeader")
    e.set(qn("w:val"), "true")
    trPr.append(e)


def khong_tach_hang(hang):
    hang._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))


# ============================================================== kiểu (style)
def kieu_san_co(d, id_nguon, id_moi, ten_moi):
    """Tạo kiểu dựng sẵn của Word (heading 3, toc 3…) bằng cách sao chép một kiểu cùng loại trong file mẫu.
    Không dùng styles.add_style vì Word sẽ coi đó là kiểu tự đặt, đổi tên thành "Heading 31" và dùng
    kiểu mặc định của nó (phông Calibri) cho mục lục."""
    goc = d.styles.element
    if goc.find(f"{qn('w:style')}[@{qn('w:styleId')}='{id_moi}']") is not None:
        return
    nguon = goc.find(f"{qn('w:style')}[@{qn('w:styleId')}='{id_nguon}']")
    moi = copy.deepcopy(nguon)
    moi.set(qn("w:styleId"), id_moi)
    moi.find(qn("w:name")).set(qn("w:val"), ten_moi)
    for tag in ("w:link", "w:rsid"):
        for e in moi.findall(qn(tag)):
            moi.remove(e)
    goc.append(moi)


def tao_kieu(d):
    st = d.styles
    kieu_san_co(d, "Heading2", "Heading3", "heading 3")
    kieu_san_co(d, "TOC2", "TOC3", "toc 3")
    kieu_san_co(d, "TOC2", "TOC4", "toc 4")

    def kieu_doan(ten, co, dam=False, nghieng=False, can=None, truoc=0, sau=6, gian=1.5, thut_dau=None,
                  thut_trai=None, phong=TNR, mau=None, dua_tren="Normal"):
        try:
            s = st[ten]
        except KeyError:
            s = st.add_style(ten, WD_STYLE_TYPE.PARAGRAPH)
        if dua_tren:
            s.base_style = st[dua_tren]
        s.font.name, s.font.size, s.font.bold, s.font.italic = phong, Pt(co), dam, nghieng
        s.font.color.rgb = RGBColor(0, 0, 0) if mau is None else mau
        font_ca_4(s.element, phong)
        pf = s.paragraph_format
        if can is not None:
            pf.alignment = can
        pf.space_before, pf.space_after, pf.line_spacing = Pt(truoc), Pt(sau), gian
        if thut_dau is not None:
            pf.first_line_indent = Cm(thut_dau)
        if thut_trai is not None:
            pf.left_indent = Cm(thut_trai)
        pf.widow_control = True
        return s

    for ten, cap, co, can, truoc, sau in (("Heading 1", 0, 16, WD_ALIGN_PARAGRAPH.CENTER, 0, 18),
                                          ("Heading 2", 1, 14, WD_ALIGN_PARAGRAPH.LEFT, 12, 6),
                                          ("Heading 3", 2, 13, WD_ALIGN_PARAGRAPH.LEFT, 8, 4)):
        s = kieu_doan(ten, co, dam=True, can=can, truoc=truoc, sau=sau, gian=1.3, thut_dau=0, thut_trai=0)
        s.paragraph_format.keep_with_next = True
        s.paragraph_format.page_break_before = (cap == 0)
        pPr = s.element.get_or_add_pPr()
        for e in pPr.findall(qn("w:outlineLvl")):
            pPr.remove(e)
        o = OxmlElement("w:outlineLvl")
        o.set(qn("w:val"), str(cap))
        pPr.append(o)
        # bỏ màu chủ đề / gạch chân / chữ nghiêng có sẵn của kiểu Heading trong file mẫu
        rpr = s.element.get_or_add_rPr()
        for tag in ("w:color", "w:u", "w:i", "w:iCs", "w:caps"):
            for e in rpr.findall(qn(tag)):
                rpr.remove(e)
        s.font.color.rgb = RGBColor(0, 0, 0)

    kieu_doan("NoiDung", 13, can=WD_ALIGN_PARAGRAPH.JUSTIFY, sau=6, gian=1.5, thut_dau=1.0)
    kieu_doan("DanhSachGach", 13, can=WD_ALIGN_PARAGRAPH.JUSTIFY, sau=3, gian=1.5, thut_dau=-0.5, thut_trai=1.0)
    kieu_doan("MaNguon", 10, can=WD_ALIGN_PARAGRAPH.LEFT, truoc=4, sau=10, gian=1.0, thut_dau=0, thut_trai=0.3,
              phong="Consolas")
    kieu_doan("ChuThichHinh", 12, nghieng=True, can=WD_ALIGN_PARAGRAPH.CENTER, truoc=4, sau=12, gian=1.15,
              thut_dau=0, thut_trai=0)
    kieu_doan("ChuThichBang", 12, nghieng=True, can=WD_ALIGN_PARAGRAPH.CENTER, truoc=10, sau=4, gian=1.15,
              thut_dau=0, thut_trai=0)
    st["ChuThichBang"].paragraph_format.keep_with_next = True
    kieu_doan("ChuBang", 12, can=WD_ALIGN_PARAGRAPH.LEFT, sau=0, gian=1.15, thut_dau=0, thut_trai=0)
    # căn trái: URL dài mà căn đều hai bên sẽ tạo khoảng trắng rất lớn giữa các chữ
    kieu_doan("TaiLieu", 13, can=WD_ALIGN_PARAGRAPH.LEFT, sau=6, gian=1.3, thut_dau=-0.9, thut_trai=0.9)
    kieu_doan("HinhAnh", 12, can=WD_ALIGN_PARAGRAPH.CENTER, truoc=6, sau=2, gian=1.0, thut_dau=0, thut_trai=0)
    st["HinhAnh"].paragraph_format.keep_with_next = True

    # nền xám cho khối mã nguồn
    pPr = st["MaNguon"].element.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), "F2F2F2")
    pPr.append(shd)

    # mục lục: phông Times, chấm dẫn tới số trang ở lề phải
    # toc 1-3: mục lục; toc 4: danh mục bảng / hình (không đậm, không thụt)
    for cap in (1, 2, 3, 4):
        s = kieu_doan(f"toc {cap}", 13, dam=(cap == 1), nghieng=(cap == 3), can=WD_ALIGN_PARAGRAPH.LEFT, sau=3,
                      gian=1.3, thut_dau=0, thut_trai=(cap - 1) * 0.6 if cap < 4 else 0)
        s.paragraph_format.tab_stops.add_tab_stop(Cm(RONG_CHU), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)


# ============================================================== chữ có đánh dấu
MAU_DANH_DAU = re.compile(r"\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`")


def viet(p, s, co=None, dam=False, nghieng=False):
    """Viết chuỗi có đánh dấu **đậm**, *nghiêng*, `mã` vào đoạn p."""
    vt = 0
    for m in MAU_DANH_DAU.finditer(s):
        if m.start() > vt:
            r = p.add_run(s[vt:m.start()])
            r.bold, r.italic = dam or None, nghieng or None
            if co:
                r.font.size = Pt(co)
        if m[1] is not None:
            r = p.add_run(m[1]); r.bold = True; r.italic = nghieng or None
        elif m[2] is not None:
            r = p.add_run(m[2]); r.italic = True; r.bold = dam or None
        else:
            r = p.add_run(m[3]); r.font.name = "Consolas"
            font_ca_4(r._r, "Consolas")
            r.font.size = Pt((co or 13) - 1.5)
        if co and m[3] is None:
            r.font.size = Pt(co)
        vt = m.end()
    if vt < len(s):
        r = p.add_run(s[vt:])
        r.bold, r.italic = dam or None, nghieng or None
        if co:
            r.font.size = Pt(co)


# ============================================================== phần đầu (bìa, danh mục)
def thay_doan(p, moi, bo_sang=True):
    """Ghi đè cả đoạn bằng chuỗi mới, giữ định dạng của run đầu tiên."""
    if not p.runs:
        p.add_run(moi)
        return
    p.runs[0].text = moi
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)
    if bo_sang:
        bo_to_sang(p.runs[0])


def dien_bia(d):
    for o in d.tables[0]._cells:
        for p in o.paragraphs:
            t = chuan(p.text)
            if t == chuan("TÊN HỌC PHẦN"):
                thay_doan(p, ND.TEN_HOC_PHAN)
            elif t == chuan("TÊN ĐỀ TÀI"):
                thay_doan(p, ND.TEN_DE_TAI)
            elif "mm/20yy" in t:
                thay_doan(p, p.text.replace("mm/20yy", "10/2026"))
        # tên đề tài dài hơn mẫu (3 dòng) → bỏ bớt 2 dòng trống phía trên dòng ngày tháng để bìa vẫn vừa 1 trang
        ds = o.paragraphs
        vt_ngay = next((i for i, p in enumerate(ds) if "10/2026" in p.text), None)
        if vt_ngay:
            trong = [p for p in ds[:vt_ngay] if not p.text.strip()][-2:]
            for p in trong:
                p._p.getparent().remove(p._p)
    # danh sách nhóm: điền tên người làm, các ô MSSV / lớp để trống cho nhóm tự điền
    hang = d.tables[1].rows[1]
    thay_doan(hang.cells[1].paragraphs[0], "Đàm Thanh Vũ")
    for i in (2, 3):
        thay_doan(hang.cells[i].paragraphs[0], "…", bo_sang=False)
    thay_doan(hang.cells[4].paragraphs[0], "")


def dien_viet_tat(d):
    bang = d.tables[3]
    mau_hang = copy.deepcopy(bang.rows[1]._tr)
    while len(bang.rows) > 1:
        bang._tbl.remove(bang.rows[-1]._tr)
    for viet_tat, day_du in ND.VIET_TAT:
        tr = copy.deepcopy(mau_hang)
        bang._tbl.append(tr)
        hang = bang.rows[-1]
        for j, (o, s) in enumerate(zip(hang.cells, (viet_tat, day_du))):
            p = o.paragraphs[0]
            for r in list(p.runs):
                r._r.getparent().remove(r._r)
            r = p.add_run(s)
            r.font.name, r.font.size = TNR, Pt(13)
            font_ca_4(r._r)
            r.bold = j == 0


def xoa_phan_mau(d):
    """Xóa mọi thứ sau tiêu đề MỤC LỤC (mục lục giả + nội dung mẫu), giữ sectPr cuối cùng."""
    body = d.element.body
    con = list(body.iterchildren())
    vt = next(i for i, e in enumerate(con)
              if e.tag == qn("w:p") and chuan(Paragraph(e, d).text) == chuan("MỤC LỤC"))
    for e in con[vt + 1:]:
        if e.tag != qn("w:sectPr"):
            body.remove(e)
    # đưa "Danh mục ký hiệu, chữ viết tắt" vào mục lục
    for p in d.paragraphs:
        if chuan(p.text) == chuan("DANH MỤC CÁC KÝ HIỆU, CHỮ VIẾT TẮT"):
            muc_dan_y(p, 0)


def tieu_de_trang(d, s, muc_luc=True):
    p = d.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(s)
    r.bold, r.font.size, r.font.name = True, Pt(14), TNR
    font_ca_4(r._r)
    if muc_luc:
        muc_dan_y(p, 0)
    return p


def phan_muc_luc(d):
    p = d.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p.add_run("Trang")
    r.italic, r.font.size, r.font.name = True, Pt(12), TNR
    them_truong(d.add_paragraph(), r'TOC \o "1-3" \h \z \u')
    p = d.add_paragraph()
    p.add_run().add_break(WD_BREAK.PAGE)
    tieu_de_trang(d, "DANH MỤC CÁC BẢNG, HÌNH VẼ, ĐỒ THỊ")
    for nhan, kieu in (("Danh mục bảng", "ChuThichBang"), ("Danh mục hình vẽ, đồ thị", "ChuThichHinh")):
        p = d.add_paragraph()
        r = p.add_run(nhan)
        r.bold, r.font.size, r.font.name = True, Pt(13), TNR
        p.paragraph_format.space_before = Pt(12)
        # mức 4 → Word dùng kiểu "toc 4" (không đậm) cho danh mục bảng / hình
        them_truong(d.add_paragraph(), f'TOC \\h \\z \\t "{kieu},4"')


# ============================================================== nội dung
def ve_bang(d, B, tieu_de, dau, dong, rong, can):
    p = d.add_paragraph(style="ChuThichBang")
    so, _, ten = B.giai_tham_chieu(tieu_de).partition(". ")
    r = p.add_run(so + ". ")
    r.bold = True
    viet(p, ten)
    bang = d.add_table(rows=1 + len(dong), cols=len(dau))
    bang.style = d.styles["Table Grid"]
    bang.alignment = WD_TABLE_ALIGNMENT.CENTER
    tong = sum(rong)
    rong = [w * min(1.0, RONG_CHU / tong) for w in rong]
    can = can or ["l"] * len(dau)
    for i, hang in enumerate(bang.rows):
        khong_tach_hang(hang)
        noi_dung = dau if i == 0 else dong[i - 1]
        for j, o in enumerate(hang.cells):
            o.width = Cm(rong[j])
            p = o.paragraphs[0]
            p.style = d.styles["ChuBang"]
            if i == 0:
                to_nen_o(o, "D9E2F3")
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                viet(p, noi_dung[j], dam=True)
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if can[j] == "c" else WD_ALIGN_PARAGRAPH.LEFT
                cac_dong = B.giai_tham_chieu(str(noi_dung[j])).split("\n")
                viet(p, cac_dong[0])
                for them in cac_dong[1:]:
                    p2 = o.add_paragraph(style="ChuBang")
                    p2.alignment = p.alignment
                    viet(p2, them)
    lap_lai_dau_bang(bang.rows[0])
    # lưới cột cho Word / LibreOffice
    grid = bang._tbl.tblGrid
    for gc, w in zip(grid.findall(qn("w:gridCol")), rong):
        gc.set(qn("w:w"), str(int(Cm(w).twips)))
    d.add_paragraph(style="ChuBang").paragraph_format.space_after = Pt(6)


def ve_hinh(d, B, tep, chu_thich, rong_cm):
    duong_dan = HINH / tep
    w, h = Image.open(duong_dan).size
    rong_cm = min(rong_cm, RONG_CHU)
    if rong_cm * h / w > CAO_HINH_TOI_DA:
        rong_cm = CAO_HINH_TOI_DA * w / h
    p = d.add_paragraph(style="HinhAnh")
    p.add_run().add_picture(str(duong_dan), width=Cm(rong_cm))
    p = d.add_paragraph(style="ChuThichHinh")
    so, _, ten = chu_thich.partition(". ")
    r = p.add_run(so + ". ")
    r.bold = True
    viet(p, ten, nghieng=True)


def ve_ma(d, ma):
    p = d.add_paragraph(style="MaNguon")
    p.paragraph_format.keep_together = True
    for i, dong in enumerate(ma.split("\n")):
        if i:
            p.add_run().add_break()
        r = p.add_run(dong)
        r.font.name = "Consolas"
        font_ca_4(r._r, "Consolas")


def viet_noi_dung(d, B):
    for k in B.khoi:
        loai = k[0]
        if loai == "h1":
            d.add_paragraph(k[1], style="Heading 1")
        elif loai == "h2":
            d.add_paragraph(k[1], style="Heading 2")
        elif loai == "h3":
            d.add_paragraph(k[1], style="Heading 3")
        elif loai == "p":
            viet(d.add_paragraph(style="NoiDung"), B.giai_tham_chieu(k[1]))
        elif loai == "ds":
            for muc in k[1]:
                p = d.add_paragraph(style="DanhSachGach")
                p.add_run("–  ")
                viet(p, B.giai_tham_chieu(muc))
        elif loai == "ma":
            ve_ma(d, k[1])
        elif loai == "hinh":
            ve_hinh(d, B, k[1], k[2], k[3])
        elif loai == "bang":
            ve_bang(d, B, *k[1:])
        elif loai == "tltk":
            for muc in k[1]:
                viet(d.add_paragraph(style="TaiLieu"), muc)
        elif loai == "ngat":
            d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def so_trang(sec):
    """Số trang ở giữa chân trang, bắt đầu từ 1."""
    sec.footer.is_linked_to_previous = False
    p = sec.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    them_truong(p, "PAGE", "1")
    for r in p.runs:
        r.font.name, r.font.size = TNR, Pt(12)
    sectPr = sec._sectPr
    pg = OxmlElement("w:pgNumType")
    pg.set(qn("w:start"), "1")
    cols = sectPr.find(qn("w:cols"))
    if cols is not None:
        cols.addprevious(pg)
    else:
        pgMar = sectPr.find(qn("w:pgMar"))
        pgMar.addnext(pg)


def main():
    B = ND.tao()
    d = Document(MAU)
    tao_kieu(d)
    dien_bia(d)
    dien_viet_tat(d)
    xoa_phan_mau(d)
    phan_muc_luc(d)
    # phần nội dung là một section riêng để đánh số trang từ 1
    sec = d.add_section(WD_SECTION.NEW_PAGE)
    so_trang(sec)
    # phần đầu (bìa, danh mục, mục lục) đánh số La Mã để mục lục không lẫn với số trang nội dung
    sp = d.sections[0]._sectPr
    pg = OxmlElement("w:pgNumType")
    pg.set(qn("w:fmt"), "lowerRoman")
    cols = sp.find(qn("w:cols"))
    (cols.addprevious if cols is not None else sp.find(qn("w:pgMar")).addnext)(pg)
    viet_noi_dung(d, B)
    # đoạn đầu tiên của section mới là "MỞ ĐẦU" (Heading 1 có ngắt trang): bỏ ngắt trang thừa
    d.core_properties.title = "Báo cáo tiểu luận – " + ND.TEN_DE_TAI.title()
    d.core_properties.author = "Đàm Thanh Vũ"
    d.core_properties.subject = ND.TEN_HOC_PHAN
    d.save(RA)
    print("Đã tạo", RA, f"({len(B.so_hinh)} hình, {len(B.so_bang)} bảng)")


if __name__ == "__main__":
    main()
