# SmartProp

Ứng dụng bất động sản sử dụng Java21/Spring Boot, MySQL8 và React/Vite.

## Cấu trúc

- `backend/`: REST API, tài khoản/phân quyền, tin đăng, kiểm duyệt và tệp.
- `frontend/`: ứng dụng người dùng và ADMIN, chung router; quản trị tại `/admin/dashboard`.
- `database/`: migration V1–V19, schema tham chiếu và seed tùy chọn.
- `ai-services/`, `frontend/integrations/valuation-v6/`: dịch vụ/model hiện có, cấu hình riêng.
- `ops/`: cấu hình triển khai HTTPS/service và hướng dẫn backup/restore.

## Chạy Backend

Cần JDK21, MySQL và schema đã được người quản trị chuẩn bị. Tạo `.env` ở root theo `.env.example`; không ghi đè cấu hình riêng đang dùng hoặc đưa secrets lên Git.

Tại `backend/`:

```powershell
.\mvnw.cmd -B -Dmaven.test.skip=true package
.\scripts\run-local.ps1 -Transport NIO2 -Chat
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
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run-local.ps1 -Transport NIO2 -Chat
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

## Chạy chatbot local sau đồng bộ schema

Database local đã lên V18 theo lineage chuẩn: V16 mã tin, V17 Cloudinary, V18 hai bảng external tương thích develop-binh. Không chạy lại migration mỗi lần mở ứng dụng; không dùng V16 crawler của nhánh khác thay V16 đã áp dụng.

Chat cần Backend mới, RAG riêng và Ollama có `qwen3:4b-instruct`. Mở ba terminal PowerShell nếu các cổng tương ứng chưa chạy:

```powershell
# Terminal 1 — Backend; -Chat bật public recommendation V1.1, không bật research.
cd D:\C2SE.01CMU\code\SmartProp
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run-local.ps1 -Transport NIO2 -Chat
```

```powershell
# Terminal 2 — RAG; dùng venv/model đã chuẩn bị trên máy này.
cd D:\C2SE.01CMU\code\SmartProp
powershell -NoProfile -ExecutionPolicy Bypass -File .\ai-services\scripts\run-chat-local.ps1
```

```powershell
# Terminal 3 — Frontend
cd D:\C2SE.01CMU\code\SmartProp\frontend
node .\node_modules\vite\bin\vite.js --host 127.0.0.1 --port 5173 --strictPort
```

Mở `http://127.0.0.1:5173/advisor/chat`. Kiểm tra Backend tại `http://127.0.0.1:8080/actuator/health`, RAG tại `http://127.0.0.1:8001/chat/health`. Không khởi động thêm process nếu cổng đang được sử dụng.

Launcher RAG lấy snapshot từ API amenities công khai và build FAISS local trước khi phục vụ. Corpus hết hạn sau 24 giờ; khởi động lại launcher để tạo snapshot mới. Không crawl, import hoặc ghi database trong bước này. Research và SQL trực tiếp được giữ tắt; dữ liệu tài sản lấy từ Recommendation API.

Runtime/model/index ở `.scratch/`, bị Git bỏ qua. Máy khác cần cài venv CPU và model riêng; pull source không tự mang theo runtime. Pin NumPy cho runtime Python 3.11 là `2.2.6`; pin `2.5.4` trước đó không có bản phát hành tương ứng trên registry đã kiểm tra. API không tự tải model khi nhận câu hỏi.

Health có thể là `configured_not_loaded` trước lần truy xuất đầu tiên vì E5 nạp lười. Nếu chat chỉ trả bằng chứng (`EVIDENCE_ONLY`), giao diện phải giữ giới hạn đó; không mô tả là Qwen đã sinh thành công. Không tự mở dữ liệu research để thay kết quả tìm kiếm rỗng.

## Chạy chatbot đầy đủ — hướng dẫn cho thành viên

Thứ tự chạy: **MySQL + Ollama → Backend → RAG → Frontend**. Thay đường dẫn bên dưới bằng thư mục clone trên máy bạn. Giữ các terminal hoạt động.

### Chuẩn bị trên mỗi máy

