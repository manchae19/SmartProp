# WP-05 — Benchmark khoảng dự đoán tổng hợp

**SYNTHETIC_METHODOLOGY_ONLY.** Python standard library, seed chính `20261128`, seed sensitivity `20261129`. Có bốn residual laws, ba mức nominal 80/90/95%, mười phương pháp và ba population đánh giá mỗi tổ hợp. Benchmark không nạp V1.3 và không dùng lịch sử residual hay dữ liệu thị trường. [Benchmark source](benchmark/wp05_prediction_interval_benchmark.py) · [Research tests](benchmark/test_wp05_prediction_interval_benchmark.py)

## Protocol và data-generating process

- Đóng băng công thức dự đoán tổng hợp, fixed half-width 25/40/55%, tail allocation 35/65 và chính sách group trước khi đánh giá. Với mỗi residual law và vai trò, sinh pseudo-random stream độc lập theo seed, scenario và role. Mỗi law có 700 entity development, 2.400 calibration, 1.800 exchangeable-reference evaluation, 1.800 temporal stress và 1.800 geographic stress. Raw counts tương ứng là 742, 2.542, 1.906, 1.906, 1.906. Development dùng cho kiểm tra setup và thống kê mô tả; chỉ calibration được phép tạo cutoff. Evaluation dùng so sánh nghiên cứu trên DGP đã công bố; sensitivity là lần lặp độc lập synthetic, chưa có final holdout thật.
- Type theo HOUSE/LAND/APARTMENT/VILLA với trọng số 52/26/19/3. District gồm cả bảy giá trị artifact. Giá điểm lấy lognormal theo type có median khoảng 6,2/4,7/3,8/16 tỷ VND và log sd 0,78. Nhóm giá suy từ point, với ngưỡng synthetic 4 và 12 tỷ. Missing count 0–3, unknown category 5% khi complete và 20% nếu thiếu. Các group biến động tự nhiên theo từng seed.
- **Additive.** Normal residual VND có sd 0,95 tỷ và target floor synthetic 1 triệu. **Skewed.** Log residual gồm normal sd 0,13, exponential rate 1 trừ 0,55 rồi nhân 0,21, và +0,12 log ở high predicted band. **Heavy tail.** Hỗn hợp normal sd 0,16/0,78 với 9% ở thành phần rộng, và shocks ±1,8 log trên 1,5% quan sát. **Heteroskedastic.** Log scale tăng theo high-price, VILLA và unknown. Mỗi missing feature tăng scale ở HOUSE và giảm scale ở LAND. Điều này kiểm việc giả định chung “càng thiếu càng bất định” có thể cho kết quả sai. Công thức và trọng số nằm trong source.
- Temporal control dùng lứa entity mới, thêm (N(0.39,0.16^2)) lên log của giá target. Geographic control chuyển thêm 72% draw sang hai district cuối và thêm (N(-0.32,0.26^2)) cho target ở hai district đó. Negative control geography đổi cả covariate mix và (Y|X), vì vậy không thể quy sai biệt cho pure covariate shift. Partitions có thời hạn snapshot/label không chồng và feature timestamp không muộn hơn inference. Time labels của tập reference giữ chung DGP với calibration.
- Mỗi entity thứ 17 có synthetic repost với listing alias. Validate khóa observation, entity, listing, repost, source, clock và frozen prediction signature trước khi chọn quan sát đầu bằng snapshot time và observation ID. Một unit mỗi entity tránh pseudoreplication. Tests đưa lỗi vào từng khóa, role, thời điểm, source và signature. Metadata integrity giả định role và danh tính không bị giả mạo. Biến đổi y sau khi lập inputs không thay đổi group hoặc interval.

## Cách đọc metric

Mọi phương pháp nhận cùng evaluation entity theo scenario/role. Coverage và Wilson 95% tính trên số interval được phát; `covered_fraction_all` dùng toàn bộ n để phản ánh abstention. Width mean/median/P90, median relative width `(U−L)/p`, tail miss và interval score đều báo theo interval được phát. Interval score bằng width cộng (2/\alpha) lần độ hụt ngoài bound. Diễn giải score trên common offered population khi availability khác nhau. Wilson là uncertainty binomial mô tả trên evaluation entities sau khi giữ cutoff cố định; nó không bao gồm bất định tái lấy mẫu calibration, multiplicity hay causality. [Gneiting và Raftery, 2007](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf)

