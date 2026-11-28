# SmartProp — WP-02 Comparable Implementation Plan (Phase A)

**Trạng thái:** PLANNED — chưa thực hiện bước nào.
**Điều kiện Phase B:** PR #46 đã merge + design được duyệt + người dùng cho phép.

---

## Phân loại công việc

| Mã | Hạng mục | Loại |
|---|---|---|
| S1 | Self-match theo entity/identity (T1) | **IMPLEMENT_WITHOUT_MIGRATION** |
| S2 | Dedupe theo `duplicate_group` (T2) | **IMPLEMENT_WITHOUT_MIGRATION** |
| S3 | Retrieval: hard filter type + district trước LIMIT, bỏ dải giá, ORDER BY ổn định | **IMPLEMENT_WITHOUT_MIGRATION** |
| S4 | Similarity theo loại hình + missingness coverage | **IMPLEMENT_WITHOUT_MIGRATION** |
| S5 | Tách budget-oriented và valuation-oriented | **IMPLEMENT_WITHOUT_MIGRATION** |
| S6 | Evidence confidence + DTO additive | **IMPLEMENT_WITHOUT_MIGRATION** |
| S7 | Aggregation chỉ trên cohort hợp lệ + `INSUFFICIENT_EVIDENCE` | **IMPLEMENT_WITHOUT_MIGRATION** |
| S8 | Dedupe T3 (cần toạ độ + ngưỡng) | **REQUIRES_DATA_APPROVAL** |
| S9 | Index `(property_type, district, transaction_type, deleted_at)` | **REQUIRES_SCHEMA_CHANGE** |
| S10 | Chuẩn hoá `duplicate_group` toàn bộ dữ liệu | **REQUIRES_DATA_APPROVAL** |
| S11 | Tích hợp Comparable vào luồng định giá (F08) | **OPTIONAL_FUTURE_WORK** |
| S12 | Rebase + đọc lại PR #46 trước khi code | **REQUIRES_PR46_MERGE** |

## Thứ tự thực hiện (mỗi bước kiểm thử độc lập)

**Bước 0 — Đồng bộ (REQUIRES_PR46_MERGE)**
`git fetch` → sync main → đọc lại diff Comparable/Advisor của PR #46 → xác nhận contract
authorization → chạy test hiện có làm baseline xanh.

**Bước 1 — Self-match + dedupe T1/T2 (S1, S2)**
Thêm `notSelf` theo identity (id, source+sourceRecordId, canonical URL, entity).
Giữ nguyên retrieval. **Test:** `ComparableEligibilityServiceTest` mở rộng; regression
`ComparableRankingLiveIT`.

**Bước 2 — Retrieval sửa (S3)**
Bỏ dải giá khỏi valuation path; hard filter trước LIMIT; ORDER BY deterministic.
**Test:** `ComparableRecallIT` (cold-start, sparse, empty cohort), kiểm tra không có
`type_error`/`locality_error`.

**Bước 3 — Similarity theo loại hình (S4, S5)**
Bảng trọng số §7 của design; bỏ `W_PRICE` khỏi valuation; giữ budget mode riêng.
**Test:** `ComparableSimilarityScorerTest` (test từng loại hình, missingness), benchmark
`--k 5/10` phải không giảm P@k so với Bước 2.

**Bước 4 — Evidence confidence + DTO (S6)**
Additive fields; **không** đổi field cũ. **Test:** contract test JSON, frontend smoke.

**Bước 5 — Aggregation & trạng thái thiếu bằng chứng (S7)**
Median/ppm² chỉ trên cohort hợp lệ; cohort nhỏ trả `INSUFFICIENT_EVIDENCE`.

**Bước 6 — Đo lại & quyết định**
Chạy benchmark synthetic, thêm test thật nếu được cấp dữ liệu. Chỉ khi đó mới xét S8–S10.

## Acceptance criteria (Phase B)

