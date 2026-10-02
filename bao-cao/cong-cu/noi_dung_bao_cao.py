"""Nội dung báo cáo tiểu luận – viết dưới dạng các khối (tiêu đề, đoạn văn, hình, bảng, mã nguồn).

Đánh dấu trong đoạn văn: **đậm**, *nghiêng*, `mã`.
Tham chiếu chéo: {H:khoa} -> "Hình 3.2", {B:khoa} -> "Bảng 2.1" (đánh số tự động theo chương).
Số liệu thực nghiệm lấy từ bao-cao/du-lieu/*.json – chính là kết quả của lần chạy đã chụp ảnh.
"""
import json
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
DL = GOC / "du-lieu"

TEN_HOC_PHAN = "HỆ QUẢN TRỊ CƠ SỞ DỮ LIỆU"
TEN_DE_TAI = ("ĐIỀU KHIỂN TRUY XUẤT ĐỒNG THỜI TRONG MYSQL/INNODB VÀ XÂY DỰNG ỨNG DỤNG MINH HỌA "
              "ĐẶT VÉ MÁY BAY")
REPO = "https://github.com/thanhvuaws-jpg/hequantricosodemodongthoi"


def doc(ten):
    return json.loads((DL / ten).read_text(encoding="utf-8"))


def so(x, chu_so=0):
    """Định dạng số kiểu Việt Nam: 1.234,5"""
    s = f"{x:,.{chu_so}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


class BaoCao:
    def __init__(self):
        self.khoi = []
        self.chuong = 0
        self.dem_hinh = 0
        self.dem_bang = 0
        self.so_hinh = {}
        self.so_bang = {}

    # ---------------------------------------------------------------- tiêu đề
    def h1(self, tieu_de, chuong=None):
        if chuong is not None:
            self.chuong, self.dem_hinh, self.dem_bang = chuong, 0, 0
        self.khoi.append(("h1", tieu_de))

    def h2(self, t):
        self.khoi.append(("h2", t))

    def h3(self, t):
        self.khoi.append(("h3", t))

    # ---------------------------------------------------------------- nội dung
    def p(self, *doan):
        for d in doan:
            self.khoi.append(("p", d))

    def ds(self, *muc):
        self.khoi.append(("ds", list(muc)))

    def ma(self, ma_nguon, ngon_ngu="sql"):
        self.khoi.append(("ma", ma_nguon.strip("\n")))

    def hinh(self, khoa, tep, ten, rong_cm=16.0):
        self.dem_hinh += 1
        so_ = f"{self.chuong}.{self.dem_hinh}"
        self.so_hinh[khoa] = so_
        self.khoi.append(("hinh", tep, f"Hình {so_}. {ten}", rong_cm))

    def bang(self, khoa, ten, dau, dong, rong_cm, can=None):
        self.dem_bang += 1
        so_ = f"{self.chuong}.{self.dem_bang}"
        self.so_bang[khoa] = so_
        self.khoi.append(("bang", f"Bảng {so_}. {ten}", dau, dong, rong_cm, can))

    def ngat(self):
        self.khoi.append(("ngat",))

    # ---------------------------------------------------------------- tham chiếu
    def giai_tham_chieu(self, s):
        import re

        def thay(m):
            loai, k = m[1], m[2]
            if loai == "H":
                return f"Hình {self.so_hinh[k]}"
            return f"Bảng {self.so_bang[k]}"
        return re.sub(r"\{([HB]):([a-z0-9_]+)\}", thay, s)


TEN_CACH = {"khong_khoa": "Không dùng khóa", "bi_quan": "Khóa bi quan", "lac_quan": "Khóa lạc quan",
            "nguyen_tu": "UPDATE nguyên tử", "deadlock": "Kịch bản deadlock"}

VIET_TAT = [
    ("2PL", "Two-Phase Locking – giao thức khóa hai pha"),
    ("ACID", "Atomicity, Consistency, Isolation, Durability – tính nguyên tố, nhất quán, cô lập, bền vững"),
    ("API", "Application Programming Interface – giao diện lập trình ứng dụng"),
    ("CSDL", "Cơ sở dữ liệu"),
    ("FK", "Foreign Key – khóa ngoại"),
    ("HQTCSDL", "Hệ quản trị cơ sở dữ liệu (Database Management System – DBMS)"),
    ("IS / IX", "Intention Shared / Intention Exclusive lock – khóa ý định đọc / khóa ý định ghi"),
    ("MVCC", "Multi-Version Concurrency Control – điều khiển đồng thời đa phiên bản"),
    ("PK", "Primary Key – khóa chính"),
    ("RU / RC / RR", "READ UNCOMMITTED / READ COMMITTED / REPEATABLE READ – các mức cô lập"),
    ("S / X", "Shared / Exclusive lock – khóa chia sẻ (khóa đọc) / khóa độc quyền (khóa ghi)"),
    ("SQL", "Structured Query Language – ngôn ngữ truy vấn có cấu trúc"),
    ("UI", "User Interface – giao diện người dùng"),
    ("WAL", "Write-Ahead Logging – ghi nhật ký trước khi ghi dữ liệu"),
]


