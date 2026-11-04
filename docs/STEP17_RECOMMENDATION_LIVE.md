# SmartProp — Bước17 Recommendation thực tế (2026-11-02)

**Kết nối PASS. Có kết quả Safe thật mà không sửa dữ liệu.** Nhánh backend-huy-latest, HEADd0c5943 không đổi. Không ghi MySQL,không chuyển VERIFIED,không publish/sửa giá,không sửa Broker/Avatar/Google/Flyway/XGBoost,không commit/push/merge.

## 1. Process,401 và cấu hình kết nối

Khi bắt đầu, cả Get-NetTCPConnection/netstat và kết nối TCP/HTTP trực tiếp đều cho thấy **không có listener tại8080/5173**; do đó không có PID Backend đang chiếm8080 tại thời điểm đó. Java PID23328 khi quan sát thuộc JRE của VSCode redhat.java, không phải listener Backend. Không thể truy lại chính xác PID của lần401 trước sau khi process đã đóng; không suy đoán PID lịch sử.

Người dùng xác nhận thường chạy bằng Maven/IDE. Đã kiểm tra thấy:

- JAR cũ backend/target (trước build,73654855 bytes) không chứa RecommendationController và không có literal matcher /api/v1/recommendations trong SecurityConfig.class. JAR mới đã kiểm thử trong.scratch có cả hai.
- Chạy bản JAR cũ được lưu riêng trên8081 với JDBC read-only đã **tái hiện HTTP401** cho POST/api/v1/recommendations. Đây là tái hiện lỗi của artifact cũ, không phải bằng chứng rằng một PID lịch sử cụ thể đã chạy artifact đó.
- Source hiện tại đã permitAll đúng **POST /api/v1/recommendations**; các route khác giữ policy cũ, anyRequest denyAll. Không sửa SecurityConfig hoặc authentication.
- Công cụ urllib mặc định không bypass proxy cho127.0.0.1 trong môi trường công cụ. Vì vậy dùng ProxyHandler({}) cho mọi kết luận HTTP trực tiếp và xác minh độc lập qua Vite/trình duyệt. Không gán tất cả401 cũ cho Spring Security chỉ dựa vào probe qua proxy.

Đã lưu artifact cũ tại.scratch/step17/previous-target-backend.jar rồi dùng Maven Wrapper clean package vào đúng **F:/SmartProp/backend/target**. Chỉ dọn thư mục build đã xác định,không reset/clean Git hoặc xóa file nguồn. Maven Clean Plugin ban đầu bị sandbox chặn tải; sau khi cho phép truy cập Maven Central,clean/package PASS. Không tự đổi bất kỳ migration/checksum/history nào.

Artifact chuẩn sau build: backend/target/smartprop-backend-0.1.0.jar,SHA256 `ceec9f4aebc20ec6e424bf3a11700a85fa5de164b80fd5194cbfe1d1189ed98c`.

Trong lượt nghiệm thu, đã đối chiếu bằng Get-NetTCPConnection và Win32_Process:

| Cổng | PID | Executable / artifact |
|---|---:|---|
|8080|3496|F:/SmartProp/.scratch/devtools/jdk-21.0.12.1+1/bin/java.exe,canonical backend/target JAR|
|5173|29100|C:/Program Files/nodejs/node.exe,Vite của frontend/vue.ui|

Cả hai là process do harness tạo,đã dừng khi test hoàn tất; không dừng process của người dùng. Không để lại server ngầm và không tuyên bố8080 vẫn đang phục vụ sau test.

Vite effective settings:target http://127.0.0.1:8080,baseURL /api/v1,proxy /api giữ nguyên path. Đã gửi cùng request trực tiếp8080 và qua5173,trả HTTP200/mode SAFE cùng contract. Không gắn token/demo key để vượt401. Các GET/users/me,/admin/users,/users/me/sessions và route không tồn tại vẫn401; budget0 trả400. Không mở các endpoint khác.

