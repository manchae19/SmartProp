# SmartProp — WP-01 Blocker Resolution

**Ngày:** 2026-11-27
**Trạng thái:** `WP_01_IMPLEMENTATION_COMPLETE` · `FLOW_A_REAL_E2E_PASS` ·
`LOCATION_VALIDATION_PASS` · `STREET_NORMALIZATION_PASS` · `V1_3_ARTIFACT_INTEGRITY_PASS` ·
**`VALIDATION_PARTIAL`** · **`NOT_READY_TO_MERGE`**
**Base:** `bab3d7b` · **Integration HEAD:** `c5a4cd1`

Nhãn: `FRESH_PASS` · `REUSED_EVIDENCE` · `FAIL` · `BLOCKED` · `NOT_RUN`

---

## A. MySQL portable setup

| Mục | Giá trị |
|---|---|
| Nguồn | `https://cdn.mysql.com//Downloads/MySQL-8.4/mysql-8.4.13-winx64.zip` (official CDN) |
| Kích thước | 268,1 MB |
| SHA256 | `e9cd98b1d23f122987b1afca26ad942efec5891481103d48ae3cde237fa3ea54` |
| Version | **8.4.13** — khớp datadir (8.4.13) |
| Vị trí | `.scratch\mysql-8.4\mysql-8.4.13-winx64` (không overwrite 8.0.46) |
| MySQL 8.0.46 hiện có | **không sửa**, không gỡ, không đổi PATH, không service mới |
| Docker | **không cài** |

**Khởi động thành công trên 3307** (`FRESH_PASS`):

```
SELECT VERSION() = 8.4.13
@@port = 3307
@@datadir = F:\SmartProp\.scratch\mysql-isolated\work-3307\data\
```

Config riêng: `--datadir`, `--port=3307`, `--bind-address=127.0.0.1`, `--pid-file=3307.pid`,
`--log-error=3307.err`, `--skip-log-bin`, `--mysqlx=0`. Không dùng config MySQL nhóm.

---

## B. Datadir backup / integrity

| Bước | Kết quả |
|---|---|
| Datadir gốc | `.scratch\mysql-isolated\data` — **209 MB, KHÔNG sửa** |
| Working copy | `.scratch\mysql-isolated\work-3307\data` — **copy riêng** |
| Không dùng `--initialize` trên datadir tồn tại | ✅ |
| Không có mysqld dùng working copy trước khi start | ✅ |
| Port 3307 free trước khi start | ✅ |
| Disk free | 62,8 GB |

**Không chạy binary mới trên bản datadir duy nhất.** Datadir gốc giữ nguyên.

---

## C. Migration lineage — **VERIFIED, nhưng KHÔNG khớp guard**

Kiểm tra thực tế bằng Flyway history trên DB `smartprop`:

| rank | version | type | success |
|---|---|---|---|
| 1 | 13 | **BASELINE** (SmartProp_existing_V13_reviewed_2026-11-01) | 1 |
| 2 | 14 | SQL | 1 |
| 3 | 17 | SQL | 1 |
| 4 | 18 | SQL | 1 |
| 5 | 19 | SQL | 1 |
| 6 | 20 | SQL | 1 |
| 7–12 | 21..26 | SQL | 1 |
| **13** | **27** | SQL (news backend v1) | 1 |

62 bảng. Database thứ hai `smartprop_v26v27` chỉ có **11 entry** (V13..V25) — **thiếu V26**.

### C.1. Guard từ chối

`MigrationLineageConfiguration.checkHistory()` chỉ cho phép **đúng 12 mục**:

```
13(BASELINE), 14, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26
```

Datadir có **13 mục** (thêm **V27** = nhánh `feature/news-backend-v1` chưa merge) →
`IllegalStateException: Unexpected/failed Local migration history; stop without repair.`

### C.2. Vì sao không vượt qua được trong phạm vi được phép

| Phương án | Khả dụng | Lý do |
|---|---|---|
| Dùng datadir hiện tại | ❌ | Có V27 ngoài allowed list |
| Xoá dòng V27 khỏi history | ❌ | **Cấm sửa Flyway history thủ công** |
| Nới guard | ❌ | **Cấm nới lỏng migration guard** |
| Baseline lại | ❌ | **Cấm baseline tùy tiện** |
| Snapshot `smartprop_v26v27` | ❌ | Thiếu V26 (11/12 mục) |
| Workflow migrate "separately reviewed" | ❌ | **Không tồn tại trong repo** (đã tìm `*.ps1/*.sh/*.cmd/*.md`) |
| Datadir mới 8.0.46 | ❌ | Cần dựng lại 26 version với lineage phân nhánh |
| Datadir của thành viên (`mysql-history-*`) | ❌ | Không chiếm tài nguyên người khác |

→ **Flow B vẫn `BLOCKED`.** Không đạt `FLOW_B_REAL_E2E_PASS`.

**Không truy cập 3306.** Chỉ thao tác trên working copy 3307.

---

## D. Location validation fix — `FRESH_PASS`

**Trước:** `location_feature="Hà Nội"` → **200** kèm giá (ngoại suy trên địa bàn chưa học).

**Sửa** (`ai-services/app/api/valuation.py`):

```python
def _supported_locations(predictor) -> set:
    info = predictor.info() if hasattr(predictor, "info") else {}
    return {clean_category(v) for v in (info.get("supported_districts") or [])}

if locations and clean_category(payload.location_feature) not in locations:
    raise HTTPException(422, detail="unsupported_location: …")
```

Chuẩn hoá bằng **chính** `clean_category` (NFC + casefold) mà model dùng, so sánh **exact
sau chuẩn hoá** — không fuzzy, không alias, **không sửa spelling của người dùng**.

### D.1. Kết quả đo qua HTTP thật

| Input | Status | Kết quả |
|---|---|---|
| `Cẩm Lệ` | **200** | ✅ |
| `Hà Nội` | **422** | ✅ |
| `""` (rỗng) | **422** | ✅ |
| `Quận Không Có Thật` | **422** | ✅ |
| `cẩm lệ` | **200** | ✅ đúng thiết kế (chuẩn hoá, không phải lỗi) |

**`LOCATION_VALIDATION_PASS`.**

**Lưu ý:** địa giới hiện hành và địa giới trong training **không** được giả định giống nhau —
whitelist lấy trực tiếp từ artifact `feature_schema.json` của V1.3 (7 quận).

---

## E. District / ward / street consistency

| Hạng mục | Trạng thái |
|---|---|
| District hợp lệ | **VERIFIED_MATCH** — whitelist từ artifact |
| District không hỗ trợ | **VERIFIED_MISMATCH** → 422 |
| Ward | **UNKNOWN_MAPPING** — không có bảng phân cấp ward↔district có provenance trong repo |
| Street ↔ district | **UNKNOWN_MAPPING** — không tự tạo mapping |
| Street category của model | **KNOWN_MODEL_CATEGORY** — 690 entry từ artifact |
| Street ngoài vocab | **OUT_OF_VOCABULARY** → `__UNKNOWN__`, không crash |

**Không tự tạo mapping đường/quận.** Không dùng synthetic làm nguồn xác minh. Không tự
geocode.

### E.1. Policy cho street không xác minh được

Model vẫn nhận street như một **category đã biết** (nếu có trong vocab). Vì không có mapping
provenance để xác nhận street↔district, chính sách hiện tại là:

- **Không** từ chối tổ hợp (không đủ bằng chứng để gọi là mismatch)
- **Không** âm thầm coi là đã xác minh — `features_used` vẫn trả `street_name` thực tế để
  FE/Advisor hiển thị
- Đề xuất hiển thị cảnh báo khi (district, street) chưa từng xuất hiện trong training
  (**chưa triển khai** — cần nguồn support data ở runtime)

---

## F. Street normalization — `FRESH_PASS`

**Trước:** `Đường Nguyễn Phước Lan` rơi vào **OOV** (mất toàn bộ tín hiệu street).

**Sửa** (`features_v1_3.py`):

```python
STREET_PREFIXES = ("đường", "phố", "đại lộ", "quốc lộ", "tỉnh lộ", "hẻm", "kiệt")

def canonical_street(value, vocabulary):
    cleaned = clean_category(value)                    # NFC + casefold + trim
    if cleaned in ("__MISSING__", "__UNKNOWN__"): return cleaned
    known = set(vocabulary)
    if cleaned in known: return cleaned                # exact match THẮNG trước
    for prefix in STREET_PREFIXES:                     # chỉ cắt khi tạo match thật
        if cleaned.startswith(prefix + " "):
            rest = cleaned[len(prefix) + 1:].strip()
            if rest and rest in known: return rest
    return cleaned                                     # không match → giữ nguyên (→ UNKNOWN)
```

**Bất biến được test:**
- Exact canonical match **luôn thắng trước** ⇒ `Đường Láng` (bản thân là entry) **không bị cắt**
- Chỉ cắt khi phần còn lại **là** entry ⇒ **không tạo match giả**
- Không fuzzy, không sửa lỗi chính tả
- Không collision: `Trần Phú` ≠ `Trần Phú 2`
- Không sửa training vocabulary gốc

### F.1. Kết quả đo qua HTTP thật (`Cẩm Lệ`, `Nguyễn Phước Lan`)

| Input | Giá | Ghi chú |
|---|---|---|
| `Nguyễn Phước Lan` | **9,8871 tỷ** | ✅ |
| `Đường Nguyễn Phước Lan` | **9,8871 tỷ** | ✅ **trước fix: 6,79 tỷ (OOV)** |
| `  nguyễn phước lan  ` | **9,8871 tỷ** | ✅ |
| `Đường Không Tồn Tại XYZ 123` | 200, ≈ baseline | OOV an toàn, không crash |
| `""` | 200, baseline | missing an toàn |

**Ba biến thể cho cùng một giá** — normalization hoạt động đúng.

### F.2. Regression tests

`ai-services/tests/test_wp01_street_canonical.py` — **13/13 PASS**:
exact, lowercase, prefix ×3, street-thật-sự-có-tiền-tố, whitespace, unknown không bị rewrite,
prefix không tạo match giả, empty/null, no-collision, NFC/NFD equivalent, numeric street (`29/3`).

**Không tuyên bố normalization cải thiện MAPE** — chưa đánh giá trên tập đánh giá.

---

## G. Input parity — `FRESH_PASS`

`buildValuationPayload` **đã** forward `bathrooms`, `house_direction`, `balcony_direction`
từ trước (có length validator). Thiếu chỉ là **input UI** ở Flow A.

Đã thêm vào `ValuationPanel.jsx`:

| Field | Điều kiện hiển thị | testid |
|---|---|---|
| `bathrooms` | không phải Đất nền | `valuation-bathrooms` |
| `house_direction` | mọi loại | `valuation-house-direction` |
| `balcony_direction` | **chỉ Căn hộ** | `valuation-balcony-direction` |

Giá trị rỗng → **không gửi** (không có default bịa). Đổi property type → field không áp dụng
bị bỏ khỏi payload (điều kiện trong `buildValuationPayload`).

| Feature | V1.3 | Flow A trước | Flow A sau | Flow B |
|---|---|---|---|---|
| street / project / road / frontage | ✅ | ✅ | ✅ | ✅ |
| bathrooms | ✅ | ❌ | **✅** | ✅ |
| house_direction | ✅ | ❌ | **✅** | ✅ |
| balcony_direction | ✅ | ❌ | **✅** | ✅ |
| access_type | ❌ không phải feature | ✅ | ✅ giữ (compat) | ❌ |

