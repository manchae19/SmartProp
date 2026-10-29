# Thử cách học giá với nested CV

[Issue #18](https://github.com/manchae19/SmartProp/issues/18) chốt trước khi
fit dữ liệu thật. Bộ train sạch có 2.213 nhóm; [đợt rà nguồn](PROPERTY_SOURCE_ADJUDICATION.md)
chưa phát hành thêm dữ liệu train. Đợt này dùng đúng nhãn/sidecar cũ để thử
ba cách học, không ghép mô tả hiện tại vào giá quá khứ.

Protocol: [NESTED_PRICE_TRIAL_PROTOCOL.md](../ai-services/app/data/NESTED_PRICE_TRIAL_PROTOCOL.md).
Chỉ chọn arm bằng hai inner folds; ba outer folds dùng để đánh giá thuật
toán chọn arm. Vocabulary fit-only, 300 rounds, params cố định, CPU 4 thread.
299 validation, mọi pilot/reserved/consumed cohort và 5 nhóm mới giữ riêng
không được dùng để fit, chọn hoặc chấm trong đợt này.

Các arm là log tổng giá/squared loss (control), log giá/m²/squared loss và
log tổng giá/absolute loss. Đơn giá là **target**, không được thêm vào X.
Thêm baseline median đơn giá theo địa bàn học trên outer train để biết
XGBoost hơn một phép ước tính đơn giản hay chưa.

Cổng đề cử: MAE gộp giảm ít nhất 5% và tốt hơn baseline median đơn giản;
từng loại không tăng MAE quá 5%, tỷ lệ
trong20% không giảm quá 5 điểm phần trăm, ít nhất 2/3 outer folds mỗi loại
không tệ hơn control. Candidate cuối chỉ được fit nếu qua toàn cổng; không
tự thay v6. Nếu không qua, giữ v6 và không mở thêm search theo điểm outer.

Đây là kiểm chứng nội bộ trên train đã được nghiên cứu, không phải benchmark
độc lập hoặc chứng minh giá giao dịch. Bảng ưu tiên thu thập dựa trên train,
không nhìn lỗi trên 5 nhóm mới. Việc thu sau phải có plan/giới hạn nguồn mới.

```powershell
# Tại gốc SmartProp, sau khi code/protocol được kiểm tra
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/train_nested_price_trial.py

# Tải lại model, tính lại selection/OOF/metrics, không fit
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/train_nested_price_trial.py --verify
```

Code lưu run bất biến theo SHA input/protocol/versions tại
`ai-services/app/data/processed/nested_price_trial/`. Dữ liệu/model nghiên
cứu giữ cục bộ; file tổng hợp kết quả được cập nhật sau lần chạy đã khóa.
