# Căn hộ Đà Nẵng v2 — xử lý nhóm nghi vấn

Ngày 11/10/2026, đã đọc bằng chứng nguồn của 64 tin bị đánh dấu trong bộ 296 căn hộ:

| Quyết định | Số tin | Xử lý |
|---|---:|---|
| Sửa nhãn theo nguồn | 11 | Giữ giá/diện tích cũ, lưu nhãn mới và bằng chứng |
| Giữ nhãn | 6 | Giải thích cờ nhầm hoặc mức giá cao có căn cứ |
| Loại khỏi phạm vi | 7 | Tin thuê, cả công trình, giỏ hàng/booking, khoản trả trước |
| Chờ xác minh | 40 | Không đưa vào train/validation/test v2 |

V2 có **249 tin = 232 tin chưa có cờ + 17 tin đã xử lý giữ/sửa**.
232 tin chưa được đối chiếu lại toàn bộ mô tả, nên đây là dữ liệu đã sàng lọc phiên bản mới,
**chưa phải 249 tin đã xác minh sạch**. Giá vẫn là giá rao, không phải giá giao dịch.

`needs_review.csv` ở thư mục `apartment_review` đang mở trong IDE đã được điền quyết định,
ghi chú và nhãn đề xuất. Bản sao trước sửa: `review_queue_before.csv`; quyết định có hash
trang và thời điểm tải: `review_decisions.csv`. Bản chốt hàng đợi: `reviewed_queue.csv`.
Chạy lại script rà soát cũ sẽ ghi đè hàng đợi, vì vậy nên dùng bản chốt ở v2 khi duyệt tiếp.

## Ví dụ đã sửa và giữ lại

- `nhadat24h:4386429`: **4.300 → 5.700 triệu**, diện tích **67 → 66,7m²**.
  Mô tả ghi tổng giá 5,7 tỷ = 4,3 tỷ trả trước + 1,4 tỷ còn lại, gồm thuế phí chuyển nhượng.
- `nhadat24h:4393989`: **183 → 9.500 triệu**, **71 → 70,3m²**.
  Mô tả ghi rõ giá bán 9,5 tỷ, còn 40 triệu/tháng là tiền thuê.
- `nhadat24h:4393797`: **3.500 → 4.700 triệu**, tiêu đề và mô tả đồng thuận giá 4,7 tỷ.
- `nhadat24h:4395745`: **189 → 2.700 triệu**, giá tổng quảng cáo khi thanh toán sớm,
  70m² gồm 53,8m² thông thủy và 16,2m² sân vườn. Điều kiện được giữ riêng.
- `nhadat24h:4370936`: giữ **2.400 triệu / 70m²**; “2tỷ4” là 2,4 tỷ.
  Phần 52m² và tổng sử dụng 70m² không được coi là hai căn khác nhau.
- Giữ một số căn cao cấp vượt 150 triệu/m² khi nhãn nguồn nhất quán,
  không loại chỉ vì giá cao và không thay tổng giá bằng dòng tiền cho thuê.

Giá thanh toán nhanh/sớm là **tổng giá quảng cáo theo phương án cụ thể**, khác số tiền
phải đóng riêng một đợt. Các tin có tên/mã căn rõ, tiêu đề khớp tổng giá của phương án
được giữ điều kiện trong `review_terms`. Không tự chia giá trả trước cho tỷ lệ để suy tổng
giá. Tin có nhiều phương án không khớp nhau được cách ly.

Diện tích thông thủy, diện tích nhãn làm tròn và diện tích gồm sân vườn còn khác định nghĩa;
ghi chú được lưu. Chưa có dữ liệu đủ để quy đổi mọi căn về một diện tích chuẩn duy nhất.
Các thay đổi là quyết định dựa trên nội dung rao tại snapshot đã lưu, không chứng minh
quyền sở hữu, báo giá hiện hành hay giao dịch thực tế.

## Baseline đã chạy lại

Giữ nguyên assignment theo nhóm của bản gốc, không chia lại để cải thiện kết quả:
**train 200, validation 25, test 24**. Dữ liệu Singapore không tham gia.
So sánh median giá/m² theo quận và ridge log-price alpha=1; chọn bằng MAE validation.

Mô hình được chọn: **median giá/m² theo quận**.

| Chỉ số trên 24 mẫu test còn lại | Kết quả |
|---|---:|
| MAE | 823,35 triệu VNĐ |
| Median APE | 12,84% |
| MAPE | 23,53% |
| R² | 0,6125 |

**Không so trực tiếp với MAE 895,62 triệu trên 26 mẫu test cũ để kết luận mô hình tốt hơn.**
Đã thay tập đánh giá qua cách ly một số bản ghi và sửa nhãn; test cũ cũng đã được quan sát.
Đây là kết quả khám phá sau xử lý dữ liệu. Chưa triển khai mô hình vào API và chưa có
tập kiểm tra mới theo thời gian. Các kiểm tra nhóm trùng là theo nhóm heuristic cũ,
không chứng minh đã loại hết mọi tin cùng căn có tiêu đề khác nhau.

## Tệp và chạy lại

- `baseline_inputs.csv`: 249 đầu vào căn hộ v2, giữ trường gốc trong `raw_json`;
  `original_price_million` và `original_area_sqm` cho đối chiếu. Giá/diện tích đã sửa ở
  trường chuẩn hóa, đơn giá tính lại từ giá mới/diện tích mới.
- `quarantined.csv`: 47 tin ngoài tập mô hình, gồm 7 loại và 40 chờ xác minh.
- `summary.json`: đối soát số lượng và SHA256, các giới hạn.
- `baseline_metrics.json`, `baseline_models.json`, `baseline_holdout_predictions.csv`:
  kết quả, tham số và dự đoán. Nhà ở/đất không được huấn luyện trong thư mục chỉ căn hộ này.

```powershell
.\ai-services\.venv\Scripts\python.exe ai-services/app/data/finalize_apartment_review.py
.\ai-services\.venv\Scripts\python.exe ai-services/app/data/train_smartprop_baseline.py --input-dir ai-services/app/data/processed/apartment_v2
.\ai-services\.venv\Scripts\python.exe -m unittest discover -s ai-services/app/data -p test_finalize_apartment_review.py
```

Script chốt chỉ áp dụng khi hàng đợi chưa có chỉnh sửa của người dùng. Nếu v2 đã tồn tại,
script kiểm tra đúng bản chốt rồi dừng. Nếu hàng đợi đã thay đổi, cần hòa giải quyết định
trong phiên bản mới, không ghi đè v2. Dữ liệu thô, baseline gốc và thí nghiệm Singapore giữ nguyên.

Bước tiếp theo: xác minh phần mô tả của 232 tin còn lại, xử lý 40 tin đang chờ nếu có bằng
chứng mới; kiểm tra trùng theo dự án/mã căn. Sau đó thu thập tập test mới có thời gian đáng tin
và tách nhóm bất động sản với train để đánh giá cuối cùng.
