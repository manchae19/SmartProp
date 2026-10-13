# Rà soát loại bất động sản trong nhóm cách ly v1

Đã xét **434 tin** có cờ loại nguồn. Quyết định dựa trên tiêu đề và danh mục đã lưu, có quy tắc và dấu vết từng tin; chưa phải xác minh độc lập từ trang chi tiết.

| Nguồn | Giữ nhãn theo bằng chứng hiện có | Loại | Chờ |
|---|---:|---:|---:|
| alonhadat | 15 | 0 | 2 |
| cafeland | 7 | 2 | 3 |
| nhadat24h | 304 | 0 | 101 |

**308 tin trong 306 nhóm** đủ điều kiện xem xét cho phiên bản tiếp theo sau kiểm tra các cờ còn lại và thành viên cùng nhóm. Giữ nhãn loại không đồng nghĩa đã duyệt sạch giá hoặc diện tích. Chưa bổ sung tin vào dữ liệu huấn luyện.

## Quyết định và giới hạn

- Giữ khi tiêu đề nêu rõ đất/nhà và danh mục nguồn là loại phù hợp hoặc nhóm nhà đất tổng hợp. Đây là phân giải lại cờ bằng quy tắc, không gán nhãn thủ công.
- Chờ khi đất nằm trong danh mục nhà, đất có nhà/tặng nhà, quảng cáo nhiều tài sản/dự án, giá theo vốn ban đầu, hoặc tiêu đề không đủ rõ.
- Loại loại thương mại/lưu trú/toàn công trình rõ trong tiêu đề, ví dụ shop khối đế và dãy trọ. Raw và quyết định v1 vẫn giữ nguyên.
- Không bỏ cờ giá, diện tích, nhiều tài sản hoặc mâu thuẫn trong nhóm nghi trùng. Mọi tin vẫn giữ nhóm và split v1.
- Không có thay đổi nhãn nào được gọi là xác minh thực địa hay kiểm tra trang chi tiết mới. Có thể còn tín hiệu chưa thể phát hiện bằng tiêu đề.

## Tệp kết quả

- `review_decisions.csv`: mọi tin, quyết định giữ/loại/chờ, bằng chứng, quy tắc và hash.
- `pending.csv`: các tin cần mô tả/trang chi tiết để quyết định.
- `excluded.csv`: loại khỏi mục tiêu nhà/đất/căn hộ thông thường.
- `eligible_for_next_version.csv`: đã giải quyết cờ loại và không còn cờ/nhóm chặn; vẫn là nhãn sàng lọc tự động.
- `summary.json`: tổng hợp, hash và kiểm tra v1 giữ nguyên.

Bước tiếp theo: đối chiếu chi tiết nhóm chờ; khi tạo v2, ưu tiên chỉ bổ sung nhóm train. Giữ nguyên ID, nhãn và nhóm trong validation/test v1 để so sánh công bằng. Nhóm vốn thuộc holdout nhưng chưa dùng trong v1 phải giữ dự phòng, không chuyển sang train.

Chạy lại: `python ai-services/app/data/review_training_categories.py`.
