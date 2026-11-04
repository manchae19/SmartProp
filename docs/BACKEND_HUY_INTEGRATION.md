# SmartProp — tích hợp vào backend-huy-latest

> Local V18/API đọc PASS: xem [FLYWAY_LOCAL_V18_RESULT.md](FLYWAY_LOCAL_V18_RESULT.md). Người dùng đã xác nhận đăng nhập trong thời gian kiểm thử; thay đổi sessions11→12 có khả năng liên quan, chưa đối chiếu độc lập. Các bảng khác không đổi. Không chạy lại apply.

> Cập nhật Local forward-only 2026-11-02: xem [FLYWAY_LOCAL_FORWARD_ONLY.md](FLYWAY_LOCAL_FORWARD_ONLY.md). Profile Local nay có V17/V18 pending; dùng launcher/profile mới. Các số liệu/test bên dưới là báo cáo tích hợp trước đó. Chưa migrate/repair.

Đã tích hợp Bước 14–15 và triển khai `/advisor` của Bước 16 trên `backend-huy-latest`. HEAD vẫn là `d0c5943`; không tạo commit, push, merge hoặc cherry-pick.

## Nguồn và bảo toàn thay đổi

- Bước 14 lấy từ commit `878f496`, chưa phải ancestor của nhánh mới. Mã được lấy theo từng file, không áp toàn bộ commit.
- Bước 15 lấy từ stash `14b06eb41e4bd0fa7ccbbac427907ffb65a90272` đã được kiểm thử. Stash Gemini cũ `28de2797cd903af2910cabc0bb14b2ba980a5693` được trích riêng và đối chiếu; các file cùng tên có nội dung khác nhau. Cả hai stash vẫn nguyên, không apply/pop/drop.
- Khôi phục Entities, Repositories, quality gate, import services/runner, Python/PowerShell importer, sáu class Recommendation và các tests. SecurityConfig và application.yml được chỉnh trên bản Backend mới, chỉ thêm route/flag cần thiết.
- Giữ nguyên Google OAuth, SessionPolicy, avatar, broker routes và dependencies mới. `.env` giữ nguyên hash ban đầu. `ListingCard.vue`, `ComparisonTray.vue`, `ListingsView.vue` và `legacy.js` có cập nhật đồng thời ngoài phần tích hợp; giữ nguyên các phiên bản hiện tại, không restore theo ảnh chụp cũ.

## Xung đột Flyway cần giữ rõ

| Version | MySQL Local hiện có | Nhánh Backend mới |
|---|---|---|
| 13 | BASELINE 13, schema đã có valuation_history | V13 broker applications |
| 14 | V14 crawler, checksum -1382804267 | V14 valuation history, checksum 679419338 |
| 15 | Chưa áp dụng | V15 avatar/Google identity |
| 16 | Chưa áp dụng | V16 external listings mới bổ sung |

**Validate mặc định của lịch sử Backend mới FAIL tại V14 trên database Local hiện tại.** Không repair, đổi checksum hoặc migrate để bỏ qua lỗi này.

Bản V14 crawler đúng từng byte được giữ tại `database/legacy-hybrid-local/V14__crawler_external_listings.sql`. SHA-256: `d56139b83c23c71581d0e6f099861270155b050d6d4585e37189a38983c3d01d`.

Profile Maven `hybrid-local-existing-v13` chỉ xác thực lịch sử Local đã biết, giới hạn target14; Validate profile này PASS. Profile không chứng nhận migration mới đã được áp dụng, không dùng tạo database mới và không dùng với migrate/clean/repair. V13–V15 của Backend mới giữ nguyên nội dung. V16 dành cho database theo lịch sử mới, chưa được chạy trên Local.

Local vẫn có 45 bảng, chưa có broker_applications, user_avatars, user_external_identities. Cần kế hoạch hòa giải hai lịch sử và phê duyệt schema riêng trước khi bật những tính năng cần các bảng đó. Spring Boot giữ JPA validate, SQL init never và Flyway startup false.

## Build, unit tests và integration tests

Maven Wrapper đã sửa lỗi `.Target[0]` khi cache không phải symlink. Vẫn dùng Maven 3.9.11 và JDK 21 của nhánh mới. Build tách khỏi target cũ:

```powershell
$env:JAVA_HOME = 'F:/SmartProp/.scratch/devtools/jdk-21.0.12.1+1'
$env:MAVEN_USER_HOME = 'F:/SmartProp/.scratch/backend-huy-integration/maven-home'
./backend/mvnw.cmd --batch-mode --no-transfer-progress '-Dmaven.repo.local=F:/SmartProp/.scratch/m2' '-Dsmartprop.build.directory=F:/SmartProp/.scratch/backend-huy-integration/build' -f backend/pom.xml package
```

