# Huấn luyện sau rà soát 4.772 tin

Bộ dữ liệu mới nằm tại [remaining_4772_review](processed/remaining_4772_review/README.md). Đã bỏ hai điều kiện chặn `older_than_183_days` và `listing_date_unavailable` theo yêu cầu; các điều kiện chất lượng khác và phân nhóm/tập giữ riêng được bảo toàn. Đây là thay đổi chính sách SmartProp, không phải tuyên bố XGBoost bảo đảm chất lượng mọi dữ liệu đầu vào.

Trong 4.772 tin chờ: 980 tin trở thành eligible, 40 tin được giữ ngoài do trùng nhóm, 3.752 tin còn cần bằng chứng. Toàn bộ collection có 3.062 eligible, 3.752 needs_review, 1.695 excluded; dữ liệu gốc không bị xóa.

Đầu vào thí nghiệm v4: **2.110 train**, **299 validation cố định của v3**, **653 eligible giữ riêng**. Train gồm 1.336 nhà, 598 đất, 176 căn hộ. Ngày đăng vẫn giữ trong metadata; không điền ngày thiếu bằng ngày cào. Các nhóm có liên hệ validation/test không được vào train. Ngày cũ/thiếu ngày không làm XGBoost từ chối dữ liệu, nhưng có thể ảnh hưởng tính đại diện theo thời gian.

## Chạy từ F:\SmartProp

```powershell
# Kiểm chứng toàn bộ nguồn và cache: đọc khoảng 4,1 GB, chỉ cần khi cần kiểm tra lại tính toàn vẹn.
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/verify_remaining_4772.py

# So sánh 3 họ mô hình trên cùng validation; không thay model v3.
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/train_reviewed_collection_v4.py
```

Kết quả tại [models_v4_validation](processed/models_v4_validation/README.md). Cùng đầu vào, mã và phiên bản thư viện sẽ xác minh run đã chốt thay vì huấn luyện lại. Model mới lưu riêng bằng fingerprint; không tự triển khai hoặc cập nhật predictor của ứng dụng.

Đợt ngày 15/10/2026 đã huấn luyện và kiểm chứng xong tại [run 1e23fad63c3a7f4b](processed/models_v4_validation/runs/1e23fad63c3a7f4b/README.md). So sánh riêng XGBoost: MAE nhà tăng 1,4%, đất giảm 0,5%, căn hộ giảm 2,8%. Khi chọn họ mô hình tốt nhất từng loại, MAE tổng thể v4 là 2.741,0 triệu VND so với 2.668,4 triệu VND của v3. Vì vậy giữ v3 làm mốc; v4 là bản thí nghiệm để đối chiếu, chưa có căn cứ thay toàn bộ mô hình hiện tại.

675 tin train bổ sung gồm 440 tin thiếu ngày, 223 tin quá ngưỡng 183 ngày cũ, 12 tin khác được giải tỏa chặn nhóm sau thay đổi ngày. Theo nguồn: 440 Homedy, 218 Nhadat24h, 17 CafeLand. Đây là các ID đại diện qua quy tắc, không phải xác minh độc lập từng tài sản. Không quy kết thay đổi sai số chỉ cho tuổi tin.

[Kiểm chứng bộ dữ liệu](processed/remaining_4772_review/independent_verification.json) đã đối chiếu hash của 2.842 đầu vào, nhãn, phân nhóm và buffer; [kiểm chứng model](processed/models_v4_validation/verification.json) tải lại model/baseline, đối chiếu 897 dự đoán và bảng so sánh. 10 kiểm thử logic rà soát đạt. Lệnh kiểm chứng model không train lại:

```powershell
./ai-services/.venv/Scripts/python.exe -X utf8 ai-services/app/data/verify_models_v4.py
```

Mỗi loại tài sản so sánh trung vị địa bàn, Ridge alpha=1 và XGBoost với cùng cấu hình cố định như v3. XGBoost chạy CPU 4 luồng, depth=3, eta=0.03, tối đa 1.500 vòng và dừng sớm theo MAE validation. Encoder/phân bố chỉ học từ train. XGBoost dùng diện tích, khu vực, phường, số phòng và cờ thiếu; không dùng giá/đơn giá/tiêu đề/mô tả/ID/nguồn làm feature. Đầu ra là log giá, cần exp để về triệu VND.

Buffer DMatrix đã kiểm tra và được tải lại để đối chiếu với CSV/schema. NaN ở feature thiếu được cho phép; giá mục tiêu phải hữu hạn và dương theo bài toán giá rao. [Tài liệu đầu vào XGBoost](https://xgboost.readthedocs.io/en/stable/python/python_intro.html).

## Đọc kết quả

`v3_v4_same_family_comparison.csv` so sánh từng họ mô hình trên đúng cùng ID/nhãn. `v3_v4_selected_comparison.csv` so sánh mô hình được chọn riêng từng loại ở mỗi phiên bản. XGBoost không mặc định thắng Ridge/trung vị. `validation_predictions.csv` giữ cả ba họ; `validation_errors.csv` dành cho xem sai số, không phải căn cứ tự sửa nhãn.

299 tin là validation phát triển đã được dùng trước đây, đồng thời dùng dừng sớm/chọn mô hình; không gọi đây là tập test độc lập. Đợt thêm 675 tin train đổi cả phân bố nguồn và thời gian, nên không kết luận rằng tuổi tin là nguyên nhân duy nhất của thay đổi sai số. Chưa thêm tọa độ căn nhà, hẻm hoặc khoảng cách tiện ích. Mục tiêu vẫn là giá rao, chưa xác minh giao dịch thực tế.

Phần cải thiện cách lưu mô tả/địa chỉ nằm trong [hướng dẫn crawler v2](CRAWLER_LOCATIONS_V2.md), tách khỏi bộ train đã chốt.

## Đợt lọc nội dung tiếp theo

[Đã rà soát tiếp 3.752 tin còn chờ](REMAINING_DATA_REVIEW.md): thêm 113 eligible, giữ ngoài 34 tin, còn 3.605 tin cần bằng chứng. Bộ đầu vào mới có 2.196 train, 299 validation, 680 eligible giữ riêng. Chưa huấn luyện lại trên bộ này; các chỉ số v4 ở trên vẫn thuộc bộ 2.110 train đã chốt. Số giá/diện tích và model v3/v4 giữ nguyên.
