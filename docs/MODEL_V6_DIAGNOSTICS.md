# Phân tích sai số v6 và kế hoạch bổ sung dữ liệu

Ngày 27/10/2026. Phân tích **299 dự đoán validation phát triển đã lưu** của run `b4b1339d3f35857e`, nhánh `all`; không tạo dự đoán mới, không fit lại model, không chấm lại pilot và không dùng lịch sử giá dự đoán làm nhãn.

## Kết quả theo loại bất động sản

| Loại | Train | Validation | MAE triệu VND | MAPE | Sai số ≤20% |
|---|---:|---:|---:|---:|---:|
| Nhà ở | 1.411 | 153 | 2.810,02 | 35,82% | 49,67% |
| Đất nền | 626 | 115 | 2.409,00 | 42,05% | 43,48% |
| Căn hộ chung cư | 177 | 31 | 895,97 | 15,75% | 67,74% |
| **Tổng** | **2.214** | **299** | **2.457,33** | **36,13%** | **49,16%** |

MAE v6 thấp hơn **9,86%** so với control v5 trên cùng 299 ID và cùng nhãn. Đây là đối chiếu các dự đoán đã lưu; không phải một đợt huấn luyện hoặc test độc lập mới. Validation đã được dùng để phát triển/chọn cấu hình; 31 căn hộ chưa đủ để kết luận mô hình ổn định rộng hơn.

Top 10 tin chiếm **22,70%** tổng sai số tuyệt đối. **68 tin giá rao từ 10 tỷ** chiếm **57,51%** sai số; trong nhóm này **61 tin bị dự đoán thấp hơn giá rao**. Cần xem cả sai số tiền và phần trăm khi đánh giá phân khúc giá cao.

## Nhóm địa bàn cần đối chiếu kỹ

Các nhóm dưới đây có ít nhất 10 mẫu validation, được trình bày để kiểm tra chất lượng và phân bố dữ liệu. Mốc 10 chỉ là quy tắc hiển thị, không bảo đảm độ tin cậy thống kê.

| Loại | Địa bàn | Train | Validation | MAE triệu VND | MAPE |
|---|---|---:|---:|---:|---:|
| Đất nền | Ngũ Hành Sơn | 82 | 15 | 7.718,87 | 83,58% |
| Đất nền | Cẩm Lệ | 62 | 11 | 2.127,96 | 73,11% |
| Nhà ở | Ngũ Hành Sơn | 113 | 17 | 3.797,89 | 35,50% |
| Nhà ở | Hải Châu | 279 | 32 | 3.683,25 | 30,70% |

Có **21 nhóm loại × địa bàn dưới 10 mẫu validation**. Không xếp hạng độ chính xác ổn định cho các nhóm nhỏ. Sai số cao không chứng minh giá nguồn sai; chỉ đối chiếu bằng chứng nguồn độc lập mới được đề xuất sửa nhãn. Phân tích chưa xác nhận nguyên nhân từ vị trí, pháp lý, dự án hoặc loại đất.

## Kế hoạch thu thập dựa trên độ phủ

Ưu tiên căn hộ vì chỉ có 177 mẫu train; đồng thời bổ sung các địa bàn mở rộng đang có ít tin. Lập chỉ tiêu theo số mẫu train, không chọn tin theo residual hoặc bỏ tin khó để tăng điểm. Tên địa bàn mở rộng không tự chứng minh ranh giới hành chính hoặc vị trí đúng tài sản.

Với mốc kế hoạch **10 tin train cho mỗi nhóm loại × địa bàn đã xuất hiện**:

| Loại | Số nhóm dưới mốc | Khoảng thiếu |
|---|---:|---:|
| Nhà ở | 9 | 71 |
| Đất nền | 16 | 131 |
| Căn hộ chung cư | 3 | 17 |
| **Tổng** | **28** | **219** |

**219 là khoảng thiếu độ phủ theo quy tắc kế hoạch**, không phải số tin đủ để bảo đảm model tốt, cũng không thay thế mục tiêu thu thêm căn hộ và một tập kiểm chứng mới. Danh sách đầy đủ nằm trong `collection_priorities.csv` của run cục bộ. Đợt phân tích này chưa cào thêm dữ liệu.

Tin mới cần đủ giá rao, diện tích, loại tài sản và địa bàn có bằng chứng; kiểm tra trùng theo nhóm tài sản và chọn split theo giao thức trước khi chấm. Giữ lại cả trường hợp khó/sai số cao. Mẫu kiểm chứng mới không được trộn vào train để tăng số lượng. Giá do model trả hoặc lưu trong lịch sử không được dùng làm nhãn.

Một dòng train lịch sử có mã địa bàn chứa tiêu đề tin vẫn được ghi nhận đúng trạng thái cũ. Bản chuẩn bị **2.213 train** đã cách ly dòng đó nhưng chưa được huấn luyện; demo hiện vẫn dùng v6 cũ. Chưa có tọa độ tài sản được xác minh để thêm khoảng cách tiện ích.

## Chạy lại và kiểm chứng

Từ gốc repo:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 -m unittest discover -s ai-services/app/data -p test_analyze_models_v6.py -v
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/analyze_models_v6.py
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/verify_models_v6_diagnostics.py
```

Cần archive `processed/` cục bộ. Run đã kiểm chứng: `models_v6_diagnostics/runs/355a330654f83092`, chọn qua `latest.json` và `verification.json`. **5 kiểm thử đạt**; verifier độc lập đối chiếu 299 ID/nhãn/dự đoán, 3 nhóm loại, **124 hàng phân nhóm**, độ phủ, chỉ tiêu thu thập và hash các file đã khóa. Không nạp model để suy luận.

Artifact gồm bảng sai số `DO_NOT_TRAIN`, metric theo loại/địa bàn/nguồn/khoảng giá/diện tích và tình trạng thiếu đặc trưng, bảng độ phủ, danh sách ưu tiên, summary và manifest SHA-256. Các CSV chi tiết và artifact nằm ngoài Git; báo cáo tổng hợp này có thể dùng cho mentor. Cùng mã và đầu vào chỉ kiểm tra lại run đã có; không ghi đè kết quả đã chốt.
