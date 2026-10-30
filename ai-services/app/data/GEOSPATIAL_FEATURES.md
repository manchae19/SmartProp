# Bổ sung đặc trưng vị trí cho SmartProp

## Rà soát cụ thể 20 tin — 13/10/2026

[Báo cáo 20 tin và bảng đối chiếu](processed/geospatial_v1/property_location_pilot/README.md). Đã đọc manh mối nguồn cho 20 tin thuộc train trong nhóm 63 tin khớp tên đường; chọn có chủ đích, không phải mẫu đại diện. Thực hiện 18 truy vấn OSM/Nominatim hữu hạn, có cache, thêm số kiệt khi nguồn nêu rõ và giới hạn trong khung đô thị thử nghiệm hiện có. 1 tin có ứng viên khớp **kiệt 59 Trương Chí Cương**, 16 tin có ứng viên khớp đường, 1 tin có kết quả chưa khớp, 2 tin không có kết quả. Chưa xác minh bất kỳ căn nhà nào, chưa duyệt đặc trưng để train.

12/20 tin có ít nhất một ứng viên lần tra trước nằm ngoài khung thử nghiệm, không có nghĩa 12 tin đăng sai. Ví dụ đường Âu Cơ trả Hội An và Trường Chinh trả Quế Sơn: cùng tên đường và vùng Đà Nẵng chưa đủ khớp địa chỉ. Vì vậy số 63 trước đây chỉ là khớp tên đường/vùng rộng, không phải 63 vị trí đúng. Khung 108.05–108.31, 15.93–16.21 không phải ranh giới hành chính hoặc phép xác minh pin nguồn; không có kết quả trong khung không chứng minh địa chỉ không tồn tại.

Đã phân biệt số kiệt 266/196/59, mã lô LK4A - 537, lời khai giao đường, chiều rộng hẻm 3m, chiều ngang thửa 5m/6m và tên đường có số Hòa Minh 21. Không biến các số này thành số nhà; tin 266 có cách viết Trường Chính/Trường Chinh khác nhau, giữ nguyên nguồn và ghi cờ cần kiểm tra. CSV/JSONL hiện không lưu mô tả chi tiết hoặc số nhà của 20 tin; hai bản này cùng API, không là xác minh độc lập. Không thể khôi phục số nhà còn thiếu bằng tâm đường.

4 kiểm thử và kiểm chứng độc lập đạt; raw, nhãn, split, bản làm việc tọa độ, model và kết quả geocoding cũ giữ nguyên. Lệnh sau đọc cache/chốt bằng chứng, không gửi mạng:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/review_property_location_pilot.py report
```

V3 vẫn dùng được làm mốc. Cải thiện tiếp cần lưu địa chỉ/mô tả chi tiết từ nguồn được phép trong các đợt cào sau; không yêu cầu người dùng tự tạo số nhà, không gán tọa độ đường thành tọa độ nhà. Không tự train phiên bản vị trí khi bằng chứng còn thiếu.

## Tìm vị trí tham khảo từ địa chỉ — 13/10/2026

Đã chạy thử 80 ID qua OSM/Nominatim: 65 truy vấn tên đường khác nhau, tất cả HTTP 200 và có cache. 63 tin có ứng viên khớp tên đường/vùng Đà Nẵng, 9 tin có kết quả chưa khớp đủ điều kiện, 8 tin không có kết quả. Tổng cộng 240 dòng ứng viên; một tin có thể có nhiều đoạn đường. **Chưa xác minh vị trí căn nhà hoặc duyệt đặc trưng mới để train.** Không dùng điểm đại diện đường để tính khoảng cách chính xác từ tài sản.

[Báo cáo và 80 liên kết Google Maps](processed/geospatial_v1/address_pilot/README.md). Bảng HTML dùng địa chỉ nguồn để tìm trên Google Maps; không tải nội dung/tọa độ Google. CSV ứng viên riêng có nguồn OSM, tất cả chưa duyệt. Phường/quận nguồn giữ nguyên để kiểm tra, không tự ánh xạ cũ/mới hoặc suy ra số nhà, độ rộng hẻm, ô tô vào được.

Đợt hữu hạn này chỉ gửi tên đường/thành phố; không gửi giá, tiêu đề, người đăng, điện thoại hoặc pin nguồn. Một máy, một luồng, tối thiểu 1,1 giây giữa yêu cầu, User-Agent định danh, cache cả phản hồi rỗng/lỗi, dừng khi dịch vụ lỗi. Không chạy định kỳ hoặc mở rộng hàng nghìn địa chỉ bằng máy chủ công cộng; cần dịch vụ phù hợp/tự triển khai theo [chính sách Nominatim](https://operations.osmfoundation.org/policies/nominatim/). © OpenStreetMap contributors; ODbL 1.0, giữ ghi công và nghĩa vụ khi phân phối dữ liệu phái sinh.

```powershell
# Chốt lại từ cache và kiểm chứng, không gửi yêu cầu mạng:
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/geocode_address_pilot.py report
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/verify_address_geocoding_pilot.py
```

Lệnh `geocode_address_pilot.py fetch` tiếp tục hàng chờ 80 ID bằng cache; đã kiểm tra chạy lại sau hoàn tất gửi **0 yêu cầu mạng**. Không tự thử lại lỗi hoặc đổi nguồn. `--endpoint` cho phép chọn nhà cung cấp HTTPS tương thích khi có quyết định đổi dịch vụ; không tự chuyển. Run và bằng chứng cũ giữ nguyên. `candidates_DO_NOT_TRAIN.csv` và bảng đối chiếu không nối vào model v3. 6 kiểm thử đạt; kiểm chứng SHA-256 xác nhận raw, nhãn, split, coordinate_review và model giữ nguyên.

## Lấy nội dung chi tiết: nguồn đang chặn

[Báo cáo tải và checkpoint 80 ID](processed/geospatial_v1/detail_review/README.md): hàng chờ ưu tiên 30 tin có điểm dùng với nhiều tên đường. Lần kiểm tra mới gửi đúng 1 yêu cầu chi tiết (`chotot:133955557`), nhận HTTP 403/Cloudflare; dừng tải nguồn. 79 URL chưa yêu cầu, không được báo thành 79 lỗi 403. Chưa có mô tả chi tiết mới hoặc vị trí được xác minh. Raw, nhãn, split, bản làm việc tọa độ và model giữ nguyên; đã đối chiếu SHA-256.

Checkpoint lưu trong run riêng, giữ nguyên bằng chứng HTML và robots. Lệnh sau chỉ xác minh/chốt kết quả đã có, không gửi thêm yêu cầu mạng:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/finalize_geospatial_detail_attempt.py
```

