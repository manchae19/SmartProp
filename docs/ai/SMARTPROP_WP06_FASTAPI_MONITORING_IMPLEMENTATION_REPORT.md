# WP-06 B1 hardening và B2/B3 · FastAPI monitoring adapters

Reviewed starting HEAD `c964fd29bb1a03fd3eb66553ef3592a1589f137f`, approved main `1c67a279a8ff6f6939767e82bb31b17584610864`. B1 checkpoint `f24d6206df17c9317150777c7c14e8a10e185d5b`. Diff cuối chỉ trong monitoring package, tests, synthetic profile và ba tài liệu WP‑06. Exact delivery HEAD được lưu trong `.smartprop/wp06-b23-remote.json` sau normal push.

**Trạng thái** `WP06_B2_B3_ADAPTERS_READY` và `WP06_FASTAPI_WIRING_BLOCKED_PENDING_WP04_INTEGRATION`. Có owned-worker adapter và fixtures. FastAPI handlers, startup, predictor, feature engineering, Spring, React và migrations giữ nguyên. Route public giữ nguyên response contract. WP‑04 `ca9b75b666f8ba3271bbebade5c5c0ba23267aef` vẫn ở nhánh riêng đang làm runtime validation. Approved main chưa chứa baseline tích hợp này.

## B1 lifecycle

Terminal loss giải phóng ticket qua bounded active ledger. Finish đã báo intent trước khi tranh main lock nên shutdown có thể nhận biết completed business operation chưa ghi được telemetry. Loss do contention, clock, overflow hoặc exception ở observer giữ riêng `lost_terminal`. Tối đa 1.024 active tickets và tối đa cùng số markers. Late duplicate không tạo observation mới. Một terminal là `completed` với một known outcome và một latency sample, hoặc `lost_terminal` với loss marker. Shutdown chỉ ghi `interrupted` cho ticket còn thực sự mở theo thời điểm đối soát.

Reducer so opening/closing per producer per generation. Chỉ giữ metadata của 10 open windows và slot đã seal gần nhất. Out-of-order được đối soát ở seal. Gap, conflicts, mismatch và known terminal loss ngăn kết luận. Replay vẫn bị watermark từ chối sau khi dedupe key đã giải phóng. Cross-generation không buộc gauge khớp. Finalized window không bị sửa khi packet kế tiếp tới muộn. [B1 hardening](SMARTPROP_WP06_TELEMETRY_CORE_IMPLEMENTATION_REPORT.md).

## B2 scope thực tế

| Thành phần | Hợp đồng |
| --- | --- |
| `fastapi_adapter.py` | Một recorder cho một worker và một population đã cấu hình. Operational, input quality, drift, explanation, interval và exporter có flags riêng mặc định false. No scheduler thread, exporter protocol, extra model startup hoặc endpoint registration. |
| `artifacts.py` | Bốn tên, sizes và SHA‑256 trùng manifest chính thức. Kiểm explicit release directory đọc theo stream, mỗi block ≤64 KiB. Tests chỉ gây lỗi trên disposable copies. Artifact check outcome và model load outcome là hai metric khác nhau. |
| Readiness | Process reachable, FastAPI lifespan ready và model ready độc lập. Fixture gọi function `app.api.valuation.health` thật với app-state giả. HTTP 200 `model_ready=false` cho process/app ready và model not_ready. Chỉ đọc fields status/version/ready, bỏ qua reason, paths và exception. Unsupported version, validation, schema/calibration mismatch, file missing, artifact invalid và load failure dùng enum. |
| API và point | Lifecycle riêng `api_request` và `invocation`. API admission đếm bao gồm validation hoặc model unavailable. Ticket point bắt đầu ở call chính, kết thúc bằng validated positive integer VND và model `v1.3`, invalid output, inference exception hoặc interruption. Options/health, stage timing và optional explanation có counters riêng. Timeout upstream không được coi là point exception. |
| Timings | Lifecycle histograms đo total AI request và observed invocation. Stage hooks dùng monotonic ns → integer µs và đo riêng model load, adapter, feature prep, point, calibration, options/health. Explanation duration dùng adapter optional với check đã được tính. Không rerun inference hoặc TreeSHAP. Histogram merge cộng counts/sums. |
| Optional contracts | WP‑04 mapping cho status, contract version `1.0`, aggregate provenance và reconstruction pass/fail. Giữ tolerance upstream `1e−5`. WP‑05 trả `NOT_ENABLED`; chưa có calibration hoặc interval issuance. |

