# Kết quả mô hình cơ sở v1

Hai ứng viên: trung vị đơn giá theo địa bàn và Ridge log giá theo log diện tích/địa bàn. Mọi thống kê, danh mục và chuẩn hóa học trên train; chọn mô hình bằng MAE validation. Không dùng tiêu đề, đơn giá chứa nhãn hay nguồn làm đặc trưng. Địa bàn chưa thấy trong train dùng mức chung.

| Loại | Train / Val / Test | MAE test (triệu VND) | MAPE test | R² test |
|---|---|---:|---:|---:|
| Nhà ở | 657 / 68 / 80 | 3096.1 | 33.4% | 0.618 |
| Đất nền | 292 / 37 / 37 | 2908.6 | 55.1% | 0.628 |
| Căn hộ chung cư | 171 / 21 / 20 | 872.3 | 25.8% | 0.617 |

Kết quả thử nghiệm trên giá rao và mẫu qua sàng lọc; chưa chứng minh hiệu quả thị trường. Không so trực tiếp với điểm số trên test cũ. Tập thiếu ngày chưa tham gia huấn luyện. Chi tiết mô hình đã chọn và chỉ số validation trong `baseline_metrics.json`.

Chạy: `python ai-services/app/data/train_training_v1.py`.
