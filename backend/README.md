# SmartProp Backend

Java21, Spring Boot3.5.x, Maven và MySQL8. API prefix `/api/v1`.

## Chạy local

Chuẩn bị schema và root `.env` theo `.env.example`. `scripts/load-env.ps1` nạp cấu hình vào process; Spring không tự đọc `.env`.

Tại `backend/`:

```powershell
.\mvnw.cmd -B -Dmaven.test.skip=true package
.\scripts\run-local.ps1 -Transport NIO2
```

Có thể dùng `scripts/run-maven.ps1` khi Maven đã cache. Dừng Backend trước package nếu Windows khóa JAR. Launcher giữ Flyway=false, SQL init=never, seed=false và Hibernate validate. Migration V1–V13 nằm ở `database/migrations/`, chỉ rollout theo kế hoạch được duyệt.

## API và quyền

- Controller/DTO ở `src/main/java/vn/smartprop/`; cấu hình ở `src/main/resources/application.yml`.
- Đăng ký tạo BUYER; BROKER cần ADMIN xét duyệt. Không tự đăng ký ADMIN hoặc cấp quyền từ Frontend.
- BROKER/ADMIN tạo tin của mình; tin qua DRAFT/PENDING/PUBLISHED. Public chỉ thấy tin hợp lệ, không nhận contact trong listing/detail DTO.
- Mutation tin/ảnh cần `expectedVersion`; stale trả409. Lỗi API dùng code/message/fields/timestamp.
- JWT kiểm tra session, status, role và tokenVersion hiện tại. Đổi mật khẩu/khóa/thu hồi quyền vô hiệu hóa các phiên theo chính sách.
- CORS phải khớp origin FE; không log token, mật khẩu, payload tài khoản hoặc `.env`.

## Refresh session

Sau kiểm tra V10, bật `REFRESH_ENABLED=true`. Access token mặc định15phút; BUYER/BROKER7ngày hoặc30ngày khi ghi nhớ; ADMIN8giờ/idle30phút. Rotation giữ hạn tuyệt đối; replay thu hồi session.

Cookie HttpOnly/SameSite=Lax/Secure mặc địnhtrue. Chỉ local HTTP loopback dùng `REFRESH_SECURE_COOKIE=false`. FE dùng API cùng origin, bật `VITE_ENABLE_REFRESH=true`, lấy CSRF qua `/auth/csrf`; refresh/logout giữ kiểm tra CSRF/Origin. Client access-only vẫn dùng login không opt-in cookie.

## Lưu trữ và vận hành

MySQL lưu metadata; bytes tệp ở `STORAGE_ROOT`, mặc định `./var/uploads` tính từ backend. Tệp riêng tải qua API kiểm tra quyền. Ảnh JPEG/PNG tối đa10MiB/tệp,12MiB/request; bằng chứng nhận thêm PDF. Không tự purge khi chưa chốt retention.

Health: `/actuator/health`, `/actuator/health/readiness`. Backup cần cả DB/storage; xem [ops](../ops/OPERATIONS.md). `.env`, `var/`, target, test source và test runner local không thuộc snapshot Git này.
