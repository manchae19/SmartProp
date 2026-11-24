# SmartProp — Bàn giao Database cho nhóm

Tài liệu dùng chung cho **tất cả thành viên** SmartProp khi cần dựng database, kiểm thử
migration, hoặc nhận baseline schema từ người quản trị.

Bổ sung cho [TEAM_SETUP.md](../TEAM_SETUP.md) (thiết lập chung) và
[database/README.md](../../database/README.md) (cấu trúc thư mục migration).

**Cập nhật:** 2026-11-24 · **Trạng thái:** baseline V21 đã kiểm chứng thực tế

---

## 1. Kiến trúc database và phân biệt môi trường

SmartProp dùng **ba môi trường MySQL riêng biệt**. Nhầm lẫn giữa chúng là nguyên nhân
hỏng dữ liệu phổ biến nhất.

| Môi trường | Cổng | Datadir | Mục đích | Ai được ghi |
|---|---:|---|---|---|
| **Local application** | 3306 | `backend/var/local-demo/mysql-data` | Database thật của nhóm | Chỉ qua app khi phát triển, có kiểm soát |
| **Staging** | 3307 | `.scratch/mysql-isolated/data` | Thử migration trước khi áp lên 3306 | Thành viên, khi test có kiểm soát |
| **E2E isolated** | 3308 | Riêng, tạo/xoá được | Test tự động có ghi dữ liệu | Test runner, xoá bất cứ lúc nào |

### Quy tắc bất biến

- **3306 là database thật.** Không chạy `flyway:migrate`, không `INSERT`/`UPDATE`/`DELETE`,
  không seed, không test cleanup. Chỉ đọc khi cần kiểm tra.
- **3307 là staging.** Dùng để thử migration. Có thể drop và dựng lại.
- **3308 là E2E.** Dùng khi test cần ghi dữ liệu (tạo listing, upload ảnh). Xoá được.

### Guard trong code

`MigrationProfileEnvironmentGuard` chỉ chấp nhận **hai URL literal**:

```java
LOCAL_URL   = "jdbc:mysql://127.0.0.1:3306/smartprop?connectionTimeZone=UTC"
STAGING_URL = "jdbc:mysql://127.0.0.1:3307/smartprop?connectionTimeZone=UTC"
```

Staging còn kiểm tra `@@datadir` phải kết thúc bằng `/mysql-isolated/data/`. Đây là
**fail-closed**: không có fallback ngầm về 3306.

> **Đã kiểm chứng:** guard từ chối mọi URL khác 3306/3307, kể cả `localhost` thay cho
> `127.0.0.1` và schema khác `smartprop`. Xem
> `MigrationLineageConfigurationTest.stagingRejectsAnyOtherHostPortOrSchema`.

---

## 2. Hai lineage migration

SmartProp có **hai lineage song song**. Không trộn lẫn.

### 2.1. Standard lineage — `database/migrations/`

Dùng cho database dựng mới từ đầu. Chạy V1 → V13 tuần tự.

```
V1__accounts_and_sessions.sql
V2__extend_accounts_and_roles.sql
...
V13__broker_applications.sql
```

Profile: `standard-migrations`

### 2.2. Legacy-hybrid-local lineage — `database/legacy-hybrid-local/`

Dùng cho database **đã có từ trước** (baseline V13 đã review). Đây là lineage của
database nhóm hiện tại.

```
V14__crawler_external_listings.sql
V17__local_broker_applications.sql
V18__local_avatar_and_google_identity.sql
V21__property_image_scan.sql
V22__property_image_analysis.sql
V23__advisor_chat_checkpoints.sql
V24__public_pre_purchase_evidence.sql
V25__flood_planned_risk_catalog.sql
```

Profile: `hybrid-local-existing-v13` (3306) và `hybrid-local-existing-v13-staging` (3307)

**Trạng thái trên `main` (2026-11-24):** V14, V17, V18, V21, V22, V23, V24, V25.
`pom.xml` đặt `<target>25</target>` cho profile này.

**Chưa có trên `main`:**

| Version | Thuộc | Trạng thái |
|---|---|---|
| V26 `property_coordinate_provenance` | PR #38 | Chưa merge |
| V27 `news_backend_v1` | PR #41 | Chưa merge |

Nếu bạn thấy V26/V27 trong worktree của mình, đó là do bạn đang ở branch của PR tương
ứng — không phải `main`. Đừng giả định `main` có chúng.

