# SmartProp — WP-02 Comparable Benchmark Report (Phase A, revised)

**Nhãn:** `SYNTHETIC_SURROGATE_BASELINE` + `SYNTHETIC_BENCHMARK`
**Không** phải đánh giá thị trường thật. **Không** tái lập production.
**Base:** `origin/main` @ `a0e3834` · **Phase A:** không sửa production.
**Phiên bản trước** (`bf71ae2`, digest `6920347b30e89f79` / `dffe16e592c1994f`) đã bị
**`SUPERSEDED_BY_CORRECTED_METHODOLOGY`** — xem §9 để biết lỗi phương pháp.

---

## 1. Provenance

- Sinh hoàn toàn bằng `docs/ai/benchmark/wp02_comparable_benchmark.py` (Python 3.11.9, thuần stdlib).
- 28 cohort = 7 quận × 4 loại hình; seed mặc định **20261127**.
- Không dùng DB, không dùng TiniX, không dùng model artifact.

## 2. Baseline fidelity — Java nào được mô phỏng, Java nào không

Surrogate mô phỏng **chính xác** các quy tắc sau (đọc từ `a0e3834`):

| Quy tắc | Nguồn | Surrogate |
|---|---|---|
| `ratioScore = 1 - min((max/min-1)/2, 1)` → 0 tại tỉ lệ 3× | `ComparableSimilarityScorer:91-96` | khớp |
| `locationScore` = 1.00 cùng quận+phường · 0.82 cùng quận · **0.45 quận lân cận** · 0.15 khác | `:98-103` | khớp |
| bedrooms `1 - min(Δ/3, 1)` | `:51` | khớp |
| floors `1 - min(Δ/4, 1)` | `:57` | khớp |
| frontage `1 - min(Δ/10, 1)` (**tuyệt đối**, không phải tỉ lệ) | `:64-65` | khớp |
| type mismatch `total *= 0.5` trước khi chia `weightUsed` | `:77-84` | khớp |
| `score = clamp(total / weightUsed, 0, 1)` | `:86-87` | khớp |
| Band giá `0.4×–2.5×` + `LIMIT` theo từng nguồn | `CandidateRepository:56,98,117` | khớp |
| Cap SmartProp 200 / External 400 / TiniX 12×25=300 | `RankingService:35-40`, repository | khớp |
| `MAX_RESULTS = 5` | `ComparableRankingService:30` | khớp |

**Không mô phỏng (khai báo công khai):**

- SQL thật, `EXPLAIN`, index, thời gian truy vấn — **NOT_RUN**.
- "Price-envelope widening" (`RankingService:89` khi kết quả < limit).
- Plausibility eligibility, source-specific mapping chi tiết, `asOf` path.
- `external_listings` **không có** ward/street/bedrooms/floors/frontage ⇒ external candidates
  chỉ được chấm trên `district/area/price/url` (đúng khả năng thật của nguồn).

⇒ Đây là **surrogate**, không phải `PRODUCTION_BASELINE_REPRODUCED`.

## 3. Định nghĩa metric (đã sửa: entity-level)

| Metric | Công thức | Ghi chú |
|---|---|---|
| `entity_precision@k` | `unique relevant entities trong top-k / k` | mẫu số **k**, không phải số dòng trả về |
| `entity_recall@k` | `unique relevant entities / tổng relevant entities của cohort` | **không** chia `min(k, relevant)` |
| `entity_ndcg@k` | DCG nhị phân, gain **một lần** cho mỗi entity | IDCG từ tối đa k entity relevant |
| `self_match_count` | số dòng trả về có `entity_id == reference.entity_id` | oracle dùng ground truth; realistic dùng identity quan sát được |
| `duplicate_excess_rows` | số dòng trùng entity **sau** lần xuất hiện đầu | |
| `wrong_type_count` / `wrong_locality_count` | số dòng sai loại hình / sai quận | |
| `fill_rate` | `số dòng trả về / (cohort × k)` | |
| `empty_result_cohorts`, `zero_positive_cohorts` | đếm cohort | cohort zero-positive bị loại khỏi recall macro và **báo cáo riêng** |

