# SmartProp WP-06 B4 — Spring monitoring và tương quan aggregate

B4 bắt đầu từ HEAD đã duyệt `4a7e66d7d8d033d1d17e843cdfa68f7e28bbe139` trên `research/wp06-model-monitoring`. Main baseline `1c67a279a8ff6f6939767e82bb31b17584610864` là ancestor. B4 cung cấp adapter Java mặc định tắt, kiểm thử synthetic và hợp đồng bàn giao. Runtime wiring chờ tích hợp WP-04 và xác minh trust boundary.

## Call path và điểm gắn sau khi được duyệt

| Đường gọi đã kiểm tra | Hành vi hiện tại | Điểm gắn dự kiến |
| --- | --- | --- |
| Posting — `ValuationController.preview` → `ValuationService.preview` → `loadOptions` / `previewV13` → `ValuationClient.exchange` | `POST /api/v1/properties/valuation-preview` dùng JWT, publisher access, rate limits và private no-store. Điều kiện sale, loại, diện tích và input được kiểm trước khi gọi options. Sau khi kiểm danh mục/địa bàn thì chạy tối đa một `POST /predict`. `GET /api/v1/properties/valuation-options` là discovery riêng. Business có thể trả preview không có giá khi AI unavailable. | Surface ở admission/terminal của route đã xác nhận. Nếu đo lỗi validation/bảo mật trước controller, đặt hook ở route-specific MVC/security boundary và tránh đếm hai lần. Opportunity quanh quyết định định giá; options là probe. Ghi dispatch tại lần gửi `/predict` thực tế và lấy outcome trước khi catch đổi thành unavailable. |
| Advisor — `AdvisorController.consult` → `AdvisorOrchestrationService.consult` → `AdvisorValuationAdapter.probeSupportedLocations` / `evaluate` → `exchange` | `POST /api/v1/advisor/consult` rate limit theo IP và actor. Research yêu cầu active admin và flag. SAFE chỉ giữ listing platform phù hợp hoặc external `VALID`/`VERIFIED`, loại TiniX và bản ghi thiếu chuẩn. `includeValuation=false` bỏ probe; nếu bật thì gọi options một lần trước vòng lặp. `evaluate` kiểm loại, diện tích, district và supported locations trước POST. Nhánh research bỏ định giá listing TiniX. | Controller ghi một surface terminal cho cả consult. Orchestration ghi opt-out một lần, candidate skip tại gate và eligibility đúng điểm kiểm, kể cả trong `evaluate`. Opportunity bắt đầu khi ứng viên đủ điều kiện theo policy. Probe/options đứng riêng. Client ghi dispatch tại lần gửi thực tế. Không đưa candidate/record key hoặc mode research của request vào metric labels. |
| Standalone — `frontend/src/features/prediction/valuation.js` → Vite `/api/ai` → FastAPI | Vite dev bỏ prefix, trỏ AI loopback mặc định 8000 và proxy timeout 15 s. Caddyfile đang track đưa `/api/*` đến Spring `127.0.0.1:8080`, chặn route research/biến thể, bỏ `X-SmartProp-Demo-Key` và `Forwarded`. File này chưa chỉ ra route riêng đưa standalone trực tiếp đến FastAPI. `ops/smartprop.service` bind Spring vào loopback. | Surface standalone thuộc ingress đã xác minh. FastAPI admission/invocation giữ unattributed khi thiếu trusted binding. Đo options/health tại boundary tương ứng. |
| Actuator và Micrometer | Actuator 3.5.16 kéo Micrometer 1.15.12. Application chỉ expose health, ẩn details, bật probes và readiness gồm `readinessState,db`. | B4 có registry tĩnh độc lập. Readiness Spring giữ ý nghĩa riêng với tính khả dụng của model. |

