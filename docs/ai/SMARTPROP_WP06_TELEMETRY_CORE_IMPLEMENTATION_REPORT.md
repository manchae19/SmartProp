# WP-06 B0/B1 · Bounded telemetry core

Baseline Phase A `6e25011533ac35d7b0b47780526c0d5273783bf5`, approved main `1c67a279a8ff6f6939767e82bb31b17584610864`. B0 khóa mẫu số và privacy. B1 thêm package độc lập dùng Python standard library. Các producer của production vẫn chưa nối vào package.

## Cấu trúc và dữ liệu

| Module | Trách nhiệm |
| --- | --- |
| `schema.py` | Registry immutable v1, release slot 1 pin V1.3 run `tinix_xgboost_v1_3_integrated`, finite state labels và 22 feature names khớp AST của transform. |
| `accumulator.py` | Integer units, numeric overflow, immutable snapshot, disjoint histogram với sum/count, merge và quantile theo khoảng bucket. |
| `core.py` | Recorder/config dark-off, process-local tickets, bounded health/drop, atomic snapshots và adapters WP‑04/WP‑05. |
| `batches.py` | Sparse binary encoding và FIFO giới hạn count/bytes. Explicit publish một window, không có worker. |
| `reducer.py` | Trusted producer registry, merge idempotent, irreversible watermark, out-of-order/restart semantics, coverage gate. |
| `alerts.py` | State machine trên closed windows để kiểm contract. Config default disabled, không cài rules, scheduling hay notification. |

Registry cấp phát **3.632/4.096 scalar slots**, tính cả disjoint buckets, overflow, sample count/sum, gauges và các counter dự trữ. Dùng `array('Q')` 29.056 bytes payload mỗi recorder/open reducer window. Tối đa 22 × 6 × 20 = 2.640 effective feature series. Global, surface, type, district và mode là các segment riêng, không nhân chéo. Raw/provenance có trục độc lập. Optional adapters dùng status, bounded check/version, provenance counts ≤22, interval scope/fallback, duration µs và width VND/ppm. SHAP tolerance `1e−5` giữ ở upstream WP‑04. Recorder đọc kết quả check đã tính, không rerun. WP‑05 `NOT_ENABLED` và `NOT_AVAILABLE` có state riêng.

Ingress accept tuple label theo đúng thứ tự registry, tối đa ba label/40 ký tự, exact bounded values. Reject extra/unregistered fields, bool trong numeric, float/NaN/Inf, strings và giá trị ngoài bounds. Raw presence/source flags có type bool theo schema riêng. No raw request/response, secrets, user identifiers hoặc exception detail được lưu. Monotonic duration dùng nguyên µs ≤3.600.000.000, count/sum ≤2⁵³−1. Trung gian được validate trước commit toàn bộ delta. Histogram validate count, sum và range có thể đạt. Percentile trả khoảng, final edge có bucket riêng với overflow > edge. Zero denominator là null.

## Lifecycle, snapshot và transport

