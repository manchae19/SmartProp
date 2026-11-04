# RAG TEAM ONBOARDING — SmartProp Chatbot

Hướng dẫn cho thành viên mới tiếp tục phát triển chatbot RAG trên SmartProp.
Branch: `develop-binh` @ `32f32a7`. Python 3.11+ (dự án đã kiểm thử trên 3.14), Node 20+, JDK 21, MySQL 8.

> Không có secret nào trong tài liệu này. Mọi credential lấy từ `.env` local (đã gitignore)
> hoặc biến môi trường. Xem `docs/handoff/SECURITY_AND_HANDOFF_REPORT.md` trước khi bắt đầu.

---

## 1. Clone / Pull

```powershell
git clone https://github.com/manchae19/SmartProp.git
cd SmartProp
git switch develop-binh
git pull --ff-only
```

Nếu đã có repo:

```powershell
git fetch origin
git switch develop-binh
git pull --ff-only
```

`develop-binh` là branch tích hợp. **Không** commit trực tiếp lên đây khi chưa trao đổi với owner.
Tạo nhánh feature riêng:

```powershell
git switch -c codex/<ten-tinh-nang>
```

### Cấu trúc thư mục

```
SmartProp/
├── backend/                 Spring Boot 3.5 (Java 21), API /api/v1
├── frontend/vue.ui/         Vue 3 + Vite, Messenger chat UI
├── ai-services/             FastAPI: RAG chat (8001) + valuation v6 (8000)
│   ├── app/rag/             orchestrator, retriever, validator, session, tools
│   ├── tests/               test_rag*.py
│   └── scripts/             build_rag_corpus.py, build_rag_index.py
├── database/migrations/     Flyway V1–V13+ (chỉ đọc, không sửa)
├── ops/                     Caddy, systemd, backup
└── docs/handoff/            tài liệu bàn giao (được track)
```

---

## 2. Cài Dependencies

### 2.1 Backend (Java)

```powershell
cd backend
.\mvnw.cmd -B -Dmaven.test.skip=true package
```

Yêu cầu: JDK 21 (`java -version`). Maven wrapper tự tải Maven, không cần cài riêng.

### 2.2 Frontend (Node)

```powershell
cd frontend/vue.ui
npm ci
```

Dùng `npm ci` (không phải `npm install`) để khớp `package-lock.json`.

### 2.3 RAG runtime (Python, CPU-only)

Tạo venv **riêng** cho RAG — không dùng chung với valuation (`ai-services/.venv`) để tránh xung đột torch.

```powershell
cd F:\SmartProp
python -m venv .scratch\rag-ollama-venv
.\.scratch\rag-ollama-venv\Scripts\python.exe -m pip install --upgrade pip

# PyTorch CPU (không cần CUDA)
.\.scratch\rag-ollama-venv\Scripts\python.exe -m pip install torch==2.9.1+cpu --index-url https://download.pytorch.org/whl/cpu

# Phần còn lại
.\.scratch\rag-ollama-venv\Scripts\python.exe -m pip install -r ai-services\requirements-rag-ollama.txt
```

Gói chính: `sentence-transformers`, `transformers`, `faiss-cpu`, `fastapi`, `uvicorn`,
`httpx`, `pymysql`, `psutil`.

> Trên Linux/macOS: `.scratch/rag-ollama-venv/bin/python`.
> `.scratch/` bị gitignore — venv không bao giờ vào Git.

---

## 3. Cài Ollama và Qwen

### 3.1 Ollama

Tải tại https://ollama.com/download. Sau khi cài:

```powershell
ollama --version
# Server tự chạy nền tại http://127.0.0.1:11434
```

### 3.2 Qwen model

SmartProp đã kiểm thử với **`qwen3:4b-instruct`**, digest
`0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`.

```powershell
ollama pull qwen3:4b-instruct
```

Kiểm tra digest khớp:

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags | Select-Object -ExpandProperty models |
  Where-Object { $_.name -eq 'qwen3:4b-instruct' } | Select-Object name, digest, size