Posting dùng timeout connect 1 s, timeout request 5 s, deadline chờ body 5 s, trần body 65.536 B, fixed IPv4 loopback và redirect `NEVER`. Advisor dùng connect 1.200 ms, options 1.800 ms, predict 4.000 ms, chờ body thêm 300 ms so với request timeout tương ứng và trần body 131.072 B. Hai client hủy future còn pending khi dừng exchange và khôi phục interrupted flag. Hai exchange không có application retry hay response cache trên call path đã audit. Retry fixture mô phỏng quyết định của caller. Cleanup sau timeout giữ outcome timeout. Một HTTP 503 đọc được vẫn là dispatch có response; outcome điểm giá ở opportunity do business quyết định. Application dispatch không đo retry nội bộ của HTTP transport.

## Adapter, privacy và budgets

- `TrustedOrigin` dùng enum chỉ server chọn. Posting/Advisor chọn từ boundary controller tin cậy. Standalone cần ingress có route đã xác minh. Unverified mặc định unattributed. Preview nội bộ, diagnostic và historical ở population riêng. Mỗi recorder nhận đúng population; synthetic replay có thể dùng surface serving trong recorder synthetic. Không đọc header, client correlation hoặc token.
- `MonitoringSchema`, `SpringTelemetry` và `DispatchOutcome` ghi bốn lifecycle độc lập. Outcome, completed và histogram cập nhật cùng nhau. Mỗi family giữ `opening + started = completed + active + lost` và `completed = sum(outcomes) = histogram.count`. Lock busy khi finish, clock invalid hoặc overflow làm mất bằng chứng terminal, được reconcile với health counters. Duplicate finish không tăng completed. Duration dùng clock monotonic; caller cung cấp UTC window. Rotation nhảy phút ghi discontinuity và để các window bị bỏ qua thiếu bằng chứng.
- Ticket là object cục bộ không serialize hoặc log. Tối đa 1.024 ticket active; rotate đến phút thứ 10 tính từ window mở ticket sẽ hết hạn. Rotation của coordinator là điều kiện thực thi giới hạn theo thời gian. Ticket được giải phóng khi finish thành công hoặc reconcile loss. Metrics chỉ nhận enum, số đo clock và UTC; không lưu user/listing ID, địa chỉ, tọa độ, giá đầu vào, mật khẩu, JWT, email, số điện thoại, payload SHAP hay nội dung chat.
- `MonitoringGuard` cô lập exception recorder, gọi business operation một lần và giữ object trả về hoặc exception gốc. `BatchBuffer` nhận packet immutable, tối đa 64 mục và 128 KiB charged bytes, tính 64 B overhead mỗi packet. Handoff tương lai phải ghi `queue_full`, `batch_rejected` hoặc `lock_busy` khi không nhận được batch. Buffer không mở socket hoặc chạy retry.
- Java dùng 445 slots tĩnh, gồm 336 wire slots và 109 local. Payload `long[445]` là 3.560 B mỗi state/snapshot, packet dense tối đa 3.390 B. Ngân sách ước tính ≤512 KiB cho một recorder, buffer, registry dùng chung và một snapshot đang encode, dự trù 96 KiB tickets, 16 KiB identity-map slots, 100 KiB registry, 132 KiB buffer và tham chiếu. Đây là mô hình phân bổ, chưa đo Java heap hoặc production overhead. Caller chỉ giữ snapshot/packet trong handoff bounded. Python ở 3.986/4.096 slots, còn 110; collector vẫn giới hạn 32 producers, 10 phút mở, 4.096 dedupe keys và buffer 512 mục/4 MiB.

### Mẫu số và quyền sở hữu

| Chỉ số | Đơn vị và cách đọc |
| --- | --- |
| Surface | Một yêu cầu cho mỗi admission của surface. Một consult phục vụ phần còn lại có thể `served` khi định giá lỗi. |
| Candidates / eligible | Đếm ứng viên được đánh giá điều kiện; terminal `eligible`, `skip` và gián đoạn riêng. |
| Opportunity | Một quyết định định giá đủ điều kiện. Point hợp lệ, cache hit, skip sau khi mở hoặc lỗi có terminal riêng. Có thể có 0 hoặc nhiều dispatch. |
| Dispatch | Một lần gọi predict qua client. Retry label chỉ đi cùng attempt mới đã được caller quyết định. Timeout/cancel/dependency/response đọc trên completed dispatches, có in-flight/lost cạnh tỷ lệ. |
| Explicit skip, cache, probes | Counter theo enum. Tỷ lệ cache dùng kết quả của cache lookups. Probe/options ngoài dispatch attempts. Opt-out theo consult và thiếu input theo candidate có mẫu số khác nhau. |
| FastAPI admission / invocation | FastAPI sở hữu model invocation và point output. Java không ghi các cells này. Fixture chứa Spring timeout và FastAPI invocation thành công trong window đầu, retry response Spring trong window sau. Không suy ra liên kết từng request từ aggregate. |