### Attribution và population

Isolated adapter nhận route enum từ **server at hook insertion point**. Primary `/predict`, preview `/predict/v1_3_preview`, internal `/api/internal/v1_3/predict` và historical compatibility là bốn population IDs riêng. Canonical/compat-real/compat-legacy còn là input mode cho quality, không tự quyết định nguồn người gọi. Một worker/recorder chỉ nhận population cấu hình. Population khác cần recorder cô lập có budget riêng được duyệt trước khi chạy đồng thời. Không dựa vào body, query hoặc header từ client để gắn surface. B2 giữ `unattributed` cho API/invocation/stages và không tạo Standalone/Posting/Advisor surface denominator. Attribution đầy đủ cần B4.

### UTC coordination và failure isolation

Trusted coordinator cung cấp wall-second và monotonic ns. UTC windows cố định 60 s. Begin ở giữa phút là partial. Chỉ publish window đủ, liên tục và được đóng tại boundary theo wall-second. Skipped/delayed boundaries hoặc wall jump vượt 2 s so với monotonic làm mất cửa sổ không chắc chắn. Khi clock regress, giữ anchor trước đó và không publish lại slot cũ. Số sequence đi theo UTC minute kể từ generation anchor, nên enqueue thất bại tạo gap thay vì reuse sequence. Shutdown đối soát local ledger và không publish partial. Reducer hiện tại nhận batch thủ công vào memory. Sau khi được phép wiring, scheduler phải phối hợp boundary trước khi ghi observation thuộc phút mới và kiểm scheduling jitter ở runtime. B1/B2 không có durability qua crash.

Hot-path adapter dùng zero wait trên primary recorder lock. Health critical sections và metadata reconciliation có upper bound, không có I/O. Các observer lỗi chỉ ghi drop reason bounded khi còn khả năng ghi. Fixtures kiểm recorder exception, lock busy, invalid numeric, overflow, collector outage, queue full, scheduler failure và shutdown. Actual HTTP success/parity không suy từ fixture. Registry v3 có **3.986/4.096 scalar slots**, caps 512 pending hoặc 4 MiB, 32 producers, 10 open windows và ≤320 open keys. Max packet **39.890 bytes**.

## Đối chiếu overlap và bản đồ B4

| File | WP‑04 so với approved main | B2/B3 hiện tại hoặc B4 cần review |
| --- | --- | --- |
| `ai-services/main.py` | Không đổi | Sau khi được phép, một recorder per worker từ lifespan và quan sát load/ready. Giữ public startup semantics. |
| `app/api/valuation.py` | Có thay đổi | Admission, route enum, observed validation và timing. Phối hợp WP‑04 trước khi thêm hooks. |
| `app/api/valuation_v1_3.py` | Không đổi | Internal population riêng, auth guard hiện có. Metadata diagnostics không được gán primary. |
| `predictor_v1_3.py` | Có thay đổi | Marker ngay tại actual point call, calibration timing, valid output. Chờ baseline WP‑04 và golden parity. |
| `adapter_v1_3.py`, `features_v1_3.py` | Không đổi | Truyền typed facts từ adapter/transform khi được phép. Không thay thứ tự hay engineering. |
| `explanation_v1_3.py` | WP‑04 thêm producer | Chờ hợp đồng tích hợp duyệt trước khi lấy derived metadata. |
| `ValuationController.preview` → `ValuationService.preview` → `ValuationClient.exchange` | B4 | Controller sở hữu Posting surface, service sở hữu opportunity, client sở hữu dispatch/retry/timeout. `/valuation-options` tách denominator và giữ principal/role. |
| `AdvisorController.consult` → `AdvisorOrchestrationService` → `AdvisorValuationAdapter.evaluate/exchange` | B4 | Một consult, zero-to-many candidates, eligible/skip theo candidate, một dispatch cho mỗi lần gửi thực. Probe options riêng. Request failure upstream không đổi kết quả FastAPI. |
| Standalone proxy và trusted B4 correlation | B4 | Chỉ route identity từ edge/peer đã xác thực. Strip client claim, không log ID hay payload. Giữ riêng Standalone surface và FastAPI admission. |