Lượt cuối bật `SMARTPROP_HYBRID_LOCAL_TEST=true`, credentials chỉ trong process: **36 tests, 0 failures/errors, 4 skipped; 32 passed**. `RecommendationMySqlIntegrationTest` gọi HTTP/MySQL thật, kiểm budget, quality, holdout, dedup và checksum 45 bảng. Không bật biến opt-in thì test đó được skip để không tự truy cập DB. Bốn test history13xxx không bật. Python importer: **10 tests PASS**, không import lại.

Validate Local sau khi nạp DB_USER/DB_PASSWORD riêng vào process, không đặt mật khẩu trong tham số:

```powershell
./backend/mvnw.cmd --batch-mode --no-transfer-progress -f backend/pom.xml -Phybrid-local-existing-v13 '-Dflyway.url=jdbc:mysql://127.0.0.1:3306/smartprop?connectionTimeZone=UTC' '-Dflyway.schemas=smartprop' '-Dflyway.target=14' org.flywaydb:flyway-maven-plugin:11.7.2:validate
```

## Kết quả API trên Backend mới

| Ca demo nội bộ | HTTP | Ứng viên | Tin trả về |
|---|---:|---:|---:|
| 2 tỷ, LIVING, ALL | 200 | 118 | 10 |
| 5 tỷ, INVESTMENT, HOUSE | 200 | 405 | 10 |
| 3 tỷ, RENTAL, APARTMENT | 200 | 30 | 10 |

Safe mode trả HTTP200 với kết quả rỗng đúng thiết kế: properties=0, toàn bộ 3.204 external đều UNVERIFIED. Demo thiếu/sai key trả403; ngân sách0 trả400. Record, quality, holdout và nhóm trùng được đối chiếu SELECT MySQL. Không có REJECTED, holdout hoặc nhóm có holdout trong kết quả; NEEDS_REVIEW chỉ theo whitelist và có cảnh báo. Các route tài khoản/admin/avatar/broker yêu cầu đăng nhập vẫn trả401 cho anonymous; public properties trả200.

Snapshot cuối sau tất cả tests khớp snapshot đầu: **45 bảng không đổi**, gồm 3.204 listings, 332 duplicate groups, 983 holdouts. Không migrate, baseline, repair hoặc import lại. Không sửa dữ liệu XGBoost, crawler CSV hoặc VPS.

## Vue Advisor + GIS

Trang `/advisor` và menu “Tư vấn AI” giữ PageLayout và thiết kế hiện có. Bộ lọc có ngân sách, mục đích, loại, diện tích, địa bàn/phường và limit. Trang dùng API thật, hiển thị tối đa5 khu vực và10 tin với điểm, giải thích và nguồn. Không có ô nhập demo key, không gửi key, không cho client chọn nguồn. Client từ chối response demo hoặc dữ liệu chưa đủ điều kiện công khai.

GIS tái sử dụng BrowseTileMap, tile OSM thật và attribution. Chỉ lấy tọa độ từ DTO properties công khai; không suy diễn ghim tài sản từ tâm khu vực hoặc địa chỉ crawler. Dữ liệu hiện tại không có public properties để đặt marker, nên không có ghim là đúng.

Frontend có **5 unit tests PASS**, production build PASS. Trình duyệt desktop1440×1000 và mobile390×844 đã gọi API thật cho ba ngân sách, không tràn ngang, không gửi demo key, không có ghim giả. OSM trả HTTP200/PNG thật. Sandbox ban đầu chặn mạng; kiểm lại ngoài sandbox tải được tile, không bỏ kiểm chứng chỉ hoặc dùng ảnh giả.

```powershell
cd F:/SmartProp/frontend/vue.ui
npm.cmd test
npm.cmd run build
```

Test browser được lưu trong source `frontend/vue.ui/e2e/advisor.live.mjs`. Khi Backend/Vite Local đang chạy:

```powershell
node frontend/vue.ui/e2e/advisor.live.mjs http://127.0.0.1:5173 .scratch/advisor-browser
```

Các process do harness tạo đã dừng. Không dừng server phát triển khác. JAR được kiểm thử ở `.scratch/backend-huy-integration/build`; không dùng JAR cũ trong target để đánh giá nhánh mới.

## Phần còn cần hoàn thành trước rollout rộng

1. Thống nhất kế hoạch migration cho hai lịch sử trước khi bật broker/avatar/Google identity. Không coi profile legacy là đã áp dụng schema Backend mới.
2. Kiểm thử đăng nhập Google và luồng broker/avatar bằng cấu hình, tài khoản thật sau rollout schema. Lượt này kiểm bảo vệ route, không tạo tài khoản giả trên database cá nhân.
3. Cần nguồn được phép công khai và tọa độ đủ tin cậy để trình diễn thẻ tin/marker thật. Không bật public demo để lấp kết quả rỗng.

Scoring là heuristic, không phải AI cá nhân hóa đã huấn luyện, dự báo tăng giá hay lợi nhuận. Bằng chứng chi tiết ở `.scratch/backend-huy-integration/`: source inventories, restored-files.json, validation logs, Maven logs, live-result.json, final-evidence.json và `advisor-live/` với API/browser results, ảnh desktop/mobile và snapshots. Không lưu credentials trong báo cáo.

