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