### 2.3. Research migrations — `database/research-migrations/`

Chèn vào giữa lineage legacy. Hai thư mục con:

```
database/research-migrations/
  V19__tinix_research_staging.sql
  poi/
    V20__poi_taxonomy_enrichment.sql
```

Profile `hybrid-local-existing-v13` khai báo **cả hai** location:
`legacy-hybrid-local` và `research-migrations`, nên V19/V20 được nhận đúng thứ tự.

### 2.4. Chuỗi đầy đủ của legacy-hybrid-local

```
BASELINE13 → V14 → V17 → V18 → V19 → V20 → V21 → V22 → V23 → V24 → V25
```

**Không có V15, V16** trong lineage này — chúng thuộc standard lineage. Đây là lý do
`MigrationLineageConfiguration` kiểm tra danh sách version cụ thể thay vì số nguyên liên tục.

> **Đã kiểm chứng:** `MigrationLineageConfigurationTest` (21 test) xác nhận guard từ chối
> version lạ, failed row, sai checksum crawler, và sai URL/port/schema. Các ca gap bắt buộc,
> duplicate và sai thứ tự được bổ sung bởi `MigrationLineageStrictTest` trong PR #41
> (chưa merge vào main).

---

## 3. Baseline V21 đã xác minh

Người quản trị database chuẩn bị sẵn một **baseline V21** để thành viên không phải dựng
schema từ đầu.

### 3.1. Nội dung baseline

| Hạng mục | Số lượng |
|---|---:|
| Base tables | **52** |
| Views | **4** |
| Flyway history rows | **7** (V13 → V21) |
| Dữ liệu nghiệp vụ | **0** — đã loại bỏ có chủ ý |
| Dữ liệu người dùng | **0** — đã loại bỏ có chủ ý |

### 3.2. Vì sao không có dữ liệu

Baseline dùng để **kiểm thử migration**, không phải để chạy demo. Dữ liệu thật chứa
email, bcrypt hash, session token — không được bàn giao.

Nếu cần dữ liệu để test tính năng, tự tạo fixture sau khi migrate (xem mục 8).

### 3.3. Nguồn gốc

Baseline được làm sạch từ dump V21 của database nhóm. Toàn bộ `INSERT` của 16 bảng chứa
dữ liệu thật đã bị xoá; **chỉ còn 1 dòng `INSERT` duy nhất** là `flyway_schema_history`.

> **Đã kiểm chứng:** import vào MySQL 8.4.13 cô lập cho kết quả 52 bảng, 4 view,
> 7 dòng Flyway history, 0 user, 0 property. Không lỗi.

---

## 4. Flyway history và checksum thực tế

Baseline chứa history **nguyên vẹn**, không sửa version hay checksum.

| Version | Description | Checksum |
|---|---|---|
| 13 | SmartProp_existing_V13_reviewed_2026-11-01 (BASELINE) | `NULL` |
| 14 | crawler external listings | **`-1382804267`** |
| 17 | local broker applications | `675090364` |
| 18 | local avatar and google identity | `-1428745198` |
| 19 | tinix research staging | `96887547` |
| 20 | poi taxonomy enrichment | `-2136193285` |
| 21 | property image scan | `1305561469` |

### Vì sao checksum V14 quan trọng

`MigrationLineageConfiguration.checkHistory()` yêu cầu:

```java
boolean legacy = history.stream().anyMatch(r ->
    "14".equals(r.get("version")) && Objects.equals(r.get("checksum"), -1382804267));
if (!legacy) throw new IllegalStateException("Expected Local BASELINE13/original crawler14 history.");
```

Checksum `-1382804267` là **crawler gốc**. Nếu khác, app từ chối khởi động với profile
`hybrid-local-existing-v13`. Đây là bảo vệ chống dùng nhầm database.

> **Đã kiểm chứng:** `MigrationLineageConfigurationTest.rejectsWrongCrawlerChecksum` xác
> nhận checksum khác bị từ chối.

---

## 5. Nhận file ZIP từ người quản trị

Baseline được bàn giao dưới dạng ZIP, **không đưa lên GitHub** (chứa schema đầy đủ, không
phù hợp để commit).

### 5.1. Yêu cầu từ người quản trị

Liên hệ người quản trị database để nhận:

