# Rà soát 222 tin và chuẩn bị dữ liệu thử nghiệm — 29/10/2026

Theo [issue #16](https://github.com/manchae19/SmartProp/issues/16), tiếp nối
[đợt bổ sung nguồn](PROPERTY_EXPANSION_RESULTS.md). Đã rà bằng quy tắc có
bằng chứng cho đủ **222/222 tin chờ**, đồng thời kiểm tra lại cả 12 ứng viên
cũ. Không truy cập website, huấn luyện hoặc chấm mô hình trong đợt này.

## Kết quả trên 222 tin chờ

| Kết luận không chồng lặp | Số tin |
|---|---:|
| Tách khỏi tập một căn hộ vì chào bán rõ nhiều căn | 2 |
| Chưa đủ bằng chứng hoặc còn quan hệ nhóm cần làm rõ | 217 |
| Đại diện một nhóm mới, giữ ngoài train | 1 |
| Tin thứ hai của cùng nhóm mới, không đếm thêm tài sản | 1 |
| Đại diện một nhóm train được đọc lại | 1 |
| **Tổng** | **222** |

Ba lỗi thiếu corroboration được giải quyết bằng giá VND đầy đủ có nhãn giá
tổng rõ trong lời rao và diện tích cùng phản hồi. Hai trong ba tin là cùng
một mã căn/dự án/diện tích, nên gộp thành một nhóm ứng viên. Tin còn lại là
ID đã thuộc train: đọc lại không làm tăng số tài sản train.

Hai cờ loại cũ chỉ dựa vào heading “tòa căn hộ” được chuyển về cần làm rõ.
Heading này không chứng minh chủ tin đang bán nguyên tòa. Các tin đó vẫn bị
chặn bởi bằng chứng nguồn/điều kiện giá chưa giải quyết; không tự chuyển thành
dữ liệu đủ chất lượng. Mọi giá trị và kết quả cổng cũ được giữ nguyên.

## Kết quả trên toàn bộ 234 snapshot

| Vai trò trong phiên bản nghiên cứu mới | Số tin/đại diện |
|---|---:|
| Đại diện nhóm train đọc lại | 6 |
| Đại diện nhóm mới giữ ngoài train | 6 |
| Bản trùng trong cùng nhóm ứng viên | 1 |
| Cần bổ sung bằng chứng/giải quyết quan hệ nhóm | 218 |
| Tách khỏi tập một căn hộ | 3 |
| **Tổng** | **234** |

Kiểm tra lại 12 ứng viên cũ phát hiện hai trường hợp cần rút: một tin tiếp
tục liệt kê giỏ hàng sau đoạn “liên hệ”; một tin chưa thống nhất nhận nhà/
dự kiến bàn giao. Có hai đại diện mới qua bước giải quyết lỗi giá VND để bù
vào danh sách ứng viên. Vì vậy tổng vẫn **6 nhóm train đọc lại + 6 nhóm mới**,
nhưng thành viên đã thay đổi. Không dùng kết quả cổng cũ như quyết định cuối.

Các nhóm là nhóm tài sản **ứng viên** dựa trên nguồn và so khớp, chưa chứng
minh tài sản độc lập ngoài thực tế. Tách khỏi tập một căn hộ không đồng nghĩa
tin giả hoặc dữ liệu phải xóa. Raw/HTML, kết quả cổng cũ và các run trung gian
đều được giữ để truy vết.

## Còn thiếu bằng chứng gì?

Cờ còn lại trên toàn bộ 234 snapshot, có chồng lặp:

| Nội dung cần làm rõ | Số tin có cờ |
|---|---:|
| Chưa có giá tổng và diện tích khớp trong lời người bán | 196 |
| Giá khởi điểm/trả trước/booking hoặc điều kiện thanh toán | 93 |
| Diện tích mô tả khác trường cấu trúc | 88 |
| Có dấu hiệu nhiều căn/giỏ hàng theo cổng cũ | 57 |
| Ngày nguồn ngoài cửa sổ 183 ngày của pilot | 55 |
| Phòng ngủ PN/BR/header chưa thống nhất theo kiểm tra mới | 54 |

Cờ ngày cũ là lựa chọn cổng pilot, không phải yêu cầu của XGBoost. Đợt này giữ
cổng đó để không thay chính sách theo số lượng đạt. Đọc lại trang hôm nay
không chứng minh lời rao đã được cập nhật hoặc tài sản còn giao dịch. Muốn
nghiên cứu nhóm có ngày đăng cũ cần protocol riêng và đánh giá theo thời gian.

Đã bổ sung kiểm tra toàn bộ lời rao sau liên hệ, phòng ngủ PN/BR khác header,
phòng ngủ giả định sau cải tạo, trạng thái bàn giao và đơn giá tiêu đề khác
tổng giá/diện tích. Không tự sửa số phòng, chọn một loại diện tích hoặc coi
giá theo m² là giá tổng. Mỗi tin có `next_action` cụ thể trong bảng kết luận.

## Dữ liệu đã chuẩn bị

Thư mục gốc tính từ `ai-services/app/data/`:
`processed/property_source_adjudication/`. Pointer `latest.json` trỏ đến run
bất biến mới nhất. Run đã tạo: `43b35a827f99077a`, có 1.120 dòng bằng chứng/
claim (không phải 1.120 tin). Bộ dữ liệu gồm:

- `pending_222_decisions.csv`: đúng 222 tin chờ, giữ cờ cũ/mới, bằng chứng,
  kết luận và việc cần làm cho từng tin.
- `all_decisions.csv`: đủ 234 snapshot, gồm cả 12 ứng viên cũ được kiểm tra lại.
- `current_observations_DO_NOT_TRAIN.csv`: giá hiện tại và diện tích, thời
  điểm quan sát, nguồn/hash, nhóm và vai trò của từng snapshot.
- `features_DO_NOT_TRAIN.csv`: đặc trưng cùng snapshot; thiếu/mâu thuẫn giữ
  trống. Không nhập giá/đơn giá hoặc nguyên văn mô tả vào tập biến dự đoán.
- `candidate_groups_DO_NOT_TRAIN.csv`: 12 đại diện, một hàng mỗi nhóm.
- `train_refresh_DO_NOT_TRAIN.csv`: 6 đại diện nhóm train đọc lại.
- `fresh_evaluation_RESERVED_DO_NOT_TRAIN.csv`: 6 nhóm mới giữ ngoài train.
- `evidence_private.csv`, `additional_group_links.json`: quote, hash và
  liên kết bổ sung; giữ cục bộ cùng kho dữ liệu nguồn.
- `schema.json`, `experiment_reservation.json`, `manifest.json`: hợp đồng
  trường dữ liệu, vai trò nhóm trước thử nghiệm và mã SHA-256.

Độ phủ đặc trưng trong các đại diện:

| Nhóm | Phòng ngủ có lời khai thống nhất | Tầng căn hộ | Nội thất | Giấy tờ | Năm bàn giao |
|---|---:|---:|---:|---:|---:|
| 6 nhóm train đọc lại | 6 | 3 | 2 | 3 | 0 |
| 6 nhóm mới giữ ngoài train | 6 | 1 | 3 | 1 | 0 |

Giấy tờ chỉ là lời khai từ nguồn. Tên dự án dùng để đối chiếu mã căn chưa
trở thành registry dự án hoặc một biến mô hình. Tọa độ/POI đủ điều kiện vẫn 0.

Vai trò giữ ngoài train được khóa **trong phiên bản ứng viên này**, chưa
đăng ký một lần chấm vào ledger toàn cục. Thử nghiệm sau phải kiểm tra đồng
thời reservation này và ledger cũ; không gọi cohort đã tiêu thụ là tập mới.

## Có train XGBoost mới ngay không?

**Chưa phát hành bộ X mới hoặc fit model mới từ lô này.** Bộ sạch cũ vẫn có
**2.213 train + 299 validation phát triển**, model ứng dụng vẫn v6. Không có
2.225 tài sản train: sáu nhóm đọc lại là nhóm train đã có, sáu nhóm mới đang
giữ riêng để kiểm chứng.

Hiện chỉ có 6 nhóm mới; chưa đạt mốc vận hành 20 nhóm của pilot. Mốc 20 cũng
không bảo đảm tính đại diện hoặc độ chính xác thống kê. Chỉ có 6 nhóm train
đọc lại qua cổng nguồn, độ phủ đặc trưng mới còn ít; không ghép các mô tả hiện
tại vào nhãn quá khứ của 2.213 tin. Cần một protocol thử nghiệm riêng về cohort,
đặc trưng, missingness và split trước mọi fit/scoring. Không chấm lại 24 nhóm
đã tiêu thụ để chọn cấu hình mới.

Bước có ích tiếp theo là thu đúng bằng chứng còn thiếu từ nguồn có một căn/
giá tổng/diện tích rõ, chọn phân khúc và địa bàn còn thiếu. Việc này cần một
plan thu thập mới với baseline ID cập nhật và giới hạn nguồn; đợt này không
cào thêm, không chạy lại các collector đã hoàn thành. Các snapshot bổ sung
cũng chưa tạo đủ chuỗi thời gian cho dự báo xu hướng.

## Chạy và kiểm chứng

Tại gốc SmartProp, dùng venv hiện có:

```powershell
# Tạo phiên bản mới theo input/code/protocol hiện tại, không gọi mạng
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/adjudicate_property_snapshots.py

# Replay đầy đủ cả nguồn cũ và kết luận mới, không fit/scoring
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/adjudicate_property_snapshots.py --verify

# Fixture không cần kho HTML/CSV thật hoặc mạng
Push-Location ai-services/app/data
try {
  & ..\..\.venv\Scripts\python.exe -X utf8 -m unittest test_property_snapshot_adjudication test_adjudicate_property_snapshots
} finally {
  Pop-Location
}
```

Run có tên theo mã hash input/code/protocol; chạy lại cùng phiên bản đối
chiếu CSV, quote, JSON/schema, inventory và SHA, không ghi đè run. Verifier
kiểm lại toàn bộ 234 snapshot, 830 liên kết cũ và protected inputs trước khi
phân vai dữ liệu mới. Liên kết mã căn chỉ được thêm, không xóa liên kết cũ.

## Kiểm thử và review

28 fixture mới kiểm tra giá VND, metadata echo, giá thuê/đặt cọc/đơn giá,
diện tích công viên, giỏ hàng sau liên hệ, heading nguyên tòa, phòng ngủ giả
định/BR, liên kết mã căn, hidden historical/protected bridge, khử trùng nhóm,
nhãn/hash/thời điểm bất biến và hợp đồng trường dữ liệu.

Kết quả review mã nguồn và replay cuối được ghi sau khi hoàn tất kiểm chứng.

Đã chạy **133 unit test đạt**, gồm 105 kiểm thử pipeline trước và 28 fixture
mới. Các test mới không cần kho dữ liệu thật hoặc mạng.
