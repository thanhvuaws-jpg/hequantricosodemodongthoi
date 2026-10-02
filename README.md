# Demo: Điều khiển truy xuất đồng thời trong MySQL/InnoDB

Ứng dụng minh họa các xung đột khi nhiều giao tác truy xuất đồng thời và cách
InnoDB xử lý chúng, qua nghiệp vụ **đặt vé máy bay** (chuyến VN-808 HAN → SGN).
Mọi kịch bản đều **chạy thật trên MySQL 9.6**. Giao diện chỉ phát lại những gì
đã thực sự xảy ra (câu lệnh, kết quả, dữ liệu, khóa), không có phần nào được giả lập.

Ba bảng dữ liệu (xem `schema.sql`):

| Bảng | Vai trò |
|---|---|
| `chuyen_bay(ma_chuyen, so_hieu, tong_ghe, so_ghe_trong, version)` | số ghế trống của mỗi chuyến – điểm tranh chấp chính |
| `ve(ma_ve, ma_chuyen, hanh_khach, thoi_diem)` | mỗi dòng là một vé đã bán |
| `ghe(ma_ghe, ma_chuyen, so_ghe, trang_thai, nguoi_giu)` | ghế 12A, 12B – dùng cho kịch bản deadlock |

## Dành cho thành viên nhóm: clone về là chạy

Chỉ cần cài **Docker Desktop** (không cần cài Python hay MySQL).

```bash
git clone https://github.com/thanhvuaws-jpg/hequantricosodemodongthoi.git
```

Sau đó vào thư mục vừa clone và nhấp đúp:

| File | Việc làm |
|---|---|
| `khoi-dong.bat` | Bật MySQL 9.6 + ứng dụng rồi mở trình duyệt tại <http://localhost:8010>. Lần đầu mất vài phút để tải image. |
| `chay-test.bat` | Chạy toàn bộ 151 test trên MySQL thật (khoảng 1 phút), báo ĐẠT hoặc chỉ ra test lỗi. |
| `dung.bat` | Tắt demo. Dữ liệu vẫn được giữ cho lần sau. |

Cổng dùng: **8010** (web) và **3310** (MySQL), không đụng MySQL có sẵn trên máy.

## Báo cáo tiểu luận

Thư mục `bao-cao/` chứa báo cáo theo đúng file format của trường (`format tieu luan.docx`):

- `BaoCao_TieuLuan_DieuKhienTruyXuatDongThoi.docx` (và bản `.pdf`) – 74 trang, 43 hình, 17 bảng,
  mục lục và danh mục bảng/hình tự động. Trang bìa còn để trống tên giảng viên, MSSV, lớp và các
  thành viên khác để nhóm tự điền.
- `hinh/` – ảnh chụp giao diện và sơ đồ; `du-lieu/` – số liệu JSON của đúng lần chạy đã chụp.
- `cong-cu/` – công cụ dựng lại báo cáo khi ứng dụng thay đổi (cần ứng dụng đang chạy):

```bash
cd bao-cao/cong-cu && python chup_giao_dien.py && python so_do.py && python tao_bao_cao.py
```

Sau đó chạy `cap_nhat_word.ps1` (hoặc mở file Word, bấm Ctrl+A rồi F9) để cập nhật mục lục và số trang.

## Chạy ứng dụng

Cách nhanh nhất trên Windows: nhấp đúp **`khoi-dong.bat`** (tự mở Docker Desktop nếu
chưa chạy, khởi động MySQL + ứng dụng, rồi mở trình duyệt). Tắt bằng **`dung.bat`**.

Hoặc bằng dòng lệnh:

```bash
docker compose up -d --build
```

Mở trình duyệt tại <http://localhost:8010>.

Khi lược đồ thay đổi, ứng dụng tự tạo lại các bảng từ `schema.sql` lúc khởi động,
nên không cần xóa volume dữ liệu bằng tay.

- MySQL 9.6 chạy trong container, map ra cổng **3310** (không đụng MySQL có sẵn trên máy).
- Tài khoản `root` / `demo123`, cơ sở dữ liệu `demo_dongthoi`.

