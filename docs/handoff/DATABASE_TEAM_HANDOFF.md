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

Dùng cho database dựng mới từ đầu. Chạy V1 → V23 tuần tự.

```
database/migrations/
  V1__accounts_and_sessions.sql
  V2__extend_accounts_and_roles.sql
  ...
  V13__broker_applications.sql
  V14__valuation_history.sql
  V15__profile_avatar_and_google_identity.sql
  V16__immutable_property_listing_codes.sql
  V17__cloudinary_property_images.sql
  V18__external_listing_support.sql
  V19__account_advisor_preferences.sql
  V21__property_image_scan.sql
  V22__property_image_analysis.sql
  V23__advisor_chat_checkpoints.sql

database/research-migrations/poi/
  V20__poi_taxonomy_enrichment.sql
```

Profile: `standard-migrations`

**Cấu hình thực tế trong `backend/pom.xml`:**

```xml
<id>standard-migrations</id>
<locations>
  <location>filesystem:${project.basedir}/../database/migrations</location>
  <location>filesystem:${project.basedir}/../database/research-migrations/poi</location>
</locations>
<target>23</target>
```

**Target = V23**, không phải V13. Đây là điểm dễ nhầm: V13 chỉ là baseline của
legacy lineage, còn standard lineage chạy tới V23.

**V20 nằm ở `research-migrations/poi/`**, không nằm trong `migrations/`. Profile
`standard-migrations` khai báo cả hai location nên V20 được nhận đúng thứ tự giữa
V19 và V21.

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

**Cấu hình thực tế trong `backend/pom.xml`:**

```xml
<id>hybrid-local-existing-v13</id>
<locations>
  <location>filesystem:${project.basedir}/../database/legacy-hybrid-local</location>
  <location>filesystem:${project.basedir}/../database/research-migrations</location>
</locations>
<target>25</target>
```

**Target = V25.** Trạng thái trên `main` (2026-11-24): V14, V17, V18, V21, V22, V23,
V24, V25 — cộng V19/V20 từ `research-migrations/`.

**Chưa có trên `main`:**

| Version | Thuộc | Trạng thái |
|---|---|---|
| V26 `property_coordinate_provenance` | PR #38 | Chưa merge |
| V27 `news_backend_v1` | PR #41 | Chưa merge |

Nếu bạn thấy V26/V27 trong worktree của mình, đó là do bạn đang ở branch của PR tương
ứng — không phải `main`. Đừng giả định `main` có chúng.

### 2.5. Quan hệ V26 → V27

V26 và V27 là **hai migration của hai PR độc lập**, nhưng bản tích hợp yêu cầu thứ tự:

```
V25 → V26 (PR #38) → V27 (PR #41)
```

**Chính sách:**

- Flyway chạy `outOfOrder=false`, nên V27 không thể áp dụng trước V26 trên đường triển
  khai thật.
