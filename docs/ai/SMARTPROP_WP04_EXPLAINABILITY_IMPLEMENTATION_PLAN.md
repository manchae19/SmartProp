# SmartProp — WP-04 Explainability Implementation Plan (Phase A)

**Chưa thực hiện bước nào.** Phase B cần user approval.

## Stages

| Stage | Nội dung | Loại |
|---|---|---|
| **B0** | Sync main, xác nhận V1.3 integrity, đọc lại contract WP-01, rà overlap WP-02/PR#46 | readiness |
| **B1** | Contract: `explanation` additive, `other_contribution_log`, `predicted_margin_log`, `output_space`, raw + display precision | IMPLEMENT_WITHOUT_MIGRATION |
| **B2** | Provenance & missingness: state theo feature, câu tiếng Việt tương ứng | IMPLEMENT_WITHOUT_MIGRATION |
| **B3** | Spring Boot: DTO additive, giữ nguyên request/response cũ | IMPLEMENT_WITHOUT_MIGRATION |
| **B4** | React: `ValuationExplanationPanel` dùng chung + chart + provenance badge + unavailable state | IMPLEMENT_WITHOUT_MIGRATION |
| **B5** | Tích hợp 3 đường: standalone, posting preview, Advisor (explanation là mục riêng) | IMPLEMENT_WITHOUT_MIGRATION |
| **B6** | Regression: math tests, FastAPI, Spring, FE, parity V1.3, contract, browser | IMPLEMENT_WITHOUT_MIGRATION |
| **B7** | Tài liệu + handoff WP-05/06/07/08 | docs |

**Không migration dự kiến.** Nếu phát sinh ⇒ dừng, xin phê duyệt riêng.

## Acceptance invariants

I01 model vẫn V1.3 · I02 hash artifact không đổi · I03 prediction không đổi ·
I04 additivity trong tolerance · I05 naive reconstruction · I06 calibration reconstruction ·
I07 không cộng log-φ thành VNĐ · I08 top-K + other · I09 grouping không double-count ·
I10 missing ≠ observed · I11 derived ≠ observed · I12 not-applicable ≠ thiếu bắt buộc ·
I13 không bịa giá trị · I14 ordering tất định · I15 giá trị hữu hạn hoặc `UNAVAILABLE` ·
I16 contract additive · I17 ba đường được trace · I18 không trộn Comparable ·
I19 không trộn interval · I20–I22 không truy cập holdout/DB/research ·
I23 formatting không đổi prediction · I24 limitations được ghi.

## Rollback

Toàn bộ thay đổi Phase B là additive: revert commit hoặc tắt cờ hiển thị explanation. Không có
migration, không đổi model, nên rollback chỉ là revert source.

## Handoff

- **WP-05**: contract có slot interval, không suy từ SHAP.
- **WP-06**: metadata explanation availability / missingness / reconstruction / latency.
- **WP-07**: Advisor hiển thị explanation tách khỏi comparable & recommendation.
- **WP-08**: RAG chỉ diễn giải explanation đã cấp quyền, không tự tạo SHAP.


---

## 9. Bổ sung sau review

- **B6** phải chạy: `--integrity-only`, `--self-test`, `--assertions`, và **hai lần** full
  benchmark để so digest per-case.
- Chấp nhận: benchmark fail phải trả exit 1 (cả `--json`), fixture rỗng phải fail.
- Không đổi production trong Phase A; mọi kiểm chứng là offline + synthetic.


---

## 10. B0 readiness (final gate)

| Hạng mục | Trạng thái |
|---|---|
| main đã sync (`ebfb230`, PR #46 merged) | ✅ merge commit thường, không amend/rebase/force |
| Phase 0 security boundaries giữ nguyên | ✅ không truy cập TiniX/protected DB/holdout |
| Không thay đổi prediction V1.3 | ✅ hash artifact không đổi |
| Không retrain, không fallback V6 | ✅ |
| Không thay đổi migration | ✅ |
| B1–B7 | **NOT_STARTED** — chờ phê duyệt |
