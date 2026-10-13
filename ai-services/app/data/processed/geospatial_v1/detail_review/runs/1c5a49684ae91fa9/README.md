# Lấy chi tiết 80 tin: trạng thái truy cập nguồn

Hàng chờ 80 ID, ưu tiên 30 tin có điểm tọa độ dùng với nhiều tên đường. Đã gửi 1 yêu cầu chi tiết thực tế; 1 trả HTTP 403. 79 URL còn lại chưa được yêu cầu, không được báo là 403 riêng từng tin.

Chưa lấy được mô tả chi tiết đã xác minh hoặc địa chỉ cấp tài sản. Không dùng nội dung trang chặn làm nội dung tin đăng; không suy tọa độ đúng căn nhà từ tên đường/phường. Dữ liệu gốc, nhãn, tập giữ riêng, bản làm việc tọa độ và model v3 giữ nguyên.

- `checkpoint.csv` / `checkpoint.json`: trạng thái chính xác của từng ID, lý do chưa tải và tham chiếu probe.
- `summary.json`: số yêu cầu thực tế và số URL chưa kiểm tra.
- Mẫu phản hồi HTTP và robots nằm trong thư mục source_access riêng, được ghi SHA-256 trong manifest.

Chạy lại finalizer cùng probe chỉ xác minh kết quả cũ, không gửi mạng hoặc ghi đè bằng chứng. Muốn kiểm tra truy cập ở thời điểm khác, tạo thư mục probe mới rồi dùng `--probe-dir`; không xóa checkpoint cũ. Nếu nguồn cho phép truy cập trở lại, cần lấy phần còn lại và xác minh ID trước khi trích địa chỉ/mô tả. Checkpoint nguồn bị chặn không có nghĩa tải 80 tin đã hoàn thành.

Để tiếp tục hiện tại cần nguồn chi tiết có quyền truy cập: bản xuất được phép của nguồn hoặc bằng chứng người đăng cung cấp. Không bỏ qua chặn truy cập bằng đổi danh tính hoặc giải CAPTCHA. V3 hiện tại vẫn là mô hình cơ sở đã huấn luyện; chưa có model vị trí mới.