- `MigrationLineageConfiguration` (PR #41) **từ chối** database có V27 mà thiếu V26 —
  dấu hiệu history bị sửa tay hoặc migration bị bỏ qua.
- V26 đơn lẻ (PR #38 chưa merge) vẫn hợp lệ.
- PR #41 **không** nới guard để chạy độc lập; nó ghi rõ dependency vào PR #38.

Đây là lý do thứ tự merge phải là **#38 trước, #41 sau**.

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
- Datadir **riêng**, tuyệt đối không dùng datadir của 3306
- Port **3307**
- Bind **127.0.0.1** (không lộ ra mạng)

### 6.2. Khai báo biến đường dẫn

Không hardcode ổ đĩa. Chọn thư mục trên máy bạn:

```powershell
# Đổi $MYSQL_HOME theo máy bạn — không bắt buộc ổ F
$MYSQL_HOME = "C:\tools\mysql-8.4.13-winx64"
$STAGING    = "C:\smartprop-staging"

$MYSQLD  = Join-Path $MYSQL_HOME "bin\mysqld.exe"
$MYSQL   = Join-Path $MYSQL_HOME "bin\mysql.exe"
$LOGDIR  = Join-Path $STAGING "logs"

# QUAN TRỌNG: datadir PHẢI kết thúc bằng /mysql-isolated/data/
# Backend guard kiểm tra @@datadir.endsWith("/mysql-isolated/data/") — đường dẫn
# khác sẽ bị từ chối khi chạy profile staging.
$DATADIR = Join-Path $STAGING "mysql-isolated\data"

New-Item -ItemType Directory -Path $STAGING, $LOGDIR -Force | Out-Null
```

> **Vì sao `mysql-isolated\data`?** `MigrationProfileEnvironmentGuard` khai báo
> `STAGING_DATADIR_SUFFIX = "/mysql-isolated/data/"` và kiểm tra
> `@@datadir.replace('\\','/').endsWith(...)`. Nếu datadir là `C:\smartprop-staging\data`,
> guard từ chối với `Staging must use the isolated datadir`. Đặt đúng thư mục con ngay
> từ đầu.

### 6.3. Kiểm tra trước khi khởi tạo

**Bắt buộc chạy trước mọi thao tác ghi.**

```powershell
# 1. Port 3307 phải trống
$busy = Get-NetTCPConnection -LocalPort 3307 -State Listen -ErrorAction SilentlyContinue
if ($busy) { throw "Port 3307 đang bị chiếm bởi PID $($busy.OwningProcess). Dừng lại." }

# 2. Datadir phải trống hoặc chưa tồn tại
if (Test-Path $DATADIR) {
    $existing = Get-ChildItem $DATADIR -ErrorAction SilentlyContinue
    if ($existing) { throw "Datadir $DATADIR đã có dữ liệu. Không ghi đè." }
}

# 3. Datadir phải khớp suffix mà Backend guard yêu cầu
$normalized = $DATADIR.Replace('\', '/').TrimEnd('/') + '/'
if (-not $normalized.EndsWith("/mysql-isolated/data/")) {
    throw "Datadir phải kết thúc bằng /mysql-isolated/data/ (guard yêu cầu). Hiện tại: $DATADIR"
}

# 4. Đường dẫn phải tuyệt đối
if (-not [IO.Path]::IsPathRooted($DATADIR)) { throw "Datadir phải là đường dẫn tuyệt đối." }

# 5. Nếu instance 3306 đang chạy, đọc datadir THẬT của nó để chắc chắn khác biệt
$localBusy = Get-NetTCPConnection -LocalPort 3306 -State Listen -ErrorAction SilentlyContinue
if ($localBusy) {
    Write-Output "Instance 3306 đang chạy (PID $($localBusy.OwningProcess))."
    Write-Output "Kiểm tra thủ công: datadir staging ($DATADIR) phải KHÁC datadir 3306."
    Write-Output "Chạy lệnh sau trên 3306 để xem datadir thật:"
    Write-Output "  mysql --no-defaults -h 127.0.0.1 -P 3306 -u <user> -p -e `"SELECT @@datadir;`""
} else {
    Write-Output "Instance 3306 không chạy — không có nguy cơ trùng datadir."
}

Write-Output "OK: port 3307 trống, datadir $DATADIR khớp guard"
```

> **Không dùng đường dẫn 3306 giả làm điều kiện bảo vệ.** Kiểm tra `$DATADIR -eq $localDatadir`
> với một biến hardcode chỉ tạo cảm giác an toàn — nó không đọc datadir thật của 3306.
> Cách đúng: đọc `@@datadir` từ instance 3306 đang chạy (nếu có) và so sánh thủ công,
> hoặc đảm bảo đường dẫn staging nằm ngoài mọi thư mục MySQL khác.

### 6.4. Khởi tạo datadir

```powershell
& $MYSQLD --no-defaults --initialize-insecure --datadir=$DATADIR
if ($LASTEXITCODE -ne 0) { throw "Initialize thất bại (exit $LASTEXITCODE). Đọc log trong $DATADIR" }

# Xác nhận datadir đã được tạo đúng
if (-not (Test-Path (Join-Path $DATADIR "mysql"))) {
    throw "Initialize báo OK nhưng không thấy thư mục mysql/. Kiểm tra lại $DATADIR"
}
Write-Output "Initialize OK: $DATADIR"
```

> **`--initialize-insecure` chỉ là bước tạm thời.** Nó tạo user `root` **không có mật
> khẩu**. Chỉ chấp nhận được vì instance này bind loopback, port 3307, datadir riêng.
>
> **Phải đặt mật khẩu root ngay sau khi xác minh instance mới** (mục 6.6), trước khi
> dùng cho bất cứ việc gì khác.
>
> **Không** dùng `--initialize-insecure` cho instance bind ra ngoài loopback hoặc dùng
> datadir của database nhóm.

### 6.5. Khởi động và chờ readiness

Không dùng `Start-Sleep` cố định — chờ thực sự:

```powershell
$proc = Start-Process -FilePath $MYSQLD `
  -ArgumentList @("--no-defaults", "--datadir=$DATADIR", "--port=3307",
                  "--bind-address=127.0.0.1", "--console") `
  -RedirectStandardOutput (Join-Path $LOGDIR "mysqld.out.log") `
  -RedirectStandardError  (Join-Path $LOGDIR "mysqld.err.log") `
  -WindowStyle Hidden -PassThru

# Chờ tối đa 60s cho tới khi port mở
$listener = $null
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 1
    $listener = Get-NetTCPConnection -LocalPort 3307 -State Listen -ErrorAction SilentlyContinue |
                Select-Object -First 1
    if ($listener) { break }
    if ($proc.HasExited) { break }
}

if (-not $listener) {
    Write-Output "--- mysqld.err.log ---"
    Get-Content (Join-Path $LOGDIR "mysqld.err.log") -Tail 30 -ErrorAction SilentlyContinue
    throw "MySQL không khởi động được trên 3307. Đọc log trên."
}

