# SmartProp v3: phân tích lỗi và chuẩn bị kiểm chứng

Phân tích **299 validation**, đối chiếu độ phủ từ **1,435 train**. Dùng đúng dự đoán và nhãn v3 đã chốt; không huấn luyện lại hoặc chấm test.

| Loại | Train | Val | Mô hình chọn | MAE (triệu VND) | MedAPE | APE >50% |
|---|---:|---:|---|---:|---:|---:|
| Nhà ở | 788 | 153 | ridge_log_area_location_alpha_1 | 3,092.0 | 22.1% | 26 |
| Đất nền | 518 | 115 | location_median_unit_price | 2,571.3 | 28.7% | 30 |
| Căn hộ chung cư | 129 | 31 | xgboost_enriched_log | 937.6 | 13.8% | 1 |

Có **57** tin APE >50%; 10 lỗi lớn nhất chiếm **21.7%** tổng sai số tuyệt đối. Tỷ lệ dự đoán lệch không quá 20% là **46.8%**.

## Những gì có thể kết luận

Nhà và đất còn sai số lớn. Hai mô hình được chọn cho các nhóm này chỉ dùng diện tích và địa bàn; chưa diễn tả số tầng, mặt tiền/hẻm, vị trí đường hoặc chất lượng công trình. Đây là giới hạn đặc trưng, chưa phải bằng chứng rằng bổ sung từng trường sẽ giảm sai số.

| Loại | Train có phường nguồn | Train có số phòng | Val có <10 train cùng địa bàn |
|---|---:|---:|---:|
| Nhà ở | 40.9% | 31.2% | 1 |
| Đất nền | 37.1% | Không áp dụng | 5 |
| Căn hộ chung cư | 76.0% | 62.0% | 2 |

Thiếu phường/số phòng chỉ là mô tả dữ liệu. Ridge nhà và baseline đất hiện không dùng hai trường này; không diễn giải tương quan trong từng nhóm thành nguyên nhân hoặc tác động nhân quả.

## Địa bàn có MAE cao trong nhóm đủ 10 mẫu validation

| Loại | Địa bàn | Val n | MAE (triệu VND) | MedAPE |
|---|---|---:|---:|---:|
| Nhà ở | Hải Châu | 32 | 3,898.6 | 26.2% |
| Nhà ở | Sơn Trà | 19 | 3,543.7 | 24.9% |
| Nhà ở | Liên Chiểu | 13 | 3,343.5 | 40.3% |
| Đất nền | Ngũ Hành Sơn | 15 | 7,241.3 | 50.1% |
| Đất nền | Sơn Trà | 14 | 6,363.5 | 40.6% |
| Đất nền | Cẩm Lệ | 11 | 2,094.6 | 28.8% |
| Căn hộ chung cư | Sơn Trà | 17 | 1,116.3 | 14.8% |

Đây là xếp hạng mô tả trên validation hiện tại. MAE giữa các địa bàn còn phụ thuộc mặt bằng giá; không dùng bảng này làm quy tắc loại tin hoặc cam kết độ chính xác.

## Hàng chờ rà soát

- [validation_priority_review.csv](validation_priority_review.csv): **64 tin**, hợp của top 20 sai số tuyệt đối và mọi APE >50%. Có URL, nhãn nguồn, sai số, lý do ưu tiên.
- [label_review_candidates.csv](label_review_candidates.csv): **37 tin train/validation**, được gắn tín hiệu theo giá/m² nằm ngoài phân vị 1–99% của train cùng loại, diện tích ngoài miền train hoặc header cache khác snapshot. Quy tắc áp dụng toàn bộ train/validation, không phụ thuộc sai số dự đoán.
- Đây là hai hàng chờ kiểm tra, có thể chồng lặp. Không phải danh sách nhãn sai; không tự sửa giá/diện tích hoặc xóa tin vì nằm ở đuôi phân bố.

Ví dụ `cafeland:3164071`: biệt thự 403 m², snapshot 1.000 triệu; dự đoán Ridge khoảng 24.572 triệu. Header và giá có cấu trúc trong cache cũng ghi 1.000 triệu; phần mô tả không có giá tổng thay thế. Cần xác minh độc lập giá rao là giá tổng thực sự. Không dùng dự đoán làm giá thay thế.

Các đất giá cao ở Ngũ Hành Sơn/Sơn Trà có sai số tuyệt đối lớn cũng chưa chứng minh nhãn sai. Tên đường, góc/mặt tiền hoặc vị trí sát biển có thể là hướng khảo sát đặc trưng, cần bằng chứng và thử nghiệm phát triển riêng; không đưa số tiền trong tiêu đề vào đầu vào.

## Chỉ số theo phân nhóm

[segment_metrics.csv](segment_metrics.csv) chứa MAE, RMSE, MAPE, MedAPE, tỷ lệ lệch ≤20%, bias trung bình và số mẫu theo loại × nguồn/địa bàn/khoảng giá/diện tích/độ phủ trường/độ hỗ trợ địa bàn. Nhóm n<10 được đánh dấu. Phân nhóm theo giá chỉ phục vụ chẩn đoán, không phải đặc trưng đầu vào.

## Kiểm chứng trên dữ liệu mới

**Mới chuẩn bị quy trình, chưa thu thập hoặc chấm tin mới (0 tin).** Đề xuất pilot 50 tài sản mới mỗi loại, tổng 150; đây là quy mô công việc đề xuất, không bảo đảm thống kê.

- [benchmark_exclusion_registry.csv](benchmark_exclusion_registry.csv): toàn bộ **8,509 ID nguồn** đã thấy, kèm URL và nhóm, không chứa giá/diện tích/tiêu đề. Loại khỏi pilot cả ID cũ và tài sản nghi trùng xuyên nguồn.
- [benchmark_candidates_template.csv](benchmark_candidates_template.csv): mẫu trống để nhập dữ liệu mới và bằng chứng duyệt giá tổng, diện tích, loại tài sản, địa bàn, timestamp và kiểm tra nghi trùng.
- [benchmark_protocol.json](benchmark_protocol.json) chốt model/manifest và thời điểm bắt đầu trước khi thu thập. Lấy các tin đủ điều kiện liên tiếp theo loại; không chọn theo dự đoán đẹp/xấu.
- Người xác minh chốt nhãn và khả năng trùng trước khi xem dự đoán. Giá mục tiêu vẫn là giá rao, không gọi là giá giao dịch. Ngày cập nhật không chứng minh ngày đăng đầu tiên hoặc tính độc lập theo thời gian.
- Giữ cố định mô hình/encoder/lựa chọn; báo cáo cả tin thu thập, bị loại và được duyệt. Không dùng kết quả pilot để tối ưu rồi tiếp tục gọi nó là test độc lập.

## Chạy lại

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/analyze_training_v3.py
```

Cùng đầu vào/mã: xác minh bản đã chốt, không ghi đè. Raw, bộ/model v1/v2/v3, các quyết định cũ và 137 tin test giữ nguyên.