Các lệnh hữu ích:

```bash
docker compose exec app pytest -q
```

```bash
docker compose down -v
```

```bash
docker exec -it demo_dongthoi_mysql mysql -uroot -pdemo123 demo_dongthoi
```

## Bốn tab của ứng dụng

### 1. Năm xung đột: sai và đúng (phần chính)

Mỗi xung đột có hai kịch bản chạy trên **cùng dữ liệu, cùng thứ tự đan xen**.
Kịch bản ĐÚNG chỉ khác kịch bản SAI đúng một điểm, và điểm đó được đánh dấu
trong code bằng nhãn "← nguyên nhân" / "← cách sửa".

| # | Xung đột | Kịch bản SAI | Kịch bản ĐÚNG | Khác biệt duy nhất |
|---|---|---|---|---|
| 1 | Mất cập nhật | REPEATABLE READ, `SELECT` thường | REPEATABLE READ, `SELECT … FOR UPDATE` | thêm `FOR UPDATE` |
| 2 | Đọc dữ liệu rác | READ UNCOMMITTED | READ COMMITTED | mức cô lập |
| 3 | Đọc không lặp lại | READ COMMITTED | REPEATABLE READ | mức cô lập |
| 4 | Bóng ma | READ COMMITTED + `FOR UPDATE` | REPEATABLE READ + `FOR UPDATE` | mức cô lập (gap lock) |
| 5 | Deadlock | A giữ ghế 12A→12B, B giữ 12B→12A | cả hai giữ 12A→12B | thứ tự khóa |

Màn hình hoạt hình gồm:

- **Lịch giao tác** (bảng giữa): đúng dạng lịch T₁ | T₂ hay vẽ trên bảng. Mỗi hàng
  là một thời điểm `t1, t2…` theo đúng thứ tự MySQL đã thực hiện; cột trái là việc
  của phiên A (quầy vé), cột phải là việc của phiên B (app di động). Kết quả hiện
  ngay dưới từng câu lệnh (giá trị đọc được, `Rows matched / Changed`, lỗi 1213…).
- **Thanh dọc cạnh mỗi cột** = vòng đời giao tác: liền màu là đang mở, đỏ đứt đoạn
  là đang bị chặn chờ khóa. Hai thanh chạy song song chính là hai giao tác đang
  *đồng thời*.
- **Chuỗi ký hiệu lịch** theo giáo trình, ví dụ `r₁(X) r₂(X) w₁(X) c₁ w₂(X) c₂`
  (r đọc, w ghi, xl xin khóa ghi, c commit, a hủy; chỉ số 1 = A, 2 = B).
- **"Chuyện gì vừa xảy ra?"**: giải thích từng bước bằng lời thường.
- **Cơ sở dữ liệu** (cột phải): nội dung bảng tại thời điểm đang xem, ở cả hai góc
  nhìn. Giá trị gạch ngang là bản *đã commit*, giá trị tô vàng là bản nháp *chưa
  commit*. Cột "Khóa" cho biết phiên nào đang giữ / đang chờ khóa gì trên dòng nào.
- **Viên SQL ✈**: bay từ câu lệnh vào CSDL rồi bay về kèm kết quả. Nếu bị chặn,
  viên ⏳ đứng chờ trước cửa cho tới khi InnoDB cho chạy tiếp.

**Vì sao A và B chạy xen kẽ từng bước?** Hai giao tác vẫn *đồng thời* (cùng mở,
chồng lên nhau về thời gian). Nhưng bên trong CSDL, các thao tác trên cùng dữ liệu
luôn diễn ra theo một thứ tự nào đó, gọi là lịch giao tác. Xung đột chỉ xuất hiện
với một số thứ tự xen kẽ nhất định, nên tab này cố định thứ tự để lần nào cũng tái
hiện được. Muốn xem chạy tự do cùng lúc thật sự thì dùng tab 2.

