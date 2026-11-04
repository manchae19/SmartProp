# BÁO CÁO BẢO MẬT & BÀN GIAO — SMARTPROP (post-migration)

Ngày: 2026-11-04
Branch đích: `develop-binh` @ `32f32a7`
Phạm vi: audit lịch sử Git, exposure credentials, cấu hình mẫu, portability, onboarding RAG.

> Tài liệu này **không chứa giá trị secret**. Mọi credential chỉ được tham chiếu bằng tên biến,
> commit hash, đường dẫn và fingerprint SHA-256 rút gọn.

---

## 1. KẾT LUẬN ĐIỀU HÀNH

| Câu hỏi | Trả lời |
|---|---|
| Repo đã sạch secret ở cây hiện tại? | **CÓ** — `develop-binh` không track `.env`, không track handover note |
| Secret có trong **lịch sử** Git? | **CÓ** — 1 commit, `bff5f1a` |
| Secret đó đã lên remote? | **CÓ** — nằm trên `origin/Backend-Huy` (đã push từ 2026-11-01) |
| Secret đó còn **đang dùng**? | **3/4 CÓ** (`MYSQL_ROOT_PASSWORD`, `JWT_SECRET`, `GEOAPIFY_API_KEY` trùng khớp với `.env` hiện tại) |
| Có chặn push `develop-binh`? | **CÓ** — xem mục 9 |

**Trạng thái: SECURITY_READY có điều kiện.**
Code, cấu hình mẫu, `.gitignore`, portability và tài liệu onboarding đã sẵn sàng.
Việc **rotate 4 credential là thao tác thủ công bắt buộc** trước khi push `develop-binh` lên GitHub.

---

## 2. AUDIT LỊCH SỬ GIT — ĐƯỜNG DẪN & COMMIT

Quét 1.208 blob text trên toàn bộ ref (`git rev-list --all --objects`), đối chiếu 10 mẫu tên biến
credential phổ biến, phân loại literal vs placeholder vs code-reference.

### 2.1 Blob chứa credential **thật** (literal, không phải placeholder)

| # | Đường dẫn | Commit chứa | Blob | Trạng thái hiện tại |
|---|---|---|---|---|
| 1 | `.env` | `bff5f1a` (thêm) → `f52362c` (xóa) | `c9560a6` | **Không** còn trong cây; **vẫn** trong lịch sử |
| 2 | `SMARTPROP_HANDOVER.md` | không thuộc commit nào (chỉ trong ref checkpoint của công cụ + file trên đĩa) | `dbedf4b` | Đã gitignore, không thể push |

### 2.2 Blob **an toàn** (đã kiểm chứng là placeholder hoặc code tham chiếu)

| Đường dẫn | Lý do an toàn |
|---|---|
| `.env.example` (mọi phiên bản, kể cả blob `d8f032d`) | 100% giá trị là `replace-with-…` hoặc rỗng; đã so khớp từng key với bản hiện tại — **giống hệt** |
| `ops/production.env.example` | `DB_PASSWORD=` và `JWT_SECRET=` để trống; comment ghi rõ "Never commit real values" |
| `ai-services/app/rag/config.py` | `db_password: str = field(default="", repr=False)` + `os.getenv(...)` — schema, không có giá trị |
| `backend/scripts/{flyway-local-forward,local_runtime,run-advisor-local,run-demo,run-tinix-advisor-local}.py` | Truyền `password` từ `private_environment()`, `secrets.token_urlsafe(48)` — sinh tại runtime |
| `backend/scripts/load-google-oauth.ps1` | `$env:GOOGLE_CLIENT_SECRET = [string]$web.client_secret` — đọc từ file OAuth, không literal |
| `backend/src/main/java/vn/smartprop/auth/SecretTokens.java` | Class tiện ích, không chứa secret |

### 2.3 Credential bị lộ trong `bff5f1a`

`.env` tại commit đó chứa 5 key có giá trị literal. Fingerprint SHA-256 (10 ký tự đầu):

