# SmartProp — Cài đặt, build và chạy dự án

SmartProp sử dụng **React + Vite**, **Java 21 / Spring Boot**, **MySQL Spatial**, dịch vụ định giá **XGBoost v6** và chatbot **RAG + Ollama/Qwen**.

Hướng dẫn chính dành cho Windows/PowerShell; phần cuối mô tả triển khai máy chủ Linux/HTTPS. Thay đường dẫn ví dụ bằng thư mục clone trên máy của bạn. Chạy lệnh từ **root repository**, trừ khi có ghi khác.

## 1. Cấu trúc và các dịch vụ

```text
SmartProp/
├── frontend/                  # React, router, UI và API client
│   ├── src/app/               # Entry point và router
│   ├── src/features/          # Các chức năng nghiệp vụ
│   ├── src/shared/            # Component, hook, state và tiện ích chung
│   ├── public/                # Ảnh/video tĩnh
│   ├── build/                 # Plugin Vite: là source, không xóa
│   ├── server/                # Chat relay cho triển khai production
│   └── integrations/valuation-v6/ # Bundle định giá đã pin
├── backend/                   # Spring Boot REST API
│   ├── src/main/java/vn/smartprop/modules/
│   └── scripts/               # Launcher, cấu hình và backup
├── database/migrations/       # Migration chuẩn V1–V19
├── ai-services/               # API định giá và chatbot/RAG
├── ops/                       # Mẫu service, HTTPS và hướng dẫn vận hành
├── .env.example               # Mẫu cấu hình Backend/MySQL
└── docker-compose.yml         # Chỉ dựng MySQL, không dựng toàn hệ thống
```

| Thành phần | Địa chỉ local | Vai trò |
|---|---|---|
| Frontend | http://127.0.0.1:5173 | Giao diện người dùng và quản trị |
| Backend | http://127.0.0.1:8080/api/v1 | Tài khoản, tin đăng, GIS, phân quyền |
| MySQL | localhost:3306 | Database `smartprop` |
| AI định giá | http://127.0.0.1:8000 | API model v6 |
| Chatbot/RAG | http://127.0.0.1:8001 | Hội thoại, truy xuất bằng chứng và recommendation |
| Ollama | http://127.0.0.1:11434 | Chạy model `qwen3:4b-instruct` |

Frontend gọi cùng origin: `/api/v1` → Backend, `/api/ai` → định giá, `/api/chat` → RAG. Vite cấu hình proxy khi phát triển. **Bản build tĩnh không tự có proxy này.**

## 2. Yêu cầu trên máy mới

- Git; JDK **21** với `JAVA_HOME` hợp lệ.
- Node.js **22.12 trở lên thuộc nhánh 22**, hoặc phiên bản đáp ứng `frontend/package.json`; có npm.
- MySQL **8.0/8.4** có hỗ trợ Spatial, đúng phiên bản tương thích với backup đang nhận. Docker Compose hiện pin MySQL **8.4.9**.
- PowerShell trên Windows. Maven Wrapper đi kèm repository, không bắt buộc cài Maven toàn máy.
- Nếu dùng chatbot: Python **3.11**, Ollama và model Qwen được nêu bên dưới.
- Nếu dùng định giá: launcher cài Python **3.14.8** riêng cùng dependency đã khóa; không dùng chung venv RAG.
- Internet cho lần tải npm/Maven/Python/model đầu tiên và các dịch vụ như Cloudinary, Geoapify, Google Login, OSM tiles. Chạy AI cần đủ RAM; kiểm tra tài nguyên theo máy thực tế.

Kiểm tra trước khi cài:

```powershell
git --version
java -version
node --version
npm --version
py -3.11 --version
```

## 3. Clone từ Git và cập nhật code

```powershell
git clone --branch Backend-Huy --single-branch https://github.com/manchae19/SmartProp.git SmartProp
cd SmartProp
git status
```

Dùng đúng branch/commit nhóm đã thống nhất nếu khác `Backend-Huy`. Hướng dẫn này áp dụng cho cấu trúc React hiện tại; thay đổi còn nằm trên máy tác giả phải được commit/push trước thì máy khác mới lấy được.

Lần cập nhật sau, kiểm tra và giữ lại thay đổi local trước:

```powershell
git status
git pull --ff-only
```

Không dùng reset/clean để xử lý thay đổi chưa lưu. Sau khi pull: cài lại dependency khi lockfile thay đổi, build lại phần đã đổi và kiểm tra migration trước khi khởi động Backend mới.

**Git không mang theo** database đang chạy, bài đăng/tài khoản, uploads, `.env`, API secrets, venv, model local, index RAG, `node_modules`, `target` hoặc `dist`. Muốn máy khác có cùng bài đăng phải bàn giao backup DB cùng tệp tương ứng, hoặc dùng database dùng chung đã được quản trị cấu hình.

## 4. Cấu hình local

### 4.1. Backend và MySQL

Chỉ sao chép mẫu khi file chưa tồn tại:

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