# Xác nhận listener là CHÍNH process vừa khởi động, không phải instance khác
if ($listener.OwningProcess -ne $proc.Id) {
    throw "Port 3307 do PID $($listener.OwningProcess) giữ, không phải PID $($proc.Id) vừa khởi động. Dừng lại."
}

Write-Output "MySQL 3307 đã sẵn sàng (PID $($proc.Id), khớp listener)"
```

> **Kiểm tra PID là bắt buộc.** Nếu port 3307 đã có instance khác từ trước, vòng chờ sẽ
> thấy port mở ngay và bạn tưởng MySQL của mình đã lên — nhưng thực tế đang nói chuyện
> với instance của người khác. So sánh `OwningProcess` với `$proc.Id` ngăn điều đó.

### 6.6. Xác minh identity và đặt mật khẩu root

**Đây là bước kiểm tra identity đầu tiên — trước mọi thao tác ghi.**

```powershell
# Xác minh instance mới đúng là cái mình vừa tạo
& $MYSQL --no-defaults -h 127.0.0.1 -P 3307 -u root -e @"
SELECT @@port AS port, @@datadir AS datadir, @@server_uuid AS uuid, @@hostname AS host;
"@
if ($LASTEXITCODE -ne 0) { throw "Không kết nối được MySQL 3307 (exit $LASTEXITCODE)" }
```

**Kiểm tra thủ công từng dòng:**

| Trường | Kỳ vọng |
|---|---|
| `port` | `3307` |
| `datadir` | đúng `$DATADIR` bạn vừa tạo, kết thúc `/mysql-isolated/data/` |
| `uuid` | **mới**, khác UUID của 3306 |
| `host` | máy bạn |

**Nếu bất kỳ trường nào sai → dừng, không đặt mật khẩu, không tạo schema.**

Chỉ khi identity đúng:

```powershell
# Đặt mật khẩu root — nhập trực tiếp, không lưu vào file
$ROOT_PW = Read-Host "Mật khẩu root cho staging 3307" -AsSecureString
$ROOT_PW_PLAIN = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($ROOT_PW))

# Mật khẩu đi qua biến môi trường, KHÔNG qua đối số command line
# (đối số hiện trong process list và có thể bị ghi vào log)
$env:MYSQL_PWD = $ROOT_PW_PLAIN

& $MYSQL --no-defaults -h 127.0.0.1 -P 3307 -u root -e @"
ALTER USER 'root'@'localhost' IDENTIFIED BY '$ROOT_PW_PLAIN';
FLUSH PRIVILEGES;
"@
if ($LASTEXITCODE -ne 0) { Remove-Item Env:MYSQL_PWD; throw "Đặt mật khẩu root thất bại (exit $LASTEXITCODE)" }

# Xác minh mật khẩu đã có hiệu lực
& $MYSQL --no-defaults -h 127.0.0.1 -P 3307 -u root -e "SELECT 'root auth OK' AS status;"
if ($LASTEXITCODE -ne 0) { Remove-Item Env:MYSQL_PWD; throw "Xác thực root thất bại (exit $LASTEXITCODE)" }

Remove-Item Env:MYSQL_PWD
Write-Output "Root password đã đặt và xác minh OK"
```

> **Mật khẩu không bao giờ đi qua đối số command line.** `mysql -p<password>` và
> `--password=<password>` đều hiện trong process list. Dùng `$env:MYSQL_PWD` (biến môi
> trường của process con) rồi xoá ngay.
>
> **Từ đây, mọi lệnh `mysql.exe` phải có xác thực.** Không còn `-u root` trần.
> Không ghi mật khẩu vào script, file `.env` commit, hay log.

### 6.7. Tạo schema và tài khoản staging

Hai tài khoản riêng biệt, quyền khác nhau:

```powershell
$env:MYSQL_PWD = $ROOT_PW_PLAIN

# Mật khẩu riêng cho từng tài khoản — không dùng chung với root
$APP_PW     = Read-Host "Mật khẩu cho smartprop_app (backend)" -AsSecureString
$APP_PW_PLAIN = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($APP_PW))

$FLYWAY_PW  = Read-Host "Mật khẩu cho smartprop_flyway (migration)" -AsSecureString
$FLYWAY_PW_PLAIN = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($FLYWAY_PW))

& $MYSQL --no-defaults -h 127.0.0.1 -P 3307 -u root -e @"
CREATE DATABASE IF NOT EXISTS smartprop
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Tài khoản migration: cần DDL để tạo bảng, nhưng không cần SUPER
CREATE USER IF NOT EXISTS 'smartprop_flyway'@'localhost' IDENTIFIED BY '$FLYWAY_PW_PLAIN';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES,
      DROP, CREATE VIEW, SHOW VIEW
  ON smartprop.* TO 'smartprop_flyway'@'localhost';

-- Tài khoản backend: chỉ DML, không DDL
CREATE USER IF NOT EXISTS 'smartprop_app'@'localhost' IDENTIFIED BY '$APP_PW_PLAIN';
GRANT SELECT, INSERT, UPDATE, DELETE ON smartprop.* TO 'smartprop_app'@'localhost';