## 2. Vì sao Safe rỗng ở các ngân sách trước

Audit read-only tại127.0.0.1:3306/smartprop,MySQL8.0.46,UUID60f0e116-d443-11f1-bdbf-7085c2fe30d2:

- **16/16 properties hiện PUBLISHED**,SALE,VND,TOTAL,price>0,area>0,không deleted/expired. Tất cả đạt bộ lọc cơ bản Recommendation,nhưng giá từ **5,5 đến35 tỷ**.
-16 tọa độ có SRID4326 và nằm trong phạm vi hiển thị bản đồ,32 ảnh còn hiệu lực. Danh sách16 ID,currency/price unit,giá,diện tích,coords,ngày publish/expiry và số ảnh ở internal_properties_review.csv. Không nhầm ST_X/ST_Y với latitude/longitude của SRS4326:diagnostic dùng ST_Latitude/ST_Longitude; frontend dùng DTO public.
-Với ngân sách2/3/5 tỷ,không tin nội bộ nào đạt price<=budget. Không nâng ngân sách ngầm hoặc trả tin vượt ngân sách. Đã thêm lựa chọn nhanh10 tỷ ở form để người dùng chủ động thử,kèm giữ nguyên mặc định2 tỷ.
-External3204 vẫnUNVERIFIED,Safe yêu cầuVALID+VERIFIED nên không xuất hiện. Các số VALID1723,NEEDS_REVIEW1419,REJECTED62;holdout983;duplicate groups332 giữ nguyên.

Vì vậy Safe0 ở ca2–3–5 tỷ là **kết quả lọc đúng**,không cần sửa giá/trạng thái hay làm yếu quality gate.

| Request thật | HTTP | Tin Safe | Khu vực |
|---|---:|---:|---:|
|2 tỷ,LIVING,ALL|200|0|0|
|5 tỷ,INVESTMENT,HOUSE|200|0|0|
|3 tỷ,RENTAL,APARTMENT|200|0|0|
|6 tỷ,LIVING,APARTMENT|200|1|1|
|10 tỷ,LIVING,ALL|200|8|5|

Các kết quả dương đều là PROPERTY/PLATFORM_PUBLISHED từ MySQL hiện có;không seed,không mock API,không dùng crawler UNVERIFIED. PUBLISHED là trạng thái duyệt của nền tảng,không chứng minh giá giao dịch/pháp lý hoặc độ chính xác tọa độ.

Top Areas thật ở10 tỷ:

| Địa bàn / phường | Điểm | Số mẫu |
|---|---:|---:|
| Thanh Khê / An Khê | 96.63 | 1 |
| Sơn Trà / Nại Hiên Đông | 90.25 | 1 |
| Liên Chiểu / Hòa Minh | 89.1 | 1 |
| Thanh Khê / Thanh Khê Đông | 85.0 | 1 |
| Hải Châu / Hòa Cường Bắc | 78.98 | 2 |

Có một record `7e6c0fcf-a092-48ec-ae9e-f2be0ee159aa` có tọa độ trùng viewport mặc định16.0544/108.2022. Đã đưa vào ghi chú rà soát provenance:không kết luận tọa độ giả và không tự sửa/xóa. Record giá16 tỷ này không nằm trong ca10 tỷ đã nghiệm thu. Các ghim kiểm thử lấy từ8 DTO public tương ứng chính8 ID kết quả,không lấy tâm khu vực thay thế.

## 3. Danh sách crawler đề xuất xác minh — chưa duyệt/chưa cập nhật

Đã lọc **1153 ứng viên để con người rà soát**,không phải1153 tin VERIFIED hoặc nguồn cung được xác nhận hiện còn bán. Điều kiện:VALID,issues rỗng,SALE,giá/diện tích dương,loại hỗ trợ,URL HTTP(S) hợp lệ,không protected holdout,không thuộc nhóm có holdout,không cờ duplicate vô nhóm;chỉ một đại diện nếu có nhóm. Loại2051 tin khỏi đợt đầu; số lý do trong data-audit.json có chồng lấn,không cộng trực tiếp.

