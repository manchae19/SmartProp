# Rà đặc trưng tài sản và thu mô tả còn thiếu

Ngày **29/10/2026**, [issue #12](https://github.com/manchae19/SmartProp/issues/12).
Đã rà đúng **2.213 train + 299 validation** và thu thêm20 trang mô tả căn hộ
thuộc train. Model/API vẫn dùng v6; chưa phát hành ma trận đặc trưng mới hoặc
huấn luyện v8 trong đợt này.

## Kết quả

Run cục bộ: `processed/property_evidence_audit/runs/79a628aae654dffa`, tính từ
`ai-services/app/data/`. Pointer: `processed/property_evidence_audit/latest.json`.

- **2.512 dòng sidecar** đúng ID/split của cohort; raw/giá/diện tích giữ nguyên.
- **898 dòng bằng chứng** có quote nguồn, SHA, quy tắc và trạng thái:819 nhận
  là lời rao rõ ràng,71 loại ngữ cảnh,8 mâu thuẫn giữ missing. Đây là số quote,
  không phải898 tài sản hoặc819 phép đo đã xác minh.
- Mô tả cũ khớp snapshot:486 train/44 validation. Riêng căn hộ: chỉ3/177 train
  và0/31 validation có mô tả cũ qua cổng, còn lại chủ yếu tiêu đề/trường số.
- Đã lấy20/20 trang căn hộ CafeLand từ hàng đợi train; tất cảHTTP200, danh tính,
  loại, giá/diện tích khớp. Tất cả được đánh dấu
  `refreshed_matching_labels_NOT_ASOF_VERIFIED`.
- Sau lượt này có3 mô tả căn hộ cũ và20 mô tả mới để nghiên cứu; **154/177**
  căn hộ train vẫn thiếu mô tả phù hợp:11 CafeLand và143 Nhadat24h.
- Chưa thu tên dự án/tòa bằng quy tắc rõ ràng;20 trang CafeLand chỉ có nhãn
  cấu trúc giá, diện tích, phòng ngủ. Không tự gán tên từ tiêu đề/địa chỉ.

Số dòng train có lời rao được nhận, sau loại mâu thuẫn/ngữ cảnh:

| Trường | Nhà ở (1.410) | Đất nền (626) | Căn hộ (177) |
|---|---:|---:|---:|
| Độ rộng kiệt/hẻm | 46 | 6 | Không áp dụng |
| Ô tô vào | 116 | 34 | Không áp dụng |
| Tầng căn hộ | Không áp dụng | Không áp dụng | 10 |
| Nội thất rõ full/cơ bản/không có | 147 | Không áp dụng | 17 |
| Lời khai giấy tờ/pháp lý | 190 | 94 | 7 |
| Năm bàn giao | Không áp dụng | Không áp dụng | 0 |

Trong validation căn hộ, chỉ1 dòng có tầng căn hộ,3 dòng có nội thất rõ,0 có
giấy tờ/năm bàn giao theo quy tắc. Coverage này chưa đủ để đánh giá đáng tin
các đặc trưng căn hộ mới. Coverage validation chỉ dùng mô tả giới hạn; không
dùng câu validation để phát triển regex hoặc thay tập kiểm chứng.

## Cách sử dụng kết quả

- `features_DO_NOT_TRAIN.csv`: giá trị trích và trạng thái mô tả, mọi dòng cấm
  tự ghép vào train. Không chứa giá nhãn làm feature hoặc tọa độ suy đoán.
- `evidence_private_DO_NOT_TRAIN.csv`: quote/hash/rule; giữ cục bộ, không commit.
- `coverage.csv`: độ phủ theo split/loại tài sản/trường.
- `collection_requests.csv`:11 tin CafeLand train còn thiếu mô tả, không bao
  gồm các nhóm kiểm chứng đã chấm.143 tin Nhadat24h cần adapter/lượt thu riêng.
- `manifest.json`: hash nguồn, code, HTML, đầu ra và nguồn được bảo vệ. Verifier
  dựng lại giá trị/quote/coverage, không chỉ kiểm hash file đầu ra.

Phủ định rõ được ghi đúng trạng thái khi contract cho phép: ô tô không vào là
`no`; sổ chưa có/đang chờ cấp là `certificate_not_available_claimed`. Các phủ
định còn mơ hồ giữ missing. “Có sổ” vẫn chỉ là lời rao, không xác nhận pháp lý.
Tên dự án/tòa, nếu bắt được, chỉ là ứng viên cần rà danh tính và chuẩn hóa.

Mô tả đọc ngày29/10 có cùng giá/diện tích **không chứng minh đặc trưng đã tồn
tại thời điểm nhãn cũ**. Vì vậy không tự nối20 mô tả mới vào X để huấn luyện
hoặc tuyên bố cải thiện. Bước tiếp theo cần thu giá và đặc trưng cùng thời điểm
cho cohort mới, kiểm nhóm trùng và có tập kiểm chứng đủ độ phủ.

## Giá theo thời gian

Đã hoàn tất watchlist20/20 ngày29/10: tất cảHTTP200/qua quy tắc, chưa thấy đổi
giá/diện tích so với lần đọc trước. Kho hiện **260 quan sát/220 ID**, gồm220
quan sát ngày27/10,20 ngày28/10 và20 ngày29/10 theo giờ Việt Nam. Các timestamp
gốc làUTC; JSON `observation_dates` ở báo cáo thị trường liệt kê ngàyUTC.

Report thị trường mới: `processed/market_price_observations/runs/d35795a6459768ca`.
Vẫn chỉ có tháng10/2026,24 nhóm ứng viên trong bảng tháng, chưa có cặp giữa hai
tháng; chưa train/công bố dự báo xu hướng.20 tin watchlist và20 tin lấy mô tả
train là **hai nhóm công việc khác nhau**, không gộp số lượng để tăng train.

## Chạy lại

Tại gốc repo; dùng môi trường hiện có và requirements review/crawler:

```powershell
# Lô20 trang đã xong: kiểm checkpoint, không tải lại
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/collect_training_property_evidence.py --count 20

# Kiểm tra lại sidecar và bằng chứng của code/input hiện tại
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/audit_property_evidence.py --verify

# Dựng run mới khi có input/rules mới, giữ nguyên các run cũ
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/audit_property_evidence.py

# Watchlist29/10 đã xong: không gọi mạng khi chạy lại
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/market_price_pipeline.py observe --run-id 2026-10-29 --count 20
```

Lô nguồn ở `data_raw/training_property_evidence_20`; mỗi phản hồi có HTML theo
SHA và metadata riêng được công bố nguyên tử. Không chỉnh policy/code của lô
đã khóa để kéo thêm tin. Cần lô/version riêng cho lượt tiếp theo. Nguồn bị chặn
thì dừng; không vượt CAPTCHA hoặc đổi danh tính.

## Kiểm chứng và review

88 unit test đạt:49 pipeline cũ,22 quan sát giá,12 quy tắc đặc trưng,5 audit/
collector. Verifier replay2.512 dòng/898 quote; keeper của bộ chuẩn bị kiểm21
hash nguồn bảo vệ và ledger. Không đổi artifact/API v6, cohort hoặc database.

### Standards

Hai lượt review độc lập không phát hiện vi phạm tiêu chuẩn repo. Một heuristic
P3 về lặp primitive ghi/fsync/link file trong collector mới được giữ lại để
tránh thay mã collector/plan đã dùng thu lô20; đây là đề xuất bảo trì, không
phải lỗi dữ liệu. Heuristic lặp nhánh diễn giải của quan sát giá đã được sửa.

### Spec

Hai lỗi của #11 đã sửa: ghi evidence bị ngắt vàHTTP200 rỗng.
Ba nhóm lỗi của #12 đã sửa: quan hệ gần nhà ở hậu vị, phủ định/chờ cấp ở hậu
vị, khoảng/lựa chọn độ rộng bằng từ nối. Có regression và hai reviewer đã kiểm
tra lại phạm vi sửa. Không còn finding Spec mở trong phạm vi đã rà.

Tổng review hiện tại: Standards0 hard violation/1 heuristic P3; Spec0 lỗi còn
mở sau sửa5 finding P2. Rà ngữ cảnh còn bảo thủ, có thể bỏ sót lời rao hợp lệ;
không coi regex là xác minh tài sản hoặc hiểu đầy đủ tiếng Việt.

[Quy tắc nguồn](../ai-services/app/data/PROPERTY_EVIDENCE_PROTOCOL.md) ·
[Review quan sát giá](MARKET_PRICE_REVIEW.md).
