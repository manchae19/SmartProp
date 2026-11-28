# WP-06 · Benchmark giám sát synthetic

Mọi dòng, nhãn, category và timing fault được sinh trong bộ nhớ. Không gọi V1.3, DB, HTTP hoặc dịch vụ ngoài. Mục tiêu là kiểm chứng phương pháp, không suy ra production detection rate hoặc overhead.

## Protocol

- 8 seeds `6,17,33,61,97,129,241,809`. 27 kịch bản, 12 window mỗi run, tổng **216 runs / 2.592 windows**. Cửa sổ thông thường có 256 logical opportunities chia ba surface synthetic. Sparse/empty còn 12/0 opportunities trong injection. Reference riêng có 512 observations trước mỗi run, RNG khác dải seed với current. Paired scenario reuse random numbers để so tín hiệu trên luồng xác suất chung, nên negative runs trong cùng seed có tương quan.
- Bốn phương pháp so **cùng** model outputs eligible từng window: PSI/JS trên fixed price bins 1/2/3/4/5/6/8/10 tỉ synthetic + overflow, KS/W1 trên ECDF sample. Type/district dùng JS trên finite categories + UNKNOWN. Prototype nhận một feature state per valid observation và một latency boundary. Production contract có nhiều boundary và 22 feature riêng. Tỷ lệ fail synthetic loại validation/skip/cache khỏi eligible terminal attempts. Case missing telemetry biết expected count từ driver và đo gap riêng.
- Warning/critical/recover của drift lần lượt là PSI `.10/.26/.065`, JS `.019/.05/.013`, KS `.15/.27/.115`, W1 `.30/.80/.23` tỉ synthetic và categorical JS `.035/.10/.021`. Min n=100 cho drift/reference và các rate đủ mẫu. Alert confirmation 2 windows, artifact mismatch immediate. Cooldown 2 windows với critical bypass. Xem ngưỡng các tín hiệu khác trong mã. Các giá trị này là knobs của kịch bản, chưa được calibrate.
- Incident thường bắt đầu window 3 và kết thúc trước window 8 theo chỉ số 0-based. Spike dừng trước window 5. MAPE có lag 2 hoặc 4 windows tùy scenario. Một hit khi nhận transition warning/critical trong injection với đúng target signal. Detection rate=TP/positive runs, FNR=FN/positive runs, FPR=negative runs có ≥1 transition / all negative runs. Alerts bên ngoài khoảng injected trong positive run được đếm riêng. Delay tính từ cửa sổ đầu có thể quan sát signal, recovery tính từ cửa sổ đầu sau signal dừng, chỉ lấy lần recover đầu sau detection. End of run có thể censor recovery.

## Drift trên cùng mẫu

| Scenario (n=8 mỗi dòng) | PSI hits | JS hits | KS hits | W1 hits |
| --- | ---: | ---: | ---: | ---: |
| Shift giá mạnh | 8 | 8 | 8 | 8 |
| Drift giữ nguyên MAPE | 8 | 8 | 8 | 8 |
| Shift yếu +0,24 tỉ | 0 | 0 | 1 | 1 |
| Tăng variance ×1,45 trên độ lệch | 7 | 7 | 0 | 8 |
| **Tổng detection / 32 positive runs** | **23 / 32** | **23 / 32** | **17 / 32** | **25 / 32** |
| Detection rate / FNR | 71,88% / 28,12% | 71,88% / 28,12% | 53,12% / 46,88% | 78,12% / 21,88% |
| FPR trên 184 negative runs | 23/184 (12,50%) | 23/184 (12,50%) | 0/184 | 0/184 |
| Alert transitions / ngoài injection ở positive run | 53 / 4 | 52 / 4 | 17 / 0 | 25 / 0 |
| Insufficient signal-windows | 80 | 80 | 80 | 80 |
| Median detection / recovery delay | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |

Kết quả phụ thuộc bins, effect sizes, threshold và sample sizes. W1 mạnh ở variance case này, KS nhạy gần nơi ECDF tách nhiều nhất và bỏ phần lớn shift phân tán. JS/PSI phát alert ở null conditions do các tail bins và sample noise dưới rule nghiên cứu. Không ưu tiên một phép đo duy nhất dựa vào bảng này. Có thể dùng JS nhẹ để screening cộng W1 để chẩn đoán, và điều chỉnh threshold bằng serving reference đã duyệt.

## Operational và lifecycle