```

Nếu digest khác, cập nhật biến `RAG_OLLAMA_DIGEST`. Validator so khớp digest; sai sẽ trả
503/`OLLAMA_MODEL_IDENTITY_MISMATCH`.

Dung lượng: ~2.5 GB. RAM khi chạy: ~3 GB (Q4 quantized, CPU hoặc GPU đều được).

> **Không** dùng `qwen3:4b` (không có hậu tố `-instruct`) — đó là model khác
> (digest `359d7dd4bcda…`), `Settings.__post_init__` sẽ từ chối.

---

## 4. Thiết lập E5, FAISS và Corpus

### 4.1 E5 embedding model

`intfloat/multilingual-e5-small`, revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`.

```powershell
# Tải một lần (cần mạng), sau đó chạy offline
.\.scratch\rag-ollama-venv\Scripts\python.exe -c "from huggingface_hub import snapshot_download; snapshot_download('intfloat/multilingual-e5-small', revision='614241f622f53c4eeff9890bdc4f31cfecc418b3', local_dir=r'F:\SmartProp\.scratch\rag-models\multilingual-e5-small')"
```

Kích thước ~470 MB. Đặt tại `.scratch/rag-models/multilingual-e5-small`.

Sau khi tải, **luôn** chạy với offline mode:

```powershell
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
```

### 4.2 Corpus PUBLIC

Corpus được build **từ API thật**, không viết tay. Cần backend đang chạy ở 8080:

```powershell
.\.scratch\rag-ollama-venv\Scripts\python.exe ai-services\scripts\build_rag_corpus.py `
    --output ai-services\var\rag\public-corpus.json
```

Kết quả in ra `documents`, `summary`, `contentHash`. Với dữ liệu Đà Nẵng hiện tại:
~82 area documents + POI evidence (~326 tổng, tùy catalog version). Mọi document có
`scope: "PUBLIC"`. **Research records không bao giờ** vào corpus này.

### 4.3 FAISS index

```powershell
.\.scratch\rag-ollama-venv\Scripts\python.exe ai-services\scripts\build_rag_index.py `
    --corpus ai-services\var\rag\public-corpus.json `
    --e5-path .scratch\rag-models\multilingual-e5-small `
    --output .scratch\tinix-integration\step19-5-3\faiss
```

Sinh ra 2 file:
- `<version>.faiss` — index `IndexFlatIP(384)`, vector chuẩn hoá L2
- `<version>.json` — manifest chứa `indexSha256`, `count`, `dimensions`, `encoderRevision`, danh sách `sourceId`

Loader **xác minh** sha256 + revision + count trước khi dùng. Nếu corpus thay đổi, phải rebuild index.

> Corpus và index **không** được commit (nằm trong `.scratch/` hoặc `ai-services/var/`).
> Mỗi thành viên tự build từ dữ liệu API hiện tại.

---
## 5. Chạy 3 Service

Thứ tự bắt buộc: **MySQL → Backend (8080) → RAG Chat (8001) → Vue (5173)**.

### 5.1 MySQL

```powershell
mysql -u root -p -e "SELECT 1"
# hoặc
Get-NetTCPConnection -LocalPort 3306 -State Listen
```

Schema do owner chuẩn bị. **Không** chạy migration, không reset DB.

### 5.2 Backend (Spring Boot, cổng 8080)

```powershell
cd backend
.\mvnw.cmd -B -DskipTests package
.\scripts\run-local.ps1 -Transport NIO2
```

`run-local.ps1` đọc root `.env` rồi khởi động JAR với `--spring.flyway.enabled=false`,
`ddl-auto=validate`, seed tắt.

Kiểm tra: `curl http://127.0.0.1:8080/actuator/health` → `{"status":"UP"}`

### 5.3 RAG Chat API (FastAPI, cổng 8001)

