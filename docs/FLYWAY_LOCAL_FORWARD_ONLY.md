# SmartProp — Local forward-only Flyway plan (2026-11-02)

> Local V18/API đọc PASS: xem [FLYWAY_LOCAL_V18_RESULT.md](FLYWAY_LOCAL_V18_RESULT.md). Người dùng đã xác nhận đăng nhập trong thời gian kiểm thử; thay đổi sessions11→12 có khả năng liên quan, chưa đối chiếu độc lập. Các bảng khác không đổi. Không chạy lại apply.

**GO để xem xét/phê duyệt kế hoạch; chưa GO thực thi.** Chỉ đọc MySQL Local 127.0.0.1:3306/smartprop trong lượt này. Không baseline, migrate, repair, import, GRANT/REVOKE, commit, push hoặc merge.

## Hai lịch sử độc lập, không sửa checksum

| Cấu hình | Location | Versions | Target |
|---|---|---|---|
| MySQL Local đã có BASELINE13/crawler14 | database/legacy-hybrid-local | V14 crawler gốc, V17 Broker, V18 Avatar/Google Identity | 18 |
| Database mới theo backend-huy-latest | database/migrations | V1–V16 chuẩn | 16 |

V13 Broker, V14 Valuation, V15 Avatar/Google và V16 crawler chuẩn giữ nguyên hash trước lượt này. File Local V14 giữ đúng byte và checksum **-1382804267**, SHA256 `d56139b83c23c71581d0e6f099861270155b050d6d4585e37189a38983c3d01d`. Không có V14 valuation checksum679419338 trong location Local. Không có hai version trùng nhau trong từng location. V17/V18 Local lấy nguyên DDL tương ứng V13/V15 chuẩn, thêm chú thích nguồn; không sửa các migration đã dùng ở môi trường khác.

## Schema thực tế và chính xác phạm vi ghi được đề xuất

Database hiện có45 bảng; history chỉ BASELINE13 và SQL14 thành công. Server UUID `60f0e116-d443-11f1-bdbf-7085c2fe30d2`, MySQL8.0.46. `valuation_history` và hai bảng external khớp đầy đủ contract. Users.id BIGINT tương thích tất cả foreign key bổ sung.

| Migration Local | Bảng tạo mới | Index/constraint/dependency |
|---|---|---|
| V17 | broker_applications | PK id; UNIQUE user_id; queue(status,updated_at,id); 2 FK tới users.id; 5 CHECK cho type/status/version/consent/action |
| V18 | user_avatars | PK user_id; UNIQUE storage_key; FK user_id tới users.id |
| V18 | user_external_identities | PK id; UNIQUE(provider,subject_id); UNIQUE(user_id,provider); FK users.id; CHECK provider GOOGLE |

InnoDB tự tạo các index hỗ trợ FK nếu cần. Không có FK trực tiếp giữa Broker, Avatar, Identity và valuation_history. Không tạo lại valuation_history/external, không sửa tài khoản, vai trò, dữ liệu cũ hoặc XGBoost. **45→48 bảng** sau thành công. Flyway tự thêm2 dòng V17/V18 vào flyway_schema_history; không UPDATE/DELETE hai dòng BASELINE13/V14, không can thiệp trực tiếp bảng history.

Dữ liệu hiện tại có2 users,10 auth_sessions,16 properties,32 property_images; khác snapshot trống của báo cáo trước. Toàn bộ đã nằm trong backup/snapshot mới. Tin platform đủ điều kiện Recommendation SALE/PUBLISHED/VND/TOTAL hiện là **16**. External vẫn3204 (VALID1723, NEEDS_REVIEW1419, REJECTED62),332 duplicate groups,983 holdouts,3204 UNVERIFIED. Không seed hoặc tạo fixture trong lượt này.

## Backup và khóa kế hoạch

Backup mới: `F:\SmartProp\.scratch\flyway-local-forward\smartprop-before-local-completion-20261102T060122419637Z.sql`

- Kích thước: 3,187,268 bytes; đủ45 CREATE TABLE, dấu Dump completed, tiến trình dump exit0.
- SHA256: `e698558e8ad91451117dc700b954cfb91231c235ca7fad375ed55e699176b3c4`.
- Dump gồm dữ liệu, trigger, routines/events nếu có; dùng single-transaction, không lock table. Snapshot trước/sau dump khớp.
- **Chưa thử restore**; kiểm tra file hoàn chỉnh không đồng nghĩa đã xác minh khôi phục. Không restore lên smartprop. Backup nằm trong .scratch bị ignore, không đưa vào Git.
- Plan: `.scratch/flyway-local-forward/plan.json`; SHA256 **`f79a84c0aa83ef5b6ae11b67f72871bd122967c854c1b0880183e60802080283`**.

