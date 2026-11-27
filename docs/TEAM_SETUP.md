# SmartProp — Hướng dẫn chạy cho thành viên nhóm

Tài liệu này bổ sung cho [README gốc](../README.md), tập trung vào **thiết lập từ đầu** và các dịch vụ AI (RAG, XGBoost, Auto-Scan, YOLOv8) mà README gốc chưa đề cập.

Dự án phục vụ **đồ án tốt nghiệp**, chạy local, không triển khai production công khai.

---

## 1. Yêu cầu hệ thống

| Thành phần | Phiên bản | Ghi chú |
|---|---|---|
| JDK | 21 | Bắt buộc — `pom.xml` khai báo `<java.version>21</java.version>` |
| Node.js | ^20.19 hoặc >=22.12 | Khai báo trong `frontend/package.json` |
| MySQL | 8.0+ | Schema do người quản trị chuẩn bị, app không tự migrate |
| Python | 3.14 | Cho AI services |
| Ollama | Mới nhất | Chạy `qwen3:4b-instruct` cho RAG Chat |
| RAM | 16 GB | RAG + XGBoost + YOLOv8 cùng chạy |
| GPU | Không bắt buộc | Toàn bộ AI chạy CPU |

---

## 2. Clone và cấu hình

```powershell
git clone https://github.com/manchae19/SmartProp.git
cd SmartProp
```

### Tạo `.env` ở thư mục gốc

Copy từ `.env.example` rồi điền giá trị thật. **Không commit `.env`.**

```powershell
Copy-Item .env.example .env
```

Các biến **bắt buộc**:

| Biến | Ý nghĩa |
|---|---|
| `DB_URL` | `jdbc:mysql://localhost:3306/smartprop?connectionTimeZone=UTC` |
| `DB_USER` | Tài khoản MySQL có quyền DML |
| `DB_PASSWORD` | Mật khẩu tài khoản đó |
| `JWT_SECRET` | Chuỗi ngẫu nhiên **ít nhất 32 byte** — app từ chối khởi động nếu ngắn hơn |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` |

Biến **nên đặt rõ** (có default nhưng dễ nhầm):

| Biến | Default | Ý nghĩa |
|---|---|---|
| `STORAGE_ROOT` | `./var/uploads` (tính từ `backend/`) | Nơi lưu ảnh và tài liệu. **Đổi sang đường dẫn tuyệt đối** nếu chạy backend từ thư mục khác, nếu không ảnh sẽ nằm rải rác. |
| `PORT` | `8080` | Cổng backend. Đổi nếu 8080 đã bận. |

Các biến **tùy chọn** (mặc định tắt):

| Biến | Mặc định | Bật khi nào |
|---|---|---|
| `BROKER_APPLICATIONS_ENABLED` | `false` | Đã áp V13 và muốn test luồng xin quyền đăng tin |
| `REFRESH_ENABLED` | `false` | Đã áp V10, muốn giữ đăng nhập sau F5 |
| `PROFILE_AVATAR_ENABLED` | `false` | Đã áp V15 |
| `GOOGLE_LOGIN_ENABLED` | `false` | Có Google OAuth client |
| `GEOCODING_ENABLED` | `false` | Có Geoapify/Google API key |
| `APP_IMAGE_ANALYSIS_ENABLED` | `false` | Đã áp V22 và muốn bật YOLOv8 |

### Frontend `.env.local`

```powershell
Copy-Item frontend\.env.example frontend\.env.local
```

Giữ mặc định `VITE_API_BASE_URL=/api/v1` và `BE_API_TARGET=http://127.0.0.1:8080`.

---

## 3. Chuẩn bị database

**App không tự chạy migration.** Schema phải được chuẩn bị trước.

> ⚠️ **Chỉ làm phần này khi bạn thực sự cần một database mới.**
> Nếu nhóm đã có database chạy sẵn (3306), **bỏ qua mục 3** — chỉ cần trỏ `DB_URL` vào đó và chạy app.
> Không bao giờ chạy `flyway:migrate` lên 3306 khi chưa backup và chưa được nhóm duyệt.

### Trường hợp A — Database mới hoàn toàn (lineage chuẩn)