```powershell
$env:RAG_LLM_PROVIDER              = 'ollama'
$env:RAG_OLLAMA_URL                = 'http://127.0.0.1:11434'
$env:RAG_OLLAMA_MODEL              = 'qwen3:4b-instruct'
$env:RAG_OLLAMA_DIGEST             = '0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0'
$env:RAG_OLLAMA_KEEP_ALIVE_SECONDS  = '0'      # 0 = giải phóng RAM sau mỗi câu (máy 16GB)
$env:RAG_E5_PATH                   = "$PWD\.scratch\rag-models\multilingual-e5-small"
$env:RAG_INDEX_DIR                 = "$PWD\.scratch\tinix-integration\step19-5-3\faiss"
$env:RAG_CORPUS_PATH               = "$PWD\ai-services\var\rag\public-corpus.json"
$env:RAG_BACKEND_URL               = 'http://127.0.0.1:8080'
$env:RAG_BACKEND_TIMEOUT_SECONDS   = '30'
$env:RAG_SQL_ENABLED               = 'true'
$env:RAG_DB_USER                   = 'smartprop'
$env:RAG_DB_PASSWORD               = '<lay tu .env local, KHONG echo>'
$env:RAG_RESEARCH_ENABLED          = 'false'     # mặc định public
$env:HF_HUB_OFFLINE                = '1'
$env:TRANSFORMERS_OFFLINE          = '1'
$env:TOKENIZERS_PARALLELISM        = 'false'

cd ai-services
..\.scratch\rag-ollama-venv\Scripts\python.exe -X utf8 -m uvicorn rag_main:app `
    --host 127.0.0.1 --port 8001 --no-proxy-headers
```

Kiểm tra:

```powershell
curl http://127.0.0.1:8001/chat/health
# {"status":"configured_not_loaded","provider":"OLLAMA",
#  "researchEnabled":false,"corpusPresent":true,"ollamaAvailable":true, ...}
```

`configured_not_loaded` là bình thường — E5 nạp lười ở câu hỏi đầu tiên (~10-20s).

Thử một câu hỏi:

```powershell
$body = @{ question = 'Cẩm Lệ có trường học nào?' } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8001/chat -Method Post -Body $body -ContentType 'application/json'
```

Kỳ vọng: `mode=SAFE`, `citations[].sourceId` bắt đầu bằng `poi-map:` hoặc `poi-evidence:`,
`amenityIntent.categories=["SCHOOL"]`, `amenityIntent.district="Cẩm Lệ"`.

### 5.4 Vue (cổng 5173)

```powershell
cd frontend/vue.ui
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Mở http://127.0.0.1:5173 → trang Chat Advisor. Vite proxy `/api` → 8080 và `/api/chat` → 8001.

---

## 6. Chạy Tests khi không có GPU

Toàn bộ test RAG chạy **CPU-only**. Không cần CUDA, không cần VRAM.

### 6.1 Unit tests (nhanh, không cần service)

```powershell
cd ai-services
..\.scratch\rag-ollama-venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p "test_rag*.py" -v
```

Kỳ vọng: `Ran 64 tests ... OK (skipped=3)`. 3 test skip là optional (cần model thật đã nạp).

Coverage:
- `test_rag.py` — orchestrator, validator, citation
- `test_rag_amenity_category.py` — hard filter category/địa bàn
- `test_rag_relevance.py` — relevance scoring
- `test_rag_multiturn.py` — session context, TTL
- `test_rag_stability.py` — fallback, error codes
- `test_rag_ollama.py` — Ollama adapter

### 6.2 Vue unit tests

```powershell
cd frontend/vue.ui
node --test --test-concurrency=1 tests/*.test.mjs
```

Kỳ vọng: 53 pass, 0 fail.

### 6.3 Backend tests

```powershell
cd backend
.\mvnw.cmd -o -B test
```

Kỳ vọng: 126 tests, 0 fail, 23 skipped (skip là MySQL live integration).
Nếu `-o` (offline) fail vì chưa cache, bỏ `-o`.