**Flow A giờ có parity đầy đủ** với các feature V1.3 thực sự dùng.

---

## H. Production routing decision — **PARTIAL**

### H.1. Phát hiện

`vite.config.js` định nghĩa **cả hai**:

```js
server:  {host:'127.0.0.1', port:5173, strictPort:true, proxy},
preview: {host:'127.0.0.1', port:4173, strictPort:true, proxy},
```

→ **Production bundle preview cũng có proxy.** Đã kiểm chứng thật:

| Kiểm tra trên `vite preview` (build production) | Kết quả |
|---|---|
| SPA `/valuation` | **200**, có `div#app` |
| `GET /api/ai/model/options` | **200**, `content-type: application/json`, body **867 byte** JSON thật (`model_version: v1.3`) |
| `POST /api/ai/predict` | **200**, `model=v1.3`, `6.605 tỷ` |
| Build | `✓ built in 4,78 s` |

### H.2. Điều còn thiếu

| Hạng mục | Trạng thái |
|---|---|
| Bundle production phục vụ + proxy | **VERIFIED** |
| SPA routing | **VERIFIED** |
| **Reverse proxy cho web server thật (nginx/IIS)** | **NOT_RUN** — không có config trong repo |
| FastAPI network exposure trong deploy thật | **NOT_RUN** |

### H.3. Quyết định

**Không đổi routing** trong WP-01. Chuyển Flow A sang Spring Boot sẽ:
- thêm auth requirement cho panel standalone (thay đổi public access)
- thêm ghi valuation history (thay đổi persistence)
- thay đổi API contract

→ **ngoài phạm vi WP-01**. Trình **architecture decision riêng (WP-09)**.

Phương án thay thế đã được kiểm chứng: **reverse proxy tương thích** (`/api/ai/*` → FastAPI),
đúng như `preview.proxy` đang làm.

`PRODUCTION_ROUTING_VERIFIED` **chưa đạt** — mới verified ở mức preview server.

---

## I. Production build integration

| Kiểm tra | Kết quả |
|---|---|
| `vite build` | **PASS** — 4,78 s |
| Static serve + SPA fallback | **PASS** |
| `/api/ai/*` proxy qua `preview` | **PASS** — JSON thật, giá thật |
| Không lộ FastAPI trực tiếp ra ngoài trong test | Không quan sát thấy |
| Error response | `422 unsupported_location` trả đúng JSON có `detail` |

---

## J. Flow A real E2E — `FRESH_PASS` (`REUSED_EVIDENCE` từ `12860fa` + fix mới)

| Kiểm tra | Kết quả |
|---|---|
| Basic (Cẩm Lệ, 100 m²) | **6,61 tỷ** |
| + street hợp lệ `Nguyễn Phước Lan` | **9,8871 tỷ** |
| + `Đường …` (tiền tố) | **9,8871 tỷ** — *sau fix* |
| + road 12 / frontage 6 | **8,98 tỷ** |
| `area = 0` | client chặn, không gọi API |
| API down | không hiện giá, báo lỗi, không JS error |
| Mobile 390 px | PASS |

---

## K. Flow B real E2E — `BLOCKED`

Xem §C. Không có MySQL khớp guard.

---

## L. Cross-flow prediction parity — `NOT_RUN`

Không thể so giá cuối khi Flow B blocked.

- **Payload parity:** đã xác định tương đương về model feature (§G) — trừ 3 field Flow A
  vừa bổ sung, nay **đã có cả hai bên**
- **Encoded vector parity:** **`NOT_RUN`** — cần Flow B chạy thật
- `CROSS_FLOW_PARITY_PASS` **chưa đạt**

---

## M. Sensitivity — giữ nguyên + xác nhận

Evidence tại `12860fa` vẫn hợp lệ (`REUSED_EVIDENCE`). Bổ sung S4/S5 đã có trong ma trận:

| Case | Street | Road | Frontage | Giá | Δ |
|---|---|---|---|---|---|
| S0 | — | — | — | 6,605 | — |
| S1 | NVL | — | — | 21,021 | +218,25% |
| S2 | — | 12 | — | 5,986 | −9,37% |
| S3 | — | — | 6 | 6,427 | −2,70% |
| **S4** | NVL | 12 | — | 18,923 | +186,49% |
| **S5** | NVL | — | 6 | 18,632 | +182,08% |
| S6 | — | 12 | 6 | 5,985 | −9,39% |
| S7 | NVL | 12 | 6 | 17,077 | +158,54% |

**Tổ hợp hợp lệ:** Hải Châu + NVL (68 dòng train) → **+211,15%** (286 M/m², sát median
train 265 M) → model nhất quán dữ liệu, **không phải implementation bug**.

**Kết luận:** độ nhạy lớn với `street_name` là **model limitation**, không thêm trần/sàn
hay hệ số tùy ý. Không khẳng định gần median training là bằng chứng accuracy.

---

## N. Backend full regression — `REUSED_EVIDENCE`

`228/228 PASS`, `BUILD SUCCESS` tại `12860fa`. Không file backend nào đổi sau đó
(chỉ `ai-services/` + `frontend/`), nên kết quả vẫn áp dụng.

---

## O. FastAPI full regression — `FRESH_PASS`

| Chỉ số | Trước | Sau |
|---|---:|---:|
| Passed | 209 | **222** |
| Skipped | 20 | 20 |
| Subtests | 84 | 84 |
| Collection errors | 2 (RAG) | **2 (RAG)** |

**+13** test mới (`test_wp01_street_canonical.py`). Không hồi quy.

### O.1. Hai lỗi RAG — đối chiếu base

| Bước | Kết quả |
|---|---|
| File | `test_rag_area_filter.py`, `test_rag_public_projection.py` |
| Lỗi | `ImportError: cannot import name 'area_spec' from 'app.rag.personalization'` |
| Trên `bab3d7b` | **cùng lỗi, cùng 2 file** (đã chạy worktree tạm; đã xoá) |
| Trên `c5a4cd1` | **cùng lỗi** |

→ Pre-existing, cùng root cause, **không do WP-01**. Không sửa RAG.

**Không báo "full suite PASS"** — 2 file không collect được, 20 test skip.

---

## P. Frontend full regression — `FRESH_PASS`

67/67 unit · build 4,78 s · Flow A E2E PASS · API-down PASS · invalid input PASS · responsive PASS.

---

## Q. Model hash integrity — `FRESH_PASS`

| File | SHA256 | Trạng thái |
|---|---|---|
| `model.json` | `3c56b6937902d9f736f9eb0278683f0c5ab8af027f5ea12b1a4072abff840a03` | không đổi |
| `calibration.json` | `17632bdf…fbfe645` | không đổi |
| `feature_schema.json` | `84be275b…61e7ea` | không đổi |

Không train · không đổi weights · không bật Shadow · không cài dependency production.
Branch hardening gốc `a7db792` **không đổi**. V1.4–V1.6 research **không đổi**.
Vue **không xoá**. `.gitignore` + 2 file Vue **không đụng**.

---

## R. Final HEAD SHA

```
Base              bab3d7b
Integration HEAD  c5a4cd1  (feature/valuation-v1-3-hardening-integration)
Hardening gốc     a7db792  (không đổi)
```

**Không commit:** raw data · DB dump · credentials · model weights · `node_modules` · `dist`.
Test DB password chỉ dùng trong phiên, không ghi vào file nào trong repo.

---

## S. Remaining blockers

| # | Blocker | Loại |
|---|---|---|
| 1 | **Flow B E2E** — datadir có V27, guard chỉ cho V13..V26; không có workflow migrate đã review; không thể sửa history/baseline/nới guard | **chặn gate** |
| 2 | **Cross-flow parity** — phụ thuộc #1 | chặn gate |
| 3 | **Reverse proxy production thật** — chưa có config nginx/IIS | chặn `PRODUCTION_ROUTING_VERIFIED` |
| 4 | Ward / street↔district mapping chưa có provenance | trung bình |
| 5 | 2 test RAG pre-existing | ngoài scope |
| 6 | `playwright` trong `vue.ui/node_modules` | cleanup riêng |

---

## T. Final gate

```
WP_01_IMPLEMENTATION_COMPLETE
FLOW_A_REAL_E2E_PASS
LOCATION_VALIDATION_PASS
STREET_NORMALIZATION_PASS
INPUT_CONTRACT_VERIFIED
V1_3_ARTIFACT_INTEGRITY_PASS
VALIDATION_PARTIAL
NOT_READY_TO_MERGE
```

**Chưa đạt:** `FLOW_B_REAL_E2E_PASS` · `CROSS_FLOW_PARITY_PASS` ·
`PRODUCTION_ROUTING_VERIFIED` (mới verified ở preview server).

### Gỡ blocker — cần quyết định của bạn

| # | Phương án | Ghi chú |
|---|---|---|
| A | Cung cấp/cài **MySQL 8.4.13** (đã tải: `.scratch/mysql-8.4/`) + **workflow migrate target 26 đã review** trên snapshot V25 | Cần bạn phê duyệt dùng snapshot `smartprop_v26v27` + chạy V26 |
| B | Cho phép **datadir sạch V13 baseline + migrate V14..V26** (dựng schema từ lineage chuẩn) | Cần phê duyệt vì chạm vào "baseline" |
| C | Cho phép **bỏ V27 khỏi working copy** (xoá bảng news + dòng history trên **bản copy**, không phải gốc) | Cần phê duyệt vì là sửa Flyway history |
| D | Chấp nhận `VALIDATION_PARTIAL` và merge sau khi review thủ công phần Flow B | Không khuyến nghị |

**Tôi không tự chọn A/B/C** vì cả ba đều chạm vào vùng bạn đã đặt ranh giới.

---

## U. MySQL Portable — vận hành và bàn giao (WP-02..WP-08)

### U.1. Tài sản được giữ lại trên ổ F

| Tài sản | Đường dẫn | Trạng thái |
|---|---|---|
| **Binary MySQL 8.4.13** | `.scratch\mysql-8.4\mysql-8.4.13-winx64\` (1205 MB) | **GIỮ** |
| `mysqld.exe` / `mysql.exe` / `mysqladmin.exe` | trong `bin\` | **GIỮ** |
| **Datadir gốc** (chuẩn bị sẵn, chỉ đọc) | `.scratch\mysql-isolated\data\` (209 MB) | **GIỮ — KHÔNG SỬA** |
| **Work copy** datadir cho 3307 | `.scratch\mysql-isolated\work-3307\data\` (216 MB) | **GIỮ** |
| `mysql-8.4.13-winx64.zip` (268 MB) | — | **ĐÃ XOÁ** (đã giải nén + xác minh) |
| MySQL 8.0.46 | `F:\MySQL\Server8.0` | **GIỮ nguyên**, không sửa |

### U.2. Script vận hành tái sử dụng

| Script | Tác dụng |
|---|---|
| `.scratch\mysql-8.4\start-3307.ps1` | Khởi động MySQL 8.4 trên `127.0.0.1:3307` với **work copy** datadir. Detached (`cmd /c start /B`) nên **không giữ pipe** khi bị capture. In ra `VERSION()`, `@@port`, `@@datadir`. |
| `.scratch\mysql-8.4\stop-3307.ps1` | `mysqladmin shutdown` graceful, chờ port free, không đụng 3306. |

**Đã kiểm chứng round-trip (`FRESH_PASS`):**

```
start-3307.ps1  → exit 0, 13,6 s
                  8.4.13   3307   F:\SmartProp\.scratch\mysql-isolated\work-3307\data\