| Key | Độ dài | Fingerprint | Có trong cây hiện tại? |
|---|---|---|---|
| `DB_PASSWORD` | — | — (không công bố) | Không (đã đổi) |
| `MYSQL_ROOT_PASSWORD` | — | — (không công bố) | **Có — trùng khớp** |
| `JWT_SECRET` | — | — (không công bố) | **Có — trùng khớp** |
| `GEOAPIFY_API_KEY` | — | — (không công bố) | **Có — trùng khớp** |
| `DEV_ADMIN_PASSWORD` | — | rỗng tại thời điểm commit | — |

Ngoài ra `SMARTPROP_HANDOVER.md` (blob `dbedf4b`) chứa `DB_PASSWORD` và `GEOAPIFY_API_KEY` dạng literal.
`GEOAPIFY_API_KEY` trong handover note **khác** với key trong `.env` (đã đối chiếu fingerprint nội bộ,
không công bố giá trị hay hash).

Blob `b51f0ce` (một bản `.env` chỉ tồn tại trong ref checkpoint `refs/codex/turn-diffs/…`, không
thuộc commit nào) có `DB_PASSWORD` trùng với giá trị trong handover note.

---

## 3. TÌNH TRẠNG EXPOSURE CHI TIẾT

### 3.1 `MYSQL_ROOT_PASSWORD` — **NGHIÊM TRỌNG**

- Lộ ở: `bff5f1a:.env` (blob `c9560a6`)
- Đã lên: `origin/Backend-Huy` (commit nằm trong lịch sử của ref này)
- **Đang dùng**: giá trị trong `.env` local **trùng khớp** với giá trị đã lộ
- Đây là tài khoản `root` của MySQL → toàn quyền trên server DB
- **Hành động**: rotate ngay, kể cả khi chỉ chạy local

### 3.2 `JWT_SECRET` — **NGHIÊM TRỌNG**

- Lộ ở: `bff5f1a:.env` (blob `c9560a6`)
- Đã lên: `origin/Backend-Huy`
- **Đang dùng**: trùng khớp
- Hệ quả: bất kỳ ai có secret có thể **tự ký JWT hợp lệ** và mạo danh bất kỳ role nào (kể cả ADMIN)
- **Hành động**: rotate ngay; rotate làm vô hiệu toàn bộ access token đang lưu hành (đúng thiết kế)

### 3.3 `GEOAPIFY_API_KEY` — **TRUNG BÌNH-CAO**

- Lộ ở: `bff5f1a:.env` (blob `c9560a6`)
- Đã lên: `origin/Backend-Huy`
- **Đang dùng**: trùng khớp
- Rủi ro: lạm dụng quota (tốn phí), không lộ dữ liệu người dùng
- **Hành động**: tạo key mới trên dashboard Geoapify, xóa key cũ, đặt quota/rate-limit

### 3.4 `DB_PASSWORD` (user ứng dụng) — **THẤP (đã rotate)**

- Lộ ở: `bff5f1a:.env`; đồng thời có trong handover note (giá trị khác)
- **Đang dùng**: giá trị hiện tại **khác** cả hai → đã được đổi sau khi lộ
- **Hành động khuyến nghị**: vẫn rotate định kỳ; xác nhận user DB này **không** có quyền DDL/GRANT

### 3.5 Tổng hợp mức ưu tiên

| Ưu tiên | Credential | Lý do |
|---|---|---|
| P0 | `JWT_SECRET` | Giả mạo phiên ADMIN |
| P0 | `MYSQL_ROOT_PASSWORD` | Toàn quyền DB |
| P1 | `GEOAPIFY_API_KEY` | Tốn phí / lạm dụng quota |
| P2 | `DB_PASSWORD` | Đã đổi, còn dư nợ lịch sử |

---
## 4. HƯỚNG DẪN ROTATE TỪNG CREDENTIAL

