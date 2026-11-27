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