### 6.4 E2E browser (cần đủ 3 service)

Playwright tests ở `frontend/vue.ui/e2e/`. Cần backend + RAG + Vue đang chạy:

```powershell
cd frontend/vue.ui
npx playwright test e2e/chat.multiturn.mjs
```

### 6.5 Giới hạn RAM 16 GB

Khi chạy test có model (E5 + Ollama), chỉ chạy **tuần tự**. Không chạy song song
nhiều suite có model. Gate khuyến nghị:

```powershell
python -c "import psutil; print(psutil.virtual_memory().available // 2**20, 'MiB free')"
```

- `< 4 GB` free và E5 chưa nạp → **không** chạy
- `< 3 GB` free và E5 đã nạp → dừng

`RAG_OLLAMA_KEEP_ALIVE_SECONDS=0` giải phóng runner Ollama sau mỗi câu, đổi lại câu tiếp theo chậm hơn.

---

## 7. Hiểu Public SAFE / Research Isolation

Đây là **ranh giới bảo mật cốt lõi** — không được vô tình phá vỡ khi thêm tính năng.

### 7.1 Hai scope

| Scope | Endpoint | Dữ liệu | Ai gọi được |
|---|---|---|---|
| `PUBLIC` | `POST /chat` | Chỉ tin `PLATFORM_PUBLISHED`, POI `VALID`, amenity PUBLIC | Bất kỳ ai (không auth) |
| `INTERNAL_RESEARCH` | `POST /chat/research` | TiniX dataset, `HYBRID_ELIGIBLE_RESEARCH`, protected holdout | Chỉ loopback + ADMIN JWT + `RAG_RESEARCH_ENABLED=true` + `RAG_DEMO_KEY` |

### 7.2 Các lớp phòng vệ (đừng bypass)

1. **Route level** (`api.py`):
   - Không có `mode`/`scope`/`research` field trong `ChatRequest` → Pydantic trả **422** nếu client gửi.
   - `/chat/research` kiểm tra `request.client.host in ("127.0.0.1", "::1")` → **403** nếu không.
   - Thiếu `Authorization` → **401**.

2. **Tool level** (`tools.py`):
   - `recommend(research=False)` gọi `/api/v1/recommendations`; `research=True` gọi `/api/v1/recommendations/research`.
   - Response phải có `mode == "SAFE"` (public) hoặc `"INTERNAL_DEMO"` (research), nếu không → `UNEXPECTED_RECOMMENDATION_MODE`.
   - Quét blob public tìm `TINIX_AI`, `tinix:`, `HYBRID_ELIGIBLE_RESEARCH`, `sampleListingCount`, `raw_payload` → `PUBLIC_RESEARCH_LEAK`.

3. **Index level** (`index_store.py`):
   - `identity()` raise `PERSISTENT_INDEX_MUST_BE_PUBLIC` nếu bất kỳ document nào `scope != "PUBLIC"`.
   - **Không bao giờ** build FAISS index từ research documents.

4. **Session level** (`session.py`):
   - `SessionStore._items` key là `(scope, session_id)` — namespace tách biệt.
   - Session id public **không** đọc được context research dù đoán đúng id.
   - Context chỉ lưu **criteria** và **references**; mọi fact hiển thị đều đọc lại từ API.
   - TTL 30 phút, tối đa 256 session, tối đa 12 turn/session.

5. **Validation level** (`validator.py`): mọi câu trả lời phải có citation khớp evidence thật;
   vượt quá evidence → `EVIDENCE_ONLY` hoặc 503 strict.

### 7.3 Checklist khi thêm tính năng

- [ ] Field mới trong `ChatRequest` **không** cho client điều khiển scope/mode/SQL.
- [ ] Mọi dữ liệu mới vào corpus phải có `scope: "PUBLIC"` và đến từ API public.
- [ ] Không log payload, JWT, mật khẩu, raw model output.
- [ ] Test mới phải có ít nhất 1 case assert public **không** lộ research.
- [ ] Không thêm endpoint trả research data mà thiếu auth + loopback check.