> Thực hiện **theo thứ tự**: DB → JWT → Geoapify → xác nhận.
> Không ghi giá trị mới vào bất kỳ file nào được Git track.

### 4.1 `MYSQL_ROOT_PASSWORD`

```powershell
# 1. Đăng nhập MySQL bằng mật khẩu hiện tại
mysql -u root -p

# 2. Đổi mật khẩu (dùng ALTER USER, không UPDATE mysql.user)
ALTER USER 'root'@'localhost' IDENTIFIED BY '<MAT_KHAU_MOI_48_KY_TU>';
FLUSH PRIVILEGES;
EXIT;
```

Sau đó cập nhật **chỉ file local** `F:\SmartProp\.env` (đã gitignore):

```
MYSQL_ROOT_PASSWORD=<MAT_KHAU_MOI>
```

Ghi chú Docker: `MYSQL_ROOT_PASSWORD` trong `docker-compose.yml` chỉ có hiệu lực khi khởi tạo volume lần đầu.
Với volume đã tồn tại, phải dùng `ALTER USER` như trên rồi cập nhật `.env`.

### 4.2 `JWT_SECRET`

```powershell
# Sinh secret mới 36 byte ngẫu nhiên, KHÔNG in ra terminal
$bytes = New-Object byte[] 36
[System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
$newSecret = [Convert]::ToBase64String($bytes).Replace('+','-').Replace('/','_').TrimEnd('=')
# Ghi trực tiếp vào .env (đã gitignore), không echo
(Get-Content .env) -replace '^JWT_SECRET=.*$', "JWT_SECRET=$newSecret" | Set-Content .env
Remove-Variable newSecret, bytes
```

Tương đương trên Linux/macOS:

```bash
NEW=$(openssl rand -base64 48 | tr '+/' '-_' | tr -d '=')
sed -i "s|^JWT_SECRET=.*|JWT_SECRET=$NEW|" .env && unset NEW
```

**Hệ quả cần thông báo cho team:** mọi phiên đăng nhập hiện tại bị vô hiệu, người dùng phải đăng nhập lại.
Đây là hành vi mong muốn, không phải sự cố.

Áp dụng cho Spring Boot qua `.env` → `backend/scripts/load-env.ps1` → `APP_JWT_SECRET`,
hoặc biến môi trường `JWT_SECRET` / `APP_JWT_SECRET` khi chạy container.

### 4.3 `GEOAPIFY_API_KEY`

1. Đăng nhập https://myprojects.geoapify.com → tạo project/key mới.
2. Giới hạn key: chỉ bật **Geocoding API**, giới hạn theo IP/domain nếu có.
3. Đặt rate limit / cảnh báo quota.
4. Xóa key cũ.
5. Cập nhật `.env` local: `GEOAPIFY_API_KEY=<KEY_MOI>`.
6. Nếu key dùng cho frontend: đặt trong `frontend/vue.ui/.env.local`, restrict theo HTTP referrer.

### 4.4 `DB_PASSWORD` (user ứng dụng, khuyến nghị)

```sql
-- Không dùng root cho ứng dụng
ALTER USER 'smartprop'@'localhost' IDENTIFIED BY '<MAT_KHAU_MOI>';
SHOW GRANTS FOR 'smartprop'@'localhost';   -- xác nhận không có DDL/GRANT
```

Cập nhật `.env`: `DB_PASSWORD=<MAT_KHAU_MOI>`

### 4.5 Cập nhật cấu hình theo từng service

| Service | Biến môi trường | Nguồn |
|---|---|---|
| Spring Boot | `DB_PASSWORD`, `JWT_SECRET` (→ `SPRING_DATASOURCE_PASSWORD`, `APP_JWT_SECRET`) | `backend/scripts/load-env.ps1` đọc root `.env` |
| FastAPI RAG | `RAG_DB_USER`, `RAG_DB_PASSWORD` | env khi khởi động `uvicorn`; **không** đọc `.env` trực tiếp |
| Docker Compose | `MYSQL_ROOT_PASSWORD`, `DB_PASSWORD` | root `.env` |
| Vue | không có secret backend; chỉ `VITE_*` public | `frontend/vue.ui/.env.local` |

