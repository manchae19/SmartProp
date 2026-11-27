# SmartProp — WP-02 Comparable Benchmark Report (Phase A, corrected assertions)

**Nhãn:** `SYNTHETIC_SURROGATE_BASELINE` + `SYNTHETIC_BENCHMARK`
Không phải đánh giá thị trường thật, không tái lập production.
**Base:** `origin/main` @ `a0e3834` · **Phase A:** không sửa production.
**Lịch sử:** `bf71ae2` (digest `6920347b30e89f79` / `dffe16e592c1994f`) và
`f7c0624` (digest `510ad28a32582e90` / `d42e938116281791`) đều
**`SUPERSEDED_BY_CORRECTED_METHODOLOGY`**.

---

## 1. Provenance

- Sinh bằng `docs/ai/benchmark/wp02_comparable_benchmark.py` (Python **3.11.9**, stdlib).
- 28 cohort = 7 quận × 4 loại hình; seed **20261127**; density `mixed`.
- Không DB, không TiniX, không model artifact.

## 2. Baseline fidelity

Surrogate mô phỏng đúng `a0e3834`: `ratioScore` → 0 tại 3× · location **1.00/0.82/0.45/0.15** ·
bedrooms `/3` · floors **`/4`** · frontage **tuyệt đối `/10`** · type mismatch **`×0.5`** ·
`clamp(total/weightUsed)` · band `0.4×–2.5×` · cap **200 / 400** (`12×25` cho TiniX) ·
`MAX_RESULTS = 5`.

**Không mô phỏng:** SQL/`EXPLAIN`/index/latency (**NOT_RUN**), price-envelope widening,
`asOf` path, plausibility eligibility. `external_listings` không có ward/bedrooms/floors/
frontage nên external chỉ chấm trên `district/area/url`.

## 3. Phương án đo

| Biến thể | Nội dung |
|---|---|
| **A** | surrogate baseline: band giá theo nguồn + cap + `notSelf` id-only + trọng số phẳng (có `W_PRICE`) |
| **B_ORACLE** | retrieval sửa + dedupe bằng **ground-truth entity** → **upper bound** |
| **B_REALISTIC** | retrieval sửa + dedupe **identity quan sát được** + trọng số phẳng (vẫn có `W_PRICE`) |
| **BF_REALISTIC** | B_REALISTIC **bỏ `W_PRICE`** khỏi similarity (correctness-first cho VALUATION_SUPPORT) |
| **C_REALISTIC** | retrieval sửa + **type-aware**, không giá, coverage shrinkage |
| **D_REALISTIC** | C + ngưỡng confidence 0.55 — **EXPERIMENTAL / DEFERRED** |

## 4. Metric (entity-level, mẫu số ghi rõ)

| Metric | Công thức |
|---|---|
| `entity_precision@k` | unique relevant entities / **k** |
| `entity_recall@k` | unique relevant entities / **tổng relevant entities của cohort** |
| `entity_ndcg@k` | DCG nhị phân, gain **một lần**/entity; IDCG từ tối đa k entity relevant |
| `self_match_count` | dòng trả về có `entity_id == reference` |
| `duplicate_excess_rows` | dòng trùng entity sau lần xuất hiện đầu |
| cohort `zero_positive` | loại khỏi recall macro và **báo cáo riêng** |

## 5. Kết quả k = 5 (28 cohort, digest `bdf107ddaf34ba57`)

| Biến thể | P@5 | R@5 | NDCG | self | dup | type | fill |
|---|---|---|---|---|---|---|---|
| A | 0.386 | 0.214 | 0.268 | **56** | **30** | 0 | 1.000 |
| B_ORACLE | 0.800 | 0.444 | 0.661 | 0 | 0 | 0 | 1.000 |
| B_REALISTIC | 0.550 | 0.306 | 0.414 | **28** | 7 | 0 | 1.000 |
| **BF_REALISTIC** | 0.550 | 0.306 | 0.412 | 28 | 7 | 0 | 1.000 |
| C_REALISTIC | 0.550 | 0.306 | 0.412 | 28 | 7 | 0 | 1.000 |
| D_REALISTIC | 0.550 | 0.306 | 0.412 | 28 | 7 | 0 | 1.000 |

## 6. Kết quả k = 10 (stress kỹ thuật; API thật trả tối đa 5)

| Biến thể | P@10 | R@10 | NDCG | self | dup |
|---|---|---|---|---|---|
| A | 0.311 | 0.345 | 0.282 | 56 | 76 |
| B_ORACLE | 0.414 | 0.460 | 0.469 | 0 | 0 |
| B_REALISTIC | 0.411 | 0.456 | 0.396 | 28 | 50 |
| **BF_REALISTIC** | **0.514** | **0.571** | **0.474** | 28 | 56 |
| C_REALISTIC | 0.511 | 0.567 | 0.472 | 28 | 56 |
| D_REALISTIC | 0.511 | 0.567 | 0.472 | 28 | 56 |

## 7. Candidate-cap pressure — cap **thực sự** bind

| Nguồn | Trước cap | Cap | Bind? |
|---|---|---|---|
| SMARTPROP | **266** | 200 | ✅ |
| EXTERNAL_LISTING | **460** | 400 | ✅ |
| Sau cap (tổng) | **600** | — | |
| Relevant bị mất **tại cap** | **6** | — | ✅ |

Relevant rows được đặt id `Z*` để sắp **sau** filler theo thứ tự tất định, nên chúng thực sự bị
cap cắt — đây là bằng chứng cap pressure, không chỉ là tên `density=heavy`.