stop-3307.ps1   → exit 0, 6,0 s
                  "MySQL 8.4 on 3307 shut down cleanly. Port free."
```

### U.3. Trạng thái sau khi dọn

| Kiểm tra | Giá trị |
|---|---|
| Port 3307 | **FREE** |
| Port 3306 | **BUSY pid 6556** — service của nhóm, **không đụng** |
| Process `mysqld` từ `mysql-8.4` | **không còn** |
| Port app 8000/8080/5173/4173 | **free** |
| Datadir gốc | **nguyên vẹn** |
| Binary 8.4 | **nguyên vẹn** |

### U.4. Quy tắc dùng lại cho WP-02..WP-08

1. `start-3307.ps1` trước mỗi phiên cần DB.
2. Làm việc **chỉ** trên work copy; datadir gốc là nguồn chỉ đọc.
3. `stop-3307.ps1` sau khi xong — giải phóng 3307.
4. **Không** xoá datadir gốc, work copy hay binary khi chưa được phê duyệt.
5. **Không** đụng 3306 dưới bất kỳ hình thức nào.

### U.5. Blocker Flow B vẫn nguyên

MySQL **khởi động được**, nhưng **guard từ chối lineage** vì datadir có **V27** ngoài
danh sách 12 mục `V13..V26` (§C). Cần quyết định A/B/C trước khi chạy Flow B.
Việc dựng lại môi trường MySQL **không** gỡ được blocker này.

---

## V. Phương án B — dựng database test sạch (thực hiện theo phê duyệt)

### V.1. Baseline artifact — tìm được, có provenance

| Mục | Giá trị |
|---|---|
| File | `.scratch\flyway-local-forward\smartprop-before-local-completion-20261102T060122419637Z.sql` |
| SHA256 | `e698558e8ad91451117dc700b954cfb91231c235ca7fad375ed55e699176b3c4` |
| Kích thước / bảng | 3,04 MB · **45 CREATE TABLE** |
| Nguồn | MySQL dump 10.13 từ **8.0.46**, ghi 2026-11-02, DB `smartprop` |
| Flyway history trong dump | `V13 BASELINE` (desc `SmartProp_existing_V13_reviewed_2026-11-01`) + `V14` checksum **`-1382804267`** |
| Dữ liệu người dùng | Có (users/auth_sessions/user_roles) → **đã xoá** sau import |

**Checksum V14 khớp đúng giá trị guard yêu cầu** (`-1382804267`) ⇒ đây là baseline chính thức
của lineage legacy, không phải snapshot đặt tên tùy ý.

### V.2. Dựng môi trường (đã làm)

| Bước | Kết quả |
|---|---|
| Datadir mới | `.scratch\mysql-isolated\clean-v26\data` — `--initialize-insecure`, **không** dùng `--initialize` trên datadir cũ |
| MySQL Portable | 8.4.13, port **3307**, bind **127.0.0.1** (tái sử dụng binary đã tải) |
| Restore dump | **PASS** — history V13 BASELINE + V14 |
| Xoá user data fixture | `users = 0` ✅ (không còn dữ liệu người dùng) |
| Flyway CLI chính thức | profile **`hybrid-local-existing-v13`** (legacy + research, target 26) |
| **`flyway:migrate`** | **BUILD SUCCESS** — `Successfully applied 10 migrations, now at version v26` |

**History cuối — đúng 12 mục như guard yêu cầu:**

```
1  13  BASELINE      7  21  SQL
2  14  SQL           8  22  SQL
3  17  SQL           9  23  SQL
4  18  SQL          10  24  SQL
5  19  SQL          11  25  SQL
6  20  SQL          12  26  SQL
```

**V26 thực sự áp dụng:** bảng `property_coordinate_audit` **tồn tại** trong schema.

Không sửa Flyway history thủ công · không nới guard · không baseline tùy tiện ·
không sửa migration SQL · không đụng 3306.

---

## W. Blocker thật sự: lineage legacy thiếu V16

### W.1. Spring Boot khởi động thất bại

```
SchemaManagementException: Schema-validation: missing column [listing_code] in table [properties]
```

### W.2. Nguyên nhân — `VERIFIED`

| Sự kiện | Bằng chứng |
|---|---|
| Cột `listing_code` do `V16__immutable_property_listing_codes.sql` tạo | file chỉ tồn tại trong `database/legacy…`? **KHÔNG** — chỉ có ở `database/migrations/V16__immutable_property_listing_codes.sql` |
| Legacy channel có V16? | **KHÔNG** (`Get-ChildItem database\legacy-hybrid-local -Filter V16*` → rỗng) |
| Guard có cho V16? | **KHÔNG** — allowed list chỉ `13,14,17,18,19,20,21,22,23,24,25,26` |
| Legacy V21 có dùng `listing_code`? | **CÓ** — `V21__property_image_scan.sql:12` |
| Schema sau migrate V26 | properties 33 cột · **`listing_code` = 0** |

**Mâu thuẫn nội tại của repository:** lineage legacy vừa *không* được phép có V16, vừa
*cần* cột do V16 tạo (V21 dùng nó), trong khi Hibernate của main bắt buộc cột đó.

### W.3. Vì sao không tự vá

| Phương án | Bị chặn bởi |
|---|---|
| Thêm V16 vào legacy channel | **Không sửa migration SQL** |
| Thêm V15/V16 vào allowed list của guard | **Không nới lỏng migration guard** |
| Chạy standard V1..V23 rồi legacy V24..V26 | V14/V17/V18 trùng **version number** nhưng khác checksum ⇒ Flyway validate fail. Đã thử bước đầu ở `clean-v26` trước khi dùng dump: `V17__local_broker_applications` xung đột vì standard `V13__broker_applications` đã tạo bảng |
| Dùng `database/docs/schema-reference.sql` | File tự ghi *"reference only, NOT an additional Flyway migration"*, 0 dòng `flyway_schema_history` ⇒ **không phải baseline có provenance** |
| Datadir 8.4.13 có sẵn (V13..V27) | Có **V27** ngoài allowed list (đã báo ở §C) |

**Kết luận: repository thiếu đường migrate hợp lệ để tới schema V26 tương thích main.**
Đúng trường hợp §4 của yêu cầu → **dừng bước migration**, không tự tạo SQL.

---

## X. Trạng thái sau phiên

| Hạng mục | Trạng thái |
|---|---|
| MySQL Portable 8.4.13 | **GIỮ** — `.scratch\mysql-8.4\` (1205 MB) |
| Fixture `clean-v26` | **GIỮ** — `.scratch\mysql-isolated\clean-v26\data` (208 MB), schema V26 + history 12 mục hợp lệ |
| Datadir gốc (V27) | **GIỮ nguyên**, không sửa |
| Work copy V27 | **GIỮ nguyên** |
| Port 3307 | **FREE** (shutdown graceful) |
| Port 3306 | **BUSY pid 6556** — service nhóm, không đụng |
| App ports | 8000/8080/5173/4173 **free** |

### X.1. Danh sách có thể dọn **sau khi được duyệt**

| Thư mục | Kích thước | Ghi chú |
|---|---|---|
| `.scratch\mysql-isolated\clean-v26\` | 208 MB | Fixture V26 — **chưa tương thích main**, giữ để điều tra |
| `.scratch\mysql-isolated\work-3307\` | 216 MB | Work copy V27 |
| `.scratch\vf`, `wp01-be`, `wp01-full` | ~vài trăm MB | Build dir tạm |

**Không xoá gì trong phiên này.**

### X.2. Điều cần quyết định để gỡ blocker Flow B

| # | Phương án | Cần bạn duyệt |
|---|---|---|
| **V-a** | Thêm `V16` (và nếu cần `V15`) vào **legacy channel** + allowed list của guard, kèm review | **sửa migration + guard** — ngoài quyền WP-01 |
| **V-b** | Tạo **V27__listing_code_for_legacy** trong legacy channel | **thêm migration mới** — cần review riêng |
| **V-c** | Cung cấp **V13 BASELINE handoff đã bao gồm `listing_code`** | cần artifact từ team DB |
| **V-d** | Chấp nhận Flow B dùng **MySQL 8.4 datadir có V27** và cho phép loại V27 khỏi bản copy | trước đây bạn đã từ chối (phương án C cũ) |

Cả bốn đều vượt ranh giới "không sửa migration / không nới guard" mà bạn đặt ra, nên
**tôi dừng và chờ quyết định**.

---

## Y. V-c — PR38 Handoff Recovery: FLOW B UNBLOCKED

### Y.1. Handoff artifact (nguồn chính thức, có SHA256)

| Artifact | SHA256 | Nội dung |
|---|---|---|
| `C:\Users\manchae\Desktop\SmartProp_PR38_Database_Handoff.zip` | `0d55168e8b44347f3058187eb60ad1f3222ec1f4a5a74ab5bcac293a4b9e80a1` | `smartprop_v21_schema.sql` (103,3 KB), `README.md`, `VERIFY.md` |
| `C:\Users\manchae\Desktop\SmartProp_PR38_Listing_Code_Handoff.zip` | `d4dfd864c268bd0aaa927ee59a8afb3bbcf99a445fb0e004ae1255f33e16cef5` | `listing_code_triggers.sql` (2,4 KB), `README.md`, `VERIFY.md` |

Giải nén (chỉ đọc) tại `.scratch\handoff-artifacts\`. **Không truy cập 3306.**

### Y.2. Giải thích mâu thuẫn V16 (đóng câu hỏi §4 của yêu cầu)

Handoff README ghi rõ nguyên nhân:

> Baseline V21 **không chứa trigger**. Đây là lỗi của file dump gốc… Dump gốc dùng
> `mysqldump --no-data` — **không có `--triggers`**.

**Baseline V21 CÓ `properties.listing_code`** (varchar(32) NOT NULL), **UNIQUE
`uq_properties_listing_code`**, và bảng `property_listing_code_allocations` — chỉ **thiếu
2 trigger**.

Điều này giải thích trọn vẹn: `listing_code` tồn tại **trong schema tại thời điểm baseline**
(không phải do V16 tạo trong quá trình migrate). Vì vậy:
- `V21__property_image_scan.sql` migrate thành công dù `V16` không có trong Flyway history —
  nó chỉ cần **cột đã tồn tại**, không cần bản thân migration V16.
- Kết luận trước đây của tôi ("legacy lineage không thể có listing_code") là **sai** vì đã
  dùng baseline từ `flyway-local-forward` (dump ngày 2026-11-02, chỉ tới V14, **trước khi**
  V16 có hiệu lực). Baseline V21 đúng đã có cột này.

### Y.3. Dựng môi trường (đã làm, đúng isolation guard)

| Bước | Kết quả |
|---|---|
| Datadir mới | `.scratch\pr38-handoff\mysql-isolated\data` — **kết thúc `/mysql-isolated/data/`** theo `STAGING_DATADIR_SUFFIX` |
| Identity check | `@@port = 3307` · `@@datadir = F:/SmartProp/.scratch/pr38-handoff/mysql-isolated/data/` · `@@server_uuid = 5a69ab6f-…` (**khác** 3306) ✅ |
| User cho view DEFINER | Tạo `smartprop@localhost` (view trong dump có `DEFINER='smartprop'@'localhost'`) — **không sửa SQL** |
| Restore V21 | **PASS** |
| Triggers | `listing_code_triggers.sql` — không khai báo DEFINER, dùng user hiện tại (Cách 1 trong README) |
| **Migrate V22..V26** | **BUILD SUCCESS** — `applied 5 migrations, now at version v26` |

### Y.4. Verify schema sau restore (`VERIFIED`)

| Kiểm tra | Giá trị |
|---|---|
| Tổng bảng | **56** |
| `properties.listing_code` | **1** ✅ |
| `uq_properties_listing_code` | **1** ✅ |
| `property_listing_code_allocations` | **1** ✅ |
| **Triggers trên `properties`** | **2** ✅ (`_insert`, `_update`) |
| `users` (dữ liệu người dùng) | **0** ✅ không có PII |
| Flyway history | **7** → sau migrate **12** |
| Coordinate provenance | `property_coordinate_audit` **tồn tại** |

**Flyway history cuối — đúng 12 mục guard yêu cầu:**

```
13 BASELINE · 14 (-1382804267) · 17 · 18 · 19 · 20 · 21 · 22 · 23 · 24 · 25 · 26
```

Không có V27. Không sửa history. Không nới guard. Không sửa migration SQL.

### Y.5. Spring Boot readiness — **PASS**

```
8080 READY
```

Hibernate `ddl-auto: validate` **PASS** — không thiếu column nào (đối lập với baseline
V13 trước đó thiếu `listing_code`).

Cần set thêm khi chạy: `APP_VALUATION_ENABLED=true` (YAML để `app.valuation.enabled: false`,
nên `ValuationClient` trả 503 `VALUATION_UNAVAILABLE` nếu không bật).

### Y.6. Flow B real E2E — **PASS (14/15)**

Test account: `wp01.test@example.invalid`, role nâng `BUYER → BROKER` trong DB cô lập
(đúng yêu cầu BROKER của `SecurityConfig`, fixture hợp lệ, không dùng tài khoản thật).

| # | Kiểm tra | Kết quả |
|---|---|---|
| 1 | Login (JWT) | **PASS** — status 200 |
| 2 | HOUSE basic | **PASS** — `5,365 tỷ` · v1.3 |
| 3 | HOUSE enriched (road/frontage/street/floors/subtype/bathrooms/direction) | **PASS** — `8,946 tỷ` |
| 4 | LAND | **PASS** — `4,059 tỷ` |
| 5 | APARTMENT (balcony direction) | **PASS** — `4,545 tỷ` |
| 6 | VILLA (subtype villa) | **PASS** — `16,775 tỷ` |
| 7 | Không token | **PASS** — **401** |
| 8 | `area = 0` | **PASS** — 400 |
| 9 | `floors = 99` | **PASS** — 400 |
| 10 | `houseSubtype = penthouse` | **PASS** — 400 |
| 11 | Street chuẩn `Nguyễn Phước Lan` | **PASS** — 8.4254 tỷ |
| 12 | Street có tiền tố `Đường …` | **PASS** — 8.4254 tỷ |
| 13 | Street lowercase + khoảng trắng | **PASS** — 8.4254 tỷ |
| 14 | **3 biến thể street cùng giá** | **PASS** — `8425395955` ×3 |
| 15 | **Location không hỗ trợ (`Hà Nội`)** | **FAIL** — trả **200** thay vì 4xx |

### Y.7. Lệch còn lại giữa hai luồng

**Flow A** (FastAPI trực tiếp): `location_feature = "Hà Nội"` → **422** ✅
**Flow B** (qua Spring Boot): cùng input → **200** (có giá)

⇒ Spring Boot **không chuyển nguyên văn** địa bàn không hợp lệ xuống FastAPI — nó map/normalize
trước khi gọi. Kết quả: chính sách location **chưa đồng nhất giữa hai luồng**.

Đây là lỗi thật, phạm vi hẹp, nằm trong `ValuationService`/`ValuationClient` — **chưa sửa**
vì cần quyết định mapping nào là chuẩn (không được tự đổi địa bàn người dùng nhập).

### Y.8. Database integrity sau E2E

| Bảng | Số dòng | Ý nghĩa |
|---|---|---|
| `properties` | **0** | Preview **không tự publish listing** ✅ |
| `valuation_history` | **0** | Preview **không ghi history** ngoài contract ✅ |
| `property_listing_code_allocations` | **0** | Không insert property → trigger chưa cấp mã, nhất quán ✅ |
| triggers | **2** | Nguyên vẹn ✅ |
| flyway_history | **12** | Không đổi trong E2E ✅ |

Không ghi đè asking price · không tạo dữ liệu vật lý giả · không sửa coordinate/legal.

### Y.9. Trạng thái môi trường sau phiên

| Hạng mục | Trạng thái |
|---|---|
| MySQL Portable 8.4.13 | **GIỮ** |
| **Fixture V26 mới** `.scratch\pr38-handoff\mysql-isolated\data` | **GIỮ** — schema đầy đủ, dùng lại được |
| Fixture `clean-v26` (thiếu listing_code) | GIỮ — không xoá |
| Datadir gốc V27 / work-3307 | GIỮ nguyên |
| Port 3307 | **FREE** |
| Port 3306 | BUSY pid 6556 — không đụng |
| 8080 / 8000 | free |

### Y.10. Khởi động lại môi trường (cho các phiên sau)

```powershell
# 1. MySQL 8.4.13 trên 3307 với fixture PR38
& F:\SmartProp\.scratch\mysql-8.4\mysql-8.4.13-winx64\bin\mysqld.exe `
  --datadir=F:\SmartProp\.scratch\pr38-handoff\mysql-isolated\data `
  --port=3307 --bind-address=127.0.0.1 --skip-log-bin --mysqlx=0