Mở `.env`, thay các giá trị mẫu bằng cấu hình riêng:

```dotenv
DB_URL=jdbc:mysql://localhost:3306/smartprop?connectionTimeZone=UTC
DB_USER=smartprop
DB_PASSWORD=<mat-khau-database-cua-may-nay>
MYSQL_ROOT_PASSWORD=<mat-khau-root-neu-dung-Docker>
JWT_SECRET=<chuoi-ngau-nhien-it-nhat-32-byte>
CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
SPRING_PROFILES_ACTIVE=dev

REFRESH_ENABLED=true
REFRESH_SECURE_COOKIE=false
ACCESS_TOKEN_MINUTES=15
BROKER_APPLICATIONS_ENABLED=true
PROFILE_AVATAR_ENABLED=true
```

Các dòng `<...>` là placeholder, phải thay trước khi chạy. Những cờ trên chỉ bật khi schema tương ứng đã sẵn sàng; bản source hiện tại yêu cầu lineage chuẩn đến V19. `REFRESH_SECURE_COOKIE=false` chỉ dành cho HTTP loopback local; HTTPS phải dùng `true`.

Tạo JWT secret bằng bộ sinh ngẫu nhiên rồi lưu riêng; không dùng mật khẩu demo làm JWT secret. Có thể tạo bằng PowerShell:

```powershell
$bytes = New-Object byte[] 48
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
[Convert]::ToBase64String($bytes)
```

`STORAGE_ROOT` tùy chọn; mặc định `backend/var/uploads` khi chạy launcher. Nếu đổi máy/thư mục lưu tệp, nên dùng đường dẫn tuyệt đối và cấp quyền cho tài khoản chạy Backend.

Spring Boot **không tự đọc root `.env`**. `run-local.ps1` nạp file này; chạy `java -jar` trực tiếp cần tự cung cấp environment. Không ghi token, mật khẩu hoặc API Secret vào biến `VITE_`.

### 4.2. Frontend

```powershell
if (!(Test-Path frontend/.env.local)) {
    Copy-Item frontend/.env.example frontend/.env.local
}
```

Các giá trị chính trong `frontend/.env.local`:

```dotenv
VITE_API_BASE_URL=/api/v1
VITE_ENABLE_REFRESH=true
BE_API_TARGET=http://127.0.0.1:8080
AI_API_TARGET=http://127.0.0.1:8000
VITE_OSM_TILE_URL=https://tile.openstreetmap.org/{z}/{x}/{y}.png
```

Giữ `VITE_ENABLE_REFRESH` đồng bộ với Backend. Dùng thống nhất **127.0.0.1:5173** khi mở web, đăng nhập và cấu hình OAuth; `localhost` là hostname khác đối với cookie/callback. Sửa biến `VITE_*` phải khởi động lại Vite hoặc build lại FE.

### 4.3. Dịch vụ tùy chọn

