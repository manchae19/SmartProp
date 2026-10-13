# Mô hình v3: so sánh trên validation

Đã huấn luyện từ 1,435 tin train và so sánh trên 299 tin validation đã chốt. Không đọc/chấm lại test.

| Loại | Train | Val | Trung vị MAE | Ridge MAE | XGBoost MAE | Chọn theo MAE |
|---|---:|---:|---:|---:|---:|---|
| Nhà ở | 788 | 153 | 3,217.0 | 3,092.0 | 3,291.4 | Ridge |
| Đất nền | 518 | 115 | 2,571.3 | 2,600.6 | 2,581.6 | Trung vị địa bàn |
| Căn hộ chung cư | 129 | 31 | 1,071.4 | 1,086.5 | 937.6 | XGBoost |

MAE tính bằng **triệu VND**; nhỏ hơn là tốt hơn. Cả ba họ mô hình dùng cùng ID và nhãn trong từng loại. Không mặc định XGBoost thắng.

| Loại | MAE mô hình chọn | RMSE | MAPE | MedAPE | Sai số ≤20% |
|---|---:|---:|---:|---:|---:|
| Nhà ở | 3,092.0 | 4,872.3 | 47.3% | 22.1% | 47.1% |
| Đất nền | 2,571.3 | 4,916.1 | 46.5% | 28.7% | 40.9% |
| Căn hộ chung cư | 937.6 | 1,447.8 | 16.8% | 13.8% | 67.7% |

## Cách hiểu kết quả

Đây là kết quả phát triển: validation đồng thời dùng để dừng sớm/chọn mô hình và có liên quan các thí nghiệm trước. Chưa phải kiểm chứng độc lập trên thị trường. Không so trực tiếp với MAE v2 vì khác cohort; không tối ưu theo 137 tin test cũ.

Dữ liệu là giá rao, chưa xác minh giao dịch. Nhóm căn hộ nhỏ; số liệu từng địa bàn/nguồn có n<10 được đánh dấu trong metrics.json. Địa bàn chưa thấy trong train dùng fallback trung vị toàn loại ở baseline và indicator bằng 0 ở mô hình tuyến tính/cây.

## Đặc trưng và lưu mô hình

XGBoost: log giá, cây hist trên CPU 4 luồng, depth=3, eta=0.03, tối đa 1500 vòng; dừng sớm sau 50 vòng không cải thiện MAE giá gốc. Chỉ thử một cấu hình cố định. Đặc trưng: diện tích, địa bàn, phường nguồn xuất hiện ≥3 lần trong train, số phòng và cờ thiếu. Đất không dùng số phòng. Không dùng ID/URL/nguồn/tiêu đề/raw_json/giá trên m²/cờ lọc làm đầu vào.

Ridge alpha=1 dùng log diện tích và địa bàn, dự đoán log giá. Baseline trung vị đơn giá học từ nhãn train theo địa bàn, fallback toàn loại. Mọi thống kê/encoder chỉ học từ train.

`metrics.json`: toàn bộ chỉ số, lựa chọn từng loại, sai số theo nguồn/địa bàn. `validation_predictions.csv`: cả ba mô hình. `validation_errors.csv`: sai số của mô hình được chọn, xếp giảm dần; sai số lớn không phải căn cứ tự sửa/loại nhãn. `feature_coverage.csv`: độ phủ đặc trưng.

Model XGBoost JSON phải dùng schema cùng loại và exp đầu ra. `baseline_models.json` lưu hai baseline. Đã tải lại các file mô hình và xác nhận dự đoán khớp trước khi chốt manifest.

Bước tiếp: rà soát lỗi theo khu vực/nguồn và lập tập kiểm chứng mới được xác minh độc lập trước khi đưa vào ứng dụng. Giữ nguyên tập chờ, raw, các bộ/model v1/v2 và test cũ.