Khởi động RAG với secret mới (PowerShell, không echo giá trị):

```powershell
$env:RAG_DB_USER = 'smartprop'
$env:RAG_DB_PASSWORD = (Get-Content .env | Select-String '^DB_PASSWORD=').Line.Split('=',2)[1]
```

### 4.6 Sau khi rotate — kiểm chứng

```powershell
curl http://127.0.0.1:8080/actuator/health          # backend UP
curl http://127.0.0.1:8001/chat/health              # researchEnabled=false cho public
# Đăng nhập lại, xác nhận token cũ trả 401
```

**Không** cần sửa code, không cần migration, không cần đổi schema.

---

## 5. KIỂM TRA `.gitignore`, `.env.example`, CẤU HÌNH MẪU

### 5.1 `.gitignore` — kết quả kiểm chứng

| Đường dẫn | Kết quả | Rule |
|---|---|---|
| `.env` | BỊ IGNORE | `.gitignore:74` |
| `.env.local`, `.env.production` | BỊ IGNORE | `.gitignore:75` (`.env.*`) |
| `frontend/vue.ui/.env` | BỊ IGNORE | `.gitignore:74` |
| `.env.example` | TRACKABLE | `!.env.example` |
| `SMARTPROP_HANDOVER.md` | BỊ IGNORE | `.gitignore:108` |
| `.scratch/**` | BỊ IGNORE | `.gitignore:84` |
| `docs/*` (mặc định) | BỊ IGNORE | `.gitignore:40` |
| **`docs/handoff/**`** | **TRACKABLE (mới)** | `!/docs/handoff/**` |

Thay đổi đã áp dụng — thêm sau dòng 46 của `.gitignore`:

```gitignore
# Team handoff reports only: versionable, no secrets, no local evidence.
!/docs/handoff/
!/docs/handoff/**
```

Đã kiểm chứng bằng file probe:

- `docs/handoff/PROBE.md` → `git add --dry-run` **thành công**
- `docs/PROBE2.md` (ngoài handoff) → **không** xuất hiện trong `git status`

Toàn bộ `docs/` còn lại vẫn bị ignore như cũ.

### 5.2 `.env.example` (root) — ĐẠT

- 26 key, tất cả placeholder hoặc giá trị an toàn (`localhost`, `false`, tên profile).
- `DB_PASSWORD=replace-with-your-local-database-password`
- `MYSQL_ROOT_PASSWORD=replace-with-a-different-local-root-password`
- `JWT_SECRET=replace-with-random-secret-at-least-32-bytes`
- `GEOAPIFY_API_KEY=`, `GOOGLE_CLIENT_SECRET=`, `DEV_ADMIN_PASSWORD=` (rỗng)
- Có comment "never use VITE_ variables" cho server keys.

### 5.3 `frontend/vue.ui/.env.example` — ĐẠT

- `VITE_GOOGLE_MAPS_API_KEY=` rỗng + comment "Put the actual value in .env.local; do not commit it".
- Không có biến server-side nào bị đưa vào `VITE_`.

### 5.4 `ops/production.env.example` — ĐẠT

- `DB_PASSWORD=` và `JWT_SECRET=` để trống.
- Dòng đầu: `# Copy to private /etc/smartprop/runtime.env. Never commit real values.`

### 5.5 Khuyến nghị tăng cường (không bắt buộc để PASS)

1. Thêm `gitleaks` / `detect-secrets` vào CI **trước** bước build.
2. Thêm pre-commit hook chặn file khớp `*.env` (trừ `*.example`).
3. Cân nhắc `git-crypt` nếu team cần version hoá cấu hình nhạy cảm.

---

## 6. BÁO CÁO MIGRATION — CÁCH THEO DÕI

`docs/DEVELOP_BINH_MIGRATION_REPORT.md` **hiện đang bị ignore** bởi `/docs/*` (dòng 40).