```
SmartProp_PR38_Database_Handoff.zip
```

### 5.2. Nội dung ZIP

| File | Mô tả |
|---|---|
| `smartprop_v21_schema.sql` | Schema V21 + Flyway history, đã làm sạch |
| `README.md` | Hướng dẫn dựng staging và áp dụng migration |
| `VERIFY.md` | Kết quả kiểm chứng thực tế của người quản trị |

### 5.3. Xác minh tính toàn vẹn

**SHA256 của ZIP:**

```
0D55168E8B44347F3058187EB60AD1F3222EC1F4A5A74AB5BCAC293A4B9E80A1
```

**SHA256 của SQL bên trong:**

```
824332B219F301F3824B177F10E7892002F7E0C2B7BACCEBD9C1455528664442
```

Kiểm tra:

```powershell
Get-FileHash SmartProp_PR38_Database_Handoff.zip -Algorithm SHA256
# Kỳ vọng: 0D55168E8B44347F3058187EB60AD1F3222EC1F4A5A74AB5BCAC293A4B9E80A1

Expand-Archive SmartProp_PR38_Database_Handoff.zip -DestinationPath .\handoff
Get-FileHash .\handoff\smartprop_v21_schema.sql -Algorithm SHA256
# Kỳ vọng: 824332B219F301F3824B177F10E7892002F7E0C2B7BACCEBD9C1455528664442
```

**Nếu SHA256 khác:** không dùng file. Liên hệ người quản trị.

### 5.4. Kích thước tham chiếu

| File | Bytes |
|---|---:|
| ZIP | 20,041 |
| SQL | 105,759 |

---

## 6. Cài MySQL và dựng isolated staging

### 6.1. Yêu cầu

- MySQL **8.0+** (đã kiểm chứng trên 8.4.13)
- Datadir **riêng**, không dùng datadir của 3306
- Port **3307**

### 6.2. Khởi tạo datadir

Chỉ chạy lần đầu:

```powershell
$MYSQLD  = "F:\SmartProp\.scratch\devtools\mysql-8.4.13-winx64\bin\mysqld.exe"
$DATADIR = "F:\SmartProp\.scratch\mysql-isolated\data"

& $MYSQLD --initialize-insecure --datadir=$DATADIR
```

> **`--initialize-insecure` chỉ là bước tạm thời.** Nó tạo user `root` **không có mật
> khẩu**. Chỉ chấp nhận được vì instance này:
> - Bind `127.0.0.1` (không lộ ra mạng)
> - Port 3307 (không phải database nhóm)
> - Datadir riêng, xoá được
>
> **Phải đặt mật khẩu root ngay sau lần khởi động đầu tiên**, trước khi dùng cho bất cứ
> việc gì khác:
>
> ```powershell
> & $MYSQL --no-defaults -h 127.0.0.1 -P 3307 -u root -e @"
> ALTER USER 'root'@'localhost' IDENTIFIED BY '<mật-khẩu-riêng>';
> FLUSH PRIVILEGES;
> "@
> ```
>
> Sau đó mọi lệnh phải dùng `-p` hoặc `MYSQL_PWD`. **Không** dùng `--initialize-insecure`
> cho bất kỳ instance nào bind ra ngoài loopback hoặc dùng datadir của database nhóm.

### 6.3. Khởi động

```powershell
Start-Process -FilePath $MYSQLD `
  -ArgumentList @("--datadir=$DATADIR", "--port=3307",
                  "--bind-address=127.0.0.1", "--console") `
  -RedirectStandardOutput "F:\SmartProp\.scratch\mysql-3307.log" `
  -RedirectStandardError  "F:\SmartProp\.scratch\mysql-3307.err.log" `
  -WindowStyle Hidden

Start-Sleep -Seconds 25
```

### 6.4. Tạo database và user

```powershell
$MYSQL = "F:\SmartProp\.scratch\devtools\mysql-8.4.13-winx64\bin\mysql.exe"

& $MYSQL --no-defaults -h 127.0.0.1 -P 3307 -u root -e @"
CREATE DATABASE IF NOT EXISTS smartprop
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'smartprop'@'localhost' IDENTIFIED BY '<mật-khẩu-riêng>';
GRANT ALL PRIVILEGES ON smartprop.* TO 'smartprop'@'localhost';
FLUSH PRIVILEGES;
"@
```