- `begin` tạo một opaque ticket có owner process và số thứ tự tăng, giữ tối đa 1.024 tickets hoạt động. `finish` chỉ nhận một terminal hợp lệ cho ticket hiện tại. `stop` chốt outstanding dưới một mutation atomic thành interrupted. Duplicate completion chỉ tăng health counter. Snapshot giữ outcome, count, histogram và gauges cùng boundary. `opening + started − completed = in_flight`; `completed = sum(outcome) = histogram.count`. Rotation carry gauge, giữ các delta khác ở đúng window producer. Window rotation từ scheduler tin cậy là việc B2, chưa có wall-clock runtime glue.
- Lock của hot path chờ tối đa 20 ms cho một lần acquire. Health drop lock độc lập, cập nhật fixed counters, cùng được lấy khi tạo snapshot. Critical sections bounded theo array/ticket caps, không I/O. Lock timeout trả failure telemetry và đếm drop, caller tương lai không đổi kết quả giá. Không có bằng chứng MP-safe từ thread tests. Mỗi producer dùng recorder riêng.
- Packet canonical little-endian gồm header 30 bytes với schema/release/population, producer/generation/sequence, timestamps UTC và entry count. Mỗi entry là index u16 + value u64, 10 bytes, index strictly increasing và nil cells bỏ qua. Packet tối đa **36.350 bytes**. Queue validate packet trước retain, tính fixed ring/header/lock và kích thước CPython mỗi bytes object. Cap **512 pending** và **4 MiB retained**, điều kiện nào chạm trước thì từ chối. Một handoff fail tạo gap ở window bị mất và drop reason best-effort vào recorder window kế tiếp. Không retry trong core.
- Một population/reducer. Producer inventory tối đa 32 known slots, một batch/slot/window UTC 60 s. Generation do caller tin cậy đăng ký, sequence bắt buộc `1+(window_start−generation_start)/60`. Dữ liệu reorder trong mười windows mở được nhận. Duplicate digest cùng slot trả duplicate. Một packet khác cho slot đã nhận bị từ chối và window báo conflict. Partial/overlap window không chuẩn, schema/release sai và numeric overflow bị từ chối. Merge integer commutative khi đủ dữ liệu và không vượt cap. Rejection overflow giữ aggregate trước đó và coverage thiếu lô. Không dùng partial aggregate để kết luận.
- Hard ceiling dedupe 4.096 keys, thiết kế inventory/window cho tối đa **320** open keys. Khi chạm cap từ chối key mới và giữ key đã nhận. Seal đóng cả window rỗng, giải phóng keys và tăng watermark không lùi. Old replay trước watermark vẫn bị từ chối sau khi keys hết vòng đời. Restart producer dùng generation mới ở window chưa nhận dữ liệu. Không ghép nửa window cũ/mới. Late packet của generation cũ bị loại, gap vẫn tồn tại. Abrupt stop không tự biến gauge trước restart thành terminal. Reducer restart cần watermark/producer anchors đã xác minh do coordinator nạp. B1 có test reconstruction từ watermark, chưa có durability hoặc distributed failover.

## Completeness và alert lifecycle

Coverage báo expected unique producers và batches từ inventory hoặc unknown, received unique slots, missing, batch coverage, instance coverage, dropped, conflicts, late arrivals tổng reducer tại thời điểm seal, và freshness. Timestamp cũ hoặc dữ liệu không đủ suppress kết luận. Thiếu **một** batch khi đủ min samples vẫn trả `INSUFFICIENT_EVIDENCE`, kể cả các mẫu còn lại đều thành công. Late arrival sau seal không sửa bằng chứng finalized.

Window alerts xử lý strictly increasing closed ends. Duplicate/late giữ nguyên state. Gap reset streaks, active incident trở thành stale. Incompatible reference hoặc coverage không đủ giữ active stale, không recovery. Confirmation/hysteresis và cooldown độc lập. Critical bypass cooldown chỉ cho policy integrity, sau xác nhận theo policy. Điều này giải quyết khác biệt Phase A prototype cho mọi critical bypass. Prototype Phase A được giữ nguyên. Restart với trusted same-policy in-memory checkpoint phục hồi state; cold start báo `NOT_AVAILABLE` tới khi có usable observation. Definition này không xóa incident từ hệ thống bên ngoài. Real drift alerts vẫn OFF vì reference chưa approve.

## Tests và reproducibility

Tất cả chạy trên Python 3.14.6. 29 B1 tests cùng 22 Phase A tests đều pass, 0 fail và 0 skip. Scope gồm concurrent readers/writers, conservation, saturation, privacy, integer overflow, histogram bounds/merge, batch reordering/dedupe/replay, restart, selection bias, alerts, optional states và disabled no-op. Synthetic profile tách khỏi deterministic JSON.

```powershell
Push-Location ai-services
python -B -m unittest discover -s tests -p test_wp06_monitoring_core.py -v
Pop-Location
python -B -m unittest discover -s docs/ai/benchmark -p test_wp06_model_monitoring_benchmark.py -v
python -B docs/ai/benchmark/wp06_model_monitoring_benchmark.py
python -B docs/ai/benchmark/wp06_telemetry_core_profile.py
python -B docs/ai/benchmark/wp06_telemetry_core_profile.py --profile
```

Phase A benchmark 27 × 8 seeds có cùng output SHA-256 `0820d4bb424d19c8660f9d116089e585cc5094fb10701e96fe8a620dc7d58c3c`. B1 deterministic JSON SHA-256 `2b41c39dcdd1ec658c6a1e33d083955922ccb42ea03cad450012db25f9a3eafa`. Digest tính trên output file PowerShell ASCII có CRLF. Git archive reproduction so cùng encoding/interpreter. Logs, exit codes, raw profile và exact remote heads lưu trong `.smartprop/wp06-b1-*` của worktree.