# 2. FastAPI
uvicorn main:app --host 127.0.0.1 --port 8000   # trong ai-services

# 3. Spring Boot
SPRING_PROFILES_ACTIVE=hybrid-local-existing-v13-staging
DB_USER=wp01test  DB_PASSWORD=<test>  JWT_SECRET=<test>
APP_VALUATION_ENABLED=true  PORT=8080
```

### Y.11. Còn lại của WP-01

| Hạng mục | Trạng thái |
|---|---|
| Flow A real E2E | **PASS** |
| **Flow B real E2E** | **PASS** (14/15; 1 case location) |
| Cross-flow prediction parity | **PARTIAL** — street 3 biến thể cho cùng giá ở cả hai luồng; encoded-vector parity chưa so |
| **Location validation đồng nhất** | **FAIL** — Flow B chấp nhận địa bàn không hỗ trợ |
| Street consistency | `UNKNOWN_MAPPING` — chưa có cảnh báo UI |
| Production routing | **PARTIAL** — chưa có reverse proxy thật |

```
WP_01_IMPLEMENTATION_COMPLETE
FLOW_A_REAL_E2E_PASS
FLOW_B_REAL_E2E_PASS (với 1 lệch location)
V1_3_ARTIFACT_INTEGRITY_PASS
LOCATION_VALIDATION_PASS (Flow A) / FAIL (Flow B)
VALIDATION_PARTIAL
NOT_READY_TO_MERGE
```

---

## Z. WP-01 FINAL CLOSURE (sau khi merge main `1f36205`)

### Z.1. Main reconciliation

| Mục | Giá trị |
|---|---|
| `origin/main` | **`1f36205f`** — "Merge pull request #39 from manchae19/feature/admin-coordinate-review-ui" |
| Merge vào integration | **`git merge origin/main`** — **sạch, 0 conflict** |
| Integration HEAD sau merge | `6258638` → sau fix: **`9c4619d`** |
| Bảo toàn | PR #38 Coordinate Provenance · PR #39 Admin Coordinate Review · parcel eligibility · evidence validation · per-property/revision conflict lock · HTTP 409 · deterministic pagination · migration lineage guard |
| PR #41/#37 | **không đụng** |
| Merge WP-01 → main | **KHÔNG** |

### Z.2. Location root cause (`VERIFIED`)

`ValuationService` dòng 68 cũ:

```java
String location=r.locationFeature().strip();                       // chưa canonical hoá
if(options.categories().stream().noneMatch(
     c->c.category().equals(category)&&c.locations().contains(location)))  // contains = case-sensitive
   return unsupported(...);
```

`DISTRICTS` và `options.categories().locations()` chứa **dạng hiển thị** ("Cẩm Lệ"), còn input
được so **nguyên văn** → `"cẩm lệ"` không khớp ⇒ **reject**, trong khi Flow A chuẩn hoá bằng
`clean_category()` nên **accept**. Đó là lệch duy nhất.

### Z.3. Location fix

```java
String location=displayDistrict(r.locationFeature());               // tái dùng helper có sẵn
if(location==null||options.categories().stream().noneMatch(...))return unsupported(...);
```

- Dùng **cùng một nguồn chuẩn**: vocabulary district của V1.3 qua `/model/options`.
- Cho phép: canonical name, Unicode NFC, trim, casefold (`equalsIgnoreCase`).
- **Không** cho phép: default district, map Hà Nội/TP.HCM → Đà Nẵng, chọn district phổ biến,
  suy diễn ward/street.
- Không hardcode whitelist thứ hai — `displayDistrict` đọc từ `DISTRICTS` đã dùng cho options.
- Không thêm mapping hành chính mới.

### Z.4. Location parity matrix — **PASS 10/10, 0 mismatch**

| district | Flow A | Flow B | decision |
|---|---|---|---|
| `Cẩm Lệ` | 200 ACCEPT | 200 ACCEPT | **OK** |
| `cẩm lệ` | 200 ACCEPT | 200 ACCEPT | **OK** (trước fix: B reject) |
| `  Cẩm Lệ  ` | 200 ACCEPT | 200 ACCEPT | **OK** |
| `Hải Châu` | 200 ACCEPT | 200 ACCEPT | **OK** |
| `Thanh Khê` | 200 ACCEPT | 200 ACCEPT | **OK** |
| `Hà Nội` | **422 REJECT** | 200 `available=false` REJECT | **OK** |
| `TP. Hồ Chí Minh` | **422 REJECT** | 200 `available=false` REJECT | **OK** |
| `Quận Không Tồn Tại` | **422 REJECT** | 200 `available=false` REJECT | **OK** |
| `""` | 422 REJECT | 400 REJECT | **OK** |
| missing | 422 REJECT | 400 REJECT | **OK** |

Status code khác nhau (được phép), **quyết định accept/reject giống nhau 10/10**.
Invalid location **không tới model inference** (Flow A 422 trước khi gọi predictor; Flow B
không gọi FastAPI).

### Z.5. Street consistency warning — **PASS 9/9**

Thêm vào FastAPI (nguồn duy nhất, cả hai luồng hưởng):

```python
STREET_UNVERIFIED_WARNING = (
    "Tên đường chưa được đối chiếu với khu vực đã chọn. "
    "Kết quả định giá có thể thay đổi đáng kể nếu thông tin vị trí không chính xác.")
