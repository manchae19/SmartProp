# Rà soát bằng chứng vị trí 20 tin — 13/10/2026

Chọn có chủ đích 20 tin train trong nhóm 63 tin khớp tên đường; không phải mẫu đại diện. 18/18 truy vấn OSM/Nominatim đã thử, 1 tin có ứng viên khớp kiệt, 16 tin có ứng viên khớp đường. **0 vị trí căn nhà được xác minh, 0 đặc trưng được duyệt train.**

12/20 tin có ít nhất một ứng viên lần trước ngoài khung đô thị thử nghiệm. Tên đường/vùng Đà Nẵng trùng chưa xác minh đúng địa chỉ: Âu Cơ trả cả Hội An, Trường Chinh trả cả Quế Sơn. Khung 108.05–108.31, 15.93–16.21 thu hẹp truy vấn cho cohort khai báo các quận đô thị cũ; đây không phải ranh giới hành chính hay bằng chứng nguồn pin đúng. Không có kết quả trong khung không chứng minh đường/nhà không tồn tại.

## Bằng chứng đã đọc

Có 3 manh mối số kiệt: 266 Trường Chính (tiêu đề khác cách viết Trường Chinh trong trường đường), 196 Âu Cơ và 59 Trương Chí Cương. Đây là số kiệt, không phải số nhà trong kiệt. LK4A - 537 là mã lô cần xác minh; không tự đổi thành số nhà 537. Nguyễn Bỉnh Khiêm giao An Mỹ 3 là lời khai góc/giao đường, không xác định đúng thửa. Hẻm 3m/kiệt 3M là chiều rộng khai báo; ngang 5m/6m là chiều ngang thửa. Hòa Minh 21 là tên đường có số, không phải số nhà 21. “Sát mặt tiền” không tự thành mặt tiền.

CSV và JSONL Chợ Tốt là hai bản lưu cùng API, không phải nguồn độc lập. Đã kiểm tra trường CSV/JSONL/source_values: không có body/description/địa chỉ cấp tài sản mới. Nguồn chi tiết từng trả HTTP 403/Cloudflare; không thử vượt chặn hoặc mượn mô tả tin khác. Không yêu cầu người dùng cung cấp số nhà mà chưa có trong dữ liệu; các tin này giữ trạng thái thiếu bằng chứng.

[20 kết luận và manh mối nguồn](reviewed_20.csv), [ứng viên đường/kiệt — không train](candidates_DO_NOT_TRAIN.csv), [số liệu](summary.json). Google Maps chỉ là liên kết tìm địa chỉ, không tải dữ liệu Google.

Tối thiểu 1,1 giây giữa yêu cầu, một luồng/máy, cache, dừng lỗi; chỉ tinh chỉnh đợt 20 tin này, không chạy định kỳ. [Chính sách Nominatim](https://operations.osmfoundation.org/policies/nominatim/). © OpenStreetMap contributors; ODbL 1.0; https://www.openstreetmap.org/copyright.

Model v3 vẫn dùng được. Muốn bổ sung vị trí cấp nhà cần nguồn tin có địa chỉ/mô tả đủ cụ thể và quyền sử dụng phù hợp; tìm đúng đường/kiệt không tạo ra dữ liệu số nhà còn thiếu. Raw, nhãn, split, coordinate_review, model giữ nguyên.