## Lệnh và evidence cuối

```powershell
Push-Location ai-services
python -B -m unittest discover -s tests -p 'test_wp06*.py' -v
Pop-Location
python -B -m unittest discover -s docs/ai/benchmark -p test_wp06_model_monitoring_benchmark.py -v
python -B docs/ai/benchmark/wp06_model_monitoring_benchmark.py
python -B docs/ai/benchmark/wp06_telemetry_core_profile.py
python -B docs/ai/benchmark/wp06_telemetry_core_profile.py --profile
```

- **56/56 WP‑06 tests** (29 B1 gốc, 11 lifecycle, 9 B2, 7 B3), **22/22 Phase A**. 0 fail, 0 skip, exit 0. Test foundation riêng trên archive của reviewed SHA **29/29**, digest v1 `2b41c39dcdd1ec658c6a1e33d083955922ccb42ea03cad450012db25f9a3eafa` đúng. B1 hardening v2 digest ghi trong báo cáo core. Fixture deterministic schema v3 `a094cd890d870b67d11124f122d8352236bc59df2b3d46bea853b34e6735594a` đổi vì registry layout và packet version. Phase A benchmark vẫn `0820d4bb424d19c8660f9d116089e585cc5094fb10701e96fe8a620dc7d58c3c`.
- Lock-probe cục bộ 10 lần forced contention mỗi chế độ. Timeout cấu hình 20 ms có median đo **31,371 ms**, max **33,9964 ms** trên host. Zero wait median **0,0028 ms**, max **0,0073 ms**, mỗi chế độ ghi đủ 10 drops. Do đó timer configured 20 ms không bảo đảm budget absolute 2 ms ở contention. Đây là kiểm thử core, không suy luận thêm P95 overhead của inference.
- Profile core v3 với 1/4/16/32 writers có added P95 isolated **18,6 / 14,9 / 14,8 / 14,6 µs**. Queue đạt **104 dense packets / 4.156.280 retained bytes**, hoặc 512 sparse packets. Traced peak cộng static registry là **6.295.037 bytes (~6,00 MiB)** khi giữ 320 open batches. Đây là allocation của fixture và chưa bao gồm RAM/runtime inference.
- **8/8** artifact hashes và byte sizes trên hai bản local khớp. Official feature manifest khớp exact 22 features theo thứ tự. Code và các deployment bindings ngoài monitoring package có diff 0. Không chạy protected database, datasets hoặc real user telemetry.
- **NOT_RUN** vì wiring bị chặn. Actual FastAPI HTTP monitoring, production golden price parity, actual single invocation/no extra model or SHAP, full FastAPI serial, RAG regression và production off/on overhead (absolute 2 ms, relative 5%, memory 8 MiB) chưa có evidence.

Rollback giữ flags off, chưa có persistent state. Nếu revert implementation, đọc packet schema tương ứng, không trộn v1/v2/v3 cùng reducer. Chờ WP‑04 tích hợp và phối hợp trước khi mở wiring. [B3 và drift](SMARTPROP_WP06_INPUT_QUALITY_DRIFT_REPORT.md).
