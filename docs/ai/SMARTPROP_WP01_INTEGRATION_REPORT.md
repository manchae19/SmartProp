# SmartProp — WP-01 V1.3 Inference Hardening Integration

**Ngày:** 2026-11-27
**Trạng thái:** `WP_01_IMPLEMENTATION_COMPLETE` · `V1_3_REAL_FEATURES_VERIFIED` ·
`REAL_E2E_PASS` (Flow A) · **`E2E_BLOCKED`** (Flow B)
**Base:** `origin/main` `bab3d7b` · **Integration HEAD:** `9a75f03`
**Branch:** `feature/valuation-v1-3-hardening-integration`
**Worktree:** `F:\SmartProp\.worktrees\v13-hardening-integration`

Nhãn: `FRESH_PASS` · `REUSED_EVIDENCE` · `FAIL` · `BLOCKED` · `NOT_RUN`

---

## A. Main reconciliation

| Mục | Giá trị |
|---|---|
| `origin/main` | **`bab3d7b`** — PR #38 merged (coordinate provenance v1) |
| Branch hardening gốc | `feature/valuation-v1-3-inference-hardening` @ `a7db792` (base `d202792`, **trước** PR #38) |
| Chiến lược tích hợp | Worktree mới từ `bab3d7b` + **cherry-pick 3 commit** hardening |
| Kết quả cherry-pick | **Sạch, 0 conflict** |
| Branch hardening gốc | **Không đổi** (`a7db792` nguyên vẹn) |

### Commit đã port

| Commit mới | Từ | Nội dung |
|---|---|---|
| `a682393` | `497b842` | default real measurements + forward posting-form features |
| `1589616` | `79fdbac` | advanced valuation fields cho posting flow |
| `3f373a0` | `a7db792` | forward floors + house subtype, clear advanced fields on reset |
| `9a75f03` | **(mới)** | expose 4 real-measurement fields trong form standalone |

**Không cherry-pick commit research nào.** Không merge vào main.

---

## B. V1.3 production policy — `FRESH_PASS`

| Yêu cầu | Kết quả |
|---|---|
| V1.3 là model duy nhất tạo định giá mới | **PASS** |
| V6 không dùng làm fallback | **PASS** — `predictor_for()` raise **503** `"Model chưa sẵn sàng."` nếu V1.3 thiếu |
| V6 chỉ dùng cho shadow comparison | **PASS** — `predictor_v6` chỉ đọc khi `shadow_manager.is_enabled()` |
| LightGBM/Ensemble không phải production | **PASS** — không có trong `ai-services/` |
| Không retrain, không đổi weights | **PASS** |

**Artifact verification (`FRESH_PASS`):**

| File | SHA256 | Khớp |
|---|---|---|
| `model.json` | `3c56b6937902d9f736f9eb0278683f0c5ab8af027f5ea12b1a4072abff840a03` | ✅ |
| `calibration.json` | `17632bdf4d578723a5c336b7c7e3aed6021dbb68f38985b763839a763fbfe645` | ✅ |
| `feature_schema.json` | `84be275b12b3c426497c00be80eed621d7323ac2a2abcb282752c7a89361e7ea` | ✅ |

Runtime: `GET /health` → `{"status":"ok","model_version":"v1.3","model_ready":true}`

---

## C. Real feature mapping

### C.1. Phát hiện kiến trúc quan trọng

**Hai luồng có backend khác nhau** (`FRESH_PASS`, kiểm bằng E2E thật):

| Luồng | Đường đi | Payload |
|---|---|---|
| **Flow A** — standalone `ValuationPanel` | React → Vite proxy `/api/ai` → **FastAPI:8000 trực tiếp** | FastAPI shape: `category`, `area_sqm`, `location_feature` |
| **Flow B** — posting `PostValuationPanel` | React → **Spring Boot** `/api/v1/properties/valuation-preview` → FastAPI | Spring Boot shape: `propertyType`, `areaSqm`, `district` |

Proxy: `'/api/ai': {target: aiTarget, rewrite: strip '/api/ai'}` → `/api/ai/predict` = `http://127.0.0.1:8000/predict`.

**Hệ quả:** validation của Spring Boot (`@Min(1) @Max(20)` cho `floors`, `@Pattern` cho `houseSubtype`)
**không áp dụng cho Flow A**. Flow A chỉ có validator của FastAPI (`applicable_fields`).

### C.2. Field mapping — Flow A (đo qua E2E, `FRESH_PASS`)

| Field | Có trong UI | Có trong payload | Tới V1.3 |
|---|---|---|---|
| property type (`category`) | ✅ select | ✅ | ✅ |
| district (`location_feature`) | ✅ select | ✅ | ✅ |
| ward | ✅ text | ✅ | ✅ |
| area (`area_sqm`) | ✅ number | ✅ | ✅ |
| **street_name** | ✅ **mới** | ✅ | ✅ |
| **project_name** | ✅ **mới** | ✅ | ✅ |
| **road_width_m** | ✅ **mới** | ✅ | ✅ |
| **frontage_width_m** | ✅ **mới** | ✅ | ✅ |
| floors | ✅ (có sẵn) | ✅ | ✅ |
| house_subtype | ✅ (có sẵn) | ✅ | ✅ |
| rooms | ✅ | ✅ | ✅ |
| access_type | ✅ (có sẵn) | ✅ | ✅ (không phải model feature) |
| house_direction | ❌ | — | — |
| balcony_direction | ❌ | — | — |
| bathrooms | ❌ | — | — |

**Trước WP-01, Form A thiếu 4 field thực đo** dù `buildValuationPayload` đã hỗ trợ đủ.
Đã bổ sung ở commit `9a75f03` — chỉ thêm input, **không** đổi payload builder.

### C.3. Không tự bịa giá trị — `FRESH_PASS`

Đo trực tiếp qua payload bắt được:

| Kiểm tra | Payload thực tế |
|---|---|
| Basic (không nhập gì thêm) | `{"category":"Nhà ở","area_sqm":100,"location_feature":"Cẩm Lệ"}` |
| Enriched (nhập road/frontage/street) | `+ "road_width_m":12,"frontage_width_m":6,"street_name":"Nguyễn Văn Linh"` |
| Xoá road_width | payload **không còn** `road_width_m` |

→ Basic **không** gửi `road_width_m`/`frontage_width_m` ⇒ **không có giả định nào** được tạo.
Đây là bằng chứng thực nghiệm cho quy tắc "không tự giả định road/frontage".

---

## D. Standalone valuation E2E — `FRESH_PASS`

**Môi trường thật:** React dev server `:5173` → Vite proxy → FastAPI `:8000` → XGBoost V1.3 thật.
Playwright + Chromium. **Không mock.**

**18/18 PASS:**

| # | Kiểm tra | Kết quả |
|---|---|---|
| 1 | Trang `/valuation` mở được | PASS |
| 2 | Đủ 4 field thực đo | PASS |
| 3 | Bấm ước tính (basic) | PASS |
| 4 | Có giá basic | **6,61 tỷ đồng** |
| 5 | Payload gửi `area_sqm` | PASS |
| 6 | Basic **không** gửi `road_width_m` | PASS |
| 7 | Basic **không** gửi `frontage_width_m` | PASS |
| 8 | Bấm ước tính (enriched) | PASS |
| 9 | Có giá enriched | **17,08 tỷ đồng** |
| 10 | Enriched **có** `road_width_m` | PASS |
| 11 | Enriched **có** `frontage_width_m` | PASS |
| 12 | Enriched **có** `street_name` | PASS |
| 13 | Thêm feature thật **làm đổi giá** | PASS — 6,61 → 17,08 tỷ |
| 14 | UI nêu model version `v1.3` | PASS |
| 15 | Không lỗi JS | PASS |
| 16 | Xoá `road_width` → payload sạch | PASS |
| 17 | Mobile 390 px vẫn hiển thị kết quả | PASS |
| 18 | Không crash native | PASS |

**Giá trị cốt lõi:** thay đổi **2,58×** (6,61 → 17,08 tỷ) khi thêm road 12 m + frontage 6 m +
đường Nguyễn Văn Linh. Chứng minh real features **thực sự chảy tới model và tác động kết quả**,
không phải chỉ có trong payload.

> **Ghi nhận:** độ nhạy này rất lớn. Với 100 m² nhà ở Cẩm Lệ, thêm đường lớn + mặt tiền rộng
> + tên đường chính làm giá tăng 2,58×. Đây là hành vi của model V1.3, không phải lỗi tích hợp —
> nhưng cần nêu trong tài liệu giải thích để người dùng hiểu mức ảnh hưởng.

### D.1. E2E test cũ đã lỗi thời — `FAIL` (pre-existing)

`frontend/e2e/valuation.e2e.mjs` dùng selector **không còn tồn tại**:
`valuation-quick-address-input`, `v6-band`, `v6-governance`, nút `"Xem dự đoán V1.3"`.
→ Test này viết cho UI Vue/cũ. **Không** do WP-01. Đã thay bằng script mới dùng selector hiện tại.

---

## E. Posting valuation preview E2E — `BLOCKED`

| Hạng mục | Trạng thái |
|---|---|
| Unit test payload construction | `FRESH_PASS` — 11 test `advancedValuation` + 7 test `postValuationInput` |
| Unit test Spring Boot forward | `FRESH_PASS` — 4 test `floors`/`subtype` trong `ValuationServiceTest` |
| **Browser E2E thật** | **`BLOCKED`** |

**Lý do BLOCKED:** Flow B cần Spring Boot + MySQL cô lập + test authentication.

| Thành phần | Trạng thái |
|---|---|
| MySQL 3306 (production) | **CẤM** — không truy cập |
| MySQL 3307 | **free** — nhưng chưa dựng instance cô lập |
| Docker/Testcontainers | Chưa xác minh khả dụng |
| Test auth | Chưa có |

**Không** dừng/hijack service thành viên. **Không** bỏ migration validation.

### E.1. Tương đương hai luồng — phân tích ở tầng payload

Cùng input ⇒ cùng output nếu payload FastAPI tương đương. So sánh:

| Key | Flow A gửi | Spring Boot tạo ra (Flow B) | Tương đương? |
|---|---|---|---|
| `category` | trực tiếp | từ `propertyType` → label tiếng Việt | ✅ |
| `area_sqm` | trực tiếp | từ `areaSqm` | ✅ |
| `location_feature` | trực tiếp | từ `district` | ✅ |
| `ward` | ✅ | ✅ | ✅ |
| `rooms` | từ `form.rooms` | từ `bedrooms` | ✅ |
| `house_subtype` | ✅ | VILLA→`villa`; HOUSE→explicit | ✅ |
| `floors` | ✅ | ✅ (chỉ HOUSE/VILLA) | ✅ |
| `road_width_m` | ✅ | ✅ | ✅ |
| `frontage_width_m` | ✅ | ✅ | ✅ |
| `street_name` | ✅ | ✅ | ✅ |
| `project_name` | ✅ | ✅ | ✅ |
| `bathrooms` | ❌ không có UI | ✅ nếu user nhập | ⚠️ Flow A thiếu input |
| `house_direction` | ❌ không có UI | ✅ nếu user nhập | ⚠️ Flow A thiếu input |
| `balcony_direction` | ❌ không có UI | ✅ | ⚠️ Flow A thiếu input |
| `access_type` | ✅ | ❌ (cố ý loại) | ⚠️ chỉ Flow A có |

**Kết luận:** payload **tương đương về model feature**. `access_type` không phải model feature
(V1.3 đo: ảnh hưởng **0,00%**). Ba field Flow A thiếu (`bathrooms`, `house_direction`,
`balcony_direction`) là **giới hạn UI của form standalone**, không phải lỗi mapping.

---

## F. Backend results — `FRESH_PASS`

| Suite | Kết quả |
|---|---|
| `ValuationServiceTest` | **12 / 12 PASS** |
| `ValuationHistoryServiceTest` | **6 / 6 PASS** |
| `AdvisorValuationAdapterTest` | **3 / 3 PASS** |
| **Tổng** | **21 / 21 PASS** |

Build: `BUILD SUCCESS`. Không regression.

---

## G. FastAPI results — `FRESH_PASS` (có 1 lỗi pre-existing)

| Chỉ số | Kết quả |
|---|---|
| Tests (loại RAG) | **209 passed, 20 skipped, 84 subtests** |
| Lỗi collection | **2** — `test_rag_area_filter.py`, `test_rag_public_projection.py` |

### G.1. Hai lỗi RAG là **có sẵn trên main** — `VERIFIED`

```
ImportError: cannot import name 'area_spec' from 'app.rag.personalization'
```

Kiểm chứng: `git show bab3d7b:ai-services/app/rag/personalization.py` **không có** `def area_spec`.
File test tồn tại trên `bab3d7b`. → **Pre-existing**, không do WP-01.

---

## H. Frontend results — `FRESH_PASS`

| Suite | Kết quả |
|---|---|
| `node --test tests/*.test.mjs` | **67 / 67 PASS** |
| Production build | **PASS — built in 2,65 s** |

Frontend tests tăng 63 → 67 do 3 test file mới từ cherry-pick
(`advancedValuation` 11, `postValuationInput` 7, `advancedDraftReset` 6).

---

## I. React/Vue runtime audit

**Phân loại: `BUILD_DEPENDENCY` (không phải runtime).**

| Kiểm tra | Kết quả |
|---|---|
| `frontend/index.html` entry | `/src/app/main.jsx` — **React** |
| `vite.config.js` plugin | `@vitejs/plugin-react` — **không** `@vitejs/plugin-vue` |
| `package.json` dependencies | **không có** `vue` |
| Build scripts | `vite build` — không build `vue.ui` |
| Tham chiếu `vue.ui` trong source | **0** |
| Tham chiếu `vue.ui` trong E2E | 2 — chỉ để lấy `node_modules/playwright` |

**Kết luận:** `frontend/vue.ui/` **không được build, không được serve, không được import**.
Nó chỉ còn giá trị vì chứa `node_modules/playwright` mà E2E scripts dùng.

→ Đề xuất cleanup **riêng** (không làm trong WP-01): chuyển `playwright` sang
`frontend/package.json` devDependencies, sau đó xoá `vue.ui/`. **Chưa xoá gì.**
Không chỉnh sửa 2 file `vue.ui` đang có thay đổi từ trước.

---

## J. Migration compatibility

| Kiểm tra | Kết quả |
|---|---|
| WP-01 có migration không? | **KHÔNG** |
| Có đổi schema DB không? | **KHÔNG** |
| Có đổi `ValuationRequest` (DTO, không phải entity)? | **CÓ** — thêm `floors`, `houseSubtype` |
| Ảnh hưởng migration lineage? | **KHÔNG** |
| Flyway history bị đụng? | **KHÔNG** |

---

## K. Database integrity

| Kiểm tra | Kết quả |
|---|---|
| MySQL 3306 truy cập | **KHÔNG** |
| MySQL 3307 | Không dựng instance (Flow B blocked) |
| Service thành viên bị dừng | **KHÔNG** |
| Migration chạy | **KHÔNG** |
| Ghi/xoá dữ liệu | **KHÔNG** |

---

## L. Performance

| Chỉ số | Giá trị |
|---|---|
| FastAPI startup | ~30 s (load V1.3 + V6 artifacts) |
| `/predict` p50 (10 lần, HTTP thật) | **62,7 ms** |
| `/predict` min / max | 41,6 ms / 294,2 ms (max là lần đầu, warm-up) |
| RAM FastAPI (working set) | **214 MB** |
| RAM peak | **613 MB** |
| Frontend build | **2,65 s** |
| Model artifact hash | `3c56b693…` **không đổi** |
| Crash native library | **KHÔNG** |

Mục tiêu < 6 GB → thực tế < 0,7 GB.

---

## M. Final HEAD SHA

| Mục | SHA |
|---|---|
| Base (`origin/main`) | `bab3d7b` |
| Integration HEAD | **`9a75f03`** |
| Branch | `feature/valuation-v1-3-hardening-integration` |
| Worktree | `F:\SmartProp\.worktrees\v13-hardening-integration` |
| Branch hardening gốc | `a7db792` — **không đổi** |

### Files thay đổi vs main (15)

```
ai-services/app/api/valuation.py
ai-services/app/models/xgboost/adapter_v1_3.py
backend/.../prediction/ValuationRequest.java
backend/.../prediction/ValuationService.java
backend/src/test/.../ValuationServiceTest.java
docs/ai/SMARTPROP_AI_VALUATION_EVALUATION_GOVERNANCE.md
frontend/src/features/prediction/AdvancedValuationFields.jsx
frontend/src/features/prediction/PostValuationPanel.jsx
frontend/src/features/prediction/ValuationPanel.jsx
frontend/src/features/prediction/advancedValuation.js
frontend/src/features/prediction/valuation.js
frontend/src/features/property/usePostEditor.js
frontend/tests/advancedDraftReset.test.mjs
frontend/tests/advancedValuation.test.mjs
frontend/tests/postValuationInput.test.mjs
```

---

## N. Remaining blockers

| # | Blocker | Ảnh hưởng |
|---|---|---|
| 1 | **Flow B E2E** — cần Spring Boot + MySQL cô lập + test auth | Posting preview chưa E2E thật |
| 2 | 2 test RAG pre-existing fail trên main | Không liên quan WP-01, nhưng suite không xanh hoàn toàn |
| 3 | E2E script cũ (`valuation.e2e.mjs`) lỗi thời | Cần cập nhật hoặc thay |
| 4 | Flow A thiếu input `bathrooms`/`house_direction`/`balcony_direction` | Giới hạn UI, không phải lỗi mapping |
| 5 | `playwright` nằm trong `vue.ui/node_modules` | Nợ kỹ thuật — cleanup riêng |

---

## O. Readiness for review

```
WP_01_IMPLEMENTATION_COMPLETE
V1_3_REAL_FEATURES_VERIFIED
VALIDATION_PARTIAL
E2E_BLOCKED
```

**Flow A E2E: PASS thật. Flow B E2E: BLOCKED.**

**Không tuyên bố READY_TO_MERGE** vì real E2E của Flow B chưa chạy.

### Đề xuất bước tiếp theo

| # | Việc | Ghi chú |
|---|---|---|
| 1 | Dựng MySQL cô lập (3307 hoặc Docker) để chạy Flow B E2E | Cần phê duyệt |
| 2 | Cập nhật `valuation.e2e.mjs` theo UI hiện tại | Có thể làm ngay |
| 3 | Chuyển `playwright` sang `frontend/package.json` rồi xoá `vue.ui` | Cleanup riêng |
| 4 | Thêm input `bathrooms`/`house_direction`/`balcony_direction` cho Flow A | Mở rộng scope — cần duyệt |
