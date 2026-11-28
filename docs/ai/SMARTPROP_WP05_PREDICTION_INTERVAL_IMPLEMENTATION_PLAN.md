# WP-05 — Các bước Phase B đề xuất

Phase A dừng ở hồ sơ review, source audit và benchmark synthetic. **`WP05_REAL_CALIBRATION_DATA_UNAVAILABLE` chặn B1/B2.** Phase B cần ủy quyền riêng và cohort được phê duyệt. B3–B7 chỉ được đưa vào sử dụng sau khi có artifact hợp lệ và release gates. Giữ nguyên point V1.3 và cả ba flow hiện hành.

| Bước | Phạm vi | Điều kiện nghiệm thu đề xuất |
| --- | --- | --- |
| **B0 · Baseline và governance** | Pin main, model run và hashes, freeze eligibility, define intended ask-price population, owner/risk approval, target coverage options và tolerances. Khoá quyền truy cập, retention và protocol so sánh cho từng flow. | Main và production hash phù hợp. Data custodian độc lập giữ lịch sử exposure. Không tái mở train/eval đã hạn chế trong WP-05. |
| **B1 · Chuẩn bị dữ liệu được phép** | Custodian kiểm identity, repost/source/provenance, embargo các cohort lịch sử, chronology, label-time và feature-time. Tách development, calibration, untouched final và shift cohort. Replay đúng point policy và input modes. | Tài liệu quyền dùng và cohort đủ coverage domain được phê duyệt. Đếm entity và lặp, ghi drop reasons. Dừng nếu membership, labels, rights hoặc chronology không chứng minh được. |
| **B2 · Calibrate và version artifact** | Đối chiếu log C với B/B′; D/E/F chỉ khi scope và tails đủ evidence. Set cutoffs chỉ trên calibration, rank hữu hạn chính xác, evaluate một lần trên final. Tổng hợp CI có xét phụ thuộc nếu nhiều observations/entity. | Predeclare coverage/tail tolerances, width/score limit, support/availability, drift/fallback và đánh giá theo flow/type/missingness. Thiếu support thì abstain, label fallback đúng phạm vi. Validate artifact bindings và rollback trước publish. |
| **B3 · FastAPI** | Module được cô lập sau point predictor, kiểm snapshot artifact và trả optional envelope. Định giá `/predict` và alias giữ các price fields và response semantics. | Same-request point parity với flag on/off, valid/unsupported/unavailable, numeric boundary và scope validation, malformed artifact, no extra model inference, rollback. |
| **B4 · Spring** | Additive tolerant DTO ở preview và Advisor, mapping dùng cùng bounds và point đã có. Giữ existing auth and timeouts. | MockMvc/serialization tests cho interval cũ, thiếu và sai schema, các field hiện hữu giữ nguyên, authorization boundaries và degraded interval vẫn có price. |
| **B5 · React** | Shared panel tiếng Việt, accessibility, number formatting outward, separate WP-02/WP-04. | Kiểm mobile/desktop, availability/fallback, các mức được duyệt, stale session/criteria và việc ẩn phần trăm thiếu validation. |
| **B6 · Runtime ba surface** | Chạy isolated real HTTP cho standalone, posting preview và Advisor, dùng fixture hoặc cohort được phép. Đánh giá behavior nhãn/quantiles trong phạm vi approved sample. | Browser và HTTP evidence phân biệt rõ, point giữ nguyên, runtime bảo toàn authorization. Flags và artifact reload fail closed. |
| **B7 · Regression và handoff** | Targeted valuation, Comparable, Advisor, regression backend/frontend/RAG theo diff, build, migration/model integrity. Publish cohort aggregate được phép và chuyển monitoring spec WP-06. | Review độc lập artifact/data/metrics, documented limitations, release owner approval và rollback drill. Gỡ feature bằng flag khi drift/control gate vi phạm. |

## Ma trận overlap chỉ đọc

So sánh các remote refs với common base tại thời điểm kiểm. WP-05 Phase A chỉ thêm tài liệu và benchmark. Các path dưới đây là phạm vi phối hợp của Phase B.

| Work | Remote SHA khảo sát | Overlap và contract tương lai |
| --- | --- | --- |
| WP-02 đã merge | `1c67a279a8ff6f6939767e82bb31b17584610864` | `AdvisorDtos.java`, `ValuationPanel.jsx`, `PostValuationPanel.jsx`, `AdvisorEvidencePanel.jsx`. Giữ `ComparableItem.featureCoverage`, cả hai evidence lists, lookup, reactive session và price-independent ranking. |
| WP-04 Explainable AI | `6d27a9254ba7871d85682837636172184131c49a` | Diff remote chạm FastAPI `schemas.py`, `valuation.py`, `predictor_v1_3.py`, Spring `ValuationService.java`, `AdvisorDtos.java`, `AdvisorValuationAdapter.java`. Panel/normalizer riêng của WP-04 có trong diff. Ba entry components React vẫn là overlap dự kiến khi lắp chung. Thêm `prediction_interval` bên cạnh `ValuationEvidence.explanation` và legacy SHAP, dùng cùng frozen point. |
| PR #37 Frontend UI | `151a07b4472ea0fd3134fb50f4f3de757e83d46f` | Giữ `ListingDetailView.jsx` và lookup WP-02. Ba luồng WP-05 không cần đổi listing detail. |
| PR #40 Google Account Linking | `24fc5711171ff20b94dcb9945d38d2543b8bccf7` | `auth/api.js` là dependency gián tiếp. Giữ status/actor/token/role và reactive auth tại surfaces phải đăng nhập. |
| PR #43 Advisor Land Integration | `f59edf223c98249ee6104c367c34537bd851aea5` | `ListingDetailView.jsx` là overlap đã ghi nhận của WP-02. Các xung đột lịch sử ở RAG/Recommendation/proxy nằm ngoài WP-05. Giữ Phase 0 security, PR #45 RAG và SAFE Comparable evidence. |

Các branch này do từng owner đồng bộ tại checkpoint riêng. WP-05 Phase A giữ nhánh nghiên cứu độc lập. [WP-02 API contract](SMARTPROP_WP02_COMPARABLE_API_CONTRACT.md) · [Thiết kế WP-05](SMARTPROP_WP05_PREDICTION_INTERVAL_TECHNICAL_DESIGN.md)

## Phase A validation

Chạy hai lượt seed chính đồng nhất, một sensitivity seed và 23 unit tests từ worktree WP-05. Đối chiếu đủ bốn file của manifest inference ở hai bản local được pin. So sánh production source, schema/migrations và baseline tree bằng Git. Các suite runtime production ngoài phạm vi thay đổi research. Full-stack HTTP, actual Caddy runtime, MySQL live/grants/views và coverage thật vẫn thiếu evidence. [Benchmark report](SMARTPROP_WP05_PREDICTION_INTERVAL_BENCHMARK_REPORT.md) · [Governance](SMARTPROP_WP05_PREDICTION_INTERVAL_DATA_GOVERNANCE.md)