| Signal | TP/positive | FP/negative | Alerts | Insufficient | Median detect / recover |
| --- | ---: | ---: | ---: | ---: | --- |
| Artifact mismatch | 8/8 | 0/208 | 8 | 0 | 0 / 0 |
| Latency (gradual và spike) | 16/16 | 0/200 | 24 | 80 | 1,5 / 1 |
| Timeout | 8/8 | 0/208 | 8 | 80 | 1 / 1 |
| Model unavailable | 8/8 | 0/208 | 8 | 80 | 1 / 1 |
| Inference exceptions | 8/8 | 0/208 | 8 | 80 | 1 / 1 |
| Missing feature | 8/8 | 0/208 | 8 | 80 | 1 / 1 |
| Unknown category | 8/8 | 0/208 | 10 | 80 | 1 / 1 |
| Categorical type JS | 16/16 | 0/200 | 17 | 80 | 1 / 1 |
| Categorical district JS | 8/8 | 0/208 | 10 | 80 | 1 / 1 |
| Explanation unavailable | 8/8 | 0/208 | 8 | 80 | 1 / 1 |
| Reconstruction failures | 8/8 | 0/208 | 8 | 80 | 1 / 1 |
| Invalid intervals | 8/8 | 0/208 | 8 | 80 | 1 / 1 |
| Missing/invalid telemetry gap | 16/16 | 0/200 | 16 | 40 | 1 / 1 |
| Delayed MAPE | 8/8 | 0/208 | 8 | 528 | 1 / 1 sau khi có nhãn |

Mỗi signal trong bảng có FNR 0 trên fault injection đã thiết kế. **296** transitions và **1.768** insufficient signal-windows trên toàn bộ methods. Warning nâng critical vẫn cùng incident và thêm một transition. 24.576 duplicate events bị loại trong từng case duplicate và concurrent. Ước lượng delayed-label case có 13.698 labels match trên 15.066 opportunities đã mature (90,92%) tới cuối mô phỏng. Invalid numeric case từ chối 2.890 events. Sparse và empty suppress drift trong toàn bộ 40 windows injection mỗi scenario. Một số alert JS/PSI ở các window bình thường bao quanh sparse/empty vẫn tính vào FPR. Case interval `NOT_ENABLED` không tạo interval invalid alert.

## Negative controls

| Population synthetic | Mean price JS | Mean delayed MAPE |
| --- | ---: | ---: |
| Healthy control | 0,008268 | 4,41265% |
| Price distribution drift, giữ relative error | 0,126257 | 4,41265% |
| Cùng phân bố feature và prediction, chỉ đổi conditional outcome | 0,008268 | 35,41279% |

Large drift kích hoạt đủ candidates trong case một. Case hai có **MAPE hits 8/8** sau label lag, với marginal drift statistic bằng control theo cùng window/seed. Hai case dùng label generator có chủ đích và không thiết lập quan hệ causal ngoài benchmark.

Negative control nhỏ mẫu dùng 320 IID window thử mỗi n, với các mẫu con paired. Raw vượt ngưỡng warning một lần ở n=12 lần lượt **PSI 320, JS 318, KS 303, W1 293**. Với n=256 là **2, 4, 0, 0**. Min-n gate đánh dấu 320/320 các window n=12 là insufficient trước khi làm confirmation. Đây là raw cutoff exceedance, khác run-level FPR sau confirmation trong bảng trên.

## Cost và bounds

Profile cục bộ với Python 3.14.6, 300 repeats với 256 vs 256. Median histogram+PSI/JS **245,75 µs**, sorted ECDF+KS/W1 **531,55 µs**, gồm binning hoặc sort. Prototype quan sát tối đa **39** series, theoretical ceiling **90** theo dimension trong code, và dedupe cap **256** IDs mỗi window. `tracemalloc` chỉ đo collector với 1.000 lần tạo/hủy window sequential. Live bytes sau 10/100/1.000 windows là **12.400 / 12.424 / 12.520**, peak **14.664** bytes. Số này không gồm process RSS, network, 22 features production, queue export hoặc chạy concurrent model.

## Tái lập

```powershell
python -B -m unittest discover -s docs/ai/benchmark -p test_wp06_model_monitoring_benchmark.py -v
python -B docs/ai/benchmark/wp06_model_monitoring_benchmark.py
python -B docs/ai/benchmark/wp06_model_monitoring_benchmark.py --profile
```

**22 tests, 0 failures, 0 skips, exit 0**. Test prototype gồm mẫu số và đồng thời cùng process, malformed/invalid numeric, zero bins, JS symmetry, percentile bucket/reset assumptions, sparse/references, alert transitions, dedupe/cardinality và cả hai hướng negative control. Reproducibility kiểm byte-level JSON với cùng interpreter. Profiling có timing biến thiên và tách khỏi deterministic JSON. Correlation nhiều process, inference parity, runtime auth và alert integrations thuộc Phase B. [Research prototype](benchmark/wp06_model_monitoring_benchmark.py) · [Tests](benchmark/test_wp06_model_monitoring_benchmark.py) · [Proposed alerts](SMARTPROP_WP06_MODEL_MONITORING_TECHNICAL_DESIGN.md).