| Dịch vụ | Cấu hình |
|---|---|
| Geoapify Geocoding/Places | Root `.env`: `GEOCODING_ENABLED=true`, `GEOCODING_PROVIDER=GEOAPIFY`, `GEOAPIFY_API_KEY=...` |
| Cloudinary | Tạo `backend/.env.cloudinary.local` từ file `.example` cùng tên; điền `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` |
| Google Login | Root `.env`: `GOOGLE_LOGIN_ENABLED=true`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_FRONTEND_ORIGIN`, `GOOGLE_REDIRECT_URI`; cần refresh session và schema V15+ |
| Email SMTP | Cần cấu hình SMTP, payload key và cờ email/worker; mặc định đang tắt, không chỉ điền SMTP là tự bật |

Google OAuth Client phải là **Web application**, đăng ký chính xác callback local:

```text
http://127.0.0.1:5173/api/v1/auth/oauth2/callback/google
```

Máy/domain khác phải đăng ký callback tương ứng và cập nhật CORS/origin/cookie. OAuth Client ID/Secret không phải Google Maps key. Tài khoản ngoài danh sách test users có thể bị chặn nếu ứng dụng OAuth còn ở chế độ testing.

Không cần key Google Maps khi dùng OSM + Geoapify. Nếu thiếu dịch vụ tìm địa chỉ, giữ ghim thủ công; không thay bằng tọa độ giả. Không commit các file cấu hình thật hoặc OAuth JSON.

## 5. Chuẩn bị database — chọn đúng một hướng

Backend mặc định **Flyway tắt**, SQL init tắt, seed tắt; Hibernate chỉ `validate`. Build JAR không tự tạo bảng. Không sửa các migration đã áp dụng hoặc nhập `schema-reference.sql` như một migration.

### 5.1. Database hoàn toàn mới

Chỉ áp dụng cho instance/schema mới được quản trị cho phép. Có thể dùng MySQL cài sẵn hoặc Docker; không chạy cả hai chồng cổng 3306.

**Cách A — MySQL có sẵn:** quản trị viên tạo schema/user. Ví dụ local, thay mật khẩu trước khi thực thi trong MySQL client:

```sql
CREATE DATABASE smartprop CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'smartprop'@'localhost' IDENTIFIED BY 'REPLACE_WITH_DB_PASSWORD';
GRANT ALL PRIVILEGES ON smartprop.* TO 'smartprop'@'localhost';
```

Quyền `ALL` trong ví dụ chỉ dành cho chuẩn bị local. Máy chủ thật cần tách tài khoản migration có DDL/TRIGGER với tài khoản runtime theo quyền cần thiết.

**Cách B — MySQL Docker:** điền hai mật khẩu trong root `.env`, rồi:

```powershell
docker compose up -d mysql
docker compose ps
```

Compose chỉ tạo database/user và volume MySQL, **chưa áp migration**. Không xóa volume hoặc dùng `docker compose down -v` để sửa lỗi.

Sau khi kiểm tra `DB_URL` đúng schema mới, chạy Flyway bằng Maven Wrapper:

```powershell
. .\backend\scripts\load-env.ps1
Push-Location backend
try {
    .\mvnw.cmd -B flyway:info
    .\mvnw.cmd -B flyway:migrate
    .\mvnw.cmd -B flyway:validate
} finally { Pop-Location }
```

Nếu Wrapper chưa có Maven, lần đầu cần mạng để tải phiên bản được pin. Khi đã cache, có thể thay `mvnw.cmd` bằng `scripts/run-maven.ps1` trong thư mục `backend`.

### 5.2. Nhận dữ liệu từ máy thành viên khác

1. Nhận backup qua kênh riêng: `database.sql`, `manifest.json`, uploads và cấu hình cần thiết; không đưa backup chứa dữ liệu cá nhân lên Git.
2. Kiểm tra backup hoàn chỉnh và SHA-256 theo manifest. Khôi phục vào schema mới/cô lập trước, không ghi đè database đang có dữ liệu.
3. DBA kiểm tra dump có `USE`, tên schema, trigger và `DEFINER` trước khi import. Tài khoản definer phải tồn tại và có quyền phù hợp; không tự xóa trigger hoặc sửa migration để bỏ lỗi.
4. Import bằng MySQL Workbench hoặc mysql client có thông tin đăng nhập riêng. Không truyền mật khẩu thật trực tiếp trên command line.
5. Khôi phục uploads vào đúng `STORAGE_ROOT`; đối chiếu UUID tin/ảnh và số lượng bản ghi. Cloudinary cần còn tài nguyên nguồn; backup metadata không thay thế backup bytes ảnh.
6. Trỏ cấu hình instance thử tới bản sao, chạy `flyway:info` và `flyway:validate`. Nếu thiếu migration, lập kế hoạch nâng cấp bản sao rồi mới duyệt rollout.

Pull Git không tự tạo tài khoản ADMIN hay mang bài đăng từ máy khác sang. Mã ngắn `listing_code`, sổ cấp mã và trigger cần được giữ cùng database; không reset hoặc tự đánh lại mã.

### 5.3. Database đã tồn tại hoặc đến từ nhánh khác

Không chạy hướng dẫn tạo mới/migrate một cách máy móc. Nhóm từng có các lineage migration khác nhau với số phiên bản trùng nhau. So sánh **version + tên migration + checksum**, không chỉ nhìn số dòng history.

Lineage chuẩn hiện tại dùng V13 broker applications, V14 valuation history, V15 Google/avatar, V16 listing code, V17 Cloudinary, V18 external listing support, V19 advisor preferences. Các thư mục `legacy-hybrid-local`, `research-migrations`, `upstream-develop-binh` không được tự ghép vào `database/migrations`.

Nếu validate báo checksum mismatch hoặc bảng/cột thiếu: dừng, sao lưu và đối chiếu với người quản trị. Không dùng Flyway clean/repair/baseline hoặc `ddl-auto=update` để ép ứng dụng chạy.

## 6. Cài dependency và build FE/BE

### Backend

```powershell
Push-Location backend
try {
    .\mvnw.cmd -B "-Dmaven.test.skip=true" package
} finally { Pop-Location }
```

JAR đầu ra: `backend/target/smartprop-backend-0.1.0.jar`. Lệnh trên bỏ qua test; build thành công không thay thế kiểm tra chạy thực tế. Nếu Windows khóa JAR, dừng Backend đang dùng JAR đó rồi build lại.

### Frontend

```powershell
Push-Location frontend
try {
    npm ci
    npm run build
} finally { Pop-Location }
```

Đầu ra: `frontend/dist/`. Dùng `npm ci` để cài đúng lockfile; không xóa `package-lock.json` để xử lý lỗi dependency. Không sao chép `node_modules` từ máy khác.

## 7. Chuẩn bị chatbot trên máy mới — một lần

Bỏ qua mục này nếu chỉ cần FE/BE. Chatbot cần cả Backend V1.1, corpus, E5/FAISS và Ollama; chỉ chạy Frontend không đủ.

### 7.1. Venv RAG và dependency CPU

```powershell
py -3.11 -m venv .scratch/rag-venv
& .\.scratch\rag-venv\Scripts\python.exe -m pip install --upgrade pip
& .\.scratch\rag-venv\Scripts\python.exe -m pip install "torch==2.9.1+cpu" --index-url https://download.pytorch.org/whl/cpu
& .\.scratch\rag-venv\Scripts\python.exe -m pip install -r .\ai-services\requirements-rag-ollama.txt
```

Không dùng venv định giá cho RAG và không sao chép nguyên venv giữa các máy. Giữ các phiên bản trong requirements; nếu hệ điều hành/Python không có wheel phù hợp, kiểm tra lại môi trường trước khi đổi phiên bản.

### 7.2. Tải E5 đúng revision

Thao tác này tải model rõ ràng trong bước chuẩn bị, không diễn ra khi người dùng gửi chat:

```powershell
$env:E5_DEST = Join-Path (Get-Location) '.scratch/rag-models/multilingual-e5-small'
& .\.scratch\rag-venv\Scripts\python.exe -c "import os; from huggingface_hub import snapshot_download; snapshot_download(repo_id='intfloat/multilingual-e5-small', revision='614241f622f53c4eeff9890bdc4f31cfecc418b3', local_dir=os.environ['E5_DEST'])"
```

Cần có `.scratch/rag-models/multilingual-e5-small/config.json` cùng đầy đủ tokenizer/weights. Nếu nhận model từ nhóm, giữ đúng snapshot/revision. Khi phục vụ, launcher bật offline và không tự tải weights.

### 7.3. Ollama/Qwen

Cài và mở Ollama, sau đó tải model một lần:

```powershell
ollama pull qwen3:4b-instruct
ollama list
```

Nếu Ollama chưa chạy, mở terminal riêng với `ollama serve`. Không mở thêm instance nếu cổng 11434 đã được sử dụng. Launcher RAG kiểm tra đúng tên model và pin digest của model đang cài.

## 8. Chuẩn bị AI định giá — một lần

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\setup-valuation-runtime.ps1
```