Alternate listing của một entity relevant **vẫn là relevant** — nó chỉ không cộng gain lần hai.

## 4. Oracle vs realistic deduplication

| Biến thể | Dedupe dùng gì | Được dùng để |
|---|---|---|
| `B_ORACLE` | `entity_id` ground truth | **upper bound** — production không thể làm điều này |
| `B_REALISTIC` | record id theo nguồn, canonical URL, `duplicate_group` namespaced theo nguồn; **T3 chỉ gắn cờ** | con số **khả thi** |
| `C_REALISTIC` | như trên + similarity theo loại hình, không dùng giá | đề xuất |
| `D_REALISTIC` | như C + ngưỡng confidence 0.55 | **EXPERIMENTAL / DEFERRED** |

Ground-truth `entity_id` **không** tham gia retrieval hay scoring của nhánh realistic.

## 5. Kết quả k = 5 (28 cohort, seed 20261127, density `mixed`, digest `510ad28a32582e90`)

| Biến thể | P@5 | R@5 | NDCG | self | dup | type | loc | fill |
|---|---|---|---|---|---|---|---|---|
| A — surrogate baseline | 0.386 | 0.214 | 0.268 | **56** | **30** | 0 | 0 | 1.000 |
| B_ORACLE (upper bound) | 0.800 | 0.444 | 0.661 | **0** | **0** | 0 | 0 | 1.000 |
| B_REALISTIC | 0.550 | 0.306 | 0.414 | **28** | **7** | 0 | 0 | 1.000 |
| C_REALISTIC | 0.550 | 0.306 | 0.412 | 28 | 7 | 0 | 0 | 1.000 |
| D_REALISTIC | 0.550 | 0.306 | 0.412 | 28 | 7 | 0 | 0 | 1.000 |

## 6. Kết quả k = 10 (18 dòng tham số, digest `d42e938116281791`)

| Biến thể | P@10 | R@10 | NDCG | self | dup |
|---|---|---|---|---|---|
| A | 0.311 | 0.345 | 0.282 | 56 | 76 |
| B_ORACLE | 0.414 | 0.460 | 0.469 | 0 | 0 |
| B_REALISTIC | 0.411 | 0.456 | 0.396 | 28 | 50 |
| C_REALISTIC | **0.511** | **0.567** | **0.472** | 28 | 56 |
| D_REALISTIC | 0.511 | 0.567 | 0.472 | 28 | 56 |

**k=10 chỉ là stress kỹ thuật.** Production API trả `MAX_RESULTS = 5`; không được đọc §6 như
hành vi hiện tại của API.

## 7. Candidate-limit & dedupe

| Chỉ số | Giá trị |
|---|---|
| Dedupe precision (realistic, synthetic) | **1.000** |
| Dedupe recall (realistic, synthetic) | **0.250** |
| False-positive merge | **0** |
| False-negative duplicate | **84** |

- Precision 1.0 vì T3 **không tự gộp** — đây là lựa chọn có chủ đích (ưu tiên precision).
- Recall 0.25 vì identity quan sát được chỉ phủ record-id/URL/group; các bản trùng "cùng
  đường + diện tích + giá" **không** bị gộp mà chỉ gắn cờ.
- **Không** tuyên bố precision 0.98 trên dữ liệu thật: đây là nhãn synthetic.
- `density=heavy` (120 filler/cohort) dùng để kiểm tra áp lực cap; filler được xếp theo
  `listing_id` (thứ tự tất định) nên cap thực sự bind.

## 8. Price invariance & buyer budget

| Kiểm tra | A | B | C |
|---|---|---|---|
| VALUATION_SUPPORT, target ×0.5 / ×2.0 | **0/56 giống**, drift **0.0905** | **0/56**, drift 0.0680 | **56/56**, drift **0.0** |

- A và B **không** bất biến theo giá: A còn band + `W_PRICE`; B bỏ band nhưng `baseline_score`
  vẫn có `W_PRICE`.