## Aggregate interchange và trust boundary

WPT3 little-endian, header 30 B, entry 10 B, slot/value theo thứ tự tăng nghiêm ngặt. Version 3, release 1 cho V1.3. Population codes 1 serving, 2 synthetic, 3 preview, 4 internal, 5 historical. Producer slot 1..32 và generation uint32 dương. Sequence bằng `1 + (window_start - generation_start)/60`. Window UTC `[start,end)` 60 giây. Ghi terminal vào window hoàn thành và chuyển in-flight qua opening/active. Đếm integer, elapsed µs floor từ nanos, tối đa 3.600.000.000 µs; scalar cap `2^53−1`. Cộng bucket counts cùng schema trước khi tính percentile nearest-rank; overflow biểu diễn lower bound với upper trống.

Spring xuất slots `0..281,388..441`. WPT3 chưa có Spring surface unattributed; local snapshot giữ nó và encoder từ chối snapshot không thể project. Wiring cần lanes riêng cho verified serving và local unknown/diagnostic để unknown không chặn export serving. Collector phải ràng producer slot với identity xác thực của transport, kiểm ownership theo slot ranges và generation đã đăng ký. Metadata trong packet chỉ là dữ liệu đối chiếu. Reducer hiện hữu kiểm binding slot, population, version, duplicate, overlap, continuity, watermark/replay; ingress ownership từng family là yêu cầu khi wiring. Restart đăng ký generation mới ở boundary và sequence về 1. Những window thiếu giữ coverage suy giảm thay vì điền số 0 có nghĩa nghiệp vụ.

Loopback dùng chung chưa phân biệt Spring, Vite, Caddy hay process khác. Cần xác thực ingress và peer bằng private mTLS hoặc channel local được giới hạn bằng quyền OS, kiểm exact path, direct/encoded variants và reject client surface/correlation. Serving Advisor chỉ thu từ consult SAFE. Consult research đã qua authorization phải nằm ở lane nội bộ riêng hoặc bỏ observation; candidate skip trên hồ sơ chưa đủ điều kiện vẫn có thể đếm trong consult SAFE. Giữ `CADDY_ACTUAL_RUNTIME_NOT_VERIFIED`, `COLLECTOR_RUNTIME_BINDING_NOT_VERIFIED`, `MYSQL_LIVE_IT_NOT_RUN`, `MYSQL_GRANTS_NOT_VERIFIED` và `DEPLOYED_VIEWS_NOT_VERIFIED`. Live telemetry, Spring/FastAPI response parity, inference parity/overhead và production deployment chưa được chạy.

## B5 — Integration map