1. Self-match leakage = 0 (test đo được, không suy đoán).
2. Không còn ứng viên sai type/district trong top-K.
3. P@k và NDCG@k trên benchmark synthetic **không thấp hơn** baseline A.
4. Không hồi quy contract API; DTO additive.
5. Không hồi quy research access (test PR #46 vẫn xanh).
6. Không migration ở bước 1–5.
7. Không nới quyền TiniX.

## Rủi ro & điểm dừng

- Nếu PR #46 đổi contract Comparable ⇒ **dừng**, cập nhật design trước khi code.
- Nếu `EXPLAIN` cho thấy cần index ⇒ tách PR riêng, **không** gộp vào WP-02.
- Nếu benchmark thật (khi có dữ liệu được phép) cho kết quả khác synthetic ⇒ ưu tiên dữ liệu thật.

---

## 17. Phase B stages (revised)

| Stage | Nội dung | Phân loại |
|---|---|---|
| B1 | PR #46 merged → sync main → đọc lại diff Comparable/Advisor → xác nhận research policy | **REQUIRES_PR46_MERGE** |
| B2 | Retrieval & eligibility: strict type, locality semantics, source eligibility, live expiry, stable ordering, cap correctness | IMPLEMENT_WITHOUT_MIGRATION |
| B3 | Identity: exact self-match, source-qualified ids, trusted source-local duplicate ids, canonical URL, **T3 flag-only** | IMPLEMENT_WITHOUT_MIGRATION |
| B4 | Purpose separation: BUYER_BUDGET / SIMILAR_LISTING / VALUATION_SUPPORT; trace mọi caller kể cả propertyId path | IMPLEMENT_WITHOUT_MIGRATION |
| B5 | Type-aware scoring trên feature **đã xác minh**; missingness policy; breakdown giải thích được | IMPLEMENT_WITHOUT_MIGRATION |
| B6 | Evidence presentation: count đã dedupe, thống kê asking-price, sample limitations, source provenance, insufficient evidence, DTO additive | IMPLEMENT_WITHOUT_MIGRATION |
| B7 | Integration: direct Comparable, property detail, valuation flow, posting preview, Advisor, FE liên quan | IMPLEMENT_WITHOUT_MIGRATION |
| B8 | Regression: backend unit, query tests, FE contract, Advisor compat, public/research isolation | IMPLEMENT_WITHOUT_MIGRATION |

**Deferred:** confidence gate D (**DEFERRED**, không phải yêu cầu Phase B), HISTORICAL_AS_OF
(**DEFERRED**), T3 auto-merge (**REQUIRES_DATA_APPROVAL**), index mới
(**REQUIRES_SCHEMA_CHANGE**, tách PR riêng), migration (**không** thực hiện trong WP-02).
Segmentation: nếu C chưa đủ evidence, triển khai **B trước**, C theo stage tăng dần.

## 18. Acceptance invariants (evidence-based, không target tuỳ ý)

1. Exact self-match bị loại khi identity xác minh được.
2. Known duplicate không xuất hiện nhiều lần khi identifier hỗ trợ xác định cùng thực thể.
3. Không auto-merge nghi trùng chưa đủ bằng chứng.
4. Strict property-type không trả sai loại hình.
5. Strict locality không mở rộng trái yêu cầu.
6. `VALUATION_SUPPORT` bất biến theo target price.
7. `BUYER_BUDGET_SEARCH` giữ ngân sách đúng contract.
8. Missing feature không bị biến thành 0 hoặc giá trị giả.
9. Tin hết hạn không tham gia evidence LIVE.
10. Ranking ổn định với cùng input.
11. Public Comparable không truy vấn/fallback TiniX.
12. Insufficient evidence được trình bày minh bạch.

**Không cam kết:** zero duplicate toàn thị trường · 100% entity resolution · metric synthetic
bằng metric production · SQL performance · calibrated confidence · cải thiện độ chính xác V1.3.

---

## 19. Reconciliation với revised design (thay thế các mục mâu thuẫn)

Các mục dưới đây **supersede** phần cũ nếu có xung đột:

| Yêu cầu cũ | Trạng thái mới |
|---|---|
| "Self-match leakage = 0" tuyệt đối | **Chỉ khi identity xác minh được.** Realistic còn residual (repost không có identity) và residual đó phải được báo cáo, không bị ép về 0 |
| Approach C phải tăng Precision@5 | **Không bắt buộc.** Giá trị chính của C là **price independence**; P@5 ngang B ở k=5 và nhỉnh ở k=10 (0.514 vs 0.511) |
| D confidence gate trong Phase B | **DEFERRED** — không phải yêu cầu Phase B |
| HISTORICAL_AS_OF | **DEFERRED** |
| T3 auto-merge | **REQUIRES_DATA_APPROVAL** — chỉ flag-only cho tới khi có labeled pairs |
| Rebase/force push để đồng bộ | **Không bắt buộc** — sync thường, không force push |
| Bỏ band giá là đủ cho valuation support | **Không đủ** — phải bỏ cả `W_PRICE` khỏi similarity (biến thể **BF**) |

### Phase B = correctness-first + incremental scoring

**Bắt buộc (correctness):**
1. Strict type/locality/source eligibility, live expiry, deterministic ordering, cap trước khi
   xếp hạng.
2. Identity: exact self-match, source-qualified id, canonical URL, group namespaced theo nguồn;
   **T3 flag-only**.
3. `VALUATION_SUPPORT`: **không** target-relative band, **không** `W_PRICE`; trace mọi caller
   kể cả nhánh `propertyId` tự load giá.
4. `BUYER_BUDGET_SEARCH` giữ nguyên budget.

**Incremental (scoring):**
5. Type-aware weights trên feature đã xác minh (không frontage/road cho public).
6. Coverage shrinkage — phải sensitivity-test trước khi chốt.
7. Evidence presentation + DTO additive (count đã dedupe, asking-price stats, limitations).

**Deferred / cần phê duyệt riêng:** D, historical as-of, T3 auto-merge, index mới
(`REQUIRES_SCHEMA_CHANGE`), mọi migration (**không** làm trong WP-02).
