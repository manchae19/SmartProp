# SmartProp

Ứng dụng bất động sản sử dụng Java 21/Spring Boot, MySQL và Vue 3/Vite.

## Cấu trúc

- backend/: REST API, phân quyền, tin đăng, ảnh, yêu thích, báo cáo, liên hệ, thông báo và các module mở rộng.
- frontend/vue.ui/: ứng dụng Vue đang sử dụng; trang quản trị ở /admin/dashboard trong cùng ứng dụng.
- database/migrations/: migration V1–V12; database/seeds/: dữ liệu seed tùy chọn.
- ai-services/ và integrations/valuation-v6/: mã dịch vụ và model hiện có.
- ops/: cấu hình triển khai và công cụ vận hành.

## Chạy Backend

Cần JDK 21, MySQL và database được chuẩn bị đúng schema. Điền cấu hình riêng trong .env từ .env.example; không đưa mật khẩu hoặc JWT secret lên Git.

PowerShell tại backend/:

~~~powershell
.\mvnw.cmd -B -Dmaven.test.skip=true package
.\scripts\run-local.ps1 -Transport NIO2
~~~

Nếu Maven đã được cache, có thể dùng .\scripts\run-maven.ps1 thay wrapper. Backend mặc định ở http://localhost:8080. Các script chạy local giữ Flyway/SQL init/seed tắt; không tự thay database. Không sửa migration đã áp dụng. Những module cần V8–V12 chỉ được bật sau khi schema/cấu hình được người quản trị duyệt.

## Chạy Frontend

PowerShell tại frontend/vue.ui/:

~~~powershell
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
~~~

Mở http://127.0.0.1:5173. Build bằng npm run build. API base, Google Maps và refresh opt-in xem .env.example trong thư mục FE. Không đưa secret Backend vào biến VITE_.

## Vận hành

Giữ database MySQL, backend/var/uploads và các bản backup riêng ngoài Git. Script backup-local.ps1 và audit-storage.ps1 nằm trong backend/scripts/. Cấu hình deployment mẫu ở ops/; cần điều chỉnh domain, HTTPS và secrets trước khi triển khai.

Đợt dọn repository đã bỏ tài liệu báo cáo, source test Backend/Frontend và kết quả UI test. Các thay đổi nghiệp vụ trước đó vẫn được giữ; đợt dọn chỉ kiểm tra build, không chạy lại test đã xóa.

## Đăng bán / cho thuê

Luồng /post có 3 bước: thông tin & giá → ảnh & vị trí → mô tả & liên hệ. Lưu nháp tài khoản cần đủ các trường Backend bắt buộc và ghim đã xác nhận; gửi duyệt cần ít nhất một ảnh. Nháp chưa lưu server được ghi rõ là nháp trình duyệt, tách theo tài khoản và mã tin. Ảnh chưa tải chỉ được giữ trong tab; tải lại trang cần chọn lại các ảnh đó.

Chưa có Google key vẫn chọn được ghim thủ công qua bản đồ OpenStreetMap. Đặt VITE_OSM_TILE_URL khi dùng tile provider khác và tuân thủ attribution/cache của provider. Không có ảnh bản đồ thì không tự gán vị trí.

Để dùng gợi ý Google, đặt VITE_GOOGLE_MAPS_API_KEY và VITE_GOOGLE_MAPS_MAP_ID trong frontend/vue.ui/.env.local rồi khởi động lại Vite. Owner cần chuẩn bị Maps JavaScript API và Places API (New), giới hạn browser key theo HTTP referrer và đúng API; không gửi key vào chat/Git. Task không tự bật API hoặc billing. Gợi ý Places chỉ hiện trên Google trong phiên; không serialize toàn bộ Place, địa chỉ gợi ý hoặc tọa độ gợi ý vào nháp. Người đăng nhập địa chỉ của mình, chủ động đặt/kéo ghim rồi xác nhận vị trí. Không dùng kết quả Google làm cache lâu dài hoặc chuyển gợi ý Google sang bản đồ khác.

Khi thay địa chỉ/phường/quận/thành phố, ghim cũ bị xóa và cần xác nhận lại. Nếu mất phản hồi tạo tin/tải ảnh, dùng nút Đối chiếu kết quả; hệ thống không tự tạo thêm tin hoặc tải lặp trong lúc chưa xác định được kết quả.

API giữ các trường số hiện có; response property có thêm priceExact/areaSqmExact dạng chuỗi để mở lại tin mà không làm tròn số thập phân lớn. Không đổi schema hoặc quy trình nháp → chờ duyệt → ADMIN phê duyệt.