-- VIEW trong dump có DEFINER='smartprop'@'localhost' — tạo user này để import không lỗi
CREATE USER IF NOT EXISTS 'smartprop'@'localhost' IDENTIFIED BY '$APP_PW_PLAIN';
GRANT SELECT, INSERT, UPDATE, DELETE ON smartprop.* TO 'smartprop'@'localhost';

FLUSH PRIVILEGES;
"@
$createExit = $LASTEXITCODE

Remove-Item Env:MYSQL_PWD

if ($createExit -ne 0) { throw "Tạo schema/user thất bại (exit $createExit)" }

# Xoá biến plaintext khỏi session — chỉ giữ $ROOT_PW_PLAIN cho các bước sau
Remove-Variable APP_PW, FLYWAY_PW -ErrorAction SilentlyContinue
Write-Output "Schema + 3 tài khoản đã tạo"
```

**Phân biệt quyền:**

| Tài khoản | Dùng cho | Quyền |
|---|---|---|
| `root` | Quản trị instance, tạo schema/user, restore | Toàn quyền — chỉ dùng khi cần |
| `smartprop_flyway` | `flyway:migrate`, `flyway:validate` | DDL + DML trên `smartprop.*` |
| `smartprop_app` | Backend runtime, integration test | Chỉ DML |
| `smartprop` | VIEW DEFINER trong dump | DML (để import không lỗi 1449) |

### 6.8. Kiểm tra identity lần hai trước khi restore

Trước khi import baseline, xác minh lại:

```powershell
$env:MYSQL_PWD = $ROOT_PW_PLAIN
& $MYSQL --no-defaults -h 127.0.0.1 -P 3307 -u root -e @"
SELECT @@port AS port, @@datadir AS datadir, @@server_uuid AS uuid;
SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='smartprop';
"@
Remove-Item Env:MYSQL_PWD
```

**Kỳ vọng:** `port=3307`, `datadir` đúng, `uuid` khớp lần kiểm tra trước, schema
`smartprop` tồn tại.

**Nếu `datadir` hoặc `uuid` khác lần trước → dừng.** Có thể bạn đang trỏ nhầm instance.

### 6.9. Vì sao guard trong code không bảo vệ được mọi lệnh

`MigrationProfileEnvironmentGuard` là một `EnvironmentPostProcessor` — nó chỉ chạy khi
**Spring Boot khởi động**. Nó **không** chạy khi bạn gọi `mysql.exe`, `mysqldump`, hay
**Maven Flyway CLI**.

| Lệnh | Guard có chạy? | Lý do |
|---|---|---|
| `mysql.exe ... -e "DROP DATABASE ..."` | **KHÔNG** | Không qua Spring |
| `mysql.exe ... < dump.sql` | **KHÔNG** | Không qua Spring |
| `mysqldump` | **KHÔNG** | Không qua Spring |
| `mvnw flyway:migrate` (không `-P`) | **KHÔNG** | Flyway Maven plugin không khởi động Spring |
| `mvnw flyway:migrate -P hybrid-local-existing-v13` | **KHÔNG** | Profile Maven chỉ set `locations`/`target`; không kiểm tra URL |
| `mvnw flyway:validate -P ...` | **KHÔNG** | Như trên |
| Spring Boot với profile staging | **CÓ** | `EnvironmentPostProcessor` chạy, kiểm tra URL + datadir |

**Điểm dễ hiểu nhầm:** profile Maven `hybrid-local-existing-v13` và profile Spring
`hybrid-local-existing-v13-staging` là **hai thứ khác nhau**. Profile Maven chỉ cấu hình
`locations` và `target` cho Flyway plugin — nó không kiểm tra `DB_URL` trỏ đi đâu.

**Kết luận:** kiểm tra `@@port` và `@@datadir` bằng tay là **bắt buộc** trước mọi thao
tác ghi. Không được dựa vào guard của ứng dụng để bảo vệ lệnh CLI.

## 7. Restore, VIEW DEFINER và kiểm tra identity

### 7.1. Kiểm tra identity TRƯỚC khi restore

**Bắt buộc. Không bỏ qua.**

```powershell
$env:MYSQL_PWD = $ROOT_PW_PLAIN

& $MYSQL --no-defaults -h 127.0.0.1 -P 3307 -u root -e @"
SELECT @@port AS port, @@datadir AS datadir, @@server_uuid AS uuid;
SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='smartprop';
"@
```

**Kiểm tra từng dòng:**

| Trường | Kỳ vọng | Nếu sai |
|---|---|---|
| `port` | `3307` | Dừng — đang trỏ nhầm instance |
| `datadir` | đúng `$DATADIR` ở mục 6.2 | Dừng — có thể là datadir 3306 |
| `uuid` | khớp lần kiểm tra mục 6.6 | Dừng — instance đã đổi |
| schema `smartprop` | tồn tại | Tạo lại theo mục 6.7 |

**Chỉ tiếp tục khi cả bốn dòng đúng.** Đây là bước duy nhất ngăn bạn ghi vào database
nhóm — guard trong code không chạy cho `mysql.exe` (xem mục 6.9).

### 7.2. Import baseline

```powershell
$env:MYSQL_PWD = $ROOT_PW_PLAIN

