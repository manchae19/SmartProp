# Thử nghiệm đặc trưng XGBoost trên validation

Giữ nguyên train/validation/test và mọi nhãn v1. Không đọc bản ghi hoặc dự đoán test trong thử nghiệm này. Giữ nguyên tham số cây, thử ba biến thể cố định: diện tích/địa bàn + log giá; thêm phường/số phòng + giá gốc; thêm phường/số phòng + log giá. Log giá dừng sớm theo MAE quy đổi về triệu VND; số phòng đất luôn để thiếu. Không sử dụng giá/m² hay tiêu đề làm đặc trưng.

| Loại | MAE validation gốc (triệu) | Biến thể chọn | MAE mới | Giảm |
|---|---:|---|---:|---:|
| Nhà ở | 2761.3 | enriched_raw | 2710.4 | 1.8% |
| Đất nền | 4142.8 | area_location_log | 3477.6 | 16.1% |
| Căn hộ chung cư | 952.4 | enriched_log | 872.5 | 8.4% |

Encoder chỉ học danh mục từ train; phường được ghép với địa bàn và cần ít nhất 3 hàng train. Phường thiếu/chưa thấy/hiếm có cờ riêng. Số phòng chỉ nhận số nguyên 1–30; thiếu giữ NaN, không tự gán 0 phòng. Đây là thông tin từ nguồn, chưa xác minh thực địa. Pháp lý/tọa độ/hướng chưa dùng do thiếu nhiều.

Mức giảm trong bảng so với XGBoost v1, không phải so với mô hình cơ sở Ridge/trung vị. Nhóm nhà vẫn có MAE validation khoảng 2.710 triệu, cao hơn Ridge khoảng 2.619 triệu. Xem chỉ số validation của mô hình cơ sở trong `training_v1/baseline_metrics.json`.

Cải thiện validation đã được dùng để chọn mô hình nên có thể lạc quan. Cần chốt cấu hình và quy tắc trước khi đánh giá test; không tiếp tục thử tham số theo điểm test. Không khẳng định mô hình mới tốt hơn trên thị trường.

Các model JSON đi kèm `_features.json` xác định thứ tự cột và phép đổi nhãn. `metrics.json` giữ mọi biến thể, `validation_predictions.csv` giữ từng dự đoán. Model log giá phải lấy exp của đầu ra khi suy luận.

Xem [phân tích lỗi và hàng chờ kiểm tra nguồn](../xgboost_validation_review/README.md).

Chạy: `python ai-services/app/data/experiment_xgboost_features.py`.
