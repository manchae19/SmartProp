# Huấn luyện v5 — 15/10/2026

**Đã có API demo v6:** [hướng dẫn khởi động và gọi dự đoán](../../README.md). API dùng bản v6/all cố định, hỗ trợ nhà ở, đất nền và căn hộ; không thay đổi các model v5 lịch sử.

**Đã có thử nghiệm đặc trưng v6:** [kết quả và cách chạy](TRAINING_V6.md). Giữ nguyên 2.214/299, nhánh kết hợp đặc trưng có MAE 2.457,33 triệu và MAPE 36,13% trên validation phát triển. V5 và các số liệu lịch sử bên dưới giữ nguyên.

Đã huấn luyện trên **2.214 train**, giữ nguyên **299 validation** và không dùng **684 tin dự phòng**. [Báo cáo](processed/models_v5_validation/runs/533deedd6b42f8f3/README.md) · [Metrics](processed/models_v5_validation/runs/533deedd6b42f8f3/metrics.json) · [Kiểm chứng độc lập](processed/models_v5_validation/verification.json).

## Kết quả

| Phiên bản | Train | MAE tổng hợp (triệu VND) | MAPE | Tỷ lệ sai số ≤20% |
|---|---:|---:|---:|---:|
| v3 | 1.435 | 2.668,36 | 43,80% | 46,82% |
| v4 | 2.110 | 2.741,05 | 46,63% | 44,82% |
| v5 | 2.214 | 2.726,10 | 40,25% | 45,15% |

V5 giảm MAE so với v4 nhưng **MAE vẫn cao hơn v3 khoảng 2,16%**. MAPE thấp hơn cả hai phiên bản trước: đây là hai thước đo khác nhau, chưa thể nói v5 tốt hơn trên mọi tiêu chí. Theo MAE tổng hợp đang dùng để chọn model, giữ v3 làm mốc; không tự thay model trong ứng dụng.

Trong v5, XGBoost có MAE thấp nhất trong ba họ thử ở cả ba loại:

| Loại | Train | Validation | XGBoost v5 MAE (triệu VND) |
|---|---:|---:|---:|
| Nhà ở | 1.411 | 153 | 3.243,40 |
| Đất nền | 626 | 115 | 2.513,96 |
| Căn hộ | 177 | 31 | 959,98 |

Nhà v5 vẫn kém Ridge v3 theo MAE; đất v5 cải thiện; căn hộ v5 kém XGBoost v3/v4. Không ghép các con số của các họ khác nhau rồi gọi tất cả là so sánh XGBoost. Bảng [cùng họ](processed/models_v5_validation/runs/533deedd6b42f8f3/same_family_comparison.csv) và [họ được chọn](processed/models_v5_validation/runs/533deedd6b42f8f3/selected_family_comparison.csv) tách rõ hai phép so sánh.

## Cách chạy tại gốc SmartProp

```powershell
./ai-services/.venv/Scripts/python.exe -X utf8 ai-services/app/data/train_reviewed_collection_v5.py
./ai-services/.venv/Scripts/python.exe -X utf8 ai-services/app/data/verify_models_v5.py
```

Script đọc `remaining_diversity_review/latest.json` và yêu cầu đúng bộ đã kiểm chứng 2.214/299. Cùng mã/đầu vào/môi trường sẽ kiểm chứng lại run đã chốt, không ghi đè model v3/v4. Đầu ra chọn qua `models_v5_validation/latest.json`; không sử dụng các thư mục `.building_*` chưa hoàn tất.

Mỗi loại thử trung vị đơn giá theo địa bàn, Ridge và XGBoost. XGBoost CPU hist 4 luồng, seed 42, cùng tham số v3/v4, tối đa 1.500 vòng, dừng sớm sau 50 vòng theo MAE thang giá gốc. Không tìm siêu tham số. Tất cả feature vocabulary/thống kê chỉ fit từ train; thiếu số phòng được giữ missing. Không thêm giá/đơn giá/tiêu đề/mô tả/ID vào X; chưa có feature vị trí tài sản, hẻm hoặc khoảng cách POI.

Đã tải lại ba model XGBoost, các baseline và schema; kiểm chứng đủ 897 dự đoán (299 tin × 3 họ), các metric, 18 so sánh cùng họ và 6 so sánh họ được chọn. SHA-256 của các đầu ra v3/v4 không đổi. Model JSON XGBoost trả log giá; dùng đúng schema của cùng loại rồi lấy exp để về triệu VND.

**Giới hạn đánh giá:** 299 tin này là validation phát triển đã dùng nhiều lần cho dừng sớm/chọn model. Các kết quả không phải độ chính xác test độc lập hoặc giá giao dịch thực tế. Không chấm test, không đụng dữ liệu dự phòng và không tự triển khai. Bước cải thiện tiếp theo nên dựa trên đặc trưng có bằng chứng và tập kiểm chứng mới, thay vì chỉ tăng số lượng tin.

## Đã phân tích sai số sau huấn luyện

[Báo cáo phân tích v5](processed/models_v5_diagnostics/runs/a85b7be306c671f8/README.md) · [Kiểm chứng phân tích](processed/models_v5_diagnostics/verification.json).

- 68 tin có giá rao từ 10 tỷ trở lên chiếm **58,40%** tổng sai số tuyệt đối; 60 tin trong nhóm này được dự đoán thấp hơn giá rao. Top 10 sai số tiền chiếm **21,29%**.
- So riêng XGBoost, MAE v3 là 2.774,38 triệu → v5 là 2.726,10 triệu, cải thiện **1,74%**. Bộ được chọn của v3 có MAE 2.668,36 triệu nhờ dùng Ridge cho nhà và trung vị cho đất; đó là phép so sánh khác.
- 1.081/1.411 nhà train thiếu số phòng có cấu trúc (**76,61%**). Tiêu đề có dấu hiệu số tầng ở 671 nhà và mặt tiền/kiệt ở 595 nhà, nhưng đây mới là dấu hiệu trong tin rao, chưa phải feature đã kiểm chứng hoặc giải thích nhân quả của sai số.
- Đã xuất [24 tin ưu tiên đối chiếu nguồn](processed/models_v5_diagnostics/runs/a85b7be306c671f8/priority_review.csv) và [10 tin cần kiểm tra phạm vi loại tài sản](processed/models_v5_diagnostics/runs/a85b7be306c671f8/source_scope_watchlist.csv). Không tự sửa/xóa nhãn dựa trên residual; giá/diện tích đề xuất để trống.

Kiểm chứng đạt: 299 cặp dự đoán, 897 hàng so sánh cùng họ, 483 hàng phân nhóm, các tỷ trọng sai số và đóng góp MAE theo loại. Model v3/v4/v5 và dataset giữ nguyên SHA-256. Chưa huấn luyện model hoặc thêm feature trong đợt phân tích này. Ưu tiên tiếp theo là trích số phòng/tầng, mặt tiền/kiệt và subtype nhà từ nguồn có bằng chứng; khoảng cách tiện ích cần tọa độ tài sản đủ tin cậy.

Chạy lại từ gốc repo:

```powershell
./ai-services/.venv/Scripts/python.exe -X utf8 ai-services/app/data/analyze_models_v5.py
./ai-services/.venv/Scripts/python.exe -X utf8 ai-services/app/data/verify_models_v5_diagnostics.py
```