$SQL_FILE = Join-Path $STAGING "smartprop_v21_schema.sql"

# Xác minh file trước khi import
$expected = "824332B219F301F3824B177F10E7892002F7E0C2B7BACCEBD9C1455528664442"
$actual = (Get-FileHash $SQL_FILE -Algorithm SHA256).Hash
if ($actual -ne $expected) { Remove-Item Env:MYSQL_PWD; throw "SHA256 không khớp. Không import." }

& $MYSQL --no-defaults -h 127.0.0.1 -P 3307 -u root smartprop `
  --default-character-set=utf8mb4 `
  -e "source $SQL_FILE"
$importExit = $LASTEXITCODE

Remove-Item Env:MYSQL_PWD

if ($importExit -ne 0) {
    throw "Import thất bại (exit $importExit). Kiểm tra trạng thái trước khi dựng lại."
}
Write-Output "Import OK"
```

**Nếu import thất bại giữa chừng:** dừng, kiểm tra trạng thái (bảng nào đã tạo, view
nào lỗi) trước khi quyết định dựng lại. Không drop ngay.

### 7.3. Xử lý VIEW DEFINER

Nếu gặp:

```
ERROR 1449 (HY000): The user specified as a definer ('smartprop'@'localhost') does not exist
```

**Nguyên nhân:** 4 VIEW (`poi_effective_v1`, `rag_public_legal_status`,
`rag_public_properties`, `rag_public_property_images`) có `DEFINER` trỏ tới user
`smartprop`@`localhost`.

**Cách xử lý:** user `smartprop`@`localhost` đã được tạo ở mục 6.7. Nếu chưa, tạo lại
**với mật khẩu riêng** (không dùng chung root):

```powershell
$env:MYSQL_PWD = $ROOT_PW_PLAIN

& $MYSQL --no-defaults -h 127.0.0.1 -P 3307 -u root -e @"
CREATE USER IF NOT EXISTS 'smartprop'@'localhost' IDENTIFIED BY '$APP_PW_PLAIN';
GRANT SELECT, INSERT, UPDATE, DELETE ON smartprop.* TO 'smartprop'@'localhost';
FLUSH PRIVILEGES;
"@

Remove-Item Env:MYSQL_PWD
```

Rồi import lại. **Không** sửa `DEFINER` trong file SQL — đó là thay đổi schema.

### 7.4. Xác minh sau import

```powershell
$env:MYSQL_PWD = $ROOT_PW_PLAIN

& $MYSQL --no-defaults -h 127.0.0.1 -P 3307 -u root smartprop -e @"
SELECT COUNT(*) AS base_tables FROM information_schema.TABLES
  WHERE TABLE_SCHEMA='smartprop' AND TABLE_TYPE='BASE TABLE';
SELECT COUNT(*) AS views FROM information_schema.VIEWS
  WHERE TABLE_SCHEMA='smartprop';
SELECT version, checksum FROM flyway_schema_history ORDER BY installed_rank;
"@

Remove-Item Env:MYSQL_PWD
```

**Kỳ vọng:**

| Kiểm tra | Giá trị |
|---|---:|
| `base_tables` | **52** |
| `views` | **4** |
| Flyway rows | **7** |

> **Đã kiểm chứng:** import thực tế trên MySQL 8.4.13 cho đúng 52/4/7.

### 7.5. Thao tác phá huỷ — chỉ trên instance disposable

Mọi lệnh `DROP DATABASE`, `TRUNCATE`, reset hay restore lại **chỉ** áp dụng khi:

- Instance đã xác minh là **disposable** (mục 7.1 pass)
- **Người sở hữu môi trường cho phép** — nếu là máy dùng chung, hỏi trước
- Không có PR khác đang dùng database đó

```powershell
# CHỈ chạy khi đã thoả cả ba điều kiện trên
# & $MYSQL --no-defaults -h 127.0.0.1 -P 3307 -u root -e "DROP DATABASE smartprop;"
```

**Không bao giờ:**

- Drop database trên 3306
- Sửa `flyway_schema_history` bằng SQL tay
- Chạy `flyway:repair` để "sửa" lỗi chưa hiểu nguyên nhân
- Dựng lại database khi PR khác đang dùng

## 8. Tạo fixture (baseline chỉ có schema)

Baseline **không có dữ liệu nghiệp vụ**. Để test tính năng, tự tạo fixture.

### 8.1. Nguyên tắc

- Fixture chỉ seed vào **3307 hoặc 3308**, không bao giờ 3306.
- Đánh dấu rõ là dữ liệu test (prefix `fixture-` trong `source_code`, domain `.invalid`).
- Không commit fixture chứa dữ liệu thật vào repo.
- Không dùng fixture để tuyên bố "đã có dữ liệu production".
- **Kiểm tra identity trước khi seed** (mục 7.1) — seed là thao tác ghi.

### 8.2. Kiểm tra schema trước khi seed

Fixture phải khớp schema thật. Kiểm tra cột và constraint trước:

```powershell
$env:MYSQL_PWD = $ROOT_PW_PLAIN