> **Bắt buộc tạo user `smartprop`@`localhost` trước khi import.** Bốn VIEW trong dump có
> `DEFINER='smartprop'@'localhost'`. Thiếu user này, import báo `ERROR 1449` ở các VIEW
> (bảng vẫn tạo đủ nhưng thiếu view).

---

## 7. Restore, VIEW DEFINER và kiểm tra identity

### 7.1. Import

```powershell
& $MYSQL --no-defaults -h 127.0.0.1 -P 3307 -u root smartprop `
  --default-character-set=utf8mb4 `
  -e "source <đường-dẫn>\smartprop_v21_schema.sql"
```

### 7.2. Xử lý VIEW DEFINER

Nếu gặp:

```
ERROR 1449 (HY000): The user specified as a definer ('smartprop'@'localhost') does not exist
```

**Nguyên nhân:** 4 VIEW (`poi_effective_v1`, `rag_public_legal_status`,
`rag_public_properties`, `rag_public_property_images`) có `DEFINER` trỏ tới user
`smartprop`@`localhost`.

**Cách xử lý an toàn:**

```powershell
& $MYSQL --no-defaults -h 127.0.0.1 -P 3307 -u root -e @"
CREATE USER IF NOT EXISTS 'smartprop'@'localhost' IDENTIFIED BY '<mật-khẩu-riêng>';
GRANT ALL PRIVILEGES ON smartprop.* TO 'smartprop'@'localhost';
FLUSH PRIVILEGES;
"@
```

Rồi import lại. **Không** sửa `DEFINER` trong file SQL — đó là thay đổi schema.

### 7.3. Kiểm tra database identity

**Trước khi ghi bất cứ thứ gì**, xác minh đúng môi trường:

```powershell
& $MYSQL --no-defaults -h 127.0.0.1 -P 3307 -u root -e @"
SELECT @@port AS port, @@datadir AS datadir, DATABASE() AS schema;
"@
```

**Kỳ vọng:**

```
port    : 3307
datadir : ...\mysql-isolated\data\
schema  : (rỗng nếu chưa chọn DB)
```

**Fail closed:** nếu port không phải 3307, hoặc datadir không chứa `mysql-isolated`,
**dừng lại**. Không tiếp tục ghi.

### 7.4. Xác minh sau import

```powershell
& $MYSQL --no-defaults -h 127.0.0.1 -P 3307 -u root smartprop -e @"
SELECT COUNT(*) AS base_tables FROM information_schema.TABLES
  WHERE TABLE_SCHEMA='smartprop' AND TABLE_TYPE='BASE TABLE';
SELECT COUNT(*) AS views FROM information_schema.VIEWS
  WHERE TABLE_SCHEMA='smartprop';
SELECT version, checksum FROM flyway_schema_history ORDER BY installed_rank;
"@
```

**Kỳ vọng:**

| Kiểm tra | Giá trị |
|---|---:|
| `base_tables` | **52** |
| `views` | **4** |
| Flyway rows | **7** |

> **Đã kiểm chứng:** import thực tế trên MySQL 8.4.13 cho đúng 52/4/7.

---

## 8. Tạo fixture (baseline chỉ có schema)

Baseline **không có dữ liệu nghiệp vụ**. Để test tính năng, tự tạo fixture.

### 8.1. Nguyên tắc

- Fixture chỉ seed vào **3307 hoặc 3308**, không bao giờ 3306.
- Đánh dấu rõ là dữ liệu test (ví dụ prefix `fixture-` trong `source_code`).
- Không commit fixture chứa dữ liệu thật vào repo.
- Không dùng fixture để tuyên bố "đã có dữ liệu production".

### 8.2. Ví dụ tối thiểu

```sql
-- Chỉ chạy trên 3307/3308
INSERT INTO users (email, password_hash, full_name, role, status, created_at, updated_at)
VALUES ('fixture-admin@example.invalid', 'x', 'Fixture Admin', 'ADMIN', 'ACTIVE',
        UTC_TIMESTAMP(6), UTC_TIMESTAMP(6));
```

Dùng domain `.invalid` cho email fixture — không thể nhầm với email thật.

### 8.3. Fixture cho module News

Module News cần `news_sources` + `news_articles`. Xem
`backend/src/test/java/vn/smartprop/modules/news/NewsSourceRightsIT.java` (thuộc PR #41,
chưa merge) để biết cấu trúc fixture đã dùng trong test.

