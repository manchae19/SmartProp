# SmartProp — WP-04 Explainability Audit (Phase A)

**Base:** `origin/main` @ `a0e3834` · **Branch:** `research/wp04-explainable-ai`
**Phạm vi:** audit + thiết kế. **Không thay đổi production.**

## 1. Kiến trúc explainability hiện tại (đã kiểm chứng)

```
React panel ──► /api/ai (Flow A) ──┐
                                   ├── FastAPI /predict, /predict/v1_3_preview
Spring Boot ──► /predict (Flow B) ─┘        │
                                            ▼
                          PredictorV1_3.predict_from_v6_payload
                            adapter_v1_3.map_v6_to_v1_3
                            features_v1_3.transform          → 22 features
                            model.predict(X)                 → log1p margin z
                            booster.predict(pred_contribs=True) → SHAP + base
                            Duan-by-band calibration
                            shap_explanation{top_factors[6], base_value_log,
                                             base_price_vnd, method, summary_vi}
```

Nguồn: `ai-services/app/models/xgboost/predictor_v1_3.py:156-223`,
`features_v1_3.py:59-114`, `adapter_v1_3.py:63-110`.

## 2. Field inventory

| Field | Source | Ý nghĩa toán học | Đơn vị | Precision | Consumer hiện tại | Hạn chế |
|---|---|---|---|---|---|---|
| `predicted_asking_price_vnd` | `max(0, exp(z)*factor-1)` | giá rao ước tính sau calib | VND (int) | nguyên | FE, Advisor, history | int rounding |
| `naive_price_vnd` | `expm1(z)` | giá trước calib | VND (int) | nguyên | FE | không hiển thị rõ |
| `calibration_factor` | `calibration.json` band factor | hệ số Duan theo band | scalar | float | FE (ẩn) | branch theo band |
| `calibration_policy` | `calibration.json.method` | tên policy | — | — | FE | — |
| `base_value_log` | `contribs[-1]` | `b` trong log space | log1p(VND) | 4 dp khi trả về | FE | làm tròn 4 dp |
| `base_price_vnd` | `int(expm1(b))` | giá tại base | VND | nguyên | FE | — |
| `top_factors[].shap_value` | `contribs[i]` | `φ_i` trong log space | log1p | **round 4 dp** | FE, Advisor | cắt top 6 |
| `top_factors[].feature_name` | schema | tên feature | — | — | FE | không có provenance |
| `method` | hằng | `XGBOOST_NATIVE_TREESHAP` | — | — | FE | — |
| `summary_vi` | template | diễn giải thô | — | — | FE/Advisor | không phân biệt missing |
| `missing_features` | adapter | feature vắng | — | — | FE | không phân biệt NOT_APPLICABLE |
| `warnings` | API | cảnh báo địa lý | — | — | FE | — |
| `features_used` | adapter | giá trị đã dùng | mixed | — | FE | lẫn observed/derived |

**Không** có: `predicted_margin_log`, `other_contribution_log`, grouping, provenance state,
`explanation_status`, `output_space`.

## 3. Đã xong ở WP-01 (tái sử dụng, không làm lại)

- Native TreeSHAP thật (`pred_contribs=True`), không phải xấp xỉ.
- `iteration_range` theo `best_iteration`.
- Log1p → expm1 → calibration tách bạch trong code.
- `base_value_log` / `base_price_vnd` / `top_factors` / `method`.
- Ba đường định giá dùng **cùng** predictor.

## 4. Findings (mức độ, vị trí, impact)

