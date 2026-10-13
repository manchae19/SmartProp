# Rà soát nhãn 296 tin căn hộ Đà Nẵng

Đợt rà soát ngày 11/10/2026 tập trung vào bộ căn hộ đã dùng cho baseline và thí nghiệm
Singapore. Đây là bước kiểm tra chất lượng nhãn, chưa phải bộ dữ liệu đã xác minh sạch.
Không áp dụng thay đổi vào dữ liệu thô hoặc huấn luyện lại mô hình trong đợt này.

Kết quả: **64 tin cần duyệt**, **232 tin chưa có cờ theo quy tắc**. Đã tải và xác minh
đúng trang chi tiết của toàn bộ 64 tin cần duyệt; cả 64 trang trả HTTP 200 và lấy được
nhãn giá, diện tích, vùng mô tả theo cấu trúc dự kiến. Trong nhóm cần duyệt có 27 tin
lệch giá giữa tiêu đề và nhãn, 23 tin lệch giá giữa mô tả và nhãn, 12 tin tổng giá dưới
500 triệu, 1 tin tiêu đề cho thuê. Các con số chồng lặp, không cộng để suy ra số tin.
Không có chênh lệch giá/diện tích giữa nhãn chi tiết hiện tại và snapshot ở 64 tin này;
các mâu thuẫn nội dung vẫn cần giải quyết trước khi dùng làm nhãn tổng giá đáng tin.

## Phạm vi và cách đọc kết quả

- 296 tin đại diện nhóm nghi trùng: 58 CafeLand, 238 Nhadat24h.
- Kiểm tra toàn bộ 296 tin bằng tiêu đề, giá/diện tích thô và giá/diện tích chuẩn hóa.
- Ưu tiên tải lại trang chi tiết cho các tin có cờ, lưu nguyên HTML và manifest để đối chiếu.
  Số trang và trạng thái đối chiếu chính xác nằm trong `summary.json`.
- `all_apartments_audit.csv`: toàn bộ 296 tin, giữ nhãn cũ và bằng chứng.
- `needs_review.csv`: tin có ít nhất một cờ cần giải quyết; các cờ có thể chồng lặp.
- `unflagged_candidates.csv`: tin chưa bị quy tắc đánh dấu, **không đồng nghĩa đã sạch**.
  Mô tả chi tiết của nhóm này chưa được lấy lại trong đợt kiểm tra ưu tiên.
- `review.html`: xem bằng trình duyệt, tìm theo ID/tiêu đề/lý do; liên kết tách khỏi CSV
  để tránh IDE tự ghép dấu phẩy và trường kế tiếp vào URL.

## Quy tắc

1. Đối chiếu giá tổng theo đơn vị tỷ/triệu và diện tích m² với nhãn đã chuẩn hóa.
2. Ưu tiên duyệt tổng giá dưới 500 triệu, đơn giá ngoài 15–150 triệu/m²,
   diện tích ngoài 25–200m². Đây là ngưỡng rà soát thử nghiệm, không phải khẳng định
   mặt bằng giá thị trường; không xóa tin chỉ vì vượt ngưỡng.
3. Phân biệt số tiền trong tiêu đề/mô tả: tổng giá, giá thuê/dòng tiền, khoản giảm giá,
   thanh toán/trả trước/giá khởi điểm, giá theo m² và giá giới hạn như “chưa tới”.
4. Giá tổng nêu trong tiêu đề lệch nhãn trên 10% hoặc diện tích lệch trên 5% có cờ.
   Số tiền thuê, khoản giảm giá và giá giới hạn không được coi là tổng giá chính xác.
5. Tiêu đề bắt đầu “cho thuê”, dấu hiệu condotel/dịch vụ, nhiều căn/giỏ hàng được duyệt riêng.
6. Với trang tải lại: kiểm tra host, ID trên URL, tiêu đề tương đồng; lấy nhãn giá/diện tích
   và vùng mô tả cụ thể của tin. Không lấy giá ở tin gợi ý, bảng tìm kiếm hay công cụ vay.
   Ghi riêng nhãn hiện tại khác snapshot, trang không truy cập được, cấu trúc không xác minh.