### 7.4 Kiểm chứng isolation

```powershell
# 1. Research route không token → phải 403
curl -X POST http://127.0.0.1:8001/chat/research -H "Content-Type: application/json" -d '{"question":"x"}'

# 2. Payload có field scope → phải 422
curl -X POST http://127.0.0.1:8001/chat -H "Content-Type: application/json" -d '{"question":"x","scope":"INTERNAL_RESEARCH"}'

# 3. Response public không được chứa marker research
#    ("INTERNAL_RESEARCH", "tinix:", "HYBRID_ELIGIBLE_RESEARCH")
```

---
## 8. Troubleshooting

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| `/chat/health` → `degraded` | Thiếu deps hoặc E5 path sai | Xem `dependencies` trong response; xác nhận `RAG_E5_PATH` là thư mục tồn tại |
| `E5_LOCAL_WEIGHTS_MISSING` | `RAG_E5_PATH` rỗng/sai | Set đúng path tới snapshot E5 |
| `OLLAMA_UNAVAILABLE_OR_MODEL_MISMATCH` | Ollama chưa chạy hoặc chưa pull model | `ollama serve` / `ollama pull qwen3:4b-instruct` |
| `OLLAMA_MODEL_IDENTITY_MISMATCH` | Digest không khớp | Cập nhật `RAG_OLLAMA_DIGEST` theo `/api/tags` |
| `PERSISTENT_INDEX_UNAVAILABLE` | `RAG_INDEX_DIR` sai hoặc index chưa build | Chạy `build_rag_index.py` |
| `CORPUS_HASH_MISMATCH` | Corpus thay đổi sau khi build index | Rebuild index từ corpus mới |
| 503 `GENERATED_RANKING_DRIFT` | Qwen sinh ranking khác API | Bình thường ở strict mode; dùng `requireGeneration=false` để nhận `EVIDENCE_ONLY` |
| 429 `CHAT_BUSY` | >4 request đồng thời | Chờ hoặc tăng semaphore (cẩn thận RAM) |
| Import `torch` fail | Chưa cài torch CPU | `pip install torch==2.9.1+cpu --index-url https://download.pytorch.org/whl/cpu` |
| `faiss` import fail | Chưa cài `faiss-cpu` | `pip install faiss-cpu==1.15.1` |

Log chẩn đoán: server ghi `RAG_DIAGNOSTIC` với `requestId`, `stage`, `reason` — **không** ghi
question, facts, raw output, JWT hay mật khẩu. Dùng `requestId` để trace.

---

## 9. Quy tắc làm việc

1. **Không** commit `.env`, `.scratch/`, model weights, corpus, index.
2. **Không** sửa `database/migrations/`, TiniX data, snapshot cache.
3. **Không** đổi `qwen3:4b-instruct` sang model khác mà không cập nhật digest + test.
4. **Không** thêm API trả research data cho public path.
5. **Không** force-push, `reset --hard`, hoặc rewrite history trên branch chia sẻ.
6. Chạy test trước khi mở PR; ghi rõ test nào skip và tại sao.
7. RAM 16 GB: chạy test tuần tự, dùng `RAG_OLLAMA_KEEP_ALIVE_SECONDS=0`.

---

## 10. Tài liệu liên quan

| File | Nội dung |
|---|---|
| `ai-services/RAG.md` | Chi tiết kiến trúc RAG, các Step 19.5.x |
| `docs/handoff/SECURITY_AND_HANDOFF_REPORT.md` | Audit bảo mật, rotate credentials |
| `docs/handoff/DEVELOP_BINH_MIGRATION_REPORT.md` | Báo cáo migration (sau khi chuyển vào handoff) |
| `README.md` | Tổng quan chạy Backend + Frontend |
| `backend/README.md` | Chi tiết backend, quyền, refresh session |
| `ops/OPERATIONS.md` | Triển khai production, backup |