- Java 21, Node.js, MySQL và Ollama; cấu hình .env riêng và schema tương thích đã chuẩn bị.
- Backend có JAR mới; nếu sửa Java, build theo hướng dẫn phía trên. Frontend chạy npm ci một lần tại frontend.
- Cần .scratch/rag-venv/Scripts/python.exe cùng thư viện RAG và E5 tại .scratch/rag-models/multilingual-e5-small. Các runtime/model này không đi theo Git; xem ai-services/RAG.md.
- Chạy ollama list để kiểm tra model. Nếu thiếu, tải một lần bằng ollama pull qwen3:4b-instruct.

### Các terminal cần chạy

MySQL phải chạy trước Backend. Nếu service MYSQL80 chưa chạy, mở PowerShell Administrator và chạy Start-Service MYSQL80; tên service trên máy khác có thể khác.

Ollama Desktop phải hoạt động. Nếu chưa chạy, mở terminal riêng, chạy ollama serve và giữ terminal đó. Không chạy thêm nếu Ollama đã hoạt động.

Terminal 1 — Backend:

~~~powershell
cd D:\C2SE.01CMU\code\SmartProp
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run-local.ps1 -Transport NIO2 -Chat
~~~

**Bắt buộc có -Chat.** Thiếu cờ này, Backend có thể trả HEURISTIC_V1 thay vì HEURISTIC_V1_1; chatbot chặn kết quả và báo 502 dù health Backend vẫn UP. Nếu đã chạy thiếu cờ, Ctrl+C tại terminal Backend cũ rồi chạy lại.

Đợi Backend health UP rồi mở Terminal 2 — RAG:

~~~powershell
cd D:\C2SE.01CMU\code\SmartProp
powershell -NoProfile -ExecutionPolicy Bypass -File .\ai-services\scripts\run-chat-local.ps1
~~~

Terminal 3 — Frontend:

~~~powershell
cd D:\C2SE.01CMU\code\SmartProp\frontend
node .\node_modules\vite\bin\vite.js --host 127.0.0.1 --port 5173 --strictPort
~~~

### Kiểm tra sau khi chạy

~~~powershell
Invoke-RestMethod http://127.0.0.1:8080/actuator/health
Invoke-RestMethod http://127.0.0.1:8001/chat/health
Invoke-RestMethod http://127.0.0.1:11434/api/tags
~~~

Backend phải UP. RAG cần ollamaAvailable=true, các dependency=true và corpusPresent=true. configured_not_loaded là trạng thái chưa nạp E5 vào bộ nhớ; health thành công chưa chứng minh chat trả lời được.

Mở http://127.0.0.1:5173/advisor/chat, tạo Hội thoại mới và hỏi “Tìm căn hộ dưới 10 tỷ ở Đà Nẵng, ưu tiên trường học”, sau đó “Đổi sang ưu tiên siêu thị”. Kết quả phụ thuộc tin công khai hiện có. Lần đầu có thể chậm vì nạp mô hình; không gửi liên tục.

### Lỗi thường gặp

- Port 5173 is already in use: FE đã chạy, dùng URL hiện có. Muốn chạy lại thì Ctrl+C tại terminal FE cũ; không dừng mọi tiến trình Node.
- Với cổng 8080/8001/11434, kiểm tra dịch vụ đã chạy trước khi mở thêm.
- Chat 502: kiểm tra -Chat, RAG/Ollama và log RAG; không bỏ kiểm tra bằng chứng.
- Thiếu venv/E5/model: máy mới phải chuẩn bị runtime riêng, clone Git chưa đủ.
- Corpus hết hạn sau 24 giờ: Ctrl+C terminal RAG rồi chạy lại launcher khi Backend đã sẵn sàng để cập nhật snapshot/index.

Các lệnh khởi động không tự migration, crawl hoặc import database. Không chạy migration mỗi lần mở ứng dụng.

## Nhu cầu cá nhân cho chatbot

Tại /account → Thông tin cá nhân, khách có thể nhập thông tin gia đình/công việc, chọn nhiều nhu cầu, chọn một ưu tiên nhất và bật “Cho phép chatbot dùng thông tin này để tư vấn”. Tất cả trường mới tùy chọn, mặc định không cá nhân hóa. Dùng Lưu thay đổi/Hủy thay đổi hiện có; nút Xóa thông tin nhu cầu cần nhấn Lưu để áp dụng.