Không coi checkpoint nguồn bị chặn là hoàn tất tải 80 tin. Một lần đánh giá truy cập mới phải dùng thư mục probe riêng và truyền `--probe-dir`, giữ bằng chứng cũ. Để lấy tiếp hiện cần nguồn chi tiết được phép truy cập hoặc bản xuất/bằng chứng người đăng cung cấp; không giải CAPTCHA hay đổi danh tính để vượt chặn. Model v3 hiện có vẫn dùng được làm mốc; chưa train model vị trí mới.

V3 đã được huấn luyện và vẫn sử dụng được làm mốc so sánh. Phần này tạo nhánh dữ liệu vị trí riêng; không thay đổi raw, nhãn, cách chia tập hoặc model v3.

## Đã rà soát 80 ứng viên

[Báo cáo bằng chứng từng tin](processed/geospatial_v1/candidate_review/README.md): 25 tin có lời khai kiệt/hẻm, 12 tin có lời khai mặt tiền/mặt phố, 43 tin chưa rõ. Có 4 tin nêu chiều rộng kiệt/hẻm (3 m, 4 m, 5 m), 6 tin nêu chiều rộng đường và 10 tin nêu tiếp cận ô tô. Các nhóm chiều rộng/ô tô có thể nằm trong nhóm kiệt/hẻm; không cộng thành số tin độc lập.

Đã quét 20 snapshot gốc, đối chiếu 160 bản lưu khớp 80 ID và tạo 240 dòng tham chiếu bằng chứng. CSV/JSONL Chợ Tốt cùng xuất phát từ một API. Không có mô tả chi tiết đã lưu cho 80 ID; các lời khai hiện chỉ được trích từ tiêu đề. 30/80 tin dùng tọa độ còn xuất hiện với nhiều tên đường trong collection; 3 tin có điểm dùng với nhiều tên phường/quận khai báo. Đây là tín hiệu xem lại, không tự kết luận tọa độ sai hay ánh xạ phường cũ/mới.