```

`V1_3PreviewResponse.warnings: list[str] = []` (additive). Spring đã đọc `warnings` từ FastAPI
và forward nguyên vẹn ⇒ **không cần sửa FE**.

| Case | Flow A | Flow B |
|---|---|---|
| Street known (`Nguyễn Phước Lan`) | cảnh báo ✅ | cảnh báo ✅ |
| Street có tiền tố `Đường …` | cảnh báo ✅ | cảnh báo ✅ |
| Street OOV | cảnh báo ✅ | cảnh báo ✅ |
| Không nhập street | **không** cảnh báo ✅ | **không** cảnh báo ✅ |
| Stale (gửi street rồi bỏ) | **không** giữ cảnh báo cũ ✅ | — |

Phân biệt rõ: `KNOWN_MODEL_CATEGORY` (street trong vocab) **không** đồng nghĩa
`VERIFIED_MATCH`. Trạng thái vẫn `UNKNOWN_MAPPING`. Cảnh báo **không** tuyên bố đã xác minh
địa chỉ. Model input giữ nguyên policy hiện tại (không tự bỏ street feature).

### Z.6. Cross-flow prediction parity — **PASS 5/5, delta = 0**

Cùng input ngữ nghĩa, so **giá cuối**:

| Case | Flow A | Flow B | delta |
|---|---:|---:|---:|
| HOUSE basic | 5,365098 tỷ | 5,365098 tỷ | **0** |
| HOUSE full (road/frontage/street/floors/subtype/bathrooms/direction) | 8,946491 tỷ | 8,946491 tỷ | **0** |
| LAND | 4,059448 tỷ | 4,059448 tỷ | **0** |
| APARTMENT (+balcony direction) | 4,544814 tỷ | 4,544814 tỷ | **0** |
| VILLA (subtype villa) | 16,775497 tỷ | 16,775497 tỷ | **0** |

Delta **chính xác 0** trên 5/5 case, 4 loại BĐS ⇒ cùng encoded vector, cùng model, cùng
calibration, cùng inverse transform.

**Về `features_used`:** hai luồng trả **shape khác nhau có chủ đích** —
Flow A: raw V1.3 (`area`, `district`, `normalized_type`, …);
Flow B: subset camelCase có giới hạn (`areaSqm`, `locationFeature`, …) do
`ValuationService` cố ý chỉ expose "numeric/enum model features", không trả arbitrary upstream
JSON. Vì vậy **không so key-by-key** được; bằng chứng parity là **giá cuối delta = 0**.
Không thêm debug endpoint công khai.

### Z.7. Flow B final E2E — **PASS 15/15**

| # | Case | Kết quả |
|---|---|---|
| 1 | Login (JWT) | PASS |
| 2 | HOUSE basic | PASS — 5,365 tỷ |
| 3 | HOUSE enriched | PASS — 8,946 tỷ |
| 4 | LAND | PASS — 4,059 tỷ |
| 5 | APARTMENT | PASS — 4,545 tỷ |
| 6 | VILLA | PASS — 16,775 tỷ |
| 7 | Không token | PASS — 401 |
| 8 | Location không hỗ trợ | PASS — REJECT (`available=false`) |
| 9 | `area=0` | PASS — 400 |
| 10 | `floors=99` | PASS — 400 |
| 11 | `subtype=penthouse` | PASS — 400 |
| 12 | Street chuẩn | PASS — 8,4254 tỷ |
| 13 | Street có tiền tố | PASS — 8,4254 tỷ |
| 14 | Street lowercase | PASS — 8,4254 tỷ |
| 15 | 3 biến thể street cùng giá | PASS — `8425395955` ×3 |

**Lưu ý vận hành:** app có rate limit — test phải giãn cách (~3 s/lệnh), nếu không sẽ nhận
**429** và dễ bị đọc nhầm là lỗi chức năng.

`APP_VALUATION_ENABLED=true` chỉ set trong **biến môi trường phiên test**; default production
của repo **không đổi**.

### Z.8. Fresh regression trên final HEAD `9c4619d`

| Suite | Kết quả | Nhãn |
|---|---|---|
| **Backend full** | **230 / 230 PASS**, BUILD SUCCESS (+2 test từ PR #39) | **FRESH_PASS** |
| **FastAPI** | **222 passed**, 20 skipped, 84 subtests, **2 collection error RAG** | **FRESH_PASS** (trừ RAG) |
| **Frontend unit** | **67 / 67 PASS** | **FRESH_PASS** |
| **Production build** | **`✓ built in 7,05 s`** | **FRESH_PASS** |
| Flow A browser E2E | PASS (trước merge; code Flow A không đổi) | `REUSED_EVIDENCE` |
| Flow B E2E | **PASS 15/15** | **FRESH_PASS** |
| Location parity | **PASS 10/10** | **FRESH_PASS** |
| Street warning | **PASS 9/9** | **FRESH_PASS** |
| Cross-flow price parity | **PASS 5/5 delta 0** | **FRESH_PASS** |

**2 lỗi RAG collection** (`test_rag_area_filter.py`, `test_rag_public_projection.py`,
`ImportError: cannot import name 'area_spec'`) — **có từ main**, đã đối chiếu base trước đó
(`bab3d7b`) và vẫn còn trên `1f36205`. **Không sửa** (ngoài scope). Không báo full suite PASS.

### Z.9. Production-like routing — **PARTIAL**

| Kiểm tra | Trạng thái |
|---|---|
| `vite build` production bundle | **PASS** |
| `vite preview` + proxy `/api/ai` → JSON thật | **PASS** (phiên trước) |
| **Reverse proxy độc lập (nginx/IIS) trên static build** | **NOT_RUN** — repo không có config deploy |

⇒ `PRODUCTION_LIKE_ROUTING_PASS` **chưa đạt**; `ACTUAL_PRODUCTION_DEPLOYMENT_VERIFIED`
**dứt khoát chưa**. Không chuyển Flow A sang Spring Boot (WP-09 chưa duyệt). FastAPI không mở
ra Internet.

### Z.10. Database integrity

| Kiểm tra | Giá trị |
|---|---|
| Flyway history | **12** (V13 BASELINE · V14 · V17..V26) — không đổi |
| `properties` | **0** |
| `valuation_history` | **0** |
| `property_listing_code_allocations` | **0** |
| Triggers `listing_code` | **2** |
| Preview tự publish listing | **KHÔNG** |
| Ghi đè asking price | **KHÔNG** |
| Ghi history ngoài contract | **KHÔNG** |
| Tạo listing code ngoài luồng đăng tin | **KHÔNG** |
| Fallback V6 | **KHÔNG** |
| Sửa toạ độ / pháp lý | **KHÔNG** |

### Z.11. Model hash integrity

| File | SHA256 (prefix) |
|---|---|
| `model.json` | `3c56b6937902d9f736f9eb0278683f0c…` |
| `calibration.json` | `17632bdf4d578723a5c336b7c7e3aed6…` |
| `feature_schema.json` | `84be275b12b3c426497c00be80eed621…` |

Không đổi. Không train. Không synthetic. Không Shadow.

### Z.12. Môi trường sau phiên

| Hạng mục | Trạng thái |
|---|---|
| Port 3307 | **FREE** (shutdown graceful) |
| Port 3306 | BUSY pid 6556 — **không đụng** |
| 8080 / 8000 | free |
| Fixture V26 `.scratch\pr38-handoff\mysql-isolated\data` | **GIỮ** — dùng lại cho WP-02..WP-08 |
| MySQL Portable 8.4.13 | **GIỮ** |
| Các fixture khác (`clean-v26`, `work-3307`, datadir gốc V27) | **GIỮ nguyên**, không xoá |

### Z.13. Final gate

```
WP_01_IMPLEMENTATION_COMPLETE
MAIN_RECONCILIATION_PASS
FLOW_A_REAL_E2E_PASS
FLOW_B_REAL_E2E_PASS
LOCATION_VALIDATION_PASS
CROSS_FLOW_PARITY_PASS
STREET_WARNING_VERIFIED
V1_3_ARTIFACT_INTEGRITY_PASS
PRODUCTION_LIKE_ROUTING_PARTIAL
```

**Chỉ còn một mục chưa đạt:** `PRODUCTION_LIKE_ROUTING_PASS` — cần reverse proxy độc lập
(nginx/IIS) cho static build, hiện repo chưa có cấu hình deploy. Đây là blocker **duy nhất**.

---

## AA. WP-01 FINAL ACCEPTANCE

### AA.1. Production-like reverse proxy — `PRODUCTION_LIKE_ROUTING_PASS`

| Mục | Giá trị |
|---|---|
| Web server | **nginx 1.29.3 Windows portable** (nginx.org, chính thức) |
| Vị trí | `.scratch\nginx\nginx-1.29.3\` — **không** Windows Service, **không** PATH, **không** ghi đè phần mềm khác |
| Listener | `127.0.0.1:8090` (loopback only, **không** phải production deployment) |
| Static root | `frontend/dist` (React production build, **không** Vite dev/preview) |
| Conf | `.scratch\nginx\nginx-1.29.3\conf\smartprop-test.conf` |

Routing đã cấu hình và kiểm chứng:

| Đường | Đích | Kiểm chứng |
|---|---|---|
| `/` (SPA fallback) | `try_files $uri $uri/ /index.html` | `/valuation` → **200**, có `div#app` |
| `/api/ai/` → FastAPI | `proxy_pass http://127.0.0.1:8000/` (**strip prefix**) | `GET /api/ai/model/options` → **200**, `application/json`, **867 byte**, `model_version: v1.3` |
| `/api/v1/` → Spring Boot | `proxy_pass http://127.0.0.1:8080` (giữ nguyên path) | `POST /api/v1/auth/login` → **200** |
| Static assets | `/assets/*` | phục vụ từ `dist`, render đầy đủ |

Header forward: `Host`, `X-Real-IP`, `Authorization`, `Cookie`, `X-Refresh-Session`, `X-CSRF-TOKEN`.
Timeout `proxy_read_timeout 30s`. **Không** tạo proxy tùy ý tới endpoint nội bộ. FastAPI **không** lộ ra Internet.

### AA.2. Browser E2E trên static production build — **PASS 13/13**

Chạy Playwright thật trên `http://127.0.0.1:8090` (nginx, **không** Vite):

| # | Kiểm tra | Kết quả |
|---|---|---|
| 1 | Deep link `/valuation` | **200** |
| 2 | SPA render (title) | PASS |
| 3 | SPA **refresh** vẫn render | PASS |
| 4 | Model options qua nginx | PASS — `v1.3`, 3 category |
| 5 | Flow A submit | PASS |
| 6 | Flow A hiển thị giá | PASS — **7,69 tỷ** |
| 7 | Có input street | PASS |
| 8 | **Street warning hiển thị trên UI** | PASS |
| 9 | Bỏ street → cảnh báo **biến mất** | PASS |
| 10 | Responsive 390 px | PASS |
| 11 | Deep link `/login` | **200** |
| 12 | Form login render | PASS |
| 13 | Không có page error | PASS |

### AA.3. Encoded-vector parity — **PASS 5/5**

Instrumentation **test-only**: `_capture_for_test()` trong FastAPI ghi payload nhận được ra file
**chỉ khi** biến môi trường `SMARTPROP_TEST_CAPTURE` được đặt. Không có endpoint debug công khai,
mặc định là no-op.

Payload của **hai luồng** được capture, sau đó nạp vào `map_v6_to_v1_3()` + `transform()` để lấy
ma trận encoded **thật** (22 feature theo `feature_schema.json`) và so từng ô.

| Case | Payload giống nhau | **Encoded vector giống nhau** |
|---|---|---|
| HOUSE basic | ✅ | ✅ |
| HOUSE enriched | ✅ | ✅ |
| LAND | ✅ | ✅ |
| APARTMENT | ✅ | ✅ |
| VILLA | ✅ | ✅ |

22 feature được đối chiếu nguyên vẹn: `area, floor_count, frontage_width, road_width,
bedroom_count, bathroom_count, has_floor, has_frontage, has_road_width, has_bedroom,
has_bathroom, has_project, has_street, has_ward, frontage_sqrt_area_ratio, normalized_type,
district, ward, raw_street_name, raw_project_name, raw_house_direction, raw_balcony_direction`.