Script tạo runtime riêng tại `backend/var/valuation-v6-runtime`, xác minh checksum Python/pip và cài wheel theo `frontend/integrations/valuation-v6/requirements-windows.lock`. Cần mạng lần đầu; không cài vào Python toàn máy.

Bundle model v6, manifest và source đóng băng phải đầy đủ. Không xóa/gộp `frontend/integrations/valuation-v6` chỉ vì tên thư mục; launcher hiện vẫn sử dụng bundle này. Không cần crawler/training để chạy web.

## 9. Chạy local hằng ngày

Thứ tự: **MySQL + Ollama → Backend → định giá/RAG → Frontend**. Mở các terminal riêng, giữ chúng chạy. Trong mỗi terminal, `cd` về root thư mục đã clone.

### Terminal 1 — Backend

```powershell
cd D:\C2SE.01CMU\code\SmartProp
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run-local.ps1 -Transport NIO2 -Chat -Valuation
```

- `-Chat`: bật recommendation `HEURISTIC_V1_1`, giữ research/external unverified tắt. Thiếu cờ này có thể làm chatbot từ chối kết quả dù health Backend UP.
- `-Valuation`: bật API tham khảo giá cho form đăng tin qua dịch vụ v6.
- Launcher không chạy migration, không tự tạo ADMIN và không seed dữ liệu.
- Nếu chỉ cần FE/BE, có thể bỏ `-Chat -Valuation`; các chức năng phụ thuộc AI sẽ chưa sẵn sàng.

### Terminal 2 — Định giá v6

```powershell
cd D:\C2SE.01CMU\code\SmartProp
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run-valuation.ps1
```

### Terminal 3 — Chatbot/RAG

Đợi Backend health UP rồi chạy:

```powershell
cd D:\C2SE.01CMU\code\SmartProp
powershell -NoProfile -ExecutionPolicy Bypass -File .\ai-services\scripts\run-chat-local.ps1
```

Launcher lấy snapshot amenities công khai, tạo corpus/index local rồi phục vụ cổng 8001. Không crawl hoặc import database. Corpus có thời hạn 24 giờ; khởi động lại launcher để làm mới từ API. Research và SQL trực tiếp được giữ tắt.

Cấu hình hiện tại yêu cầu Backend `127.0.0.1:8080` và Ollama `127.0.0.1:11434`; đổi cổng Backend bằng `-Port` không tự đổi được peer mà RAG chấp nhận.

### Terminal 4 — Frontend

