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
