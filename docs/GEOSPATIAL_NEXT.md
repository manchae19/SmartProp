# Dữ liệu vị trí cho lần huấn luyện tiếp theo

Rà soát ngày **26/10/2026**. API demo vẫn dùng v6; tài liệu này không xác nhận đã huấn luyện model có tọa độ hoặc tiện ích.

## Trạng thái đã đối chiếu

Đối chiếu theo `record_key` giữa run đặc trưng v6 `6c9b866cdd95c66d` và audit vị trí `0f2be923900adb3e` đang lưu cục bộ:

| Chỉ tiêu | Train | Validation phát triển |
|---|---:|---:|
| Số tin v6 | 2.214 | 299 |
| Có tọa độ số từ nguồn | 67 | 6 |
| Có manh mối tên đường | 425 | 10 |
| Có lời rao về mặt tiền/kiệt đã trích trong v6 | 951 | 121 |
| Tọa độ được xác minh đúng tài sản và quyền dùng ML | **0** | **0** |

Địa chỉ có dữ liệu không đồng nghĩa có số nhà hoặc có thể định vị đúng căn nhà. Tọa độ số chưa phải tọa độ đã xác minh. Cả 80 dòng trong `geospatial_v1/coordinate_review.csv` hiện chưa được duyệt. Các con số 2.082 eligible/2.002 cần định vị trong audit ngày 12/10 là cohort lịch sử, không thay thế số liệu v6 trên.

Trong pilot cũ: 65 truy vấn tên đường cho 80 tin tạo 240 ứng viên; 63 tin có ứng viên khớp đường. Đợt rà soát sâu 20 tin chỉ có 1 tin khớp tham chiếu kiệt và 16 tin khớp đường; **0 vị trí cấp tài sản được xác minh**. Chưa có snapshot OSM hoặc file khoảng cách thật đã chốt trong thư mục geospatial hiện hành. [Bằng chứng và giới hạn lịch sử](../ai-services/app/data/GEOSPATIAL_FEATURES.md).

Một lần thử lại POST tới `https://overpass-api.de/api/interpreter` với khung thử nghiệm sẵn có `[15.93, 108.05, 16.21, 108.31]` bị chặn socket `WinError 10013`, chưa nhận phản hồi HTTP. Không thử máy chủ khác hoặc lặp lại. Đây là giới hạn môi trường của lần kiểm tra, **không chứng minh dịch vụ Overpass hiện bị lỗi**. Metadata cục bộ: `.scratch/geospatial-next-2026-10-26/overpass-probe.json`.

Sau đó chạy một lần bằng quyền mạng được duyệt với script `geospatial_enrichment.py fetch-osm` và cùng khung/endpoint: nhận HTTP **502**, không lưu snapshot dùng được. Đã dừng; không thử endpoint khác hoặc chạy geocoding hàng loạt. Trạng thái POI vẫn thiếu.

## Cải thiện có thể triển khai ngay

1. Tạo bản chuẩn bị train mới từ snapshot v6, kiểm tra mọi `location_feature` với danh mục địa bàn đã rà soát. Đưa mã tiêu đề tin sai vào hàng chờ sửa có lý do; không đổi tên mã đó thành phường theo suy đoán. Giữ nguyên các snapshot, giá, nhóm và split cũ. Lỗi đã xác định tại [LOCATION_LABELS.md](LOCATION_LABELS.md).
2. Xuất bảng readiness cho đúng cohort mới: có/thiếu tên đường, tọa độ nguồn, bằng chứng xác minh, quyền tái sử dụng và snapshot POI. Giữ đặc trưng khoảng cách thiếu khi chưa đủ điều kiện; không điền 0 hoặc dùng tâm đường/phường.
3. Dùng [collector v2 hiện có](../ai-services/app/data/collect_chotot_locations_v2.py) khi nhập bản xuất hoặc lấy nguồn được phép: nó giữ nguyên mô tả, địa chỉ chi tiết, số nhà/số kiệt và chiều rộng có nguồn. Hiện chưa có đầu ra `data_raw/chotot_locations_v2`; không báo đã thu được dữ liệu đó. Không cần viết lại phép tính khoảng cách đã có trong [geospatial_enrichment.py](../ai-services/app/data/geospatial_enrichment.py).

