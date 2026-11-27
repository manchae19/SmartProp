# SmartProp — WP-04 Explainability Benchmark Report (Phase A, reviewed)

**Nhãn:** `FRESH_EVIDENCE` (chạy thật trên model V1.3) · input **synthetic**.
**Base:** `origin/main` @ `a0e3834` · **Branch:** `research/wp04-explainable-ai`
**Phiên bản trước** (`3e1ff0c`) — `SUPERSEDED_BY_REVIEW_CORRECTIONS`.

---

## 1. Môi trường & integrity

| | |
|---|---|
| Runtime SHA (evidence) | worktree `research/wp04-explainable-ai` @ `3e1ff0c` (đo trước bản sửa); bản sửa là commit mới trên cùng branch |
| Python | **3.11.9** · venv `ai-services/.venv` |
| xgboost | **3.4.1** · numpy/pandas theo venv project |
| real-feature-input flag | mặc định `SMARTPROP_V1_3_REAL_FEATURES` = true (không set biến) |
| `model.json` | `3c56b693…ff840a03` ✅ |
| `calibration.json` | `17632bdf…3fbfe645` ✅ |
| `feature_schema.json` | `84be275b…9361e7ea` ✅ |
| `artifact_manifest.json` | `419599ec…41f2dce` (ghi nhận; không pinned) |

**Bắt buộc dùng venv của project.** Chạy bằng venv khác (xgboost build khác) gây
`XGBoostError: Found a category not in the training set ... column 17` — lỗi môi trường,
không phải lỗi production.

## 2. Fixture

- 7 district (vocabulary thật) × 3 category (`HOUSE`, `LAND`, `APARTMENT`) × **5 profile**
  (`MINIMAL`, `TYPICAL`, `RICH`, `MISSINGNESS`, `UNKNOWN_CATEGORY`) = **105 case**.
- **8 extras**, mỗi cái khai báo kỳ vọng: 6 `SUCCESS` (small/large area, NFC/NFD district,
  missing ward, missing street) + 2 `REJECT` (area = 0, district ngoài vocabulary).
  Extras được validate qua **chính `ValuationRequest`** (contract API) rồi mới gọi predictor.
- **VILLA không phải category** trong `normalized_type` (villa là `house_subtype` của HOUSE)
  ⇒ không tạo category giả.
- Không database, không research dataset, không holdout.

## 3. Kết quả (105 case, digest `0fe2bf2375caf32a`)

| Kiểm tra | max | median | p95 |
|---|---|---|---|
| TreeSHAP additivity (tương đối) | **1.190e-06** | 3.736e-07 | 8.868e-07 |
| Naive `expm1(z)` reconstruction | **2.108e-10** | 5.128e-11 | 1.368e-10 |
| Calibration reconstruction | **3.612e-06** | 3.612e-06 | 3.612e-06 |
| Top-K + remainder (log unit) | **0.1239** | 0.0346 | 0.0902 |
| **Grouped ≡ total** | **0.0** | 0.0 | 0.0 |

```
cases passed 105 · failed 0 · extras ok 8/8 · self-tests PASS · exit 0
provenance: OBSERVED 420 · DERIVED 945 · MISSING 812 · UNKNOWN_CATEGORY 42 · NOT_APPLICABLE 91
```

## 4. Exit codes

| Lệnh | Exit |
|---|---|
| `--integrity-only` (hash đúng) | 0 |
| hash sai | 2 |
| `--self-test` | 0 (PASS) / 1 (FAIL) |
| full benchmark, mọi invariant đạt | 0 |
| có bất kỳ failure | **1** (cả text **và** `--json`) |

`--assertions` **không return sớm**: nó chạy integrity + toàn bộ mathematical benchmark +
failure-path self-tests, đúng như trên.

## 5. Failure-path self-tests (chứng minh benchmark biết FAIL)

`--self-test` kiểm các kiểm-tra có thể phát hiện lỗi thật:

- feature **không có group** → phát hiện
- feature **trùng** trong vector → phát hiện
- group entry **không tồn tại** trong vector → phát hiện
- **tổng group sai** → phát hiện (sai 1.0 so với kỳ vọng)
- **matrix rỗng** → phát hiện (`require_cases`)
- additivity vượt ngưỡng (1e-4 > 1e-5) → phát hiện
- classifier provenance: `UNKNOWN_CATEGORY` / `MISSING` / `NOT_APPLICABLE` / `OBSERVED`
  đều phân loại đúng

`self-tests: PASS (0 lỗi)`.

## 6. Determinism

Hai lần chạy cùng cấu hình: digest **giống nhau** (`0fe2bf2375caf32a`).

Digest bao gồm **per-case**: `case_id`, `price`, `naive`, `calibration_factor`, `margin`,
`base_log`, **toàn bộ 22 contribution**, tên + thứ tự top-K, **group sums**, **provenance
từng feature**, và **outcome của extras**. Chỉ loại bỏ `total_ms`/`latency_ms` — không loại
`results` hay `failures`.

## 7. Grouped contribution — aggregate thật

`aggregate_groups()` cộng **signed** contribution theo `FEATURE_GROUPS`, đồng thời kiểm:
mỗi feature đúng một group, không thiếu, không thừa, không trùng. `Σ(group) − Σ(φ) = 0.0`
chính xác trên 105 case. **Không** dùng `Σ|φ|`.

## 8. Provenance — suy từ ma trận thật

Trạng thái được suy từ **giá trị đã transform** (`frame.iloc[0][feature]`), không từ request:

| Điều kiện thực tế | State |
|---|---|
| feature computed (`has_*`, ratio) | `DERIVED` |
| encoded `__UNKNOWN__` | `UNKNOWN_CATEGORY` (42 quan sát) |
| encoded thiếu + feature không áp dụng cho loại hình | `NOT_APPLICABLE` (91) |
| encoded thiếu | `MISSING` (812) |
| có raw field tương ứng | `OBSERVED` (420) |
| có giá trị nhưng adapter tự điền | `DERIVED` |

`DEFAULTED` và `UNVERIFIED` **không** xuất hiện vì pipeline hiện tại không có nhánh
default tường minh; nếu gặp, classifier trả `UNVERIFIED` chứ không mặc định `DERIVED`.

## 9. Latency

`predict_from_v6_payload` đầy đủ (adapter + transform + predict + SHAP + formatting):
median **≈40 ms**, p95 **≈48 ms** trên máy local, không tách cold-start, **không phải SLA**.

## 10. Limitations

- Input synthetic ⇒ **không** suy ra hành vi thị trường.
- VILLA không phủ như category.
- Chưa đo cold-start/memory.
- `test_valuation_shap_contract.py` và `probe_shap.py`: **NOT_RUN** (chưa audit xong khả năng
  truy cập dữ liệu của script lịch sử).
- Chưa triển khai explanation contract trong production ⇒ đây là **design-phase evidence**.

## 11. Cách chạy

```bash
P=<repo>/ai-services/.venv/Scripts/python.exe
$P docs/ai/benchmark/wp04_explainability_benchmark.py --artifacts-dir <repo>/ai-services/artifacts/v1_3 --integrity-only
$P docs/ai/benchmark/wp04_explainability_benchmark.py --self-test
$P docs/ai/benchmark/wp04_explainability_benchmark.py --artifacts-dir <repo>/ai-services/artifacts/v1_3 --assertions
$P docs/ai/benchmark/wp04_explainability_benchmark.py --artifacts-dir <repo>/ai-services/artifacts/v1_3 --json
```