& $MYSQL --no-defaults -h 127.0.0.1 -P 3307 -u root smartprop -e @"
SHOW COLUMNS FROM users;
SHOW COLUMNS FROM news_sources;
"@

Remove-Item Env:MYSQL_PWD
```

Đối chiếu với `database/docs/schema-reference.sql` trước khi viết INSERT. Cột `NOT NULL`
không có default sẽ làm INSERT thất bại.

### 8.3. Fixture cho test KHÔNG cần đăng nhập

Nếu test chỉ đọc dữ liệu và không login, `password_hash` có thể là giá trị giả:

```sql
-- CHỈ dùng khi test không đăng nhập bằng tài khoản này
INSERT INTO users (email, password_hash, full_name, role, status, created_at, updated_at)
VALUES ('fixture-admin@example.invalid', 'x', 'Fixture Admin', 'ADMIN', 'ACTIVE',
        UTC_TIMESTAMP(6), UTC_TIMESTAMP(6));
```

> **`password_hash='x'` không phải bcrypt hợp lệ.** Đăng nhập bằng tài khoản này sẽ
> **luôn thất bại**. Chỉ dùng cho test đọc dữ liệu, không dùng cho test auth.

### 8.4. Fixture cho test CẦN đăng nhập

Nếu integration test cần login thật, phải tạo bcrypt hash hợp lệ. Dùng test helper của
backend thay vì hardcode hash:

```java
// Trong test source — dùng PasswordEncoder của ứng dụng
String hash = passwordEncoder.encode("fixture-password");
jdbc.update("INSERT INTO users (email, password_hash, ...) VALUES (?, ?, ...)",
    "fixture-admin@example.invalid", hash);
```

Hoặc tạo hash bằng công cụ có sẵn của dự án, rồi dùng giá trị đó trong fixture SQL.
**Không** copy hash từ database thật.

### 8.5. Fixture cho module News

Module News cần `news_sources` + `news_articles`. Xem
`backend/src/test/java/vn/smartprop/modules/news/NewsSourceRightsIT.java` (thuộc PR #41,
chưa merge) để biết cấu trúc fixture đã dùng trong test.

Các trạng thái cần có để test đầy đủ:

| Trạng thái nguồn | Mục đích test |
|---|---|
| `APPROVED` + `enabled=1` + `allow_summary=1` | Bài hiện công khai, có summary |
| `APPROVED` + `enabled=1` + `allow_summary=0` | Summary phải bị ẩn |
| `APPROVED` + `enabled=0` | Bài không được hiện |
| `PENDING_REVIEW` | Bài không được hiện |

### 8.6. Fixture cho test backfill

Nếu test kiểm tra backfill migration, **tạo fixture trước bước backfill** theo đúng
scenario:

1. Migrate tới version **trước** migration backfill
2. Seed dữ liệu ở trạng thái cũ
3. Chạy migration backfill
4. Kiểm tra dữ liệu sau backfill

Không seed sau khi đã migrate — sẽ không test được logic backfill.

---

## 9. Flyway migrate và validate trên staging

### 9.1. Kiểm tra branch và target trước khi chạy

**Target phụ thuộc `pom.xml` của branch bạn đang checkout** — không phụ thuộc PR đã merge
hay chưa. Cùng một profile có thể có `target` khác nhau giữa các branch.

```powershell
cd <đường-dẫn>\backend

# 1. Branch hiện tại
git branch --show-current

# 2. Target THỰC TẾ trong pom.xml của branch này
Select-String -Path pom.xml -Pattern '<id>|<target>' | ForEach-Object { $_.Line.Trim() }

# 3. Migration có sẵn trong branch này
Get-ChildItem ..\database\legacy-hybrid-local -Filter 'V*.sql' |
  Sort-Object Name | Select-Object -Last 3
```

**Đối chiếu target với migration có sẵn:**

| Branch | Profile `hybrid-local-existing-v13` | Ghi chú |
|---|---:|---|
| `main` | **25** | V14–V25 (+ V19/V20 từ `research-migrations/`) |
| PR #38 (Coordinate Provenance) | **dự kiến 26** | Thêm V26 — kiểm tra `pom.xml` thực tế |
| PR #41 (News Backend) | **dự kiến 27** | Thêm V27 — kiểm tra `pom.xml` thực tế |

**Không giả định.** Luôn đọc `<target>` trong `pom.xml` của branch đang checkout. Nếu
`target` nhỏ hơn version cao nhất trong `database/legacy-hybrid-local/`, Flyway sẽ bỏ qua
migration đó — dấu hiệu pom chưa được cập nhật cho branch.

**Kiểm tra chéo:**

```powershell
$target = (Select-String -Path pom.xml -Pattern '<target>(\d+)</target>' |
           Select-Object -First 1).Matches.Groups[1].Value
