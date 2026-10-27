# SmartProp

Ứng dụng bất động sản sử dụng Java21/Spring Boot, MySQL8 và Vue3/Vite.

## Cấu trúc

- `backend/`: REST API, tài khoản/phân quyền, tin đăng, kiểm duyệt và tệp.
- `frontend/vue.ui/`: ứng dụng người dùng và ADMIN, chung router; quản trị tại `/admin/dashboard`.
- `database/`: migration V1–V13, schema tham chiếu và seed tùy chọn.
- `ai-services/`, `integrations/valuation-v6/`: dịch vụ/model hiện có, cấu hình riêng.
- `ops/`: cấu hình triển khai HTTPS/service và hướng dẫn backup/restore.

## Chạy Backend

Cần JDK21, MySQL và schema đã được người quản trị chuẩn bị. Tạo `.env` ở root theo `.env.example`; không ghi đè cấu hình riêng đang dùng hoặc đưa secrets lên Git.

Tại `backend/`:

```powershell
.\mvnw.cmd -B -Dmaven.test.skip=true package
.\scripts\run-local.ps1 -Transport NIO2
```

Nếu Maven đã cache, có thể dùng `scripts/run-maven.ps1`. Dừng Backend trước khi package nếu Windows khóa JAR. API ở `http://127.0.0.1:8080/api/v1`; health ở `/actuator/health`.

Launcher tắt Flyway, SQL init và seed; Hibernate chỉ validate. Đóng gói không tự chạy migration. Không sửa migration đã áp dụng hoặc reset DB để khởi động app. Tính năng mở rộng chỉ bật khi schema/cấu hình đã được kiểm tra và phê duyệt.

## Chạy Frontend

Tại `frontend/vue.ui/`:

```powershell
npm ci
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Mở `http://127.0.0.1:5173`, build bằng `npm run build`. Dev proxy chuyển `/api` về Backend loopback8080; production cần reverse proxy cùng domain. Cấu hình riêng trong `.env.local` theo `.env.example`; không đặt secrets Backend vào biến `VITE_`.

## Tài khoản và đăng tin

Đăng ký tạo BUYER. Người dùng xin quyền đăng tin ở Account; ADMIN xét duyệt riêng qua `/admin/broker-applications`. BROKER ACTIVE/ADMIN đăng tin theo quyền Backend, mỗi tin đi qua `DRAFT → PENDING → PUBLISHED`. Public chỉ thấy tin hợp lệ được duyệt.

Đăng ký quyền đăng tin cần V13 và `BROKER_APPLICATIONS_ENABLED=true` sau khi schema/rollout được phê duyệt; cấu hình mẫu giữ tính năng tắt.

Wizard ba bước: thông tin/giá → ảnh/vị trí → mô tả/liên hệ. Vị trí phải xác nhận; sửa địa chỉ yêu cầu xác nhận lại. OSM hỗ trợ ghim thủ công; Google/Geoapify cần key/cấu hình riêng. API trống/lỗi không thay bằng tin giả.

Home V3, Listings và Map dùng điều hướng/bộ lọc chung; giữ so sánh, bản đồ và công cụ tài chính. Biểu đồ mô phỏng có nhãn, tách khỏi thống kê API thực. Ảnh/video Home nằm trong `frontend/vue.ui/public/`.

## Đăng nhập bền vững

Sau khi kiểm tra V10 và CORS/origin, bật root `.env`: `REFRESH_ENABLED=true`, `ACCESS_TOKEN_MINUTES=15`. FE `.env.local`: `VITE_ENABLE_REFRESH=true`, `VITE_API_BASE_URL=/api/v1`. Khởi động lại Backend/Vite và đăng nhập lại một lần để nhận cookie.

Access token ở memory, refresh cookie HttpOnly. BUYER/BROKER có phiên7ngày hoặc30ngày khi chọn ghi nhớ; ADMIN tối đa8giờ, idle30phút. Local HTTP loopback dùng `REFRESH_SECURE_COOKIE=false`; HTTPS phải đặttrue. Giữ cùng hostname khi đăng nhập/F5.

## Dữ liệu và vận hành

MySQL lưu dữ liệu nghiệp vụ; ảnh/tài liệu ở `backend/var/uploads` hoặc `STORAGE_ROOT`. Giữ `.env`, uploads, backup, dependencies, build output và test/evidence local ngoài Git. Property Importer là công cụ độc lập, không thuộc bản source này.

Xem [Backend](backend/README.md), [Frontend](frontend/README.md), [Database](database/README.md), [vận hành/backup](ops/OPERATIONS.md).