Chưa có bằng chứng xác minh vị trí cấp tài sản hoặc quyền dùng dữ liệu để train; không tự duyệt tọa độ. Bản `coordinate_review.csv`, mọi dữ liệu gốc và model v3 giữ nguyên. Không dùng tiêu đề chứa giá trong file review làm đầu vào mô hình.

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/review_geospatial_candidates.py
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/verify_geospatial_candidate_review.py
.\ai-services\.venv\Scripts\python.exe -X utf8 -m unittest discover -s ai-services/app/data -p test_review_geospatial_candidates.py -v
```

Chạy lại cùng đầu vào xác minh run đã chốt, không sửa bản làm việc. Lần thử lại tải OSM sau khi rà soát vẫn nhận HTTP 504; chưa có khoảng cách thật hoặc model mới.

## Kết quả ngày 12/10/2026

Đã kiểm tra toàn bộ 8.509 ID duy nhất trong collection hiện tại:

| Chỉ tiêu | Số tin |
| --- | ---: |
| Có cặp tọa độ hợp lệ về số | 2.752 |
| Có tọa độ và thuộc nhóm eligible | 80 |
| Eligible còn cần định vị | 2.002 |
| Train v3 có tọa độ | 67 |
| Validation v3 có tọa độ | 6 |
| Tọa độ đã xác minh vị trí chính xác và quyền dùng ML | 0 |

Toàn bộ tọa độ hiện có đến từ Chợ Tốt. Có 844 cặp tọa độ khác nhau; 2.296 tin chia sẻ tọa độ với ít nhất một tin khác, một điểm được 98 ID sử dụng. Đây là dấu hiệu cần kiểm chứng, không tự chứng minh tọa độ sai hoặc tài sản trùng. Cả 73 tin train/validation có tọa độ đều là nhà ở. Không suy rộng độ phủ này sang đất/căn hộ hoặc toàn bộ Đà Nẵng mới.

Các con số đếm ID, không phải số tài sản vật lý độc lập. Tin bị loại/chờ duyệt không được đưa trở lại train chỉ vì có tọa độ. Địa chỉ có số nhà/tên đường chỉ tạo hàng chờ; không coi tâm phường hoặc điểm nội suy theo đường là vị trí căn nhà.

[Báo cáo hiện tại](processed/geospatial_v1/README.md) dẫn đến các CSV và kết quả kiểm chứng. Đây là CSV phục vụ pipeline ML, không phải workbook Excel.

## Trạng thái tải bản đồ

Đã thử truy vấn nhỏ khung `south=15.93, west=108.05, north=16.21, east=108.31`, có vùng đệm trên 3 km quanh 80 ứng viên hiện có. Không gửi địa chỉ hay giá tin đăng đến dịch vụ.

Máy chủ `overpass-api.de` trả HTTP 504 và thông báo quá tải; `overpass.private.coffee` trả HTTP 500; máy chủ `maps.mail.ru` không vượt qua kiểm tra chứng chỉ TLS trong môi trường hiện tại. Không vô hiệu hóa xác minh TLS. **Chưa tải được snapshot OSM thật, chưa tính khoảng cách thật và chưa huấn luyện mô hình vị trí.** Các kiểm thử khoảng cách dùng fixture tổng hợp riêng, không đưa vào dữ liệu đồ án.

Công cụ tải có cache theo truy vấn; chỉ lưu phản hồi JSON đầy đủ, không có `remark` lỗi. Dừng khi dịch vụ lỗi; không lặp tự động hoặc gọi riêng hàng nghìn tin. Khung tải chỉ là vùng thử nghiệm quanh ứng viên hiện tại, không phải ranh giới Đà Nẵng cũ/mới.

## Chạy lại và kiểm chứng

Từ `F:\SmartProp`:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/geospatial_enrichment.py audit
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/verify_geospatial_enrichment.py
.\ai-services\.venv\Scripts\python.exe -X utf8 -m unittest discover -s ai-services/app/data -p test_geospatial_enrichment.py -v
```