$highest = (Get-ChildItem ..\database\legacy-hybrid-local -Filter 'V*.sql' |
            ForEach-Object { [int]($_.Name -replace '^V(\d+)__.*$','$1') } |
            Measure-Object -Maximum).Maximum
Write-Output "pom target = $target | migration cao nhất = $highest"
if ([int]$target -lt $highest) {
    Write-Output "CẢNH BÁO: pom target thấp hơn migration có sẵn — kiểm tra lại branch"
}
```

### 9.2. Cấu hình môi trường — dùng tài khoản migration

**Không dùng `root` cho Flyway.** Dùng `smartprop_flyway` đã tạo ở mục 6.7:

```powershell
$env:DB_URL      = 'jdbc:mysql://127.0.0.1:3307/smartprop?connectionTimeZone=UTC'
$env:DB_USER     = 'smartprop_flyway'
$env:DB_PASSWORD = $FLYWAY_PW_PLAIN   # biến từ mục 6.7, không hardcode
```

> **Không đặt `DB_PASSWORD = ''`.** Sau mục 6.6, root đã có mật khẩu; `smartprop_flyway`
> luôn có mật khẩu. Mật khẩu rỗng sẽ bị từ chối.

### 9.3. Kiểm tra trạng thái

```powershell
.\mvnw.cmd -o -B -P hybrid-local-existing-v13 flyway:info
```

> **`-o` (offline) chỉ dùng khi dependencies đã có trong `~/.m2`.** Nếu chưa từng build,
> bỏ `-o` để Maven tải dependencies.

**Kỳ vọng sau khi import baseline V21:**

```
Schema version: 21
| 22 | property image analysis      | Pending |
| 23 | advisor chat checkpoints     | Pending |
| 24 | public pre purchase evidence | Pending |
| 25 | flood planned risk catalog   | Pending |
```

### 9.4. Áp dụng migration

```powershell
.\mvnw.cmd -o -B -P hybrid-local-existing-v13 flyway:migrate
if ($LASTEXITCODE -ne 0) { throw "flyway:migrate thất bại (exit $LASTEXITCODE)" }
```

**Kỳ vọng:** V22 → V23 → V24 → V25 áp dụng tuần tự.

### 9.5. Validate — chỉ PASS khi không còn pending

```powershell
.\mvnw.cmd -o -B -P hybrid-local-existing-v13 flyway:validate
$validateExit = $LASTEXITCODE

if ($validateExit -ne 0) {
    Write-Output "flyway:validate FAIL (exit $validateExit) — còn migration pending hoặc checksum sai"
    Write-Output "Chạy flyway:info để xem version nào pending, rồi flyway:migrate."
} else {
    Write-Output "flyway:validate PASS"
}
```

**Điều kiện PASS:** `$LASTEXITCODE -eq 0` **và** output có `Successfully validated N migrations`.

**Nếu command trả lỗi** như:

```
Detected resolved migration not applied to database: 22
```

thì đó là **FAIL**, không phải PASS. Nghĩa là còn migration pending — chạy
`flyway:migrate` trước.

> **Đã kiểm chứng:** trên baseline V21 (chưa migrate), `flyway:validate` trả lỗi
> `Detected resolved migration not applied to database: 22`. Đây là trạng thái **dự kiến
> trước khi migrate**, không phải PASS. Chỉ sau khi migrate đủ V22–V25 thì validate mới
> PASS.

### 9.6. Quy tắc

- **Không** bật `outOfOrder=true`.
- **Không** chạy `flyway:repair` khi chưa hiểu nguyên nhân.
- **Không** sửa `flyway_schema_history` bằng SQL tay.
- **Không** tắt checksum validation.
- **Không** đánh dấu validate PASS nếu command trả lỗi.

## 10. Cấu hình Backend kết nối staging

### 10.1. Profile

| Profile | Port | Dùng khi |
|---|---:|---|
| `hybrid-local-existing-v13` | 3306 | Chạy app với database thật |
| `hybrid-local-existing-v13-staging` | 3307 | Test migration, integration test |
| `standard-migrations` | — | Database dựng mới từ V1 |

### 10.2. Chạy với staging — tài khoản backend

**Không dùng `root`.** Dùng `smartprop_app` đã tạo ở mục 6.7 (chỉ DML, không DDL):

```powershell
$env:SPRING_PROFILES_ACTIVE = 'hybrid-local-existing-v13-staging'
$env:DB_URL      = 'jdbc:mysql://127.0.0.1:3307/smartprop?connectionTimeZone=UTC'
$env:DB_USER     = 'smartprop_app'
$env:DB_PASSWORD = $APP_PW_PLAIN   # biến từ mục 6.7, không hardcode
$env:JWT_SECRET  = '<chuỗi-ngẫu-nhiên-32-byte>'

