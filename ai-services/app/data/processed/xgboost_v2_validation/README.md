# Huấn luyện lại sau đối chiếu nguồn v2

Dùng biến thể XGBoost đã chọn trên validation v1; giữ nguyên tham số cây. Huấn luyện trên train v2 và dừng sớm bằng validation v2. Huấn luyện lại cùng họ mô hình cơ sở đã chọn ở v1. Không đọc bản ghi test hay chấm lại test.

| Loại | Val n | XGBoost v1 trên nhãn v2 | XGBoost v2 | Cơ sở v2 | Đơn vị |
|---|---:|---:|---:|---:|---|
| Nhà ở | 68 | 2761.3 | 2663.0 | 2616.7 | triệu VND |
| Đất nền | 34 | 4436.9 | 3822.5 | 3729.1 | triệu VND |
| Căn hộ chung cư | 17 | 866.2 | 797.0 | 824.3 | triệu VND |

Các cột đều dùng cùng ID validation còn lại và cùng nhãn v2. Cột v1 là dự đoán đã lưu, không huấn luyện lại. So sánh này không phải kết quả test, không chứng minh tổng quát hóa. Không so trực tiếp với MAE trên toàn bộ 126 tin validation cũ.

`metrics.json` có MAE, MAPE, R², cả biến thể được chọn trước đó, mô hình cơ sở và hash đầu vào. Các model JSON có schema đi kèm; dùng exp cho model log giá. Nhóm nhà vẫn cần xem mô hình cơ sở trước khi chọn XGBoost.

Test v1 giữ nguyên 137 tin và vẫn có chất lượng sàng lọc tự động, có thể còn lỗi tương tự. Chưa gọi đây là benchmark sạch cuối cùng.

Xem [quyết định nguồn và bộ v2](../training_v2/README.md).

Chạy: `python ai-services/app/data/train_reviewed_v2_validation.py`.