Nguồn ứng viên:alonhadat25,cafeland373,chotot56,homedy347,nhadat24h352. Loại:nhà802,đất258,căn hộ93. Collected_at10–11/10/2026 là thời gian thu thập,không phải xác nhận ngày đăng hoặc còn bán hôm nay. Chưa truy cập lại hoặc xác minh liên hệ các URL.

- external_manual_verification_candidates.csv:đầy đủ1153 ID/record_key,URL,giá,diện tích,địa bàn,basis và flags.
- verification_pilot_30.csv:đề xuất30 record đa dạng nguồn/loại/khu vực để duyệt trước;review_decision=PENDING,mọi mục xác minh=NOT_CHECKED.
- external_excluded.csv:2051 bản ghi và lý do loại.
- internal_properties_review.csv:16 properties;không có đề xuất auto-publish hoặc patch giá.

Nếu tất cả được xác minh thành công thì trong tập1153 có75 tin giá<=2 tỷ,180 tin<=3 tỷ,496 tin<=5 tỷ;đây chỉ là **khả năng theo trường giá**,không phải kết quả Safe hiện tại hoặc lời hứa xác minh được.

Đợt30 record đề xuất (URL và checklist đầy đủ trong CSV):

| record_key | Nguồn | Loại | Địa bàn |
|---|---|---|---|
| `alonhadat:19135848` | alonhadat | Nhà ở | Cẩm Lệ |
| `alonhadat:18672237` | alonhadat | Nhà ở | Hải Châu |
| `alonhadat:18727522` | alonhadat | Nhà ở | Liên Chiểu |
| `alonhadat:19132352` | alonhadat | Nhà ở | Ngũ Hành Sơn |
| `alonhadat:18777161` | alonhadat | Nhà ở | Thanh Khê |
| `alonhadat:18976983` | alonhadat | Đất nền | Liên Chiểu |
| `alonhadat:9620057` | alonhadat | Đất nền | Sơn Trà |
| `alonhadat:19135892` | alonhadat | Đất nền | Thanh Khê |
| `cafeland:3151995` | cafeland | Căn hộ chung cư | Cẩm Lệ |
| `cafeland:3166983` | cafeland | Căn hộ chung cư | Hải Châu |
| `cafeland:3145033` | cafeland | Căn hộ chung cư | Ngũ Hành Sơn |
| `cafeland:3150181` | cafeland | Căn hộ chung cư | Sơn Trà |
| `cafeland:3179962` | cafeland | Căn hộ chung cư | Thanh Khê |
| `cafeland:3144990` | cafeland | Nhà ở | Cẩm Lệ |
| `cafeland:3173265` | cafeland | Nhà ở | Hòa Vang |
| `cafeland:3144937` | cafeland | Nhà ở | Hải Châu |
| `cafeland:3146716` | cafeland | Nhà ở | Ngũ Hành Sơn |
| `cafeland:3144978` | cafeland | Nhà ở | Sơn Trà |
| `cafeland:3144933` | cafeland | Nhà ở | Thanh Khê |
| `cafeland:3150127` | cafeland | Đất nền | Cẩm Lệ |
| `cafeland:3145203` | cafeland | Đất nền | Hòa Vang |
| `cafeland:3145050` | cafeland | Đất nền | Hải Châu |
| `cafeland:3144967` | cafeland | Đất nền | Ngũ Hành Sơn |
| `cafeland:3145013` | cafeland | Đất nền | Sơn Trà |
| `cafeland:3145176` | cafeland | Đất nền | Thanh Khê |
| `chotot:134925160` | chotot | Nhà ở | Cẩm Lệ |
| `chotot:135152455` | chotot | Nhà ở | Hải Châu |
| `chotot:135127334` | chotot | Nhà ở | Liên Chiểu |
| `chotot:135162714` | chotot | Nhà ở | Ngũ Hành Sơn |
| `chotot:135150835` | chotot | Nhà ở | Sơn Trà |