Dùng khi tạo database trống cho máy cá nhân hoặc database cô lập để test.

```powershell
cd backend
.\mvnw.cmd -Pstandard-migrations flyway:migrate
```

Áp V1 → V22 theo thứ tự. **Chỉ chạy trên database trống**, không chạy trên database đã có dữ liệu.

### Trường hợp B — Database đã có từ trước (lineage legacy)

Database cũ dùng `legacy-hybrid-local` (BASELINE13 + V14 crawler + V17/18/19). **Không chạy `flyway:migrate` với profile chuẩn** — sẽ conflict checksum vì cùng version nhưng khác nội dung (ví dụ V13 là `valuation_history` ở lineage chuẩn, nhưng `broker_applications` ở lineage legacy).

Kiểm tra lineage hiện tại trước khi làm gì:

```powershell
cd backend
.\mvnw.cmd -Phybrid-local-existing-v13 flyway:info
```

Nếu history là `13(BASELINE), 14, 17, 18, 19, 20, 21` → đây là lineage legacy. Chỉ dùng profile `hybrid-local-existing-v13` cho database này, **không** dùng `standard-migrations`.

Gap giữa hai lineage (thiếu `listing_code`, thiếu cột Cloudinary, thiếu `user_advisor_preferences`) cần xử lý riêng — hỏi người quản trị database của nhóm trước khi thay đổi bất kỳ schema nào.

### Kiểm tra sau khi migrate

```powershell
cd backend
.\mvnw.cmd -Phybrid-local-existing-v13 flyway:validate
```

Kỳ vọng: `Successfully validated N migrations`.

### Bảng quan trọng theo version

| Version | Nội dung | Ảnh hưởng |
|---|---|---|
| V13 | `broker_applications` | Luồng xin quyền đăng tin |
| V16 | `listing_code` + trigger | Mã tin `SP001`, `SP002`… |
| V19 | `user_advisor_preferences` | Cá nhân hoá chatbot |
| V21 | `property_image_scan` | Auto-Scan |
| V22 | `property_image_analysis` | YOLOv8 |

### Phân biệt các môi trường

Dự án dùng nhiều database cho mục đích khác nhau. **Không nhầm lẫn giữa chúng.**

| Môi trường | Cổng | Mục đích | Ai được ghi |
|---|---:|---|---|
| **Local application** | 3306 | Database chính, dữ liệu thật của nhóm | Chỉ qua app khi đang phát triển |
| **Staging** | 3307 | Kiểm thử trước khi áp lên 3306 | Chỉ khi test có kiểm soát |
| **E2E isolated** | 3308 | Chạy test tự động có ghi dữ liệu | Test tự động, xoá được bất cứ lúc nào |

**Quy tắc an toàn:**

- **3306 là database thật.** Không chạy `flyway:migrate` lên 3306 khi chưa backup và chưa được nhóm duyệt.
- **3307 là staging.** Dùng để thử migration trước. Có thể reset nếu cần.
- **3308 là database cô lập cho E2E.** Dùng khi cần test có ghi dữ liệu (tạo listing, upload ảnh). Xoá và tạo lại được.

Nếu chỉ muốn chạy app để xem giao diện, dùng 3306 với dữ liệu sẵn có — **không cần migrate gì thêm**.

Nếu muốn test luồng đăng tin/upload ảnh, dùng 3308 để không làm bẩn dữ liệu thật.

> **Chi tiết đầy đủ về database:** xem
> [Bàn giao Database cho nhóm](handoff/DATABASE_TEAM_HANDOFF.md) — kiến trúc ba môi trường,
> hai lineage migration, baseline V21 đã kiểm chứng, hướng dẫn restore và xử lý VIEW DEFINER,
> quy tắc phối hợp migration giữa các PR, và checklist trước khi merge.

---

## 4. Chạy Backend

```powershell
cd backend
.\mvnw.cmd -B -Dmaven.test.skip=true package
.\scripts\run-local.ps1 -Transport NIO2 -Chat
```

`-Chat` bật `app.recommendation.v11-enabled=true` — **cần thiết** để RAG Chat không trả 502 `UNEXPECTED_RECOMMENDATION_MODE`.

Health: <http://127.0.0.1:8080/actuator/health> → `{"status":"UP"}`