---

## 9. Flyway migrate và validate trên staging

### 9.1. Cấu hình môi trường

```powershell
cd F:\SmartProp\backend

$env:DB_URL      = 'jdbc:mysql://127.0.0.1:3307/smartprop?connectionTimeZone=UTC'
$env:DB_USER     = 'root'
$env:DB_PASSWORD = ''
```

### 9.2. Kiểm tra trạng thái

```powershell
.\mvnw.cmd -o -B -P hybrid-local-existing-v13 flyway:info
```

**Kỳ vọng sau khi import baseline V21:**

```
Schema version: 21
| 22 | property image analysis  | Pending |
| 23 | advisor chat checkpoints | Pending |
| 24 | public pre purchase evidence | Pending |
| 25 | flood planned risk catalog | Pending |
```

### 9.3. Áp dụng migration

```powershell
.\mvnw.cmd -o -B -P hybrid-local-existing-v13 flyway:migrate
```

**Kỳ vọng:** V22 → V23 → V24 → V25 áp dụng tuần tự.

### 9.4. Validate

```powershell
.\mvnw.cmd -o -B -P hybrid-local-existing-v13 flyway:validate
```

**Kỳ vọng:** `Successfully validated N migrations`.

> **Đã kiểm chứng:** trên baseline V21, `flyway:validate` báo
> `Detected resolved migration not applied to database: 22` — **đây là kết quả đúng**,
> vì DB ở V21 và còn migration pending. Không phải lỗi.

### 9.5. Quy tắc

- **Không** bật `outOfOrder=true`.
- **Không** chạy `flyway:repair` khi chưa hiểu nguyên nhân.
- **Không** sửa `flyway_schema_history` bằng SQL tay.
- **Không** tắt checksum validation.

---

## 10. Cấu hình Backend kết nối staging

### 10.1. Profile

| Profile | Port | Dùng khi |
|---|---:|---|
| `hybrid-local-existing-v13` | 3306 | Chạy app với database thật |
| `hybrid-local-existing-v13-staging` | 3307 | Test migration, integration test |
| `standard-migrations` | — | Database dựng mới từ V1 |

### 10.2. Chạy với staging

```powershell
$env:SPRING_PROFILES_ACTIVE = 'hybrid-local-existing-v13-staging'
$env:DB_USER     = 'root'
$env:DB_PASSWORD = ''
$env:JWT_SECRET  = '<chuỗi-ngẫu-nhiên-32-byte>'

cd F:\SmartProp\backend
.\mvnw.cmd -o -B spring-boot:run
```

### 10.3. Chạy integration test

```powershell
$env:DB_URL      = 'jdbc:mysql://127.0.0.1:3307/smartprop?connectionTimeZone=UTC'
$env:DB_USER     = 'root'
$env:DB_PASSWORD = ''
$env:SPRING_PROFILES_ACTIVE = 'hybrid-local-existing-v13-staging'
$env:JWT_SECRET  = '<chuỗi-ngẫu-nhiên-32-byte>'

.\mvnw.cmd -o -B test
```

Test có ghi dữ liệu **tự kiểm tra port** trước khi chạy:

```java
Integer port = jdbc.queryForObject("SELECT @@port", Integer.class);
assertThat(port).isEqualTo(3307);
```

Đây là guard fail-closed — test từ chối chạy nếu không phải 3307.

---

## 11. Quản lý migration mới và phối hợp giữa các PR

### 11.1. Chọn version

1. Kiểm tra version cao nhất hiện có:
   ```powershell
   Get-ChildItem database\legacy-hybrid-local -Filter 'V*.sql' |
     Sort-Object Name | Select-Object -Last 3
   ```
2. Kiểm tra các PR đang mở có migration chưa merge.
3. Chọn version **tiếp theo chưa tồn tại**.

### 11.2. Tránh xung đột giữa các PR

**Vấn đề:** hai PR cùng chọn V26 → merge xong sẽ trùng version.

**Quy tắc:**

- Trước khi tạo migration, kiểm tra `git ls-tree origin/main database/legacy-hybrid-local/`.
- Nếu PR khác đã chiếm version, chọn version cao hơn.
- Ghi rõ trong PR body: "migration Vxx, không trùng PR #yy".

### 11.3. Migration phụ thuộc nhau

