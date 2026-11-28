# WP-06 · Kế hoạch Phase B chờ phê duyệt

Phase A bàn giao nghiên cứu, source audit, metric contract, privacy và benchmark. Các bước dưới đây có thể tách commit, gate và rollback. B1–B4 có thể kiểm operational bằng fixtures khi chưa có nhãn hoặc reference hợp pháp. B5 chỉ đọc optional contracts sau khi nhánh tương ứng được phê duyệt, hoặc đo `NOT_ENABLED` theo capability khi chưa có.

| Giai đoạn | Triển khai đề xuất | Gate bắt buộc |
| --- | --- | --- |
| B0 · Baseline và governance | Pin base SHA, rollout pane, source of truth per metric, RBAC, schema/frozen bins, privacy, approved budget, allowlist, runtime classes. Chốt availability của authorized reference/labels, snapshot WP‑04/WP‑05 và Caddy route thật. | Map chính xác 3 surfaces, risk register, deny rules, manifest SHA, code owners duyệt. Baseline latency khi flags off trong môi trường được phép. |
| B1 · Telemetry bounded | Schema version + enums, pre-allocated counters, histogram combiner, event/batch lifecycle, idempotent merge, capability/drop. Dark off mặc định. | Concurrent writers, restart, overflow, invalid numeric, same-batch retry, metric count conservation, telemetry down, no PII high cardinality. |
| B2 · FastAPI | Health/readiness/load/integrity, terminal reason classification, validation, timings ở adapter/point/calibration, allowed outputs. Quan sát existing native TreeSHAP riêng, không bật Shadow. | Verify model files/manifest, missing artifact, invalid input, invalid output, no V6. Golden point parity và một call model. Document giữa app-ready và artifact-ready. |
| B3 · Input quality và drift | Monitor raw flags, effective state, applicable dims, provenance và categorical allowlist trên đúng 22 columns. Private histograms/trend. Reference compatible, cửa sổ đầy đủ và sample suppression. | Fixtures sparse/empty, schema mismatch, range and mode separation, manifest field order, PSI/JS/W1/KS reproducibility. Real drift flags giữ off khi chưa có serving reference phê duyệt. |
| B4 · Spring và correlation | Reuse Actuator registry where available. Add trusted temporary operation context tới loopback, stage counters và response classification. Advisor consult vs candidate counts, bounds and late timeouts. | Sequential/concurrent dual-flow fixture và cancellation, dispatch retry, cache-if-enabled, unsupported/disabled, transport failure, telemetry restart. Verify 3 surfaces không double count. |
| B5 · WP‑04 và optional WP‑05 | Adapter chỉ dùng status/version/histograms/aggregate integrity. WP‑04 giữ tolerance, output price và evidence independence. WP‑05 chưa bật giữ `NOT_ENABLED`, artifact incompatible giữ `NOT_AVAILABLE`. | Snapshots malformed/partial/unsupported, version mismatch, reconstruction, latent aggregation, interval-width and no-label absence. Lỗi optional không làm fail point. |
| B6 · Dashboard private | Spring approved aggregate read projection, Vietnamese dashboard, internal ingress allowlist. Staging isolated fixtures, no public metrics endpoint. | Real Caddy/Tomcat isolated config, direct reachability tests, current ADMIN revocation, A11y, latency, size cap, no-store and row/label suppression, route variants deny. |
| B7 · Regression và handoff | Fresh regression theo runtime tác động, benchmark cost across workers, alert false alarm sign-off, rollback, on-call runbook. | Artifact/migration scope, source parity, runtime budgets, source and auth isolation, publish evidence and remaining limitations. No production deploy without explicit approval. |

Các Phase A tests chứng minh behavior của prototype offline. Cases mất dữ liệu, active rights, consumer idempotence, HTTP late completions và failure isolation qua process là Phase B release tests. Không suy diễn chúng từ unit tests. Delayed evaluation track riêng cần protocol nhãn và approve bởi custodian, label match coverage theo mode, cohort drift, cohort adequacy và release review trước dashboard. True empirical interval coverage còn phụ thuộc WP‑05 có issued intervals.

## Overlap đọc-only

Đối chiếu đường dẫn diff của 8 tệp mới WP‑06 với nhánh từ merge base tương ứng. Bảng phân biệt path overlap hiện tại và overlap tiềm năng của Phase B. Snapshot remote được kiểm lại sau preflight.

| Track | Snapshot remote | Phase A direct overlap | Contract cần bảo toàn cho Phase B |
| --- | --- | --- | --- |
| WP‑04 `research/wp04-explainable-ai` | `074bb7333b93651d8f0bd8cae5b4a01cf63f3834` | 0 | Predictor + valuation route + DTOs, condition và reconstruction `1e−5`, giữ cả hai Advisor Comparable evidence fields độc lập. |
| WP‑05 `research/wp05-prediction-interval` | `a0a5d88db1a77bc3dc55f9981dd313faa52f5b8b` | 0 | Optional interval/status và bounded output, schema artifact binding, riêng observed labels. WP‑05 B1/B2 vẫn bị chặn. |
| PR #37 integration | `fb918e6f5a68cedf35b7e6e908897af4e895bb7a` | 0 | Existing standalone/posting/Advisor clients, token refresh và trạng thái auth của Market. Giữ UI flow, không đưa public monitor payload. |
| PR #37 contributor | `151a07b4472ea0fd3134fb50f4f3de757e83d46f` | 0 | Tách riêng original branch với integration, tham chiếu read-only. |
| PR #40 Google Account Linking | `24fc5711171ff20b94dcb9945d38d2543b8bccf7` | 0 | Existing session store, auth token handling và active role. Internal read projection phải re-check rights. |
| PR #43 Advisor Land Integration | `f59edf223c98249ee6104c367c34537bd851aea5` | 0 | Advisor/Tomcat/Caddy, Phase 0 isolation, PR #45 và WP‑02 evidence. PR vẫn deferred. |

Main có PR #44/#45/#46/#47. Trong lúc audit, WP‑04 B6 và PR #37 integration tiến thêm một commit mỗi nhánh từ phiên song song. WP‑06 chỉ đọc các ref đó. B0 cần kiểm remote và overlap lại ngay trước khi bắt đầu.

## Rollback và evidence

Tắt flags theo producer/exporter/UI, dùng previous schema compatible khi được phê duyệt. Ghi discontinuity và suppress alerts cho window lẫn phiên bản. Revert monitoring-only commit theo plan giữ point, artifacts, config auth và migrations. Giữ Caddy actual runtime, live MySQL/grants/views chưa xác minh. Checkpoint cục bộ giữ exact revision, artifact comparison và reproducibility output. [Research audit](SMARTPROP_WP06_MODEL_MONITORING_RESEARCH_REPORT.md) · [Metric contract](SMARTPROP_WP06_MODEL_MONITORING_METRIC_CONTRACT.md) · [Benchmark](SMARTPROP_WP06_MODEL_MONITORING_BENCHMARK_REPORT.md).
