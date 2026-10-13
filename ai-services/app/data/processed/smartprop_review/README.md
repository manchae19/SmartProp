# SmartProp: rà soát ba nguồn và baseline thử nghiệm

Ngày đánh giá: 11/10/2026. Giá mục tiêu là **giá rao bán tổng**, đơn vị triệu đồng; không phải giá giao dịch.

## Kết quả xử lý

Đã đối chiếu 4.511 bản ghi có ID nguồn riêng biệt: 1.092 CafeLand, 1.392 Homedy và 2.027 Nhadat24h. Không có ID trùng trong từng nguồn. CSV thô được giữ nguyên; `summary.json` lưu SHA-256 của từng đầu vào để kiểm tra lại.

Đã lấy trang chi tiết của 92 tin CafeLand Hòa Tiến/Bà Nà từ danh sách rà soát có sẵn. Dữ liệu bổ sung nằm ở `../../data_raw/cafeland_batch/cafeland_scope_recovered.csv`, có tham chiếu đối chiếu địa danh và checkpoint riêng. Đợt bổ sung đã hoàn tất, không thay đổi checkpoint phân trang của crawler gốc.

| Trạng thái không chồng lặp | Số bản ghi |
|---|---:|
| Ứng viên qua quy tắc sàng lọc | 2.639 |
| Cần rà soát giá, diện tích, loại tin hoặc đối chiếu nguồn | 873 |
| Chưa xác định được một quận/huyện cũ duy nhất | 105 |
| Qua các kiểm tra khác nhưng mốc hiển thị quá 183 ngày | 301 |
| Loại bất động sản khác | 200 |
| Ngoài hoặc chưa chứng minh thuộc vùng Đà Nẵng cũ | 393 |
| Tổng | 4.511 |

393 bản ghi nhóm địa bàn cuối nằm trong batch Homedy. Chúng được loại khỏi đầu vào mô hình, không xóa khỏi dữ liệu thô. Các trạng thái áp dụng theo thứ tự trong script; bản ghi bị giữ lại có thể đồng thời mang nhiều lý do rà soát.

`all_records_audit.csv` lưu toàn bộ bản ghi, dữ liệu gốc trong `raw_json`, vị trí dòng nguồn, trường chuẩn hóa và lý do xử lý. `needs_review.csv` có 978 bản ghi của hai nhóm cần rà soát. `candidates.csv` chứa 2.639 ứng viên, chưa phải dữ liệu đã xác minh thủ công.

## Địa bàn và thời gian

Đối chiếu địa danh mới theo [Nghị quyết 1659/NQ-UBTVQH15](https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-quyet-so-1659-nq-ubtvqh15-sap-xep-cac-dvhc-cap-xa-cua-thanh-pho-da-nang-nam-2025-119250616202714604.htm). Hòa Tiến/Bà Nà được ánh xạ về Hòa Vang cũ; An Hải về Sơn Trà; Hòa Cường về Hải Châu. Đây là suy luận địa bàn từ tên đơn vị và phạm vi sáp nhập, chưa xác minh vị trí thực địa của từng bất động sản.

Không tự gán Hòa Khánh, Hải Vân, Hòa Xuân, An Khê hoặc tên Liên Chiểu không có tiền tố quận vào một quận/huyện cũ duy nhất vì đơn vị mới trải qua nhiều quận/huyện cũ. Do đó 105 tin mang nhãn Liên Chiểu không đủ chi tiết được giữ lại để rà soát, dù crawler ban đầu chấp nhận nhãn này.

Trong 1.300 thẻ CafeLand rà soát: 477 có địa danh ánh xạ được một quận/huyện cũ; 622 trải qua nhiều quận/huyện cũ; 201 ngoài hoặc chưa xác định. Đã lấy chi tiết 92 trong số 477 thẻ ánh xạ được. Các thẻ chưa lấy chi tiết không được tự thêm vào ứng viên. Kết quả từng thẻ ở `cafeland_scope_audit.csv`.

Địa chỉ Nhadat24h thường không chứa tên tỉnh. Script dùng đồng thời nhãn địa bàn `in_scope`, trang danh sách Đà Nẵng và quận/huyện cũ; crawler nguồn trước đó kiểm tra mã tỉnh trên thẻ tin. Không coi bằng chứng này là đã xác minh địa chỉ thực tế.

Mốc CafeLand là thời gian cập nhật nguồn, không phải ngày đăng đầu tiên. Nhadat24h dùng ngày hiển thị hoặc ước lượng số ngày tương đối tại thời điểm thu thập. Homedy không có ngày đăng/cập nhật đáng tin trong đầu vào; không suy ngày từ URL ảnh hay ngày thu thập. 785 ứng viên Homedy có thời gian chưa biết; 712 được giữ trong bộ đại diện baseline.

## Quy tắc sàng lọc và nghi trùng

Phân tích lại giá tổng từ đơn vị tỷ/triệu và đối chiếu số nguồn. Không đổi giá theo m² thành giá tổng hoặc điền giá thỏa thuận. Ngưỡng rà soát thử nghiệm: giá dưới 100 triệu; diện tích ngoài 20–1.000 m²; đơn giá ngoài 2–300 triệu/m². Có đối chiếu giá danh sách/chi tiết Homedy, cờ nguồn, loại bất động sản và các dấu hiệu giá trả trước/khởi điểm trong tiêu đề.

