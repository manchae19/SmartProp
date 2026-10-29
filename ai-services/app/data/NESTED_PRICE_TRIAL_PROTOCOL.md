# Thử cách học giá — protocol chốt trước fit, 29/10/2026

Issue #18. Mục tiêu là tìm cải thiện đo được trên bộ sạch sẵn có và xác định
điều kiện dùng mô hình cho đồ án. Không nới cổng dữ liệu để có thêm mẫu.

## Dữ liệu và ranh giới

- Chỉ dùng 2.213 train của `training_next_preparation/runs/4fdb8ef79db89b16`
  và sidecar v6/all tương ứng. Không thêm mô tả hiện tại vào nhãn quá khứ.
- Giữ 299 validation phát triển, mọi reserved/pilot/consumed cohort và 5 nhóm
  mới của `property_source_adjudication/runs/4fd1c013b621ac45` ngoài mọi fit,
  chọn cấu hình, early stopping và scoring. Chỉ kiểm hash bảo vệ.
- Không gọi website hoặc lặp lại việc lọc tin mà nội dung nguồn còn thiếu.
  Giá rao là nhãn; không suy giá giao dịch, tọa độ hoặc lịch sử chưa quan sát.
- Không sửa file đặc trưng đã khóa, raw/run cũ, ledger, API, model v6 hoặc DB.

## Ba arm cố định

1. `log_total_squared`: log tổng giá, `reg:squarederror`, control v6/all.
2. `log_unit_squared`: log(tổng giá/diện tích), `reg:squarederror`; suy luận
   `exp(prediction) * area_sqm`. **Đơn giá chỉ là target**, không là biến X.
3. `log_total_absolute`: log tổng giá, `reg:absoluteerror`.

Giữ cùng feature contract v6/all. Vocabulary/schema chỉ học trên phần fit
nhỏ nhất; không để địa bàn/phường ở phần giữ lại đi vào vocabulary fit.
Giá, đơn giá, title, description, ID không vào X. Thiếu giữ đúng cách mã hóa
của v6, không suy đặc trưng từ giá.

Params chung: hist/CPU, 4 thread, seed42, max_depth3, eta0.03,
min_child_weight5, subsample0.8, colsample_bytree0.8, reg_lambda10.
300 rounds cố định, không early stopping hoặc thay params sau điểm outer.
Inverse log clip [-20,30] giống thử nghiệm train trước, rồi mới nhân diện tích
cho arm đơn giá. Cấm thêm arm sau khi đã xem điểm số của protocol này.

## Nested CV

- Ba outer folds theo SHA-256 của nhóm ứng viên; salt `price-trial-v1/outer/`.
  Mỗi nhóm được giữ lại đúng một lần. Sắp ID trước để thứ tự nguồn không đổi fold.
- Trong mỗi outer train, hai inner folds theo salt
  `price-trial-v1/inner/{outer_fold}/`. Fit đủ ba arm trên mỗi inner train.
- Chọn arm bằng MAE triệu VND gộp các dự đoán inner giữ lại (không dùng MAE
  log hoặc trung bình không trọng số). Tie đúng bằng nhau ưu tiên thứ tự arm trên.
- Fit lại control và arm được chọn trên toàn outer train. Chấm outer sau chọn;
  nếu chọn control thì dùng chung model/prediction, không fit thêm vô ích.
- Baseline đơn giản: median giá/m² theo địa bàn chỉ khi outer train có ít
  nhất 5 mẫu địa bàn đó; fallback median giá/m² toàn loại. Median chỉ tính
  từ outer train, không gồm outer labels.
- Báo control, thuật toán chọn arm và baseline đơn giản trên toàn OOF và
  từng loại: MAE/RMSE triệu VND, MAPE/median APE, trong20%, số sai số>50%, R².
  Báo thêm theo fold và độ phủ theo địa bàn từ train. Không chọn arm theo outer.

Đây là kiểm chứng nội bộ trên dữ liệu train đã từng được nghiên cứu, **không
phải benchmark độc lập** hoặc ước lượng không thiên lệch cho thị trường.
Không so trực tiếp điểm này với 299 validation hoặc 24 nhóm đã tiêu thụ.

## Cổng đề cử offline

Đánh giá thuật toán chọn arm so với control trên outer OOF:

- MAE gộp giảm ít nhất 5%.
- Mỗi loại không tăng MAE quá 5% và tỷ lệ trong20% không giảm quá 5 điểm phần trăm.
- Mỗi loại có ít nhất 2/3 outer folds không tệ hơn control về MAE.

Chỉ khi cả ba điều kiện đạt mới chạy chọn arm bằng 3fold trong toàn train mỗi
loại (salt `price-trial-v1/final/`) rồi fit candidate cuối trên toàn phần train
của loại đó. Candidate là file nghiên cứu, không được tự triển khai. Nếu cổng
không đạt, giữ v6 và không mở thêm search chỉ để có model thắng.

## Hoàn tất và tính lại

Lưu protocol trước first fit, params/versions, membership/schema/models,
inner/outer predictions, bảng chọn arm, metric và manifest. Verifier tải lại
model để dựng lại prediction, selection, median baseline và mọi bảng metric;
không fit khi verify. Có khóa một tiến trình ghi và kiểm hash trước/sau chạy.

Kế hoạch thu tiếp dựa trên OOF của **train** và độ phủ đặc trưng, ưu tiên
phân khúc/địa bàn có ít mẫu hoặc median APE cao. Không dùng 5 nhóm mới hoặc
cohort đã chấm để điều chỉnh quota/luật lọc. Mọi lô thu sau phải có plan/baseline
ID và giới hạn nguồn riêng; không đăng ký crawler định kỳ trong đợt này.

Mức đủ tốt của đợt: có kết luận đo được, tái lập được, không lỗi P1/P2 còn mở
trong phạm vi sửa và quyết định giữ/đề cử rõ ràng. Mức này không tự chứng minh
AI đủ chính xác cho mọi tài sản hoặc đã dự báo được xu hướng.

## Cơ sở phương pháp

- [Nested CV: chọn cấu hình và đánh giá ở hai vòng khác nhau](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html).
- [Scikit-learn: tách dữ liệu và fit preprocessing chỉ trên phần train](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage).
- [XGBoost: squared loss và absolute loss](https://xgboost.readthedocs.io/en/stable/parameter.html#learning-task-parameters).
  Thư viện cục bộ được giữ nguyên; kiểm tra objective trên fixture trước dữ liệu thật.