1. Sau khi WP-04 tích hợp, audit exact snapshot rồi gắn FastAPI B2 tại admission và single point compute. Gắn Spring tại các điểm trong call path ở trên. Giữ flags riêng mặc định tắt, test point/Advisor output parity, malformed replies, cancellation, zero-to-many, timeout với downstream point, inference count và Caddy/Tomcat thực.
2. WP-04 producer ghi availability và version. Checker đo schema/check status, latency và reconstruction đúng tại nơi kiểm, giữ relative tolerance `1e-5`. Consumer ghi mismatch khi DTO price khác authoritative point. Giữ cả hai Advisor comparable evidence fields cùng feature coverage. Counts theo attempts, envelopes checked, reconstructable và applicable feature opportunities. Không recompute SHAP hoặc xuất base value, contributions, factors hay payload.
3. Giữ tám bucket provenance ở B5.

   | WP-04 | Aggregate bucket |
   | --- | --- |
   | OBSERVED | observed |
   | DERIVED | derived |
   | DEFAULTED | defaulted |
   | MISSING | missing |
   | MISSING_INVALID | missing_invalid |
   | UNKNOWN_CATEGORY | unknown_category |
   | NOT_APPLICABLE | not_applicable |
   | UNVERIFIED | unverified |

   B2 v3 chỉ có sáu provenance counters mỗi AI source. Mapping lossless cần versioned registry tám bins trên bốn scope, tăng 8 slots lên dự kiến 3.994/4.096 trước các thay đổi B5 khác. Producer, decoder và projection nâng version đồng bộ. Giữ provenance projection unavailable trước khi được duyệt; không gộp invalid vào missing hoặc unverified vào unknown. Reject enum lạ; không thêm tên/giá trị từng feature.
4. WP-05 dùng `NOT_ENABLED` khi chưa bật, `NOT_AVAILABLE` khi không tương thích artifact/model/schema. Tách availability và width online khỏi empirical coverage cần ground truth. Giữ `WP06_REAL_SERVING_REFERENCE_UNAVAILABLE`, `WP06_DELAYED_ACCURACY_DATA_UNAVAILABLE` và `WP05_REAL_CALIBRATION_DATA_UNAVAILABLE`.
5. Probe zero-wait của B2 chỉ kiểm primary-lock. Đo health-lock contention của Python, reconciliation và snapshot interference trong benchmark inference cô lập, flags off/on cùng artifacts và concurrency 1/4/16/32, có collector outage/saturation/restart. Báo added p50/p95/p99, lock wait, drops và lost/recovery. Java test dùng fixture tranh chấp lock; chi phí runtime chưa được xác minh.

## B6 — Đề xuất read contract cho Admin Dashboard

| Projection | Đọc nội bộ |
| --- | --- |
| Readiness và freshness | Release/schema, population, UTC window, process/app/model/integrity và options riêng. Expected/received sources và batches, lost, drops, late, continuity. Trạng thái `AVAILABLE`, `NOT_ENABLED`, `NOT_AVAILABLE`, `INSUFFICIENT_EVIDENCE`, `STALE`; tỷ lệ null khi mẫu số hoặc coverage thiếu. |
| Funnel vận hành | Surface, candidate eligibility, opportunity, cache, dispatch/retry/timeout/cancel/dependency và actual invocation/point theo owner. Hiển thị numerator, denominator, in-flight/lost và bucket estimates P50/P95/P99 sau merge. |
| Feature quality, drift và optional | Approved aggregate cohorts, reference/sample size và freshness. Explanation fidelity/version/latency/provenance theo B5. Interval availability/width/coverage theo cohort đủ điều kiện. Synthetic riêng. |
| Authorization và privacy | Backend kiểm active ADMIN và permission monitoring mỗi request, deny mặc định, no-store. Role revoke cùng token xóa projection và invalidate pending response. Fixed windows/queries, suppress `n<30`, chặn differencing, kiểm ingress và encoded variants. Security audit tách riêng. |

B6 mới là hợp đồng đề xuất. Không có dashboard API, React, alerting, exporter hoặc persistence trong B4.

## Fresh validation

Python 3.14.6, Java 21 và Maven offline. Log và exit code ở `.smartprop/wp06-b4-*` trong worktree. Không khởi chạy ứng dụng hoặc database.