Quy trình trước bất kỳ quyết định VERIFIED:

1. Duyệt danh sách ID và định nghĩa mức xác minh. Giữ UNVERIFIED trong lúc review; không nhập lại dữ liệu.
2. Mở đúng URL/ID nguồn,ghi thời điểm và bằng chứng;HTTP200 đơn thuần không chứng minh tin còn bán.
3. Đối chiếu một tài sản/một giao dịch bán,giá tổng VND,diện tích,loại,địa bàn và freshness;đặc biệt transaction_basis suy ra URL phải có bằng chứng nội dung bán. Bất nhất/404/hết tin/đa tài sản giữ lại để xử lý,không coi là đã xác minh.
4. Kiểm tra lại holdout và toàn bộ duplicate group ở thời điểm đề xuất thay đổi;không làm lộ holdout hoặc chọn một đại diện có liên hệ tới holdout. So khớp provenance với tin platform để tránh trình bày hai nguồn như hai tài sản chắc chắn khác nhau.
5. Muốn khẳng định hiện còn bán hoặc vị trí căn nhà thì cần bằng chứng cập nhật từ nguồn/người có thẩm quyền. Không suy diễn từ địa chỉ chung hoặc tâm khu vực. Dữ liệu external hiện chưa có contract tọa độ công khai cho FE;việc xác minh nguồn không tự tạo ghim.
6. Ghi quyết định,người review,ngày review,bằng chứng và thời hạn rà soát lại vào hồ sơ cục bộ. Chỉ sau người dùng duyệt **đúng từng ID và mức thay đổi** mới chuẩn bị thao tác cập nhật có precondition/backup/audit trail;không có script UPDATE hoặc thay đổi schema được thực hiện trong Bước17.

Hiện đã có gợi ý thật từ16 tin nội bộ nên **không cần sửa dữ liệu để nghiệm thu kết nối**. Xác minh crawler là công việc tăng độ phủ riêng,chờ duyệt;không yêu cầu phê duyệt hàng loạt1153 bản ghi.

## 4. Kiểm thử và bảo toàn

| Hạng mục | Kết quả |
|---|---|
|Maven Wrapper clean package|PASS:57 tests,52 passed,5 skipped,0 failures/errors|
|Vue tests/build|PASS:13/13 tests,Vite build thành công|
|Runtime guard Python|PASS:4 tests kiểm artifact,read-only,port bị chiếm và target Local|
|POST Recommendation trực tiếp8080|PASS,không còn401 ở runtime đúng|
|FE5173 → Backend8080 → MySQL|PASS,request thật qua Vite proxy|
|Loading,empty,error/retry,form filters|PASS;offline test chỉ abort request,không mock payload|
|Positive Safe cards/Top Areas|PASS:8 tin,5 khu vực thật ở10 tỷ|
|GIS chọn hai chiều|PASS:thẻ→ghim,ghim→thẻ,đúng8 ID/coords từ public DTO|
|OSM|12 tile thực tải được,0 lỗi,attribution hiện|
|Desktop/mobile|PASS1440×1000,390×844 và360×800,không tràn ngang|
|Authentication boundaries|Protected GET vẫn401,unknown route401,budget0=400;không gọi login/refresh hoặc mutate session|
|Source records/history|CSV audit properties/external trước-sau giống từng byte,Flyway history13/14/17/18 không đổi|
|Source ngoài phạm vi|Broker,Avatar,Google,SecurityConfig,migration SQL,pom,.env,ListingCard không đổi hash|

Năm skipped là4 test valuation history chưa bật môi trường riêng và1 authenticated-read không có session hợp lệ;không tạo phiên/tài khoản để ép test chạy. Bài kiểm thử chạy pool JDBC read-only với SET SESSION TRANSACTION READ ONLY,tắt seed/import/startup migrate;không chạy MySQL demo13306 hoặc VPS. Không dùng thẻ test fixture làm kết quả live. Vite/plugin có warning timing khi build,exit0;không phải lỗi bundle.