## Đối chiếu dependency với schema MySQL thật

| Thành phần của nhánh mới | Schema Local | Kết luận |
|---|---|---|
| V13 broker_applications | Chưa có | BASELINE13 không chứng minh V13 Broker đã chạy |
| V14 valuation_history | Đã có, khớp toàn bộ contract | Không tạo lại; bảng đến từ lịch sử cũ |
| V15 user_avatars, user_external_identities | Chưa có | Chưa thể kiểm thử đầy đủ Avatar/Google Identity |
| V16 external_listings, external_duplicate_groups | Đã có, khớp contract | Không chạy V16 trên Local hiện tại |

Các foreign key của Broker/History/Avatar/Identity đều tham chiếu users.id, kiểu BIGINT tương thích. Không có dependency FK trực tiếp giữa ba migration V13–V15. Xem migration-dependencies.json để biết kết quả đối chiếu từng bảng.

Phương án an toàn: giữ nguyên hai lịch sử và checksum hiện tại; thống nhất lineage với nhóm Backend trước, rồi chuẩn bị rollout chỉ tiến tới để bổ sung ba bảng còn thiếu, có precondition/schema diff và backup mới. Phiên bản bổ sung phải được kiểm tra chưa dùng trong nhánh đích. V16 hiện chỉ là đề xuất cho database theo lịch sử mới, không giải quyết tự động xung đột trên Local. Nếu bắt buộc một lịch sử mặc định chung, cần kế hoạch cutover riêng; không repair checksum, không tạo lại bảng valuation/external, không reimport 3.204 tin. Chưa thực hiện thao tác ghi nào.

## Chạy Backend và Vue Advisor với Local hiện tại

Tại F:/SmartProp, sau khi build đúng thư mục ở trên, dùng launcher riêng để chạy phiên Advisor chỉ đọc. Launcher chỉ đọc DB_USER/DB_PASSWORD/JWT_SECRET từ .env vào bộ nhớ hoặc yêu cầu nhập kín tại terminal; không sửa .env. Phải cài Python và JDK21; JAVA_HOME có thể trỏ JDK21 khác trên máy.

Terminal Backend:

```powershell
cd F:/SmartProp
python -X utf8 backend/scripts/run-advisor-local.py --check
python -X utf8 backend/scripts/run-advisor-local.py --port 8080
```

Terminal Vue:

```powershell
cd F:/SmartProp/frontend/vue.ui
npm.cmd run dev
```

Mở http://127.0.0.1:5173/advisor (hoặc cổng Vite thông báo). Nếu 8080 đang được dùng, chạy Backend với --port 8082; đặt $env:SMARTPROP_DEV_API_TARGET='http://127.0.0.1:8082' trong terminal Vue trước npm.cmd run dev. Không dừng tiến trình khác để lấy cổng.

Launcher cố định 127.0.0.1:3306/smartprop, kiểm history/checksum, giữ safe mode, không chạy Flyway/seed/import. Kết nối JDBC chỉ đọc. Broker/Avatar/Google bị tắt riêng trong phiên Advisor này do schema chưa đủ; mã nguồn, .env và cấu hình gốc các chức năng vẫn giữ. Đây không phải hướng dẫn bật toàn bộ hệ thống nghiệp vụ trên schema thiếu bảng. Ctrl+C dừng Backend do launcher tạo.

## Bảng nghiệm thu

| Hạng mục | Kết quả | Giới hạn |
|---|---|---|
| Tích hợp mã Bước14–15 và bảo toàn Backend | PASS | Chỉ thêm một route vào SecurityConfig; mã Java cũ còn lại nguyên vẹn |
| Maven package/tests | PASS | 36 tests:32 passed,4 skipped,0 lỗi |
| Python importer | PASS | 10 tests; không import lại |
| Vue unit/build | PASS | 5 tests; build lại sau cập nhật đồng thời của người dùng |
| API thật safe/demo | PASS | Safe rỗng đúng thiết kế; demo có kết quả và403 khi sai/thiếu key |
| Advisor desktop/mobile, GIS | PASS | API thật; OSM thật; không có ghim giả; chưa có public properties để thử marker thật |
| Dữ liệu MySQL | PASS | Snapshot45 bảng không đổi; 3.204 tin,332 nhóm,983 holdout |
| Flyway Validate lịch sử Local riêng | PASS | Chỉ xác minh lineage cũ,target14 |
| Flyway Validate mặc định nhánh mới | FAIL | Xung đột V14,không migrate/repair |
| E2E Broker/Avatar/Google có đăng nhập | CHƯA XÁC MINH | Bảo toàn mã/route; cần ba bảng và cấu hình/tài khoản thật |

Không commit, push, merge, migrate, repair, import lại hoặc sửa dữ liệu XGBoost/VPS trong lượt tích hợp.