Nếu migration của bạn phụ thuộc migration của PR khác:

- **Không** nới lỏng guard để PR của bạn chạy độc lập.
- Ghi rõ dependency trong PR body.
- Kiểm thử trên integration worktree có đủ cả hai migration.
- Merge theo đúng thứ tự.

**Ví dụ thực tế:** PR #41 (News, V27) phụ thuộc PR #38 (Coordinate Provenance, V26).
Guard được sửa để **từ chối** V27 khi thiếu V26 — không phải chấp nhận.

### 11.4. Không sửa migration đã triển khai

Nếu migration đã áp dụng ở môi trường cần bảo toàn:

- **Không** sửa file (checksum sẽ đổi, Flyway từ chối).
- Tạo migration mới để sửa.

Nếu migration **chưa merge** và chỉ tồn tại ở DB test có thể tái tạo, có thể sửa trực
tiếp — nhưng phải dựng lại DB test từ baseline.

---

## 12. Lỗi thường gặp và cách xử lý an toàn

| Lỗi | Nguyên nhân | Cách xử lý |
|---|---|---|
| `ERROR 1449 ... definer does not exist` | Thiếu user `smartprop`@`localhost` cho VIEW | Tạo user rồi import lại. Không sửa DEFINER trong SQL |
| `Detected resolved migration not applied: N` | DB cũ hơn file migration | Chạy `flyway:migrate`. Đây là trạng thái bình thường |
| `Detected applied migration not resolved locally: N` | DB có migration mà file không có | Kiểm tra đúng branch/worktree. Không xoá history |
| `Migration checksum mismatch for version N` | File migration bị sửa sau khi áp dụng | Khôi phục file gốc. Không chạy `repair` mù |
| `Expected Local BASELINE13/original crawler14 history` | Sai database hoặc history bị sửa | Kiểm tra `@@port`, `@@datadir`. Dùng đúng DB |
| `Wrong Local database identity` | Port/schema không khớp profile | Kiểm tra `DB_URL`. Không sửa guard |
| `Staging must use the isolated datadir` | Datadir không phải `mysql-isolated` | Dựng lại datadir đúng, hoặc dùng profile local |
| `V27 requires V26` | Migration phụ thuộc chưa áp dụng | Áp V26 trước. Không nới guard |
| `Access denied for user` | Sai credential | Kiểm tra `DB_USER`/`DB_PASSWORD`. Không hardcode |
| `Table already exists` khi import | Import hai lần | Drop database rồi import lại từ baseline |

### Nguyên tắc chung khi gặp lỗi

1. **Đọc thông báo đầy đủ** — Flyway nói rõ version và lý do.
2. **Không chạy `repair`** trước khi hiểu nguyên nhân.
3. **Không sửa `flyway_schema_history`** bằng SQL tay.
4. **Không xoá database** để "làm sạch" khi chưa backup.
5. Nếu không chắc, **dừng và hỏi người quản trị**.

---

## 13. Quyền hạn

### 13.1. Thành viên

| Được phép | Không được phép |
|---|---|
| Dựng MySQL cô lập trên 3307/3308 | Ghi vào 3306 |
| Import baseline vào 3307/3308 | Chạy migration trên 3306 |
| Chạy `flyway:migrate` trên 3307 | Sửa `flyway_schema_history` |
| Tạo fixture trên 3307/3308 | Commit dữ liệu thật vào repo |
| Tạo migration mới trong PR riêng | Sửa migration đã merge |
| Chạy test trên 3307 | Chạy test cleanup trên 3306 |
| Đọc schema 3306 | `DROP`/`TRUNCATE` bất kỳ DB nào |

### 13.2. Người quản trị database

| Trách nhiệm | Ghi chú |
|---|---|
| Chuẩn bị baseline schema | Đã làm sạch dữ liệu nhạy cảm |
| Cung cấp ZIP handoff | Kèm SHA256 để xác minh |
| Duyệt migration trước khi áp lên 3306 | Xem checklist mục 14 |
| Backup trước khi migrate 3306 | Bắt buộc |
| Xử lý sự cố database | Người duy nhất có quyền ghi 3306 |

### 13.3. Không ai được

- Commit `.env`, credential, hoặc dump database.
- Đưa file SQL backup lên GitHub.
- Chia sẻ mật khẩu qua repo hoặc issue.
- Tự merge PR có migration chưa được duyệt.

