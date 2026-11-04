# SmartProp — Local V18 kiểm thử đọc PASS, đã ghi nhận hoạt động đăng nhập (2026-11-02)

**Migration, schema, startup và kiểm thử đọc đã PASS.** Ngày2026-11-02, người dùng xác nhận chính mình đã đăng nhập SmartProp trong thời gian kiểm thử và cho biết phiên tăng11→12 có khả năng do lần đăng nhập này. Đã ghi nhận giải thích; chưa đối chiếu thời gian tạo để khẳng định quan hệ nhân quả. Không xóa hoặc thay đổi phiên, không chạy thêm DB tests/DDL để cập nhật báo cáo.

## Flyway và bảo toàn dữ liệu

Nhánh backend-huy-latest, HEADd0c5943 không đổi. Chỉ MySQL8.0.46 tại127.0.0.1:3306/smartprop. Tổng48 bảng. History:

| Version | Type | Checksum | Success |
|---|---|---:|---|
|13|BASELINE|NULL|YES|
|14 crawler gốc|SQL|-1382804267|YES|
|17 Local Broker|SQL|675090364|YES|
|18 Local Avatar/Google schema|SQL|-1428745198|YES|

V17/V18 đã được thực thi đúng một lần theo phê duyệt trước đó. Lượt tiếp tục này chỉ validate/read/tests, **không migrate lại**, không repair/baseline/import/seed. V13–V16 chuẩn và V14 crawler Local vẫn nguyên hash/checksum. Target Local18; location legacy-hybrid-local riêng. Database mới vẫn dùng migrations V1–V16 chuẩn, không trộn hai locations.

Snapshot được chấp nhận sau xác nhận của người dùng giữ đúng48 bảng,11 sessions. **Toàn bộ48 bảng không đổi trong các cửa sổ kiểm thử Maven/API đã hoàn tất**. Lần chốt sau đó ghi nhận12 sessions, chỉ rowcount/checksum auth_sessions đổi; toàn bộ schema, history, trigger và47 bảng còn lại giữ nguyên. Người dùng đã xác nhận hoạt động đăng nhập và nêu khả năng giải thích phiên12; đây là thông tin do người dùng cung cấp, chưa phải kết luận đối chiếu độc lập. Không sửa dữ liệu hoặc ghi đè baseline. Hai users,16 properties,32 property_images,3204 external_listings,332 duplicate groups được giữ nguyên. Ba bảng broker_applications,user_avatars,user_external_identities còn0 dòng. Holdouts983, suspected duplicates1024, UNVERIFIED3204; VALID1723/NEEDS_REVIEW1419/REJECTED62.

Backup gốc được duyệt3187268 bytes và backup mới ngay trước migrate vẫn nguyên SHA256/dấu hoàn tất. **Chưa thử restore**. Xem execution-receipt.json và plan.json để biết đường dẫn/hash. Không đưa backup vào Git.

## Kiểm thử hoàn tất sau xác nhận

| Hạng mục | Kết quả |
|---|---|
|Flyway Local Validate nghiêm ngặt|PASS; không ignore pending/checksum/missing/future|
|Maven Wrapper package|PASS:57 tests,53 passed,4 skipped,0 failures/errors|
|MySQL/HTTP integration tests|4/4 PASS, không skipped|
|Hibernate ddl-auto validate / Spring Boot|PASS, profile Local rõ ràng,48 bảng|
|Recommendation SAFE|HTTP200 cho ba ngân sách; kết quả rỗng đúng eligibility/verification hiện tại|
|Recommendation INTERNAL_DEMO|HTTP200,10 tin/5 khu vực mỗi ca chính; quality/holdout/dedup đã kiểm|
|Demo thiếu/sai key|HTTP403|
|Ngân sách0|HTTP400|
|Broker GET có xác thực|HTTP200, đọc trạng thái hiện có; không submit/review hồ sơ|
|Avatar GET có xác thực|HTTP200, enabled=true, available=false do bảng chưa có ảnh|
|Avatar content khi chưa có ảnh|HTTP404 đúng thiết kế|
|Broker/Avatar/Admin anonymous|HTTP401|
|Broker/Avatar service trên MySQL thật|PASS, đọc bằng existing active user, không tạo account|
|Google config|HTTP200, available=false; Google OAuth vẫn tắt|
|Bảo toàn trong các cửa sổ Maven/API hoàn tất|PASS,48 bảng không đổi,11 sessions|
|Bảo toàn tại lần chốt cuối|auth_sessions11→12; người dùng đã xác nhận đăng nhập, có khả năng liên quan; các bảng khác giữ nguyên. Snapshot tổng thể không được coi là bất biến|

