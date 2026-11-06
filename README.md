# SmartProp

Ứng dụng bất động sản sử dụng Java21/Spring Boot, MySQL8 và React/Vite.

## Cấu trúc

- `backend/`: REST API, tài khoản/phân quyền, tin đăng, kiểm duyệt và tệp.
- `frontend/`: ứng dụng người dùng và ADMIN, chung router; quản trị tại `/admin/dashboard`.
- `database/`: migration V1–V17, schema tham chiếu và seed tùy chọn.
- `ai-services/`, `frontend/integrations/valuation-v6/`: dịch vụ/model hiện có, cấu hình riêng.
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

Tại `frontend/`:

```powershell
npm ci
node .\node_modules\vite\bin\vite.js --host 127.0.0.1 --port 5173 --strictPort
```

Mở `http://127.0.0.1:5173`, build bằng `npm run build`. Dev proxy chuyển `/api` về Backend loopback8080; production cần reverse proxy cùng domain. Cấu hình riêng trong `.env.local` theo `.env.example`; không đặt secrets Backend vào biến `VITE_`.

## Tài khoản và đăng tin

Đăng ký tạo BUYER. Người dùng xin quyền đăng tin ở Account; ADMIN xét duyệt riêng qua `/admin/broker-applications`. BROKER ACTIVE/ADMIN đăng tin theo quyền Backend, mỗi tin đi qua `DRAFT → PENDING → PUBLISHED`. Public chỉ thấy tin hợp lệ được duyệt.

Đăng ký quyền đăng tin cần V13 và `BROKER_APPLICATIONS_ENABLED=true` sau khi schema/rollout được phê duyệt; cấu hình mẫu giữ tính năng tắt.

Wizard ba bước: thông tin/giá → ảnh/vị trí → mô tả/liên hệ. Vị trí phải xác nhận; sửa địa chỉ yêu cầu xác nhận lại. OSM hỗ trợ ghim thủ công; Google/Geoapify cần key/cấu hình riêng. API trống/lỗi không thay bằng tin giả.

Home V3, Listings và Map dùng điều hướng/bộ lọc chung; giữ so sánh và bản đồ. Biểu đồ mô phỏng có nhãn, tách khỏi thống kê API thực. Ảnh/video Home nằm trong `frontend/public/`.

## Đăng nhập bền vững

Sau khi kiểm tra V10 và CORS/origin, bật root `.env`: `REFRESH_ENABLED=true`, `ACCESS_TOKEN_MINUTES=15`. FE `.env.local`: `VITE_ENABLE_REFRESH=true`, `VITE_API_BASE_URL=/api/v1`. Khởi động lại Backend/Vite và đăng nhập lại một lần để nhận cookie.

Access token ở memory, refresh cookie HttpOnly. BUYER/BROKER có phiên7ngày hoặc30ngày khi chọn ghi nhớ; ADMIN tối đa8giờ, idle30phút. Local HTTP loopback dùng `REFRESH_SECURE_COOKIE=false`; HTTPS phải đặttrue. Giữ cùng hostname khi đăng nhập/F5.

## Dữ liệu và vận hành

MySQL lưu dữ liệu nghiệp vụ; ảnh/tài liệu ở `backend/var/uploads` hoặc `STORAGE_ROOT`. Giữ `.env`, uploads, backup, dependencies, build output và test/evidence local ngoài Git. Property Importer là công cụ độc lập, không thuộc bản source này.

Xem [Backend](backend/README.md), [Frontend](frontend/README.md), [Database](database/README.md), [vận hành/backup](ops/OPERATIONS.md).

## Đồng bộ các nhánh

Bản hợp nhất giữ đăng nhập bền vững, duyệt quyền BROKER và Home V3 từ Backend-Huy; bổ sung định giá v6, lịch sử riêng tư và dữ liệu nghiên cứu từ các nhánh đã nằm trong feature/apartment-pilot-100. Dữ liệu nghiên cứu trên Git không tự trở thành tin công khai trong MySQL.

Trang /valuation dùng API AI v6 chuẩn tại ai-services/run_api.py, qua proxy /api/ai. Chuẩn bị môi trường bằng backend/scripts/setup-valuation-runtime.ps1, chạy AI bằng backend/scripts/run-valuation.ps1. Không tự chạy crawler hoặc training khi khởi động web.

Migration V13__broker_applications.sql của môi trường Backend-Huy được giữ nguyên. Lịch sử định giá nằm trong V14__valuation_history.sql và cần phê duyệt rollout riêng. Chưa áp dụng V14 thì các API lịch sử báo chưa sẵn sàng. Môi trường đã dùng V13__valuation_history.sql từ nhánh khác phải đối chiếu Flyway history riêng trước rollout; không đổi migration đã áp dụng hoặc chạy clean/reset.

## Chạy nhanh bằng terminal Windows

Mở hai terminal PowerShell trong VS Code và giữ cả hai chạy. MySQL service MYSQL80 phải ở trạng thái Running.

Terminal 1 — Backend:

```powershell
cd D:\C2SE.01CMU\code\SmartProp
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run-local.ps1 -Transport NIO2
```

Terminal 2 — Frontend:

```powershell
cd D:\C2SE.01CMU\code\SmartProp\frontend
node .\node_modules\vite\bin\vite.js --host 127.0.0.1 --port 5173 --strictPort
```

Mở http://127.0.0.1:5173/home. Kiểm tra Backend: http://127.0.0.1:8080/actuator/health. Nhấn Ctrl+C ở từng terminal để dừng.

Nếu MySQL chưa chạy, mở PowerShell với quyền Administrator và chạy `Start-Service MYSQL80`. Không cần chạy lại migration mỗi lần khởi động. Launcher Backend tự nạp root .env và backend/.env.cloudinary.local.

Chỉ khi sửa code Java hoặc chưa có JAR: dừng Backend, tại root chạy `powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run-maven.ps1 -B -Dmaven.test.skip=true package`, rồi khởi động lại Terminal 1. Nếu Frontend chưa có node_modules, chạy `npm ci` tại frontend trước khi chạy dev.

## Đồng bộ develop-binh ngày 04/11/2026

Nguồn: team/develop-binh tại 3235182. Nhánh làm việc: sync/develop-binh-20261104. Mốc local trước hợp nhất: e3441bc. Giữ Vue, cấu trúc modules/features, GIS tương tác và ảnh Cloudinary. .env giữ riêng trên máy và không còn thuộc snapshot Git mới.

Migration V16 của develop-binh là lịch sử khác V16 listing_code đã áp dụng local. Bản nguyên gốc được lưu tại database/upstream-develop-binh/standard-migrations/V16__crawler_external_listings.sql, ngoài thư mục migration chuẩn. Không chạy profile standard-migrations hoặc legacy-hybrid-local trên database local hiện tại. Cần thiết kế migration kế tiếp riêng nếu muốn bổ sung external_listings; đồng bộ code không đồng nghĩa đã nhập dataset hoặc rollout schema của nhánh Bình.

Các màn hình advisor/chat đã có code; dịch vụ AI, bộ dữ liệu nghiên cứu, Python dependencies và cổng chat 8001 cần cấu hình riêng theo README/ai-services/RAG.md. Không tự bật nghiên cứu, crawler hoặc import dữ liệu trong đợt đồng bộ này.