---

## 14. Checklist trước khi merge PR và triển khai migration

### 14.1. Trước khi tạo PR có migration

- [ ] Version chưa tồn tại trên `origin/main`
- [ ] Version không trùng PR đang mở khác
- [ ] Migration chạy được trên 3307 từ baseline
- [ ] `flyway:validate` PASS sau migrate
- [ ] Không sửa migration đã merge
- [ ] Ghi rõ dependency (nếu có) trong PR body

### 14.2. Trước khi merge PR

- [ ] Backend test PASS trên 3307
- [ ] Migration áp dụng được từ baseline V21
- [ ] Không có migration trùng version với PR khác
- [ ] Guard migration lineage không bị nới lỏng
- [ ] Không có credential trong diff
- [ ] Không có dump database trong diff

### 14.3. Trước khi triển khai lên 3306

- [ ] **Backup 3306** (bắt buộc)
- [ ] Migration đã test trên 3307 từ baseline
- [ ] `flyway:info` trên 3306 xác nhận version hiện tại
- [ ] Không có migration pending bất thường
- [ ] Có người quản trị database giám sát
- [ ] Có kế hoạch rollback

### 14.4. Sau khi triển khai

- [ ] `flyway:validate` PASS
- [ ] `flyway:info` hiển thị version mới
- [ ] App khởi động được
- [ ] Smoke test chức năng liên quan
- [ ] Ghi lại version và thời điểm triển khai

---

## 15. SHA256 tham chiếu

| File | SHA256 |
|---|---|
| `SmartProp_PR38_Database_Handoff.zip` | `0D55168E8B44347F3058187EB60AD1F3222EC1F4A5A74AB5BCAC293A4B9E80A1` |
| `smartprop_v21_schema.sql` | `824332B219F301F3824B177F10E7892002F7E0C2B7BACCEBD9C1455528664442` |

**Kích thước:**

| File | Bytes |
|---|---:|
| ZIP | 20,041 |
| SQL | 105,759 |

> **Lưu ý:** SHA256 chỉ dùng để xác minh file bạn nhận đúng là file người quản trị tạo.
> Nếu người quản trị cập nhật baseline, SHA256 sẽ khác — hỏi lại để lấy giá trị mới.

---

## 16. Ngày cập nhật và trạng thái kiểm chứng

**Cập nhật lần cuối:** 2026-11-24

### Đã kiểm chứng thực tế

| Hạng mục | Bằng chứng |
|---|---|
| Baseline V21 import được | 52 bảng, 4 view, 7 Flyway rows trên MySQL 8.4.13 |
| Flyway history nguyên vẹn | Checksum V14 = `-1382804267` khớp guard |
| Không dữ liệu nhạy cảm | Chỉ 1 dòng INSERT (`flyway_schema_history`) |
| VIEW DEFINER cần user `smartprop` | Gặp `ERROR 1449` khi thiếu, hết lỗi sau khi tạo user |
| `flyway:validate` trên V21 | Báo pending V22 — đúng trạng thái |
| Guard từ chối URL khác | `MigrationLineageConfigurationTest` 21 test |
| Guard từ chối gap/duplicate/order | `MigrationLineageStrictTest` 18 test — **thuộc PR #41, chưa merge** |
| Test ghi dữ liệu tự kiểm tra port | `assertThat(port).isEqualTo(3307)` trong IT |

### Chưa kiểm chứng trong tài liệu này

| Hạng mục | Ghi chú |
|---|---|
| Dựng MySQL từ đầu theo mục 6 | Hướng dẫn dựa trên môi trường đã có sẵn |
| Áp dụng V26 (PR #38) | Thuộc PR #38, chưa merge |
| Áp dụng V27 (PR #41) | Thuộc PR #41, chưa merge |
| Triển khai lên 3306 | Không thực hiện — database nhóm chỉ đọc |
| Fixture cho mọi module | Chỉ ví dụ tối thiểu |

---

## Liên kết

- [TEAM_SETUP.md](../TEAM_SETUP.md) — thiết lập chung, biến môi trường, chạy app
- [database/README.md](../../database/README.md) — cấu trúc thư mục migration
- [ops/OPERATIONS.md](../../ops/OPERATIONS.md) — backup/restore, vận hành
- [database/docs/database-design.md](../../database/docs/database-design.md) — thiết kế schema
