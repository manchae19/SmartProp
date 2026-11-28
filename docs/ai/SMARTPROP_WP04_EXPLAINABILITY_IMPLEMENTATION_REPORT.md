# SmartProp — WP-04 Explainability Implementation Report (Phase B, partial)

**Branch:** `research/wp04-explainable-ai` · **Baseline:** main `ebfb230` (PR #46 merged)

## Đã triển khai

### B1 — Explanation contract (FastAPI) ✅
`ai-services/app/models/xgboost/explanation_v1_3.py` (mới) + wire trong
`PredictorV1_3.predict()`:

- Dùng **native TreeSHAP đã tính sẵn** — **không gọi model lần thứ hai**.
- Không đổi prediction path, `iteration_range`, calibration policy.
- `contribution_log_raw` full precision; `contribution_log_display` làm tròn 4 dp.
- Top-K (6) + `other_contribution_log` tái lập **toàn bộ** contribution.
- `grouped_contributions` cộng **signed**, không double-count.
- Ordering tất định: `(-|φ|, feature_name)`.
- Legacy `shap_explanation` **giữ nguyên** (6 key cũ).
- Thêm `explanation` vào `V1_3PreviewResponse` (optional, default `None`) ⇒ payload cũ vẫn hợp lệ.
- Wire additive vào `/predict` và `/predict/v1_3_preview`.

### B2 — Feature provenance ✅ (tầng dữ liệu)
7 trạng thái; suy từ **encoded value** + raw payload keys + loại hình:
`OBSERVED / DERIVED / DEFAULTED / MISSING / NOT_APPLICABLE / UNKNOWN_CATEGORY / UNVERIFIED`.
Không mặc định `DERIVED`; ward thiếu ⇒ `MISSING`; ward lạ ⇒ `UNKNOWN_CATEGORY`; LAND ⇒ `NOT_APPLICABLE`.
Câu tiếng Việt theo trạng thái (`context_note_vi`).

### Failure isolation ✅
`build_explanation` lỗi ⇒ `status = UNAVAILABLE`, `factors = null`, **giá vẫn hợp lệ**,
legacy block nguyên vẹn.

## Chưa triển khai (cần approval riêng / lượt sau)

| Mục | Trạng thái |
|---|---|
| B3 Spring Boot DTO/proxy | **NOT_STARTED** |
| B4 React `ValuationExplanationPanel` | **NOT_STARTED** |
| B5 tích hợp 3 đường (runtime) | **NOT_STARTED** — hiện mới có tầng FastAPI |
| B6 full-stack regression + browser | **PARTIAL** — chỉ FastAPI |
| B7 docs/handoff đầy đủ | **PARTIAL** (báo cáo này) |

## Rollback
Revert commit này; explanation là additive nên không ảnh hưởng client cũ, không migration.

## Evidence
FastAPI non-RAG: **437 passed / 20 skipped / 84 subtests / exit 0**.
WP-04 contract tests: **14/14**. Benchmark: **105 case / 15 extras / digest không đổi**
`9eedb3c7c3668f61` ⇒ chứng minh explanation **không đổi prediction/benchmark**.


---

## B1/B2 final validation (round 3)

### Additivity normalisation (root cause)
LAND failed because the validator divided the residual by `|margin - base|` (0.805) instead of
`|margin|` (22.08): residual 2.575e-05 → 3.2e-05 relative instead of 1.17e-06. Fixed to the
reviewed Phase A formula `abs(margin-(base+sum_phi))/max(1,|margin|) <= 1e-5`. No tolerance
relaxation. `margin_shap == log_pred` verified (parity exact), so no tree-range discrepancy.

### Legacy nullability
`shap_valid` is computed from the SHAP numbers themselves (dimension, finiteness, group
mapping, additivity, margin parity). Legacy `shap_explanation` is returned only when
`shap_valid`; otherwise it is `null`. A **builder-only** failure keeps the valid legacy block
and sets `explanation.status = UNAVAILABLE`.

### HTTP contract
`tests/test_wp04_explanation_http.py`: both endpoints × HOUSE/LAND/APARTMENT/VILLA plus six
failure modes injected at the **native SHAP output** (exception, NaN, Infinity, dimension,
additivity, margin mismatch). All return HTTP 200 with an unchanged price; invalid input still
returns 4xx. Strict `json.dumps(..., allow_nan=False)` and recursive finiteness checks.

### Benchmark rejection source
Extras now separate **SCHEMA** (ValuationRequest), **ADAPTER** (adapter + transform executed
alone) and **INTERNAL** (any error from full prediction, always a failure).

### Environment
`faiss-cpu==1.15.1` installed with `--no-deps` into the project venv
(Python 3.14.6, numpy 2.5.3, xgboost 3.4.1 — both unchanged, `pip check` clean, nothing else
added or changed). Installed into the shared `ai-services/.venv` because the worktree has no
venv of its own — recorded as a deviation from "worktree-local venv".

### Fresh evidence
- `tests/test_wp04_explanation_http.py` + contract: **37 passed**
- `tests/test_rag_g2.py`: **37 passed**
- Full FastAPI serial: **1216 passed, 20 skipped, 105 subtests, exit 0**
- Benchmark `--assertions`: 105 cases, 15 extras, self-tests PASS, digest `9eedb3c7c3668f61`
- Two JSON runs: identical digest, exit 0

---

## B3 — Spring Boot integration

### Contract
`ValuationService.Preview` và `AdvisorDtos.ValuationEvidence` mang thêm một component
`JsonNode explanation` (additive, cuối record). `ValuationClient` vốn đã trả `JsonNode` nên
không đổi tầng transport.

- `explanationOf(JsonNode body)`: `null` cho absent / NullNode / MissingNode / non-object;
  object hợp lệ được truyền nguyên. Không tạo attribution ở Java.
- `ValuationEvidence` có thêm constructor 12-arg tương thích ngược để caller cũ (và test cũ của
  PR #39/#45) không phải sửa.
- Legacy `shap_explanation` giữ nguyên (`ShapSummary`), không bị thay thế.
- Prediction, persistence, authorization không đổi; không migration.

### Verification
- `ValuationExplanationContractTest` — **8 test**: round-trip giữ nested fields + precision,
  legacy payload không có `explanation` → JSON `null`, cả 4 status (`AVAILABLE`, `PARTIAL`,
  `UNAVAILABLE`, `NOT_SUPPORTED`) đi qua nguyên vẹn, malformed (array/string/null/absent) → `null`,
  không sinh factors giả.
- `ValuationExplanationRuntimeTest` — **5 test**: HTTP thật trên loopback qua `ValuationClient`
  thật tới stub peer phục vụ payload cùng shape FastAPI: explanation sống sót qua hop, payload
  legacy, malformed, peer 503 → lỗi unavailable, route preview.
- **Phát hiện**: Jackson `JsonNode` giữ số dạng **double** (IEEE-754), không phải BigDecimal tuỳ ý.
  FastAPI phát `float64` nên round-trip là lossless; test dùng đúng biểu diễn float64
  (`-0.8049478546599858`). Nếu sau này cần số thập phân tuỳ ý phải bật
  `USE_BIG_DECIMAL_FOR_FLOATS` — ghi lại làm điều kiện mở rộng.
- Backend: **271 test, 0 failure** (`mvnw -o test`, BUILD SUCCESS).
- FastAPI WP04 (contract + HTTP + matrix parity): **51 passed**; benchmark 105 case, digest
  `9eedb3c7c3668f61` không đổi.