Điều khiển: ▶ Phát / ⏸ Dừng, đi từng bước bằng phím ← →, phím Space để phát/dừng,
bấm vào thanh tiến độ để nhảy tới bước bất kỳ, chọn tốc độ 0,5× / 1× / 2×.
Khi cuộn xuống xem lịch giao tác, bấm **▲ Ẩn thanh trên** (góc trên bên phải) để thanh tiêu đề
không che màn hình; bấm **▼ Hiện thanh trên** để hiện lại.
Khi đã chạy cả hai kịch bản của một xung đột, thẻ **So sánh hai kịch bản** sẽ hiện ra bên dưới.

### 2. Nhiều khách đặt vé

Từ 1 tới 60 khách (mỗi khách là một luồng có kết nối riêng) cùng tranh một số
ghế có hạn. Hỗ trợ bốn cách xử lý: không khóa, khóa bi quan, khóa lạc quan,
UPDATE nguyên tử; và một kịch bản deadlock. Biểu đồ diễn biến có thanh tua thời
gian, chú thích "bị chặn bởi ai", và bảng khóa lấy mẫu mỗi 25 ms.

### 3. Ma trận mức cô lập

Sáu thí nghiệm × bốn mức cô lập = 24 lần chạy, so với lý thuyết chuẩn SQL.

### 4. So sánh hiệu năng

So sánh thời gian, số vé bán vượt, số lần thử lại, số lần chờ khóa của bốn cách
xử lý. Có thêm khảo sát khi số khách tăng dần.

## Kết quả thực nghiệm

### Ma trận mức cô lập (đo trên MySQL 9.6)

| Hiện tượng | RU | RC | RR | S |
|---|---|---|---|---|
| Đọc dữ liệu rác | xảy ra | không | không | không |
| Đọc không lặp lại | xảy ra | xảy ra | không | không |
| Bóng ma (đọc thường) | xảy ra | xảy ra | **không** \* | không |
| Bóng ma (đọc có khóa) | xảy ra | xảy ra | **không** \* | không |
| Mất cập nhật | xảy ra | xảy ra | **xảy ra** \* | không (deadlock) |

\* khác với lý thuyết chuẩn SQL.

### Những phát hiện đáng đưa vào báo cáo

1. **REPEATABLE READ của MySQL chặn được bóng ma** (chuẩn SQL không yêu cầu điều này),
   nhờ MVCC cho đọc thường và next-key lock (khóa dòng + khoảng trống) cho đọc có khóa.
2. **REPEATABLE READ của MySQL không chặn được mất cập nhật**. UPDATE luôn ghi lên
   bản mới nhất, không kiểm tra dòng đó đã bị sửa sau snapshot hay chưa. Tệ hơn, nếu B
   ghi đúng giá trị A vừa ghi thì MySQL chỉ báo `Rows matched: 1, Changed: 0`, nên ứng dụng
   không có cách nào biết mình vừa làm mất dữ liệu.
3. **Ở SERIALIZABLE, mất cập nhật được ngăn bằng deadlock**: hai bên cùng giữ khóa S rồi
   cùng xin nâng lên khóa X, InnoDB phải hủy một bên.
4. **Gap lock thấy được tận mắt**: ở REPEATABLE READ, A giữ `X,GAP` trên bản ghi chỉ mục
   `(2, 4)` và B chờ khóa `X,GAP,INSERT_INTENTION` trên đúng khoảng đó. Ở READ COMMITTED
   không có gap lock nên B chèn được.
5. **INSERT không đơn nguyên ở mức vật lý**: khi INSERT của B bị chặn, dòng mới đã nằm
   trong chỉ mục chính (đọc ở READ UNCOMMITTED đã thấy), chỉ đang kẹt ở chỉ mục phụ.
6. **Dòng mới chèn chỉ có khóa ngầm (implicit lock)**: mã giao tác ghi ngay trong dòng,
   `data_locks` không liệt kê cho tới khi có giao tác khác đụng vào.
7. **Ở REPEATABLE READ, UPDATE giữ khóa cả trên dòng không khớp điều kiện**: trong
   kịch bản deadlock ĐÚNG, B vẫn giữ khóa X trên ghế 12A dù `Rows matched: 0`.