Script sẽ từ chối nếu UUID/host/port/database, history, bất kỳ DDL/rowcount/checksum/trigger, migration hoặc file thực thi khác kế hoạch đã duyệt. Nếu dữ liệu thay đổi hợp lệ, cần prepare/duyệt snapshot mới; không tự ghi đè kế hoạch rồi apply. Trước migrate còn tạo backup mới và kiểm lại snapshot ngay sát thao tác ghi.

## Kết quả kiểm thử thực tế

| Kiểm tra | Kết quả |
|---|---|
| Local Validate checksum/history đã áp dụng | PASS; V17/V18 được ghi rõ pending trong tiền kiểm |
| Standard Validate trên legacy Local | Từ chối đúng thiết kế do V14 khác checksum; không dùng cấu hình này cho Local |
| Contract V1–V16 chuẩn so với Local sau bổ sung dự kiến | PASS offline:47 bảng dữ liệu,92 CHECK, không sai lệch |
| Database mới thật: migrate/validate | CHƯA CHẠY; không có phê duyệt tạo/ghi database mới |
| Maven package/test | PASS:54 tests,50 passed,4 skipped,0 failures/errors |
| Python guard/schema tests | PASS:9 tests |
| Hibernate mapping trên Local hiện tại | PASS qua Spring Boot integration test, ddl-auto validate |
| Recommendation thật: safe/demo | PASS; HTTP200; demo key sai/thiếu403; budget sai400 |
| Startup full Local khi chưa có V17/V18 | Bị chặn đúng thiết kế |
| Startup sai standard hoặc thiếu profile trên crawler14 Local | Bị chặn đúng thiết kế |
| Runtime tự bật Flyway migrate | Bị chặn trước datasource initialization |
| Broker/Avatar/Google policy regression | PASS:5 tests; không phải authenticated E2E |
| Broker/Avatar/Google E2E trên bảng mới | CHỜ PHÊ DUYỆT MIGRATION và cấu hình/tài khoản thật |

Ba ca demo2B LIVING ALL,5B INVESTMENT HOUSE,3B RENTAL APARTMENT vẫn lần lượt118/405/30 ứng viên; mỗi ca10 tin và5 khu vực. Safe trả rỗng đúng quality gate hiện tại. Không REJECTED, protected holdout hoặc duplicate group chứa holdout xuất hiện. NEEDS_REVIEW chỉ whitelist nội bộ và có cảnh báo. 45 bảng giống hệt snapshot đầu sau toàn bộ test. Logs/evidence tại `.scratch/flyway-local-forward/`; Maven tại `.scratch/backend-huy-integration/maven-integration.log`.

## Lệnh xem xét — chưa chạy apply

Tại F:/SmartProp, dùng Python hoặc ai-services/.venv/Scripts/python.exe. Credentials chỉ đọc riêng từ .env vào bộ nhớ hoặc nhập kín tại terminal; không in/hardcode mật khẩu, không login-path/config-editor.

Tiền kiểm + backup (chỉ đọc database; chạy lại sẽ tạo kế hoạch/hash mới):

```powershell
python -X utf8 backend/scripts/flyway-local-forward.py --prepare
```

**Chỉ sau khi người dùng duyệt đúng kế hoạch/hash này**, lệnh ghi được đề xuất là:

```powershell
python -X utf8 backend/scripts/flyway-local-forward.py --apply --reviewed-plan-sha256 f79a84c0aa83ef5b6ae11b67f72871bd122967c854c1b0880183e60802080283
```

Script gọi Maven Wrapper với profile hybrid-local-existing-v13, location Local cố định, JDBC127.0.0.1:3306/smartprop, target18, createSchemas=false, baselineOnMigrate=false, cleanDisabled=true, outOfOrder=false. Thứ tự: tiền kiểm/snapshot → Validate lịch sử đã áp dụng (chỉ bỏ qua known pending17/18) → backup mới → migrate target18 → **Validate nghiêm ngặt, không ignore pending/missing/future/checksum** → kiểm48 bảng, schema mới và dữ liệu44 bảng cũ (history kiểm riêng).