⇒ Feature names, thứ tự, numeric, categorical, missing indicators và encoded values **giống hệt**
giữa hai luồng. Kết hợp với delta giá = 0 ⇒ raw model output, calibration và final price giống hệt.

### AA.4. Location contract — **PASS**

| Luồng | HTTP | Business result | Giá |
|---|---|---|---|
| Flow A (`/predict`, `Hà Nội`) | **422** | reject, `detail="unsupported_location: …"` | **None** |
| Flow B (`valuation-preview`, `Hà Nội`) | **200** | `available=false`, `modelVersion=null` | **None** |

**Làm rõ báo cáo cũ:** HTTP 200 của Flow B **không** phải một định giá thật — đó là envelope
"không đủ điều kiện định giá" của contract Spring (`available=false`) và **không có giá**.
Phân biệt rõ **HTTP status** ≠ **business result**.

Invalid location **không tới model inference**: Flow A chặn trước predictor; Flow B không gọi
FastAPI (trả envelope ngay). Policy đã sửa giữ nguyên; không map địa danh ngoài Đà Nẵng.

### AA.5. Street warning UI — Flow A **PASS**, Flow B **NOT_VERIFIED**

| Luồng | API warnings | UI render |
|---|---|---|
| Flow A | PASS 9/9 | **PASS** (browser, nginx static build) |
| Flow B | PASS 9/9 (Spring forward đúng) | **NOT_VERIFIED** — chưa chạy browser trên `/post` |

Với case thật (Flow A): có street → cảnh báo hiển thị; bỏ street → cảnh báo biến mất (không stale).
`UNKNOWN_MAPPING` giữ nguyên, không tạo mapping địa lý.

### AA.6. Regression

| Suite | Kết quả | Nhãn |
|---|---|---|
| **FastAPI** (sau instrumentation) | **222 passed**, 20 skipped, 84 subtests, **2 RAG collection error** | **FRESH_PASS** (trừ RAG) |
| Backend full (merged HEAD, backend không đổi sau đó) | **230 / 230** | **FRESH_PASS** |
| Frontend unit | **67 / 67** | **FRESH_PASS** |
| Production build | `✓ built in 1,68 s` | **FRESH_PASS** |
| Browser E2E (nginx + static) | **13 / 13** | **FRESH_PASS** |
| Encoded-vector parity | **5 / 5** | **FRESH_PASS** |
| Location contract | 2/2 luồng reject đúng | **FRESH_PASS** |

2 lỗi RAG (`area_spec`) vẫn **có từ main** — không sửa (ngoài scope). Không gọi full suite PASS.

### AA.7. Database + model integrity

| Kiểm tra | Giá trị |
|---|---|
| Flyway history | **12** (không đổi) |
| `properties` | **0** |
| `valuation_history` | **0** |
| `property_listing_code_allocations` | **0** |
| Triggers `listing_code` | **2** |
| `model.json` | `3c56b693…` (không đổi) |
| `calibration.json` | `17632bdf…` (không đổi) |
| `feature_schema.json` | `84be275b…` (không đổi) |

Không train · không đổi weights · không Shadow · không nới rate limit production.

### AA.8. Trạng thái môi trường

`3307 FREE` (shutdown qua `SHUTDOWN`) · `3306 BUSY` (service nhóm, **không đụng**) ·
`8000/8080/8090 FREE` · MySQL Portable + fixture V26 + nginx portable **giữ lại** để tái sử dụng.

### AA.9. Gate

```
WP_01_IMPLEMENTATION_COMPLETE
MAIN_RECONCILIATION_PASS
FLOW_A_REAL_E2E_PASS
LOCATION_VALIDATION_PASS
CROSS_FLOW_PRICE_PARITY_PASS
ENCODED_VECTOR_PARITY_PASS
PRODUCTION_LIKE_ROUTING_PASS
V1_3_ARTIFACT_INTEGRITY_PASS
FLOW_B_REAL_E2E_PASS (HTTP integration 15/15 — KHÔNG phải browser)
STREET_WARNING_UI_PASS (Flow A browser; Flow B chỉ API)
NOT_READY_FOR_FINAL_REVIEW
```

**Hai mục chưa đạt đúng nghĩa:**
1. **Flow B browser E2E** — mới chạy HTTP integration 15/15, **chưa** drive `/post` multi-step trên browser.
2. **Street warning UI ở Flow B** — API forward đúng nhưng **chưa** xác minh React render.

---

## AB. WP-01 FINAL BROWSER ACCEPTANCE

### AB.1. Runtime environment (tái sử dụng, không cài lại)

| Thành phần | Giá trị | Kiểm chứng |
|---|---|---|
| MySQL Portable 8.4.13 | `.scratch\mysql-8.4\` · `127.0.0.1:3307` | READY |
| Fixture V26 | `.scratch\pr38-handoff\mysql-isolated\data` | `@@datadir` kết thúc `/mysql-isolated/data/` · **không** restore lại |
| FastAPI | `127.0.0.1:8000` | READY |
| Spring Boot | `127.0.0.1:8080`, profile `hybrid-local-existing-v13-staging` | READY |
| nginx 1.29.3 | `127.0.0.1:8090` · static `frontend/dist` | READY |
| Trình duyệt | Playwright + Chromium thật | — |

**Phát hiện khi khởi động:** browser login qua nginx ban đầu trả **403** vì
`app.cors-origins` mặc định chỉ cho `http://localhost:5173`. Đã chạy test với
`CORS_ORIGINS=http://127.0.0.1:8090,http://localhost:8090,http://localhost:5173`
qua **biến môi trường phiên test** — **không** sửa default production.
Sau đó `POST /api/v1/auth/login` → **200**, chuyển tới `/home`.

### AB.2. Flow B browser E2E — **BLOCKED (không đạt)**

Đã đi được tới bước 2 của form đăng tin bằng trình duyệt thật, **không mock**:

| Bước | Kết quả |
|---|---|
| Mở `/login`, đăng nhập bằng form thật | **PASS** — 200, → `/home` |
| Điều hướng client-side tới `/post` (token lưu in-memory, hard reload sẽ mất) | **PASS** |
| Điền bước 1 (`#post-propertyType`, `#post-title`, `#post-area`, `#post-price`) | **PASS** |
| Chuyển bước 1 → 2 | **PASS** — `/post/step-2` |
| Điền bước 2 (`#post-address`, `#post-district`) | **PASS** |
| **Panel định giá `[data-testid="valuation-panel"]` render** | **FAIL** — `panels=0` (kể cả sau khi scroll cuối trang) |
| Kích hoạt định giá, đọc `valuation-price` | **NOT_RUN** (phụ thuộc panel) |
| Street warning UI ở Flow B | **NOT_RUN** (phụ thuộc panel) |
| Page error | **PASS** — 0 lỗi |

**Nguyên nhân đã xác định:** bước 2 là "Ảnh & vị trí"; panel định giá **không render** khi
form chưa có ảnh bất động sản (hoặc panel nằm ở bước 3). Chưa xác định được điều kiện chính xác
trong ngân sách phiên này, nên **không kết luận** là panel bị lỗi.

Screenshot bằng chứng: `.scratch\shots\flowb-step2-nopanel.png`.

⇒ **`FLOW_B_REAL_E2E_PASS` vẫn KHÔNG đạt ở nghĩa browser.** Evidence hiện có chỉ là
**HTTP integration 15/15** (phiên trước), loại evidence khác.

### AB.3. Street Warning UI

| Luồng | API | UI render |
|---|---|---|
| Flow A | 9/9 | **PASS** — browser trên static build (`chưa được đối chiếu với khu vực`), biến mất khi bỏ street |
| Flow B | 9/9 (Spring forward đúng) | **NOT_RUN** — panel chưa render |

### AB.4. Authentication & error handling (browser)

| Case | Kết quả |
|---|---|
| Truy cập `/post` khi chưa đăng nhập | **PASS** — redirect `/login?reason=login-required` |
| Login sai qua UI (bị CORS chặn trước khi sửa) | **PASS** — 403, không vào được |
| Login đúng qua UI | **PASS** — 200, `/home` |
| HTTP 200 + `available=false` (Flow B, location sai) | Không hiển thị như định giá thành công (không có giá) |

### AB.5. Test instrumentation safety — **PASS**

`_capture_for_test()` trong `ai-services/app/api/valuation.py`:

| Tiêu chí | Kết quả |
|---|---|
| Mặc định **no-op** | **PASS** — chỉ hoạt động khi `SMARTPROP_TEST_CAPTURE` được đặt; unset ⇒ `return` ngay |
| Public endpoint | **PASS** — không có; đây là hàm nội bộ gọi từ handler |
| Capture request người dùng thật | **PASS** — không; chỉ khi operator đặt biến môi trường |
| Dữ liệu nhạy cảm | **PASS** — chỉ ghi payload đặc trưng định giá (không PII, không token) |
| Ghi file ngoài test dir | **PASS** — đường dẫn do operator chỉ định; không có input từ người dùng |
| Thay đổi model output | **PASS** — không; chỉ đọc `payload.model_dump()` rồi return |
| Commit file capture/raw input | **PASS** — không; `encode-capture.jsonl` nằm trong `.scratch` |

**Quyết định:** giữ lại instrumentation (env-gated) để **tái lập** encoded-vector parity.
Loại bỏ nó sẽ làm mất khả năng tái lập bằng chứng; đây là 16 dòng, không ảnh hưởng runtime.
Nếu muốn bỏ, đó là một commit riêng sau nghiệm thu.

### AB.6. Regression evidence

Không có thay đổi **source** trong phiên này (chỉ chạy test). Code checkpoint giữ nguyên `649570e`.

| Suite | Kết quả | Nhãn |
|---|---|---|
| FastAPI (222 passed / 20 skip / 84 subtests / **2 RAG collection error**) | không đổi | `REUSED_EVIDENCE` (đúng code checkpoint) |
| Backend full 230/230 | không đổi | `REUSED_EVIDENCE` |
| Frontend 67/67 · build | không đổi | `REUSED_EVIDENCE` |
| Flow A browser trên static build | **13/13** (phiên trước) | `REUSED_EVIDENCE` |
| Flow B browser | **BLOCKED** | **FAIL** |
| Encoded-vector parity 5/5 | đã đo trực tiếp | `REUSED_EVIDENCE` |

2 lỗi RAG `area_spec` vẫn là vấn đề **pre-existing của main** — không sửa, không báo full PASS.

### AB.7. Database & model integrity

| Kiểm tra | Giá trị |
|---|---|
| Flyway history | **12** |
| Trigger `listing_code` | **2** |
| `properties` | **0** (không tạo tin đăng) |
| `valuation_history` | **0** |
| `property_listing_code_allocations` | **0** |
| `users` | **1** (test account `wp01.test@example.invalid`, không phải dữ liệu thật) |
| `model.json` | `3c56b693…` không đổi |
| `calibration.json` | `17632bdf…` không đổi |
| `feature_schema.json` | `84be275b…` không đổi |

Không có listing, không có history, không có allocation, không sửa toạ độ/pháp lý.
PR #38 và PR #39 **bảo toàn** (không sửa file nào của họ).

### AB.8. Môi trường

`3307 FREE` · `3306 BUSY` (service nhóm, không đụng) · `8000/8080/8090 FREE`.
Giữ lại: MySQL Portable, fixture V26, nginx portable, screenshots.

### AB.9. Gate

