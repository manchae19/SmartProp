# V6 — đặc trưng từ nội dung tin rao

**API demo v6 đã được tạo ngày 17/10/2026:** [cách chạy và gọi dự đoán](../../README.md). API nạp ba model/schema của run `b4b1339d3f35857e`, nhánh `all`, kiểm tra SHA-256 khi khởi động và dùng lại bộ trích/encoder v6 nguyên bản. Đây là suy luận phục vụ demo cục bộ.

**Đã chấm pilot 132 tin ngày 17/10/2026:** [báo cáo kiểm chứng](V6_HOLDOUT_PILOT.md). MAE 1.928,18 triệu VND, MAPE 35,86%, tỷ lệ sai số ≤20% là 59,09%. Đây là pilot lưu trữ khác cohort validation bên dưới; 132 tin từ nay đã được đánh giá, không còn là test mới chưa chấm.

Đã bổ sung đặc trưng có câu bằng chứng và thử nghiệm 5 cấu hình XGBoost trên **2.214 train**, cùng **299 validation**, giữ riêng **684 tin dự phòng**. Cấu hình kết hợp `all` có MAE thấp nhất trên validation phát triển; chưa triển khai thay model ứng dụng.

[Báo cáo mô hình](processed/models_v6_ablation/runs/b4b1339d3f35857e/README.md) · [Metrics](processed/models_v6_ablation/runs/b4b1339d3f35857e/metrics.json) · [Kiểm chứng model](processed/models_v6_ablation/verification.json) · [Đặc trưng và bằng chứng](processed/property_features_v6/runs/6c9b866cdd95c66d/README.md) · [Kiểm chứng đặc trưng](processed/property_features_v6/verification.json).

## Kết quả trên cùng validation

| Cấu hình | MAE (triệu VND) | MAPE | Sai số ≤20% | MAE so với v5 |
|---|---:|---:|---:|---:|
| Giữ nguyên v5 — control | 2.726,10 | 40,25% | 45,15% | 0,00% |
| Thêm phòng ngủ/tầng | 2.614,10 | 37,17% | 48,49% | −4,11% |
| Thêm mặt tiền/kiệt | 2.578,46 | 39,96% | 46,15% | −5,42% |
| Thêm biệt thự/nhà cấp 4 | 2.735,14 | 40,99% | 43,14% | +0,33% |
| Kết hợp cả ba nhóm | **2.457,33** | **36,13%** | **49,16%** | **−9,86%** |

MAE cấu hình `all` cũng thấp hơn khoảng **7,91%** so với bộ model được chọn của v3 (2.668,36 triệu). V3 là Ridge cho nhà, trung vị cho đất, XGBoost cho căn hộ; đó không phải XGBoost thuần. Thêm riêng subtype không cải thiện, nên không kết luận mọi đặc trưng mới đều hữu ích độc lập.

| Loại | V5 MAE | V6 all MAE | Thay đổi |
|---|---:|---:|---:|
| Nhà ở | 3.243,40 | 2.810,02 | −13,36% |
| Đất nền | 2.513,96 | 2.409,00 | −4,18% |
| Căn hộ | 959,98 | 895,97 | −6,67% |

Đơn vị triệu VND. Các nhánh dùng cùng tham số/seed XGBoost v5, CPU hist 4 luồng, tối đa 1.500 vòng, dừng sớm sau 50 vòng theo MAE ở thang giá gốc. Giao thức và luật trích được cố định trước lần fit đầu; không sửa luật sau khi thấy điểm. Control được fit lại và khớp từng dự đoán v5. Nhánh thắng được chọn toàn cục, không ghép nhánh tốt nhất theo từng loại.

## Thông tin đã bổ sung

| Đặc trưng trong train | Trước | Sau |
|---|---:|---:|
| Nhà có số phòng ngủ | 330/1.411 | **533/1.411** |
| Căn hộ có số phòng ngủ | 122/177 | **141/177** |
| Nhà có số tầng hiện hữu được nêu rõ | Chưa dùng | **620/1.411** |
| Nhà có lời rao xác định mặt tiền/kiệt | Chưa dùng | **673/1.411** |
| Đất có lời rao xác định mặt tiền/kiệt | Chưa dùng | **278/626** |
| Nhà có subtype biệt thự/nhà cấp 4 rõ | Chưa dùng | **89/1.411** |

Đây là lời rao được trích có bằng chứng, không phải đo đạc thực địa hoặc xác minh căn nhà. 530 HTML mô tả dùng trong bước này đã kiểm tra SHA-256, khớp ID/header giá/diện tích với snapshot. Tin khác sử dụng tiêu đề và trường có cấu trúc đã lưu. Có 57 dòng phát hiện mâu thuẫn giữa các lời rao; numeric/categorical không rõ giữ thiếu, riêng phòng có cấu trúc giữ giá trị gốc khi chữ mâu thuẫn.

Mỗi giá trị có quote/rule/source trong `feature_evidence_DO_NOT_TRAIN.csv`. Không lấy phòng trọ thành phòng ngủ, số tầng tòa chung cư thành tầng nhà, kế hoạch xây/nhà gần đó thành hiện trạng, “khu biệt thự” thành subtype, “gần mặt tiền” thành mặt tiền, tên Võ Văn Kiệt thành kiệt hoặc bề ngang thửa đất thành lối vào. Bộ trích bảo thủ có thể bỏ sót câu đúng; không đoán để tăng độ phủ.

