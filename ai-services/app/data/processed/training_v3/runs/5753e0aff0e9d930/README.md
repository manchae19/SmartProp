# Training v3: dữ liệu phát triển đã chốt

Giá tổng rao bán, đơn vị triệu VND. Giữ nguyên nhãn của pipeline; không sửa giá/diện tích.

| Loại | Train | Validation |
|---|---:|---:|
| Nhà ở | 788 | 153 |
| Đất nền | 518 | 115 |
| Căn hộ chung cư | 129 | 31 |

Tổng: **1,435 train, 299 validation**; 348 tin qua lọc khác giữ riêng. Không chép nhãn test sang v3.

Validation lấy toàn bộ đại diện qua lọc có reservation validation và không có reservation test. Nhóm có cả train/validation từ các thí nghiệm cũ chỉ dùng cho validation. Mọi nhóm validation/test cũ bị cấm vào train. Quy tắc được chốt trước khi chạy mô hình.

Có 105/119 ID validation v2 xuất hiện trong validation v3. Tập mới khác thành phần và có dữ liệu từng liên quan các thí nghiệm cũ; không so trực tiếp MAE với báo cáo v2, không gọi đây là test độc lập.

`train.csv`, `validation.csv`: trường đầu vào có cấu trúc và nhãn; metadata ID/URL/nhóm/nguồn/chất lượng chỉ phục vụ truy vết, không đưa vào ma trận đặc trưng. Không chép raw_json/tiêu đề/mô tả/đơn giá vào đầu vào mô hình.

`split_registry.csv` và `reserved_holdout_registry.csv` lưu ID/nhóm, không có giá hoặc diện tích. `summary.json` lưu phân bố nguồn, địa bàn, khoảng giá/diện tích và độ phủ ngày. `manifest.json` chốt hash đầu vào, đầu ra và các artifact cũ.

Phường lấy đúng trường nguồn, số phòng chỉ nhận số nguyên 1–30; đất để thiếu số phòng. Không trích giá hoặc đặc trưng từ tiêu đề. Encoder/trung vị/chuẩn hóa chỉ học từ train.

Đây là dữ liệu thử nghiệm cho đồ án, chưa đại diện đầy đủ thị trường. 137 tin test cũ giữ nguyên và không được chấm trong đợt này.