Nếu MySQL DDL lỗi giữa chừng có thể để lại một phần bảng do auto-commit. Script dừng, lưu execution-receipt FAILED, không tự rollback/drop/repair/retry. Lần apply sau bị chặn bởi inventory/history khác kế hoạch; phải rà soát riêng. Script không chạy SQL dump backup.

## Profile runtime và cách chạy

Maven profile chỉ chọn location cho CLI; Spring profile chọn location trong JAR. Hai profile cùng tên được khai báo riêng và phải chọn rõ ràng. Không tự suy đoán/chuyển profile theo DB. Trộn profile dev/standard/local bị từ chối. Runtime không chạy Flyway migrate; chỉ đọc history và validate. Default/standard trên Local crawler14 bị từ chối. Không ghi đè .env hoặc SecurityConfig.

Sau khi migration được duyệt và hoàn thành:

```powershell
cd F:/SmartProp
python -X utf8 backend/scripts/run-backend-local.py --check
python -X utf8 backend/scripts/run-backend-local.py --port 8080
```

Launcher kiểm48 bảng/history/strict Validate trước startup, bật Broker/Avatar qua profile riêng, chặn startup seed/import, giữ recommendation safe. Google không tự bật: cần cấu hình riêng GOOGLE_LOGIN_ENABLED, client-id/client-secret hợp lệ, refresh enabled, callback/origin trùng khớp và cookie policy phù hợp Local. Không đưa Google secret/demo key vào frontend.

Trong khi chờ migration, vẫn chạy Advisor chỉ đọc:

```powershell
python -X utf8 backend/scripts/run-advisor-local.py --port 8080
```

Chỉ launcher Advisor rõ ràng mới được require-complete=false, đồng thời bắt buộc JDBC read-only/init READ ONLY và Broker/Avatar/Google tắt. Lịch sử áp dụng vẫn validate checksum; pending chỉ17/18. Không coi chế độ này là full Backend.

Vue (giữ nguyên mã Bước16):

```powershell
cd F:/SmartProp/frontend/vue.ui
npm.cmd run dev
```

Mở http://127.0.0.1:5173/advisor. Nếu8080 bận, dùng --port8082 và đặt $env:SMARTPROP_DEV_API_TARGET='http://127.0.0.1:8082' trong terminal Vue trước npm run dev. Không dừng process khác. Map giữ tile OpenStreetMap thật, không tạo ghim giả.

Đối với database mới hoàn toàn: chỉ database/migrations (V1–V16), không baseline13, không thêm legacy-hybrid-local vào cùng locations. Sau khi được phê duyệt riêng việc tạo/migrate database mới, dùng Maven profile standard-migrations và JDBC đích mới; validate đầy đủ rồi runtime Spring profile standard-migrations. Không dùng script Local này cho database mới.

## Files trong lượt chuẩn bị này

- `.gitignore`
- `backend/pom.xml`
- `backend/scripts/flyway-local-forward.py`
- `backend/scripts/mysql_schema_contract.py`
- `backend/scripts/run-advisor-local.py`
- `backend/scripts/run-backend-local.py`
- `backend/scripts/test_flyway_local_forward.py`
- `backend/src/main/java/vn/smartprop/database/MigrationProfileEnvironmentGuard.java`
- `backend/src/main/java/vn/smartprop/database/MigrationLineageConfiguration.java`
- `backend/src/main/resources/META-INF/spring.factories`
- `backend/src/main/resources/application-hybrid-local-existing-v13.yml`
- `backend/src/main/resources/application-standard-migrations.yml`
- `backend/src/test/java/vn/smartprop/database/MigrationLineageConfigurationTest.java`
- `backend/src/test/java/vn/smartprop/database/FeatureRolloutContractTest.java`
- `backend/src/test/java/vn/smartprop/recommendation/RecommendationMySqlIntegrationTest.java`
- `database/legacy-hybrid-local/V17__local_broker_applications.sql`
- `database/legacy-hybrid-local/V18__local_avatar_and_google_identity.sql`
- `docs/FLYWAY_LOCAL_FORWARD_ONLY.md`
- `docs/BACKEND_HUY_INTEGRATION.md`
- `docs/HYBRID_RECOMMENDATION_V1.md`

Các thay đổi FE đồng thời của người dùng (ListingCard, ComparisonTray, ListingsView, ListingDetailView, legacy.js) được giữ nguyên; lượt này không sửa Vue. Mã Broker/Avatar/Google/SecurityConfig và migration chuẩn không bị ghi đè. Git HEAD/branch/stash không thay đổi.
