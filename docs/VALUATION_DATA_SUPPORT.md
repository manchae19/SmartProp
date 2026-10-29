# Cảnh báo độ phủ dữ liệu trong kết quả định giá

[Issue #19](https://github.com/manchae19/SmartProp/issues/19), tiếp nối
[thử nghiệm mô hình](NESTED_PRICE_TRIAL.md) không đạt cổng đề cử. Model ứng
dụng vẫn v6; giá và feature matrix giữ nguyên. Phần cải thiện của demo là
thông báo rõ hơn khi dữ liệu hỗ trợ đầu vào còn mỏng.

## Người dùng sẽ thấy gì?

API thêm nội dung vào `warnings` đã có, FE hiện đã hiển thị danh sách này:

- Khi loại bất động sản/địa bàn có dưới 10 nhóm trong bộ tham chiếu sạch:
  “Loại bất động sản tại địa bàn này chỉ có 4 nhóm trong bộ dữ liệu tham
  chiếu sạch; kết quả có thể có sai số lớn.” Số 4 là số mẫu thực của cặp
  căn hộ/Liên Chiểu trong bản tham chiếu hiện tại.
- Khi có ít nhất 10 nhóm, nhưng diện tích nằm ngoài percentile5–95 mô tả
  diện tích của nhóm cùng loại/địa bàn: cảnh báo diện tích ngoài khoảng phổ biến.
- Khi profile thiếu, sai SHA, sai release hoặc không có cặp loại/địa bàn:
  thông báo chưa có thống kê độ phủ phù hợp. API vẫn chạy theo model hiện tại.

Đây là **độ phủ mẫu tham chiếu**, không phải độ tin cậy, xác suất dự đoán đúng
hoặc khoảng giá bảo đảm. Percentile diện tích là thống kê mô tả diện tích,
không phải khoảng dự đoán giá. Ngưỡng 10 phục vụ thông báo ít mẫu, không chứng
minh trên ngưỡng đó thì model đã chính xác.

Không đổi keys/request validation của API, cách chọn địa bàn, giá dự đoán,
thông tin đã dùng hoặc lịch sử định giá. BE/FE/database không sửa trong đợt này.
Các cảnh báo mới đi qua cùng mảng warnings mà FE đang hiển thị. Sau khi cập
nhật mã nguồn cần khởi động lại AI API để tiến trình nạp profile mới; không
cần train lại hoặc migration database.

## Bộ tham chiếu là gì?

`app/core/reference_support_v6.json` là thống kê tổng hợp của bộ **2.213 nhóm
train sạch** tại `training_next_preparation/runs/4fdb8ef79db89b16`. Đây không
phải toàn bộ 2.214 dòng mà release v6 gốc đã fit: một địa bàn không hợp lệ
đã được cách ly khi chuẩn bị bản sạch. Không gọi số mẫu tham chiếu là số mẫu
chính xác mà từng request của model đã học.

Profile có 56 cặp loại/địa bàn, 28 cặp dưới 10 mẫu. Giữ riêng địa bàn nguồn
cũ/mới, không suy cùng ranh giới chỉ vì cùng tên. Chỉ gồm số nhóm và khoảng
mô tả diện tích khi đủ mẫu; không có ID tin, giá, URL, mô tả, số điện thoại
hoặc thông tin cá nhân. Cặp dưới 10 mẫu không công bố thống kê diện tích.

Profile được gắn với run/manifest v6 và SHA cố định trong loader. Loader kiểm
schema, số đếm, tổng mẫu và khoảng diện tích; thiếu/sai thông tin thì không
sử dụng profile. Metadata được nạp một lần cùng vòng đời predictor, không
tải CSV/HTML riêng tư hoặc fit model trong request.

## Tạo lại và kiểm chứng

Lệnh này cần kho dữ liệu nguồn cục bộ; profile tổng hợp đã được đóng cùng
repo để API trên máy clone không cần CSV/HTML.

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/build_reference_support_v6.py --verify
.\ai-services\.venv\Scripts\python.exe -X utf8 -m unittest discover -s ai-services/tests -v
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/tests/smoke_http_v6.py --diagnose
```

Generator đối chiếu manifest nguồn/release, dựng lại JSON và so từng byte;
không âm thầm ghi đè profile đã xuất. JSON dùng LF ổn định để hash giữ nguyên
khi clone Windows/Linux.

SHA profile: `497765c4226df7b52fcd71d24d37b2e3af2082b71d7c092cd87110d7dd9a0217`.

## Giới hạn và kiểm thử

Các fixture kiểm ít mẫu, thiếu profile, sai hash/release, biên diện tích,
schema/count/range không hợp lệ, không công bố dữ liệu riêng tư và API giữ
nguyên keys/giá. Bộ API hiện có replay đủ 299 prediction đã công bố để kiểm
parity; đây là kiểm tính tương thích, không phải lần đánh giá chất lượng mới.

Nghiên cứu train cho thấy nhiều cặp địa bàn mỏng có sai số nội bộ dao động
lớn. Profile chỉ giúp người dùng nhận ra giới hạn dữ liệu; nó không làm model
chính xác hơn. Muốn cải thiện định giá cần bổ sung nguồn/đặc trưng đủ bằng
chứng và kiểm chứng mới; muốn dự báo xu hướng cần quan sát qua nhiều thời điểm.

Kết quả cuối: **157 kiểm thử pipeline dữ liệu + 32 kiểm thử API đạt trên
checkout sạch**, gồm replay 299 prediction đã công bố. **10 kiểm thử FE đạt**.
Smoke HTTP launcher với stdin đóng/cwd khác đạt cho cả 3 loại, theo dõi health
5 giây và dừng đúng tiến trình kiểm thử. Không dừng dịch vụ người dùng.

## Standards

Review riêng: 0 hard violation, 0 heuristic đáng kể cần xử lý. Thuật ngữ là
độ phủ tham chiếu, số nhóm/percentile không trở thành confidence hoặc khoảng
dự đoán. Profile phân biệt bộ sạch/release, không xuất dữ liệu riêng tư.
Reviewer chạy lại 6 test loader/API và 3 test builder: đạt.

## Spec

Review riêng: không có P1/P2 hoặc yêu cầu còn thiếu trong phạm vi #19.
Reviewer xác nhận profile binding/fallback, ngưỡng ít mẫu/diện tích, warnings
cũ, giá/feature matrix/API keys giữ nguyên và BE/FE/DB không sửa. Fixture
review chạy độc lập đạt; không fit dữ liệu riêng tư hoặc chấm cohort mới.

Mốc bàn giao là demo có kiểm chứng và thông báo giới hạn rõ, kèm quyết định
giữ model hiện tại từ thử nghiệm đã khóa. Đây chưa là chứng nhận độ chính
xác ngoài thị trường; chưa có model dự báo xu hướng được phát hành.