| ID | Mức | Nội dung | Vị trí | Evidence | Phase B |
|---|---|---|---|---|---|
| WP04-F01 | **P1** | Top-6 bị cắt **không có** phần "yếu tố khác" ⇒ biểu đồ không tái lập được tổng contribution. Đo được: phần dư tới **0.1239 log unit** (median 0.0399) | `predictor_v1_3.py:212-213` | benchmark §4 | **bắt buộc** thêm `other_contribution_log` |
| WP04-F02 | **P1** | `shap_value` bị `round(...,4)` ngay trong payload; FE không thể tái lập chính xác | `:207` | source | tách `raw` (full precision) và `display` |
| WP04-F03 | **P1** | Không phân biệt missing / not-applicable / unknown-category ⇒ nguy cơ hiển thị "phường làm tăng giá" khi người dùng chưa nhập ward | `summary_vi`, `missing_features` | §5 dưới | **bắt buộc** provenance state |
| WP04-F04 | **P2** | Không expose `predicted_margin_log` và `output_space` ⇒ client không kiểm chứng được additivity | response | source | additive field |
| WP04-F05 | **P2** | Không có trạng thái explanation khi SHAP fail (không có `AVAILABLE/PARTIAL/UNAVAILABLE`) | `:161-168` | source | policy |
| WP04-F06 | **P3** | `summary_vi` là câu mẫu chung, không phản ánh factor cụ thể | `:190-205` | source | template theo factor |
| WP04-F07 | **P3** | FE không hiển thị base/naive/calibration bridge | FE panels | source | design |

## 5. Missingness & provenance — những gì **không** xác định được từ payload hiện tại

Với input chỉ có `district` + `area`: model vẫn trả 6 factor. Nhưng payload **không** cho biết
factor nào đến từ giá trị quan sát, factor nào đến từ nhánh xử lý missing (XGBoost định tuyến
missing theo hướng học được). Vì vậy câu "Phường này làm giá tăng X" là **không thể kiểm chứng**
từ payload hiện tại ⇒ phải chặn ở tầng trình bày (Phase B) và bổ sung provenance.

## 6. Cross-layer

Ba đường (Standalone `/predict`, Posting preview qua Spring, Advisor qua `AdvisorValuationAdapter`)
đều dùng cùng predictor và cùng block explanation. **Chưa** có bằng chứng full-stack parity mới
trong Phase A ⇒ ghi `PREDICTOR_LEVEL_VERIFIED`, không `FULL_STACK_PARITY_VERIFIED`.

## 7. Tests hiện có

`ai-services/tests/test_valuation_shap_contract.py`, `probe_shap.py`,
`run_20_sample_shap_audit.py` — **chưa chạy** trong Phase A (`NOT_RUN`), vì một số script lịch sử
có thể đọc dữ liệu; benchmark mới thay thế an toàn cho mục đích Phase A.


---

## 8. Bổ sung sau review (execution correctness)

- `--assertions` trước đây return sớm sau bước hash ⇒ **đã sửa**: giờ chạy full benchmark +
  failure self-tests. Thêm `--integrity-only` cho nhu cầu chỉ kiểm hash.
- Đếm **per-case** passed/failed (không dùng `len(cases) - len(failures)`).
- Extras được phân loại `SUCCESS`/`REJECT` theo **contract `ValuationRequest`**;
  `UNEXPECTED_ERROR` ⇒ failure.
- Kiểm thêm: dimension SHAP, thứ tự feature so với schema, `isfinite`, NaN.
- Grouped contribution: aggregate **thật** theo `FEATURE_GROUPS` (signed), có kiểm thiếu/trùng/thừa.
- Provenance: suy từ **ma trận đã transform**, phân biệt `UNKNOWN_CATEGORY` (42 quan sát) và
  `NOT_APPLICABLE` (91) thay vì mặc định `DERIVED`.


---

## 9. Final gate corrections

- **Production matrix parity:** benchmark trước đây ghi đè `ward` bằng raw payload. Production
  lấy ward từ **canonical record** (`PredictorV1_3.predict()` dựng `input_row` từ record, sau khi
  adapter strip tiền tố `Phường/Xã/Thị trấn` và casefold). Đã sửa và assert ở đúng tầng
  (`input_row` vs `__MISSING__/__UNKNOWN__` encoded), cộng thêm so `model.predict(frame)` với
  booster margin để chứng minh cùng ma trận.
- **Extras outcome:** `SUCCESS` chỉ pass khi actual SUCCESS; `REJECT` chỉ pass khi bị từ chối
  đúng nguồn (schema/adapter); `UNEXPECTED_ERROR` **luôn fail**.
- **Artifact count:** thư mục V1.3 chỉ có **4 file**; đã hash toàn bộ 4, không thể đáp ứng "8".
- **PR #46:** đã merge vào main tại `ebfb230`; Phase 0 security handoff (`docs/handoff/…`) đã
  nằm trong main sau merge.