JSON xuất đầy đủ nominal, calibration/global/group counts, evaluation/offer counts, coverage error, Wilson, mean/median/relative/P90 width, hai tail miss, score, insufficient, fallback và invalid rates cho cả 360 tổ hợp và các subgroup theo type, district, predicted band, missing count, unknown và type×band. Values unavailable là JSON null. Chi tiết lệnh và đường dẫn output ở cuối.

## So sánh chính ở mức danh nghĩa 90%

Ô là **coverage % / median width tỷ VND** trên 1.800 evaluation entity mỗi law. Fixed baseline có danh nghĩa chỉ để đối chiếu.

| Phương pháp | Additive | Skewed | Heavy tail | Heteroskedastic |
| --- | ---: | ---: | ---: | ---: |
| Fixed relative | 87,6 / 4,43 | 83,1 / 4,33 | 93,0 / 4,44 | 97,1 / 4,34 |
| Absolute | 91,6 / 3,17 | 90,4 / 10,59 | 88,7 / 6,00 | 88,6 / 4,84 |
| Relative conformal | 91,1 / 5,28 | 91,2 / 6,64 | 89,8 / 3,56 | 88,0 / 2,90 |
| Log | 91,2 / 5,75 | 91,1 / 5,38 | 89,3 / 3,59 | 87,6 / 2,92 |
| Asymmetric log | 91,4 / 5,59 | 92,2 / 5,51 | 89,9 / 3,58 | 88,1 / 2,92 |
| Log by type | 91,7 / 5,80 | 91,2 / 5,39 | 87,9 / 3,44 | 88,1 / 2,84 |
| Log by predicted band | 91,3 / 4,01 | 91,4 / 4,99 | 89,1 / 3,38 | 87,8 / 2,73 |
| Log type×band with fallback | 91,9 / 4,36 | 91,2 / 5,09 | 88,9 / 3,29 | 87,9 / 2,64 |
| Log type×band with abstention | 91,2 / 4,12 | 91,3 / 4,73 | 89,0 / 3,04 | 88,1 / 2,46 |
| Fixed-scale adaptive log | 91,4 / 5,86 | 91,2 / 5,10 | 88,5 / 3,40 | 88,4 / 2,81 |

Log tại 80/90/95% cho additive 80,1/91,2/96,5%, skewed 81,4/91,1/96,2%, heavy tail 77,8/89,3/94,8% và heteroskedastic 78,1/87,6/94,4%. Seed sensitivity ở nominal 90 tương ứng 89,2/89,5/91,3/89,2%. Một lần calibration và evaluation có thể dưới nominal ngay cả khi DGP exchangeable; bảo đảm split conformal lấy trung bình qua calibration và quan sát mới.

Absolute có median width 3,17 tỷ, interval score trung bình 3,75 tỷ ở additive, so với log 5,75 và 8,89 tỷ. Với skewed, absolute median 10,59 tỷ so với log 5,38 tỷ. Asymmetric giảm upper miss ở skewed từ 8,83% xuống 4,72% và tăng lower miss từ 0,06% lên 3,06%; high-price subgroup coverage tăng từ 86,6% lên 93,8%, n=305. Mean interval score giảm từ 15,59 xuống 13,76 tỷ. Scope nhỏ và DGP định trước, nên kết quả chỉ là căn cứ nghiên cứu thêm.

## Nhóm, fallback và shift

