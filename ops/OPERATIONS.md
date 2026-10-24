# Vận hành SmartProp

Các file ở đây là cấu hình chuẩn bị triển khai; chưa cấu hình domain, chứng chỉ hay đưa ứng dụng lên máy chủ thật. Caddyfile/service dùng Linux. Không chạy thay đổi máy chủ từ phiên phát triển Windows.

## Chạy local

Backend: backend/scripts/run-local.ps1 -Transport NIO2. FE: tại frontend/, npm run dev. Trang quản trị thực tế nằm cùng app: http://127.0.0.1:5173/admin/dashboard. Thư mục frontend/vue.ui/admin-dashboard cũ là scaffold Vite, không phải trang quản trị đang nối API. Token giữ memory, reload cần đăng nhập lại.

## Database thử riêng

Cách đã kiểm chứng trên máy này: giữ FE dev ở5173, tại backend/ chạy .\scripts\run-isolated-mysql.ps1. Script dùng mysqld.exe cài sẵn, datadir riêng backend/var/mysql-it-*/data, cổng3307 chỉ bind127.0.0.1, tắt mysqlx, tài khoản riêng/mật khẩu ngẫu nhiên. MySQL80/cổng3306 và grant của nó không thay đổi. Sau test tắt instance, xóa file credentials tạm; giữ data để điều tra. Không Docker/Flyway.

Có thể dùng -ExistingData với đúng datadir test đã tạo để tiết kiệm khởi tạo; vẫn tạo schema UUID mới mỗi lần, không ghi đè/drop schema trước. Có backup local thì -CheckBackupRestore sẽ chạy thử restore tuần tự trước suite. FE dev5173 và Chrome cần sẵn sàng để kiểm tra trình duyệt với HTTP backend test/random port. Node binary hiện tại C:/Program Files/nodejs/node.exe; chỉnh ProcessBuilder nếu môi trường khác.

Tài khoản runtime local không có quyền CREATE DATABASE (1044), vì vậy không dùng nó để tạo test schema trong MySQL80 hiện tại. Cách thay thế thủ công, không còn bắt buộc: tài khoản quản trị chạy prepare-test-database.sql rồi run-integration.ps1 với schema rỗng. Không cần người dùng chạy script Workbench khi dùng native instance3307.

Từ đợt completion22/10, test bắt buộc TEST_DB_URL tại127.0.0.1:3307/schema smartprop_it_* và TEST_DB_USER/TEST_DB_PASSWORD riêng; không fallback credential/runtime3306. Schema phải rỗng. Nó sao chép cấu trúc bảng/constraint/index/generated column và trigger từ metadata hiện tại, không sao chép dữ liệu người dùng, không chạy Flyway/Docker. Chỉ chèn fixtures tổng hợp vào schema thử. Các bảng AI được sao chép cấu trúc rỗng để giữ toàn vẹn chuỗi FK; không chạy nghiệp vụ AI hoặc đọc rows AI. Sau test giữ nguyên schema và tệp trong TEMP để kiểm tra. Muốn chạy lại dùng schema thử rỗng mới; không tự drop/reset schema cũ. Không đưa mật khẩu vào chat hoặc command line.

## Triển khai HTTPS

1. Chuẩn bị máy chủ Java21/MySQL8 tương thích schema, tài khoản runtime DML và quyền metadata/TRIGGER cần thiết, không DDL. Schema production do người quản trị chuẩn bị, không tự migrate trong app.
2. Build FE với VITE_API_BASE_URL=/api/v1, đưa frontend/vue.ui/dist vào /srv/smartprop/frontend. Đưa JAR vào /srv/smartprop/backend. Không đưa file .env/source/secrets vào thư mục phục vụ web.
3. Tạo user hệ điều hành smartprop, /var/lib/smartprop/uploads do user đó sở hữu. Tạo /etc/smartprop/runtime.env từ production.env.example, quyền0600, cấp quyền đọc riêng cho service. Điền DB_PASSWORD, JWT_SECRET ngẫu nhiên ít nhất32 byte và domain HTTPS thực. Không dùng JWT secret dev.
4. Cài service smartprop.service. Backend chỉ listen127.0.0.1:8080, không mở trực tiếp8080/MySQL ra internet. Caddy là điểm nhận traffic tin cậy. Bật forwarded headers chỉ khi BE được bảo vệ phía sau proxy này.
5. Đặt SMARTPROP_DOMAIN trong môi trường service Caddy và DNS A/AAAA về máy chủ. Caddy phục vụ SPA, proxy /api/* và tự quản lý TLS khi có domain/cổng80/443 hợp lệ. Validate cấu hình bằng caddy validate --config /path/to/Caddyfile trước khi reload.
6. Kiểm tra health/readiness trực tiếp từ máy chủ; kiểm tra đăng nhập, CORS cùng domain, upload/tải tệp và route SPA sau reload. Chưa xác minh triển khai thật khi không có domain/máy chủ.

## Sao lưu và khôi phục

Trên Windows local: backend/scripts/backup-local.ps1. Script đã chạy thành công, checksum và việc xóa credentials tạm đã kiểm tra. Mặc định tạo backend/var/backups/smartprop-<thời gian>-<id>/ gồm database.sql, uploads và manifest.json có SHA256. Script đọc DB qua snapshot single-transaction, không khóa bảng và không DML; key file bất biến/xóa mềm giữ bytes nên chụp DB trước, copy file sau. Không chạy cleanup/purge đồng thời. Credentials chỉ ở file tạm riêng quyền Windows của người chạy, bị xóa trong finally; không truyền mật khẩu qua command line.

Backup chứa dữ liệu cá nhân/hash tài khoản: giữ ACL riêng, lưu bản sao ngoài máy và mã hóa ổ/backup theo hệ thống vận hành. Script không tự mã hóa, không đẩy backup ra dịch vụ ngoài. Kiểm tra manifest.complete=true, SHA256, đủ các storage_key được DB snapshot tham chiếu. Một folder không có manifest hoàn chỉnh không dùng để phục hồi.

Khôi phục luôn thử trên database mới, không import đè smartprop: tạo schema mới bằng tài khoản quản trị, nhập database.sql bằng mysql client với cấu hình credentials riêng, copy uploads vào thư mục riêng, trỏ DB_URL/STORAGE_ROOT của instance thử, chạy Hibernatevalidate và xác minh ảnh/bằng chứng/quyền. Sau khi đối chiếu số lượng/tham chiếu và kiểm thử người dùng, mới lên kế hoạch chuyển production có thời gian dừng. Restore drill đã thực thi thành công trên schema mới ở instance3307:35 bảng,0 tham chiếu tệp trong snapshot hiện tại; chưa suy rộng sang backup storage lớn.

## Retention và tệp không còn tham chiếu

Soft-delete giữ bytes để bảo toàn bằng chứng và backup. Chưa có chính sách lưu giữ pháp lý/thời hạn được chốt, vì vậy chưa tự xóa tệp. backend/scripts/audit-storage.ps1 liệt kê metadata keys bị thiếu và bytes không được tham chiếu; chế độ chỉ đọc, không purge. Tệp mồ côi có thể do crash giữa ghi file và commit. Chỉ lên lịch xóa sau khi chốt retention, có backup hợp lệ và kiểm tra không còn tham chiếu từ bản sao cần giữ.