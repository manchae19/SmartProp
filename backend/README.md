# SmartProp Backend

Java 21, Spring Boot 3.5.16, Maven Wrapper và MySQL 8. Backend chạy tại `http://localhost:8080`, API có prefix `/api/v1`.

## Chạy local

MySQL80 phải đang chạy, schema `smartprop` đã chuẩn bị. Giữ `.env` hiện có ở root; không ghi đè hoặc đưa secret vào FE. Spring không tự đọc `.env`; scripts/load-env.ps1 nạp cấu hình vào process.

Tại `backend/`, khi cần build:

```powershell
.\scripts\run-maven.ps1 '-B' '-DforkCount=0' 'test'
.\scripts\run-maven.ps1 '-B' '-DskipTests' 'package'
```

Khởi động:

```powershell
.\scripts\run-local.ps1 -Transport NIO2
```

Java 21 phải trên PATH hoặc JAVA_HOME. Launcher PowerShell dùng Maven đã được Wrapper tải vào cache; máy hiện tại có vấn đề khi gọi subprocess qua cmd.exe. Máy khác có thể dùng Maven Wrapper trực tiếp. Dừng BE trước khi package nếu Windows khóa JAR. Có thể chọn `-Port 8081` khi cổng 8080 đang dùng; `NIO2` là tùy chọn transport cho máy Windows hiện tại.

Workflow local cưỡng chế Flyway=false, SQL init=never, seed=false và Hibernate `ddl-auto=validate`; không tự sửa schema. Không chạy Docker MySQL ở cổng 3306 hoặc migration/reset DB trong workflow này. SQL nguồn V1–V7 phải giữ nguyên.

## API và quyền

- [API contract đầy đủ](../docs/backend-tasks/BACKEND_API_CONTRACT.md).
- [Audit và kế hoạch BE-10–BE-18](../docs/backend-tasks/BACKEND_COMPLETION_AUDIT.md).
- JWT Bearer; role lấy từ DB, không tự đăng ký ADMIN. Đổi mật khẩu hoặc khóa tài khoản thu hồi phiên.
- BROKER/ADMIN đăng tin, mỗi người sửa tin của mình; ADMIN kiểm duyệt qua API riêng. Public chỉ thấy tin PUBLISHED chưa xóa/chưa hết hạn; public DTO không chứa contact.
- Mutation tin/ảnh cần expectedVersion; stale trả 409. JSON lỗi có code/message/fields/timestamp; không log mật khẩu, token hoặc .env.
- CORS cần đúng origin FE: localhost:5173 hoặc 127.0.0.1:5173 theo CORS_ORIGINS. Không bật DEBUG/TRACE MVC với dữ liệu tài khoản thật.

## Dữ liệu và tệp

MySQL lưu bản ghi nghiệp vụ; thư mục database/ chỉ chứa SQL. `STORAGE_ROOT` mặc định `./var/uploads` tính từ backend working directory. DB lưu metadata, bytes ảnh/bằng chứng lưu riêng và tải qua API kiểm tra quyền.

JPEG/PNG; bằng chứng nhận thêm PDF. Tối đa 10 MiB/tệp, 12 MiB/request, một file/request; 30 ảnh/tin và 10 bằng chứng/báo cáo. PDF mới kiểm tra định dạng cơ bản, chưa quét mã độc đầy đủ. Xóa mềm giữ bytes; chưa có purge tự động. Backup phải gồm cả DB và storage.

## Kiểm tra

- GET `/actuator/health` và `/actuator/health/readiness` (gồm DB).
- Suite mặc định là unit/MockMvc/config; thành công không thay thế persistence.
- Khi được phép chạy integration, khởi động FE tại 5173 rồi chạy `.\scripts\run-isolated-mysql.ps1`. Script dùng MySQL tạm cổng 3307/datadir và schema thử riêng; không Flyway/Docker/reset DB nguồn.
- Không bật hai legacy integration tests có Flyway/Docker. Không ghi fixture vào database smartprop thật.

[Hướng dẫn HTTPS, backup/restore và storage](../ops/OPERATIONS.md). Các file deploy là cấu hình mẫu, chưa chứng minh đã triển khai lên server/domain thật.