### 6.1 Đề xuất (hạ tầng đã sẵn sàng)

Chuyển báo cáo bàn giao vào **`docs/handoff/`** — thư mục vừa được mở ngoại lệ:

```
docs/handoff/
├── DEVELOP_BINH_MIGRATION_REPORT.md
├── SECURITY_AND_HANDOFF_REPORT.md   (tài liệu này)
└── RAG_TEAM_ONBOARDING.md
```

So sánh phương án:

| Phương án | Đánh giá |
|---|---|
| Mở toàn bộ `/docs/` | ❌ Kéo theo evidence nội bộ, file nháp |
| Thêm `!/docs/<tên-file>` từng file | ⚠️ Phải sửa `.gitignore` mỗi lần thêm báo cáo |
| **`docs/handoff/**` (đề xuất)** | ✅ Một rule, ranh giới rõ, không mở `.scratch` |
| Để trong `.scratch/` | ❌ Không bao giờ tới được thành viên khác |

### 6.2 Cách commit (khi bạn quyết định)

```powershell
New-Item -ItemType Directory -Path docs/handoff -Force
Move-Item docs/DEVELOP_BINH_MIGRATION_REPORT.md docs/handoff/
git add docs/handoff/ .gitignore backend/scripts/build_amenity_catalog_json.py `
        backend/scripts/spatial_analysis_amenity_scoring.py `
        backend/scripts/test_amenity_evidence_api_live.py `
        backend/scripts/test_spatial_amenity_scoring.py
