# SmartProp — WP-02 Comparable Correctness: Technical Design (Phase A)

**Trạng thái:** PHASE_A_PROPOSED_DESIGN — chưa có thay đổi production.
**Base:** `origin/main` @ `a0e38349807b23fa071d0779d0a6211be9f3fb99` (PR #44 merged).
**Phụ thuộc:** Phase B chỉ bắt đầu sau khi **PR #46** merge và được phê duyệt.

---

## 1. Kiến trúc hiện tại (đã kiểm chứng trên `a0e3834`)

| Thành phần | Vai trò |
|---|---|
| `ComparableController` (45 LOC) | `POST /api/v1/properties/comparables`, decode request |
| `ComparableRankingService` (366 LOC) | điều phối: eligibility → scoring → ranking → DTO |
| `ComparableCandidateRepository` (170 LOC) | 3 nguồn: SmartProp, external listing, TiniX research |
| `ComparableEligibilityService` (65 LOC) | `notSelf`, `withinEnvelope` |
| `ComparableSimilarityScorer` (139 LOC) | trọng số cố định, chuẩn hoá theo `weightUsed` |
| `ComparableSourceClassifier` (34 LOC) | nhãn nguồn `SMARTPROP` / `EXTERNAL_LISTING` / `TINIX_RESEARCH` |
| `ComparableDtos` (69 LOC) | contract trả về frontend/Advisor |

Luồng: request → repository (SQL có `price BETWEEN … LIMIT`) → eligibility (`notSelf`,
`withinEnvelope`) → scorer → sort → cắt top-N → DTO.

## 2. Findings audit đã xác minh lại trên source hiện tại

| ID | Mức | Nội dung | Trạng thái trên `a0e3834` | Bằng chứng |
|---|---|---|---|---|
| WP02-F01 | P0 | `TINIX_RESEARCH` lọt vào đường public | **CONFIRMED** | `ComparableCandidateRepository:38-56,162` truy vấn `tinix_dataset_records` với `HYBRID_ELIGIBLE_RESEARCH`; `ComparableSourceClassifier` phát nhãn `TINIX_RESEARCH`. PR #46 đang sửa — **chưa merge** |
| WP02-F02 | P1 | Self-match chỉ so ID | **CONFIRMED** | `ComparableEligibilityService:52-54` — `referenceId.equals(candidateId)`; không có entity/source/URL. Repost cùng entity khác listing id ⇒ lọt |
| WP02-F03 | P1 | Price envelope + `W_PRICE` tạo vòng lặp giá | **CONFIRMED** | `ComparableCandidateRepository:56,98,117` `price BETWEEN :min AND :max LIMIT :cap` (dải 0.4×–2.5×); `ComparableSimilarityScorer:24` `W_PRICE = 0.08` |
| WP02-F04 | P1 | Thiếu `asOf`, lọt tin hết hạn | **NOT_VERIFIED trong phạm vi Phase A** (cần đọc thêm `expires_at` ở repository) |
| WP02-F05 | P1 | `bedrooms == null` → `0`; `W_FRONTAGE` chết | **PARTIALLY_RESOLVED**: scorer chỉ tính khi cả hai phía không null (không ép 0), nhưng `W_FRONTAGE` vẫn 0.06 và frontage hiếm khi có dữ liệu |
| WP02-F06 | P1 | `AdvisorEvidencePanel` bỏ giá/diện tích/khu vực | **NOT_VERIFIED** (frontend, ngoài phạm vi source backend của Phase A) |
| WP02-F07 | P2 | Ứng viên thưa thông tin được điểm cao | **CONFIRMED** | `ComparableSimilarityScorer:36,41,47,51-53` — `score = Σ(w·s)/Σ(weightUsed)`; ứng viên chỉ khớp 1 feature với s=1.0 vẫn đạt 1.0 |
| WP02-F08 | P3 | Standalone/Posting chưa có khung Comparable | **CONFIRMED** (không có call site nào trong luồng định giá) |

**Không có finding nào được coi là RESOLVED nếu không kiểm lại source.** F04/F06 ghi
`NOT_VERIFIED` thay vì suy đoán.

## 3. Kiến trúc mục tiêu

```
request ──► Retrieval (SQL: type + district hard filters, NO price band, stable ORDER, cap)
        ──► Entity resolution (4 tầng)
        ──► Eligibility (identity, freshness, envelope theo mục đích)
        ──► Similarity (theo loại hình, missingness-aware)
        ──► Evidence confidence (coverage-aware, tách khỏi similarity)
        ──► Aggregation (median/ppm²/warning chỉ trên cohort hợp lệ)
        ──► DTO (additive fields, backward compatible)
```

## 4. Thiết kế Candidate Retrieval

**Nguyên tắc:** lọc cứng trước, xếp hạng sau, **không dùng giá làm tiêu chí lấy mẫu** cho
valuation-oriented.

```sql
-- valuation-oriented (mặc định cho Comparable)
WHERE property_type = :type            -- hard
  AND district      = :district        -- hard (fallback chỉ khi được phép, xem §4.2)
  AND transaction_type = :tx           -- hard
  AND deleted_at IS NULL
ORDER BY (duplicate/entity key), data_quality_score DESC, ABS(area - :refArea) ASC, id ASC
LIMIT :cap
```

- `ABS(area - :refArea)` thay `ABS(price - :refPrice)` — diện tích là feature vật lý, không phải
  giá trị cần kiểm chứng.
- `ORDER BY` phải **deterministic**: luôn có tie-break bằng `id`.
- Loại đúng property type/district **trước** `LIMIT` để ứng viên sai không chiếm slot.
- `cap` đề xuất 200 sau lọc (hiện 20 sau khi đã lọc bằng dải giá) — cần đo `EXPLAIN` trước khi
  đổi; đây là **đề xuất**, chưa chạy trên DB.

### 4.1. Chỉ mục đề xuất (REQUIRES_SCHEMA_CHANGE — **chờ duyệt**)

Ứng viên: `(property_type, district, transaction_type, deleted_at)`; partial index cho
`age_days`/`expires_at`. **Không tạo index trong Phase A/B đầu tiên** — đo `EXPLAIN` trước.

### 4.2. Geographic fallback (PROPOSED_DESIGN, chưa phải chính sách)

| Bậc | Phạm vi | Điều kiện | Ghi chú trên kết quả |
|---|---|---|---|
| 1 | cùng phường/xã | mặc định | `SAME_WARD` |
| 2 | cùng quận, khác phường | chỉ khi bậc 1 < `MIN_EVIDENCE` | `SAME_DISTRICT` |
| 3 | quận lân cận có khai báo | chỉ khi bậc 2 < `MIN_EVIDENCE`, **không** áp dụng khi người dùng đặt district bắt buộc | `NEIGHBOURING_DISTRICT` |

**Fallback địa giới không phải bằng chứng cùng vị trí** — mọi kết quả mở rộng phải mang cờ và
bị hạ confidence. Không tự map Hòa Vang → Sơn Trà.

## 5. Thiết kế Deduplication (entity resolution)

Tách **listing** (bản ghi tin) khỏi **physical property** (bất động sản thật).

| Tầng | Điều kiện | Hành động | Precision |
|---|---|---|---|
| T1 Exact identity | cùng `property id`, hoặc cùng `(source, sourceRecordId)`, hoặc cùng canonical URL | loại | rất cao |
| T2 Duplicate group | `duplicate_group` đã có và đáng tin trong schema | loại (giữ bản tốt nhất) | cao |
| T3 Cross-source | cùng geometry điểm (≤ 15 m) **và** cùng loại **và** diện tích lệch ≤ 2% **và** (cùng giá ±3% hoặc cùng ảnh) | loại | trung bình-cao, cần ngưỡng |
| T4 Suspected | chỉ trùng đường + diện tích + giá | **giữ, gắn cờ** chứ không gộp | thấp |

- **Ưu tiên precision**: thà lọt một bản trùng còn hơn gộp hai tài sản khác nhau.
- "Cùng đường, cùng diện tích, cùng giá" **không** đủ để gộp (T4).
- Chuẩn hoá tiếng Việt: NFC, casefold, trim, gộp khoảng trắng trước khi so khớp URL/địa chỉ.
- Không xoá/sửa dữ liệu production; chỉ lọc trong bộ kết quả.
- Cần `duplicate_group` + toạ độ đáng tin ⇒ nằm trong **REQUIRES_SCHEMA_CHANGE / REQUIRES_DATA_APPROVAL**.

## 6. Phương pháp Similarity

Hai mục đích, hai policy:

| | Budget-oriented | Valuation-oriented |
|---|---|---|
| Mục tiêu | tìm tài sản trong ngân sách | tìm bằng chứng độc lập |
| Giá | là bộ lọc hợp lệ | **không** dùng làm tiêu chí lấy mẫu, **không** vào similarity |
| Trọng số | phẳng như hiện tại | theo loại hình (§7) |

Đề xuất valuation-oriented: **bỏ `W_PRICE` khỏi similarity**; giá vẫn là dữ liệu bằng chứng
(hiển thị, tính ppm²) nhưng không định hình việc chọn mẫu.

## 7. Type-aware similarity

| Feature | LAND | HOUSE | APARTMENT | VILLA |
|---|---|---|---|---|
| location | 0.45 | 0.34 | 0.36 | 0.32 |
| area | 0.35 | 0.26 | 0.30 | 0.28 |
| bedrooms | — | 0.12 | 0.16 | 0.10 |
| floors | — | 0.10 | — | 0.12 |
| frontage | 0.12 | 0.10 | — | 0.10 |
| road | 0.08 | 0.08 | — | 0.08 |
| project | — | — | 0.18 | — |

Rationale: LAND không có phòng/tầng, nhưng frontage và road quyết định giá trị lô; APARTMENT
không có frontage/road nhưng project là biến phân biệt mạnh nhất. **Không** feature nào được
giả lập khi thiếu dữ liệu.

**Missingness-aware:** `score = Σ(w·s) / Σ(w_available)` **nhân** hệ số phủ
`(0.5 + 0.5 × coverage)`, với `coverage = Σ(w_available) / Σ(w_total)` — chặn F07 (ứng viên chỉ
khớp 1 feature không thể đạt điểm tối đa).

## 8. Missing-data policy

| Trạng thái | Xử lý |
|---|---|
| `null` | missing — **không** bằng 0, **không** bằng "đường nhỏ" |
| Feature thiếu | không đóng góp similarity, chỉ giảm coverage/confidence |
| Toàn bộ feature thiếu trừ location | không đủ bằng chứng → `INSUFFICIENT_EVIDENCE` |
| HOUSE/VILLA | **không** tự suy từ giá cao hay diện tích lớn |

## 9. Evidence Confidence (tách khỏi similarity)

```
confidence = 0.30·identity + 0.20·location_precision + 0.15·same_street
           + 0.20·feature_completeness + 0.10·verified + 0.05·freshness
```

Nhãn: `HIGH ≥ 0.75`, `MEDIUM ≥ 0.55`, `LOW ≥ 0.35`, còn lại `INSUFFICIENT_EVIDENCE`.
**Đây là policy đề xuất, chưa calibration.** Không gọi là xác suất, không gọi là khoảng tin cậy.

## 10. Ranh giới Research Access (bảo toàn PR #46)

- Public Comparable: **chỉ** `SMARTPROP` + `EXTERNAL_LISTING` đủ điều kiện. Không truy vấn
  TiniX, không trả metadata TiniX, không fallback TiniX.
- Research Comparable: explicit opt-in, ADMIN ACTIVE, session hợp lệ, cache tách biệt.
- Thiết kế này **không** mở rộng quyền research; benchmark Phase A **không** dùng dữ liệu TiniX
  và không dùng sealed holdout.
- **Ràng buộc Phase B:** phải rebase/đọc lại PR #46 trước khi implement; nếu PR #46 đổi contract
  authorization, WP-02 tuân theo PR #46.

## 11. Tương thích API

- Endpoint giữ nguyên `POST /api/v1/properties/comparables`.
- Thêm **field additive**: `evidenceConfidence`, `confidenceLabel`, `scopeLevel`
  (`SAME_WARD|SAME_DISTRICT|NEIGHBOURING_DISTRICT`), `dedupeApplied`, `excludedReasons`.
- Không đổi ngữ nghĩa field cũ; không xoá field.
- Frontend/Advisor đọc thêm field, không phá vỡ consumer cũ.

## 12. Rủi ro & giới hạn

| Rủi ro | Giảm thiểu |
|---|---|
| Cohort nhỏ ở quận mới → ít kết quả | trả `INSUFFICIENT_EVIDENCE` + giải thích, **không** bịa số |
| Dedupe T3 gộp nhầm tài sản khác | ngưỡng chặt, T4 chỉ gắn cờ |
| Tăng `cap` gây chậm | `EXPLAIN` trước, index có điều kiện |
| Trùng lặp với PR #46 | Phase B chỉ sau merge + đọc lại diff |
| Benchmark synthetic không đại diện thị trường | nhãn `SYNTHETIC_BENCHMARK`, không suy ra chất lượng thật |
| Nhãn relevance do ta định nghĩa | định nghĩa hiện tại **loại giá** khỏi nhãn để tránh vòng lặp (xem benchmark report) |

## 13. Acceptance criteria (Phase B)

1. Self-match leakage = 0 trên mọi nguồn public (đo bằng test, không suy đoán).
2. Không có ứng viên sai `property_type`/`district` trong top-K.
3. Dedupe precision ≥ 0.98 trên fixture synthetic; recall ghi nhận riêng.
4. `W_PRICE` không còn trong valuation similarity; budget mode vẫn có lọc giá riêng.
5. Không hồi quy endpoint contract; DTO additive.
6. Không hồi quy research access (test PR #46 vẫn xanh).
7. Không migration trong bước 1–3; migration chỉ khi được duyệt riêng.

---

## 14. Bổ sung sau review methodology (Phase A revised)

### 14.1. Baseline fidelity — surrogate, không phải production

Surrogate mô phỏng đúng `ComparableSimilarityScorer` (location 1.00/0.82/**0.45**/0.15,
`ratioScore` về 0 tại 3×, floors `/4`, frontage tuyệt đối `/10`, type mismatch `×0.5`) và cap
theo nguồn (200/400/12×25, `MAX_RESULTS=5`). **Không** mô phỏng SQL/index/latency,
price-envelope widening, `asOf` path. Nhãn bắt buộc: `SYNTHETIC_SURROGATE_BASELINE`.

### 14.2. Identity: ba lớp, không trộn

| Lớp | Dùng ở đâu |
|---|---|
| Ground-truth entity | **chỉ** đánh giá (`B_ORACLE`) |
| Observable identity | record id theo nguồn, canonical URL, `duplicate_group` namespaced theo source |
| Predicted duplicate grouping | kết quả dedupe thật (T1/T2 merge, T3 flag-only) |

`external_listings` không có ward/street/bedrooms/floors/frontage ⇒ không được chấm như
SmartProp. `duplicate_group` **không** chia sẻ namespace giữa hai nguồn.

### 14.3. Comparable purpose — bắt buộc explicit

`VALUATION_SUPPORT` · `BUYER_BUDGET_SEARCH` · `SIMILAR_LISTING`. Với `VALUATION_SUPPORT`:
target price **không** được dùng cho band, nearest-price, price similarity, fallback hay nhãn
relevance. Lưu ý `ComparableRankingService` có propertyId path tự load giá từ DB ⇒ phải trace
**toàn bộ** caller; xoá `priceVnd` khỏi request là chưa đủ.

### 14.4. Feature availability (verified, không suy đoán)

| Feature | SMARTPROP | EXTERNAL_LISTING |
|---|---|---|
| district | ✅ projected | ✅ projected |
| ward | ✅ | ❌ không có cột |
| area | ✅ | ✅ |
| asking price | ✅ | ✅ |
| bedrooms | ✅ | ❌ |
| floors | ✅ (cột `floor` dạng string, chưa project) | ❌ |
| frontage / road width | ❌ không có cột tách rời | ❌ |
| project_id | ✅ nullable, chưa project | ❌ |
| detail URL / duplicate group | — | ✅ nếu có |

⇒ Trọng số đề xuất **không** dùng frontage/road (chỉ TiniX mới có, ngoài phạm vi public).

### 14.5. Missingness — sáu trạng thái phải phân biệt

Không áp dụng cho loại hình · source không hỗ trợ · candidate thiếu · reference chưa cung cấp ·
giá trị không hợp lệ · giá trị thật bằng 0. LAND **không** bị phạt vì thiếu bedrooms.
Coverage shrinkage `0.5 + 0.5×coverage` chỉ là **proposal**, cần sensitivity test ở Phase B.

### 14.6. Expiry & locality

LIVE: `PUBLISHED` **và** `(expires_at IS NULL OR expires_at > UTC_TIMESTAMP(6))` **và**
`deleted_at IS NULL` **và** transaction type khớp. `expires_at NULL` = không có hạn (theo schema)
— ghi rõ, không tự suy diễn. HISTORICAL_AS_OF: **DEFERRED**. Locality: `SAME_WARD` →
`SAME_DISTRICT` → `NEIGHBOURING_DISTRICT`, chỉ fallback khi được phép, luôn mang cờ và hạ
confidence; strict locality **không** mở rộng; không hardcode Hòa Vang → Sơn Trà.

### 14.7. Double-check trên `bookings`/`price` presence

Presence của asking price chỉ quyết định candidate có dùng được cho **thống kê giá** hay không;
nó **không** quyết định similarity vật lý và **không** được tham gia confidence gate (lý do
D bị DEFERRED).

### 14.8. Security contracts (Phase 0, từ PR #46)

Public/SAFE: không truy vấn TiniX, không dòng TiniX, không count research, không fallback,
public/research cache tách biệt, giữ role hiện có (BROKER/ADMIN theo contract đã duyệt — public
mode **không** đồng nghĩa anonymous). Research: explicit opt-in + ADMIN ACTIVE + session sống +
server flag + source eligibility + no-store. Advisor SAFE không được fallback TiniX.

### 14.9. Cơ chế bất biến giá (bắt buộc) — kết quả benchmark

Benchmark chứng minh: bỏ **band giá** (retrieval) **không đủ** để `VALUATION_SUPPORT` bất biến
theo target price, vì `W_PRICE` vẫn nằm trong similarity (ids 0/56 giống khi ×0.5/×2.0).
Bỏ **cả `W_PRICE`** cho kết quả bất biến tuyệt đối (pool/ids/scores 56/56, drift 0.0).

⇒ `VALUATION_SUPPORT` **bắt buộc** loại target price khỏi: band, nearest-price, price
similarity, fallback và nhãn relevance. Loại hình-aware weights (C) là tối ưu **tăng dần**,
không phải điều kiện để đạt correctness này.