```powershell
cd D:\C2SE.01CMU\code\SmartProp\frontend
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Mở **http://127.0.0.1:5173/home**. Quản trị: `/admin/dashboard`; chatbot: `/advisor/chat`; định giá: `/valuation`.

Dừng từng dịch vụ bằng Ctrl+C tại terminal tương ứng. Chỉ chạy một instance cho mỗi cổng. Lần mở máy tiếp theo không cần `npm ci`, tải model hoặc migrate lại nếu source/dependency/schema không đổi.

## 10. Tài khoản và quyền đăng tin

- Đăng ký qua web tạo **BUYER**. Người dùng xin quyền đăng tin tại Account; ADMIN duyệt hồ sơ để có quyền BROKER.
- BROKER ACTIVE/ADMIN tạo tin theo phân quyền Backend; tin đi qua `DRAFT → PENDING → PUBLISHED`.
- Đăng nhập ADMIN chỉ có khi database đã có tài khoản đó; repository không cung cấp mật khẩu ADMIN chung.
- Backend kiểm tra quyền thật; thay UI hoặc localStorage không cấp được quyền.

### ADMIN đầu tiên trên database development mới

Nếu không phục hồi tài khoản từ backup, người phụ trách được phép có thể dùng `DevAdminSeed` **một lần trên database development mới**, không dùng cho production hoặc để nâng quyền user hiện có. Mật khẩu tối thiểu 12 ký tự và tối đa 72 byte UTF-8.

```powershell
. .\backend\scripts\load-env.ps1
$env:DEV_ADMIN_EMAIL = Read-Host 'Email ADMIN development moi'
$adminPassword = Read-Host 'Mat khau ADMIN development' -AsSecureString
$env:DEV_ADMIN_PASSWORD = [Net.NetworkCredential]::new('', $adminPassword).Password
Push-Location backend
try {
    java -jar .\target\smartprop-backend-0.1.0.jar --spring.profiles.active=dev --app.seed.enabled=true --spring.flyway.enabled=false --spring.sql.init.mode=never --spring.jpa.hibernate.ddl-auto=validate --app.database-seed.enabled=false
} finally {
    Remove-Item Env:DEV_ADMIN_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:DEV_ADMIN_EMAIL -ErrorAction SilentlyContinue
    $adminPassword = $null
    Pop-Location
}
```

Dừng Backend thường trước khi chạy lệnh này. Sau khi xác nhận tạo tài khoản, Ctrl+C và chạy lại launcher bình thường ở mục 9. Seed từ chối nâng role tài khoản đã tồn tại. Chỉ điền `DEV_ADMIN_ENABLED` trong `.env` không bật được seed vì launcher bình thường luôn truyền `app.seed.enabled=false`.

## 11. Kiểm tra sau cài đặt

```powershell
Invoke-RestMethod http://127.0.0.1:8080/actuator/health
Invoke-RestMethod http://127.0.0.1:8080/actuator/health/readiness
Invoke-RestMethod http://127.0.0.1:8080/api/v1/properties
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8001/chat/health
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

Backend cần `UP`; AI v6 cần model ready. RAG cần dependencies, Ollama và corpus sẵn sàng. `configured_not_loaded` có thể là E5 chưa nạp lười; health thành công chưa chứng minh chat đã trả lời được.

Kiểm tra tay:

1. Đăng nhập → Account → F5; kiểm tra đúng tài khoản và quyền.
2. Tìm kiếm Home → URL `/listings` giữ bộ lọc → mở `/listing/:id` → bản đồ giữ cùng `propertyId`.
3. BROKER tạo nháp, upload, xác nhận vị trí, gửi duyệt; ADMIN kiểm duyệt. Public không thấy tin chưa duyệt.
4. Gửi chat “Tìm căn hộ dưới 10 tỷ ở Đà Nẵng, ưu tiên trường học”, rồi “Đổi sang ưu tiên siêu thị”. Kết quả phụ thuộc dữ liệu công khai thực tế.
5. Mở định giá và gửi một bộ thông tin hợp lệ. Kiểm tra ảnh thật, GIS và bố cục điện thoại.

`EVIDENCE_ONLY` là kết quả chỉ dựa bằng chứng; không mô tả như Qwen đã sinh thành công. Không thêm dữ liệu giả để lấp kết quả tìm kiếm rỗng.

## 12. Build và triển khai Linux/HTTPS

Phần này là hướng dẫn cấu hình; cần nghiệm thu trên máy chủ mục tiêu. Các script `.ps1` phía trên dành cho Windows, không chạy trực tiếp bằng Bash.

### 12.1. Build artifacts

Trên máy có đúng JDK/Node:

```bash
cd backend
chmod +x mvnw
./mvnw -B -Dmaven.test.skip=true package
cd ../frontend
npm ci
npm run build
```

FE phải build với `VITE_API_BASE_URL=/api/v1` và `VITE_ENABLE_REFRESH=true` nếu dùng persistent login/Google. Biến `VITE_*` được đóng vào bundle lúc build; đổi environment của web server sau đó không sửa bundle đã có.

Ví dụ bố trí máy chủ:

```text
/srv/smartprop/app/            # Checkout đầy đủ, nằm ngoài web root
/srv/smartprop/www/            # Chỉ nội dung frontend/dist/
/srv/smartprop/backend/        # JAR phục vụ systemd
```