Ba ca2 tỷ LIVING ALL,5 tỷ INVESTMENT HOUSE,3 tỷ RENTAL APARTMENT có118/405/30 ứng viên demo. Không có REJECTED,holdout hoặc duplicate group chứa holdout lọt kết quả. NEEDS_REVIEW chỉ theo whitelist demo kèm cảnh báo; public SAFE không hiển thị UNVERIFIED.

Các GET có xác thực dùng session/user thật đã tồn tại, token chỉ ký trong bộ nhớ bằng key riêng của Spring test process. Không gọi login/register/refresh, không tạo/cập nhật session, không gửi X-Session-Activity. Bốn skipped là valuation history tests cũ chưa bật môi trường riêng; không phải lỗi Broker/Avatar hoặc truy cập database demo.

Không tuyên bố đã nghiệm thu các thao tác ghi như submit/review Broker, upload/delete Avatar, đăng nhập/refresh hay Google OAuth. Các thao tác đó cố ý chưa chạy. Không thay đổi XGBoost, VPS, .env, ListingCard.vue hoặc mã Vue trong lượt tiếp tục. Không commit/push/merge. Đã ghi nhận giải thích hoạt động đăng nhập của người dùng; không yêu cầu xác nhận lại cho việc ghi nhận này. Không cần kiểm tra DB bổ sung chỉ để cập nhật báo cáo, và không cần migrate lại. Nếu cần chứng minh chính xác phiên nào thuộc lần đăng nhập nào, chỉ đọc thời gian tạo phiên trong một bước riêng; hiện chưa thực hiện.

## Cách chạy hiện tại

Terminal Backend tại F:/SmartProp:

```powershell
python -X utf8 backend/scripts/run-backend-local.py --check
python -X utf8 backend/scripts/run-backend-local.py --port 8080
```

Launcher dùng Local profile, Broker/Avatar bật, Google ép tắt, Recommendation SAFE; không startup migration/import/seed. Nếu8080 đang dùng, chọn8082; không dừng process khác. Dùng launcher full Backend này cho Local đã lên18; không dùng launcher Advisor cũ chỉ chấp nhận history13/14.

Terminal Vue:

```powershell
cd F:/SmartProp/frontend/vue.ui
npm.cmd run dev
```

Mở http://127.0.0.1:5173/advisor (hoặc cổng Vite thông báo). Khi Backend dùng8082, đặt $env:SMARTPROP_DEV_API_TARGET='http://127.0.0.1:8082' trước npm run dev. Mã Advisor/GIS đã giữ nguyên; không tạo tọa độ/ghim giả. Các Backend test process do harness tạo đã dừng; không tự dừng ứng dụng của người dùng hoặc để lại server test lâu dài.

## Bằng chứng và lịch sử điểm dừng

- `.scratch/flyway-local-forward/execution-receipt.json`,local-migrate.log:V17/V18 đã PASS.
- `plan.json`:snapshot45 bảng được duyệt ban đầu, không ghi đè.
- `drift-report.json`,drift-snapshot.json:bằng chứng điểm dừng10→11 sessions trước xác nhận; giữ nguyên để truy vết.
- `acceptance/accepted-baseline.json`:ghi rõ người dùng xác nhận đăng nhập/chạy ứng dụng và snapshot48 bảng/11 sessions được chấp nhận.
- `acceptance/final-evidence.json`,final-snapshot.json:số liệu cuối, chứng cứ test đã PASS và sai lệch phiên12 sau test.
- `acceptance/latest-difference.json`:bằng chứng gốc auth_sessions11→12, giữ nguyên. `acceptance/user-login-confirmation.json`:lời xác nhận đăng nhập và mức độ quy kết có khả năng, chưa kiểm chứng độc lập.
- `acceptance/api/live-result.json`:API thật hai mode, budgets,Top Areas/Properties,scores/explanations/source và SQL safety checks; credentials/demo key không được ghi vào artifact.
- `.scratch/backend-huy-integration/maven-integration.log`,build/surefire-reports/:57 tests hoàn tất; cả4 actual-MySQL tests PASS.
- Báo cáo dừng trước xác nhận được giữ tại EXECUTION_REPORT_BEFORE_USER_CONFIRMATION.md. Không coi report dừng cũ là trạng thái cuối hiện tại.
