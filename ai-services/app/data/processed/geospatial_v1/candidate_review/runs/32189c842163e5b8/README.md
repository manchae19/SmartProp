# Rà soát 80 tin có tọa độ

Đã rà soát 80 ID: 67 train, 6 validation, 7 reserved. Reserved chỉ kiểm tra bằng chứng vị trí/đường tiếp cận, không phân tích nhãn giá hoặc dự đoán và không đưa vào model.

## Bằng chứng kiệt/hẻm từ tiêu đề

| Loại lời khai | Số tin |
| --- | ---: |
| unknown | 43 |
| alley_claim | 25 |
| frontage_claim | 12 |

Có 4 tin nêu chiều rộng kiệt/hẻm; 6 tin nêu chiều rộng đường. Có 10 tin nêu kiệt/hẻm ô tô hoặc ô tô đến cửa. Không suy ra chiều rộng hẻm từ ngang nhà, số kiệt, diện tích hay số tầng. “Sát mặt tiền” không được coi là nhà mặt tiền; MT viết tắt giữ tín hiệu chờ xem thêm.

## Vị trí chưa đủ xác minh

30/80 tin dùng điểm tọa độ còn xuất hiện với nhiều tên đường nguồn trong toàn bộ collection. Đây là nghi vấn điểm đại diện hoặc dữ liệu nguồn không chính xác, không tự chứng minh căn nhà nằm sai địa chỉ hoặc tin trùng. Không ép tên phường mới/cũ thành cùng một địa chỉ.

Cả 80 tin không có số nhà được xác minh hoặc bằng chứng độc lập xác nhận vị trí đúng tài sản. CSV và JSONL là hai bản lưu của cùng API, không phải hai nguồn xác minh độc lập. Các cache chi tiết đã lưu không có mô tả của 80 ID này; không mượn mô tả tin khác.

**0 vị trí được nâng thành đã xác minh; 0 đặc trưng được tự duyệt để train.** V3 vẫn sử dụng được; đây là kiểm tra bổ sung, không phải điều kiện chạy v3. Không sửa nhãn, tọa độ, phân nhóm, tập giữ riêng hoặc model. Bản làm việc coordinate_review.csv giữ nguyên.

## Tệp kết quả

- `reviewed_80.csv`: mỗi ID một dòng, lời khai, các tín hiệu và bằng chứng tiêu đề gốc.
- `evidence.csv`: tham chiếu file, dòng, trường và SHA-256, không tự coi nguồn là xác minh độc lập.
- `coordinate_clusters.csv`: các điểm chung và danh sách đường/phường khai báo để đối chiếu.

Các tệp có tiêu đề chứa giá chỉ dùng để xem bằng chứng, **không nhập toàn bộ vào XGBoost**. Đặc trưng mới chỉ được chọn rõ ràng sau khi xác minh và tạo phiên bản riêng. “Gần bệnh viện/công viên” là lời khai chưa đo, không chuyển thành khoảng cách mét.

Bước tiếp cần nội dung chi tiết/địa chỉ cấp tài sản và nguồn định vị được phép sử dụng. Không thể chứng minh tọa độ đúng căn nhà chỉ bằng tên đường/phường và một điểm API.