Mô hình nhận giá trị theo whitelist, không nhận nguyên văn tiêu đề/mô tả, giá/đơn giá, ID hoặc nguồn. Giá header chỉ dùng để kiểm tra mô tả đúng snapshot, không vào X. Giá/diện tích/nhãn/nhóm/split gốc giữ nguyên. Vocabulary địa bàn/phường chỉ học từ train. Chưa có độ rộng hẻm, tọa độ tài sản hoặc khoảng cách tiện ích.

## Chạy và kiểm chứng tại gốc SmartProp

```powershell
./ai-services/.venv/Scripts/python.exe -X utf8 -m unittest discover -s ai-services/app/data -p test_property_text_features_v6.py -v
./ai-services/.venv/Scripts/python.exe -X utf8 ai-services/app/data/build_property_features_v6.py
./ai-services/.venv/Scripts/python.exe -X utf8 ai-services/app/data/verify_property_features_v6.py
./ai-services/.venv/Scripts/python.exe -X utf8 ai-services/app/data/train_property_features_v6.py
./ai-services/.venv/Scripts/python.exe -X utf8 ai-services/app/data/verify_models_v6.py
```

Chọn đầu ra qua `property_features_v6/latest.json` và `models_v6_ablation/latest.json`, cùng `verification.json` tương ứng. Các snapshot trung gian giữ để truy vết; không sử dụng thư mục `.building_*`. Cùng mã/đầu vào/môi trường sẽ kiểm chứng run đã chốt. Script không cào thêm nguồn.

16 kiểm thử trích thông tin đạt. Kiểm chứng độc lập đã phát lại 2.513 dòng đặc trưng và 3.485 hàng bằng chứng; tải lại **15 model**, kiểm tra **1.495 dự đoán**, mọi metric/cấu hình/model được chọn. Model v3/v4/v5, dataset gốc và reservation giữ nguyên SHA-256.

`selection.json` trỏ model/schema của nhánh `all` để thử nghiệm phát triển. Suy luận phải dùng cùng extractor và schema, giữ unknown/missing đúng quy tắc; model trả log giá rồi exp về triệu VND. API demo đã dùng đúng quy trình này; các artifact model và dữ liệu huấn luyện giữ nguyên.

**Giới hạn:** validation đã được dùng nhiều lần cho dừng sớm và chọn model/cấu hình; đây chưa phải test độc lập, các so sánh thêm/bỏ feature không chứng minh nhân quả. Giá mục tiêu vẫn là giá rao. Bước tiếp theo là kiểm chứng bằng tài sản mới theo giao thức đã cố định trước khi thay model ứng dụng; không chọn tin kiểm chứng theo residual hoặc sửa giá để cải thiện điểm.

## Đã kiểm tra lịch sử 684 tin dự phòng — 17/10/2026

[Báo cáo kiểm tra lịch sử](processed/reserved_holdout_audit/runs/9406f9eb8e954325/README.md) · [Kiểm chứng độc lập](processed/reserved_holdout_audit/verification.json).

| Kết luận từ artifact cục bộ | Số ID |
|---|---:|
| Có dấu vết dự đoán hoặc đầu vào train/validation | 539 |
| Liên kết lịch sử với ID đã dùng | 12 |
| Chưa thấy dấu vết sử dụng trực tiếp hoặc qua liên kết đã lưu | 133 |
| Tổng | 684 |

133 ứng viên gồm **78 nhà**, **47 đất**, **8 căn hộ**, thuộc 133 thành phần liên kết lịch sử khác nhau. Đã kiểm kê 401 CSV, chỉ giữ metadata qua allowlist; các cột giá và dự đoán không được đưa vào phân tích/lựa chọn ứng viên. Train/validation đã chuẩn bị cũng bị chặn bảo thủ; chỉ nằm trong `test.csv` chưa đủ để kết luận đã chấm. Lịch sử nhóm/cặp nghi trùng được nối bắc cầu, không chỉ kiểm tra cùng ID.

8 kiểm thử và kiểm chứng độc lập đã đạt; đã phát lại toàn bộ metadata lịch sử, xác minh SHA-256 model/dataset và [giao thức ứng viên gắn với v6](processed/reserved_holdout_audit/runs/9406f9eb8e954325/locked_candidate_protocol.json). Chưa đọc/phân tích nhãn giá ứng viên, chưa chấm test và chưa thay model.

**133 là ứng viên không có dấu vết sử dụng tìm thấy**, không phải chứng nhận test độc lập/tài sản mới. Các liên kết trùng chưa lưu hoặc sử dụng bên ngoài repo vẫn có thể chưa được phát hiện; dữ liệu cũng đã qua bộ lọc chất lượng chung. Bước tiếp theo là kiểm tra phạm vi loại tài sản/trùng còn thiếu theo quy tắc cố định, rồi đánh giá một lần với model/schema/extractor v6 đã khóa. Đây là pilot trên dữ liệu lưu trữ, chưa phải kiểm chứng theo thời gian tương lai. Chỉ 8 căn hộ nên đánh giá riêng phân khúc này còn thiếu ổn định; có thể cần đợt kiểm chứng căn hộ mới có mục tiêu.

Chạy lại kiểm tra lịch sử:

```powershell
./ai-services/.venv/Scripts/python.exe -X utf8 ai-services/app/data/audit_reserved_holdout.py
./ai-services/.venv/Scripts/python.exe -X utf8 ai-services/app/data/verify_reserved_holdout_audit.py
./ai-services/.venv/Scripts/python.exe -X utf8 -m unittest discover -s ai-services/app/data -p test_audit_reserved_holdout.py -v
```