8. **Bẫy khi giám sát khóa** (gặp khi làm demo này):
   - `information_schema.innodb_trx` lấy dữ liệu từ một bộ đệm, chỉ được làm mới khi đã hơn
     0,1 giây không ai đọc. Đọc liên tục sẽ mãi nhận ảnh chụp cũ.
   - `data_lock_waits` liệt kê cả những yêu cầu đang xếp hàng phía trước, không chỉ người
     đang giữ khóa. Phải ghép thêm `data_locks` và lọc `LOCK_STATUS = 'GRANTED'`.
   - Một câu truy vấn trên `performance_schema` không phải ảnh chụp nguyên tử: nó đọc
     từng dòng ở những thời điểm hơi lệch nhau. Nếu chạy trúng lúc khóa đang được chuyển
     giao, có thể thấy cả người giữ cũ lẫn người giữ mới "cùng giữ" một khóa X.
   - `THREAD_ID` trong `data_locks` là luồng đã tạo cấu trúc khóa, không phải chủ sở hữu.
     Khi B bị hủy vì deadlock, khóa được trao cho A lại mang `THREAD_ID` của B. Chủ sở hữu
     thật là `ENGINE_TRANSACTION_ID`.

### So sánh bốn cách đặt vé

Điều kiện: 10 khách, 5 ghế, cân nhắc 100 ms.

| Cách | Vé bán ra | Bán vượt | Nhất quán | Thử lại | Thời gian |
|---|---|---|---|---|---|
| Không khóa | 10 | **5** | **Không** | 0 | ~280 ms |
| Khóa bi quan | 5 | 0 | Có | 0 | ~1100 ms |
| Khóa lạc quan | 5 | 0 | Có | ~30 | ~780 ms |
| UPDATE nguyên tử | 5 | 0 | Có | 0 | ~150 ms |

## Kiểm thử

151 test chạy trên MySQL thật (không dùng mock, vì thứ cần kiểm chứng chính là
hành vi khóa của InnoDB). Bộ test được chạy lặp lại nhiều lần để loại trừ test
chập chờn. Các nhóm test:

- `tests/test_xungdot.py`: 10 kịch bản sai/đúng; mỗi bước đều có ảnh chụp; dòng
  đang sửa dở luôn có đúng một chủ khóa X; chủ khóa đúng sau deadlock.
- `tests/test_phongthinghiem.py`: 24 ô ma trận; bất biến của bộ điều phối hai phiên; gap lock.
- `tests/test_kichban.py`: tính đúng đắn của từng cách đặt vé ở nhiều quy mô (1–60 khách);
  tính loại trừ của khóa X; hồi quy lỗi bộ đệm `innodb_trx`.
- `tests/test_api.py`: kiểm tra tham số, mã lỗi, chặn hai lượt chạy song song (409).

Lưu ý: đừng thao tác trên giao diện trong lúc chạy test, vì hai bên dùng chung cơ sở dữ liệu.

## Cấu trúc mã nguồn

```
demo-dongthoi/
├── docker-compose.yml     # MySQL 9.6 + ứng dụng
├── Dockerfile
├── schema.sql             # tạo CSDL (chạy tự động lần đầu)
├── app/
│   ├── csdl.py            # kết nối, mức cô lập, khóa "một kịch bản mỗi lúc"
│   ├── kichban.py         # nhiều khách đặt vé, theo dõi khóa, so sánh hiệu năng
│   ├── phongthinghiem.py  # bộ điều phối hai phiên A/B + ma trận mức cô lập
│   ├── xungdot.py         # 5 xung đột × 2 kịch bản sai/đúng
│   ├── main.py            # API FastAPI
│   └── static/            # giao diện (HTML, CSS, JS cho từng tab)
└── tests/
```

Phần đáng đọc nhất khi bảo vệ đề tài:

- `app/xungdot.py`: định nghĩa 10 kịch bản, rất ngắn và dễ đọc.
- `thuc_thi_hai_phien()` trong `app/phongthinghiem.py`: cách điều phối hai phiên
  khi một phiên bị chặn (hoãn bước, chạy bù, chụp khóa).