Schema dùng migration chuẩn V19__account_advisor_preferences.sql, bảng user_advisor_preferences liên kết users.id. V19 này thuộc lineage chuẩn của repository, khác V19 nghiên cứu trong research-migrations; không trộn hai lineage. Không tự chạy migration trên máy khác nếu chưa đối chiếu lịch sử và sao lưu.

Luồng: GET/PATCH /api/v1/users/me lưu/đọc advisorPreferences theo tài khoản xác thực; GET /api/v1/users/me/advisor-context chỉ xuất khu vực và nhu cầu được đồng ý. /api/chat giữ cùng URL cho frontend, relay chuyển yêu cầu có Bearer sang /chat/personalized. RAG kiểm tra JWT qua Backend và đọc lại consent ở mỗi lượt; không tin user ID hoặc hồ sơ do trình duyệt tự gửi. Cookie và khóa research không chuyển vào chat.

Tắt cá nhân hóa, xóa nhu cầu, đăng xuất hoặc đổi tài khoản ngừng dùng dữ liệu hồ sơ ở lượt tiếp theo. Khi consent/hồ sơ thay đổi, ngữ cảnh có nguồn gốc hồ sơ được làm mới; không tái dùng tham chiếu cũ. Sửa ưu tiên trong chat chỉ áp dụng phiên chat, không ghi hồ sơ.

Có thể chấm SCHOOL, MARKET/SUPERMARKET, HOSPITAL/PHARMACY, PARK và PUBLIC_TRANSPORT khi có bằng chứng nhóm tương ứng ở khu vực. Mỗi lượt tối đa bốn nhóm ưu tiên có dữ liệu; ưu tiên nhất đứng đầu. SCHOOL chưa xác minh từng cấp học; nhóm y tế chưa khẳng định riêng phòng khám; không suy ra khoảng cách từ nhà hoặc thời gian đi lại. Gym, sân thể thao, hồ bơi, quán cà phê, nhà hàng, trung tâm thương mại/cửa hàng tiện lợi, khu vui chơi và gần nơi làm việc được lưu nhưng chưa tự chấm điểm. Nhu cầu khác và khu vực làm việc được lưu trong tài khoản, chưa dùng tính khoảng cách hay suy luận tiêu chí.

Thử: lưu Trường tiểu học (ưu tiên nhất), Siêu thị và Công viên; mở /advisor/chat, nhập “Tìm căn hộ dưới 10 tỷ”. Sau đó nhắn “Lần này ưu tiên siêu thị hơn trường học”. Kiểm tra ngân sách/loại nhà giữ nguyên. Tắt cá nhân hóa tại Account, lưu rồi gửi lượt chat tiếp để kiểm tra hồ sơ không còn được dùng.

Các tệp triển khai chính:
- Frontend: frontend/src/features/account/AccountView.jsx, LifestyleFields.jsx, LifestyleFields.css; frontend/src/features/prediction/chatRuntime.js; frontend/build/chatProxy.mjs; frontend/server/chat-relay.mjs.
- Backend: backend/src/main/java/vn/smartprop/modules/user/UserDtos.java, UserService.java, AdvisorPreferencesService.java, AdvisorContextController.java; backend/src/main/java/vn/smartprop/security/SecurityConfig.java.
- RAG: ai-services/app/rag/account_preferences.py, personalization.py, orchestrator.py, session.py, tools.py, api.py.
- Database: database/migrations/V19__account_advisor_preferences.sql.
- Kiểm thử: backend/src/test/java/vn/smartprop/user/AdvisorPreferencesTest.java; ai-services/tests/test_rag_account_preferences.py. Các test xếp hạng hiện có cũng được chạy lại.

Nghiệm thu local 08/11/2026: build FE/BE PASS; 35 Java tests PASS; 76 RAG tests PASS, 3 test yêu cầu môi trường/model riêng bỏ qua. REST persistence/security trên MySQL cô lập và UI mock desktop 1440/mobile 390 PASS. V19 đã được duyệt, backup/rollout local thành công; dữ liệu và cấu trúc bảng cũ giữ nguyên, không tạo hồ sơ mẫu trên database chính. Chat công khai thật sau restart dùng Qwen/E5/FAISS thành công; phần cá nhân hóa được kiểm tra qua REST thử + unit/mock, cần người dùng lưu hồ sơ thật để nghiệm thu tài khoản của mình.