- Ở heteroskedastic nominal 90%, log coverage là 90,1% ở low và 80,4% ở high-price (n=654/311), 93,1% ở complete và 74,5% ở missing=3 (n=857/106), 76,9% ở unknown (n=234), 75,9% ở VILLA (n=58). Adaptive cải thiện missing=3 lên 83,0%, unknown lên 84,6%, VILLA 86,2%; coverage complete giảm còn 90,7%. Các nhóm nhỏ có uncertainty lớn.
- Với (k=\lceil(n+1)(1-\alpha)\rceil), mức hữu hạn tối thiểu là 4/9/19 cho 80/90/95%. Quy tắc research cho nhóm yêu cầu lưới rank ≤ `alpha/4` và đủ 10 kỳ vọng tail observations `n×alpha`, cho 50/100/200 entity. Đây là tiêu chí ổn định thực nghiệm cần xác minh tiếp, không thêm bảo đảm thống kê. Log type×band ở heteroskedastic có n=229 cho HOUSE-HIGH, cutoff 0,4003 và hai rank kề 0,3963–0,4047; VILLA-HIGH n=33 và VILLA-LOW n=5 đều không qua gate. So sánh adjacent-cutoff đo nhạy cục bộ, không thay bootstrap hoặc calibration độc lập.
- Ở nominal 90%, fallback type khoảng 3,2–3,4%, type×band 6,9–8,0%. Variant không fallback abstain đúng tỷ lệ tương ứng, nên coverage của nó chỉ trên tập có bounds. Heteroskedastic type×band khi fallback giảm miss ở high-price overall nhưng VILLA vẫn 75,9%. Global fallback không cấp bảo đảm riêng cho VILLA. Không có invalid interval trong các run chính; unit tests kích hoạt invalid/insufficient chủ động.

| 90% log | Reference coverage (Wilson 95%) | Temporal shift | Geographic shift |
| --- | ---: | ---: | ---: |
| Additive | 91,22% (89,83–92,44) | 64,89% | 73,50% |
| Skewed | 91,11% (89,71–92,34) | 49,78% | 77,17% |
| Heavy tail | 89,33% (87,82–90,68) | 35,44% | 55,00% |
| Heteroskedastic | 87,61% (86,01–89,05) | 29,00% | 52,78% |

Ở heteroskedastic temporal, upper misses đạt 70,39%. Geographic lower misses đạt 44,00%. Negative controls thành công khi cho thấy phương pháp có thể mất coverage trong điều kiện sai giả định. Các unit test kiểm 23 ca gồm rank, ties, support, abstention, corrupted values, overflow, provenance, overlap và cả hai shifts. C là ứng viên nghiên cứu Phase B vì bám p và tỉ lệ quy mô, trong khi B/D/E/F phải tiếp tục là đối chứng. [Research report](SMARTPROP_WP05_PREDICTION_INTERVAL_RESEARCH_REPORT.md)

## Tái lập

Từ repository root, dùng Python 3.14.6 cho lần chạy lưu bằng chứng. Script chạy bằng stdlib và không nhận nguồn dữ liệu làm input.

```powershell
python -B -m unittest discover -s docs/ai/benchmark -p test_wp05_prediction_interval_benchmark.py -v
cmd.exe /d /c "python -B docs\ai\benchmark\wp05_prediction_interval_benchmark.py --seed 20261128 > .smartprop\wp05-benchmark.json"
cmd.exe /d /c "python -B docs\ai\benchmark\wp05_prediction_interval_benchmark.py --seed 20261128 > .smartprop\wp05-benchmark-repeat.json"
cmd.exe /d /c "python -B docs\ai\benchmark\wp05_prediction_interval_benchmark.py --seed 20261129 > .smartprop\wp05-benchmark-sensitivity.json"
Get-FileHash .smartprop/wp05-benchmark.json,.smartprop/wp05-benchmark-repeat.json
```

Tạo thư mục `.smartprop` nếu checkout mới chưa có. Cả hai run seed chính exit 0 và khớp byte, SHA-256 `f0f85552d01f5b187f3227218293fc3ab64dfeda24e793d701e33476ea9e16d9`. Seed sensitivity exit 0. Tests exit 0, 23 pass. Không có timestamp/duration trong JSON. Các file JSON đầy đủ, log, mã thoát và hash để ở checkpoint riêng. Số liệu trong bảng được làm tròn từ output. Khác phiên bản Python hoặc hệ điều hành có thể thay đổi chữ số cuối của kết quả dấu phẩy động.