## 5. Chạy lại đúng dịch vụ

Chạy hai terminal riêng tại F:/SmartProp. Launcher mới chỉ dùng canonical backend/target,kiểm có controller/matcher và độ mới source,JDK21,branch đúng,cổng trống. Nếu8080 đã bị chiếm thì từ chối,chọn8082;không dừng process không rõ nguồn.

Terminal Backend kiểm thử Recommendation **chỉ đọc**:

```powershell
python -X utf8 backend/scripts/run-recommendation-local.py --check
python -X utf8 backend/scripts/run-recommendation-local.py --port 8080
```

Terminal Vue:

```powershell
cd F:/SmartProp/frontend/vue.ui
$env:SMARTPROP_DEV_API_TARGET='http://127.0.0.1:8080'
$env:VITE_API_BASE_URL='/api/v1'
$env:VITE_ENABLE_REFRESH='false'
npm.cmd run dev
```

Mở http://127.0.0.1:5173/advisor. Chọn10 tỷ/Tất cả loại để thấy8 tin,hoặc6 tỷ/Căn hộ để thấy1 tin theo dữ liệu đã audit. Bộ lọc còn lại để trống khi thử lần đầu.

Chế độ launcher này dành cho nghiệm thu đọc Recommendation,không dùng để login/register/upload vì các thao tác đó cần ghi DB. Nó không thay SecurityConfig hoặc backend authentication đang chạy khác;không xóa chức năng tài khoản. Để dùng hệ thống nghiệp vụ đầy đủ,hãy dùng launcher Backend đầy đủ hiện có và quyền ghi được người dùng cho phép riêng,giữ nguyên chính sách public Recommendation.

Nếu vẫn chạy Maven/IDE:chọn đúng project backend/pom.xml,main vn.smartprop.SmartPropApplication,JDK21 và duy nhất Spring profile hybrid-local-existing-v13 cho Local này. Dùng env riêng hiện có cho DB/JWT,không hardcode vào run arguments. Giữ Flyway startup=false,SQL init=never,ddl-auto=validate,seed/import tắt,Recommendation UNVERIFIED=false. Reload Maven project/rebuild sau đổi nhánh;không chạy lại classpath/JAR cũ. Không thay migration profile chuẩn của database mới. Không chỉnh file cấu hình IDE bí mật trong lượt này.

Trong công cụ HTTP có proxy,thêm localhost/127.0.0.1/::1 vào no-proxy hoặc dùng request trực tiếp;launcher mới đặt NO_PROXY cho process con. Không dùng cách bỏ authentication để chữa lỗi kết nối sai runtime.

## 6. File thay đổi và bằng chứng

- `.gitignore`
- `backend/scripts/run-recommendation-local.py`
- `backend/scripts/test_recommendation_runtime.py`
- `frontend/vue.ui/user/views/AdvisorView.vue`
- `frontend/vue.ui/e2e/advisor.live.mjs`
- `docs/ADVISOR_FRONTEND.md`
- `docs/STEP17_RECOMMENDATION_LIVE.md`

backend/target là artifact build được cập nhật,bản cũ giữ ở.scratch. Không thay bất kỳ dữ liệu huấn luyện nào. Bằng chứng tại.scratch/step17/:runtime-before.json,stale-reproduction.json,stack-result.json,maven.log,vue-tests.log,vue-build.log,final-audit.json,browser/advisor-browser-result.json,ảnh desktop/mobile và các CSV review. Các URL/ID review chỉ nằm trong hồ sơ cục bộ,không được đẩy Git.

Tham chiếu kỹ thuật cho đọc tọa độ geographic SRS:[MySQL Point Property Functions](https://dev.mysql.com/doc/refman/8.0/en/gis-point-property-functions.html). Kiểm tra phạm vi số học không xác minh vị trí vật lý.