---

## 5. Chạy Frontend

```powershell
cd frontend
npm ci
node .\node_modules\vite\bin\vite.js --host 127.0.0.1 --port 5173 --strictPort
```

Mở <http://127.0.0.1:5173>.

---

## 6. Chạy AI Services

Có **bốn** dịch vụ AI, mỗi cái một cổng và một venv riêng.

### 6.1 XGBoost Valuation — cổng 8000

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 .\ai-services\run_api.py
```

Model V6 có sẵn trong Git (`ai-services/artifacts/v6/`, ~2 MB).

**V1.3 cần tải riêng** (~28 MB, không có trong Git):

```powershell
cd ai-services
.\scripts\fetch-v1_3-artifacts.ps1 -BaseUrl "https://<host>/v1_3"
```

Hoặc đặt biến môi trường rồi chạy không tham số:

```powershell
$env:V1_3_ARTIFACT_BASE_URL='https://<host>/v1_3'
.\scripts\fetch-v1_3-artifacts.ps1
```

Script đọc `ai-services/artifacts/v1_3.manifest.json`, tải 4 file (`model.json`, `feature_schema.json`, `calibration.json`, `artifact_manifest.json`) và **kiểm SHA-256 từng file**, từ chối nếu sai. Nếu không có V1.3, API vẫn chạy với V6 — `/predict/v1_3_preview` trả 503.

Chi tiết phân phối artifact: [`ai-services/V1_3_ARTIFACTS.md`](../ai-services/V1_3_ARTIFACTS.md).

Health: <http://127.0.0.1:8000/health>

### 6.2 RAG Chat — cổng 8001

Cần **ba** thứ không có trong Git:

| Thành phần | Kích thước | Cách lấy |
|---|---|---|
| E5 embedding model | ~470 MB | `sentence-transformers/multilingual-e5-small` |
| FAISS index + corpus | ~500 KB | Build bằng script (xem dưới) |
| Qwen3-4B | ~2,5 GB | `ollama pull qwen3:4b-instruct` |

Tạo venv riêng:

```powershell
python -m venv .scratch\rag-ollama-venv
.scratch\rag-ollama-venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.scratch\rag-ollama-venv\Scripts\python.exe -m pip install -r ai-services\requirements-rag-ollama.txt
```

Build corpus và index (cần Backend 8080 đang chạy):

```powershell
cd ai-services
..\.scratch\rag-ollama-venv\Scripts\python.exe -X utf8 scripts\build_rag_corpus.py --output ..\.scratch\rag-data\public-corpus.json
..\.scratch\rag-ollama-venv\Scripts\python.exe -X utf8 scripts\build_rag_index.py --corpus ..\.scratch\rag-data\public-corpus.json --e5-path ..\.scratch\rag-models\multilingual-e5-small --output ..\.scratch\rag-data\faiss
```

Chạy service:

```powershell
$env:RAG_E5_PATH='F:\SmartProp\.scratch\rag-models\multilingual-e5-small'
$env:RAG_INDEX_DIR='F:\SmartProp\.scratch\rag-data\faiss'
$env:RAG_CORPUS_PATH='F:\SmartProp\.scratch\rag-data\public-corpus.json'
$env:RAG_LLM_PROVIDER='ollama'
$env:RAG_OLLAMA_KEEP_ALIVE_SECONDS='0'
..\.scratch\rag-ollama-venv\Scripts\python.exe -m uvicorn rag_main:app --host 127.0.0.1 --port 8001 --no-proxy-headers
```

Health: <http://127.0.0.1:8001/chat/health>

**Lưu ý:** corpus có TTL 24 giờ. Hết hạn sẽ trả 503 `PUBLIC_CORPUS_SNAPSHOT_EXPIRED` — rebuild corpus là xong.

### 6.3 Auto-Scan (imagecheck) — cổng 18001

Dùng chung venv RAG:

```powershell
cd ai-services
..\.scratch\rag-ollama-venv\Scripts\python.exe -m uvicorn imagecheck_main:app --host 127.0.0.1 --port 18001 --no-proxy-headers
```

Health: <http://127.0.0.1:18001/image-duplicates/health>

### 6.4 YOLOv8 (vision) — cổng 18002

**Venv riêng bắt buộc** — `ultralytics` kéo theo `torchvision`, `opencv-python`, `polars` và monkeypatch `PIL.Image.open`. Cài chung venv RAG sẽ đe doạ Auto-Scan.

```powershell
python -m venv .scratch\yolov8-venv
.scratch\yolov8-venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
.scratch\yolov8-venv\Scripts\python.exe -m pip install -r ai-services\requirements-vision.txt
```

**Tải model weights** (~6,5 MB, không có trong Git):

```powershell
$env:YOLO_CONFIG_DIR='F:\SmartProp\.scratch\yolov8-config'
New-Item -ItemType Directory -Force -Path 'F:\SmartProp\ai-services\var\vision' | Out-Null
.scratch\yolov8-venv\Scripts\python.exe -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
Move-Item yolov8n.pt ai-services\var\vision\
```

Chạy service:

```powershell
$env:VISION_MODEL_DIR='F:\SmartProp\ai-services\var\vision'
$env:YOLO_CONFIG_DIR='F:\SmartProp\.scratch\yolov8-config'
cd ai-services
..\.scratch\yolov8-venv\Scripts\python.exe -m uvicorn vision_main:app --host 127.0.0.1 --port 18002 --no-proxy-headers
```

Health: <http://127.0.0.1:18002/image-analysis/health>

**Bật tính năng:** cần cả V22 đã áp **và** biến môi trường:

```powershell
$env:APP_IMAGE_ANALYSIS_ENABLED='true'
$env:APP_IMAGE_ANALYSIS_BASE_URL='http://127.0.0.1:18002'
```

Mặc định `false` — backend chạy bình thường trên schema V21 khi tắt.

---

## 7. Chạy tất cả bằng một script

`ops/start-smartprop-local.ps1` quản lý vòng đời các service:

```powershell
.\ops\start-smartprop-local.ps1
```

Script kiểm tra theo thứ tự:

1. MySQL 3306 phải đang chạy.
2. RAG Chat 8001 phải sẵn sàng (script **không** tự start — cần chạy trước).
3. Imagecheck 18001: nếu healthy thì bỏ qua, nếu cổng bận mà health sai thì **báo lỗi, không kill**.
4. Vision 18002: **optional** — thiếu venv hoặc weights thì báo skip, không fatal.
5. Backend 8080.
6. Frontend 5173.

Dừng:

```powershell
.\ops\stop-smartprop-local.ps1
```

Chỉ dừng process do script ghi PID. **Không** dừng MySQL hoặc RAG Chat.

---

## 8. Kiểm tra health

| Service | URL | Kỳ vọng |
|---|---|---|
| Backend | `http://127.0.0.1:8080/actuator/health` | `{"status":"UP"}` |
| Frontend | `http://127.0.0.1:5173/` | 200 |
| XGBoost | `http://127.0.0.1:8000/health` | `model_version=v6` |
| RAG Chat | `http://127.0.0.1:8001/chat/health` | `ready` hoặc `configured_not_loaded` |
| Auto-Scan | `http://127.0.0.1:18001/image-duplicates/health` | `configured` |
| YOLOv8 | `http://127.0.0.1:18002/image-analysis/health` | `ready` |