## 8. Pair-level dedupe metrics

`dedupe_realistic` trả **cặp merge** `(giữ, bỏ)`; mỗi cặp được đối chiếu ground-truth identity:

| Chỉ số | Giá trị |
|---|---|
| True positive | **2** |
| False positive (gộp nhầm entity khác) | **0** |
| False negative (trùng thật nhưng không gộp được) | **1** |
| Precision | **1.000** |
| Recall | **0.667** |

Fixtures kiểm tra: trùng qua record-id tin cậy · hai entity khác nhau nhưng cùng diện tích/giá ·
source-id collision (42 ở hai nguồn) · thiếu source identity · thiếu URL · cùng nhãn group nhưng
khác namespace · trùng URL chuẩn hoá · **repost cùng entity nhưng URL mới → không gộp được (fn)**.

Không tạo identity key từ giá trị rỗng. T3 vẫn **flag-only** ⇒ không merge nghi trùng.

## 9. Self-match — assertion không vacuous

Fixture có đủ: bản ghi **chính xác** của reference (cùng record-id + URL) · **repost** cùng entity
nhưng identity khác · một comparable **khác entity**. Kết quả:

| Kiểm tra | Kết quả |
|---|---|
| Exact observable self-match bị loại (realistic) | ✅ |
| Oracle loại **mọi** entity của reference (kể cả repost) | ✅ |
| Realistic **giữ** repost không xác minh được | ✅ (đúng, và là residual) |
| Không loại nhầm comparable khác entity | ✅ |

**Residual self-match trung thực: 28 dòng** (1 repost/cohort) ở nhánh realistic; oracle = 0.
Không tuyên bố realistic đạt zero physical self-match khi identity evidence không đủ.

## 10. Price invariance — VALUATION_SUPPORT

So sánh **toàn pipeline** (pool sau cap, pool sau dedupe, thứ tự top-K, và điểm) ở target ×0.5/×2.0:

| Biến thể | pool giống | ids giống | scores giống | drift |
|---|---|---|---|---|
| A | 17/56 | 2/56 | 0/56 | 0.0905 |
| B_REALISTIC | 56/56 | **0/56** | 0/56 | 0.0554 |
| **BF_REALISTIC** | 56/56 | **56/56** | **56/56** | **0.0** |
| **C_REALISTIC** | 56/56 | 56/56 | 56/56 | 0.0 |
| D_REALISTIC | 56/56 | 56/56 | 56/56 | 0.0 |

**Kết luận quan trọng:** bỏ **band giá** (B) là chưa đủ — `W_PRICE` vẫn làm ranking phụ thuộc
target price. **Phải bỏ `W_PRICE` khỏi VALUATION_SUPPORT** (BF) mới đạt bất biến. Vì vậy:
**BF là yêu cầu correctness bắt buộc; C (type-aware) là incremental.**

## 11. Buyer-budget

`BUYER_BUDGET_SEARCH` với `budget_max = 0.9 × target`: **0 vi phạm** trên toàn bộ cohort.
Chính sách ngân sách giữ nguyên, không bị ảnh hưởng bởi thay đổi của VALUATION_SUPPORT.

## 12. Confidence gate (D) — DEFERRED

- Không tạo khác biệt đo được trên fixture hiện tại (k=5 và k=10 đều bằng C).
- Review độc lập ghi nhận: k=10 C 280 dòng → D 258 dòng, relevance **không đổi**.
- Confidence bị `price` presence chi phối (0.58 → 0.54 có thể loại candidate); LAND chỉ có
  location+area vẫn đạt ≈0.65 > ngưỡng.
- **D = DEFERRED**, không nằm trong Phase B. Nhãn HIGH/MEDIUM/LOW/INSUFFICIENT_EVIDENCE là
  descriptive policy, không phải calibrated confidence.

## 13. Assertions (`--assertions`) — 16/16 PASS

`k<1 rejected` · `cap binds 266/460` · `post-cap respects caps` · `relevant lost at cap = 6` ·
`no false merge at pair level` · `trusted identifiers merge` · `exact observable self removed` ·
`distinct comparable kept` · `oracle removes all reference entities` · `realistic keeps repost` ·
`ranking IDs+scores stable under reversed input` · `BF price invariance drift 0.0` ·
`C price invariance drift 0.0` · `B alone NOT invariant` · `budget violations = 0`.

## 14. Reproducibility

```bash
python docs/ai/benchmark/wp02_comparable_benchmark.py --k 5
python docs/ai/benchmark/wp02_comparable_benchmark.py --k 10
python docs/ai/benchmark/wp02_comparable_benchmark.py --k 5 --json
python docs/ai/benchmark/wp02_comparable_benchmark.py --assertions
```

Python 3.11.9 · exit 0 · hai lần chạy cùng cấu hình cho digest **giống nhau**
(`bdf107ddaf34ba57` tại k=5) ⇒ deterministic.
`digest` = SHA256 của **payload metric** (rows + dedupe pairs + invariance + budget + cap probe
+ k/seed/density). **Không** phải hash dataset.

## 15. Limitations

- Nhãn relevance và nhãn trùng do fixture tự sinh ⇒ **không** suy ra metric thị trường.
- Chưa có labeled pairs thật ⇒ chưa đặt ngưỡng auto-merge T3.
- Không đo SQL/index/latency; **không** có `EXPLAIN PASS`.
- `asOf`/historical chưa mô phỏng; chưa chạy trên dữ liệu thật.
