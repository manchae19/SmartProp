# SmartProp Database

`migrations/` chứa SQL nguồn V1–V13; `seeds/` chứa fixture development. Dữ liệu người dùng nằm trong MySQL server, không nằm trong thư mục này.

## Workflow local hiện tại

- Dùng MySQL80/schema smartprop đã chuẩn bị và cấu hình DB_URL/DB_USER/DB_PASSWORD trong .env riêng ở root.
- Backend tắt Flyway, SQL init, seed; Hibernate chỉ validate schema. Chạy theo [backend README](../backend/README.md).
- Không ghi đè .env, không reset/xóa database hoặc chạy Docker MySQL chồng cổng 3306.
- Giữ nguyên migration đã áp dụng. Schema mới phải có kế hoạch được duyệt, dùng phiên bản tiếp theo chưa tồn tại và thử trước trên DB riêng.
- Maven đóng gói SQL vào JAR không có nghĩa tự thực thi migration khi app chạy.

## Tài liệu cần giữ

- [Thiết kế database](docs/database-design.md).
- [Schema tham chiếu](docs/schema-reference.sql).
- [SHA-256 migration V1–V7](docs/migration-checksums.json).
- [Hướng dẫn backup/restore và môi trường thử](../ops/OPERATIONS.md).

scripts/verify-schema.cjs là công cụ kiểm tra trên database thử riêng; có tạo cấu trúc/schema thử, không chạy vào DB ứng dụng. Fixture development không tự seed trong workflow local hiện tại.