`configured_not_loaded` ở RAG là **bình thường** — E5 nạp lười ở request đầu tiên.

---

## 9. Lỗi thường gặp

### Backend không khởi động: `Schema-validation: missing table [...]`

Database thiếu migration. Chạy `flyway:migrate` với đúng profile lineage.

### Backend không khởi động: `JWT_SECRET must contain at least 32 UTF-8 bytes`

`JWT_SECRET` trong `.env` quá ngắn. Tạo chuỗi ngẫu nhiên ≥32 byte.

### RAG Chat trả 502 `UNEXPECTED_RECOMMENDATION_MODE`

Backend chưa bật V1.1. Chạy lại với `-Chat`:

```powershell
.\scripts\run-local.ps1 -Transport NIO2 -Chat
```

### RAG Chat trả 503 `PUBLIC_CORPUS_SNAPSHOT_EXPIRED`

Corpus quá 24 giờ. Rebuild:

```powershell
cd ai-services
..\.scratch\rag-ollama-venv\Scripts\python.exe -X utf8 scripts\build_rag_corpus.py --output ..\.scratch\rag-data\public-corpus.json
..\.scratch\rag-ollama-venv\Scripts\python.exe -X utf8 scripts\build_rag_index.py --corpus ..\.scratch\rag-data\public-corpus.json --e5-path ..\.scratch\rag-models\multilingual-e5-small --output ..\.scratch\rag-data\faiss
```