Khi máy chủ sẵn sàng, tải snapshot nhỏ đã định trước:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/geospatial_enrichment.py fetch-osm --bbox 15.93 108.05 16.21 108.31
```

Có thể chọn máy chủ dự phòng đã được liệt kê trong tài liệu OSM qua `--endpoint`. Không tự động chuyển sang geocoder công cộng hoặc dịch vụ Google. Với khối lượng địa chỉ lớn, chọn dịch vụ có quyền tái sử dụng phù hợp hoặc geocoder tự triển khai; không dùng Nominatim công cộng để quét toàn bộ tiện ích/định vị hàng loạt lặp lại. [Chính sách Nominatim](https://operations.osmfoundation.org/policies/nominatim/) giới hạn tài nguyên, yêu cầu định danh ứng dụng và cache; tác vụ lớn thường xuyên cần nguồn thay thế.

## Xác minh và tạo đặc trưng

`coordinate_review.csv` trong thư mục geospatial là bản làm việc sao chép từ mẫu 80 ứng viên; trạng thái ban đầu đều chưa duyệt. Các run audit đã chốt chỉ đọc. Muốn bổ sung tọa độ cho 2.002 tin còn lại, thêm dòng tương ứng vào bản làm việc cùng bằng chứng; công cụ từ chối ID trùng, không tồn tại hoặc không eligible.

Chỉ ghi `location_verified=True`, `precision=property` và `reuse_for_ml_verified=True` khi có bằng chứng đủ rõ về đúng tài sản và quyền sử dụng dữ liệu. Ghi người kiểm chứng, thời gian ISO có múi giờ, nguồn tọa độ và bằng chứng có thể truy vết. Nguồn cho phép khai báo: `openstreetmap`, `open_data`, `survey`, `owner_supplied`, `listing_source`; việc khai báo không tự cấp quyền cho dữ liệu nguồn. Không dùng tọa độ trích từ Google rồi đổi tên nguồn. Không đánh dấu đã xác minh chỉ vì tọa độ có nhiều chữ số thập phân.

Sau khi có snapshot thật và tọa độ được xác minh, chạy:

```powershell
$geoRoot = 'F:\SmartProp\ai-services\app\data\processed\geospatial_v1'
$auditRun = Join-Path $geoRoot (Get-Content (Join-Path $geoRoot 'latest_audit.json') -Raw | ConvertFrom-Json).run
# Thay đường dẫn bên dưới bằng thư mục snapshot được lệnh fetch-osm in ra.
$osmRun = Join-Path $geoRoot 'osm_snapshots\<snapshot-id>'
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/geospatial_enrichment.py build-features --audit-dir $auditRun --osm-dir $osmRun --reviews (Join-Path $geoRoot 'coordinate_review.csv')
```

Chỉ tạo feature cho train/validation hiện có; reserved/test giữ riêng. `features.csv` giữ đủ cohort, các hàng chưa định vị được ghi thiếu. `unverified_preview_DO_NOT_TRAIN.csv` là bản xem thử cho tọa độ nguồn chưa xác minh; không dùng nó để huấn luyện hay chọn mô hình. Không có cột giá trong hai file này.

Đặc trưng đầu tiên: khoảng cách đường chim bay (m) đến trường học `amenity=school`, bệnh viện `amenity=hospital`, công viên `leisure=park` gần nhất trong 3 km, kèm cờ không tìm thấy. Khoảng cách đến node/tâm bounding box đại diện công trình, không phải cổng vào hay quãng đường đi bộ. Vùng không đủ đệm tìm kiếm được ghi thiếu. Không có đối tượng OSM trong 3 km không chứng minh thực tế không có tiện ích; không thay thiếu bằng khoảng cách 0 m.

Đây là tiện ích được gắn tag trên bản đồ, chưa chứng minh sở hữu công hay khả năng tiếp cận. Không đếm các cơ sở khi chưa xử lý node/way/relation biểu diễn cùng một cơ sở. Chưa suy ra mặt tiền, chiều rộng kiệt/hẻm hoặc ô tô vào được; những thuộc tính đó cần bằng chứng từ tin đăng/khảo sát hoặc dữ liệu đường phù hợp.

## Thử nghiệm mô hình sau này

Giữ v3 làm mốc, tạo phiên bản mới thay vì sửa model cũ. Đánh giá mô hình cơ sở và mô hình thêm vị trí trên cùng cohort/split; báo cáo riêng mẫu có/thiếu đặc trưng và theo nguồn. Không chỉ lọc 73 tin Chợ Tốt rồi kết luận cải thiện trên toàn bộ dữ liệu. Không dùng giá/mô tả giá làm đặc trưng; xử lý trùng tài sản và xem xét nhóm vị trí để tránh rò rỉ.

Snapshot OSM hiện tại chưa chứng minh trạng thái tiện ích ở ngày đăng các tin cũ. Nếu thử nghiệm dự đoán lịch sử, cần dữ liệu bản đồ tương ứng hoặc ghi rõ giới hạn thời gian; kết quả không tự chứng minh khả năng dự đoán tương lai. Chọn model trên validation phát triển; tập kiểm chứng mới vẫn cần thu thập độc lập theo quy trình đã chốt.

## Nguồn và giấy phép

© OpenStreetMap contributors. Dữ liệu OSM theo ODbL 1.0; ghi công và xử lý nghĩa vụ giấy phép khi phân phối dữ liệu phái sinh. Giữ timestamp, khung truy vấn, ID OSM, SHA-256 của phản hồi và nguồn trong metadata. Không coi dữ liệu mở là dữ liệu không có điều kiện sử dụng.

- [Copyright và giấy phép OpenStreetMap](https://www.openstreetmap.org/copyright).
- [Overpass QL: truy vấn nwr và out center](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL).
- [Máy chủ Overpass công cộng và chính sách tài nguyên](https://wiki.openstreetmap.org/wiki/Overpass_API#Public_Overpass_API_instances).
- [Định nghĩa trường học](https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dschool), [bệnh viện](https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dhospital).
