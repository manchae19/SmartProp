# Chạy và đọc kết quả SmartProp v3

Đợt ngày 12/10/2026 (giờ Việt Nam) đã tạo bộ dữ liệu và huấn luyện thử nghiệm. Không cần cài thêm thư viện: môi trường `.venv` hiện có NumPy và XGBoost; Ridge dùng NumPy, không cần scikit-learn.

- [Bộ training_v3 đã chốt](processed/training_v3/README.md): 1.435 train, 299 validation, 348 đại diện qua lọc giữ riêng.
- [Báo cáo so sánh mô hình](processed/models_v3_validation/README.md): trung vị theo địa bàn, Ridge và XGBoost cho từng loại tài sản.
- [Kết quả kiểm chứng](processed/models_v3_validation/verification.json): hash, nhãn, phân nhóm, mô hình đã lưu và số liệu báo cáo.

Từ `F:\SmartProp`, chạy lần lượt:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/build_training_v3.py
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/train_training_v3.py
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/validate_training_v3.py
```

Cùng đầu vào/mã/phiên bản thư viện: hai lệnh đầu xác minh bản đã chốt, không ghi đè hay train lại. Đầu vào thay đổi sẽ tạo run mới có fingerprint và cập nhật `latest.json`. Dữ liệu/model cũ và toàn bộ raw giữ nguyên. Hai script tạo dữ liệu/train có thể nhận `--pipeline-dir` / `--input-dir` để chỉ định một bản đã chốt.

XGBoost chạy CPU, 4 luồng, không cần GPU. Mỗi loại dùng một cấu hình cố định, dừng sớm theo validation. Ridge và trung vị học thống kê từ train. Chỉ số tại đây là kết quả phát triển: validation đã liên quan các thí nghiệm trước và dùng để chọn mô hình. Không chấm lại 137 tin test cũ hoặc gọi validation là test độc lập.

Đầu vào dự đoán chỉ gồm diện tích, địa bàn, phường nguồn, số phòng và cờ thiếu. Category chọn mô hình riêng. `price_million` là nhãn, còn ID, URL, nguồn và nhóm chỉ để truy vết. Không dùng tiêu đề, mô tả, raw_json, đơn giá hoặc cờ lọc làm đặc trưng. Mô hình XGBoost cần đúng thứ tự schema và lấy exp đầu ra log giá.

Kiểm tra logic chống rò rỉ:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 -m unittest discover -s ai-services/app/data -p test_training_v3.py -v
```

Kết quả hiện tại còn sai số lớn ở nhà và đất, độ phủ phường/số phòng thấp; căn hộ chỉ có 31 mẫu validation. Bước tiếp là rà soát sai số theo nguồn/địa bàn và thu thập một tập kiểm chứng mới được xác minh độc lập. Không tự sửa giá hoặc loại tin chỉ vì mô hình dự đoán sai.

## Phân tích lỗi sau huấn luyện

[Báo cáo chẩn đoán v3](processed/training_v3_diagnostics/README.md) phân tích 299 validation theo loại, nguồn, địa bàn, mức giá, diện tích và độ phủ đặc trưng. Có hai hàng chờ: ưu tiên lỗi validation và tín hiệu kiểm tra nhãn trên toàn bộ train/validation. Các tín hiệu không tự thay đổi nhãn hoặc loại tin.

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/analyze_training_v3.py
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/verify_training_v3_diagnostics.py
```

Báo cáo cũng có quy trình và mẫu trống cho pilot 150 tài sản mới (50 mỗi loại), kèm danh sách loại trừ toàn bộ ID đã thấy. Pilot hiện chưa thu thập hoặc chấm điểm. Giữ cố định model trước khi thu thập, xác minh nhãn và nghi trùng trước khi xem dự đoán; ghi nhận mọi tin bị loại cùng lý do. Ngày cập nhật không chứng minh ngày đăng đầu tiên.