git status   # xác nhận KHÔNG có .env, không có .scratch
git commit -m "docs(handoff): publish migration and security handoff reports"
```

`git status` phải **không** liệt kê bất kỳ file `.env`, `*.log`, hay `.scratch/**`.

---
## 7. PORTABILITY — ĐƯỜNG DẪN HARDCODE

### 7.1 Kết quả quét

Quét toàn bộ file code được track (`*.py`, `*.mjs`, `*.js`, `*.ps1`, `*.cmd`, `*.java`, `*.json`,
`*.yml`, `*.properties`) tìm literal `F:\SmartProp` / `F:/SmartProp`.

**Trước khi sửa: 4 file code** (17 file `.md` khác chỉ là ví dụ minh hoạ lệnh trong tài liệu).

| File | Dòng | Trước |
|---|---|---|
| `backend/scripts/build_amenity_catalog_json.py` | 18 | `ROOT = Path("F:/SmartProp")` |
| `backend/scripts/spatial_analysis_amenity_scoring.py` | 24 | `ROOT = Path("F:/SmartProp")` |
| `backend/scripts/test_amenity_evidence_api_live.py` | 26 | `ROOT = Path("F:/SmartProp")` |
| `backend/scripts/test_spatial_amenity_scoring.py` | 18 | `ROOT = Path("F:/SmartProp")` |

### 7.2 Đã sửa

Chuẩn hoá theo pattern **đã có sẵn** trong repo (`flyway-local-forward.py`, `run-demo.py`,
`run-recommendation-local.py` đều dùng `Path(__file__).resolve().parents[2]`):

```python
ROOT = Path(os.environ.get("SMARTPROP_ROOT", Path(__file__).resolve().parents[2]))
```

- Cho phép override qua `SMARTPROP_ROOT` khi cần trỏ sang vị trí khác.
- Mặc định tự suy ra repo root từ vị trí file (`backend/scripts/` → lên 2 cấp).
- Đã thêm `import os` cho 3 file còn thiếu.
- **`py_compile` PASS cả 4 file** (exit 0).

### 7.3 Sau khi sửa

```
git grep -E "F:/SmartProp" HEAD -- '*.py' '*.mjs' '*.js' '*.ps1' '*.cmd' '*.java'
→ (không còn kết quả)
```

17 file `.md` còn lại chỉ là ví dụ lệnh (`Từ F:\SmartProp, chạy...`) — không ảnh hưởng thực thi.
Nếu muốn sạch tuyệt đối, thay bằng "từ thư mục gốc repo". Không bắt buộc.

### 7.4 Biến môi trường portable đã có sẵn

| Biến | Ý nghĩa | Mặc định |
|---|---|---|
| `SMARTPROP_ROOT` | Gốc repo cho script Python | suy ra từ `__file__` |
| `RAG_BACKEND_URL` | Backend URL | `http://127.0.0.1:8080` (validate cứng loopback) |
| `RAG_E5_PATH` | Thư mục weights E5 | — (bắt buộc khi chạy RAG thật) |
| `RAG_INDEX_DIR` | Thư mục FAISS artifact | — |
| `RAG_CORPUS_PATH` | File corpus JSON | `var/rag/public-corpus.json` |
| `RAG_QWEN_PATH` | Qwen weights (provider `transformers`) | — |
| `RAG_OLLAMA_URL` | Ollama endpoint | `http://127.0.0.1:11434` (validate cứng) |
| `RAG_RESEARCH_ENABLED` | Bật research | `false` |
| `RAG_DEMO_KEY` | Demo key cho research | rỗng |

---

## 8. TÀI LIỆU ONBOARDING

Đã tạo: **`docs/handoff/RAG_TEAM_ONBOARDING.md`**

Bao phủ đủ 8 mục: clone/pull, dependencies, Ollama + Qwen, E5/FAISS/corpus, chạy 3 service,
test không GPU, Public SAFE / Research isolation, troubleshooting.

---

## 9. DANH SÁCH THAO TÁC THỦ CÔNG TRƯỚC KHI PUSH

> **CẬP NHẬT 2026-11-04 — quyết định của chủ repo:**
> `develop-binh` là nhánh phát triển riêng. Chủ repo **chấp nhận rủi ro** và **giữ nguyên**
> `GEOAPIFY_API_KEY`, `JWT_SECRET` cùng cấu hình MySQL hiện tại trong giai đoạn phát triển local.
> Việc rotate **không** được thực hiện trong nhiệm vụ này.
>
> Hệ quả đã được ghi nhận: các giá trị này vẫn tồn tại trong lịch sử `bff5f1a` và có thể truy xuất
> từ `origin/Backend-Huy`. Bảng dưới đây giữ nguyên như **khuyến nghị** để tham chiếu khi chuyển
> sang môi trường staging/production hoặc khi mở repo cho người ngoài.

| # | Việc cần làm | Bắt buộc? | Ghi chú |
|---|---|---|---|
| 1 | Rotate `JWT_SECRET` (P0) | **BẮT BUỘC** | Toàn bộ phiên cũ bị vô hiệu |
| 2 | Rotate `MYSQL_ROOT_PASSWORD` (P0) | **BẮT BUỘC** | Dùng `ALTER USER`, không reset DB |
| 3 | Rotate `GEOAPIFY_API_KEY` (P1) | **BẮT BUỘC** | Xóa key cũ trên dashboard |
| 4 | Xác nhận `DB_PASSWORD` hiện tại khác giá trị trong `bff5f1a` và handover note | **BẮT BUỘC** | Hiện đã khác, chỉ cần xác nhận |
| 5 | Chạy lại smoke test sau rotate | **BẮT BUỘC** | Backend health + RAG health + 1 câu hỏi |
| 6 | Quyết định xử lý `origin/Backend-Huy` | **BẮT BUỘC** | Secret vẫn ở đó; xem 9.1 |
| 7 | Commit `docs/handoff/` + `.gitignore` + 4 script portable | Khuyến nghị | Chưa commit — bạn quyết định |
| 8 | Push `develop-binh` (ahead 45) | Chờ bạn | Không tự push |
| 9 | Bật secret scanning trong CI | Khuyến nghị | gitleaks / detect-secrets |
| 10 | Xóa/lưu an toàn `SMARTPROP_HANDOVER.md` trên đĩa | Khuyến nghị | Đã gitignore nhưng vẫn chứa secret thật |

### 9.1 Về việc secret nằm trên `origin/Backend-Huy`

Commit `bff5f1a` đã push lên `origin/Backend-Huy` từ 2026-11-01 (trước phiên này).
Ba lựa chọn, **tất cả đều yêu cầu rotate trước**:

| Lựa chọn | Mô tả | Rủi ro |
|---|---|---|
| A. Rotate, giữ lịch sử | Secret cũ vô giá trị sau rotate; lịch sử nguyên vẹn | Thấp (**khuyến nghị**) |
| B. Rotate + `git filter-repo` xóa `.env` khỏi mọi commit | Sạch hoàn toàn | **Cần force-push**, phá clone của team |
| C. Rotate + xóa hẳn branch `Backend-Huy` trên remote | Đơn giản nhất | Mất lịch sử nhánh; cần team đồng ý |

Phiên này **không** thực hiện B/C (ràng buộc: không rewrite history, không force, không xóa branch).

---

## 10. THAY ĐỔI TRONG PHIÊN NÀY

| File | Thay đổi | Trạng thái Git |
|---|---|---|
| `.gitignore` | Thêm ngoại lệ `!/docs/handoff/` + `!/docs/handoff/**` | Chưa commit |
| `backend/scripts/build_amenity_catalog_json.py` | `ROOT` portable + `import os` | Chưa commit |
| `backend/scripts/spatial_analysis_amenity_scoring.py` | `ROOT` portable + `import os` | Chưa commit |
| `backend/scripts/test_amenity_evidence_api_live.py` | `ROOT` portable | Chưa commit |
| `backend/scripts/test_spatial_amenity_scoring.py` | `ROOT` portable + `import os` | Chưa commit |
| `docs/handoff/SECURITY_AND_HANDOFF_REPORT.md` | Tài liệu này (mới) | Chưa commit |
| `docs/handoff/RAG_TEAM_ONBOARDING.md` | Hướng dẫn onboarding (mới) | Chưa commit |
| `docs/DEVELOP_BINH_MIGRATION_REPORT.md` | Không đổi (vẫn bị ignore) | — |

**Không** thay đổi: TiniX data, MySQL schema, Hybrid V1.1, snapshot cache, code chatbot,
Vue, backend Java.

---

## 11. KIỂM CHỨNG KHÔNG HỒI QUY

| Kiểm tra | Kết quả |
|---|---|
| `py_compile` 4 script đã sửa | PASS (exit 0) |
| `git grep F:/SmartProp` trong code | 0 kết quả |
| `.gitignore` chặn `.env` | PASS |
| `.gitignore` cho phép `docs/handoff/**` | PASS |
| Cây `develop-binh` chứa `.env` | KHÔNG |
| Backup còn nguyên | CÓ (`repo-all-refs.bundle`, 627,239,616 bytes) |

Không chạy lại test nặng: thay đổi chỉ là đường dẫn khởi tạo `ROOT` trong script tiện ích
(không thuộc đường chạy runtime của backend/chat/Vue), đã verify bằng `py_compile`.

---

## 12. KẾT LUẬN

**SECURITY_READY (có điều kiện).**

Đã hoàn tất:

- Audit toàn bộ 1.208 blob lịch sử, xác định **chính xác 1 commit** (`bff5f1a`) chứa secret thật.
- Phân loại rõ 3/4 credential còn trùng khớp với giá trị đang dùng.
- `.gitignore`, `.env.example`, `ops/production.env.example` đều ĐẠT.
- Cơ chế theo dõi báo cáo bàn giao qua `docs/handoff/` đã hoạt động.
- 4 file hardcode `F:\SmartProp` đã portable hoá, compile PASS.
- Tài liệu onboarding RAG hoàn chỉnh cho thành viên mới.

**Chưa thể push an toàn** cho tới khi bạn hoàn thành mục 9 (rotate 4 credential + smoke test).
