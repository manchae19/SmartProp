# WP-06 · Kiến trúc và chính sách cảnh báo đề xuất

## Phương án

| Phương án | Phù hợp và chi phí vận hành |
| --- | --- |
| A. Logging hiện có + bounded in-process metrics | Phase B đầu tiên có thể dùng counter/histogram nội bộ, schema allowlist và batched reducer. Ít dependency, nhạy restart. Log chỉ là chẩn đoán bằng reason code, không suy ra denominator hoặc percentile từ sampled logs. Private merge theo schema, offset/reset và producer generation. |
| B. Prometheus-compatible | Nếu Ops có scraper nội bộ, expose đường riêng trên loopback/private network, dùng counter và histogram chung edges. Multi-instance sum đạt semantics khi xử lý reset, content negotiation và target churn. Cần storage, scrape RBAC, retention và hard network budget. Chưa có exporter production được xác minh. [Prometheus](https://prometheus.io/docs/practices/histograms/). |
| C. Actuator và Micrometer | Spring đã có Actuator, chỉ health được cấu hình expose. Dùng MeterRegistry hiện có cho Java nếu B0 xác minh, giữ FastAPI writer riêng với contract tương thích. Prometheus registry là lựa chọn triển khai sau phê duyệt và cần check classpath/network gate. [Spring Boot](https://docs.spring.io/spring-boot/reference/actuator/metrics.html). |
| D. OpenTelemetry | Phù hợp nhiều service/instances khi cần private collector, histogram temporality và đường correlation có kiểm soát. Thêm agent/SDK, trace sampling, cost/network/privacy review. Deferred đến khi cần. [OTel SDK](https://opentelemetry.io/docs/specs/otel/metrics/sdk/). |
| E. Internal dashboard projection | Đọc aggregates đã duyệt qua server authorization, gồm suppression và freshness. Không query trực tiếp model metrics từ trình duyệt. Có thể triển khai sau A hoặc trên B/C. Cần quyền truy cập, review revocation và retention. |

Chọn **A cho FastAPI và C cho các counters Java tương thích đã có**, với schema histogram portable để tích hợp B khi Ops phê duyệt. E dựa vào aggregate snapshot. D chưa cần. Routing browser→AI hoặc Spring→AI giữ nguyên.

## Dòng dữ liệu và failure isolation

1. Chỗ xử lý chính gửi observation nhỏ, enum và numeric boundary đã validate. Giá point computed một lần như cũ. Giữ payload và auth ngoài recorder, không dùng lại call để bổ sung missing telemetry. Đo elapsed monotonic từng stage qua timer stop trong finally. Handler gọi wrapper local bounded, ghi tối đa một terminal outcome. Sync exception của telemetry được cô lập và ghi drop counter best-effort. Không widen scope sang data pipeline hoặc thêm inference.
2. Producer giữ immutable schema registry. Buffered fixed-size counters hoặc bounded non-blocking enqueue, flush ngoài prediction thread. Khi đầy, bỏ quan sát theo policy, tăng dropped counter dự trữ và đánh dấu coverage. Giá trị NaN, infinity, âm, out-of-range hay unregistered rớt sớm. Output đồng bộ point không đợi IO, retry hay dashboard availability. Kiểm số thread/worker và bound số timeseries theo privacy design.
3. Reducer nhận batch idempotent theo generation/sequence, merge bucket counts đúng schema và population, tránh cộng lại scrape cumulative counters. Giữ active state nhỏ, batch retry bounded, TTL và độc lập với point deadlines. Không dùng shared local file làm lock qua process. Sau crash hoặc drift clock, mark window incomplete và chờ enough aligned batches. Correlation ephemeral, dùng cho đối soát edges chứ không đếm unique users.
4. Separate circuit theo module/options/explanation/interval/observability. Monitor không tự bật Shadow, fallback V6, retry point, disable model hoặc đổi giá. Nếu điểm đã thành công mà optional WP‑04/WP‑05 lỗi, chỉ ghi trạng thái optional, giữ point. Trên main hiện tại TreeSHAP còn inline nên isolation đầy đủ là điều kiện phụ thuộc integration WP‑04. WP‑05 có thể hoàn toàn disabled trong pilot.

## Chính sách alert để thử ở Phase B

Các số dưới đây là **ứng viên thử nghiệm**, sẽ được duyệt sau baselines thật. Dùng release+signal+surface/partition key với allowlist, chỉ một incident đang mở mỗi key, có owner và nguyên nhân bounded. Warning khi vượt ngưỡng 2 window đủ mẫu liên tiếp, critical khi vượt critical 2 window hoặc integrity mismatch xác thực. Recovery cần 2 window dưới ngưỡng recover riêng, cooldown minh họa 2 window sau recovery. Critical integrity mới được bypass cooldown. Dữ liệu thiếu làm reset streak, giữ incident đang mở ở trạng thái stale, không gửi recovery giả. Dedupe notifications và cảnh báo availability nhiều tầng chung một incident khi root cause đã xác minh.

| Nhóm | Ứng viên chạy shadow alert nội bộ được duyệt ở Phase B | Recovery và điều tra |
| --- | --- | --- |
| Service unavailability | Cả hai probe loopback trong 2 phút fail hoặc majority ready giảm đến 0 trên inventory biết được. Mismatch manifest đã kiểm ngay critical. Một probe missing là monitoring gap riêng. | 2 lần ready + consistent inventory, so process log và model ready. Artifact recovery cần deploy bản pin được duyệt. |
| Prediction failures và timeout | Trên 5 phút >=100 terminal eligible opportunities, warn trên baseline +5 pp, critical +15 pp ở 2 window. Phân loại stage trước khi mở incident. Omit model-failure gauge khi chỉ có UI timeout. | Recover dưới baseline +2 pp 2 window; đối chiếu options requests, late completion và exporter drops. |
| Latency | P95 vượt SLO theo surface hoặc 1.5× baseline kèm absolute floor, critical 2×. Min n dựa trên tail uncertainty, ví dụ >=200 cho P95 và >=1.000 cho P99 descriptive. Chỉ báo điểm `>bucket` nếu overflow, kèm count. | Recover dưới 1.2×/SLO trong đủ window; phân biệt saturation, model stage, projection, edge. |
| Missingness, unknown | >=200 applicable, delta +10 pp và một baseline confidence band được duyệt cho pilot. Critical +20 pp khi sustained trên nhiều cửa sổ. | Recover <+5 pp và xác minh không đổi mode/applicability. Kiểm raw vs effective, district/type mix. |
| Unlabeled drift | JS histogram và delta per feature/price, W1 kiểm sensitivity. Fixed reference compatible, hai sample sizes >=200, composite effect + null-watermark guard. Chạy advisory warning, chưa tự paging critical chỉ do unlabeled drift. | 2 cửa sổ dưới ngưỡng recover đã preregister. So fixed và rolling, stratified mix, baseline seasonality, missingness và telemetry gaps. |
| WP‑04 reconstruction | Warn theo reconstruction failures / eligible checked, volume tối thiểu và sustained, ví dụ >=100 và >1% trong 2 cửa sổ. Contract version mismatch giữ deployment review, tolerance vẫn 1e−5. | Valid contract, reconstructable count đủ và không tăng fail. Dùng internal test, không xuất factors. |
| WP‑05 invalid intervals | Bất kỳ artifact mismatch confirmed hoặc trả bound invalid nên triage ngay. Rate of failures trên calculation attempts và `NOT_ENABLED` riêng. | Chứng minh contract version, inventory consistency và zero invalid trên đủ issued. Point vẫn chạy khi interval tắt. |
| Delayed quality | Chỉ với observed labels hợp pháp. Predeclare effect tối thiểu và bootstrap precision, ví dụ MAPE +5 pp hoặc empirical coverage −5 pp với 2 mature cohorts và minimum label match rate. Chưa có nhãn → `NOT_AVAILABLE`. | Validate match rate, modes, population shift và missing labels. Compare same target, no ad-hoc percentile mixing. |

Synthetic benchmark dùng cửa sổ rời, fixed thresholds riêng, route metrics tính đúng denominator mẫu nhỏ. Ổn định thresholds giai đoạn review audit bằng observed null windows, A/A, incident replays synthetic hợp lệ, rare-event rate uncertainty, báo FPR theo cảnh báo và theo family. Không gửi external notifications ở Phase A. [Benchmark WP‑06](SMARTPROP_WP06_MODEL_MONITORING_BENCHMARK_REPORT.md).

## Dashboard nội bộ dự kiến

Wireframe nội dung tiếng Việt, dùng verified snapshot của collector và server RBAC.

| Khu vực | Chỉ số và trạng thái đọc |
| --- | --- |
| Trên cùng | “Phiên bản mô hình”, “Mô hình sẵn sàng”, “Kiểm tra artifact”, “Lần cập nhật”, “Tỷ lệ telemetry nhận được”. Mỗi badge có text, time scope và reason, không dựa riêng vào màu. |
| Lưu lượng và hiệu năng | “Yêu cầu định giá”, “Tỷ lệ trả giá hợp lệ”, “Từ chối đầu vào”, “Hết thời gian chờ”, P50/P95/P99 với n và surface/chặng. Hỗ trợ focus bàn phím, responsive, không công bố data nhỏ. |
| Dữ liệu đầu vào và drift | “Thiếu dữ liệu”, “Giá trị ngoài từ điển”, “Phân bố giá dự đoán”. Cảnh báo drift mang nhãn “Tín hiệu thống kê”, n/current/reference, method và sample coverage. |
| Optional | “Khả dụng giải thích” với trạng thái WP‑04. “Khả dụng khoảng dự đoán” với trạng thái “Chưa bật” hoặc reason đủ quyền. Không tạo giá trị giả khi unavailable. |
| Chất lượng trễ và sự cố | “Chưa có nhãn giá rao được duyệt” khi thiếu labels. Khi approve hiển thị MAE/MAPE/W20, coverage, tail misses với thời gian và n. “Cảnh báo gần đây” chỉ aggregate incidents và owner. Synthetic preview có banner “Dữ liệu mô phỏng”. |

## Budget, kiểm chứng và rollback

Đề xuất so flag off/on trên exact same release, đồng thời 1/4/16/32 synthetic requests, đủ repeated runs, monitor stale/down, 4 KiB event tối đa, exporters blocked, reservoir cap, process restart và overload. Kiểm point V1.3 bitwise integer parity trên mọi surface, contract, ciphertext/credentials scan, no I/O on hot path, exact single inference, histogram merge và no data escaping. Gate đề xuất `added p95 <= 2ms and <=5%`, p99 báo riêng, steady memory `<=8 MiB` mỗi worker riêng telemetry và drop rate có cap dựa coverage budget. Phase A chỉ đo calculation/collector synthetic offline. Chưa chứng minh production overhead.

Runtime flags độc lập mặc định off, allow rollback collector/exporter/dashboard trước. Disable telemetry ở edge/Java/AI tương thích, giữ point metrics unavailable khi không có data. Nếu schema/boundary sai, đóng incompatible window, quay lại release schema đã duyệt và re-approve any rebuilt reference. Rollback collector không thay predictor, không bật Shadow hoặc mở quyền. Khi cần rollback optional contract, theo WP‑04/05 flags và bảo toàn V1.3.