- **C bất biến tuyệt đối** — giá không còn là feature similarity, không còn band.
- `BUYER_BUDGET_SEARCH`: **0 vi phạm** ngân sách trên toàn bộ cohort.

## 9. Vì sao bản báo cáo trước bị superseded

| Lỗi | Bản cũ | Bản này |
|---|---|---|
| Đơn vị relevance | listing ID | **entity** |
| Recall | chia `min(k, relevant)` | chia **tổng relevant entities** |
| Baseline fidelity | location theo đường, floors/5, frontage theo tỉ lệ, không có type penalty | khớp Java: 1.0/0.82/0.45/0.15, floors/4, frontage tuyệt đối, `×0.5` |
| Self-match | báo 2.9% | **56/140** ở A; realistic còn **28** (oracle 0) |
| Dedupe | oracle trá hình | tách **oracle** vs **realistic** |
| Candidate cap | cap 20 chia sẻ, không bao giờ bind | cap theo nguồn + cohort `heavy` |
| D | "không loại candidate nào" | ở k=10 D loại dòng; vẫn **DEFERRED** (xem §10) |
| Price invariance | không đo | đo, A/B fail, C pass |

## 10. Confidence gate (D) — findings & deferral

- Ở k=5, D **không** lọc dòng nào (fill 1.000); ở k=10 D cũng không lọc trong cấu hình này.
- Review độc lập trước đó ghi nhận: k=10 C trả 280 → D trả 258 (−22 dòng), relevance **không đổi**.
  Trên fixture hiện tại, gate **không** tạo ra giá trị đo được.
- Confidence hiện tính cả `price` presence (completeness) ⇒ một LAND chỉ có location+area
  vẫn đạt ≈0.65 và vượt ngưỡng; thay đổi presence của `price` có thể đẩy 0.58 → 0.54 và loại
  candidate. Đó là **hành vi chưa đủ cơ sở**.
- **Kết luận: D = DEFERRED.** Không đưa vào Phase B. Nhãn HIGH/MEDIUM/LOW/INSUFFICIENT_EVIDENCE
  là **descriptive policy**, không phải calibrated confidence, không phải prediction interval.

## 11. Reproducibility

```bash
python docs/ai/benchmark/wp02_comparable_benchmark.py --k 5
python docs/ai/benchmark/wp02_comparable_benchmark.py --k 10
python docs/ai/benchmark/wp02_comparable_benchmark.py --k 5 --json
python docs/ai/benchmark/wp02_comparable_benchmark.py --assertions
```

- Python **3.11.9**, exit 0. Chạy 2 lần cùng cấu hình cho digest **giống nhau**
  (`510ad28a32582e90` ở k=5) ⇒ deterministic.
- `digest` = SHA256 của **payload metric** (rows + dedupe_prf + price_invariance + buyer_budget
  + k/seed/density). **Không** phải hash toàn bộ dataset fixture.
- `--assertions`: 10 assertion độc lập (xem §12), exit 0.

## 12. Targeted assertions (`--assertions`) — 10/10 PASS

`k<1 rejected` · `duplicate gain counted once` · `duplicate excess row reported` ·
`empty cohort counted` · `zero-positive cohort excluded from recall and counted` ·
`oracle removes exact self-match` · `row count stable under input order change` ·
`VALUATION_SUPPORT price invariance (C, drift 0.0)` · `baseline A is NOT price invariant` ·
`BUYER_BUDGET_SEARCH honours budget_max`.

## 13. Limitations

- Nhãn relevance và nhãn trùng do benchmark tự sinh ⇒ **không** suy ra metric thị trường.
- Chưa có nhãn người thật, chưa chạy trên cohort thật.
- Không đo SQL/index/latency thật; **không** có `EXPLAIN PASS`.
- T3 (suspected cross-source) chỉ gắn cờ, chưa có labeled pairs ⇒ chưa thể đặt ngưỡng auto-merge.
- `asOf`/historical chưa mô phỏng.
