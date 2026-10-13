# Phân tích lỗi XGBoost trên validation

Đã phân tích 126 tin validation, đối chiếu hash đầu vào với mô hình gốc. Không phân tích lại test, không sửa nhãn/split.

| Loại | Số tin | Sai số tương đối >50% | >100% |
|---|---:|---:|---:|
| Nhà ở | 68 | 11 | 3 |
| Đất nền | 37 | 20 | 10 |
| Căn hộ chung cư | 21 | 3 | 1 |

## Các trường hợp cần kiểm tra

Có 11 tin validation và 76 tin train có tín hiệu cần kiểm tra nguồn. Sai số dự đoán lớn không chứng minh nhãn sai. Không loại tin vì mô hình dự đoán sai hoặc sửa giá theo dự đoán.

- CafeLand 3146736: đất 516m² ở Hòa Phú, giá 3,6 tỷ nhưng dự đoán khoảng 28,3 tỷ. Giá trong tiêu đề khớp nhãn; có khả năng địa bàn cấp huyện và diện tích chưa đủ diễn tả khác biệt đất vùng ven. Chưa có bằng chứng để sửa nhãn.
- Nhadat24h 4374835: “cặp liền kề”, “890tr/lô”; cần xác minh diện tích tương ứng một lô hay cả cặp.
- Nhadat24h 4396478: “2 tỷ/căn”, “đóng 50%”; cần phân biệt giá toàn bộ và lịch thanh toán. Không tự coi 2 tỷ là giá trả trước.

## Bổ sung đặc trưng

Đề xuất thử phường/xã có sẵn trong trường nguồn, số phòng hợp lệ và cờ thiếu dữ liệu. Không trích số tiền từ tiêu đề làm đặc trưng. Danh mục phường học từ train, giá trị chưa thấy có cờ riêng. Không suy phường CafeLand từ tên quận hoặc đoán từ tiêu đề.

Pháp lý, tọa độ và hướng có độ phủ thấp trong train nên chưa đưa vào thử nghiệm đầu. Pháp lý không có dữ liệu được giữ là thiếu, không coi là không có sổ.

`feature_coverage.csv` ghi độ phủ thực tế theo loại và split; `validation_errors.csv` có sai số từng tin; `validation_source_check_queue.csv` và `train_source_check_queue.csv` giữ URL và lý do cần đối chiếu. Chưa tải lại trang chi tiết.

Chạy: `python ai-services/app/data/analyze_xgboost_validation.py`.