Đưa nội dung `frontend/dist/` vào `/srv/smartprop/www`, JAR vào `/srv/smartprop/backend`. Giữ checkout tại `/srv/smartprop/app` để chạy AI và relay. Không đưa `.env`, backup hoặc source vào thư mục phục vụ web; đổi document root của mẫu `ops/Caddyfile` theo vị trí static thực tế.

### 12.2. Backend, database và storage

- DBA chuẩn bị schema đúng lineage và backup/restore đã được kiểm tra; app tiếp tục dùng Hibernate validate, không auto-migrate.
- Dùng `ops/smartprop.service` và `ops/production.env.example` làm mẫu. Runtime env nằm ngoài web root, chỉ tài khoản service được đọc.
- Đặt `CORS_ORIGINS` theo domain HTTPS thật; `REFRESH_ENABLED=true`, `REFRESH_SECURE_COOKIE=true`, `STORAGE_ROOT=/var/lib/smartprop/uploads` và JWT secret riêng cho máy chủ.
- Muốn chạy chatbot, đặt `APP_RECOMMENDATION_V11_ENABLED=true`; muốn form đăng tin dùng model, đặt `APP_VALUATION_ENABLED=true`. Bật `BROKER_APPLICATIONS_ENABLED=true` và `PROFILE_AVATAR_ENABLED=true` khi đã xác nhận schema tương ứng; Google Login cần bộ client/origin/callback HTTPS riêng như mục 4.3. Các module messaging/projects/legal/email mặc định tắt: chỉ bật cờ tương ứng sau khi kiểm tra schema/cấu hình và được người vận hành cho phép.
- MySQL và các service nội bộ chỉ mở trên mạng riêng/loopback. Cấp quyền ghi uploads cho user service, kiểm tra `ReadWritePaths` khi thêm thư mục cache.
- Tạo service riêng cho RAG, định giá, Ollama và chat relay. Windows embedded runtime không dùng được trên Linux; tạo venv Linux, cài dependency phù hợp từ requirements và kiểm tra model/manifest trước khi phục vụ.
- Trên Linux, build corpus/index bằng `ai-services/scripts/build_rag_corpus.py`, `build_rag_index.py`; cấu hình các biến RAG tương đương launcher Windows rồi chạy `uvicorn rag_main:app` tại `ai-services` bằng venv RAG. Model E5 cần chuẩn bị trước; `RAG_RESEARCH_ENABLED=false`, `RAG_SQL_ENABLED=false`, peer Backend/Ollama vẫn theo mục 9.

### Lệnh chuẩn bị AI/RAG trên Linux

Ví dụ bên dưới chạy tại `/srv/smartprop/app`, cần có Python 3.11 cho RAG và Python 3.14 cho định giá. Tài khoản service phải đọc được model và ghi được thư mục corpus/index. Cài Ollama riêng, chạy Backend trước khi tạo corpus.

```bash
cd /srv/smartprop/app
python3.11 -m venv .scratch/rag-venv
.scratch/rag-venv/bin/python -m pip install --upgrade pip
.scratch/rag-venv/bin/python -m pip install 'torch==2.9.1+cpu' --index-url https://download.pytorch.org/whl/cpu
.scratch/rag-venv/bin/python -m pip install -r ai-services/requirements-rag-ollama.txt
export E5_DEST="$PWD/.scratch/rag-models/multilingual-e5-small"
.scratch/rag-venv/bin/python -c "import os; from huggingface_hub import snapshot_download; snapshot_download(repo_id='intfloat/multilingual-e5-small', revision='614241f622f53c4eeff9890bdc4f31cfecc418b3', local_dir=os.environ['E5_DEST'])"
ollama pull qwen3:4b-instruct
```

Sau khi Ollama hoạt động, chuẩn bị environment RAG trong service riêng; các biến dưới đây cũng dùng được khi chạy thủ công:

```bash
cd /srv/smartprop/app
export RAG_LLM_PROVIDER=ollama
export RAG_BACKEND_URL=http://127.0.0.1:8080
export RAG_BACKEND_TIMEOUT_SECONDS=30
export RAG_OLLAMA_URL=http://127.0.0.1:11434
export RAG_OLLAMA_MODEL=qwen3:4b-instruct
export RAG_OLLAMA_KEEP_ALIVE_SECONDS=300
export RAG_OLLAMA_DIGEST="$(curl -fsS http://127.0.0.1:11434/api/tags | .scratch/rag-venv/bin/python -c 'import json,sys; print(next(m["digest"] for m in json.load(sys.stdin)["models"] if m["name"]=="qwen3:4b-instruct"))')"
export RAG_E5_PATH="$PWD/.scratch/rag-models/multilingual-e5-small"
export RAG_CORPUS_PATH="$PWD/.scratch/rag-data/public-corpus.json"
export RAG_INDEX_DIR="$PWD/.scratch/rag-data/faiss"
export RAG_RESEARCH_ENABLED=false
export RAG_SQL_ENABLED=false
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export PYTHONPATH="$PWD/ai-services"
.scratch/rag-venv/bin/python ai-services/scripts/build_rag_corpus.py --output "$RAG_CORPUS_PATH"
.scratch/rag-venv/bin/python ai-services/scripts/build_rag_index.py --corpus "$RAG_CORPUS_PATH" --e5-path "$RAG_E5_PATH" --output "$RAG_INDEX_DIR"
.scratch/rag-venv/bin/python -m uvicorn rag_main:app --host 127.0.0.1 --port 8001 --no-proxy-headers
```

