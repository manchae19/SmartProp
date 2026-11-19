-- Chạy bằng tài khoản quản trị trên MySQL localhost:3306.
-- Chỉ bổ sung quyền tạo view trên schema đã duyệt; không tạo ADMIN ứng dụng.
GRANT CREATE VIEW, SHOW VIEW ON smartprop.* TO 'smartprop'@'localhost';
-- Sau khi chạy, báo lại để kiểm tra và xử lý Flyway V20 thất bại có kiểm soát.
-- Không tự xóa bảng hoặc sửa flyway_schema_history bằng SQL.