7. Giá tổng trong mô tả không khớp nhãn được giữ dưới dạng bằng chứng nghi vấn.
   Nếu mô tả nhiều căn hoặc nhiều giá, chưa chọn một giá để thay thế tự động.

Chưa phân tích đầy đủ mọi cách viết tiền Việt: số viết bằng chữ, ký hiệu không chuẩn,
đơn vị chen ký tự, khoảng giá, ngữ cảnh xa và nhiều căn có thể bị bỏ sót hoặc gắn cờ nhầm.
Nội dung mô tả và các đoạn bằng chứng được giữ để người duyệt kiểm tra.

## Hai trường hợp đã đối chiếu

- `nhadat24h:4395745`: giá thô và nhãn chi tiết cùng là **189 triệu**; tiêu đề ghi
  **2,7 tỷ**, mô tả cũng ghi **2,7 tỷ** và điều kiện thanh toán sớm. Dấu hiệu mâu thuẫn
  nằm trên nguồn, chưa thể quy kết lỗi crawler. Giá gốc vẫn giữ 189 triệu; cần xác nhận
  tổng giá và điều kiện trước khi sửa nhãn trong bộ dữ liệu phiên bản tiếp theo.
- `cafeland:2157463`: nhãn **1,2 tỷ**, tiêu đề “Thanh toán 1.2TY”; mô tả nêu **4,120 tỷ**
  và nhiều căn khác trong giỏ hàng. Chưa đủ căn cứ xác định 1,2 tỷ là tổng giá hay phần
  thanh toán, hoặc chọn đúng một giá thay thế từ giỏ hàng. Giữ lại để duyệt.

## Quy trình duyệt tiếp theo

Tạo bản sao `needs_review.csv` trước khi ghi quyết định; script sinh báo cáo sẽ ghi lại
các file CSV đầu ra khi chạy lại. Các trường `proposed_price_million`, `proposed_area_sqm`,
`reviewer_decision`, `reviewer_note` đang để trống có chủ đích.

Với từng tin, ghi một quyết định: giữ nhãn; sửa nhãn có bằng chứng; loại khỏi phạm vi
căn hộ bán; hoặc chưa đủ thông tin. Nếu sửa, ghi giá triệu VNĐ/diện tích m², bằng chứng
và điều kiện thanh toán. Không suy giá từ dự đoán mô hình, trung vị khu vực hoặc giá căn khác.
Tin không đủ căn cứ phải được giữ trạng thái chờ xử lý, chưa đưa trở lại tập sạch.

Chỉ sau khi xử lý nhãn mới chốt phiên bản dữ liệu sạch và xây dựng đánh giá mới.
Tập test 26 căn hiện tại đã được xem trong phân tích trước; không gọi nó là tập test
độc lập mới sau khi thay quy tắc. Cần kế hoạch test theo thời gian, ưu tiên dữ liệu
thu thập mới có ngày đáng tin và không trùng nhóm với train. Không chia lại ngẫu nhiên
chỉ để có kết quả đẹp hơn.

## Tái lập và bảo toàn dữ liệu

```powershell
.\ai-services\.venv\Scripts\python.exe ai-services/app/data/review_apartment_labels.py
.\ai-services\.venv\Scripts\python.exe ai-services/app/data/fetch_apartment_review.py
.\ai-services\.venv\Scripts\python.exe ai-services/app/data/review_apartment_labels.py
.\ai-services\.venv\Scripts\python.exe -m unittest discover -s ai-services/app/data -p test_review_apartment_labels.py
```

Lệnh fetch cần mạng, chỉ tải tin có cờ và bỏ qua ID đã lưu trong manifest; đọc robots.txt,
giãn cách ít nhất 3 giây, dừng khi gặp chặn/CAPTCHA/HTTP 403/429. HTML chỉ là snapshot
hiện tại, không chứng minh nội dung tại ngày thu thập ban đầu. Thời điểm và SHA256
trang được lưu trong `fetch_manifest.json`. Không chạy nhiều tiến trình fetch cùng lúc.

Các SHA256 đầu vào được ghi trong `summary.json` và kiểm tra lại trước khi kết thúc.
`baseline_inputs.csv`, CSV raw và các kết quả thí nghiệm Singapore giữ nguyên.
Không dùng sai số mô hình hoặc dự đoán trên test để chọn tin cần duyệt.
