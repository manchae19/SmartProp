# Bổ sung vị trí và tiện ích cho SmartProp

**Đã rà soát cụ thể 20 tin:** [báo cáo và bảng đối chiếu](property_location_pilot/README.md). Tra 18 truy vấn tinh chỉnh: 1 tin khớp kiệt 59 Trương Chí Cương, 16 tin khớp đường, 1 tin có ứng viên chưa khớp, 2 tin không có kết quả. Chưa có vị trí căn nhà được xác minh. Đã phát hiện ứng viên đường trùng tên ở Hội An/Quế Sơn trong kết quả cũ; số 63 trước đây chỉ là khớp tên đường/vùng rộng. [Kiểm chứng nguồn/cache/model giữ nguyên](property_location_pilot/independent_verification.json).

**Đã tra địa chỉ ngày 13/10/2026:** [báo cáo và 80 liên kết Google Maps](address_pilot/README.md). Thực hiện 65 truy vấn tên đường khác nhau qua OSM/Nominatim cho 80 tin, tất cả HTTP 200 và có cache. 63 tin có ứng viên khớp đường/vùng Đà Nẵng, 9 tin có kết quả chưa khớp đủ điều kiện, 8 tin không tìm thấy. Chưa xác minh vị trí căn nhà hoặc đưa tọa độ đường vào XGBoost. [Kiểm chứng độc lập dữ liệu/model và cache](address_pilot/independent_verification.json).

**Kiểm tra tải chi tiết 80 tin:** [checkpoint và phản hồi nguồn](detail_review/README.md). Đã ưu tiên 30 tin dùng chung điểm với nhiều đường; URL thử `chotot:133955557` trả HTTP 403/Cloudflare. 79 URL còn lại chưa được yêu cầu. Chưa lấy được mô tả chi tiết mới. [Kiểm chứng checkpoint](detail_review/verification.json). Dữ liệu/model cũ và bản rà soát 80 tiêu đề giữ nguyên.

**Đã hoàn tất rà soát 80 ứng viên:** [báo cáo từng tin và bằng chứng](candidate_review/README.md). Có 25 lời khai kiệt/hẻm, 12 mặt tiền/mặt phố, 43 chưa rõ; 4 lời khai chiều rộng hẻm, 10 lời khai tiếp cận ô tô. 30 tin dùng tọa độ còn xuất hiện với nhiều tên đường nguồn. Đây là thông tin trích từ tiêu đề, chưa xác minh thực tế; chưa có vị trí được nâng thành đã xác minh. [Kết quả kiểm chứng 240 dòng bằng chứng](candidate_review/verification.json). Lần thử tải OSM sau rà soát vẫn trả HTTP 504.

Ngày 12/10/2026: đã rà soát 8.509 ID duy nhất. Có 2.752 tin chứa tọa độ hợp lệ về số (844 cặp khác nhau), đều từ Chợ Tốt. Tọa độ chưa được xác minh ở cấp bất động sản và chưa có bằng chứng quyền tái sử dụng để train.

| Nhóm | Số tin |
| --- | ---: |
| Eligible có tọa độ để xác minh | 80 |
| Eligible còn cần định vị | 2.002 |
| Train v3 có tọa độ | 67 |
| Validation v3 có tọa độ | 6 |
| Tọa độ đã xác minh và được duyệt dùng ML | 0 |

Cả 73 train/validation có tọa độ đều thuộc nhà ở. 2.296 tin dùng cùng một cặp tọa độ với tin khác; điểm lặp nhiều nhất có 98 ID. Không tự coi đây là tọa độ sai hay tin trùng. Số tin không đồng nghĩa số tài sản vật lý độc lập.

- [Báo cáo audit đã chốt](audit_runs/0f2be923900adb3e/README.md).
- [Độ phủ theo nguồn và cohort](audit_runs/0f2be923900adb3e/coverage.csv).
- [Toàn bộ vị trí nguồn](audit_runs/0f2be923900adb3e/location_audit.csv).
- [Bản làm việc xác minh 80 ứng viên](coordinate_review.csv), chưa duyệt.
- [2.002 tin cần định vị](audit_runs/0f2be923900adb3e/geocoding_queue.csv).
- [Kiểm chứng dữ liệu và model giữ nguyên](verification.json).
- [Trạng thái tải OSM](download_status.json).
- [Hướng dẫn, điều kiện sử dụng và lệnh chạy](../../GEOSPATIAL_FEATURES.md).

Đã viết công cụ tải/cache snapshot OSM và tính khoảng cách đường chim bay đến trường học, bệnh viện, công viên trong 3 km. **Chưa tải được snapshot thật**: máy chủ chính quá tải HTTP 504, máy chủ dự phòng HTTP 500 và lỗi chứng chỉ. Không tắt TLS. **Chưa tạo đặc trưng khoảng cách thật hoặc huấn luyện model vị trí.** 9 kiểm thử dùng dữ liệu tổng hợp tách biệt đã đạt; không đưa fixture vào đồ án.

20 snapshot raw, toàn bộ output collection và output dữ liệu/model v3 đã được đối chiếu SHA-256. Raw, giá, diện tích, cách chia tập và model v3 giữ nguyên. V3 vẫn dùng được làm mô hình cơ sở. Sau khi tải OSM thành công, xác minh vị trí và nguồn/quyền dữ liệu để tạo một phiên bản đặc trưng mới; không tự lấy tọa độ Google hoặc tâm phường làm tọa độ căn nhà.

© OpenStreetMap contributors — dữ liệu ODbL 1.0. [Giấy phép và ghi công](https://www.openstreetmap.org/copyright). [Danh sách máy chủ Overpass](https://wiki.openstreetmap.org/wiki/Overpass_API#Public_Overpass_API_instances).