Rồi restart RAG service.

### YOLOv8 health trả `unavailable` với `MODEL_MISSING`

Chưa có `yolov8n.pt`. Xem mục 6.4.

### YOLOv8 trả 503 `MODEL_LOAD_FAILED:ModuleNotFoundError`

Đang chạy bằng venv không có `ultralytics`. Phải dùng `.scratch/yolov8-venv`.

### Auto-Scan trả `PENDING_RETRY` với `VISION_HTTP_429`

Rate limit 20 ảnh/phút. Đợi hoặc retry thủ công. Backoff tự động: 30s → 2m → 8m, tối đa 3 lần.

### `flyway:info` báo `Unrecognised migration name format`

Đã sửa — `schema-reference.sql` được chuyển từ `database/migrations/` sang `database/docs/`. Nếu vẫn gặp, kiểm tra không có file `.sql` không phải migration trong thư mục migrations.

### Frontend build lỗi `spawn EPERM`

Chạy trong môi trường bị hạn chế quyền spawn process. Chạy `npm run build` trong terminal thường.

---

## 10. Kiểm thử

```powershell
# Backend
cd backend
.\mvnw.cmd test

# Frontend
cd frontend
node --test
node .\node_modules\vite\bin\vite.js build

# AI services
cd ai-services
..\.scratch\yolov8-venv\Scripts\python.exe -X utf8 -m unittest tests.test_vision_detector tests.test_vision_api tests.test_vision_document
..\.scratch\rag-ollama-venv\Scripts\python.exe -X utf8 -m unittest tests.test_image_duplicates
..\.scratch\rag-ollama-venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p 'test_rag*.py'
..\ai-services\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p 'test_v*.py'
```

**Lưu ý:** `test_v*.py` khi chạy bằng `ai-services/.venv` sẽ có 5 test vision fail vì venv đó không có `ultralytics`. Đó là **đúng thiết kế** — vision có venv riêng.

---

## 11. Những gì KHÔNG có trong Git

| Thành phần | Kích thước | Lý do |
|---|---|---|
| `yolov8n.pt` | 6,5 MB | `*.pt` gitignored |
| V1.3 model | 28 MB | Quá lớn, có script fetch |
| E5 embedding | ~470 MB | Model bên thứ ba |
| Qwen3-4B | ~2,5 GB | Ollama pull riêng |
| FAISS index + corpus | ~500 KB | Sinh tự động |
| `.env` | — | Chứa secret |
| `node_modules/`, `target/`, `dist/` | — | Build output |

---

## 12. Giấy phép

**Ultralytics YOLOv8 là AGPL-3.0.** Chi tiết nghĩa vụ và phạm vi sử dụng học thuật: [`ai-services/docs/YOLOV8_LICENSE_NOTICE.md`](../ai-services/docs/YOLOV8_LICENSE_NOTICE.md).

Tóm tắt: dùng cho đồ án, chạy local, không phân phối, không dịch vụ công khai → nghĩa vụ AGPL **chưa bị kích hoạt**. Nếu sau này triển khai công khai, phải mở mã nguồn phần liên quan hoặc mua Enterprise License.

---

## 13. Liên kết

- [README gốc](../README.md) — tổng quan dự án
- [Backend](../backend/README.md) — API, quyền, lưu trữ
- [Frontend](../frontend/README.md) — React, router, proxy
- [Database](../database/README.md) — migration, schema
- [Vận hành](../ops/OPERATIONS.md) — triển khai HTTPS, backup/restore
- [AI services](../ai-services/README.md) — API định giá v6
- [RAG](../ai-services/RAG.md) — kiến trúc RAG Chat
- [Bản đồ dự án](PROJECT_MAP.md) — cấu trúc file