def tao():
    B = BaoCao()
    tt = doc("thong_tin.json")["may_chu"]
    ss = doc("ss.json")
    ks = doc("ks.json")
    mt = doc("cl_ma_tran.json")
    dv = {m: doc(f"dv_{m}.json")["tom_tat"] for m in ("khong_khoa", "bi_quan", "lac_quan", "nguyen_tu", "deadlock")}
    xd = {(m, l): doc(f"xd_{m}_{l}.json")
          for m in ("mat_cap_nhat", "doc_rac", "doc_khong_lap_lai", "bong_ma", "deadlock") for l in ("sai", "dung")}
    phien_ban = tt["phien_ban"]

    # ==================================================================== MỞ ĐẦU
    B.h1("MỞ ĐẦU")
    B.p(
        "Trong các hệ thống thông tin hiện đại, cơ sở dữ liệu hiếm khi chỉ phục vụ một người dùng tại một thời "
        "điểm. Một hệ thống đặt vé máy bay trực tuyến có thể nhận hàng trăm yêu cầu giữ chỗ trong cùng một giây "
        "cho cùng một chuyến bay; một sàn thương mại điện tử trong đợt khuyến mãi có hàng nghìn khách cùng bấm "
        "“Mua ngay” cho một số lượng hàng có hạn. Khi nhiều giao tác cùng đọc và ghi lên cùng một dữ liệu, nếu "
        "hệ quản trị cơ sở dữ liệu không điều phối tốt thì dữ liệu sẽ sai lệch: vé bị bán vượt số ghế, số dư bị "
        "trừ sai, báo cáo đọc phải số liệu chưa từng tồn tại chính thức.",
        "**Điều khiển truy xuất đồng thời** (concurrency control) là thành phần của hệ quản trị cơ sở dữ liệu "
        "có nhiệm vụ cho phép nhiều giao tác chạy xen kẽ để tận dụng tài nguyên, nhưng vẫn bảo đảm kết quả như "
        "thể chúng chạy lần lượt. Đây là một trong những nội dung trọng tâm của học phần Hệ quản trị cơ sở dữ "
        "liệu, gắn liền với các khái niệm giao tác, lịch giao tác, khóa, đa phiên bản và mức cô lập.",
        f"Tiểu luận này nghiên cứu cơ chế điều khiển truy xuất đồng thời của **MySQL {phien_ban}** với storage "
        "engine **InnoDB** – hệ quản trị cơ sở dữ liệu mã nguồn mở được dùng rất rộng rãi. Bên cạnh phần lý "
        "thuyết, nhóm xây dựng một **ứng dụng minh họa** theo nghiệp vụ đặt vé máy bay, trong đó mọi kịch bản "
        "đều được chạy thật trên MySQL: năm xung đột kinh điển (mất cập nhật, đọc dữ liệu rác, đọc không lặp "
        "lại, bóng ma, khóa chết) được tái hiện dưới dạng lịch giao tác có hoạt hình, kèm kịch bản sai và kịch "
        "bản đúng chỉ khác nhau đúng một điểm; nhiều khách hàng đặt vé đồng thời với bốn cách xử lý tranh chấp; "
        "ma trận sáu hiện tượng trên bốn mức cô lập được đối chiếu với lý thuyết chuẩn SQL. Ứng dụng đọc trực "
        "tiếp bảng khóa của InnoDB, nhờ đó người xem thấy được tận mắt khóa dòng, khóa khoảng trống và vòng chờ "
        "gây ra khóa chết.",
        "Kết quả thực nghiệm cho thấy một số điểm MySQL/InnoDB khác với lý thuyết chuẩn SQL – chẳng hạn mức "
        "REPEATABLE READ của MySQL chặn được hiện tượng bóng ma nhưng lại không chặn được mất cập nhật. Những "
        "phát hiện này được trình bày, giải thích và kiểm chứng bằng số liệu trong các chương sau.",
    )

    # ==================================================================== CHƯƠNG 1
    B.h1("CHƯƠNG 1. GIỚI THIỆU", chuong=1)
    B.h2("1.1. Lý do chọn đề tài")
    B.p(
        "Các ứng dụng trực tuyến ngày nay đều là hệ thống nhiều người dùng. Ở những nghiệp vụ có tài nguyên hữu "
        "hạn như bán vé, giữ chỗ, quản lý tồn kho hay chuyển tiền, nhiều yêu cầu thường tranh nhau cùng một dòng "
        "dữ liệu trong những khoảnh khắc rất ngắn. Một lỗi điều khiển đồng thời không gây ra thông báo lỗi nào, "
        "ứng dụng vẫn chạy bình thường, nhưng dữ liệu đã sai: hai khách cùng nhận được một ghế, hoặc số ghế còn "
        "lại không khớp với số vé đã bán. Những lỗi như vậy rất khó phát hiện khi kiểm thử bằng tay vì chúng chỉ "
        "xuất hiện với một thứ tự xen kẽ nhất định của các câu lệnh.",
        "Trong khi đó, nhiều lập trình viên sử dụng hệ quản trị cơ sở dữ liệu với giả định rằng “đã có giao "
        "tác thì dữ liệu sẽ đúng”, hoặc hiểu các mức cô lập theo bảng lý thuyết của chuẩn SQL mà không biết mỗi "
        "hệ quản trị cài đặt chúng theo cách riêng. Với MySQL/InnoDB, mức mặc định REPEATABLE READ không ngăn "
        "được mất cập nhật – điều trái với trực giác của nhiều người. Ở phía học tập, lịch giao tác thường chỉ "
        "được vẽ trên bảng, người học khó hình dung khi nào một giao tác bị chặn, khóa nào đang được giữ, và vì "
        "sao hệ quản trị lại chọn hủy một giao tác khi xảy ra khóa chết.",
        "Từ thực tế đó, nhóm chọn đề tài **điều khiển truy xuất đồng thời trong MySQL/InnoDB** kết hợp xây dựng "
        "một ứng dụng minh họa. Nếu giải quyết được, đề tài vừa giúp người học hiểu sâu lý thuyết giao tác thông "
        "qua quan sát hành vi thật của một hệ quản trị phổ biến, vừa giúp người phát triển ứng dụng lựa chọn "
        "đúng kỹ thuật (khóa bi quan, khóa lạc quan, câu lệnh nguyên tử, mức cô lập phù hợp) khi xây dựng các "
        "chức năng có tranh chấp dữ liệu. Cách tiếp cận này cũng áp dụng được cho các nghiệp vụ tương tự như "
        "bán hàng khuyến mãi, ngân hàng hay quản lý kho.",
    )
    B.h2("1.2. Mục tiêu đề tài")
    B.p(
        "Hệ thống được xây dựng là một **ứng dụng web minh họa** dành cho sinh viên và giảng viên học phần Hệ "
        "quản trị cơ sở dữ liệu. Ứng dụng giúp người dùng quan sát trực quan các xung đột khi nhiều giao tác "
        "truy xuất đồng thời và cách InnoDB xử lý chúng, với dữ liệu, câu lệnh, kết quả và bảng khóa đều lấy "
        "trực tiếp từ MySQL chứ không mô phỏng.",
        "Kết quả cần đạt được gồm:",
    )
    B.ds(
        "Về lý thuyết: hệ thống hóa các khái niệm giao tác, tính chất ACID, lịch giao tác và tính khả tuần tự; "
        "các hiện tượng bất thường khi truy xuất đồng thời; kỹ thuật khóa, giao thức khóa hai pha, điều khiển đa "
        "phiên bản (MVCC); các mức cô lập theo chuẩn SQL và cách InnoDB cài đặt chúng.",
        "Về ứng dụng: tái hiện được 5 xung đột (mất cập nhật, đọc dữ liệu rác, đọc không lặp lại, bóng ma, khóa "
        "chết), mỗi xung đột có một kịch bản SAI và một kịch bản ĐÚNG chạy trên cùng dữ liệu, cùng thứ tự xen "
        "kẽ; hiển thị lịch giao tác dạng hoạt hình, dữ liệu đã commit / chưa commit và bảng khóa tại từng bước.",
        "Về thực nghiệm: mô phỏng nhiều khách đặt vé đồng thời với 4 cách xử lý (không khóa, khóa bi quan, khóa "
        "lạc quan, UPDATE nguyên tử), đo thời gian, số vé bán vượt, số lần chờ khóa, số lần thử lại; lập ma "
        "trận 6 hiện tượng × 4 mức cô lập và đối chiếu với lý thuyết chuẩn SQL.",
        "Về công nghệ: đóng gói toàn bộ bằng Docker (MySQL và ứng dụng) để chạy được bằng một cú nhấp; xây dựng "
        "bộ kiểm thử tự động chạy trên MySQL thật để bảo đảm các kịch bản luôn tái hiện đúng.",
    )
    B.h2("1.3. Phạm vi đề tài")
    B.p(
        f"Đề tài giới hạn ở hệ quản trị **MySQL {phien_ban}** với storage engine **InnoDB**, chạy trên một máy "
        "chủ đơn (không xét nhân bản, phân cụm hay giao tác phân tán). Nghiệp vụ minh họa là một hệ thống đặt vé "
        "máy bay đã được giản lược còn ba bảng (chuyến bay, vé, ghế), đủ để tạo ra mọi loại tranh chấp cần "
        "nghiên cứu. Về mức cô lập, đề tài khảo sát đủ bốn mức của chuẩn SQL: READ UNCOMMITTED, READ COMMITTED, "
        "REPEATABLE READ và SERIALIZABLE.",
        "Ứng dụng minh họa phục vụ mục đích học tập và thực nghiệm, chạy cục bộ trên máy cá nhân thông qua "
        "Docker; đề tài không hướng tới xây dựng một hệ thống đặt vé hoàn chỉnh (thanh toán, tài khoản người "
        "dùng, phân quyền…). Thời gian thực hiện là một học kỳ của học phần Hệ quản trị cơ sở dữ liệu.",
    )
    B.h2("1.4. Đối tượng nghiên cứu")
    B.p(
        "Đối tượng nghiên cứu chính của đề tài là **cơ chế điều khiển truy xuất đồng thời của InnoDB**, bao gồm: "
        "mô hình giao tác và các mức cô lập; hệ thống khóa (khóa dòng, khóa khoảng trống, next-key lock, khóa ý "
        "định, khóa ý định chèn); cơ chế đa phiên bản dựa trên undo log; cơ chế phát hiện và xử lý khóa chết. "
        "Bên cạnh đó, đề tài nghiên cứu các **kỹ thuật phía ứng dụng** để xử lý tranh chấp: khóa bi quan với "
        "SELECT … FOR UPDATE, khóa lạc quan với cột phiên bản, câu lệnh UPDATE nguyên tử có điều kiện, và quy "
        "ước thứ tự khóa để phòng tránh khóa chết.",
    )
    B.h2("1.5. Phương pháp nghiên cứu")
    B.p(
        "**Phương pháp thu thập thông tin:** đọc và tổng hợp giáo trình cơ sở dữ liệu [1], [2], các công trình "
        "kinh điển về xử lý giao tác [3], [6], [7], tài liệu chính thức của MySQL về mô hình khóa và giao tác "
        "của InnoDB [4], [8]–[11].",
        "**Phương pháp xử lý thông tin:** phân tích định tính các lịch giao tác (viết bằng ký hiệu r, w, c, a) "
        "để giải thích vì sao một xung đột xảy ra hay không; phân tích định lượng các số đo thu được khi chạy "
        "thực nghiệm như thời gian xử lý, số vé bán vượt, số lần chờ khóa, số lần thử lại.",
        "**Phương pháp thực nghiệm:** xây dựng ứng dụng điều phối nhiều phiên làm việc trên MySQL thật, chạy các "
        "kịch bản với thứ tự xen kẽ được kiểm soát, ghi nhận kết quả từng câu lệnh và chụp bảng khóa từ "
        "performance_schema sau mỗi bước; so sánh kết quả đo được với lý thuyết. Toàn bộ kịch bản được kiểm "
        "chứng lặp lại bằng bộ kiểm thử tự động gồm 151 trường hợp.",
    )
    B.h2("1.6. Bố cục đề tài")
    B.p(
        "Phần còn lại của báo cáo tiểu luận được tổ chức như sau.",
        "Chương 2 trình bày cơ sở lý thuyết của đề tài. Chương này bắt đầu từ khái niệm giao tác, các tính chất "
        "ACID và lịch giao tác, sau đó phân tích năm hiện tượng bất thường có thể xảy ra khi nhiều giao tác truy "
        "xuất đồng thời. Tiếp theo, chương trình bày các kỹ thuật điều khiển đồng thời gồm kỹ thuật khóa, giao "
        "thức khóa hai pha, điều khiển đa phiên bản và các cách xử lý khóa chết, cùng với bốn mức cô lập của "
        "chuẩn SQL. Phần cuối chương đi sâu vào MySQL và InnoDB: kiến trúc, các loại khóa, cơ chế đa phiên bản, "
        "phát hiện khóa chết và cách giám sát khóa qua performance_schema, rồi giới thiệu các công nghệ dùng để "
        "xây dựng ứng dụng minh họa.",
        "Chương 3 trình bày đóng góp chính của đề tài là ứng dụng minh họa điều khiển truy xuất đồng thời. Phần "
        "phân tích hệ thống xác định yêu cầu, kiến trúc, lược đồ cơ sở dữ liệu, thiết kế năm cặp kịch bản xung "
        "đột và bộ điều phối cho phép hai phiên chạy xen kẽ ngay cả khi một phiên bị chặn vì chờ khóa. Phần xây "
        "dựng sản phẩm mô tả từng chức năng qua giao diện thực tế, đồng thời phân tích kết quả mà MySQL trả về "
        "trong từng kịch bản. Chương kết thúc bằng phần kiểm thử, đánh giá và tổng hợp những điểm MySQL/InnoDB "
        "khác với lý thuyết.",
        "Phần Kết luận tổng kết những gì đề tài đã làm được so với mục tiêu, các bài học rút ra và hướng phát "
        "triển tiếp theo. Phụ lục cung cấp hướng dẫn cài đặt, lược đồ cơ sở dữ liệu và cấu trúc mã nguồn.",
    )

    # ==================================================================== CHƯƠNG 2
    B.h1("CHƯƠNG 2. CƠ SỞ LÝ THUYẾT", chuong=2)
    B.p(
        "Để giải thích được vì sao một kịch bản gây ra xung đột và vì sao một thay đổi nhỏ lại ngăn được xung "
        "đột đó, đề tài cần dựa trên lý thuyết xử lý giao tác. Chương này trình bày các khái niệm nền tảng theo "
        "trình tự: giao tác và lịch giao tác (để mô tả chính xác điều gì xảy ra), các hiện tượng bất thường (để "
        "biết cần ngăn chặn điều gì), các kỹ thuật điều khiển đồng thời và mức cô lập (để biết hệ quản trị ngăn "
        "chặn bằng cách nào), và cuối cùng là cách MySQL/InnoDB cài đặt các kỹ thuật đó – vì đây chính là hệ "
        "quản trị mà ứng dụng minh họa sử dụng."
    )
    B.h2("2.1. Giao tác và lịch giao tác")
    B.h3("2.1.1. Khái niệm giao tác")
    B.p(
        "**Giao tác** (transaction) là một đơn vị xử lý logic gồm một dãy thao tác đọc/ghi trên cơ sở dữ liệu, "
        "được hệ quản trị xem như một khối không thể chia cắt: hoặc tất cả các thao tác đều có hiệu lực, hoặc "
        "không thao tác nào có hiệu lực [1]. Một giao tác bắt đầu bằng lệnh `START TRANSACTION` (hoặc `BEGIN`) và "
        "kết thúc bằng `COMMIT` (ghi nhận vĩnh viễn) hoặc `ROLLBACK` (hủy bỏ toàn bộ). Ví dụ, nghiệp vụ bán một "
        "vé máy bay gồm hai thao tác phải đi cùng nhau: giảm số ghế trống của chuyến bay và thêm một dòng vé mới."
    )
    B.ma("""
START TRANSACTION;
UPDATE chuyen_bay SET so_ghe_trong = so_ghe_trong - 1
 WHERE ma_chuyen = 1 AND so_ghe_trong > 0;
INSERT INTO ve (ma_chuyen, hanh_khach) VALUES (1, 'Nguyễn An');
COMMIT;
""")
    B.p("Nếu hệ thống gặp sự cố giữa hai câu lệnh, giao tác bị hủy và số ghế trống được khôi phục, không có "
        "trạng thái “đã trừ ghế nhưng chưa có vé”.")
    B.h3("2.1.2. Các tính chất ACID")
    B.p("Một hệ quản trị cơ sở dữ liệu hỗ trợ giao tác phải bảo đảm bốn tính chất, thường gọi tắt là ACID "
        "({B:acid}). Đề tài tập trung vào tính **cô lập** – tính chất do bộ điều khiển truy xuất đồng thời "
        "chịu trách nhiệm.")
    B.bang("acid", "Bốn tính chất ACID của giao tác", ["Tính chất", "Ý nghĩa", "Cơ chế tương ứng trong InnoDB"], [
        ["Atomicity – tính nguyên tố", "Tất cả thao tác của giao tác cùng có hiệu lực hoặc cùng bị hủy.",
         "Undo log: hoàn tác các thay đổi khi ROLLBACK hoặc khi giao tác bị hủy."],
        ["Consistency – tính nhất quán", "Giao tác đưa CSDL từ một trạng thái hợp lệ sang một trạng thái hợp lệ.",
         "Ràng buộc khóa chính, khóa ngoại, CHECK; logic nghiệp vụ trong giao tác."],
        ["Isolation – tính cô lập", "Các giao tác chạy đồng thời không thấy trạng thái dở dang của nhau.",
         "Hệ thống khóa và MVCC, điều chỉnh bằng mức cô lập."],
        ["Durability – tính bền vững", "Thay đổi đã COMMIT không bị mất kể cả khi hệ thống gặp sự cố.",
         "Redo log ghi trước (WAL), doublewrite buffer."],
    ], [3.6, 6.4, 6.5])
    B.h3("2.1.3. Các trạng thái của giao tác")
    B.p("Trong suốt vòng đời, một giao tác đi qua các trạng thái được mô tả ở {H:trang_thai}. Giao tác ở trạng "
        "thái **hoạt động** khi đang thực hiện các thao tác; sau thao tác cuối cùng nó chuyển sang **ủy thác một "
        "phần**; khi thông tin cần thiết đã được ghi an toàn vào nhật ký, giao tác **đã ủy thác**. Nếu có lỗi "
        "hoặc bị hệ quản trị hủy (chẳng hạn để phá khóa chết), giao tác chuyển sang **thất bại** rồi **đã hủy "
        "bỏ** sau khi mọi thay đổi được hoàn tác.")
    B.hinh("trang_thai", "so_do_trang_thai_giao_tac.png", "Sơ đồ trạng thái của một giao tác", 14.5)
    B.h3("2.1.4. Lịch giao tác và tính khả tuần tự")
    B.p(
        "Khi nhiều giao tác chạy đồng thời, các thao tác của chúng được hệ quản trị thực hiện theo một thứ tự "
        "đan xen nào đó gọi là **lịch giao tác** (schedule). Để viết lịch ngắn gọn, giáo trình dùng ký hiệu: "
        "`r₁(X)` – giao tác T₁ đọc đơn vị dữ liệu X; `w₁(X)` – T₁ ghi X; `c₁` – T₁ commit; `a₁` – T₁ hủy bỏ. "
        "Ứng dụng minh họa dùng thêm ký hiệu `xl₁(X)` để chỉ việc T₁ xin khóa ghi trên X.",
        "Một lịch là **tuần tự** nếu các giao tác chạy lần lượt, không đan xen; lịch tuần tự luôn cho kết quả "
        "đúng nhưng không tận dụng được tính đồng thời. Một lịch đan xen được gọi là **khả tuần tự** "
        "(serializable) nếu kết quả của nó tương đương với một lịch tuần tự nào đó. Hai thao tác của hai giao tác "
        "khác nhau **xung đột** nếu cùng truy cập một đơn vị dữ liệu và ít nhất một thao tác là ghi; lịch là "
        "**khả tuần tự xung đột** nếu có thể hoán đổi các thao tác không xung đột để biến nó thành một lịch tuần "
        "tự [1], [7]. Mục tiêu của bộ điều khiển đồng thời là chỉ cho phép các lịch khả tuần tự (hoặc các lịch "
        "đủ an toàn theo mức cô lập đã chọn).",
        "{B:lich_mat} là một lịch đan xen không khả tuần tự kinh điển: cả hai giao tác bán vé đều đọc số ghế "
        "trống X = 7 rồi cùng ghi 6. Kết quả 6 không tương đương với bất kỳ lịch tuần tự nào (T₁ rồi T₂ hay T₂ "
        "rồi T₁ đều cho 5).",
    )
    B.bang("lich_mat", "Lịch giao tác gây mất cập nhật: r₁(X) r₂(X) w₁(X) c₁ w₂(X) c₂",
           ["Thời điểm", "T₁ (quầy vé A)", "T₂ (ứng dụng di động B)", "Giá trị X trong CSDL"], [
               ["t1", "r₁(X) → đọc được 7", "", "7"],
               ["t2", "", "r₂(X) → đọc được 7", "7"],
               ["t3", "w₁(X) ← ghi 7 − 1 = 6", "", "6 (chưa commit)"],
               ["t4", "c₁", "", "6"],
               ["t5", "", "w₂(X) ← ghi 7 − 1 = 6", "6 (chưa commit)"],
               ["t6", "", "c₂", "6 – lẽ ra phải là 5"],
           ], [2.3, 4.6, 4.8, 4.8], can=["c", "l", "l", "l"])
    B.h2("2.2. Các vấn đề khi truy xuất đồng thời")
    B.p("Nếu không có cơ chế điều khiển, các lịch đan xen có thể gây ra những hiện tượng bất thường sau. Mỗi "
        "hiện tượng được minh họa bằng nghiệp vụ đặt vé, với X là số ghế trống của chuyến VN-808.")
    B.h3("2.2.1. Mất cập nhật (Lost update)")
    B.p("Hai giao tác cùng đọc một giá trị, cùng tự tính giá trị mới dựa trên giá trị đã đọc, rồi lần lượt ghi "
        "đè. Thay đổi của giao tác ghi trước bị giao tác ghi sau xóa mất ({B:lich_mat}). Hậu quả trong nghiệp "
        "vụ: bán hai vé nhưng số ghế trống chỉ giảm một, dẫn tới **bán vượt** số ghế. Chuẩn SQL-92 không định "
        "nghĩa hiện tượng này một cách hình thức; Berenson và cộng sự gọi nó là P4 và chỉ ra rằng mức REPEATABLE "
        "READ cài đặt bằng khóa sẽ ngăn được nó [3].")
    B.h3("2.2.2. Đọc dữ liệu rác (Dirty read)")
    B.p("Giao tác T₁ đọc giá trị mà T₂ đã ghi nhưng **chưa commit**; sau đó T₂ hủy bỏ. T₁ đã dựa vào một dữ "
        "liệu chưa từng tồn tại chính thức. Lịch: `w₂(X) r₁(X) a₂`. Ví dụ: hệ thống đang giữ chỗ tạm thời đặt số "
        "ghế trống về 0, giao tác khác đọc thấy “hết vé” và từ chối khách, nhưng sau đó việc giữ chỗ bị hủy.")
    B.h3("2.2.3. Đọc không lặp lại (Non-repeatable read)")
    B.p("Trong cùng một giao tác, T₁ đọc một dòng hai lần nhưng nhận hai giá trị khác nhau vì giữa hai lần đọc, "
        "T₂ đã sửa và commit dòng đó. Lịch: `r₁(X) w₂(X) c₂ r₁(X)`. Hiện tượng này làm các phép tính dựa trên "
        "nhiều lần đọc (chẳng hạn lập báo cáo) trở nên mâu thuẫn.")
    B.h3("2.2.4. Bóng ma (Phantom read)")
    B.p("T₁ đọc một **tập các dòng** thỏa một điều kiện (một vị từ, ký hiệu P), chẳng hạn “mọi vé của chuyến "
        "VN-808”. Trong lúc T₁ chưa kết thúc, T₂ **chèn thêm** một dòng thỏa điều kiện đó và commit. Lần đọc sau, "
        "T₁ thấy xuất hiện thêm một dòng “bóng ma”. Khác với đọc không lặp lại (dòng cũ bị sửa), bóng ma liên quan "
        "tới dòng **mới**, nên không thể ngăn chỉ bằng cách khóa các dòng đang tồn tại.")
    B.h3("2.2.5. Khóa chết (Deadlock)")
    B.p("Khóa chết xảy ra khi các giao tác chờ nhau thành một vòng tròn: T₁ giữ tài nguyên X và chờ Y, trong "
        "khi T₂ giữ Y và chờ X. Không giao tác nào tự tiến lên được ({H:do_thi_cho}). Khóa chết không làm sai dữ "
        "liệu nhưng làm hệ thống treo nếu không được phát hiện; hệ quản trị phải chọn hủy một giao tác (gọi là "
        "nạn nhân) để phá vòng chờ, và ứng dụng phía nạn nhân phải chạy lại giao tác.")
    B.hinh("do_thi_cho", "so_do_do_thi_cho.png", "Đồ thị chờ của hai giao tác bị khóa chết", 13.5)
    B.h2("2.3. Các kỹ thuật điều khiển truy xuất đồng thời")
    B.h3("2.3.1. Kỹ thuật khóa")
    B.p(
        "Kỹ thuật khóa (locking) gắn với mỗi đơn vị dữ liệu một khóa mà giao tác phải xin trước khi truy cập. Có "
        "hai loại khóa cơ bản: **khóa chia sẻ (S)** cho phép đọc – nhiều giao tác có thể cùng giữ; **khóa độc "
        "quyền (X)** cho phép ghi – chỉ một giao tác được giữ và loại trừ mọi khóa khác. Để kết hợp khóa ở nhiều "
        "mức (bảng và dòng) mà không phải duyệt từng dòng, các hệ quản trị dùng thêm **khóa ý định** IS và IX đặt "
        "ở mức bảng trước khi khóa dòng bên trong [4]. Ma trận tương thích của các khóa mức bảng trong InnoDB được "
        "cho ở {B:tuong_thich}: một yêu cầu khóa chỉ được cấp nếu tương thích với mọi khóa mà giao tác khác đang "
        "giữ, nếu không giao tác phải chờ.",
    )
    B.bang("tuong_thich", "Ma trận tương thích khóa mức bảng của InnoDB", ["Yêu cầu \\ Đang giữ", "X", "IX", "S", "IS"], [
        ["X", "Xung đột", "Xung đột", "Xung đột", "Xung đột"],
        ["IX", "Xung đột", "Tương thích", "Xung đột", "Tương thích"],
        ["S", "Xung đột", "Xung đột", "Tương thích", "Tương thích"],
        ["IS", "Xung đột", "Tương thích", "Tương thích", "Tương thích"],
    ], [3.9, 3.15, 3.15, 3.15, 3.15], can=["c", "c", "c", "c", "c"])
    B.h3("2.3.2. Giao thức khóa hai pha (2PL)")
    B.p(
        "Chỉ khóa thôi chưa đủ để bảo đảm khả tuần tự – còn phụ thuộc vào thời điểm nhả khóa. **Giao thức khóa "
        "hai pha** chia giao tác thành pha tăng trưởng (chỉ xin khóa) và pha thu hẹp (chỉ nhả khóa); một khi đã "
        "nhả một khóa thì không được xin thêm khóa nào. Mọi lịch tuân theo 2PL đều khả tuần tự xung đột [7]. Biến "
        "thể **2PL nghiêm ngặt** (strict 2PL) giữ mọi khóa ghi cho tới khi commit hoặc rollback, nhờ đó tránh được "
        "hủy dây chuyền; InnoDB áp dụng cách này – khóa dòng chỉ được nhả khi giao tác kết thúc. Nhược điểm của "
        "2PL là giảm tính đồng thời và có thể gây khóa chết.",
    )
    B.h3("2.3.3. Điều khiển đồng thời đa phiên bản (MVCC)")
    B.p(
        "MVCC lưu nhiều phiên bản của mỗi dòng dữ liệu. Khi một giao tác ghi, phiên bản cũ được giữ lại; giao "
        "tác khác cần đọc sẽ được cung cấp phiên bản phù hợp với thời điểm của nó (một **ảnh chụp – snapshot**) "
        "thay vì phải chờ khóa. Nhờ vậy, **người đọc không chặn người ghi và người ghi không chặn người đọc**. "
        "MVCC thường được kết hợp với khóa: đọc thường dùng snapshot, còn ghi và đọc có khóa vẫn dùng khóa để "
        "tuần tự hóa. Cách InnoDB cài đặt MVCC được trình bày ở mục 2.5.4.",
    )
    B.h3("2.3.4. Khóa bi quan và khóa lạc quan")
    B.p("Ở mức ứng dụng, có hai triết lý xử lý tranh chấp khi đọc dữ liệu rồi ghi dựa trên giá trị đã đọc "
        "({B:bi_lac}). Ngoài ra, nếu toàn bộ điều kiện có thể viết trong **một câu UPDATE có điều kiện** (ví dụ "
        "`SET so_ghe_trong = so_ghe_trong - 1 WHERE … AND so_ghe_trong > 0`) thì việc đọc và ghi diễn ra nguyên "
        "tử bên trong hệ quản trị, không còn khe hở giữa đọc và ghi.")
    B.bang("bi_lac", "So sánh khóa bi quan và khóa lạc quan", ["Tiêu chí", "Khóa bi quan (pessimistic)", "Khóa lạc quan (optimistic)"], [
        ["Giả định", "Xung đột thường xảy ra, phải ngăn từ đầu.", "Xung đột hiếm, chỉ cần phát hiện khi ghi."],
        ["Cách làm", "Khóa dòng ngay khi đọc: SELECT … FOR UPDATE.",
         "Đọc kèm cột version; khi ghi kiểm tra WHERE version = giá trị đã đọc và tăng version."],
        ["Khi có tranh chấp", "Giao tác sau phải chờ giao tác trước commit.",
         "Câu UPDATE không tác động dòng nào; ứng dụng phải đọc lại và thử lại."],
        ["Ưu điểm", "Đơn giản, không phải thử lại.", "Không giữ khóa trong lúc người dùng cân nhắc."],
        ["Nhược điểm", "Giữ khóa lâu làm giảm tính đồng thời, có thể khóa chết.",
         "Tranh chấp cao thì thử lại rất nhiều, có thể bỏ cuộc."],
    ], [3.0, 6.75, 6.75])
    B.h3("2.3.5. Xử lý khóa chết")
    B.p(
        "Có ba hướng xử lý khóa chết: **phòng ngừa** – buộc mọi giao tác xin khóa theo cùng một thứ tự toàn cục "
        "(ví dụ luôn khóa ghế có mã nhỏ trước) thì không thể hình thành vòng chờ; **phát hiện và phá vỡ** – hệ "
        "quản trị duy trì đồ thị chờ, khi phát hiện chu trình thì chọn một giao tác làm nạn nhân và hủy nó; và "
        "**hết thời gian chờ** – giao tác chờ khóa quá một ngưỡng thời gian thì bị báo lỗi. InnoDB dùng đồng thời "
        "phát hiện vòng chờ và hết thời gian chờ (mục 2.5.5).",
    )
    B.h2("2.4. Mức cô lập giao tác theo chuẩn SQL")
    B.p(
        "Bảo đảm khả tuần tự tuyệt đối có chi phí cao, nên chuẩn SQL định nghĩa bốn **mức cô lập** cho phép đánh "
        "đổi giữa tính đúng đắn và hiệu năng. Mỗi mức được định nghĩa bằng những hiện tượng mà nó cho phép xảy ra "
        "({B:muc_co_lap}) [5]. Người lập trình chọn mức cô lập cho từng phiên bằng lệnh "
        "`SET SESSION TRANSACTION ISOLATION LEVEL …`.",
        "Berenson và cộng sự [3] chỉ ra rằng định nghĩa dựa trên hiện tượng của chuẩn SQL còn mơ hồ và bỏ sót "
        "một số bất thường như mất cập nhật (P4) hay lệch ghi (write skew); đồng thời mỗi hệ quản trị cài đặt các "
        "mức cô lập theo cách riêng (bằng khóa hay bằng snapshot), nên hành vi thực tế có thể khác bảng lý thuyết. "
        "Đây chính là điều ứng dụng minh họa đo đạc và kiểm chứng ở Chương 3.",
    )
    B.bang("muc_co_lap", "Các mức cô lập và hiện tượng được phép xảy ra theo chuẩn SQL",
           ["Mức cô lập", "Đọc dữ liệu rác", "Đọc không lặp lại", "Bóng ma"], [
               ["READ UNCOMMITTED", "Có thể", "Có thể", "Có thể"],
               ["READ COMMITTED", "Không", "Có thể", "Có thể"],
               ["REPEATABLE READ", "Không", "Không", "Có thể"],
               ["SERIALIZABLE", "Không", "Không", "Không"],
           ], [5.0, 3.85, 3.85, 3.8], can=["l", "c", "c", "c"])
    B.h2("2.5. Hệ quản trị CSDL MySQL và storage engine InnoDB")
    B.h3("2.5.1. Lịch sử hình thành và kiến trúc")
    B.p(
        "MySQL được công ty MySQL AB (Thụy Điển) phát hành lần đầu năm 1995 và nhanh chóng trở thành hệ quản trị "
        "cơ sở dữ liệu mã nguồn mở phổ biến cho các ứng dụng web. Năm 2008, MySQL AB được Sun Microsystems mua "
        "lại; năm 2010, Oracle mua Sun và tiếp quản MySQL. Storage engine **InnoDB** do Innobase Oy phát triển, "
        "trở thành engine mặc định từ phiên bản 5.5 (2010) thay cho MyISAM vốn không hỗ trợ giao tác. Từ năm 2023, "
        f"Oracle phát hành MySQL theo hai dòng: bản hỗ trợ dài hạn (LTS) và bản Innovation; ứng dụng minh họa dùng "
        f"MySQL {phien_ban}.",
        "MySQL có kiến trúc phân tầng ({H:kien_truc}): tầng máy chủ lo kết nối, phân tích cú pháp, tối ưu và thực "
        "thi câu lệnh; tầng lưu trữ gồm các storage engine giao tiếp qua một API chung. Chỉ engine nào hỗ trợ "
        "giao tác mới có điều khiển truy xuất đồng thời – vì vậy mọi bảng trong đề tài đều khai báo "
        "`ENGINE=InnoDB`. Điểm mạnh của MySQL/InnoDB là phổ biến, miễn phí, hỗ trợ đầy đủ ACID, khóa mức dòng và "
        "MVCC; điểm yếu là một số hành vi mức cô lập khác chuẩn SQL (như sẽ thấy ở Chương 3), và mức mặc định "
        "REPEATABLE READ không tự phát hiện xung đột ghi như một số hệ quản trị khác.",
    )
    B.hinh("kien_truc", "so_do_kien_truc_mysql.png", "Kiến trúc phân tầng của MySQL và các thành phần chính của InnoDB", 15.5)
    B.h3("2.5.2. Mô hình giao tác của InnoDB")
    B.p(
        "Mỗi kết nối tới MySQL là một **phiên** (session); hai giao tác đồng thời luôn thuộc hai phiên khác nhau. "
        "Mặc định MySQL bật chế độ autocommit (mỗi câu lệnh là một giao tác), và mức cô lập mặc định của InnoDB "
        f"là **REPEATABLE READ** (máy chủ trong đề tài báo `{tt['muc_co_lap']}`).",
        "InnoDB phân biệt hai cách đọc [8]. **Đọc nhất quán** (consistent read) là câu SELECT thường: nó đọc trên "
        "snapshot, không đặt khóa và không bao giờ bị chặn. Ở REPEATABLE READ, snapshot được tạo ở lần đọc đầu "
        "tiên và dùng lại suốt giao tác; ở READ COMMITTED, mỗi câu SELECT lấy một snapshot mới. **Đọc có khóa** "
        "(locking read) gồm `SELECT … FOR UPDATE`, `SELECT … FOR SHARE` và các câu UPDATE, DELETE: chúng luôn "
        "đọc **bản mới nhất** (đọc hiện hành – current read) và đặt khóa lên các bản ghi đã duyệt. Riêng ở mức "
        "SERIALIZABLE, InnoDB tự chuyển mọi SELECT thường thành `SELECT … FOR SHARE` khi autocommit tắt.",
        "Hệ quả quan trọng: câu UPDATE ở REPEATABLE READ ghi lên bản mới nhất mà không kiểm tra dòng đó đã bị "
        "giao tác khác sửa sau thời điểm snapshot hay chưa. Đây là nguyên nhân MySQL vẫn để xảy ra mất cập nhật "
        "ở mức này.",
    )
    B.h3("2.5.3. Các loại khóa trong InnoDB")
    B.p("Khóa dòng của InnoDB thực chất là khóa trên **bản ghi chỉ mục**. Các loại khóa chính gồm [4]:")
    B.ds(
        "**Record lock** – khóa đúng một bản ghi chỉ mục (trong performance_schema hiện là `X,REC_NOT_GAP` hoặc "
        "`S,REC_NOT_GAP`).",
        "**Gap lock** – khóa **khoảng trống** giữa hai bản ghi chỉ mục, không khóa bản ghi nào (`X,GAP`). Gap lock "
        "chỉ có tác dụng ngăn chèn dữ liệu mới vào khoảng đó; các gap lock không xung đột với nhau.",
        "**Next-key lock** – record lock trên một bản ghi cộng với gap lock trên khoảng trống ngay trước nó (`X`). "
        "Ở REPEATABLE READ, đọc có khóa theo điều kiện phạm vi dùng next-key lock để chặn bóng ma.",
        "**Insert intention lock** – một loại gap lock do câu INSERT đặt trước khi chèn "
        "(`X,GAP,INSERT_INTENTION`); nó phải chờ nếu khoảng trống đang bị giao tác khác giữ gap lock.",
        "**Khóa ý định IS/IX** – đặt ở mức bảng trước khi khóa dòng bên trong.",
    )
    B.p("{H:khoa_chi_muc} minh họa sự khác biệt giữa REPEATABLE READ và READ COMMITTED khi giao tác A chạy "
        "`SELECT … FROM ve WHERE ma_chuyen = 1 FOR UPDATE`. Ở READ COMMITTED, InnoDB tắt gap lock cho các phép "
        "tìm kiếm thông thường nên chỉ khóa các bản ghi đang tồn tại – đó là lý do bóng ma xuất hiện ở mức này.")
    B.hinh("khoa_chi_muc", "so_do_khoa_chi_muc.png", "Record lock, gap lock và next-key lock trên chỉ mục ma_chuyen", 16.0)
    B.h3("2.5.4. Cơ chế đa phiên bản (MVCC) trong InnoDB")
    B.p(
        "Mỗi dòng trong InnoDB có các trường ẩn, trong đó `DB_TRX_ID` lưu mã giao tác cuối cùng đã sửa dòng và "
        "`DB_ROLL_PTR` trỏ tới bản ghi trong **undo log** chứa phiên bản trước [9]. Khi một giao tác cần đọc nhất "
        "quán, InnoDB tạo một **read view** – danh sách các giao tác đang hoạt động tại thời điểm đó. Nếu phiên "
        "bản hiện tại do một giao tác chưa commit (hoặc commit sau read view) tạo ra, InnoDB lần theo con trỏ "
        "hoàn tác để dựng lại phiên bản cũ phù hợp ({H:mvcc}). Ở READ UNCOMMITTED, InnoDB bỏ qua bước này và "
        "đọc thẳng bản mới nhất – đó chính là đọc dữ liệu rác.",
    )
    B.hinh("mvcc", "so_do_mvcc.png", "MVCC: cùng một dòng, các cách đọc khác nhau thấy các phiên bản khác nhau", 15.5)
    B.h3("2.5.5. Phát hiện và xử lý khóa chết trong InnoDB")
    B.p(
        "Khi tham số `innodb_deadlock_detect` bật (mặc định), InnoDB kiểm tra đồ thị chờ mỗi khi một giao tác phải "
        "chờ khóa. Nếu phát hiện chu trình, InnoDB **ngay lập tức** hủy một giao tác – ưu tiên giao tác “nhỏ” "
        "hơn, tính theo số dòng đã chèn, sửa, xóa – và trả về lỗi **1213** (ER_LOCK_DEADLOCK) [10]. Ngoài ra, "
        "giao tác chờ khóa lâu hơn `innodb_lock_wait_timeout` sẽ nhận lỗi **1205**. Trong đề tài, máy chủ đặt "
        f"`innodb_lock_wait_timeout = {tt['han_cho_khoa']}` giây và bật `innodb_print_all_deadlocks` để ghi mọi "
        "khóa chết vào nhật ký.",
    )
    B.h3("2.5.6. Giám sát khóa qua performance_schema")
    B.p(
        "Từ MySQL 8.0, thông tin khóa của InnoDB được cung cấp qua hai bảng `performance_schema.data_locks` (mọi "
        "khóa đang giữ hoặc đang chờ) và `performance_schema.data_lock_waits` (cặp yêu cầu đang chờ – khóa đang "
        "chặn) [11]. Các cột quan trọng gồm `OBJECT_NAME` (bảng), `INDEX_NAME` (chỉ mục), `LOCK_TYPE` (TABLE / "
        "RECORD), `LOCK_MODE` (chế độ khóa, ví dụ `X,GAP`), `LOCK_STATUS` (GRANTED / WAITING) và `LOCK_DATA` (giá "
        "trị khóa của bản ghi). Ứng dụng minh họa đọc hai bảng này để hiển thị khóa tại từng bước:",
    )
    B.ma("""
SELECT t.PROCESSLIST_ID AS ma_conn, l.ENGINE_TRANSACTION_ID AS trx,
       l.OBJECT_NAME AS bang, l.INDEX_NAME AS chi_muc, l.LOCK_TYPE AS loai_khoa,
       l.LOCK_MODE AS che_do_khoa, l.LOCK_STATUS AS trang_thai,
       l.LOCK_DATA AS du_lieu
  FROM performance_schema.data_locks l
  JOIN performance_schema.threads t ON t.THREAD_ID = l.THREAD_ID
 WHERE l.OBJECT_SCHEMA = DATABASE();
""")
    B.h2("2.6. Công nghệ xây dựng ứng dụng minh họa")
    B.p("Ứng dụng minh họa được xây dựng với các công nghệ trong {B:cong_nghe}. Tiêu chí lựa chọn là gọn nhẹ, "
        "phổ biến, cho phép mở nhiều kết nối MySQL song song và dễ triển khai trên máy của mọi thành viên.")
    B.bang("cong_nghe", "Các công nghệ sử dụng", ["Thành phần", "Công nghệ", "Vai trò"], [
        ["Hệ quản trị CSDL", f"MySQL {phien_ban}, InnoDB", "Đối tượng nghiên cứu; chạy trong container Docker."],
        ["Máy chủ ứng dụng", "Python 3.13, FastAPI, Uvicorn", "API REST điều phối các kịch bản, trả kết quả dạng JSON."],
        ["Kết nối CSDL", "PyMySQL", "Mỗi phiên/khách là một kết nối riêng chạy trên một luồng (thread) riêng."],
        ["Giao diện", "HTML, CSS, JavaScript thuần", "4 tab chức năng, hoạt hình lịch giao tác, biểu đồ SVG."],
        ["Triển khai", "Docker, Docker Compose", "Đóng gói MySQL và ứng dụng; chạy bằng tệp khoi-dong.bat."],
        ["Kiểm thử", "pytest, httpx", "151 trường hợp kiểm thử chạy trên MySQL thật."],
        ["Quản lý mã nguồn", "Git, GitHub", "Chia sẻ mã nguồn cho các thành viên nhóm."],
    ], [3.8, 5.0, 7.7])

    # ==================================================================== CHƯƠNG 3
    B.h1("CHƯƠNG 3. PHÂN TÍCH HỆ THỐNG VÀ XÂY DỰNG SẢN PHẨM", chuong=3)
    B.h2("3.1. Phân tích hệ thống")
    B.p(
        "Dựa trên lý do chọn đề tài và mục tiêu ở Chương 1, ứng dụng minh họa phải trả lời được ba câu hỏi cho "
        "người học: xung đột xảy ra như thế nào (thấy được lịch giao tác và dữ liệu tại từng bước), vì sao một "
        "thay đổi nhỏ lại ngăn được xung đột (so sánh kịch bản sai và đúng), và cái giá của từng cách xử lý là "
        "gì (đo đạc khi nhiều giao tác cùng tranh chấp). Yêu cầu xuyên suốt là mọi kết quả phải đến từ MySQL "
        "thật, không được mô phỏng."
    )
    B.h3("3.1.1. Yêu cầu chức năng")
    B.bang("yc_chuc_nang", "Yêu cầu chức năng", ["Mã", "Chức năng", "Mô tả"], [
        ["CN01", "Năm xung đột: sai và đúng", "Chọn một trong 5 xung đột, chạy kịch bản SAI hoặc ĐÚNG trên MySQL; "
                                              "hiển thị lịch giao tác T₁ | T₂, kết quả từng câu lệnh, dữ liệu và khóa."],
        ["CN02", "Phát lại dạng hoạt hình", "Phát/dừng, đi từng bước, nhảy tới bước bất kỳ, chọn tốc độ; "
                                            "giải thích bằng lời từng bước."],
        ["CN03", "So sánh hai kịch bản", "Đặt cạnh nhau mức cô lập, câu lệnh then chốt, lịch thực thi, số lần "
                                         "bị chặn, thời gian chờ khóa và lỗi của kịch bản sai và đúng."],
        ["CN04", "Nhiều khách đặt vé", "1–60 khách (mỗi khách một kết nối) cùng đặt vé với 4 cách xử lý hoặc "
                                       "kịch bản deadlock; biểu đồ diễn biến, sơ đồ ghế, bảng khóa, nhật ký SQL."],
        ["CN05", "Phòng thí nghiệm mức cô lập", "Chạy 6 thí nghiệm ở 4 mức cô lập (24 lần) và lập ma trận đối "
                                                "chiếu với lý thuyết chuẩn SQL; xem chi tiết từng thí nghiệm."],
        ["CN06", "So sánh hiệu năng", "Chạy 4 cách xử lý nhiều lần, lấy trung bình; khảo sát khi số khách tăng dần."],
        ["CN07", "Giám sát khóa", "Đọc performance_schema.data_locks và data_lock_waits để biết ai giữ, ai chờ khóa gì."],
    ], [1.6, 4.2, 10.7])
    B.h3("3.1.2. Yêu cầu phi chức năng")
    B.bang("yc_phi_cn", "Yêu cầu phi chức năng", ["Yêu cầu", "Mô tả"], [
        ["Trung thực", "Mọi số liệu, kết quả, bảng khóa lấy từ MySQL thật; giao diện chỉ phát lại những gì đã xảy ra."],
        ["Tái hiện được", "Kịch bản xung đột cho cùng kết quả ở mọi lần chạy (thứ tự xen kẽ được cố định)."],
        ["Dễ triển khai", "Chỉ cần Docker Desktop; nhấp đúp khoi-dong.bat là chạy, không đụng MySQL có sẵn trên máy (cổng 3310)."],
        ["An toàn dữ liệu demo", "Tại một thời điểm chỉ một kịch bản được chạy (trả mã 409 nếu đang bận)."],
        ["Kiểm thử tự động", "Bộ kiểm thử chạy trên MySQL thật, chạy lặp nhiều lần không chập chờn."],
        ["Dễ hiểu", "Giao diện tiếng Việt, ký hiệu lịch theo giáo trình, chú giải và giải thích từng bước."],
    ], [3.8, 12.7])
    B.h3("3.1.3. Sơ đồ use case")
    B.p("Ứng dụng có một tác nhân là người học hoặc giảng viên. {H:use_case} liệt kê các chức năng mà tác nhân "
        "sử dụng; mỗi nhóm chức năng tương ứng với một tab của giao diện.")
    B.hinh("use_case", "so_do_use_case.png", "Sơ đồ use case của ứng dụng minh họa", 14.0)
    B.h3("3.1.4. Kiến trúc hệ thống")
    B.p(
        "Hệ thống gồm ba thành phần ({H:kien_truc_ht}). **Trình duyệt** hiển thị giao diện bốn tab, gọi API bằng "
        "HTTP và nhận kết quả dạng JSON. **Container ứng dụng** chạy FastAPI, gồm các mô-đun: `main.py` (khai báo "
        "API), `xungdot.py` (định nghĩa 5 xung đột × 2 kịch bản), `phongthinghiem.py` (bộ điều phối hai phiên và "
        "các thí nghiệm mức cô lập), `kichban.py` (nhiều khách đặt vé, theo dõi khóa, so sánh hiệu năng) và "
        "`csdl.py` (quản lý kết nối, mức cô lập). **Container MySQL** chạy MySQL "
        f"{phien_ban}, ánh xạ ra cổng 3310 để không xung đột với MySQL có sẵn trên máy. Mỗi phiên A, B hay mỗi "
        "khách hàng là một kết nối PyMySQL riêng, vì trong MySQL một giao tác gắn với đúng một kết nối.",
    )
    B.hinh("kien_truc_ht", "so_do_kien_truc_he_thong.png", "Kiến trúc tổng thể của ứng dụng minh họa", 16.0)
    B.p("Các API chính của ứng dụng được liệt kê trong {B:api}.")
    B.bang("api", "Các API của ứng dụng", ["Phương thức", "Đường dẫn", "Chức năng"], [
        ["GET", "/api/thong-tin", "Thông tin máy chủ MySQL (phiên bản, engine, mức cô lập mặc định…)."],
        ["GET", "/api/xung-dot", "Danh sách 5 xung đột kèm mã nguồn SQL của từng phiên."],
        ["POST", "/api/xung-dot/chay", "Chạy một kịch bản (mã xung đột, sai/đúng), trả về nhật ký từng bước."],
        ["POST", "/api/chay", "Nhiều khách đặt vé với một cách xử lý."],
        ["POST", "/api/thi-nghiem/chay", "Chạy một thí nghiệm ở một mức cô lập."],
        ["POST", "/api/thi-nghiem/ma-tran", "Chạy toàn bộ 6 thí nghiệm × 4 mức cô lập."],
        ["POST", "/api/so-sanh", "So sánh 4 cách xử lý, lặp nhiều lần."],
        ["POST", "/api/khao-sat", "Khảo sát khi số khách tăng dần."],
    ], [2.3, 4.9, 9.3])
    B.h3("3.1.5. Thiết kế cơ sở dữ liệu")
    B.p(
        "Cơ sở dữ liệu `demo_dongthoi` gồm ba bảng, đều dùng `ENGINE=InnoDB` ({H:luoc_do}). Bảng `chuyen_bay` "
        "lưu số ghế trống của từng chuyến – đây là **điểm tranh chấp chính**: mọi giao tác bán vé đều đọc và ghi "
        "cột `so_ghe_trong` của cùng một dòng. Cột `version` phục vụ khóa lạc quan. Bảng `ve` lưu mỗi vé đã bán "
        "và có chỉ mục `fk_ve_chuyen` trên cột `ma_chuyen` – chỉ mục này là nơi xuất hiện gap lock trong kịch bản "
        "bóng ma. Bảng `ghe` lưu hai ghế 12A, 12B dùng cho kịch bản khóa chết.",
    )
    B.hinh("luoc_do", "so_do_luoc_do_csdl.png", "Lược đồ cơ sở dữ liệu demo_dongthoi", 15.5)
    B.bang("mo_ta_bang", "Mô tả các cột của ba bảng", ["Bảng", "Cột", "Kiểu", "Ý nghĩa"], [
        ["chuyen_bay", "ma_chuyen (PK)", "INT", "Mã chuyến bay"],
        ["", "so_hieu", "VARCHAR(100)", "Số hiệu, ví dụ VN-808"],
        ["", "tong_ghe", "INT", "Tổng số ghế mở bán"],
        ["", "so_ghe_trong", "INT", "Số ghế còn trống – dữ liệu bị tranh chấp"],
        ["", "version", "INT", "Phiên bản dòng, tăng mỗi lần ghi (khóa lạc quan)"],
        ["ve", "ma_ve (PK)", "INT AUTO_INCREMENT", "Mã vé"],
        ["", "ma_chuyen (FK)", "INT", "Chuyến bay của vé"],
        ["", "hanh_khach", "VARCHAR(50)", "Tên hành khách"],
        ["", "thoi_diem", "DATETIME(6)", "Thời điểm bán, chính xác tới micro giây"],
        ["ghe", "ma_ghe (PK)", "INT", "Mã ghế"],
        ["", "ma_chuyen (FK)", "INT", "Chuyến bay của ghế"],
        ["", "so_ghe", "VARCHAR(10)", "Số ghế: 12A, 12B"],
        ["", "trang_thai", "VARCHAR(20)", "'trong' hoặc 'dang_giu'"],
        ["", "nguoi_giu", "VARCHAR(50)", "Phiên đang giữ ghế"],
    ], [2.6, 3.6, 4.0, 6.3], can=["l", "l", "l", "l"])
    B.p("Trước mỗi kịch bản, ứng dụng xóa và nạp lại dữ liệu ban đầu: chuyến VN-808 (mã 1) có 10 ghế, còn "
        "trống 7; chuyến VN-216 (mã 2) còn trống 8; bảng `ve` có 5 vé (An, Bình, Chi thuộc VN-808; Dũng, Giang "
        "thuộc VN-216); bảng `ghe` có hai ghế 12A, 12B đều trống. Nhờ vậy mọi kịch bản xuất phát từ cùng một "
        "trạng thái.")
    B.h3("3.1.6. Thiết kế năm cặp kịch bản xung đột")
    B.p(
        "Nguyên tắc thiết kế quan trọng nhất là: **kịch bản ĐÚNG chỉ khác kịch bản SAI đúng một điểm** – một "
        "mệnh đề, một mức cô lập hoặc một thứ tự khóa. Hai kịch bản chạy trên cùng dữ liệu, cùng thứ tự xen kẽ "
        "các bước, nên người xem biết chắc điểm khác biệt đó chính là nguyên nhân (hoặc cách sửa). Trên giao "
        "diện, dòng then chốt được đánh dấu “← nguyên nhân” ở kịch bản sai và “← cách sửa” ở kịch bản đúng. "
        "{B:nam_cap} tóm tắt thiết kế.",
    )
    B.bang("nam_cap", "Thiết kế năm cặp kịch bản sai / đúng", ["#", "Xung đột", "Kịch bản SAI", "Kịch bản ĐÚNG", "Khác biệt duy nhất"], [
        ["1", "Mất cập nhật", "REPEATABLE READ, SELECT thường rồi UPDATE ghi đè", "REPEATABLE READ, SELECT … FOR UPDATE", "Thêm FOR UPDATE"],
        ["2", "Đọc dữ liệu rác", "READ UNCOMMITTED", "READ COMMITTED", "Mức cô lập"],
        ["3", "Đọc không lặp lại", "READ COMMITTED", "REPEATABLE READ", "Mức cô lập"],
        ["4", "Bóng ma", "READ COMMITTED + FOR UPDATE", "REPEATABLE READ + FOR UPDATE", "Mức cô lập (gap lock)"],
        ["5", "Khóa chết", "A khóa 12A → 12B, B khóa 12B → 12A", "Cả hai khóa 12A → 12B", "Thứ tự khóa"],
    ], [0.8, 2.9, 4.6, 4.4, 3.8], can=["c", "l", "l", "l", "l"])
    B.p("Mỗi kịch bản là một danh sách bước có thứ tự, mỗi bước gồm mã bước, phiên thực hiện, câu SQL và mô tả. "
        "Ví dụ kịch bản SAI của xung đột mất cập nhật được khai báo trong `xungdot.py` như sau (bước `K1` là bước "
        "kiểm tra, không thuộc giao tác nào):")
    B.ma("""
Buoc("A1", "A", "START TRANSACTION", "A mở giao tác"),
Buoc("B1", "B", "START TRANSACTION", "B mở giao tác"),
Buoc("A2", "A", SQL_DOC_GHE, "A đọc số ghế còn – đọc thường, không khóa",
     diem_khac=True),
Buoc("B2", "B", SQL_DOC_GHE, "B cũng đọc số ghế còn", diem_khac=True),
Buoc("A3", "A", _ghi_tru_mot("A2"), "A bán 1 vé: ghi lại giá trị đã đọc − 1"),
Buoc("A4", "A", "COMMIT", "A commit"),
Buoc("B3", "B", _ghi_tru_mot("B2"), "B bán 1 vé: ghi lại giá trị đã đọc − 1"),
Buoc("B4", "B", "COMMIT", "B commit"),
Buoc("K1", "A", SQL_DOC_GHE, "Kiểm tra: lẽ ra phải còn 5 ghế"),
""", "python")
    B.h3("3.1.7. Bộ điều phối hai phiên")
    B.p(
        "Thách thức kỹ thuật lớn nhất của ứng dụng là chạy hai phiên xen kẽ đúng thứ tự trong khi một câu lệnh "
        "có thể bị InnoDB **chặn** vì chờ khóa: phiên bị chặn treo lại, nhưng phiên kia vẫn phải chạy tiếp được "
        "(nếu không, khóa sẽ không bao giờ được nhả). Bộ điều phối `thuc_thi_hai_phien()` giải quyết như "
        "{H:dieu_phoi}: mỗi phiên có một kết nối và một luồng thực thi riêng; bộ điều phối gửi câu lệnh rồi chờ "
        "tối đa 700 ms. Nếu câu lệnh chưa trả về, bước đó được đánh dấu **bị chặn** và bảng khóa được chụp ngay "
        "lúc ấy; các bước sau của cùng phiên được **hoãn** lại vì một kết nối không thể gửi câu lệnh mới khi câu "
        "trước chưa xong. Khi câu bị chặn hoàn tất (do phiên kia commit/rollback hoặc do InnoDB phá khóa chết), "
        "kết quả được ghi nhận và các bước đã hoãn được **chạy bù**.",
        "Sau mỗi sự kiện, bộ điều phối chụp dữ liệu theo **hai góc nhìn** bằng hai kết nối riêng không đặt khóa: "
        "một kết nối ở READ COMMITTED (thấy bản đã commit) và một kết nối ở READ UNCOMMITTED (thấy bản mới nhất, "
        "kể cả bản nháp chưa commit). Giao diện hiển thị hai giá trị này cạnh nhau: giá trị gạch ngang là bản đã "
        "commit, giá trị tô vàng là bản nháp. Nhờ đó người xem thấy rõ dữ liệu “dở dang” của từng giao tác.",
    )
    B.hinh("dieu_phoi", "so_do_dieu_phoi.png", "Lưu đồ bộ điều phối hai phiên", 15.5)
    B.h3("3.1.8. Thiết kế bốn cách đặt vé đồng thời")
    B.p("Ở chức năng nhiều khách đặt vé, mỗi khách là một luồng với kết nối riêng; mọi luồng được giữ ở “vạch "
        "xuất phát” cho tới khi tất cả đã sẵn sàng rồi mới cùng chạy, để tạo tranh chấp thật. Giữa bước đọc và "
        "bước ghi có một khoảng “cân nhắc” (mặc định 100 ms) mô phỏng thời gian khách xem lại đơn hàng – đây "
        "chính là khe hở nơi tranh chấp xảy ra. Bốn cách xử lý được cài đặt như sau.")
    B.p("**Cách 1 – Không dùng khóa (đọc rồi ghi đè):**")
    B.ma("""
START TRANSACTION;
SELECT so_ghe_trong FROM chuyen_bay WHERE ma_chuyen = 1;          -- đọc được n
-- … khách cân nhắc …
UPDATE chuyen_bay SET so_ghe_trong = n - 1     -- ghi đè giá trị tự tính
 WHERE ma_chuyen = 1;
INSERT INTO ve (ma_chuyen, hanh_khach) VALUES (1, 'Khách i');
COMMIT;
""")
    B.p("**Cách 2 – Khóa bi quan:** giống cách 1 nhưng câu đọc là `SELECT so_ghe_trong FROM chuyen_bay WHERE "
        "ma_chuyen = 1 FOR UPDATE`, đặt khóa X lên dòng ngay khi đọc; các khách khác phải xếp hàng.")
    B.p("**Cách 3 – Khóa lạc quan:** mỗi lần thử là một giao tác mới; nếu câu UPDATE không tác động dòng nào "
        "(do version đã đổi) thì rollback, chờ ngẫu nhiên một chút rồi thử lại, tối đa 8 lần.")
    B.ma("""
START TRANSACTION;
SELECT so_ghe_trong, version                   -- đọc được n, v
  FROM chuyen_bay WHERE ma_chuyen = 1;
-- … khách cân nhắc …
UPDATE chuyen_bay SET so_ghe_trong = n - 1, version = version + 1
 WHERE ma_chuyen = 1 AND version = v;
-- 0 dòng bị tác động => có người ghi trước => ROLLBACK rồi thử lại
INSERT INTO ve (ma_chuyen, hanh_khach) VALUES (1, 'Khách i');
COMMIT;
""")
    B.p("**Cách 4 – UPDATE nguyên tử có điều kiện:** điều kiện còn ghế nằm ngay trong câu UPDATE nên không có "
        "khe hở giữa đọc và ghi; nếu 0 dòng bị tác động nghĩa là đã hết ghế.")
    B.ma("""
START TRANSACTION;
UPDATE chuyen_bay SET so_ghe_trong = so_ghe_trong - 1
 WHERE ma_chuyen = 1 AND so_ghe_trong > 0;
INSERT INTO ve (ma_chuyen, hanh_khach) VALUES (1, 'Khách i');
COMMIT;
""")
    B.p("Ngoài ra, chế độ **deadlock** cho các khách giữ hai ghế 12A, 12B theo thứ tự ngược nhau (một nửa số "
        "khách giữ 12A trước, nửa còn lại giữ 12B trước) để quan sát InnoDB phát hiện và phá vòng chờ.")
    B.h3("3.1.9. Giám sát khóa và các vấn đề gặp phải")
    B.p(
        "Trong lúc kịch bản nhiều khách chạy, một luồng riêng lấy mẫu `data_locks` và `data_lock_waits` mỗi 25 ms "
        "để biết câu lệnh nào bị chặn và **bị ai chặn**. Quá trình xây dựng cho thấy một số “bẫy” khi giám sát "
        "khóa mà tài liệu ít đề cập, cần xử lý để số liệu đúng:",
    )
    B.ds(
        "`information_schema.innodb_trx` được phục vụ từ một bộ đệm chỉ làm mới khi đã hơn 0,1 giây không ai đọc; "
        "đọc liên tục sẽ mãi nhận ảnh chụp cũ. Ứng dụng dùng `performance_schema.threads` thay thế.",
        "`data_lock_waits` liệt kê cả những yêu cầu đang xếp hàng phía trước chứ không chỉ người đang giữ khóa; phải "
        "ghép với `data_locks` và lọc `LOCK_STATUS = 'GRANTED'` để biết ai thật sự chặn.",
        "`THREAD_ID` trong `data_locks` là luồng đã tạo cấu trúc khóa, chưa chắc là chủ sở hữu: khi B bị hủy vì khóa "
        "chết, khóa được trao cho A lại mang `THREAD_ID` của B. Chủ sở hữu thật được xác định qua "
        "`ENGINE_TRANSACTION_ID` (ứng dụng dùng khóa ý định mức bảng của mỗi giao tác để ánh xạ).",
        "Một truy vấn trên performance_schema không phải ảnh chụp nguyên tử; nếu chạy trúng lúc khóa đang được "
        "chuyển giao, có thể thấy cả người giữ cũ lẫn người giữ mới.",
    )

    # ---------------------------------------------------------------- 3.2 giao diện
    B.h2("3.2. Xây dựng giao diện sản phẩm")
    B.p("Giao diện được tổ chức thành bốn tab tương ứng với các nhóm chức năng ở {H:use_case}. Các hình trong "
        "mục này là ảnh chụp trực tiếp từ ứng dụng khi chạy trên MySQL; số liệu trong hình và trong các bảng là "
        "kết quả của cùng một lần chạy.")
    B.h3("3.2.1. Giao diện tổng quan và điều hướng")
    B.p(
        "**Tên chức năng:** màn hình chính. **Chức năng:** giới thiệu bối cảnh đặt vé chuyến VN-808 Hà Nội – TP. Hồ "
        f"Chí Minh, hiển thị thông tin máy chủ (MySQL {phien_ban}, engine InnoDB, mức cô lập mặc định, thời gian chờ "
        "khóa, trạng thái phát hiện khóa chết) và thanh tab để chuyển giữa bốn chức năng ({H:tong_quan}).",
    )
    B.hinh("tong_quan", "giao_dien_tong_quan.png", "Giao diện tổng quan của ứng dụng", 16.0)
    B.p("Thanh tiêu đề dính ở đầu màn hình nên khi cuộn xuống xem lịch giao tác, nó che mất một phần nội dung. "
        "Nút **▲ Ẩn thanh trên** cho phép ẩn thanh này; nút nổi **▼ Hiện thanh trên** ở góc phải dùng để hiện lại, "
        "và lựa chọn được nhớ trong trình duyệt ({H:thanh_hien}, {H:thanh_an}).")
    B.hinh("thanh_hien", "thanh_tren_dang_hien.png", "Khi thanh trên đang hiện, một phần lịch giao tác bị che", 15.0)
    B.hinh("thanh_an", "thanh_tren_da_an.png", "Sau khi bấm “Ẩn thanh trên”, lịch giao tác và bảng CSDL hiện đầy đủ", 15.0)
    B.h3("3.2.2. Chức năng năm xung đột: sai và đúng")
    B.p(
        "**Tên chức năng:** 5 xung đột: sai và đúng (tab 1). **Chức năng:** người dùng chọn một xung đột "
        "({H:xd_ds}), chọn kịch bản SAI hoặc ĐÚNG; ứng dụng chạy kịch bản trên MySQL rồi phát lại dưới dạng hoạt "
        "hình. Thanh điều khiển ({H:xd_dk}) cho phép phát/dừng, đi từng bước (phím ← →), nhảy tới bước bất kỳ trên "
        "thanh tiến độ, chọn tốc độ 0,5× / 1× / 2× và chạy lại kịch bản trên MySQL.",
        "Màn hình phát lại gồm: dòng tóm tắt bước hiện tại; khung **“Chuyện gì vừa xảy ra?”** giải thích bằng lời; "
        "**lịch thực thi** viết bằng ký hiệu giáo trình theo đúng thứ tự MySQL đã thực hiện; bảng **lịch giao "
        "tác** hai cột T₁ (phiên A – quầy vé) và T₂ (phiên B – ứng dụng di động), mỗi hàng là một thời điểm, kết "
        "quả hiện ngay dưới câu lệnh; thanh dọc cạnh mỗi cột thể hiện giao tác đang mở (liền màu) hoặc đang bị "
        "chặn chờ khóa (đỏ, đứt đoạn); và khung **CSDL** bên phải hiển thị dữ liệu cùng cột khóa tại thời điểm "
        "đang xem.",
    )
    B.hinh("xd_ds", "xd_danh_sach.png", "Danh sách năm xung đột", 16.0)
    B.hinh("xd_dk", "xd_dieu_khien.png", "Chọn kịch bản, hướng dẫn đọc màn hình và thanh điều khiển phát lại", 16.0)

    def tom_tat(m, l):
        r = xd[(m, l)]
        tk = r["tong_ket"]
        lich = " ".join(x["ky_hieu"] for x in r["lich"])
        loi = ", ".join(tk["loi"]) if tk["loi"] else "không"
        return lich, tk["so_lan_bi_chan"], tk["thoi_gian_cho_ms"], loi, r

    ket_qua_xd = []

    def mot_xung_dot(so_, ma, ten, ten_en, mo_dau, phan_tich_sai, phan_tich_dung, rong_sai=15.0, rong_dung=15.0):
        B.h3(f"3.2.{so_ + 2}. Xung đột {so_}: {ten} ({ten_en})")
        B.p(mo_dau)
        lich_s, chan_s, cho_s, loi_s, rs = tom_tat(ma, "sai")
        lich_d, chan_d, cho_d, loi_d, rd = tom_tat(ma, "dung")
        B.p(f"**Kịch bản SAI** – {rs['tieu_de']} (mức cô lập {rs['muc_co_lap']}). Lịch thực thi đo được: "
            f"`{lich_s}`. " + phan_tich_sai)
        B.hinh(f"{ma}_sai", f"xd_{ma}_sai.png", f"{ten} – kịch bản SAI tại bước then chốt", rong_sai)
        B.p(f"Kết luận do ứng dụng sinh ra từ kết quả thật của MySQL: *“{rs['giai_thich']}”*")
        B.p(f"**Kịch bản ĐÚNG** – {rd['tieu_de']} (mức cô lập {rd['muc_co_lap']}). Lịch thực thi đo được: "
            f"`{lich_d}`. " + phan_tich_dung)
        B.hinh(f"{ma}_dung", f"xd_{ma}_dung.png", f"{ten} – kịch bản ĐÚNG tại bước then chốt", rong_dung)
        B.p(f"Kết luận của ứng dụng: *“{rd['giai_thich']}”*")
        B.p(f"Khi đã chạy cả hai kịch bản, thẻ **So sánh hai kịch bản** đặt chúng cạnh nhau ({{H:{ma}_ss}}).")
        B.hinh(f"{ma}_ss", f"xd_{ma}_so_sanh.png", f"{ten} – so sánh hai kịch bản", 16.0)
        ket_qua_xd.append([ten, "Có" if rs["xay_ra"] else "Không", "Có" if rd["xay_ra"] else "Không",
                           str(chan_d), so(cho_d) + " ms" if cho_d else "0", loi_s if loi_s != "không" else "—",
                           loi_d if loi_d != "không" else "—"])

    mot_xung_dot(
        1, "mat_cap_nhat", "Mất cập nhật", "Lost update",
        "Hai phiên cùng bán một vé của chuyến VN-808 khi còn 7 ghế trống. Kết quả đúng sau hai lần bán phải là 5.",
        "Cả hai phiên đọc được 7 vì câu SELECT thường là đọc nhất quán, không đặt khóa. A ghi 6 và commit; B cũng "
        "ghi 6 – đúng giá trị A vừa ghi – nên MySQL chỉ trả về `Rows matched: 1, Changed: 0`, không có lỗi hay "
        "cảnh báo nào. Bước kiểm tra cuối cho thấy còn 6 ghế ({H:mat_cap_nhat_sai}). Điều này chứng minh mức "
        "REPEATABLE READ của MySQL **không** ngăn được mất cập nhật.",
        "Câu đọc của A dùng `FOR UPDATE` nên đặt khóa X lên dòng ngay khi đọc. Câu đọc của B cũng xin khóa X nên "
        "bị chặn (ký hiệu `xl₂(X)` kèm đồng hồ cát) cho tới khi A commit ({H:mat_cap_nhat_dung}); khi được chạy "
        "tiếp, B đọc giá trị **mới** là 6 và ghi 5. Đây là đọc hiện hành: dù ở REPEATABLE READ, câu đọc có khóa "
        "vẫn thấy bản mới nhất.",
    )
    mot_xung_dot(
        2, "doc_rac", "Đọc dữ liệu rác", "Dirty read",
        "Phiên B sửa số ghế trống thành 0 nhưng chưa commit (chẳng hạn đang giữ chỗ tạm), phiên A đọc số ghế, sau "
        "đó B rollback.",
        "Ở READ UNCOMMITTED, câu SELECT của A đọc thẳng bản mới nhất trong InnoDB nên thấy 0 – con số chưa từng "
        "được commit ({H:doc_rac_sai}). Trong khung CSDL, giá trị 0 được tô vàng kèm nhãn “chưa commit”.",
        "Chỉ đổi mức cô lập lên READ COMMITTED, câu lệnh giữ nguyên. A đọc được 7 – bản đã commit – do InnoDB "
        "dựng lại từ undo log, và A **không phải chờ** B ({H:doc_rac_dung}). Đây là ưu điểm của MVCC so với cài "
        "đặt bằng khóa thuần túy.",
    )
    mot_xung_dot(
        3, "doc_khong_lap_lai", "Đọc không lặp lại", "Non-repeatable read",
        "Phiên A đọc số ghế trống hai lần trong cùng một giao tác; giữa hai lần đọc, phiên B bán một vé (ghi 6) "
        "và commit.",
        "Ở READ COMMITTED, mỗi câu SELECT lấy một snapshot mới nên lần đọc thứ hai của A thấy 6 trong khi lần đầu "
        "thấy 7 ({H:doc_khong_lap_lai_sai}).",
        "Ở REPEATABLE READ, snapshot được tạo ở lần đọc đầu tiên và dùng lại suốt giao tác, nên A đọc hai lần đều "
        "ra 7, trong khi B vẫn sửa và commit bình thường, không ai bị chặn ({H:doc_khong_lap_lai_dung}).",
    )
    mot_xung_dot(
        4, "bong_ma", "Bóng ma", "Phantom read",
        "Phiên A khóa toàn bộ vé của chuyến VN-808 bằng `SELECT … FOR UPDATE` (3 vé), phiên B cố chèn thêm vé "
        "cho đúng chuyến đó rồi commit, sau đó A khóa lại.",
        "Ở READ COMMITTED, InnoDB chỉ khóa 3 bản ghi đang tồn tại (record lock), khoảng trống giữa chúng vẫn mở; "
        "INSERT của B thành công và lần khóa thứ hai của A thấy 4 dòng – dòng thứ tư là “bóng ma” "
        "({H:bong_ma_sai}).",
        "Ở REPEATABLE READ, `FOR UPDATE` đặt next-key lock: khóa cả bản ghi lẫn khoảng trống. INSERT của B rơi vào "
        "khoảng đã bị khóa nên phải chờ khóa ý định chèn và bị chặn cho tới khi A commit ({H:bong_ma_dung}). Hai "
        "lần khóa của A đều thấy 3 dòng.",
    )
    nan_nhan = "B" if "chọn B" in xd[("deadlock", "sai")]["giai_thich"] else "A"
    con_lai = "A" if nan_nhan == "B" else "B"
    chi_so = "₂" if nan_nhan == "B" else "₁"
    mot_xung_dot(
        5, "deadlock", "Khóa chết", "Deadlock",
        "Hai phiên cùng muốn giữ hai ghế 12A và 12B. Mỗi lần giữ ghế là một câu UPDATE đặt khóa X lên dòng ghế.",
        "A giữ 12A, B giữ 12B, rồi A xin 12B (bị chặn vì B đang giữ) và B xin 12A: hai bên chờ nhau thành vòng "
        f"tròn. InnoDB phát hiện ngay lập tức, không đợi hết thời gian chờ khóa, chọn {nan_nhan} làm nạn nhân và "
        f"trả về lỗi **1213** ({{H:deadlock_sai}}). Ký hiệu `xl{chi_so}(…) a{chi_so}` cho thấy {nan_nhan} xin khóa "
        f"rồi bị hủy; {con_lai} được chạy tiếp và giữ cả hai ghế.",
        "Chỉ đổi thứ tự khóa của B: cả hai đều khóa 12A trước. B phải chờ A ở ghế 12A, nhưng A không cần thứ gì B "
        "đang giữ nên **không có vòng chờ** – chỉ là xếp hàng bình thường ({H:deadlock_dung}). Khi A commit, B đọc "
        "lại bản mới nhất, thấy ghế đã có người giữ (`Rows matched: 0`) nên không giữ được ghế nào – đúng nghiệp "
        "vụ và không có lỗi.",
    )
    B.p("{B:kq_xd} tổng hợp kết quả đo được của mười kịch bản: mọi kịch bản SAI đều tái hiện được xung đột và "
        "mọi kịch bản ĐÚNG đều ngăn được nó, đúng như thiết kế.")
    B.bang("kq_xd", "Kết quả đo được của năm cặp kịch bản",
           ["Xung đột", "SAI: xảy ra", "ĐÚNG: xảy ra", "ĐÚNG: số lần bị chặn", "ĐÚNG: thời gian chờ", "Lỗi (SAI)", "Lỗi (ĐÚNG)"],
           ket_qua_xd, [3.2, 1.9, 2.0, 2.2, 2.4, 2.6, 2.2], can=["l", "c", "c", "c", "c", "c", "c"])

    # ------------------------------------------------ tab 2
    B.h3("3.2.8. Chức năng mô phỏng nhiều khách đặt vé")
    B.p(
        "**Tên chức năng:** Nhiều khách đặt vé (tab 2). **Chức năng:** khác với tab 1 (thứ tự xen kẽ cố định), ở "
        "đây nhiều khách thật sự xuất phát cùng một mili giây và tranh nhau số ghế có hạn. Người dùng chọn cách xử "
        "lý tranh chấp, số khách (1–60), số ghế mở bán, thời gian cân nhắc và mức cô lập ({H:dv_cau_hinh}); khung "
        "bên dưới mô tả cách làm và mã SQL tương ứng.",
    )
    B.hinh("dv_cau_hinh", "dv_cau_hinh.png", "Cấu hình mô phỏng nhiều khách đặt vé", 16.0)
    k = dv["khong_khoa"]
    B.p(
        f"Với **không dùng khóa**, {k['so_khach']} khách tranh {k['tong_ghe']} ghế: hệ thống bán ra "
        f"{k['so_ve_da_ban']} vé, **bán vượt {k['ban_vuot']} vé**, trong khi cột số ghế trống vẫn báo "
        f"{k['so_ghe_con_lai']} ({H_('dv_kk_kq')}). Biểu đồ diễn biến ({H_('dv_kk_tl')}) cho thấy mỗi hàng là một "
        "giao tác: đoạn xám dài là lúc khách cân nhắc khi giao tác vẫn mở, đoạn đỏ là lúc bị chặn chờ khóa. Đáng "
        f"chú ý là ngay cả khi không dùng khóa, vẫn có {k['so_lan_cho_khoa']} lần chờ khóa vì câu UPDATE luôn phải "
        "xin khóa X; nhưng khóa đến quá muộn – sau khi giá trị đã được đọc. Sơ đồ khoang ghế đánh dấu các ghế bị "
        f"bán trùng ({H_('dv_kk_ghe')}).",
    )
    B.hinh("dv_kk_kq", "dv_khong_khoa_ket_qua.png", "Kết quả khi không dùng khóa: bán vượt", 16.0)
    B.hinh("dv_kk_tl", "dv_khong_khoa_dong_thoi_gian.png", "Diễn biến bên trong CSDL khi không dùng khóa", 16.0)
    B.hinh("dv_kk_ghe", "dv_khong_khoa_khoang_ghe.png", "Sơ đồ khoang ghế: các ghế bị bán trùng", 16.0)
    b_ = dv["bi_quan"]
    B.p(
        f"Với **khóa bi quan**, kết quả đúng: bán {b_['so_ve_da_ban']} vé, còn {b_['so_ghe_con_lai']} ghế, "
        f"{b_['so_het_ve']} khách nhận thông báo hết vé. Biểu đồ ({H_('dv_bq_tl')}) cho thấy các giao tác xếp hàng: "
        "đoạn đỏ rất dài vì mỗi khách giữ khóa suốt thời gian cân nhắc. Bảng khóa lấy mẫu từ performance_schema "
        f"({H_('dv_bq_khoa')}) cho thấy nhiều khách cùng chờ khóa `X,REC_NOT_GAP` trên bản ghi khóa chính 1 của "
        f"bảng chuyen_bay. Tổng thời gian chờ khóa là {so(b_['tong_thoi_gian_cho_khoa_ms'])} ms.",
    )
    B.hinh("dv_bq_tl", "dv_bi_quan_dong_thoi_gian.png", "Diễn biến khi dùng khóa bi quan: các giao tác xếp hàng", 16.0)
    B.hinh("dv_bq_khoa", "dv_bi_quan_bang_khoa.png", "Các khóa InnoDB lấy mẫu trong lúc chạy khóa bi quan", 16.0)
    l_ = dv["lac_quan"]
    n_ = dv["nguyen_tu"]
    B.p(
        f"Với **khóa lạc quan**, dữ liệu cũng đúng ({l_['so_ve_da_ban']} vé) nhưng có tới "
        f"**{l_['so_lan_thu_lai']} lần thử lại** do va chạm version ({H_('dv_lq_tl')}): mỗi đoạn ngắn trên biểu đồ là "
        f"một lần thử, kết thúc bằng ROLLBACK. Với **UPDATE nguyên tử**, kết quả đúng và nhanh nhất – "
        f"{so(n_['thoi_gian_ms'])} ms ({H_('dv_nt_kq')}) – vì không có khe hở giữa đọc và ghi, và khóa chỉ được "
        "giữ trong thời gian rất ngắn.",
    )
    B.hinh("dv_lq_tl", "dv_lac_quan_dong_thoi_gian.png", "Diễn biến khi dùng khóa lạc quan: nhiều lần thử lại", 16.0)
    B.hinh("dv_nt_kq", "dv_nguyen_tu_ket_qua.png", "Kết quả khi dùng UPDATE nguyên tử", 16.0)
    d_ = dv["deadlock"]
    B.p(
        f"Ở chế độ **deadlock** với {d_['so_khach']} khách, InnoDB phát hiện vòng chờ và hủy {d_['so_deadlock']} "
        f"giao tác (đoạn màu đỏ sẫm trên biểu đồ, {H_('dv_dl_tl')}); nhật ký câu lệnh ghi lại lỗi 1213 mà MySQL "
        f"trả về ({H_('dv_dl_log')}).",
    )
    B.hinh("dv_dl_tl", "dv_deadlock_dong_thoi_gian.png", "Diễn biến kịch bản deadlock: InnoDB hủy giao tác nạn nhân", 16.0)
    B.hinh("dv_dl_log", "dv_deadlock_nhat_ky.png", "Nhật ký câu lệnh SQL của kịch bản deadlock", 16.0)
    B.bang("kq_dv", f"Kết quả một lần chạy với {k['so_khach']} khách, {k['tong_ghe']} ghế, cân nhắc {k['think_ms']} ms",
           ["Cách xử lý", "Vé bán", "Bán vượt", "Ghế còn", "Nhất quán", "Thử lại", "Chờ khóa", "Thời gian"],
           [[TEN_CACH[r["che_do"]], str(r["so_ve_da_ban"]), str(r["ban_vuot"]),
             str(r["so_ghe_con_lai"]), "Có" if r["nhat_quan"] else "Không", str(r["so_lan_thu_lai"]),
             str(r["so_lan_cho_khoa"]), so(r["thoi_gian_ms"]) + " ms"]
            for r in (dv["khong_khoa"], dv["bi_quan"], dv["lac_quan"], dv["nguyen_tu"])],
           [3.6, 1.6, 1.8, 1.7, 2.0, 1.7, 1.9, 2.2], can=["l", "c", "c", "c", "c", "c", "c", "c"])

    # ------------------------------------------------ tab 3
    B.h3("3.2.9. Chức năng ma trận mức cô lập")
    B.p(
        "**Tên chức năng:** Ma trận mức cô lập (tab 3). **Chức năng:** chạy 6 thí nghiệm hai phiên ở cả 4 mức cô "
        "lập (24 lần chạy) và lập ma trận cho biết hiện tượng nào thực sự xảy ra, đặt cạnh lý thuyết chuẩn SQL "
        f"({H_('cl_mt')}). Ô viền nét đứt màu cam là chỗ MySQL khác lý thuyết. Bấm vào một ô để xem chi tiết thí "
        "nghiệm từng bước, kèm bảng khóa tại lúc có phiên bị chặn.",
    )
    B.hinh("cl_mt", "cl_ma_tran.png", "Ma trận 6 hiện tượng × 4 mức cô lập đo trên MySQL", 15.5)
    ten_tn = {"doc_rac": "Đọc dữ liệu rác", "doc_khong_lap_lai": "Đọc không lặp lại",
              "bong_ma": "Bóng ma (đọc thường)", "bong_ma_doc_khoa": "Bóng ma (đọc có khóa)",
              "mat_cap_nhat": "Mất cập nhật", "doc_nhat_quan": "Đọc nhất quán ≠ đọc hiện hành"}
    dong_mt = []
    for ma_tn, hang in mt["bang"].items():
        o = []
        for muc in mt["cac_muc"]:
            c = hang[muc]
            if c["xay_ra"] is None:
                s = "?"
            elif ma_tn == "doc_nhat_quan":
                s = "Khác nhau" if c["xay_ra"] else "Giống nhau"
            else:
                s = "Xảy ra" if c["xay_ra"] else "Không"
            if c["khac_ly_thuyet"]:
                s += " *"
            if c["co_deadlock"]:
                s += " (deadlock)"
            elif c["co_chan"] and not c["xay_ra"]:
                s += " (chặn)"
            o.append(s)
        dong_mt.append([ten_tn.get(ma_tn, ma_tn)] + o)
    B.bang("ma_tran", "Kết quả ma trận đo trên MySQL (* = khác lý thuyết chuẩn SQL)",
           ["Hiện tượng", "READ UNCOMMITTED", "READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE"],
           dong_mt, [4.3, 3.0, 3.0, 3.1, 3.1], can=["l", "c", "c", "c", "c"])
    B.p(
        "Ma trận cho thấy ba điểm MySQL/InnoDB khác lý thuyết, đều ở mức REPEATABLE READ: (1) bóng ma khi đọc "
        "thường **không** xảy ra vì đọc nhất quán dùng snapshot; (2) bóng ma khi đọc có khóa cũng **không** xảy ra "
        "vì next-key lock chặn lệnh chèn; (3) mất cập nhật **vẫn xảy ra** vì UPDATE không kiểm tra xung đột ghi. "
        "Ở SERIALIZABLE, mất cập nhật được ngăn bằng khóa chết: cả hai giao tác cùng giữ khóa S rồi cùng xin nâng "
        "lên khóa X, InnoDB phải hủy một bên. Hàng cuối cho thấy ở REPEATABLE READ, trong cùng một giao tác, SELECT "
        "thường và SELECT … FOR UPDATE có thể trả về hai giá trị khác nhau – lý do khóa bi quan phải dùng FOR "
        "UPDATE ngay từ lần đọc đầu tiên.",
        f"{H_('cl_gap')} là chi tiết thí nghiệm bóng ma có khóa ở REPEATABLE READ. Bảng khóa tại bước B bị chặn "
        "là bằng chứng trực tiếp cho gap lock: A giữ `X` (next-key) trên các bản ghi `(1, 1)`, `(1, 2)`, `(1, 3)` "
        "của chỉ mục `fk_ve_chuyen` và `X,GAP` trên bản ghi `(2, 4)`, còn B chờ khóa `X,GAP,INSERT_INTENTION` trên "
        "đúng khoảng đó – khớp hoàn toàn với {H:khoa_chi_muc}.",
    )
    B.hinh("cl_gap", "cl_bong_ma_rr.png", "Chi tiết thí nghiệm bóng ma có khóa ở REPEATABLE READ: B bị gap lock chặn", 12.0)

    # ------------------------------------------------ tab 4
    B.h3("3.2.10. Chức năng so sánh hiệu năng")
    dk = ss["dieu_kien"]
    B.p(
        "**Tên chức năng:** So sánh hiệu năng (tab 4). **Chức năng:** chạy cả bốn cách xử lý trong cùng điều kiện, "
        f"lặp lại nhiều lần rồi lấy trung bình ({H_('ss')}); phần khảo sát tăng dần số khách để thấy chi phí của "
        f"từng cách khi tranh chấp tăng ({H_('ks')}). Kết quả với {dk['so_khach']} khách, {dk['ton_kho']} ghế, cân "
        f"nhắc {dk['think_ms']} ms, lặp {dk['so_lan']} lần được tổng hợp ở {B_('ss_bang')}.",
    )
    B.hinh("ss", "ss_ket_qua.png", "So sánh bốn cách xử lý tranh chấp", 16.0)
    tenss = {"khong_khoa": "Không dùng khóa", "bi_quan": "Khóa bi quan", "lac_quan": "Khóa lạc quan",
             "nguyen_tu": "UPDATE nguyên tử"}
    B.bang("ss_bang", "Kết quả trung bình của bốn cách xử lý",
           ["Cách xử lý", "Thời gian TB", "Nhanh – chậm nhất", "Vé bán TB", "Bán vượt TB", "Lần cho kết quả sai",
            "Thử lại TB", "Chờ khóa TB"],
           [[tenss[m], so(r["thoi_gian_tb"]) + " ms", f"{so(r['thoi_gian_min'])} – {so(r['thoi_gian_max'])} ms",
             so(r["ve_ban_tb"], 1), so(r["ban_vuot_tb"], 1), f"{r['so_lan_sai']} / {r['so_lan_chay']}",
             so(r["thu_lai_tb"], 1), so(r["cho_khoa_tb"], 1)] for m, r in ss["ket_qua"].items()],
           [3.2, 2.0, 2.7, 1.7, 1.8, 2.0, 1.6, 1.6], can=["l", "c", "c", "c", "c", "c", "c", "c"])
    B.hinh("ks", "ks_ket_qua.png", "Khảo sát chịu tải khi số khách tăng dần", 16.0)
    dong_ks = []
    for i, muc in enumerate(ks["cac_muc"]):
        h = [str(muc), str(ks["chuoi"]["khong_khoa"][i]["ton_kho"])]
        for m in ("khong_khoa", "bi_quan", "lac_quan", "nguyen_tu"):
            r = ks["chuoi"][m][i]
            s = so(r["thoi_gian_ms"]) + " ms"
            if m == "khong_khoa":
                s += f"\nvượt {r['ban_vuot']}"
            elif m == "bi_quan":
                s += f"\nchờ {r['cho_khoa']}"
            elif m == "lac_quan":
                s += f"\nthử lại {r['thu_lai']}" + (f", bỏ cuộc {r['bo_cuoc']}" if r["bo_cuoc"] else "")
            h.append(s)
        dong_ks.append(h)
    B.bang("ks_bang", f"Khảo sát chịu tải (cân nhắc {ks['think_ms']} ms; số ghế bằng một nửa số khách)",
           ["Số khách", "Số ghế", "Không khóa", "Khóa bi quan", "Khóa lạc quan", "UPDATE nguyên tử"],
           dong_ks, [1.8, 1.6, 3.2, 3.2, 3.6, 3.1], can=["c", "c", "c", "c", "c", "c"])
    kk, bq, lq, nt = (ss["ket_qua"][m] for m in ("khong_khoa", "bi_quan", "lac_quan", "nguyen_tu"))
    cuoi = ks["chuoi"]
    B.p(
        f"Từ số liệu có thể rút ra: (1) không dùng khóa nhanh nhưng **sai ở mọi lần chạy** ({kk['so_lan_sai']}/"
        f"{kk['so_lan_chay']}), bán vượt trung bình {so(kk['ban_vuot_tb'], 1)} vé; (2) trong các cách cho kết quả "
        f"đúng, **UPDATE nguyên tử nhanh nhất** ({so(nt['thoi_gian_tb'])} ms) và nên là lựa chọn mặc định khi điều "
        f"kiện viết được trong một câu lệnh; (3) khóa bi quan ({so(bq['thoi_gian_tb'])} ms) chậm vì các giao tác "
        f"phải xếp hàng suốt thời gian cân nhắc; (4) khóa lạc quan ({so(lq['thoi_gian_tb'])} ms) không phải chờ "
        f"khóa lâu nhưng phải thử lại trung bình {so(lq['thu_lai_tb'], 1)} lần, và khi tranh chấp tăng lên "
        f"{ks['cac_muc'][-1]} khách thì số lần thử lại lên tới {cuoi['lac_quan'][-1]['thu_lai']}"
        + (f", có {cuoi['lac_quan'][-1]['bo_cuoc']} khách bỏ cuộc" if cuoi['lac_quan'][-1]['bo_cuoc'] else "")
        + ". Khóa lạc quan chỉ phù hợp khi xung đột hiếm.",
    )

    # ---------------------------------------------------------------- 3.3 kiểm thử
    B.h2("3.3. Kiểm thử và triển khai")
    B.p(
        "Vì thứ cần kiểm chứng chính là hành vi khóa của InnoDB, bộ kiểm thử **không dùng dữ liệu giả lập** mà "
        "chạy trực tiếp trên MySQL trong container. Bộ kiểm thử gồm 151 trường hợp chia thành bốn nhóm "
        f"({B_('kiem_thu')}) và đã được chạy lặp lại nhiều lần để loại trừ kiểm thử chập chờn. Lần chạy gần nhất "
        "cho kết quả **151/151 đạt** trong khoảng 45 giây.",
    )
    B.bang("kiem_thu", "Các nhóm kiểm thử tự động", ["Tệp kiểm thử", "Số ca", "Nội dung kiểm tra"], [
        ["tests/test_xungdot.py", "56", "10 kịch bản sai/đúng cho đúng kết quả; mỗi bước có ảnh chụp dữ liệu và khóa; dòng "
                                         "đang sửa dở luôn có đúng một chủ khóa X; chủ khóa đúng sau khóa chết."],
        ["tests/test_phongthinghiem.py", "37", "24 ô của ma trận mức cô lập; bất biến của bộ điều phối hai phiên; "
                                               "gap lock xuất hiện ở REPEATABLE READ."],
        ["tests/test_kichban.py", "39", "Tính đúng đắn của từng cách đặt vé ở nhiều quy mô (1–60 khách); tính loại trừ "
                                        "của khóa X; hồi quy lỗi bộ đệm innodb_trx."],
        ["tests/test_api.py", "19", "Kiểm tra tham số, mã lỗi, chặn hai lượt chạy song song (mã 409)."],
    ], [4.6, 1.6, 10.3], can=["l", "c", "l"])
    B.p(
        "Về triển khai, toàn bộ hệ thống được đóng gói bằng Docker Compose gồm hai dịch vụ `mysql` (image "
        f"mysql:9.6, cổng 3310) và `app` (Python 3.13, cổng 8010). Mã nguồn được chia sẻ trên GitHub tại {REPO}. "
        "Thành viên nhóm chỉ cần cài Docker Desktop, tải mã nguồn về và nhấp đúp các tệp sau:",
    )
    B.ds(
        "`khoi-dong.bat` – tự mở Docker Desktop nếu chưa chạy, khởi động MySQL và ứng dụng, chờ sẵn sàng rồi mở "
        "trình duyệt tại http://localhost:8010.",
        "`chay-test.bat` – khởi động hệ thống (nếu cần) và chạy toàn bộ 151 kiểm thử, báo ĐẠT hoặc chỉ ra ca lỗi.",
        "`dung.bat` – tắt hệ thống, cho MySQL tối đa 60 giây để ghi hết dữ liệu xuống đĩa; dữ liệu được giữ lại "
        "cho lần sau.",
    )
    B.p("Trong quá trình kiểm tra toàn bộ giao diện để chụp ảnh cho báo cáo, nhóm phát hiện và sửa thêm một số "
        "lỗi hiển thị: ô ma trận mức cô lập bị dồn vào một cột do một quy tắc CSS dùng chung tên lớp; bảng khóa "
        "bị bóp méo trong một cột hẹp; cột khóa trong khung CSDL bị cắt ở bảng nhiều cột; nhãn trên biểu đồ diễn "
        "biến khó đọc trên nền tối. Tất cả đã được sửa và đưa lên kho mã nguồn.")

    B.h2("3.4. Đánh giá và những phát hiện về MySQL/InnoDB")
    B.p("Qua thực nghiệm, nhóm rút ra những điểm đáng chú ý sau – nhiều điểm khác với lý thuyết chuẩn SQL hoặc ít "
        "được đề cập trong giáo trình:")
    B.ds(
        "**REPEATABLE READ của MySQL chặn được bóng ma** (chuẩn SQL không yêu cầu), nhờ MVCC cho đọc thường và "
        "next-key lock cho đọc có khóa.",
        "**REPEATABLE READ của MySQL không chặn được mất cập nhật.** UPDATE luôn ghi lên bản mới nhất mà không "
        "kiểm tra dòng đã bị sửa sau snapshot. Tệ hơn, khi giá trị ghi trùng giá trị cũ, MySQL chỉ báo "
        "`Rows matched: 1, Changed: 0`, ứng dụng không có cách nào biết dữ liệu vừa bị mất.",
        "**Ở SERIALIZABLE, mất cập nhật được ngăn bằng khóa chết**: hai bên cùng giữ khóa S rồi cùng xin nâng lên "
        "khóa X; ứng dụng phải sẵn sàng bắt lỗi 1213 và chạy lại.",
        "**Gap lock quan sát được tận mắt**: ở REPEATABLE READ, A giữ `X,GAP` trên bản ghi chỉ mục `(2, 4)`, B chờ "
        "`X,GAP,INSERT_INTENTION` trên đúng khoảng đó; ở READ COMMITTED không có gap lock nên B chèn được.",
        "**INSERT không đơn nguyên ở mức vật lý**: khi INSERT của B bị chặn, dòng mới đã nằm trong chỉ mục chính "
        "(đọc ở READ UNCOMMITTED đã thấy), chỉ đang kẹt ở chỉ mục phụ.",
        "**Dòng mới chèn chỉ có khóa ngầm** (implicit lock): mã giao tác được ghi ngay trong dòng, `data_locks` "
        "không liệt kê cho tới khi có giao tác khác đụng vào.",
        "**Ở REPEATABLE READ, UPDATE giữ khóa cả trên dòng không khớp điều kiện**: trong kịch bản khóa chết đúng, "
        "B vẫn giữ khóa X trên ghế 12A dù `Rows matched: 0`.",
    )
    B.p("Đối chiếu với mục tiêu ở Chương 1, ứng dụng đã tái hiện đủ năm xung đột với kịch bản sai/đúng, đo đạc "
        "được bốn cách xử lý tranh chấp, lập được ma trận mức cô lập và chỉ ra chính xác những điểm MySQL khác lý "
        "thuyết; mọi kết quả đều kiểm chứng được bằng bộ kiểm thử tự động.")

    # ==================================================================== KẾT LUẬN
    B.h1("KẾT LUẬN")
    B.p("**Kết quả đạt được.** Đề tài đã hệ thống hóa lý thuyết điều khiển truy xuất đồng thời – giao tác, lịch "
        "giao tác, các hiện tượng bất thường, kỹ thuật khóa, giao thức khóa hai pha, MVCC, mức cô lập – và làm "
        "rõ cách MySQL/InnoDB cài đặt các kỹ thuật đó. So với mục tiêu đề ra, nhóm đã xây dựng hoàn chỉnh ứng dụng "
        "minh họa với bốn chức năng: năm cặp kịch bản xung đột sai/đúng có hoạt hình lịch giao tác và bảng khóa "
        "thật; mô phỏng tới 60 khách đặt vé đồng thời với bốn cách xử lý; ma trận 24 thí nghiệm mức cô lập; so "
        "sánh và khảo sát hiệu năng. Hệ thống chạy được bằng một cú nhấp nhờ Docker và được bảo đảm bởi 151 kiểm "
        "thử tự động trên MySQL thật.",
        "So với các tài liệu chỉ trình bày bảng mức cô lập theo lý thuyết, đóng góp nổi bật của đề tài là **kiểm "
        "chứng bằng thực nghiệm** và chỉ ra những điểm MySQL khác chuẩn SQL: REPEATABLE READ chặn được bóng ma "
        "nhưng không chặn được mất cập nhật, SERIALIZABLE ngăn mất cập nhật bằng khóa chết, cùng các chi tiết về "
        "gap lock, khóa ngầm và những bẫy khi giám sát khóa qua performance_schema.",
        "**Bài học kinh nghiệm.** Không nên tin rằng “có giao tác là dữ liệu đúng”: cần chọn kỹ thuật phù hợp với "
        "từng nghiệp vụ. Khi điều kiện viết được trong một câu lệnh, UPDATE nguyên tử là lựa chọn đúng và nhanh "
        "nhất; khi phải đọc rồi mới quyết định, cần khóa bi quan bằng FOR UPDATE ngay từ lần đọc đầu; khóa lạc "
        "quan chỉ phù hợp khi tranh chấp hiếm. Mọi giao tác nên xin khóa theo một thứ tự thống nhất, và ứng dụng "
        "luôn phải sẵn sàng xử lý lỗi 1213, 1205 bằng cách chạy lại giao tác. Về mặt kỹ thuật, nhóm cũng học được "
        "cách điều phối nhiều kết nối song song và cách đọc đúng thông tin khóa của InnoDB.",
        "**Hạn chế.** Đề tài mới khảo sát MySQL trên một máy chủ đơn; chưa xét các hiện tượng phức tạp hơn như "
        "lệch ghi (write skew), chưa so sánh với hệ quản trị khác và chưa đo hiệu năng ở quy mô lớn.",
        "**Hướng phát triển.** Trước mắt, có thể bổ sung kịch bản lệch ghi và kịch bản thứ tự khóa trên nhiều "
        "bảng, cho phép người dùng tự soạn kịch bản hai phiên ngay trên giao diện, và xuất lịch giao tác ra tệp để "
        "đưa vào bài giảng. Về lâu dài, ứng dụng có thể mở rộng sang PostgreSQL (vốn phát hiện xung đột ghi ở "
        "REPEATABLE READ) để so sánh trực tiếp hai cách cài đặt mức cô lập, khảo sát hành vi đồng thời trên hệ "
        "thống nhân bản, và tích hợp vào bài giảng thực hành của học phần.",
    )

    # ==================================================================== TÀI LIỆU
    B.h1("DANH MỤC TÀI LIỆU THAM KHẢO")
    B.khoi.append(("tltk", [
        "[1] A. Silberschatz, H. F. Korth, and S. Sudarshan, *Database System Concepts*, 7th ed. New York, NY, USA: "
        "McGraw-Hill Education, 2019.",
        "[2] R. Elmasri and S. B. Navathe, *Fundamentals of Database Systems*, 7th ed. Boston, MA, USA: Pearson, 2016.",
        "[3] H. Berenson, P. Bernstein, J. Gray, J. Melton, E. O'Neil, and P. O'Neil, “A critique of ANSI SQL "
        "isolation levels,” in *Proc. ACM SIGMOD Int. Conf. Management of Data*, San Jose, CA, USA, 1995, pp. 1–10. "
        "DOI: 10.1145/223784.223785.",
        "[4] Oracle Corporation, “InnoDB Locking,” *MySQL Reference Manual*. [Online]. Available: "
        "https://dev.mysql.com/doc/refman/en/innodb-locking.html (truy cập 10/2026).",
        "[5] ISO/IEC 9075-2:2016, *Information technology — Database languages — SQL — Part 2: Foundation "
        "(SQL/Foundation)*. Geneva, Switzerland: ISO, 2016.",
        "[6] J. Gray and A. Reuter, *Transaction Processing: Concepts and Techniques*. San Francisco, CA, USA: "
        "Morgan Kaufmann, 1993.",
        "[7] P. A. Bernstein, V. Hadzilacos, and N. Goodman, *Concurrency Control and Recovery in Database Systems*. "
        "Reading, MA, USA: Addison-Wesley, 1987.",
        "[8] Oracle Corporation, “Consistent Nonlocking Reads” và “Locking Reads,” *MySQL Reference Manual*. "
        "[Online]. Available: https://dev.mysql.com/doc/refman/en/innodb-consistent-read.html (truy cập 10/2026).",
        "[9] Oracle Corporation, “InnoDB Multi-Versioning,” *MySQL Reference Manual*. [Online]. Available: "
        "https://dev.mysql.com/doc/refman/en/innodb-multi-versioning.html (truy cập 10/2026).",
        "[10] Oracle Corporation, “Deadlocks in InnoDB,” *MySQL Reference Manual*. [Online]. Available: "
        "https://dev.mysql.com/doc/refman/en/innodb-deadlocks.html (truy cập 10/2026).",
        "[11] Oracle Corporation, “The data_locks Table,” *MySQL Reference Manual*. [Online]. Available: "
        "https://dev.mysql.com/doc/refman/en/performance-schema-data-locks-table.html (truy cập 10/2026).",
        "[12] S. Ramírez, “FastAPI Documentation.” [Online]. Available: https://fastapi.tiangolo.com (truy cập 10/2026).",
        "[13] Docker Inc., “Docker Compose Documentation.” [Online]. Available: https://docs.docker.com/compose/ "
        "(truy cập 10/2026).",
    ]))

    # ==================================================================== PHỤ LỤC
    B.h1("PHỤ LỤC")
    B.h2("Phụ lục A. Hướng dẫn cài đặt và chạy")
    B.ds(
        "Cài Docker Desktop (Windows 10/11) và mở nó lên một lần.",
        f"Tải mã nguồn: `git clone {REPO}.git` (hoặc tải tệp ZIP từ GitHub và giải nén).",
        "Nhấp đúp `khoi-dong.bat`. Lần đầu cần vài phút để tải image MySQL và Python; các lần sau chỉ vài giây.",
        "Trình duyệt tự mở http://localhost:8010. Muốn chạy kiểm thử: nhấp đúp `chay-test.bat` (không thao tác trên "
        "giao diện trong lúc chạy kiểm thử). Muốn tắt: nhấp đúp `dung.bat`.",
        "Có thể kết nối trực tiếp tới MySQL của demo tại cổng 3310, tài khoản root / demo123, CSDL demo_dongthoi.",
    )
    B.h2("Phụ lục B. Lược đồ cơ sở dữ liệu (schema.sql)")
    B.ma("""
CREATE TABLE chuyen_bay (
    ma_chuyen    INT PRIMARY KEY,
    so_hieu      VARCHAR(100)  NOT NULL,             -- ví dụ: VN-808
    tong_ghe     INT           NOT NULL,
    so_ghe_trong INT           NOT NULL,
    version      INT           NOT NULL DEFAULT 0    -- phục vụ khóa lạc quan
) ENGINE=InnoDB;

CREATE TABLE ve (
    ma_ve      INT AUTO_INCREMENT PRIMARY KEY,
    ma_chuyen  INT          NOT NULL,
    hanh_khach VARCHAR(50)  NOT NULL,
    thoi_diem  DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_ve_chuyen FOREIGN KEY (ma_chuyen)
        REFERENCES chuyen_bay(ma_chuyen)
) ENGINE=InnoDB;

CREATE TABLE ghe (
    ma_ghe      INT PRIMARY KEY,
    ma_chuyen   INT          NOT NULL,
    so_ghe      VARCHAR(10)  NOT NULL,                -- ví dụ: 12A
    trang_thai  VARCHAR(20)  NOT NULL DEFAULT 'trong',
    nguoi_giu   VARCHAR(50)  NULL,
    CONSTRAINT fk_ghe_chuyen FOREIGN KEY (ma_chuyen)
        REFERENCES chuyen_bay(ma_chuyen)
) ENGINE=InnoDB;
""")
    B.h2("Phụ lục C. Cấu trúc mã nguồn")
    B.ma("""
hequantricosodemodongthoi/
├── docker-compose.yml     # MySQL 9.6 + ứng dụng
├── Dockerfile
├── schema.sql             # tạo CSDL (chạy tự động lần đầu)
├── khoi-dong.bat · chay-test.bat · dung.bat
├── app/
│   ├── csdl.py            # kết nối, mức cô lập, khóa "một kịch bản mỗi lúc"
│   ├── kichban.py         # nhiều khách đặt vé, theo dõi khóa, hiệu năng
│   ├── phongthinghiem.py  # bộ điều phối hai phiên A/B + ma trận mức cô lập
│   ├── xungdot.py         # 5 xung đột × 2 kịch bản sai/đúng
│   ├── main.py            # API FastAPI
│   └── static/            # giao diện (HTML, CSS, JS cho từng tab)
├── tests/                 # 151 kiểm thử chạy trên MySQL thật
└── bao-cao/               # báo cáo, công cụ chụp ảnh và vẽ sơ đồ
""", "text")
    return B


# tham chiếu dùng trong f-string (không dùng được {H:...} vì trùng cú pháp f-string)
def H_(khoa):
    return "{H:" + khoa + "}"


def B_(khoa):
    return "{B:" + khoa + "}"
