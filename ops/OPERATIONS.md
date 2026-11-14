# Vận hành SmartProp

Các file ở đây là cấu hình chuẩn bị triển khai; chưa cấu hình domain, chứng chỉ hay đưa ứng dụng lên máy chủ thật. Caddyfile/service dùng Linux. Không chạy thay đổi máy chủ từ phiên phát triển Windows.

## Chạy local

Backend: backend/scripts/run-local.ps1 -Transport NIO2. FE: tại frontend/, npm run dev. Trang quản trị thực tế nằm cùng app: http://127.0.0.1:5173/admin/dashboard. Trang quản trị dùng cùng router Vue. Access token giữ memory; khi schema V10 và refresh được cấu hình đúng, cookie HttpOnly khôi phục phiên sau F5. Xem root README để bật refresh ở local; production phải dùng cookie Secure và HTTPS.

## Triển khai HTTPS

1. Chuẩn bị máy chủ Java21/MySQL8 tương thích schema, tài khoản runtime DML và quyền metadata/TRIGGER cần thiết, không DDL. Schema production do người quản trị chuẩn bị, không tự migrate trong app.
2. Build FE với VITE_API_BASE_URL=/api/v1, đưa frontend/dist vào /srv/smartprop/frontend. Đưa JAR vào /srv/smartprop/backend. Không đưa file .env/source/secrets vào thư mục phục vụ web.
3. Tạo user hệ điều hành smartprop, /var/lib/smartprop/uploads do user đó sở hữu. Tạo /etc/smartprop/runtime.env từ production.env.example, quyền0600, cấp quyền đọc riêng cho service. Điền DB_PASSWORD, JWT_SECRET ngẫu nhiên ít nhất32 byte và domain HTTPS thực. Không dùng JWT secret dev.
4. Cài service smartprop.service. Backend chỉ listen127.0.0.1:8080, không mở trực tiếp8080/MySQL ra internet. Caddy là điểm nhận traffic tin cậy. Bật forwarded headers chỉ khi BE được bảo vệ phía sau proxy này.
5. Đặt SMARTPROP_DOMAIN trong môi trường service Caddy và DNS A/AAAA về máy chủ. Caddy phục vụ SPA, proxy /api/* và tự quản lý TLS khi có domain/cổng80/443 hợp lệ. Validate cấu hình bằng caddy validate --config /path/to/Caddyfile trước khi reload.
6. Kiểm tra health/readiness trực tiếp từ máy chủ; kiểm tra đăng nhập, CORS cùng domain, upload/tải tệp và route SPA sau reload. Chưa xác minh triển khai thật khi không có domain/máy chủ.

## Sao lưu và khôi phục

Trên Windows local: backend/scripts/backup-local.ps1. Script đã chạy thành công, checksum và việc xóa credentials tạm đã kiểm tra. Mặc định tạo backend/var/backups/smartprop-<thời gian>-<id>/ gồm database.sql, uploads và manifest.json có SHA256. Script đọc DB qua snapshot single-transaction, không khóa bảng và không DML; key file bất biến/xóa mềm giữ bytes nên chụp DB trước, copy file sau. Không chạy cleanup/purge đồng thời. Credentials chỉ ở file tạm riêng quyền Windows của người chạy, bị xóa trong finally; không truyền mật khẩu qua command line.

Backup chứa dữ liệu cá nhân/hash tài khoản: giữ ACL riêng, lưu bản sao ngoài máy và mã hóa ổ/backup theo hệ thống vận hành. Script không tự mã hóa, không đẩy backup ra dịch vụ ngoài. Kiểm tra manifest.complete=true, SHA256, đủ các storage_key được DB snapshot tham chiếu. Một folder không có manifest hoàn chỉnh không dùng để phục hồi.

Khôi phục luôn thử trên database mới, không import đè smartprop: tạo schema mới bằng tài khoản quản trị, nhập database.sql bằng mysql client với cấu hình credentials riêng, copy uploads vào thư mục riêng, trỏ DB_URL/STORAGE_ROOT của instance thử, chạy Hibernatevalidate và xác minh ảnh/bằng chứng/quyền. Sau khi đối chiếu số lượng/tham chiếu và kiểm thử người dùng, mới lên kế hoạch chuyển production có thời gian dừng.

## Retention và tệp không còn tham chiếu

Soft-delete giữ bytes để bảo toàn bằng chứng và backup. Chưa có chính sách lưu giữ pháp lý/thời hạn được chốt, vì vậy chưa tự xóa tệp. backend/scripts/audit-storage.ps1 liệt kê metadata keys bị thiếu và bytes không được tham chiếu; chế độ chỉ đọc, không purge. Tệp mồ côi có thể do crash giữa ghi file và commit. Chỉ lên lịch xóa sau khi chốt retention, có backup hợp lệ và kiểm tra không còn tham chiếu từ bản sao cần giữ.
## Mã tin đăng listing_code — V16 (đã rollout local)

- Bảng `properties`, UUID `id` và các khóa ngoại được giữ nguyên. API trả `listingCode`; đây là trường chỉ đọc, không thuộc payload tạo/sửa.
- `property_listing_code_allocations` là sổ cấp số InnoDB AUTO_INCREMENT, không có FK cascade đến tin đăng. Giữ toàn bộ bảng này và trigger khi backup/restore; không purge/reset số cấp. Mã có thể có khoảng trống.
- Trigger INSERT tự cấp SP001…SP999, SP1000…; trigger UPDATE chặn đổi mã. Backfill bao gồm cả tin đã xóa mềm, theo `created_at, id`.
- Kiểm thử cô lập: từ root chạy `node backend/scripts/check-listing-codes.cjs`. Cần MySQL 8 binaries, Java 21 và Maven đã cache; script tạo MySQL riêng trong TEMP/cổng riêng, tự dừng đúng process đã tạo, không đọc .env hay dùng DB chính. Kết quả/log được giữ trong TEMP.
- Đã rollout local ngày 02/11/2026: localhost:3306/smartprop nâng V13 → V16 bằng Flyway sau backup và kiểm tra bản sao. Có 6 tin SP001–SP006, 0 mã null/rỗng/trùng; dữ liệu cũ của 42 bảng và khóa ngoại được đối chiếu giữ nguyên trước khi khởi động ứng dụng.
- Trước rollout: duyệt các migration còn thiếu V14–V16, sao lưu DB/upload, thử nâng cấp bản sao, dừng toàn bộ luồng ghi tin. MySQL DDL có implicit commit; không xem migration này là giao dịch có thể rollback toàn bộ.
- Migration cần quyền DDL/TRIGGER và quyền của trigger definer còn hiệu lực. Chỉ áp dụng bằng tài khoản quản lý schema đã được duyệt; không bật auto-migrate trong app.
- Chỉ build/cài và khởi động Backend mới sau khi schema đạt V16. Backend local đã cập nhật JAR và kiểm tra health/API thành công. Không chạy bản model này trên schema trước V16.
- Sau rollout kiểm tra `SELECT id, listing_code, title FROM properties ORDER BY created_at, id;` và `SELECT COUNT(*), COUNT(DISTINCT listing_code), SUM(listing_code IS NULL) FROM properties;`. Số tin/UUID phải khớp trước nâng cấp, số mã null bằng 0. Kiểm tra thêm tạo DRAFT bằng BROKER và hiển thị mã trong quản trị.

- Backup rollout V16: `backend/var/backups/smartprop-20261102-234920-174942` (database.sql và manifest SHA-256). Đã phục hồi thành công trên MySQL cô lập cổng riêng trước khi nâng DB chính.

## Cloudinary SP003 — đã rollout local V17 (03/11/2026)

- Đã thử nâng bản sao V16 → V17 và đồng bộ ảnh thật trước khi rollout localhost:3306/smartprop. Backup: backend/var/backups/smartprop-20261103-145024-9f3420; database.sql SHA-256: 9eec2935ab1ece62db54b3f0405e28bc79ca588688b2e11aa7320251ba788d32. Khi restore bản sao phải tạo đúng tài khoản DEFINER của trigger, cấp quyền trong schema thử; không sửa trigger đã áp dụng.
- SP003 UUID 2714133f-7f99-4d42-b4e7-63cb61bb5dfd, vẫn PUBLISHED; 6 JPEG / 701917 bytes từ asset_folder SmartProp/dev/properties/SP003, 1 trang metadata thực tế. Đã lưu URL, public_id, asset_id và cloud/folder trên property_images. Thứ tự 0–5, đúng 1 bìa; contentVersion 10 → 11. Chạy lại: created=0, updated=0, unchanged=6, version vẫn 11. SP004–SP006 không thay đổi; UUID, mã, dữ liệu nghiệp vụ và toàn bộ FK được giữ nguyên.
- Backend đọc CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET từ backend/.env.cloudinary.local (Git bỏ qua). backend/.env.cloudinary.local.example chỉ chứa mẫu trống. Không dùng VITE_ hoặc root .env đang được Git theo dõi cho secrets Cloudinary.
- V17 bổ sung storage_provider (LOCAL/CLOUDINARY), cloudinary_cloud_name, cloudinary_asset_id, cloudinary_public_id, cloudinary_secure_url, cloudinary_asset_folder. LOCAL vẫn yêu cầu storage_key; CLOUDINARY không cần tệp local. Unique (property_id, cloudinary_cloud_name, cloudinary_asset_id) chống trùng; giữ UUID ảnh cũ khi khớp asset_id hoặc bằng chứng SHA-256 thật của ảnh local. Không tự phục hồi ảnh đã xóa mềm.
- GET /api/v1/admin/properties/{UUID}/cloudinary-preview chỉ đọc metadata. POST /api/v1/admin/properties/{UUID}/cloudinary-sync với JSON {"expectedVersion":11} yêu cầu ADMIN ACTIVE, kiểm tra phiên bản và khóa tin trong transaction. Phân trang next_cursor có giới hạn và phát hiện cursor lặp; tối đa 30 ảnh/tin và 60 MB/lô. Không xóa tài nguyên Cloudinary.
- API ảnh hiện có giữ nguyên images[].url. Backend kiểm tra quyền rồi lấy ảnh từ đúng CDN/cloud, xác minh nội dung và SHA-256; không chuyển JWT/API Secret đến CDN hoặc trình duyệt. Ảnh local vẫn hoạt động. Popup GIS bổ sung ảnh bìa thật.
- CLI chỉ đọc mặc định: powershell -File backend/scripts/sync-cloudinary.ps1 -ListingCode SP003. Chỉ ghi khi thêm -Apply -OperatorId <ADMIN_ID> -ExpectedVersion <VERSION_MỚI_NHẤT>. Không dùng quyền của chủ tin thay ADMIN; không cấp role tự động. Loader đọc cấu hình DB local; kiểm tra đích trước khi chạy.
- Kiểm thử: node backend/scripts/check-cloudinary.cjs — 27 PASS (9 client, 5 delivery, 5 phân quyền media, 8 MySQL integration), MySQL/cổng/schema cô lập, mock HTTP; gồm phân trang, lỗi provider, không ghi một phần, concurrent sync, tái sử dụng local, unique và Hibernate validate. FE npm test: 126 PASS; FE/BE build thành công. Bản sao backup: migration và đồng bộ thật 6 ảnh, rerun không trùng PASS.
- Kiểm tra runtime local: Hibernate validate và health UP; GET 6 ảnh trả JPEG HTTP 200; Playwright thực tế PASS cho Home, Detail, popup GIS và liên kết đúng UUID. Backend đã khởi động lại với Flyway/seed tắt.
- Giới hạn: cần mạng tới Cloudinary để xem ảnh; các tin SP004–SP006 chưa có ảnh và chưa được tự đồng bộ. Backup chỉ có metadata Cloudinary; cần chính sách sao lưu bytes Cloudinary riêng nếu yêu cầu khôi phục độc lập nhà cung cấp. Không commit/push trong đợt này.
