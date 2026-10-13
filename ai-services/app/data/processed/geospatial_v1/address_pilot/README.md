# Thử tìm vị trí từ địa chỉ: 80 tin

80 ID; 65/65 truy vấn duy nhất đã thử. 63 tin có ứng viên khớp tên đường và vùng Đà Nẵng; **0 căn nhà được xác minh, 0 đặc trưng được duyệt để train**.

Trạng thái theo ID: `{'candidates_returned': 72, 'no_result': 8}`. Một truy vấn có thể dùng chung nhiều ID; không cộng số ID thành số yêu cầu mạng.

[Mở 80 liên kết Google Maps](runs/a92df9d1354170c7/review.html), [checkpoint](runs/a92df9d1354170c7/checkpoint.csv), [ứng viên OSM — không train](runs/a92df9d1354170c7/candidates_DO_NOT_TRAIN.csv), [số liệu](runs/a92df9d1354170c7/summary.json). Không tải nội dung/tọa độ Google; các liên kết dùng đúng địa chỉ nguồn, không tự thêm số nhà.

Truy vấn OSM chỉ gửi tên đường và Đà Nẵng; không gửi giá, tiêu đề, tên người đăng, số điện thoại hoặc pin nguồn. Tên phường/quận cũ giữ trong hàng chờ để kiểm tra thủ công, không tự ánh xạ. Không suy ra chiều rộng hẻm, ô tô vào được hoặc khoảng cách từ căn nhà. Một kết quả khớp đường vẫn có thể là đoạn đường/địa điểm đại diện. Không chọn kết quả đầu tiên làm vị trí tài sản.

Đợt hữu hạn 80 ID trên một máy, một luồng, cách yêu cầu ít nhất 1,1 giây, cache cả phản hồi rỗng/lỗi; dừng ở lỗi dịch vụ. Không chạy định kỳ hoặc mở rộng hàng nghìn địa chỉ bằng dịch vụ công cộng. [Chính sách Nominatim](https://operations.osmfoundation.org/policies/nominatim/).

© OpenStreetMap contributors; ODbL 1.0; https://www.openstreetmap.org/copyright. Giữ bằng chứng và nghĩa vụ ODbL khi phân phối dữ liệu phái sinh. Chưa chỉnh raw, nhãn, split, coordinate_review hoặc model v3.