| Command | Exit | Kết quả / evidence |
| --- | ---: | --- |
| `cd ai-services; python -B -m unittest discover -s tests -p 'test_wp06*.py' -v` | 0 | 56 passed, 0 failures/errors/skips, `existing.log`. |
| `python -B -m unittest discover -s docs/ai/benchmark -p test_wp06_model_monitoring_benchmark.py -v` | 0 | 22 passed, 0 failures/errors/skips, `phase-a-tests.log`. |
| `python -B docs/ai/benchmark/wp06_model_monitoring_benchmark.py` | 0 | 27 scenarios × 8 seeds, 2.592 windows; SHA-256 `0820d4bb424d19c8660f9d116089e585cc5094fb10701e96fe8a620dc7d58c3c`, `phase-a.json`. |
| `python -B docs/ai/benchmark/wp06_telemetry_core_profile.py` | 0 | Fixture v3 SHA-256 `a094cd890d870b67d11124f122d8352236bc59df2b3d46bea853b34e6735594a`, `core.json`. |
| Hai script benchmark trên với `--profile` | 0 mỗi lệnh | `phase-a-profile.json`, `core-profile.json`. Core modeled peak 6.295.037 B; added P95 synthetic 7,8–21,1 µs. Profile phụ thuộc host. |
| `cd backend; .\mvnw.cmd -o '-Dtest=SpringTelemetryTest,AggregateBatchTest' test` | 0 | 16 JUnit passed, 0 failures/errors/skips, `java.log`. Zero-to-many, retry/timeout, cancellation, expiry, privacy, bounded queue, contention và failures qua fixture. |
| `python -B docs/ai/benchmark/wp06_b4_interop.py` | 0 | 4 passed, 0 failures/errors/skips, `interop.log`; cùng command đạt 4/4 từ source archive của index, `archive-interop.log`. Hai Java windows byte-identical với fixture Python, reducer kiểm timeout và point độc lập, version, population, binding, replay, generation và missing. |
| `cd backend; .\mvnw.cmd -o '-Dincludes=io.micrometer:*' dependency:tree` | 0 | Xác minh Actuator/Micrometer offline, `micrometer.log`. |
| `Get-FileHash -Algorithm SHA256` đối chiếu manifest V1.3 | 0 | 8/8 khớp SHA-256 và byte sizes, bốn file × hai bản artifact hiện hữu, `integrity.json`. |

Diff không đổi valuation, Advisor và security handlers, V1.3, migrations, Caddy/Vite, B1–B3 hay các nhánh song song. Không truy cập protected DB, dataset, holdout hoặc chạy production inference.

## Parallel handoff

Đối chiếu theo merge-base với main baseline. B4 và toàn bộ WP06 đều có 0 file overlap trực tiếp với từng remote dưới đây. Chi tiết ở `.smartprop/wp06-b4-overlap.json`.

| Remote | SHA | Ranh giới khi tích hợp sau |
| --- | --- | --- |
| WP-04 | `58081b4fe4e347adbb313e0d3ccc03d7f4fe514d` | Thay đổi `valuation.py`, `predictor_v1_3.py`, `explanation_v1_3.py`, `AdvisorValuationAdapter.java`, `ValuationService.java` so với main. Commit mới so với SHA producer đã audit `ca9b75b6` chỉ bổ sung báo cáo fixture và blocker migration V2 ở nhánh WP-04. Source producer và mapping provenance giữ nguyên. |
| WP-05 | `a0a5d88db1a77bc3dc55f9981dd313faa52f5b8b` | Optional interval và giới hạn calibration. |
| PR #37 | `151a07b4472ea0fd3134fb50f4f3de757e83d46f` | Giữ route và behavior UI. |
| PR #48 | `287b4b2d032a3d22581fd993e212366c452d7c3a` | Session/auth riêng; dashboard kế thừa revocation ở B6. |
| PR #49 / `integration/pr37-ui-validation` | `33024758a4ee7e01702e4c8bda6049d8bc076075` | Hai ref cùng SHA tại snapshot. Giữ session ownership. |
| PR #41 | `da1d8c34c4303c84996f2f78212793c1f57a4228` | News Backend riêng. |
| PR #43 | `f59edf223c98249ee6104c367c34537bd851aea5` | Có thay đổi ở Vite/Caddy. Giữ Phase 0, RAG PR45 và WP02 evidence khi tích hợp sau. |

Trạng thái bàn giao `WP06_B4_ISOLATED_ADAPTERS_READY`, `WP06_RUNTIME_WIRING_BLOCKED_PENDING_WP04_INTEGRATION`, `WAITING_FOR_WP06_B4_INDEPENDENT_REVIEW`.
