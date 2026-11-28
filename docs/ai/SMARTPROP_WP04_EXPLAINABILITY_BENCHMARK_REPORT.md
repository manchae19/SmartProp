# SmartProp — WP-04 Explainability Benchmark Report (Phase A, final gate)

**Nhãn:** `FRESH_EVIDENCE` (chạy thật trên V1.3) · input **synthetic**.
**Baseline:** `origin/main` @ **`ebfb230`** (PR #46 đã merge) · branch `research/wp04-explainable-ai`.
**Supersedes:** `4ade8a5` (`SUPERSEDED_BY_FINAL_GATE_CORRECTIONS`).

---

## 1. Environment & artifact integrity

| | |
|---|---|
| Python | **3.11.9** · venv `ai-services/.venv` · xgboost **3.4.1** |
| Real-feature flag | mặc định (`SMARTPROP_V1_3_REAL_FEATURES` không set ⇒ true) |
| `model.json` | `3c56b6937902d9f736f9eb0278683f0c5ab8af027f5ea12b1a4072abff840a03` ✅ |
| `calibration.json` | `17632bdf4d578723a5c336b7c7e3aed6021dbb68f38985b763839a763fbfe645` ✅ |
| `feature_schema.json` | `84be275b12b3c426497c00be80eed621d7323ac2a2abcb282752c7a89361e7ea` ✅ |
| `artifact_manifest.json` | `419599ecbefbe24bbbc1754a0224a7c25747ac3a08827d4e14ea62a5e41f2dce` (ghi nhận) |

**Chỉ có 4 artifact** trong thư mục V1.3 — không phải 8. Yêu cầu "8 SHA-256" **không thể đáp ứng**;
đã hash **toàn bộ** 4 file hiện có. Không tải artifact khác.

## 2. Fixture

- **105 case** = 7 district × 3 category × 5 profile
  (`MINIMAL`, `TYPICAL`, `RICH`, `MISSINGNESS`, `UNKNOWN_CATEGORY`).
- **15 extras** có kỳ vọng khai báo: 11 `SUCCESS` (small/large area, NFC/NFD, missing ward,
  ward có tiền tố `Phường 1`, ward trần `1`, ward unknown, street unknown, villa subtype) +
  4 `REJECT` (area 0, area −5, district ngoài vocabulary, LAND+rooms).
- VILLA là `house_subtype` của HOUSE, **không** phải category ⇒ không tạo category giả.

## 3. Production feature-matrix parity (P1 đã sửa)

Bản trước **ghi đè** `ward` trong frame bằng raw payload ward. Production không làm vậy: nó dựng
`input_row` từ **canonical record** (`PredictorV1_3.predict()`), nên ward đã được adapter
strip tiền tố và casefold trước khi vào `transform`.

Đã sửa + assert ở **đúng tầng**:

1. `input_row["ward"] == mapped["ward"]` (không dùng raw payload).
2. Encoded ward đúng sentinel: `None → __MISSING__`, ngoài vocabulary → `__UNKNOWN__`.
3. `predictor.model.predict(frame) == booster margin` (cùng booster ⇒ chứng minh cùng feature
   order và cùng giá trị).
4. Thứ tự cột == `schema["features"]`.

## 4. Kết quả (digest `9eedb3c7c3668f61`)

| Kiểm tra | max | median | p95 |
|---|---|---|---|
| TreeSHAP additivity (rel) | **1.190e-06** | 3.736e-07 | 8.868e-07 |
| Naive `expm1(z)` | **2.108e-10** | 5.128e-11 | 1.368e-10 |
| Calibration reconstruction | **3.612e-06** | 3.612e-06 | 3.612e-06 |
| Top-K remainder (log) | **0.1239** | 0.0346 | 0.0902 |
| **Grouped ≡ total** | **0.0** | 0.0 | 0.0 |

```
cases passed 105 · failed 0 · extras ok 15/15 · self-tests PASS · exit 0
provenance: OBSERVED 420 · DERIVED 945 · MISSING 812 · UNKNOWN_CATEGORY 42 · NOT_APPLICABLE 91
```

## 5. Extras outcome correctness (P1 đã sửa)

| Kỳ vọng | Điều kiện PASS | Ghi chú |
|---|---|---|
| `SUCCESS` | actual `SUCCESS` | bất kỳ `ValueError`/lỗi khác ⇒ FAIL |
| `REJECT` | `REJECTED` **đúng nguồn** (`SCHEMA` hoặc `ADAPTER`) | SUCCESS ⇒ FAIL |
| `UNEXPECTED_ERROR` | **luôn FAIL** | không bao giờ tính là reject hợp lệ |

Đã chạy: `extras ok 15/15`.

## 6. Exit codes

| Tình huống | Exit |
|---|---|
| integrity đúng | 0 |
| artifact thiếu/sai hash | **2** (đã chạy với `--artifacts-dir` không tồn tại) |
| `--self-test` phát hiện lỗi | 1 |
| full benchmark có failure (text hoặc `--json`) | **1** |

`--assertions` = integrity + toàn bộ benchmark + self-tests (không return sớm).

## 7. Determinism

Hai lượt `--json`: digest **`9eedb3c7c3668f61`** = **`9eedb3c7c3668f61`**, exit 0 cả hai.

Digest gồm **per-case**: case_id, price, naive, calibration_factor, margin, base_log,
**toàn bộ 22 φ**, top-K names+order, **group sums**, **provenance từng feature**, **outcome extras**.
Giá trị làm tròn **10 chữ số thập phân** (`DIGEST_DECIMALS = 10`) — đủ để phân biệt sai lệch thật,
đủ ổn định giữa hai lượt chạy. Loại bỏ **chỉ** `total_ms`, `latency_ms` và **đường dẫn môi trường**
(`dir`) — không loại `results`/`failures`.

## 8. Grouped contribution

`aggregate_groups()` cộng **signed** theo `FEATURE_GROUPS`; phát hiện feature thiếu group, trùng,
group thừa. `Σ(group) − Σ(φ) = 0.0` trên 105 case. Không dùng `Σ|φ|`.

## 9. Provenance

Suy từ **ma trận đã transform**; `input_row` (canonical record) là nguồn cho OBSERVED/derived.
`MISSING` 812 · `NOT_APPLICABLE` 91 · `UNKNOWN_CATEGORY` 42 · `OBSERVED` 420 · `DERIVED` 945.
`DEFAULTED` không có nhánh tường minh trong pipeline hiện tại; nếu không xác định an toàn →
`UNVERIFIED`, không mặc định `DERIVED`.

## 10. Limitations

- Synthetic ⇒ không suy ra hành vi thị trường.
- Top-K remainder **đã đo** (max 0.1239 log unit) nhưng **production contract tái lập
  (`other_contribution_log`) chưa triển khai** — đây là khoảng trống F01 của Phase B.
- VILLA không phủ như category.
- Chưa đo cold-start / memory.
- `test_valuation_shap_contract.py`, `probe_shap.py`: **NOT_RUN** (chưa audit xong khả năng
  truy cập dữ liệu của script lịch sử).
- Chỉ 4 artifact có sẵn.

## 11. Reproduce

```bash
P=<repo>/ai-services/.venv/Scripts/python.exe
$P docs/ai/benchmark/wp04_explainability_benchmark.py --artifacts-dir <repo>/ai-services/artifacts/v1_3 --integrity-only
$P docs/ai/benchmark/wp04_explainability_benchmark.py --self-test
$P docs/ai/benchmark/wp04_explainability_benchmark.py --artifacts-dir <repo>/ai-services/artifacts/v1_3 --assertions
$P docs/ai/benchmark/wp04_explainability_benchmark.py --artifacts-dir <repo>/ai-services/artifacts/v1_3 --json
```
