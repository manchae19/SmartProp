# Bộ dữ liệu train hiện tại — 15/10/2026

**Model mới nhất đã thử nghiệm:** [v6 với đặc trưng nội dung](TRAINING_V6.md), dùng cùng 2.214 train/299 validation và 684 tin giữ riêng. Bộ lọc gốc và nhãn không thay đổi; feature mới lưu riêng trong `processed/property_features_v6`.

**Kiểm chứng bổ sung:** [pilot v6 132 tin](V6_HOLDOUT_PILOT.md) đã được chấm từ nhóm dự phòng sau audit/sàng lọc. Reservation và train/validation vẫn giữ nguyên; registry exposure được lưu riêng để tránh xem các tin đã chấm là test mới trong lần sau.

[Báo cáo đã kiểm chứng](processed/remaining_diversity_review/runs/1d45c8941172a52d/README.md) · [Kiểm chứng độc lập](processed/remaining_diversity_review/verification.json).

| Phần dữ liệu | Số tin |
|---|---:|
| Train | 2.214 |
| Validation cố định | 299 |
| Eligible giữ riêng | 684 |
| Tổng eligible | 3.197 |
| Còn chờ | 3.583 |
| Đã loại | 1.729 |
| Tổng ID nguồn duy nhất | 8.509 |

Train gồm **1.411 nhà ở**, **626 đất nền**, **177 căn hộ**. Đợt này kiểm tra toàn bộ 3.605 ID còn chờ của bản trước, bổ sung 22 eligible: 18 train (9 nhà, 9 đất; 16 CafeLand, 2 Nhadat24h) và 4 giữ riêng. Chưa có căn hộ mới vượt tất cả điều kiện; không nhân bản hoặc hạ chuẩn để cân bằng số lượng. Danh mục, giá và diện tích số không thay đổi trong đợt này.

## Dùng đúng đầu vào mới

[Train CSV](processed/remaining_diversity_review/runs/1d45c8941172a52d/training_inputs/train.csv), [validation CSV](processed/remaining_diversity_review/runs/1d45c8941172a52d/training_inputs/validation.csv), [registry dự phòng](processed/remaining_diversity_review/runs/1d45c8941172a52d/training_inputs/reserved_holdout_registry.csv). Schema và 6 buffer DMatrix nằm cùng thư mục `training_inputs`. **Đã huấn luyện model v5 trên 2.214 tin**, có [kết quả và cách chạy](TRAINING_V5.md). Model v4 vẫn dùng 2.110 train; script `train_reviewed_collection_v4.py` đọc đầu vào cũ. Dùng `train_reviewed_collection_v5.py` cho bộ 2.214 tin, giữ nguyên v3/v4. Các trường `model_trained: false` trong manifest/summary của đợt lọc ghi trạng thái tại thời điểm xuất dữ liệu; kết quả huấn luyện được lưu riêng trong `models_v5_validation`, không sửa snapshot lọc đã chốt.

Chọn bản hiện tại qua `processed/remaining_diversity_review/latest.json`. Các báo cáo `remaining_3752_review`, `remaining_4772_review` và `collection_pipeline` là snapshot lịch sử, không sửa số liệu hoặc con trỏ của chúng. Các run trung gian trong thư mục mới cũng được giữ để truy vết; chỉ dùng bản được `latest.json` và `verification.json` cùng xác nhận.

## Những điều đã kiểm tra

- Từng ID còn chờ được đối chiếu với bằng chứng nguồn đã lưu. 146 HTML của các quyết định nguồn có thể áp dụng được kiểm tra SHA-256; không tuyên bố đã tải mới hoặc kiểm tra lại toàn bộ kho HTML.
- Diễn giải giá viết tắt khi khớp chính xác giá header nguồn, loại ảnh hưởng định dạng Markdown, phân biệt footer môi giới, dự định xây dựng và thu nhập cho thuê với tài sản/giá bán hiện hữu. Không điền giá bằng model hoặc suy đoán từ khu vực.
- Giá dạng x, nhiều tài sản/phòng thuê khép kín, diện tích hoặc địa điểm mâu thuẫn tiếp tục chờ. Mô tả dài giống nhau qua hai nhóm cũ được đánh dấu nghi trùng; không tự đổi nhóm hoặc đưa thành viên holdout vào train.
- Bảo toàn đủ 2.196 hàng train trước và 299 hàng validation; giá/diện tích, raw JSON, ID nhóm và reservation không thay đổi. Các đầu ra model v3/v4 giữ nguyên SHA-256.
- 14 kiểm thử và kiểm chứng độc lập đạt: tải lại cả 6 DMatrix, so số hàng/cột, nhãn log giá và ma trận feature với CSV/schema fit trên train. Giá, đơn giá, tiêu đề/mô tả và ID không là feature.

Trong 3.583 tin còn chờ, 1.770 tin có bằng chứng khớp ID nhưng còn vấn đề; 1.813 tin thiếu/chưa khớp nguồn (gồm 1.798 Chợ Tốt chưa được yêu cầu riêng do nguồn bị chặn trước đó). Không có yêu cầu mạng mới trong đợt lọc. Chất lượng ở đây là kiểm chứng tin rao theo nguồn, chưa xác minh giá giao dịch/thực địa. Thêm số lượng không đảm bảo model tốt hơn; giữ validation cố định để so sánh công bằng khi train phiên bản kế tiếp.

## Chạy lại và kiểm chứng

```powershell
./ai-services/.venv/Scripts/python.exe -X utf8 ai-services/app/data/filter_remaining_diversity.py
./ai-services/.venv/Scripts/python.exe -X utf8 ai-services/app/data/verify_remaining_diversity.py
./ai-services/.venv/Scripts/python.exe -X utf8 -m unittest discover -s ai-services/app/data -p test_remaining_diversity_rules.py -v
```

Cùng đầu vào/mã sẽ kiểm chứng lại run hiện tại. Không cần cào lại nguồn để chạy bộ lọc này.
