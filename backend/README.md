# SmartProp Backend

Java 21, Spring Boot 3.5.16, Maven Wrapper và MySQL 8. Backend chạy tại `http://localhost:8080`, API có prefix `/api/v1`.

Nguồn nhập từ nhánh `Backend-Huy` tại `ac13ec3`. Nhánh tích hợp bổ sung API lịch sử định giá theo tài khoản, SQL V13 và các kiểm thử có thể chạy lại. [Hướng dẫn định giá/lịch sử và demo riêng](../docs/VALUATION_HISTORY.md). Chạy nhanh từ gốc repo trên máy hiện tại:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 backend/scripts/run-demo.py
```

Launcher này dùng MySQL demo mới riêng, không đọc `.env`; phần chạy local phía dưới dành cho database nguồn đã được người phụ trách chuẩn bị.

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

- [Hợp đồng API lịch sử định giá](../docs/VALUATION_HISTORY.md).
- Controller/service của các tính năng nghiệp vụ được giữ từ nhánh BE; các màn hình FE ngoài định giá cần nối riêng.
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
- Từ gốc repo, chạy `ai-services/.venv/Scripts/python.exe -X utf8 backend/scripts/check-history-mysql.py` để tạo MySQL/schema mới cổng 13317, AI riêng 18081 và kiểm tra JWT → model → lịch sử. Không ghi fixture vào database `smartprop` nguồn.
- Thêm `--browser` để kiểm tra cả Vue trên trình duyệt với BE/MySQL/model thật. Cần thêm Node, dependencies frontend và hai cổng trống 18082/15174. [Luồng kiểm tra](../docs/VALUATION_HISTORY.md).
- `ai-services/.venv/Scripts/python.exe -X utf8 backend/scripts/check-demo.py` kiểm tra kết nối stack demo mặc định và proxy FE, không sửa database hoặc dừng dịch vụ; dùng khi gặp lỗi 502/cổng bận.

Đây là bản tích hợp local, chưa triển khai server/domain thật. Database nguồn dùng quy trình migration/backup của nhóm; lịch sử yêu cầu áp dụng V13. Demo riêng đã có launcher giữ dữ liệu và dừng đúng tiến trình do nó tạo.