```
WP_01_IMPLEMENTATION_COMPLETE
MAIN_RECONCILIATION_PASS
FLOW_A_REAL_E2E_PASS
LOCATION_VALIDATION_PASS
CROSS_FLOW_PRICE_PARITY_PASS
ENCODED_VECTOR_PARITY_PASS
PRODUCTION_LIKE_ROUTING_PASS
TEST_INSTRUMENTATION_SAFE
V1_3_ARTIFACT_INTEGRITY_PASS
FLOW_B_REAL_E2E_PASS  ← KHÔNG đạt ở nghĩa browser
STREET_WARNING_UI_PASS ← Flow A đạt; Flow B chưa kiểm được
NOT_READY_FOR_FINAL_REVIEW
```

### AB.10. Việc cần làm để đóng hai mục còn lại

1. Xác định điều kiện render `PostValuationPanel` ở bước 2/3 (có thể cần ≥1 ảnh, hoặc panel
   nằm ở bước 3) — đọc `PostView.jsx` quanh `step === 2` / `step === 3`.
2. Bổ sung fixture ảnh nhỏ vào DB cô lập **hoặc** dùng ảnh mẫu để form hợp lệ.
3. Chạy lại browser E2E cho: HOUSE/LAND/APARTMENT/VILLA, street warning, mobile.
4. Fetch `origin/main` mới nhất trước khi tạo PR.

---

## AC. WP-01 FLOW B BROWSER ROOT CAUSE & CLOSURE

### AC.1. Exact root cause — **selector đúng, luồng test sai**

`PostValuationPanel` **có thật** và `data-testid="valuation-panel"` **có thật**. Test trước
tìm nó ở bước 2, nhưng panel nằm ở **BƯỚC 1**.

| Bằng chứng | Nguồn |
|---|---|
| `[showValuation] = useState(() => createStateStore(false))` | `PostView.jsx:50` — mặc định **false** |
| `onToggle` → `view.updateShowValuationValue($event.target.open)` | `PostView.jsx:917` — chỉ bật khi `<details>` **mở** |
| `{view.showValuation ? <PostValuationPanel …/> : null}` | `PostView.jsx:925` — render có điều kiện |
| `<details>` nằm trong aside của **bước 1**; probe: step1 `details=1`, step2 `details=0` | Playwright probe |

⇒ Panel là **UI thu gọn tuỳ chọn** ("Giá tham khảo · Tùy chọn"), phải bấm vào summary mới render.
**Không phải bug React.**

### AC.2. Nguyên nhân thứ hai — nút bị `disabled` (phát hiện sản phẩm thật)

Sau khi mở panel, nút "Xem giá tham khảo" **disabled** với thông báo:

> "Số phòng ngủ nằm ngoài phạm vi model (0–30; 0 là chưa khai báo)."

Khi field `#post-bedrooms` **để trống**, panel coi là ngoài phạm vi và khoá nút ⇒ người dùng
mở panel trên form mới sẽ không định giá được cho tới khi nhập phòng ngủ.
Thông báo ghi "0 là chưa khai báo" nhưng trạng thái trống lại bị chặn — **mâu thuẫn nhỏ về UX**.
Đây là quan sát thật; **chưa sửa** vì ngoài phạm vi tối thiểu của WP-01 và không chặn nghiệm thu
(người dùng nhập phòng ngủ là dùng được). Ghi nhận làm follow-up.

### AC.3. Test script changes (không sửa source production)

| Thay đổi | Lý do |
|---|---|
| Mở `<details>` "Giá tham khảo" **ở bước 1** trước khi dự đoán | điều kiện render thật |
| Chọn `[data-testid="valuation-location"]` = "Cẩm Lệ" | panel bắt buộc chọn khu vực |
| Bấm `[data-testid="valuation-preview"]` ("Xem giá tham khảo") | nút dự đoán thật |
| Chờ option district xuất hiện (async `/valuation-options`) | tránh race |
| Nhập `#post-bedrooms` hợp lệ (bỏ trống với Đất nền) | nút bị disable khi trống |
| Mở `[data-testid="valuation-advanced-toggle"]` để dùng `valuation-street-name` | trường street nằm trong "Thông tin bổ sung" |
| Retry 1 lần khi UI còn "—" | warm-up lần đầu |

**Không bypass validation · không inject state · không gọi API thay UI · auth/valuation/Spring/FastAPI/MySQL đều thật · không mock gì.**

### AC.4. Production source changes

**Không có.** Code checkpoint giữ nguyên `649570e`; source tree sạch (`git status` rỗng).

### AC.5. Flow B browser matrix — **PASS 15/15**

| # | Case | Kết quả |
|---|---|---|
| 1 | Login qua UI + mở `/post` | **PASS** |
| 2 | Mở `<details>` → panel render | **PASS** |
| 3 | HOUSE basic | **PASS** — 5.749.775.772 ₫ |
| 4 | Đổi input → định giá lại, **không stale** | **PASS** — 5,75 tỷ → 12,01 tỷ |
| 5 | HOUSE enriched (bedrooms/bathrooms) | **PASS** — 5.516.158.792 ₫ |
| 6 | LAND | **PASS** — 4.445.049.207 ₫ |
| 7 | APARTMENT | **PASS** — 4.525.170.095 ₫ |
| 8 | VILLA | **PASS** — 5.872.234.072 ₫ |
| 9 | Street warning (có street) | **PASS** |
| 10 | Street warning — prefix `Đường ` | **PASS** |
| 11 | Street warning — OOV street | **PASS** |
| 12 | Street warning — missing street (không cảnh báo) | **PASS** |
| 13 | Responsive 390 px | **PASS** |
| 14 | Page error | **PASS** — 0 |
| 15 | Network thật | `POST /api/v1/properties/valuation-preview` → **200** |

Giá hiển thị **trên giao diện**, không chỉ HTTP response. Screenshot:
`.scratch\shots\flowb-house-basic.png`, `flowb-mobile.png`.

**NOT_RUN (ghi rõ):** flow tới bước 2/3 và "thoát form không publish" — không chạy trong phiên này;
bước 2 cần xác nhận vị trí bằng Google Maps (phụ thuộc bên thứ ba).

### AC.6. Street Warning UI matrix

| Case | Flow A (browser) | Flow B (browser) |
|---|---|---|
| Known street | PASS | **PASS** |
| Prefix `Đường ` | PASS (API) | **PASS** |
| OOV street | PASS (API) | **PASS** |
| Missing street → không cảnh báo | PASS | **PASS** |
| Không stale sau khi đổi input | PASS | **PASS** (giá đổi, warning theo input) |

`UNKNOWN_MAPPING` giữ nguyên; cảnh báo không tuyên bố đã xác minh địa chỉ.

### AC.7. CORS deployment requirements (runbook)

`app.cors-origins` mặc định chỉ `http://localhost:5173`. Khi phục vụ static build qua một origin
khác (nginx `127.0.0.1:8090`), browser bị **403** ở `POST /api/v1/auth/login` — **không phải lỗi auth**.

**Bắt buộc khi deploy:**

```
CORS_ORIGINS=https://<domain-thật>
```

- Liệt kê **chính xác** origin, phân tách bằng dấu phẩy.
- **Không** dùng wildcard `*` (kèm `allowCredentials`, sẽ không hợp lệ và mở rộng tấn công).
- Trong phiên test dùng `http://127.0.0.1:8090,http://localhost:8090,http://localhost:5173` qua env.
- `app.cors-origins` là **cấu hình deploy**, không phải code — không sửa default trong repo.

### AC.8. Test instrumentation

`_capture_for_test()` vẫn env-gated (`SMARTPROP_TEST_CAPTURE`), mặc định no-op, không endpoint,
không PII, không đổi output. **Chưa chuyển sang harness riêng** trong phiên này — cần giữ để tái lập
encoded-vector parity 5/5. Đề xuất follow-up: chuyển sang pytest fixture/harness sau nghiệm thu.

### AC.9. Regression

Không đổi production source ⇒ evidence giữ nguyên đúng code checkpoint `649570e`:
Backend **230/230** · FastAPI **222 passed** / 20 skip / 84 subtests / **2 RAG collection error**
(pre-existing main) · Frontend **67/67** · build OK · encoded parity **5/5** · Flow A browser **13/13**.

Flow B browser **15/15 FRESH** (phiên này). Không nâng `REUSED_EVIDENCE` thành `FRESH_PASS`.

### AC.10. Integrity

| Kiểm tra | Giá trị |
|---|---|
| Flyway history | **12** |
| Triggers `listing_code` | **2** |
| `properties` | **0** (không publish) |
| `valuation_history` | **0** |
| `property_listing_code_allocations` | **0** |
| `users` | **1** (test account) |
| Model hashes | `3c56b693…` / `17632bdf…` / `84be275b…` — không đổi |
| Fallback V6 | không |

### AC.11. Môi trường

`3307 FREE` · `3306 BUSY` (service nhóm, không đụng) · `8000/8080/8090 FREE`.
Giữ: MySQL Portable, fixture V26, nginx portable, screenshots.

### AC.12. Gate

```
WP_01_IMPLEMENTATION_COMPLETE
MAIN_RECONCILIATION_PASS
FLOW_A_REAL_E2E_PASS
FLOW_B_REAL_E2E_PASS
LOCATION_VALIDATION_PASS
CROSS_FLOW_PRICE_PARITY_PASS
ENCODED_VECTOR_PARITY_PASS
STREET_WARNING_UI_PASS
PRODUCTION_LIKE_ROUTING_PASS
TEST_INSTRUMENTATION_SAFE
V1_3_ARTIFACT_INTEGRITY_PASS
READY_FOR_FINAL_REVIEW
```

**Ghi chú phạm vi:** Flow B browser đã phủ đủ 5 loại BĐS + street warning + responsive + không stale
ở **bước 1** (nơi panel định giá thực sự nằm). Các bước 2–3 (ảnh, xác nhận vị trí qua Google Maps,
gửi duyệt) **không** nằm trong phạm vi định giá và phụ thuộc dịch vụ bên thứ ba.

**Follow-up đề xuất (không chặn nghiệm thu):**
1. Panel báo "phòng ngủ ngoài phạm vi" khi field trống → nên coi trống = chưa khai báo.
2. Chuyển `_capture_for_test()` sang test harness riêng.
3. Bổ sung E2E bước 2–3 khi có môi trường Maps được phép.

---

## AD. WP-01 FINAL RELEASE CLEANUP & PR PREPARATION

**Integration HEAD:** `68dfaf4` · **origin/main:** `1f36205f` · **V1.3:** `a7db792`

### AD.1. Bedrooms root cause & fix

**Root cause** — `frontend/src/features/prediction/valuation.js:24`:

```js
const rooms = String(draft.bedrooms ?? '0');          // '' KHÔNG bị ?? bắt
if (propertyType !== 'LAND' && (!/^\d+$/.test(rooms) || Number(rooms) > 30)) return { reason: … };
```

`<input type="number">` trả **chuỗi rỗng** `''` khi để trống. `??` chỉ bắt `null/undefined`,
nên `''` lọt xuống `/^\d+$/` → **false** ⇒ báo "ngoài phạm vi" và **disable** nút.

**Fix** (chỉ valuation preview, không chạm validation publish):

```js
const roomsRaw = String(draft.bedrooms ?? '').trim();
const roomsProvided = roomsRaw !== '';
if (propertyType !== 'LAND' && roomsProvided && (!/^\d+$/.test(roomsRaw) || Number(roomsRaw) > 30)) …
…
bedrooms: propertyType === 'LAND' || !roomsProvided ? null : Number(roomsRaw),
```