Các ngưỡng chỉ hỗ trợ sàng lọc, không chứng minh tin đúng/sai. Không tự sửa những giá thấp đáng ngờ khi thiếu bằng chứng nguồn. Cờ cần rà soát chưa được giải quyết thủ công. Phân loại theo nguồn/tiêu đề có thể nhầm và cần kiểm tra trước khi dùng chính thức.

Phát hiện 296 cặp nghi trùng, trong đó 72 cặp xuyên nguồn. Cặp nghi trùng là tiêu đề chuẩn hóa khớp trong cùng quận và loại, hoặc tiêu đề tương tự ít nhất 0,88, giao token ít nhất 0,65, diện tích lệch không quá 1% và giá lệch không quá 5%. Có điều kiện số token để hạn chế khớp tiêu đề ngắn. Chi tiết và hai URL đối chiếu ở `possible_duplicate_pairs.csv`.

Những liên kết này chỉ là ứng viên cùng bất động sản. Giữ toàn bộ bản ghi trong audit; chỉ chọn một đại diện cho mỗi nhóm khi thử baseline. Sau bước này có 2.455 đại diện: 1.515 nhà, 644 đất và 296 căn hộ. Có thể bỏ sót tin trùng khác tiêu đề hoặc gom nhầm tiêu đề quảng cáo giống nhau.

## Baseline và kiểm tra

So sánh hai mô hình riêng cho từng loại bất động sản: trung vị đơn giá theo quận nhân diện tích; hồi quy ridge alpha=1 của log giá theo log diện tích và quận. Không dùng giá/đơn giá làm đặc trưng. Không dùng nguồn, tiêu đề hoặc cột rà soát làm đặc trưng. Các trung vị, mã hóa quận và chuẩn hóa diện tích đều chỉ học từ train.

Chia nhóm nghi cùng bất động sản bằng SHA-256 với seed `smartprop-v1`, ngưỡng 80/10/10 cho train/validation/test. Có 1.938 train, 258 validation và 259 test. Chọn mô hình theo MAE validation. Tập test chỉ đánh giá mô hình đã chọn; chưa phải đánh giá theo thời gian tương lai hay nguồn hoàn toàn mới.

| Loại | Số test | MAE (tỷ đồng) | Sai số phần trăm tuyệt đối trung vị | MAPE |
|---|---:|---:|---:|---:|
| Nhà ở | 175 | 2,603 | 28,65% | 66,32% |
| Đất nền | 58 | 2,604 | 32,74% | 67,49% |
| Căn hộ | 26 | 0,896 | 13,65% | 107,95% |

MAPE cao cho thấy còn giá rao rất thấp đáng ngờ và các trường hợp mô hình sai lớn. Căn hộ chỉ có 26 mẫu test; không suy rộng độ chính xác từ chỉ số trung vị. Đã xem một số sai số lớn để chẩn đoán; kết quả này là mốc thử nghiệm, không dùng như benchmark cuối cùng hay triển khai định giá.

`baseline_metrics.json` lưu cả hai mô hình, kết quả validation/test và sai số theo quận. `baseline_models.json` lưu tham số; `baseline_holdout_predictions.csv` lưu dự đoán đối chiếu. Chưa tích hợp mô hình vào API.

Đã kiểm tra: tổng số bản ghi/trạng thái khớp; ID nguồn không trùng; 92 ID bổ sung đều nằm trong danh sách rà soát ban đầu và đã lấy chi tiết; SHA-256 đầu vào không đổi; nhóm nghi trùng không nằm ở nhiều tập; giá đầu vào mô hình dương và hữu hạn. Các kiểm thử quy tắc có trong `test_smartprop_preparation.py`.

## Ưu tiên bổ sung

`coverage_and_collection_plan.csv` có số đại diện theo 7 quận/huyện và 3 loại. Mốc 50 bản/ô là chỉ tiêu thử nghiệm để nhận diện nhóm ít dữ liệu, không phải yêu cầu phân bố thị trường phải đều.

Ưu tiên nhà Hòa Vang (21 đại diện), căn hộ Liên Chiểu (3), căn hộ Thanh Khê (26), căn hộ Cẩm Lệ (31). Đất Hòa Vang đã có 246 đại diện nên chưa cần cào thêm đại trà. Căn hộ Hòa Vang chưa có mẫu: cần kiểm tra nguồn cung thực tế trước khi đặt mục tiêu số lượng. Đợt này chỉ bổ sung 92 tin có sẵn để tránh tăng số lượng mà không tăng chất lượng.

Trước vòng mô hình tiếp theo, nên lấy/xác minh chi tiết các giá đáng ngờ và bổ sung vị trí đường, hẻm, dự án, loại nhà, pháp lý khi nguồn có dữ liệu. Không suy các trường thiếu. Cần một đánh giá độc lập mới nếu thay đổi quy tắc sau khi đã xem sai số test hiện tại.

## Chạy lại từ F:\SmartProp

Chỉ chạy xử lý sau khi crawler dừng để đầu vào ổn định:

```powershell
.\ai-services\.venv\Scripts\python.exe ai-services/app/data/prepare_smartprop_dataset.py --as-of 2026-10-11
.\ai-services\.venv\Scripts\python.exe ai-services/app/data/train_smartprop_baseline.py
.\ai-services\.venv\Scripts\python.exe ai-services/app/data/test_smartprop_preparation.py
```

Script lấy chi tiết bổ sung có thể chạy lại, sẽ bỏ qua 92 ID đã lưu:

```powershell
.\ai-services\.venv\Scripts\python.exe ai-services/app/data/crawler_cafeland/recover_cafeland_scope.py --input-dir ai-services/app/data/data_raw/cafeland_batch --max-new 100
```