Tạo venv định giá riêng và chạy trong terminal/service khác:

```bash
cd /srv/smartprop/app
python3.14 -m venv .scratch/valuation-venv
.scratch/valuation-venv/bin/python -m pip install -r ai-services/requirements.txt
.scratch/valuation-venv/bin/python ai-services/run_api.py --port 8000
```

Không dùng lock wheel Windows cho Linux. Các dependency/model đã được xác minh local Windows; môi trường Linux cần nghiệm thu lại trước production. Khi đưa các lệnh vào systemd, dùng đường dẫn tuyệt đối, environment riêng và quyền service phù hợp; không coi `export` ở terminal là cấu hình bền vững của service.

### 12.3. Reverse proxy đầy đủ

**`ops/Caddyfile` hiện chỉ proxy `/api/*` về Backend. Không dùng nguyên mẫu đó để kết luận chat/định giá đã được nối.** Máy chủ cần các tuyến riêng:

| Tuyến công khai | Upstream |
|---|---|
| `/api/v1/*` | Backend `127.0.0.1:8080` |
| `/api/ai/*` | AI `127.0.0.1:8000`, bỏ prefix `/api/ai` |
| `/api/chat` | Chat relay `127.0.0.1:8082`, chỉ nhận POST theo contract |
| Các route React còn lại | Static files; fallback `index.html` |

Chạy relay bằng Node trong service riêng, với environment:

```dotenv
CHAT_UPSTREAM_URL=http://127.0.0.1:8001/chat
CHAT_RELAY_HOST=127.0.0.1
CHAT_RELAY_PORT=8082
```

Lệnh tại `/srv/smartprop/app/frontend/`: `node server/chat-relay.mjs`. Giữ `server/`, `package.json` và các module `src/` mà relay import trong checkout riêng; chỉ có `dist` thì chưa đủ để chạy relay. Relay kiểm tra response công khai và chuyển request có Bearer hợp lệ tới `/chat/personalized`; không đưa RAG trực tiếp ra Internet.

Ví dụ nội dung site Caddy cần được người vận hành thay domain/đường dẫn và validate trước khi áp dụng:

```caddyfile
example.com {
    encode zstd gzip
    route {
        @loopbackOnly {
            path /api/v1/recommendations/research /api/v1/recommendations/research/* /api/v1/amenities/research /api/v1/amenities/research/*
        }
        @loopbackVariant {
            path_regexp loopback_norm (?i)^/+api/+(?:v1/+)?(?:recommendations/+research|amenities/+research)(?:[;/]|$)
        }
        @ambiguousApiPath {
            expression {http.request.uri}.matches("(?i)^/+api(?:/|%2f|%5c|;)[^?]*(?:%2f|%5c|%2e%2e|\\.\\.|;|//)")
        }
        handle @loopbackOnly {
            header Content-Type "application/json; charset=utf-8"
            header Cache-Control "no-store"
            respond `{"code":"FORBIDDEN","message":"Route nội bộ chỉ cho phép truy cập trực tiếp trên loopback."}` 403
        }
        handle @loopbackVariant {
            header Content-Type "application/json; charset=utf-8"
            header Cache-Control "no-store"
            respond `{"code":"FORBIDDEN","message":"Route nội bộ chỉ cho phép truy cập trực tiếp trên loopback."}` 403
        }
        handle @ambiguousApiPath {
            header Content-Type "application/json; charset=utf-8"
            header Cache-Control "no-store"
            respond `{"code":"FORBIDDEN","message":"Đường dẫn API không hợp lệ."}` 403
        }
        @chat path /api/chat
        handle @chat {
            reverse_proxy 127.0.0.1:8082
        }
        handle /api/chat/* {
            respond 404
        }
        handle_path /api/ai/* {
            reverse_proxy 127.0.0.1:8000
        }
        handle /api/* {
            reverse_proxy 127.0.0.1:8080 {
                header_up -X-SmartProp-Demo-Key
                header_up -Forwarded
            }
        }
        handle {
            root * /srv/smartprop/www
            try_files {path} /index.html
            file_server
        }
    }
}
```

