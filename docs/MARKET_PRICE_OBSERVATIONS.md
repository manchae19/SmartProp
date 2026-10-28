# Cải thiện định giá và chuẩn bị dữ liệu xu hướng

Đã thực hiện ngày **28/10/2026**, theo [issue #11](https://github.com/manchae19/SmartProp/issues/11).
Nhánh làm việc: `feature/market-price-observations`. **Model ứng dụng vẫn là v6**;
lần này xây dữ liệu quan sát và kiểm tra độ sẵn sàng, chưa chứng minh mô hình
định giá chính xác hơn hoặc huấn luyện mô hình dự báo xu hướng.

## Kết quả chạy thực tế

| Nội dung | Kết quả |
|---|---:|
| Cache CafeLand đã kiểm chứng và nhập vào kho mới | 220 |
| ID cũ được đọc lại trực tiếp ngày 28/10 | 20/20 |
| Phản hồi 200 và qua quy tắc chất lượng trong lượt đọc lại | 20/20 |
| ID có giá/diện tích thay đổi giữa hai lần đọc | 0/20 |
| Tổng quan sát đã lưu | **240** |
| Tổng ID tin rao duy nhất | **220** |
| Quan sát qua quy tắc chất lượng | 44 |
| Nhóm ứng viên qua quy tắc trong bảng tháng | **24** |
| Tháng có quan sát thực tế | **1: tháng 10/2026** |

44 quan sát qua quy tắc gồm 24 quan sát ban đầu và 20 quan sát đọc lại, không
phải 44 tài sản. 196 tin còn lại vẫn lưu bằng chứng nhưng chưa được đưa vào
thống kê qua quy tắc. Chất lượng này là rà soát lời rao, chưa xác minh tài sản
thực địa hoặc giá giao dịch. Không đổi giá trong mẫu 20 tin qua hai ngày
**không chứng minh giá thị trường ổn định**.

Ngày nguồn có thể là tháng7, nhưng giá chỉ được chứng minh tại lúc đọc trang
27–28/10. Vì vậy không tạo các điểm giá tháng7–9 từ ngày đăng/cập nhật nguồn.
Các tin thuộc 24 nhóm đã chấm v7 vẫn cấm ghép vào train/encoder/early stopping.

Kho append-only và bằng chứng nằm ở
`ai-services/app/data/data_raw/market_price_observations/`, được gitignore.
Mỗi tin có nhiều quan sát UTC, SHA HTML, provenance và trạng thái nguồn.
SQLite cấm sửa/xóa qua SQL thông thường; không cần cài thêm MySQL cho kho này.
Lịch sử người dùng lưu định giá trong BE vẫn là nghiệp vụ riêng.

## Báo cáo để xem

Đầu ra hiện tại:
`ai-services/app/data/processed/market_price_observations/runs/9e4d4e006ab405f8/`.
`processed/market_price_observations/latest.json` trỏ tới bản hiện hành.

- `README.md`, `summary.json`: số liệu, cổng dữ liệu và giới hạn.
- `dashboard.html`: bảng giá rao mô tả, có nhãn địa bàn tiếng Việt, phân biệt
  địa bàn mở rộng và hiển thị ô thiếu mẫu; mở trực tiếp bằng trình duyệt.
- `monthly_asking_prices.csv`: trung vị giá rao theo tháng × địa bàn × diện
  tích, một nhóm ứng viên một mẫu/tháng. Không coi là chỉ số giá giao dịch.
- `valuation_readiness.csv`: độ phủ đặc trưng của cohort sạch.
- `collection_priorities.csv`: địa bàn/loại tài sản còn ít nhóm train.
- `observations_DO_NOT_TRAIN.csv`: từng quan sát và khóa bằng chứng, cấm tự
  nối vào tập huấn luyện.

10 ô thống kê hiện chỉ có 1–6 nhóm/ô, đều dưới mốc kế hoạch10. Chưa có cặp
quan sát giữa hai tháng, nên mọi % thay đổi tháng để thiếu. Cổng chuẩn bị
backtest18 tháng chưa đạt; **chưa có dự báo xu hướng**. Mốc10/18 là quy ước
lấy mẫu và thiết kế thử nghiệm, không phải yêu cầu của XGBoost hoặc bảo đảm
độ chính xác. Có thể bổ sung kho lịch sử hợp lệ đã có bằng chứng theo thời
gian; không nhất thiết phải chờ18 tháng mới bắt đầu nghiên cứu.

## Phần còn thiếu để cải thiện định giá

| Loại | Train | Validation phát triển | Train có lời rao lối vào | Train có tọa độ nguồn | Train có feature vị trí đủ điều kiện |
|---|---:|---:|---:|---:|---:|
| Nhà ở | 1.410 | 153 | 672 | 67 | 0 |
| Đất nền | 626 | 115 | 278 | 0 | 0 |
| Căn hộ | 177 | 31 | 0 | 0 | 0 |

Các dòng lối vào/tầng/phòng là lời rao được trích, chưa phải đo đạc. Toàn bộ
tọa độ và khoảng cách POI chưa đủ điều kiện dùng. 444 tin nhà ở thiếu ngày
nguồn; không tự lấy ngày cào bù thành ngày đăng hoặc thời điểm của giá cũ.

Đã xuất68 ô loại × địa bàn có dưới10 nhóm train, trong đó40 ô chưa có nhóm.
Đây là kế hoạch lấy mẫu theo **train**, không dựa vào điểm pilot. Không cần
cào cho đủ mọi ô bằng mọi giá; ưu tiên địa bàn/phân khúc có nhu cầu sử dụng và
nguồn đủ bằng chứng.

Ưu tiên thực hiện tiếp:

1. Bổ sung căn hộ ở dự án/địa bàn còn ít mẫu; giữ dự án/tòa, tầng căn hộ, năm
   bàn giao, pháp lý, diện tích sử dụng và nội thất khi nguồn ghi rõ.
2. Với nhà/đất, giữ bằng chứng độ rộng kiệt, ô tô vào, lối vào, pháp lý và hiện
   trạng. Không suy độ rộng hẻm từ chiều ngang thửa đất.
3. Chỉ tạo khoảng cách tiện ích khi tọa độ đúng tài sản, nguồn/quyền tái sử dụng
   và snapshot bản đồ đã được kiểm chứng. Không dùng tâm phường thay vị trí nhà.
4. Duy trì quan sát giá; bổ sung nguồn/lịch sử hợp lệ trước khi thiết kế backtest
   theo thời gian và so sánh với baseline giá trị gần nhất. Chưa có tác vụ tự
   chạy theo lịch được đăng ký trong đợt này.

## Lệnh sử dụng

Tại `F:\SmartProp`, môi trường hiện có đã đủ dependencies. Máy mới cần
`requirements_apartment_review.txt` và kho cache riêng để seed; không cần cache
để chạy các kiểm thử bằng fixture.

```powershell
# Nhập lại cache: không gọi mạng, không nhân đôi dòng
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/market_price_pipeline.py seed

# Lượt 28/10 đã hoàn tất; chạy lại cùng run-id chỉ đọc kết quả
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/market_price_pipeline.py observe --run-id 2026-10-28 --count 20

# Quan sát ở lần tiếp theo: dùng run-id mới cho ngày thực sự chạy
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/market_price_pipeline.py observe --run-id 2026-10-29 --count 20

# Phân tích lại bằng chứng và xuất báo cáo mới
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/market_price_pipeline.py verify
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/market_price_pipeline.py report
```

`run-id` là định danh lượt chạy; **không dùng nó làm ngày quan sát**. Thời gian
luôn được lấy lúc nhận phản hồi thực. Collector tôn trọng robots, cách yêu cầu
ít nhất3 giây, dừng khi bị chặn/lỗi mạng. Không chỉnh code/policy khi đang chạy;
run chưa hoàn tất mà đổi code phải dùng phiên bản/run mới. Run đã hoàn tất
được kiểm chứng và đọc lại dù mã vận hành sau đó đổi, không sửa plan cũ.

## Kiểm chứng

- **20 kiểm thử mới**: idempotency, giữ cả hai giá, thời gian/múi giờ, lỗi nguồn,
  bằng chứng bị sửa, đếm trùng nhóm, sai cơ cấu mẫu, tháng thiếu, tiếp tục sau
  ngắt, khóa được dọn, chạy lại run hoàn tất không sửa file/không gọi mạng.
- Cùng49 kiểm thử pipeline trước: **69 kiểm thử đạt**.
- Tái phân tích HTML và quyết định cho240 quan sát; checksum và giá trị trùng
  kết quả đã lưu. Nhập lại thêm0 dòng; run28/10 tiếp tục ở trạng thái
  `read_only_completed`, không gọi mạng.
- Đã mở dashboard bằng Edge headless và kiểm tra ảnh render:10 dòng dữ liệu,
  không lộ mã địa bàn nội bộ. 21 checksum nguồn được bảo vệ của bản chuẩn bị
  train khớp; không thay model/API, split, ledger, MySQL hoặc lịch sử tài khoản.

[Quy tắc đầy đủ](../ai-services/app/data/MARKET_PRICE_PROTOCOL.md) ·
[Thuật ngữ](../GLOSSARY.md) · [Quyết định về thời gian giá](adr/0001-price-observation-time.md).