cd <đường-dẫn>\backend
.\mvnw.cmd -o -B spring-boot:run
```

> **`DB_PASSWORD` không được rỗng.** Sau mục 6.6, mọi tài khoản đều có mật khẩu.
> Nếu bạn thấy hướng dẫn nào dùng `DB_PASSWORD = ''`, đó là trước khi đặt mật khẩu —
> không áp dụng sau bước 6.6.

### 10.3. Chạy integration test

Integration test cần **quyền DDL** (tạo/xoá bảng test, cleanup), nên dùng tài khoản
migration thay vì `smartprop_app`:

```powershell
$env:DB_URL      = 'jdbc:mysql://127.0.0.1:3307/smartprop?connectionTimeZone=UTC'
$env:DB_USER     = 'smartprop_flyway'
$env:DB_PASSWORD = $FLYWAY_PW_PLAIN
$env:SPRING_PROFILES_ACTIVE = 'hybrid-local-existing-v13-staging'
$env:JWT_SECRET  = '<chuỗi-ngẫu-nhiên-32-byte>'

.\mvnw.cmd -o -B test
```

> **`-o` (offline) chỉ dùng khi dependencies đã có.** Nếu chưa build lần nào, bỏ `-o`.

### 10.4. Guard trong test

Test có ghi dữ liệu **tự kiểm tra port** trước khi chạy:

```java
Integer port = jdbc.queryForObject("SELECT @@port", Integer.class);
assertThat(port).isEqualTo(3307);
```

Đây là guard fail-closed — test từ chối chạy nếu không phải 3307.

**Giới hạn:** guard này chỉ kiểm tra **port**, không kiểm tra `datadir` hay `server_uuid`.
Nếu bạn chạy một instance khác cũng trên 3307, guard sẽ không phát hiện. Vì vậy vẫn phải
kiểm tra identity bằng tay (mục 7.1) trước khi chạy test có ghi dữ liệu.

### 10.5. Guard của Spring không bảo vệ lệnh CLI

`MigrationProfileEnvironmentGuard` chạy khi Spring Boot khởi động với profile staging —
nó kiểm tra `DB_URL` phải là `127.0.0.1:3307/smartprop` và `@@datadir` phải chứa
`mysql-isolated`.

Nhưng guard **không chạy** cho:

- `mysql.exe` (mọi lệnh trực tiếp)
- `mysqldump`
- `mvnw flyway:*` (profile Maven chỉ set `locations`/`target`, không kiểm tra URL)

Xem mục 6.9 để biết bảng đầy đủ.

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
| `Staging must use the isolated datadir` | Datadir không phải `mysql-isolated` | **Dừng thực thi.** Kiểm tra và dựng lại staging datadir đúng. **Không** dùng profile local để bỏ qua staging guard |
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
| `flyway:validate` trên V21 | Trả lỗi `Detected resolved migration not applied: 22` — **đây là FAIL, không phải PASS** |
| Guard từ chối URL khác | `MigrationLineageConfigurationTest` 21 test |
| Guard từ chối gap/duplicate/order | `MigrationLineageStrictTest` 18 test — **thuộc PR #41, chưa merge** |
| Test ghi dữ liệu tự kiểm tra port | `assertThat(port).isEqualTo(3307)` trong IT |
| `pom.xml` target | standard = **23**, legacy-hybrid-local = **25** trên `main` |

### DOCUMENTED_ONLY — chưa chạy thử

Các hướng dẫn sau **chưa được thực thi end-to-end** trong quá trình soạn tài liệu:

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| Dựng MySQL từ đầu theo mục 6 | **DOCUMENTED_ONLY** | Viết dựa trên môi trường đã có sẵn, chưa chạy lại từ datadir trống |
| `--initialize-insecure` + đặt mật khẩu root | **DOCUMENTED_ONLY** | Chưa chạy chuỗi lệnh này |
| Tạo `smartprop_flyway` / `smartprop_app` | **DOCUMENTED_ONLY** | Phân quyền theo least-privilege, chưa kiểm chứng từng GRANT |
| Readiness loop + PID check (mục 6.5) | **DOCUMENTED_ONLY** | Chưa chạy trên máy sạch |
| Áp dụng V26 (PR #38) | **NOT_RUN** | Thuộc PR #38, chưa merge |
| Áp dụng V27 (PR #41) | **NOT_RUN** | Thuộc PR #41, chưa merge |
| Triển khai lên 3306 | **NOT_RUN** | Không thực hiện — database nhóm chỉ đọc |
| Fixture cho mọi module | **DOCUMENTED_ONLY** | Chỉ ví dụ tối thiểu, chưa seed thật |
| Fixture có bcrypt hash hợp lệ | **DOCUMENTED_ONLY** | Chưa tạo hash thật để test login |

**Không đánh dấu VERIFIED cho bất kỳ mục nào ở bảng trên.**

---

## Liên kết

- [TEAM_SETUP.md](../TEAM_SETUP.md) — thiết lập chung, biến môi trường, chạy app
- [database/README.md](../../database/README.md) — cấu trúc thư mục migration
- [ops/OPERATIONS.md](../../ops/OPERATIONS.md) — backup/restore, vận hành
- [database/docs/database-design.md](../../database/docs/database-design.md) — thiết kế schema