Giữ các header bảo mật/thiết lập vận hành phù hợp từ `ops/Caddyfile`. Cấu hình DNS/TLS, chỉ đặt `SERVER_FORWARD_HEADERS_STRATEGY=native` và `SERVER_TOMCAT_REMOTEIP_INTERNAL_PROXIES=127\.\d{1,3}\.\d{1,3}\.\d{1,3}|0:0:0:0:0:0:0:1|::1` khi Backend chỉ lắng nghe trên `127.0.0.1:8080` phía sau Caddy; đăng ký lại Google callback `https://YOUR_DOMAIN/api/v1/auth/oauth2/callback/google`. Không dùng Vite dev server làm production server.

Xem thêm [vận hành và backup](ops/OPERATIONS.md). File này có một số ghi chép lịch sử; đối chiếu source/README hiện tại khi gặp đường dẫn hoặc hướng dẫn test cũ.

## 13. Backup, cập nhật và bàn giao

Backup local Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\backup-local.ps1
```

Cần MySQL client tools đúng đường dẫn; script nhận tham số `-MySqlDump` nếu vị trí cài khác. Backup gồm DB, storage có sẵn và manifest; kiểm tra hoàn chỉnh/checksum, giữ riêng và thử restore định kỳ. Ảnh Cloudinary cần chính sách sao lưu riêng nếu muốn phục hồi độc lập nhà cung cấp.

Khi cập nhật máy đang có dữ liệu:

1. Ghi lại commit hiện tại, sao lưu DB và uploads.
2. Pull commit được duyệt, đối chiếu thay đổi migration/configuration.
3. Nếu có migration mới: thử bản sao, duyệt rollout rồi mới áp dụng; không sửa migration cũ.
4. Cài dependency theo lockfile khi thay đổi; build, dừng đúng service cũ và thay artifacts.
5. Khởi động theo thứ tự, smoke test mục 11. Rollback code phải xét khả năng tương thích schema; khôi phục DB là thao tác riêng được duyệt.

Không cần bàn giao `node_modules`, venv, cache/build cũ. Cần bàn giao an toàn cấu hình mẫu + secrets qua kênh riêng, backup/ảnh, model đúng phiên bản, nguồn dữ liệu và quyền sử dụng liên quan. Không xóa `.scratch/rag-venv`, `rag-models`, `rag-data` trên máy đang chạy chatbot như thể chúng đều là file rác.

## 14. Lỗi thường gặp

| Hiện tượng | Cách kiểm tra/xử lý |
|---|---|
| Port 5173/8080/8000/8001 đã dùng | Kiểm tra `Get-NetTCPConnection -State Listen -LocalPort 5173` hoặc `netstat -ano`. Xác định đúng process/terminal, không kill hàng loạt; không mở thêm instance |
| DB connection refused / access denied | Kiểm tra MySQL/service/port, `DB_URL`, user, password và quyền theo host; build không sửa được kết nối DB |
| Thiếu bảng/cột hoặc checksum mismatch | Đối chiếu Flyway history/lineage và backup; không reset DB hoặc sửa migration để bỏ lỗi |
| Definer does not exist sau restore | DBA xử lý đúng tài khoản/quyền definer trên instance đích; giữ trigger cấp mã tin |
| Mất đăng nhập sau F5 | Đồng bộ cờ refresh FE/BE, cookie Secure theo HTTP/HTTPS, CORS và hostname; build/restart sau đổi biến VITE |
| Google redirect_uri_mismatch | So callback thực tế với OAuth Console, origin, hostname, port, HTTP/HTTPS và trạng thái test users |
| Chat 502/503 | Kiểm tra đủ Backend `-Chat`, RAG, Ollama/model, corpus/index và log từng service; health UP riêng lẻ chưa đủ |
| Model/venv RAG missing | Chuẩn bị đúng mục 7, không trông chờ Git mang theo `.scratch` của máy khác |
| Định giá 502/503 | Chạy runtime v6; kiểm tra cổng 8000, manifest, proxy `/api/ai`; Backend preview cần `-Valuation` |
| FEATURE_DISABLED | Kiểm tra cờ tính năng và schema tương ứng; không bỏ phân quyền hoặc validation để vượt lỗi |
| Không thấy tin trên Home | DB có thể trống, đang lọc hoặc tin chưa PUBLISHED/đã hết hạn/ẩn/xóa; không tự công khai bằng SQL |
| Ảnh thiếu hoặc lỗi | Kiểm tra metadata, uploads/Cloudinary và quyền; `CLOUDINARY_IMAGE_CHANGED` cần ADMIN đối chiếu/đồng bộ nguồn, không bỏ kiểm tra checksum |
| Trang riêng lỗi khi refresh production | Cấu hình SPA fallback `index.html`; kiểm tra API không bị chuyển thành HTML |
| Giao diện cũ sau pull | Cài lại dependency khi cần, build lại FE, cập nhật đúng `dist`; dev có thể khởi động bằng `npm --prefix frontend run dev -- --force` |

Các thông tin nhạy cảm chỉ giữ trong cấu hình riêng hoặc secret manager. Không gửi `.env`, token, password, Client Secret hoặc backup dữ liệu cá nhân lên repository.
