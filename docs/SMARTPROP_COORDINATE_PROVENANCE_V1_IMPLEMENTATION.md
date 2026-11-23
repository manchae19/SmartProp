# SmartProp — Coordinate Provenance V1: Triển khai

**Ngày:** 2026-11-23
**Base:** `main @ d202792` (sau merge PR #35 và #36)
**Branch:** `feature/coordinate-provenance-v1`

---

## Tổng quan

Coordinate Provenance V1 ghi nhận **nguồn gốc, độ chính xác và lịch sử thay đổi tọa độ**
của từng bất động sản. Hệ thống tách ba khái niệm độc lập mà trước đây bị lẫn:

| Khái niệm | Câu hỏi | Nguồn dữ liệu |
|---|---|---|
| `geographic_validity` | Điểm có hợp lệ và đúng địa bàn không? | `DanangSpatialValidator` |
| `coordinate_provenance` | Tọa độ đến từ đâu? | `coordinate_source` |
| `parcel_accuracy` | Có đúng thửa đất không? | `accuracy_level` + `verification_status` |

**`VERIFIED_EXACT` chỉ trả lời câu hỏi thứ nhất, ở cấp quận.** Nó không suy ra được
hai câu còn lại — đây là kết luận trung tâm của PR #36 và là ràng buộc thiết kế của
V1.

---

## A. Database

### A.1. Migration

**`V26__property_coordinate_provenance.sql`** — V26 còn trống sau V25.

Bảng `property_coordinate_audit`, 31 cột, 7 index, 3 FK:

| Nhóm | Cột |
|---|---|
| Identification | `id`, `property_id`, `revision` |
| Coordinate snapshot | `audited_latitude`, `audited_longitude`, `srid`, `coordinate_fingerprint`, `fingerprint_version` |
| Address snapshot | `address_snapshot`, `district_snapshot`, `ward_snapshot` |
| Provenance | `coordinate_source`, `source_reference`, `source_recorded_at`, `source_recorded_by` |
| Accuracy | `accuracy_level`, `accuracy_meters`, `accuracy_method` |
| Verification | `verification_status`, `verification_method`, `verified_at`, `verified_by`, `evidence_reference` |
| Geographic validation | `geographic_validation_status`, `geographic_validation_note`, `validator_scope_version`, `validated_at` |
| Lifecycle | `created_at`, `superseded_at`, `superseded_reason`, `current_key` |

### A.2. Ràng buộc then chốt

```sql
-- Mỗi tin chỉ có tối đa một audit hiện hành.
-- MySQL 8 không có partial index → dùng cột sinh VIRTUAL.
current_key CHAR(36) GENERATED ALWAYS AS (
  IF(superseded_at IS NULL, property_id, NULL)) VIRTUAL,
CONSTRAINT uq_coord_audit_current UNIQUE (current_key)

-- Accuracy cấp thửa chỉ hợp lệ khi đã xác minh độc lập.
CONSTRAINT ck_coord_audit_parcel_requires_verification CHECK (
  accuracy_level <> 'PARCEL' OR verification_status = 'VERIFIED')

-- VERIFIED phải có phương pháp và thời điểm.
CONSTRAINT ck_coord_audit_verified_fields CHECK (
  verification_status <> 'VERIFIED'
  OR (verification_method IS NOT NULL AND verified_at IS NOT NULL))

-- accuracy_meters chỉ có khi accuracy_level khác UNKNOWN.
CONSTRAINT ck_coord_audit_accuracy_meters CHECK (
  (accuracy_level = 'UNKNOWN' AND accuracy_meters IS NULL)
  OR (accuracy_level <> 'UNKNOWN'))
```

**Vì sao `VIRTUAL` không phải `STORED`:** MySQL cấm FK `ON DELETE CASCADE` trên base
column của stored generated column. Đã gặp `ERROR 1215` khi thử `STORED`. `VIRTUAL`
vẫn đánh được UNIQUE index trong MySQL 8.

**Vì sao `BIGINT` cho `verified_by`:** `users.id` là `BIGINT`, không phải `CHAR(36)`.
Đã gặp `ERROR 3780` khi khai `CHAR(36)`.

### A.3. Kết quả kiểm chứng migration

```
Chạy trên smartprop_coordinate_it (DB cô lập, MySQL 8.4.13):
  31 cột | 7 index | 3 FK
```

**11/11 constraint test PASS:**

| Test | Kỳ vọng | Kết quả |
|---|---|---|
| T1 insert hợp lệ | PASS | ✅ |
| T2 `PARCEL` không `VERIFIED` | Bị chặn | ✅ |
| T3 hai audit current cùng property | Bị chặn | ✅ |
| T4 `coordinate_source` lạ | Bị chặn | ✅ |
| T5 `accuracy_meters` với `UNKNOWN` | Bị chặn | ✅ |
| T6 `VERIFIED` thiếu method | Bị chặn | ✅ |
| T7 FK property không tồn tại | Bị chặn | ✅ |
| T8 latitude ngoài `[-90,90]` | Bị chặn | ✅ |
| T9 `revision < 1` | Bị chặn | ✅ |
| T10 supersede rồi insert mới | PASS | ✅ |
| T11 `VERIFIED` + `PARCEL` + method + verified_at | PASS | ✅ |

### A.4. Backfill dữ liệu cũ

**`database/seeds/coordinate_provenance_backfill_v1.sql`**

Nguyên tắc: **không suy nguồn từ tên ảnh, không tự xác minh cấp thửa.**

```text
coordinate_source   = UNKNOWN
accuracy_level      = UNKNOWN
accuracy_meters     = NULL
verification_status = UNVERIFIED
```

**Idempotent:** chỉ chèn cho tin chưa có audit hiện hành.

```
Lần 1: 155 tin → 155 audit
Lần 2: 0 dòng (không tạo trùng)
```

Không sửa `properties.location`, `listing_code`, `status` hay `owner`.

---

## B. Backend

### B.1. File mới

| File | Vai trò |
|---|---|
| `PropertyCoordinateAudit.java` | Enum + record `Status` + hàm `derive()` suy ba cờ eligibility |
| `PropertyCoordinateAuditRepository.java` | JDBC access, fingerprint SHA-256 |
| `PropertyCoordinateAuditService.java` | Điều phối ghi audit, verify, mark stale |
| `PropertyCoordinateController.java` | API đọc trạng thái, lịch sử, verify, pending |

### B.2. File sửa

| File | Thay đổi |
|---|---|
| `PropertyService.java` | Gọi `coordinateAudit.record()` trong `create()` và `patch()`; `view()` nhận `Coordinate` |
| `PropertyDtos.java` | Thêm record `Coordinate` vào `View` |

### B.3. Fingerprint — giải quyết "đổi địa chỉ nhưng giữ tọa độ"

```java
public static String fingerprint(double latitude, double longitude,
                                 String address, String district, String ward,
                                 String validatorScopeVersion) {
    String payload = String.format(Locale.ROOT, "%.7f|%.7f|%s|%s|%s|%s",
        latitude, longitude, address, district, ward, validatorScopeVersion);
    // SHA-256
}
```

**Bốn thành phần:** tọa độ + địa chỉ + quận + phường + phiên bản validator.

Đổi **bất kỳ** thành phần nào cũng làm fingerprint đổi → audit cũ bị supersede. Đây là
điểm sửa cho vấn đề nêu trong PR #36 mục 15: *"Không chỉ so sánh latitude/longitude
rồi coi trạng thái cũ vẫn còn hiệu lực."*

**Làm tròn 7 chữ số thập phân** (≈1 cm) trước khi hash để nhiễu IEEE-754 không làm đổi
fingerprint. Đã có test `fingerprintIgnoresFloatingPointNoise`.

### B.4. Luồng create

```text
POST /api/v1/properties
  → PropertyService.create()
      → access.publisherForUpdate(actor)      [quyền BROKER/ADMIN]
      → fill(p, r)                            [tạo POINT từ lat/lon]
      → properties.saveAndFlush(p)
      → coordinateAudit.record(p, USER_PINNED, null, actor)
          → fingerprint(lat, lon, address, district, ward, scopeVersion)
          → supersedeCurrent() nếu đã có bản cũ
          → validator.validate()              [geographic validity]
          → insert audit (accuracy=UNKNOWN, verification=UNVERIFIED)
      → commit
```

`@Transactional(propagation = MANDATORY)` trên `record()` — audit lỗi thì property
rollback theo. Không có trạng thái "property tạo thành công nhưng audit mất".

### B.5. Luồng update

`patch()` gọi `record()` sau `saveAndFlush`. Nếu fingerprint không đổi (người dùng lưu
form mà không đổi vị trí), **không tạo bản ghi mới** — tránh phình lịch sử.

Nếu fingerprint đổi: supersede bản cũ → tạo revision mới với `accuracy=UNKNOWN`,
`verification=UNVERIFIED`. **Không kế thừa xác minh của tọa độ cũ.**

### B.6. Luồng publish

`transition()` **không** gọi `record()`. `PUBLISHED` không nâng mức xác minh — đúng
yêu cầu PR #36 mục 16.

### B.7. API

| Endpoint | Quyền | Mô tả |
|---|---|---|
| `GET /properties/{id}/coordinate` | Công khai (tin PUBLISHED), chủ tin, admin | Trạng thái tọa độ + 3 cờ eligibility |
| `GET /properties/{id}/coordinate/history` | Chủ tin, admin | Lịch sử đầy đủ |
| `GET /admin/coordinates/pending` | Admin | Tin chờ xác minh |
| `POST /properties/{id}/coordinate/verify` | **Admin** | Ghi quyết định xác minh |

**Không có endpoint nào cho phép người đăng tự đặt `verificationStatus`.** Quyền kiểm
tra ở `access.admin(actor)`, không dựa vào giá trị client gửi.

### B.8. Response

`PropertyDtos.View` có thêm trường `coordinate`:

```json
{
  "coordinateSource": "USER_PINNED",
  "accuracyLevel": "UNKNOWN",
  "accuracyMeters": null,
  "verificationStatus": "UNVERIFIED",
  "geographicValidationStatus": "VERIFIED_EXACT",
  "referenceMapEligible": true,
  "distanceAnalysisEligible": false,
  "parcelAnalysisEligible": false,
  "revision": 1,
  "auditedAt": "2026-11-23T12:00:00Z"
}
```

**Tương thích ngược:** trường `coordinate` là bổ sung. Client cũ bỏ qua được. Không xóa
hay đổi ngữ nghĩa trường nào đang có.

### B.9. Quy tắc eligibility

Nguồn duy nhất: `PropertyCoordinateAudit.derive()`.

```text
referenceMapEligible     = geographicStatus ∈ {VERIFIED_EXACT, VERIFIED_BOUNDARY_BUFFER}
distanceAnalysisEligible = referenceMapEligible
                           ∧ coordinateSource ≠ UNKNOWN
                           ∧ accuracyLevel ≠ UNKNOWN
parcelAnalysisEligible   = accuracyLevel = PARCEL ∧ verificationStatus = VERIFIED
```

**`VERIFIED_EXACT` một mình không bật `distanceAnalysisEligible`.** Đã có test
`verifiedExactAloneDoesNotEnableDistanceAnalysis`.

---

## C. Frontend

### C.1. Component mới

**`CoordinateStatusPanel.jsx`** + `.css`

Hiển thị:
- Headline theo mức bằng chứng (`coordinateHeadline`)
- Cảnh báo khi `INVALID_DISTRICT_MISMATCH` — **không tự di chuyển marker**
- Nguồn vị trí, độ chính xác, trạng thái xác minh
- Ghi chú "chưa xác minh cấp thửa" khi chỉ có `referenceMapEligible`

**Màu theo mức bằng chứng:** `verified` (xanh), `reference` (xám), `warning` (vàng),
`neutral`. **Không dùng đỏ cho "chưa xác minh"** — chưa xác minh không phải lỗi.

### C.2. Tích hợp

| File | Thay đổi |
|---|---|
| `ListingDetailView.jsx` | Chèn `<CoordinateStatusPanel coordinate={view.property?.coordinate} />` trước `PrePurchaseChecks` |
| `PostView.jsx` | Thêm ghi chú "vị trí tham khảo" dưới map picker |

**Tái sử dụng `locationLabel`** có sẵn — không tạo logic hiển thị trùng.

---

## D. GIS và AI

### D.1. GIS eligibility

Ba cờ do backend tính, GIS đọc từ `coordinate` trong response. **Không** GIS nào tự suy
từ `geographicValidationStatus`.

**Mặc định an toàn:** thiếu provenance hoặc accuracy → `distanceAnalysisEligible = false`,
`parcelAnalysisEligible = false`.

### D.2. Chưa kích hoạt

| Chức năng | Trạng thái | Lý do |
|---|---|---|
| `VERIFIED_AREA_OVERLAP` | **NOT_IMPLEMENTED** | Chưa có polygon vùng ngập (PR #35) |
| `NEAR_VERIFIED_LOCATION` | **NOT_IMPLEMENTED** | Chưa có geometry vị trí ngập |
| Đo khoảng cách tới điểm ngập | **BLOCKED** | `distanceAnalysisEligible = 0/152` |

### D.3. AI Advisor

**Không thay đổi pipeline XGBoost V1.3.** Không retrain. Không sửa Recommendation.

Advisor có thể đọc `coordinate` từ response property nếu cần, nhưng **chưa tích hợp
trong PR này** — cần thiết kế prompt riêng để không cho AI khẳng định vượt bằng chứng.

---

## E. Kiểm thử

| Suite | Passed | Failed | Skipped |
|---|---:|---:|---:|
| Backend unit (toàn bộ) | **196** | 0 | 0 |
| — trong đó `PropertyCoordinateAuditTest` | **8** | 0 | 0 |
| **HTTP integration (`CoordinateProvenanceIT`)** | **14** | 0 | 0 |
| Flyway validate | **12 migrations** | 0 | 0 |
| Constraint SQL (DB cô lập) | **11** | 0 | 0 |
| Backfill idempotency | **2 lần** | 0 | 0 |
| Frontend build (Vite) | **PASS** (8.25s) | 0 | 0 |
| Frontend unit | **NOT_RUN** | — | — |

**Frontend unit chưa chạy:** chưa có test cho `CoordinateStatusPanel`. Cần bổ sung ở PR
sau — component hiện chỉ render, logic eligibility nằm ở backend đã có test.

### E.1. Test đã viết

`PropertyCoordinateAuditTest` — 8 ca:

1. `verifiedExactAloneDoesNotEnableDistanceAnalysis`
2. `distanceAnalysisNeedsProvenanceAndAccuracy`
3. `parcelAnalysisNeedsParcelAccuracyAndVerification`
4. `boundaryBufferStillAllowsReferenceMap`
5. `invalidDistrictMismatchDisablesEverything`
6. `absentStatusIsSafeDefault`
7. `fingerprintChangesWhenAddressChanges`
8. `fingerprintIgnoresFloatingPointNoise`

---

## F. Giới hạn còn tồn tại

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| Migration V26 | **IMPLEMENTED + TESTED** | Chạy trên DB cô lập |
| Bảng audit + constraints | **IMPLEMENTED + TESTED** | 11/11 constraint test PASS |
| Ghi audit khi create/update | **IMPLEMENTED + TESTED** | 14 HTTP integration test |
| Fingerprint đổi theo địa chỉ | **IMPLEMENTED + TESTED** | Unit + integration test |
| API đọc trạng thái | **IMPLEMENTED + TESTED** | Public detail trả audit thật |
| API verify (admin) | **IMPLEMENTED + TESTED** | `expectedRevision` chặn race |
| Backfill dữ liệu cũ | **IMPLEMENTED + TESTED** | Idempotent, 155 tin |
| Frontend hiển thị trạng thái | **IMPLEMENTED** | Build PASS, chưa có unit test |
| Frontend cảnh báo sai địa bàn | **IMPLEMENTED** | Chưa có test |
| Admin review UI | **NOT_IMPLEMENTED** | API có, UI chưa |
| GIS flood integration | **BLOCKED** | Thiếu geometry ngập |
| AI Advisor integration | **NOT_IMPLEMENTED** | Cần thiết kế prompt riêng |
| Integration test HTTP | **IMPLEMENTED + TESTED** | 14/14 PASS trên DB cô lập |

### F.1. Việc cần làm ở PR sau

1. **Integration test HTTP** cho create/update/verify — cần Spring Boot test với DB cô lập.
2. **Admin review UI** — dùng `GET /admin/coordinates/pending` đã có.
3. **Frontend unit test** cho `CoordinateStatusPanel`.
4. **AI Advisor integration** — thêm `coordinate` vào evidence, thiết kế prompt để AI
   không khẳng định vượt bằng chứng.
5. **GIS flood integration** — chờ polygon vùng ngập từ nguồn có thẩm quyền.

---

## F.2. Bảy blocker đã sửa sau review

| Blocker | Trước | Sau |
|---|---|---|
| Transaction verify | `MANDATORY` không có transaction bao ngoài → `IllegalTransactionStateException` | `@Transactional` trên service — service tự mở transaction |
| Revision race | `WHERE property_id = ? AND superseded_at IS NULL` — xác minh nhầm revision mới | `WHERE property_id = ? AND revision = ? AND superseded_at IS NULL` + `expectedRevision` bắt buộc → 409 |
| Public detail | `PropertySearch.detail()` dùng `view()` không coordinate → luôn `absent()` | Nối `service.coordinate(id)` vào tất cả 8 điểm gọi |
| Source provenance | Gán `USER_PINNED` cho mọi request | `UNKNOWN` — request chỉ mang lat/lon, không chứng minh thao tác ghim |
| Optional audit | `@Autowired(required=false)` + `if (coordinateAudit != null)` | Constructor injection bắt buộc — audit lỗi thì property rollback |
| Eligibility cấp thửa | Chỉ `PARCEL` + `VERIFIED` | Thêm geographic validity + provenance + evidence (method + verifiedAt) |
| Backfill fingerprint | `FORMAT(x, 7)` thêm dấu phẩy phân cách (`1,234.5000000`) | `CAST(... AS DECIMAL(10,7))` — khớp `String.format(Locale.ROOT)` |

### Chi tiết từng sửa

**Blocker 1 — transaction.** `verify()` đổi từ `MANDATORY` sang `@Transactional`. Controller
không mở transaction; service tự mở. Đã kiểm chứng qua HTTP: `adminVerifySucceedsWithoutTransactionException`
PASS, không ném `IllegalTransactionStateException`.

**Blocker 2 — revision race.** Thêm `expectedRevision` vào `VerifyRequest` (`@NotNull @Min(1)`).
Repository `UPDATE ... WHERE property_id = ? AND revision = ? AND superseded_at IS NULL`.
Affected rows = 0 → 409. Test `staleExpectedRevisionReturns409` PASS: admin gửi revision 1
sau khi người đăng đã tạo revision 2 → 409, revision 2 vẫn `UNVERIFIED`.

Thêm `CONSTRAINT uq_coord_audit_revision UNIQUE (property_id, revision)` chặn hai request
đồng thời cùng tính `maxRevision()+1`.

**Blocker 3 — public detail.** `PropertySearch.detail()` và 7 điểm gọi khác
(`FavoriteService` ×2, `PropertyMediaService`, `PropertyModerationService` ×3) đã nối
`service.coordinate(id)`. Test `publicDetailReturnsRealAuditNotAbsent` PASS — trả
`coordinateSource=UNKNOWN`, `revision=1`, không phải `absent()`.

Test `publicDetailDoesNotLeakVerifierIdentity` PASS — response không chứa `verifiedBy`
hay `evidenceReference`.

**Blocker 4 — provenance.** `create()` và `patch()` ghi `Source.UNKNOWN`. Lý do: request
chỉ mang `latitude`/`longitude`, không có bằng chứng người dùng đã ghim trên bản đồ hay
nhập tay. Ghi `USER_PINNED` sẽ là khai man. Test `createWritesAuditWithUnknownProvenance`
PASS.

**Blocker 5 — audit bắt buộc.** Bỏ `@Autowired(required=false)` và `if (coordinateAudit != null)`.
Constructor injection bắt buộc. Nếu bảng audit thiếu, Spring context fail rõ ràng thay vì
âm thầm bỏ qua.

**Blocker 6 — eligibility cấp thửa.** `derive()` yêu cầu **đồng thời**: geographic validity
+ provenance khác `UNKNOWN` + accuracy khác `UNKNOWN` + `VERIFIED` + có
`verificationMethod` và `verifiedAt` + `accuracyLevel = PARCEL`. Test
`parcelEligibilityRequiresAllConditions` PASS: `PARCEL` + `VERIFIED` nhưng provenance
`UNKNOWN` → `parcelAnalysisEligible = false`.

**Blocker 7 — fingerprint.** MySQL `FORMAT(1234.5, 7)` = `'1,234.5000000'` (có dấu phẩy);
Java `String.format(Locale.ROOT, "%.7f", 1234.5)` = `'1234.5000000'`. Đổi sang
`CAST(... AS DECIMAL(10,7))`. Đã kiểm chứng 7 ca: toạ độ nhỏ, âm, trailing zeros,
address NULL, unicode, scope khác — tất cả khớp.

**Giới hạn `DECIMAL(10,7)`:** tối đa 3 chữ số nguyên. Đà Nẵng có lat 15–16, lon 107–108
nên an toàn. Toạ độ ngoài khoảng này cần `DECIMAL(12,7)`.

**Scope version backfill:** `'BACKFILL_V1'` khác `validator.scopeVersion()` — fingerprint
backfill **không bao giờ** khớp runtime. Đây là chủ ý: lần đầu người dùng lưu tin, audit
backfill bị supersede và revision mới được tạo. Không có revision giả vì backfill chỉ tạo
một bản/tin với trạng thái `UNKNOWN` an toàn.

### Môi trường kiểm chứng HTTP

```
MySQL 8.4.13 @ 127.0.0.1:3307/smartprop (DB cô lập)
Profile: hybrid-local-existing-v13-staging
58 bảng + trigger properties_listing_code_insert/update
Users: 9001 BROKER, 9002 ADMIN, 9003 BROKER
```

**Lưu ý khi dựng DB test:** phải copy `flyway_schema_history` (lineage guard
`MigrationLineageConfiguration` yêu cầu BASELINE13/crawler14) và trigger V16
(`properties_listing_code_insert`) — nếu thiếu, `listing_code` không có default và
POST /properties trả 500.

### SecurityConfig

Thêm hai rule trước `anyRequest().denyAll()`:

```java
.requestMatchers(HttpMethod.POST,"/api/v1/properties/*/coordinate/verify").hasRole("ADMIN")
.requestMatchers(HttpMethod.GET,"/api/v1/properties/*/coordinate",
                 "/api/v1/properties/*/coordinate/history").permitAll()
```

Không thêm rule này thì endpoint mới bị `denyAll()` chặn.

---
## G. Quyết định thiết kế

| Quyết định | Lý do |
|---|---|
| Bảng riêng thay vì cột trong `properties` | Cần lịch sử nhiều revision; cột chỉ lưu trạng thái cuối |
| `VIRTUAL` generated column cho `current_key` | MySQL cấm FK CASCADE trên stored generated column |
| Fingerprint gồm cả địa chỉ | Đổi địa chỉ mà giữ tọa độ vẫn làm kết luận cũ hết hiệu lực |
| Làm tròn 7 chữ số trước hash | Nhiễu IEEE-754 không được làm đổi fingerprint |
| `MANDATORY` propagation | Audit và property phải cùng transaction |
| Không ghi audit khi fingerprint không đổi | Tránh phình lịch sử khi lưu form không đổi vị trí |
| `accuracy = UNKNOWN` mặc định | Không suy từ `VERIFIED_EXACT` hay số chữ số thập phân |
| `verification = UNVERIFIED` mặc định | Publish không nâng mức xác minh |
| Verify chỉ qua `access.admin()` | Không cho client tự khai `VERIFIED` |

---

## Phụ lục — Lệnh kiểm chứng

```bash
# Migration
mysql -h 127.0.0.1 -P 13306 -u root smartprop_coordinate_it \
  -e "source database/legacy-hybrid-local/V26__property_coordinate_provenance.sql"

# Constraints
python .scratch/test-constraints.py

# Backfill (idempotent)
mysql ... -e "source database/seeds/coordinate_provenance_backfill_v1.sql"   # lần 1
mysql ... -e "source database/seeds/coordinate_provenance_backfill_v1.sql"   # lần 2 → 0

# Backend
cd backend && ./mvnw test

# Flyway
./mvnw -P hybrid-local-existing-v13 flyway:validate

# Frontend
cd frontend && node node_modules/vite/bin/vite.js build
```

---

**Tài liệu liên quan**

- `docs/SMARTPROP_COORDINATE_PROVENANCE_AUDIT.md` (PR #36)
- `docs/SMARTPROP_GIS_V2_RESEARCH_AND_READINESS.md` (PR #35)