- Trống ⇒ **`null` (missing)**, đúng missing-value handling của V1.3 (`bedroom_count = NaN`,
  `has_bedroom = 0`), **không** gán 0 (0 là giá trị người dùng chủ động khai báo).
- `0` vẫn hợp lệ; `-1`, `31`, `2.5`, `abc` vẫn bị chặn.
- LAND luôn `null`.

**Regression:** `frontend/tests/postValuationInput.test.mjs` — **20/20** (13 case mới: empty,
undefined, null, whitespace, 0, 1, 30, −1, 31, decimal, invalid string, LAND có/không bedrooms).

### AD.2. Test capture removed from production — **PASS**

| Trước | Sau |
|---|---|
| `_capture_for_test()` + `SMARTPROP_TEST_CAPTURE` **trong** `app/api/valuation.py` | **Đã xoá hoàn toàn** (`git grep` = 0 match) |
| Ghi payload ra file nếu env bật | Không còn đường ghi nào trong production |
| — | Capture chuyển sang `ai-services/tests/parity/capture_app.py` (pure-ASGI middleware, chỉ tồn tại trong test, import `main:app` của production) |

Production inference **không** ghi feature vector/request data. Không debug endpoint.
Không đổi output, schema, calibration. Parity vẫn tái lập: chạy
`uvicorn tests.parity.capture_app:app --port 8001` với `SMARTPROP_PARITY_CAPTURE`,
Spring trỏ `APP_VALUATION_BASE_URL=http://127.0.0.1:8001`.
Không commit capture file (nằm trong `.scratch`).

**Encoded-vector parity sau khi chuyển — PASS 5/5** (đo lại, không suy luận):
payload (trừ `title`/`description` là metadata tin đăng, không phải feature) **giống hệt** và
**ma trận encoded 22 feature giống hệt** cho HOUSE basic, HOUSE enriched, LAND, APARTMENT, VILLA.

### AD.3. Flow B valuation preview browser E2E — **PASS 18/18**

Gate đúng phạm vi: **`FLOW_B_VALUATION_PREVIEW_E2E_PASS`** (không gọi
`FULL_PROPERTY_POSTING_E2E_PASS` — chưa kiểm thử toàn quy trình đăng tin).

| # | Case | Kết quả |
|---|---|---|
| 1 | Login qua UI → `/post` | **PASS** |
| 2 | Mở `<details>` "Giá tham khảo" → panel | **PASS** |
| 3 | **HOUSE basic với bedrooms TRỐNG** | **PASS** — 6.605.239.848 ₫ (đây là fix) |
| 4 | bedrooms = 0 | **PASS** — vẫn định giá |
| 5 | bedrooms = 31 | **PASS** — bị chặn (disabled) |
| 6 | Đổi input → giá mới, không stale | **PASS** — 6,61 → 13,19 tỷ |
| 7 | HOUSE enriched | **PASS** — 5.516.158.792 ₫ |
| 8 | LAND | **PASS** — 4.445.049.207 ₫ |
| 9 | APARTMENT | **PASS** — 4.531.630.748 ₫ |
| 10 | VILLA | **PASS** — 5.893.564.675 ₫ |
| 11 | Street warning (có street) | **PASS** |
| 12 | Prefix `Đường ` | **PASS** |
| 13 | OOV street | **PASS** |
| 14 | Missing street | **PASS** — không cảnh báo |
| 15 | Responsive 390 px | **PASS** |
| 16 | Page error | **PASS** — 0 |
| 17 | Network thật | `POST /api/v1/properties/valuation-preview` **200** |
| 18 | Không mock auth/valuation/Spring/FastAPI/MySQL | **PASS** |

**NOT_RUN (ghi rõ):** bước 2–3 (Google Maps location) và "thoát form không publish" —
ngoài phạm vi valuation preview.

### AD.4. Flow A browser E2E — **PASS 13/13** (fresh, build mới)

Deep link · SPA render · refresh · model options qua nginx · submit · giá **7,69 tỷ** ·
street warning hiển thị · bỏ street → cảnh báo mất · responsive 390 px · `/login` 200 · 0 page error.

### AD.5. Regression (final code `68dfaf4`)

| Suite | Command | Kết quả | Nhãn |
|---|---|---|---|
| Backend full | `backend\mvnw.cmd -o -B test` | **230/230 PASS**, BUILD SUCCESS | **FRESH_PASS** |
| FastAPI | `pytest tests/ -q --ignore-glob='*test_rag*'` | **222 passed**, 20 skipped, 84 subtests | **FRESH_PASS** (trừ RAG) |
| Frontend | `node --test tests/*.test.mjs` | **91/91 PASS** (exit 0) | **FRESH_PASS** |
| Production build | `vite build` | `✓ built in 6.09 s` | **FRESH_PASS** |
| Flow A browser | Playwright + nginx | **13/13** | **FRESH_PASS** |
| Flow B browser | Playwright + nginx | **18/18** | **FRESH_PASS** |
| Encoded parity | harness 8001 | **5/5 + 22 feature** | **FRESH_PASS** |

**2 lỗi RAG** (`test_rag_area_filter.py`, `test_rag_public_projection.py`,
`ImportError: area_spec`) — **pre-existing trên main**, không sửa, **không** báo full FastAPI PASS.

### AD.6. Database integrity

| Kiểm tra | Trước | Sau |
|---|---|---|
| Flyway history | 12 | **12** |
| Triggers `listing_code` | 2 | **2** |
| `properties` | 0 | **0** |
| `valuation_history` | 0 | **0** |
| `property_listing_code_allocations` | 0 | **0** |
| `users` | 1 (test account) | **1** |

Không publish · không ghi đè asking price · không tạo listing code · không ghi history ·
không đổi toạ độ/pháp lý. Không xoá dữ liệu ngoài phiên test.

### AD.7. Model integrity

`model.json 3c56b693…` · `calibration.json 17632bdf…` · `feature_schema.json 84be275b…` — **không đổi**.
V1.3 vẫn là model duy nhất sinh giá mới · không fallback V6 · không train · không Shadow.

### AD.8. PR diff summary — **CLEAN**

`git diff --stat origin/main...HEAD` → **24 files, ~3.5k insertions, 19 deletions**.

| Nhóm | Số file |
|---|---|
| `backend/src/main` (ValuationRequest, ValuationService) | 2 |
| `backend/src/test` (ValuationServiceTest) | 1 |
| `frontend/src` (ValuationPanel, PostValuationPanel, AdvancedValuationFields, valuation.js, advancedValuation.js, usePostEditor.js) | 6 |
| `frontend/tests` | 3 |
| `ai-services/app` (schemas, valuation, adapter, features_v1_3) | 4 |
| `ai-services/tests` (street canonical + parity harness) | 3 |
| `docs/ai` | 5 |

Quét file ngoài scope (`jsonl|zip|npy|node_modules|.scratch|artifacts|.env|datadir|mysql|nginx|png|sql`)
→ **rỗng**. Không có dump/weights/raw data/credentials/screenshot trong diff.
Không file V1.4–V1.6 nào bị xoá.

**Không migration mới.** Không đổi migration SQL. Không nới guard.

### AD.9. Proposed PR

**Title:**
```
feat(ai): harden XGBoost V1.3 valuation inference and input consistency
```

**Description** (rút gọn — bản đầy đủ ở `SMARTPROP_WP01_FINAL_REPORT.md`):

> **Summary** — Siết luồng định giá XGBoost V1.3 ở cả hai luồng sản phẩm: kiểm tra địa bàn theo
> artifact, chuẩn hoá tên đường, hoàn thiện input contract, cảnh báo độ tin cậy vị trí.
>
> **Problem** — (1) địa bàn không hỗ trợ vẫn trả giá; (2) `Đường X` rơi vào OOV nên mất tín hiệu
> vị trí; (3) Flow A thiếu bathrooms/hướng nhà/ban công; (4) Flow B từ chối `cẩm lệ` trong khi
> Flow A chấp nhận; (5) không cảnh báo khi tên đường chưa đối chiếu được với khu vực;
> (6) để trống phòng ngủ làm khoá nút định giá.
>
> **Implementation** — whitelist district từ `feature_schema.json`; `canonical_street()`
> (exact-match-first, chỉ bỏ tiền tố khi ra entry thật, không fuzzy); `displayDistrict()`
> chuẩn hoá input Flow B; `warnings` (additive) cho street chưa xác minh; blank bedrooms = missing.
>
> **Architecture** — Flow A: React → `/api/ai` → FastAPI. Flow B: React → Spring Boot
> `/api/v1/properties/valuation-preview` → FastAPI. Không đổi kiến trúc; WP-09 gateway chưa duyệt.
>
> **Validation** — 422 (A) / `available=false` (B) cho địa bàn không hỗ trợ; parity 10/10.
>
> **Optional features** — blank = missing; không suy diễn, không default.
>
> **Street normalization** — NFC, casefold, trim, prefix strip có kiểm chứng.
>
> **Geographic warning** — `UNKNOWN_MAPPING` vẫn giữ; cảnh báo không tuyên bố đã xác minh địa chỉ.
>
> **Cross-flow parity** — giá cuối delta **0** trên 5/5 case; encoded vector 22 feature giống hệt.
>
> **Tests** — Backend 230/230 · FastAPI 222 (+2 pre-existing collection errors) · Frontend 91/91 ·
> Flow A browser 13/13 · Flow B browser 18/18 · build OK.
>
> **Routing** — production bundle phục vụ qua nginx (SPA fallback, `/api/ai` và `/api/v1`).
> **Chưa** kiểm thử deployment production thật.
>
> **CORS** — deploy cần `CORS_ORIGINS=https://<domain>` chính xác, **không wildcard**.
>
> **Database** — không migration mới; không publish/không ghi history ngoài contract.
>
> **Model** — hash không đổi; V1.3 là model duy nhất; không fallback V6.
>
> **Known limitations** — chưa E2E bước 2–3 của form đăng tin (Google Maps); chưa kiểm thử toàn
> bộ quy trình publish; `UNKNOWN_MAPPING` cho street↔district.
>
> **Pre-existing** — 2 lỗi RAG `area_spec` có từ main, không sửa.
>
> **Rollback** — revert merge commit; không có migration nên không cần rollback DB.
>
> **Merge risk** — thấp: additive API field, không đổi schema DB, không đổi model.

### AD.10. Gate

```
WP_01_IMPLEMENTATION_COMPLETE
MAIN_RECONCILIATION_PASS
FLOW_A_REAL_E2E_PASS
FLOW_B_VALUATION_PREVIEW_E2E_PASS
OPTIONAL_BEDROOMS_VALIDATION_PASS
LOCATION_VALIDATION_PASS
CROSS_FLOW_PRICE_PARITY_PASS
ENCODED_VECTOR_PARITY_PASS
STREET_WARNING_UI_PASS
PRODUCTION_LIKE_ROUTING_PASS
TEST_CAPTURE_REMOVED_FROM_PRODUCTION
DATABASE_INTEGRITY_PASS
V1_3_ARTIFACT_INTEGRITY_PASS
PR_DIFF_CLEAN
READY_FOR_PR_CREATION
```

### AD.11. Môi trường sau phiên

`3307 FREE` · `3306 BUSY` (service nhóm, không đụng) · `8000/8001/8080/8090 FREE`.
Giữ: MySQL Portable 8.4.13 · fixture V26 · nginx 1.29.3 · scripts test trong `.scratch`.
**Chưa push · chưa tạo PR · chưa merge.**