## Performance research

Synthetic bursts gồm 1.500 histogram observations mỗi writer, một reader lấy snapshot đồng thời. Sleep 1 ms giữa nhóm 16 quan sát để lấy mẫu snapshot, ngoài vùng bấm giờ. Đo `perf_counter_ns`; lock timing bao gồm đo instrumentation riêng. Bảng dùng µs, nearest ranks. Snapshot tails có ít mẫu, chỉ mô tả host test.

| Writers | Hot-path P50/P95/P99 | P95 trừ disabled | Lock P50/P95/P99 | Snapshot count và P50/P95/P99 |
| ---: | --- | ---: | --- | --- |
| 1 | 6,3 / 32,2 / 63,5 | 30,3 | 0,6 / 3,2 / 7,6 | 12 · 203,6 / 277,9 / 277,9 |
| 4 | 6,8 / 20,0 / 34,9 | 18,8 | 0,6 / 2,3 / 4,1 | 11 · 165,5 / 205,7 / 205,7 |
| 16 | 6,8 / 20,1 / 30,6 | 19,1 | 0,6 / 2,2 / 3,2 | 18 · 141,7 / 291,7 / 291,7 |
| 32 | 7,2 / 22,3 / 37,2 | 21,4 | 0,6 / 2,4 / 3,7 | 38 · 172,6 / 416,8 / 467,9 |

- Run trên không mất hot-path observation. Run thử ít yield ghi 14 lock drops trên tải 32 writers, được đếm riêng. Unit tests kiểm số observation ghi thành công cộng drops bằng số gọi. Không diễn giải zero drops của một run thành production guarantee.
- Reducer dense merge P50/P95/P99 **3.844,5/5.009,4/5.179,4 µs**. Flood 500 duplicate batches P95 **1.612,3 µs**, không tăng count. Reject flood 2.000 labels và 2.000 numeric inputs, P95 **3,2/3,4 µs** tương ứng. Batch decode/merge là off hot path. Restart và late replay đạt fixtures.
- Khi consumer không drain, buffer dừng ở **115 dense batches và 4.188.333 retained bytes**, hoặc **512 small batches**. Test memory với 1.024 active tickets, queue tối đa và reducer chứa 320 open batches ghi **5.273.336 bytes peak tracer**. Registry được đo tách **742.618 bytes retained**, modeled peak **6.015.954 bytes (~5,74 MiB)**, dưới budget nghiên cứu 8 MiB. Số này mô tả Python allocations trong stress fixture. Không gồm RSS của toàn service, hàng đợi do caller tự tạo hoặc references snapshot mà caller giữ.
- Core P95 delta synthetic ở dưới 2 ms tuyệt đối. Tỷ lệ overhead 5% trên V1.3 và latency end-to-end off/on **NOT_RUN**, thuộc B2/B7. Không có production runtime, DB, Caddy hoặc dataset kiểm ở đây.

## Isolation, integrity và rollback

Phase A giữ đủ 8 tệp, mở rộng 3 tài liệu B0. Các tệp benchmark Phase A giữ nguyên. Production predictor, route/FastAPI lifecycle, Spring/Advisor/auth, frontend, Caddy và migrations không đổi. Kiểm 4 official artifact SHA-256 và byte sizes trên mỗi trong hai bản cục bộ, **8/8** khớp. B0 W20 đã xác minh từ Step 20.11B source. [Metric contract](SMARTPROP_WP06_MODEL_MONITORING_METRIC_CONTRACT.md) · [Privacy governance](SMARTPROP_WP06_MODEL_MONITORING_PRIVACY_GOVERNANCE.md).

B2 insertion map và việc phải chờ WP‑04 ở [implementation plan](SMARTPROP_WP06_MODEL_MONITORING_IMPLEMENTATION_PLAN.md). WP‑04 đã tiến độc lập tới `ca9b75b666f8ba3271bbebade5c5c0ba23267aef` khi kiểm. WP‑05, PR #37 original/integration, PR #41, PR #43 và PR #48 được đối chiếu read-only. Gate dữ liệu thật vẫn đóng. Rollback là giữ config off hoặc revert hai commits B0/B1 qua quy trình được duyệt. Core không có route, background task hay state cần migrate.