Lối vào đã là đặc trưng của v6; phần còn thiếu là độ rộng kiệt có bằng chứng và vị trí đúng tài sản. Tên đường gần nhất trên bản đồ không tự chứng minh tài sản có mặt tiền đường đó.

## Điều kiện để nối vị trí vào XGBoost

Đã triển khai và chạy `ai-services/app/data/prepare_training_next.py`: bản chuẩn bị tại `processed/training_next_preparation/runs/4fdb8ef79db89b16` có **2.213 train**, **299 validation giữ nguyên byte**, giữ nguyên registry dự phòng và chỉ sao chép đặc trưng v6 của đúng ID. **1 tin `homedy:3205669` được cách ly** vì mã địa bàn là tiêu đề; không suy đoán địa bàn thay thế. Train mới có 424 manh mối đường, 67 tọa độ nguồn; validation có 10 và 6. Tất cả còn bị chặn ở cổng đặc trưng vị trí. Manifest ghi SHA-256 nguồn/đầu ra và được kiểm tra lại; chưa fit encoder, train model hay chấm lại pilot. Chạy lại cùng script/đầu vào chỉ kiểm chứng run đã có.

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/prepare_training_next.py
```

- Tọa độ phải gắn đúng ID tài sản, có nguồn/bằng chứng kiểm tra, người và thời điểm duyệt; `precision=property`, `location_verified=True`, `reuse_for_ml_verified=True` đều phải có căn cứ. Một dòng khai báo không tự xác minh các điều kiện này.
- Snapshot POI phải đầy đủ, lưu thời gian bản đồ, khung tải, endpoint, ID OSM, SHA-256 và ghi công. Pipeline hiện tính khoảng cách đường chim bay đến trường học, bệnh viện, công viên trong 3 km; chưa phải quãng đường đi bộ hoặc khoảng cách đến cổng công trình.
- Không tìm thấy đối tượng OSM trong phạm vi không chứng minh thực tế không có tiện ích. Thiếu dữ liệu phải giữ thiếu; không tự kết luận công trình thuộc sở hữu công hoặc có thể tiếp cận.
- Giữ cùng cohort/split và chống trùng khi so sánh baseline với model thêm vị trí; không đưa tập dự phòng/pilot đã chấm vào train để tăng số lượng. Snapshot bản đồ hiện tại chưa chứng minh trạng thái tiện ích tại ngày đăng tin cũ.

## Nguồn chính thức đã kiểm tra

- [Chính sách Nominatim](https://operations.osmfoundation.org/policies/nominatim/): máy chủ công cộng giới hạn tối đa 1 yêu cầu/giây, yêu cầu nhận diện ứng dụng và cache; việc geocode hàng loạt thường xuyên cần giải pháp phù hợp khác. Không dùng để quét hàng nghìn địa chỉ lặp lại hoặc tìm toàn bộ POI.
- [Các máy chủ Overpass](https://wiki.openstreetmap.org/wiki/Overpass_API#Public_Overpass_API_instances): máy chủ miễn phí phục vụ dự án nhỏ, có thể quá tải; có thể dùng bản trích xuất vùng và xử lý offline khi khối lượng lớn. Không đặt truy vấn bản đồ công cộng vào từng lần người dùng ước tính giá.
- [Giấy phép OSM](https://www.openstreetmap.org/copyright): dữ liệu theo ODbL, cần ghi công OpenStreetMap contributors và giữ thông tin giấy phép khi phân phối; rà soát nghĩa vụ với dữ liệu phái sinh.
- [Đường service/alley](https://wiki.openstreetmap.org/wiki/Tag:highway%3Dservice): `highway=service` có nhiều loại, trong đó `service=alley`; chỉ một tag service không xác nhận lối vào tài sản.
- [Chiều rộng](https://wiki.openstreetmap.org/wiki/Key:width): `width` mặc định theo mét, khác `maxwidth` là hạn chế pháp lý và khác `est_width` là ước lượng. Không suy ra chiều rộng hẻm từ chiều ngang thửa đất hoặc loại đường.
