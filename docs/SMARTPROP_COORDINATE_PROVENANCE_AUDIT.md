# SmartProp — Kiểm toán nguồn gốc và chất lượng tọa độ bất động sản

**Ngày kiểm toán:** 2026-11-23
**Mốc nền:** `main @ 034ec2d`
**Database:** `127.0.0.1:3306/smartprop` — **chỉ đọc**, không INSERT/UPDATE/DELETE/ALTER
**Phương pháp:** truy vấn SELECT + đọc mã nguồn + **chạy `DanangSpatialValidator` bằng Java thật**

---

## Trả lời sáu câu hỏi

**1. 152 tin bất động sản này thực chất từ đâu ra?**

Có **dấu hiệu mạnh** của một chiến dịch nạp hàng loạt: **151/152 tin** có ảnh theo quy
ước máy sinh (`batch_N_M.jpg` hoặc `<Tên_Đường>_N.jpg`), 173/173 ảnh lưu
`storage_provider='LOCAL'` với **0 ảnh qua Cloudinary**, 168/168 ảnh có `uploaded_by`
trùng `owner_id`, và 135 tin tạo trong **10 phút** cùng ngày.

Nhưng **không tìm thấy script nạp** trong repository hay git history, không có
`import_batch_id`, không có audit log. Vì vậy: **`STRONGLY_INFERRED`, không phải
`DIRECTLY_CONFIRMED`.**

**2. Vì sao database có 153 tin nhưng mẫu chỉ có 152?**

Vì **1 tin `DRAFT`** (`SP257`, "AutoScan local duplicate"). Bộ lọc mẫu dùng
`status='PUBLISHED'` nên loại nó ra.

**3. Bao nhiêu tin từ người dùng, import, crawler, seed, demo?**

| Nhóm | Confirmed | Inferred | Unknown |
|---|---:|---:|---:|
| Người dùng đăng thật | 0 | 0 | **0** |
| Nạp hàng loạt | **0** | **151** | 0 |
| Crawler / Tinix | 0 | 0 | **0** |
| Demo / seed / test | **1** | — | — |
| Chưa xác định | — | — | 0 |
| **Tổng** | **0** | **151** | **1** |

**4. Bao nhiêu tọa độ được xác minh cấp bất động sản?**

**Chưa tìm thấy bằng chứng xác minh cấp thửa cho bất kỳ tin nào trong 152 tin.**
Điều này **không** có nghĩa cả 152 tọa độ đều sai — nhiều điểm có thể đúng thực tế,
nhưng không có chứng cứ để chứng minh.

**5. `VERIFIED_EXACT` có đang bị hiểu sai thành độ chính xác cấp thửa?**

**Có.** `VERIFIED_EXACT` chỉ kiểm tra điểm nằm trong **polygon quận lịch sử** — vùng
rộng hàng chục km². Tên enum gợi ý "chính xác" nhưng ngữ nghĩa thực tế là "hợp lệ về
mặt địa giới hành chính cấp quận".

**6. Đã đủ điều kiện phát triển GIS ngập cấp bất động sản chưa?**

**Chưa.** Kết luận: **`NOT_READY_FOR_PARCEL_LEVEL_ANALYSIS`**.

---

## A. Nguồn gốc 152 tin

### A.1. Chênh lệch 153 và 152 — snapshot xác minh

**Thời điểm snapshot:** 2026-11-23 16:30 (Asia/Saigon)

```sql
SELECT COUNT(*) FROM properties;                                    -- 153
SELECT COUNT(*) FROM properties WHERE status='PUBLISHED';           -- 152
SELECT COUNT(*) FROM properties WHERE status='DRAFT';               --   1
```

| Điều kiện lọc | Số bản ghi | Loại bỏ |
|---|---:|---:|
| Tổng bảng `properties` | **153** | — |
| `status='PUBLISHED'` | **152** | **1** |
| `deleted_at IS NULL` | 153 | 0 |
| Chưa hết hạn | 153 | 0 |
| Không phải fixture (`f0000000-%`) | 153 | 0 |

**Chỉ một điều kiện loại bỏ bản ghi: `status='PUBLISHED'`.** Ba điều kiện còn lại
**không loại thêm bản ghi nào** — đã kiểm chứng bằng cách chạy từng điều kiện riêng lẻ.

Tin bị loại: `SP257` — "AutoScan local duplicate", `DRAFT`, địa chỉ `14 AutoScan Street`,
tạo 2026-11-13.

Bộ lọc mẫu dùng trong PR #33, #34, #35:

```sql
WHERE status='PUBLISHED' AND deleted_at IS NULL
  AND (expires_at IS NULL OR expires_at > UTC_TIMESTAMP(6))
  AND id NOT LIKE 'f0000000-%'
```

### A.2. Bằng chứng về quy ước đặt tên ảnh

**Kiểm tra quan hệ ảnh ↔ property ID** (không dùng số ảnh thay cho số tin):

| Chỉ số | Giá trị |
|---|---:|
| Tổng ảnh trong bảng | 173 |
| Ảnh liên kết với 152 tin PUBLISHED | **168** |
| Ảnh tên `batch_N_M.jpg` (toàn bảng) | **81** |
| **Property ID duy nhất có ảnh batch** | **73** |
| Tin **không** có ảnh batch | **79** |
| Ảnh batch có `uploaded_by` = owner | **81/81** |
| Ảnh không liên kết tin PUBLISHED | 5 |
| `storage_provider` | `LOCAL` cho **173/173** |
| Ảnh qua Cloudinary | **0** |
| `uploaded_by` = `owner_id` (168 ảnh của mẫu) | **168/168** |
| Ảnh dùng lại (sha256 trùng) | 38 ảnh có sha, 24 sha khác nhau |

**Phân bố ảnh batch theo ngày tạo tin:**

| Ngày | Tin có ảnh batch | Ảnh batch |
|---|---:|---:|
| 2026-11-02 | 6 | 14 |
| 2026-11-07 | 67 | 67 |

**Số lô:** 6 (`batch_1`, `batch_2`, `batch_3`, `batch_5`, `batch_7`, `batch_8`).

#### Nhóm 79 tin KHÔNG có ảnh batch — vẫn có bằng chứng

Đây là điểm quan trọng: **79 tin không có ảnh batch nhưng vẫn có ảnh theo quy ước
sinh tự động khác** — `<Tên_Đường>_N.jpg`:

```
SP001 | Ngô_Thế_Liễu_0.jpg
SP002 | Phan_Xích_Long_0.jpg, Phan_Xích_Long_1.jpg, Phan_Xích_Long_2.jpg
SP004 | Hòa_Minh_19_0.jpg, Hòa_Minh_19_1.jpg, Hòa_Minh_19_2.jpg
```

| Chỉ số | Giá trị |
|---|---:|
| Tin có ảnh `batch_N_M.jpg` **hoặc** `<Tên>_N.jpg` | **151/152** |
| Tin không có ảnh theo quy ước nào | **1** (`SP256`, ảnh `baseline.png`) |
| 79 tin không batch: có ảnh | **79/79** |
| 79 tin không batch: `created_at` = `published_at` cùng giây | **72/79** |
| 73 tin có batch: `created_at` = `published_at` cùng giây | **73/73** |
| 79 tin không batch: khung giờ tạo ngày 11-07 | 03:37:52 → 03:47:37 |
| 73 tin có batch: khung giờ tạo ngày 11-07 | 03:37:52 → 03:47:37 |

**Hai nhóm dùng chung khung giờ 10 phút, cùng owner, cùng quy ước đặt tên ảnh.**
Điều này cho thấy cả 151 tin được xử lý bởi cùng một quy trình, không chỉ 73 tin có
ảnh batch.

#### Giới hạn của bằng chứng này

**Tên ảnh là bằng chứng về quy ước đặt tên hoặc xử lý ảnh, không tự động chứng minh
cơ chế tạo bản ghi `properties`.**

Không kết luận ảnh được script sinh nếu chưa có bằng chứng về script đó. Có thể mô tả
chính xác hơn: *tên ảnh phù hợp quy ước batch do máy sinh*.

Không tìm thấy script nạp trong repo hay git history (xem A.4).

### A.3. Bằng chứng gián tiếp (INFERRED)

| Dấu hiệu | Giá trị | Mức |
|---|---|---|
| Số owner khác nhau | **2** (151 tin `BROKER`, 1 tin `ADMIN`) | INFERRED |
| Phân bố ngày tạo | 11-01: 6, 11-02: 10, **11-07: 135**, 11-13: 1 | INFERRED |
| Khoảng thời gian tạo 135 tin | 03:37:52 → 03:47:37 (**10 phút**) | INFERRED |
| `created_at` = `published_at` cùng giây | **135/135** | INFERRED |
| `listing_code` | `SP001`..`SP256`, thiếu 104 số | INFERRED |

**Những dấu hiệu này ủng hộ giả thuyết nạp hàng loạt nhưng không tự chứng minh cơ chế
tạo từng bản ghi.** Một owner không chứng minh tất cả tin được import; tạo nhanh không
chứng minh dữ liệu là giả; `created_at = published_at` không tự chứng minh chưa qua
quy trình duyệt.

### A.4. Điều KHÔNG tìm thấy

| Tìm gì | Kết quả |
|---|---|
| Script nạp trong repo | **Không có** — không file nào chứa `INSERT INTO properties` với 135 dòng |
| `import_batch_id` trong `properties` | **Không có cột này** |
| Audit log ghi tạo tin | **Không có** — `audit_logs` chỉ 5 bản ghi |
| FK `external_listings` → `properties` | **Không có** |
| Commit git chứa script nạp | **Không tìm thấy** |
| File CSV/JSON nguồn | **Không tìm thấy** |
| `DevDatabaseSeed` tạo properties | **Không có** — chỉ `DevAdminSeed` tạo admin |

**Vì vậy: 151 tin có dấu hiệu mạnh của việc nạp hàng loạt (`STRONGLY_INFERRED`), dựa
trên quy ước tên ảnh, thời điểm tạo tin và owner chung. Tuy nhiên, chưa có script,
import log hoặc metadata trực tiếp để chứng minh cơ chế tạo từng bản ghi.**

Báo cáo này **không** khẳng định:

- 151 tin chắc chắn được import bằng một script cụ thể
- 151 tin chắc chắn là dữ liệu bất động sản thật
- Không có người dùng thật nào từng đăng tin
- Không có dữ liệu nào từng bắt nguồn từ crawler

### A.5. Phân loại nguồn — bảng cuối

| Nhóm nguồn | Confirmed | Inferred | Unknown | Bằng chứng |
|---|---:|---:|---:|---|
| `MANUAL_USER_LISTING` | 0 | 0 | **0** | Không tìm thấy dấu hiệu đăng riêng lẻ — **không** khẳng định chắc chắn không có |
| `IMPORTED_LISTING` | **0** | **151** | 0 | Xem giải thích dưới |
| `CRAWLER_DATA` | 0 | 0 | **0** | `external_listings` (3204) không có FK tới `properties`; `tinix_dataset_records` (185 973) tách biệt — **không** khẳng định dữ liệu chưa từng xuất phát từ crawler |
| `SEED_OR_DEMO` | **1** | — | — | `SP256` "AutoScan local baseline", owner `ADMIN`, ảnh `baseline.png` |
| `UNKNOWN_ORIGIN` | — | — | 0 | — |
| **Tổng** | **0** | **151** | **1** | **152** |

#### Vì sao `IMPORTED_LISTING` là `STRONGLY_INFERRED`, không phải `DIRECTLY_CONFIRMED`

**Định nghĩa ba mức:**

| Mức | Nghĩa |
|---|---|
| `DIRECTLY_CONFIRMED` | Có chứng cứ trực tiếp về cơ chế tạo/import: script, import log, batch metadata có quan hệ rõ ràng đến bản ghi |
| `STRONGLY_INFERRED` | Có dấu hiệu mạnh: thời gian tạo hàng loạt, owner chung, tên ảnh batch, mã tin tuần tự — nhưng **chưa có log trực tiếp** của việc tạo tin |
| `UNKNOWN_ORIGIN` | Không đủ căn cứ kết luận |

**Bằng chứng hiện có cho 151 tin:**

| Bằng chứng | Loại | Có chứng minh cơ chế tạo `properties`? |
|---|---|---|
| 151/152 tin có ảnh theo quy ước máy sinh (`batch_N_M.jpg` hoặc `<Tên>_N.jpg`) | Gián tiếp | **Không** — chứng minh quy ước đặt tên ảnh |
| 168/168 ảnh `uploaded_by` = `owner_id` | Gián tiếp | **Không** — chứng minh cùng tài khoản |
| 173/173 ảnh `storage_provider='LOCAL'`, 0 Cloudinary | Gián tiếp | **Không** — chứng minh không qua UI upload |
| 135 tin tạo trong 10 phút ngày 11-07 | Gián tiếp | **Không** — chứng minh tạo nhanh |
| `created_at` = `published_at` cùng giây (135/135) | Gián tiếp | **Không** — chứng minh không qua duyệt thủ công |
| 151/152 tin một owner | Gián tiếp | **Không** — chứng minh cùng tài khoản |
| `listing_code` tuần tự `SP001`..`SP256` | Gián tiếp | **Không** — chứng minh cấp mã tự động |

**Không có bằng chứng trực tiếp nào:** không script, không `import_batch_id`, không
audit log, không FK từ bảng nguồn.

**Vì vậy: `STRONGLY_INFERRED`, không phải `DIRECTLY_CONFIRMED`.**

#### Điều báo cáo này KHÔNG khẳng định

| Không khẳng định | Lý do |
|---|---|
| "151 tin được import bằng script X" | Không tìm thấy script |
| "0 tin người dùng thật đăng" | Chỉ là **chưa tìm thấy bằng chứng** người dùng tự đăng |
| "0 tin từ crawler" | Không có provenance để kiểm chứng nguồn gốc dữ liệu ban đầu |
| "135 tin là dữ liệu bất động sản thật" | Giá/diện tích/ảnh khác nhau không chứng minh tính xác thực ngoài đời |
| "135 tin là dữ liệu giả" | Không có bằng chứng |

**Tách biệt hai kết luận:**

1. **Cơ chế nạp:** 151 tin có dấu hiệu mạnh của nạp hàng loạt (`STRONGLY_INFERRED`).
2. **Tính xác thực nội dung:** `UNKNOWN` — không đủ bằng chứng để kết luận thật hay giả.

---

## B. Chất lượng tọa độ

### B.1. Tính hợp lệ kỹ thuật

| Kiểm tra | Kết quả |
|---|---|
| Tổng tin trong mẫu | **152** |
| Có POINT hợp lệ | **152** |
| SRID = 4326 | **152** |
| `ST_IsValid` = true | **152** |
| Tọa độ `(0,0)` | **0** |
| Đảo trục lat/lon | **0** |
| Tọa độ trùng lặp hoàn toàn | **0** |

### B.2. Thống kê chữ số thập phân — sửa lại

**Vấn đề của báo cáo trước:** các nhóm `2 chữ số: 2`, `3 chữ số: 50`, `4 chữ số: 121`,
`trên 4 chữ số: 23` **cộng lại vượt 152** vì không định nghĩa rõ loại trừ hay cộng dồn.

**Nguyên nhân gốc:** MySQL `ST_Latitude`/`ST_Longitude` trả `DOUBLE`. In full precision
sinh artifact IEEE-754 — ví dụ `15.985000000000001` cho một tọa độ thực chất là `15.985`.
Đếm chữ số trên output thô là **sai phương pháp**.

**Cách sửa:** làm tròn về 9 chữ số (đủ chính xác ~0.1 mm) trước khi đếm chữ số có nghĩa.

#### A. Số chữ số thập phân biểu diễn — nhóm LOẠI TRỪ NHAU, tổng = 152

| Nhóm | Số tin |
|---|---:|
| ≤2 chữ số (thô ~1,1 km) | **1** |
| 3 chữ số (~110 m) | **97** |
| 4 chữ số (~11 m) | **41** |
| 5 chữ số (~1,1 m) | **1** |
| 6 chữ số (~0,11 m) | **1** |
| ≥7 chữ số (<0,11 m) | **11** |
| **TỔNG** | **152** |

#### B. Ngưỡng độ phân giải — CỘNG DỒN, **không được cộng các hàng**

Mỗi hàng là "số tin có độ phân giải **thô hơn hoặc bằng** ngưỡng":

| Ngưỡng | Số tin |
|---|---:|
| ≤2 chữ số | 1 |
| ≤3 chữ số | 98 |
| ≤4 chữ số | 139 |
| ≤5 chữ số | 140 |

#### C. Sai số vị trí thực tế

**`UNKNOWN` cho cả 152 tin.** Không có metadata nguồn gốc hay độ chính xác.

**Số chữ số thập phân KHÔNG suy ra được sai số thực tế.** Tọa độ lưu 6 chữ số không
chứng minh chính xác đến 10 cm; tọa độ 3 chữ số không chứng minh sai 110 m.

**Báo cáo trước ghi "50 tin có sai số 110 m" là SAI** — đó là độ phân giải biểu diễn,
không phải sai số nguồn.

### B.3. Phân loại nguồn gốc tọa độ

| Nhóm | Số lượng | Bằng chứng |
|---|---:|---|
| `PARCEL_VERIFIED` | **0** | Không có xác minh thực địa, không có dữ liệu địa chính |
| `USER_PINNED_UNVERIFIED` | **0** | Không có audit log ghi hành vi ghim |
| `GEOCODED_ADDRESS` | **0** | `PropertyService` không gọi geocoding khi tạo tin |
| `IMPORTED_COORDINATE` | **151** | Nạp hàng loạt, tọa độ đi kèm dữ liệu |
| `ADMIN_CENTROID_OR_DEFAULT` | **0** | Phân bố rộng, không dồn tâm quận |
| `UNKNOWN_PROVENANCE` | **1** | `SP256` — tin test |
| **Tổng** | **152** | |

### B.4. Cơ chế tạo tọa độ

**Backend** — `PropertyService.java` L53-57:

```java
Double lat = r.latitude() != null ? r.latitude() : p.location == null ? null : p.location.getY();
Double lon = r.longitude() != null ? r.longitude() : p.location == null ? null : p.location.getX();
if (...) throw ApiInputs.bad("Tọa độ bắt buộc: latitude [-90,90], longitude (-180,180]");
p.location = new GeometryFactory(new PrecisionModel(), 4326).createPoint(new Coordinate(lon, lat));
```

**Tọa độ đến từ request, không geocode.**

**Frontend** — `ManualLocationMap.jsx` L23-28:

```javascript
// This initial center is only a viewport. No point is selected until a deliberate action.
latitude: 16.0544,   // viewport mặc định, KHÔNG phải điểm được chọn
```

| Câu hỏi | Trả lời |
|---|---|
| Người đăng tự ghim được không? | **Có** |
| Có lưu vị trí mặc định của bản đồ không? | **Không** — viewport tách khỏi điểm chọn |
| Có tự điền tọa độ theo địa chỉ không? | **Không** |
| Có dùng geocoding API không? | **Không** trong luồng tạo tin |
| Có lưu nguồn gốc và độ chính xác? | **Không** — không có cột nào |
| Cập nhật địa chỉ có đồng bộ tọa độ? | Không kiểm chứng được — không có audit log |

---

## C. Kiểm toán `DanangSpatialValidator` — chạy Java thật

### C.1. Phương pháp

Báo cáo trước dùng **mô phỏng Python** — không đủ để khẳng định phân bố của Java.
Lượt này chạy **chính class production** qua harness:

```java
// backend/src/test/java/vn/smartprop/gis/CoordinateAuditHarness.java
DanangSpatialValidator validator = new DanangSpatialValidator(mapper);
DanangAdminNormalizer normalizer = new DanangAdminNormalizer();

GisDtos.AdminNormalizationResult normalized =
    normalizer.normalize(district, ward, city);          // chuẩn hoá như production
String canonical = normalized.canonicalDistrict();

GisDtos.CoordinateValidationResult result =
    validator.validate(lat, lon, canonical, true);       // allowPublicPin = true
```

**Điểm then chốt:** phải chuẩn hoá `district` qua `DanangAdminNormalizer` trước khi gọi
validator. Lần chạy đầu bỏ bước này nên 150/152 tin trả `VERIFIED_DANANG_POLYGON` —
validator không tìm thấy polygon vì tên quận chưa chuẩn hoá.

### C.2. Kết quả Java thật — 152 tin

| `CoordinateStatus` | Số tin Java | Số tin Python trước | Chênh lệch |
|---|---:|---:|---:|
| `VERIFIED_EXACT` | **140** | 137 | **+3** |
| `VERIFIED_BOUNDARY_BUFFER` | **11** | 11 | 0 |
| `VERIFIED_DANANG_POLYGON` | **0** | 1 | **−1** |
| `INVALID_DISTRICT_MISMATCH` | **1** | 1 | 0 |
| `INVALID_SWAPPED_AXES` | **0** | 0 | 0 |
| `OUTSIDE_DANANG_BOUNDS` | **0** | 2 | **−2** |
| `INVALID_COORDINATES` | **0** | 0 | 0 |
| `NONE_ADMIN_ONLY` | **0** | 0 | 0 |
| **TỔNG** | **152** | 152 | |

### C.3. Nguyên nhân chênh lệch

**`SP105` và `SP111` — báo cáo trước ghi `OUTSIDE_DANANG_BOUNDS`, thực tế `VERIFIED_EXACT`.**

Nguyên nhân: script Python tự đặt khung `lat 15.90–16.20, lon 108.05–108.35`, nhưng
`DanangSpatialValidator.java` L45-48 dùng khung **rộng hơn**:

```java
private static final double DANANG_MIN_LAT = 15.90;
private static final double DANANG_MAX_LAT = 16.25;
private static final double DANANG_MIN_LON = 107.80;
private static final double DANANG_MAX_LON = 108.40;
```

| ID | Tọa độ | Khung Python | Khung Java | Kết quả Java |
|---|---|---|---|---|
| `SP105` | 15.985, 108.028 | Ngoài (lon < 108.05) | **Trong** | `VERIFIED_EXACT` (Hòa Vang) |
| `SP111` | 16.125, 108.035 | Ngoài (lon < 108.05) | **Trong** | `VERIFIED_EXACT` (Hòa Vang) |

**Bài học:** không dùng ngưỡng do script tự đặt để gán trạng thái của Java validator.

**`SP256`** — Python ghi `VERIFIED_DANANG_POLYGON`, Java ghi `VERIFIED_EXACT`. Nguyên
nhân: Python không chuẩn hoá `district` (`Hai Chau` không dấu) nên không khớp polygon
`Hải Châu`; Java chuẩn hoá qua `DanangAdminNormalizer` nên khớp.

### C.4. Tin không phải `VERIFIED_EXACT`

| ID | Trạng thái | Quận chuẩn hoá | Ghi chú |
|---|---|---|---|
| `SP005` | `VERIFIED_BOUNDARY_BUFFER` | Cẩm Lệ | Cách biên ~103 m |
| `SP013` | `INVALID_DISTRICT_MISMATCH` | Liên Chiểu | Thuộc Hải Châu, lệch **2 734 m** |
| `SP032` | `VERIFIED_BOUNDARY_BUFFER` | Thanh Khê | Cách biên ~20 m |
| `SP039` | `VERIFIED_BOUNDARY_BUFFER` | Hải Châu | Cách biên ~5 m |
| `SP066` | `VERIFIED_BOUNDARY_BUFFER` | Hòa Vang | Cách biên ~449 m |
| `SP073` | `VERIFIED_BOUNDARY_BUFFER` | Cẩm Lệ | Cách biên ~36 m |
| `SP086` | `VERIFIED_BOUNDARY_BUFFER` | Hòa Vang | Cách biên ~428 m |
| `SP093` | `VERIFIED_BOUNDARY_BUFFER` | Cẩm Lệ | Cách biên ~346 m |
| `SP098` | `VERIFIED_BOUNDARY_BUFFER` | Hải Châu | Cách biên ~17 m |
| `SP110` | `VERIFIED_BOUNDARY_BUFFER` | Cẩm Lệ | Cách biên ~508 m |
| `SP117` | `VERIFIED_BOUNDARY_BUFFER` | Cẩm Lệ | Cách biên ~173 m |
| `SP149` | `VERIFIED_BOUNDARY_BUFFER` | Thanh Khê | Cách biên ~11 m |

---

## D. Ý nghĩa thật của `VERIFIED_EXACT`

### D.1. Điều kiện tạo

`DanangSpatialValidator.java` L167-179:

```java
if (canonicalDistrict != null && coreDistrictPolygons.containsKey(canonicalDistrict)) {
    Geometry declaredPoly = coreDistrictPolygons.get(canonicalDistrict);
    if (declaredPoly.contains(pt) || declaredPoly.touches(pt)) {
        return new CoordinateValidationResult(
            CoordinateStatus.VERIFIED_EXACT, ...,
            "Tọa độ WGS84 (SRID 4326) nằm khớp trong ranh giới địa lý "
            + districtDisplayLabel(canonicalDistrict) + ".");
    }
```

**`VERIFIED_EXACT` = điểm nằm trong polygon QUẬN đã khai báo.**

### D.2. Điều `VERIFIED_EXACT` KHÔNG xác minh

| Không xác minh | Ghi chú |
|---|---|
| Tọa độ đúng địa chỉ | Không có dữ liệu địa chỉ để đối chiếu |
| Tọa độ đúng số nhà | Không có dữ liệu số nhà |
| Tọa độ đúng tòa nhà | Không có dữ liệu tòa nhà |
| Tọa độ đúng thửa đất | Không có dữ liệu địa chính |
| Người dùng thực sự ghim | Không có audit log |
| Sai số dưới 10 m | Không có metadata độ chính xác |

### D.3. Polygon đang dùng

`danang-search-scopes.geojson` — **11 polygon, tất cả level `LEGACY_DISTRICT`**:

```
Hải Châu, Thanh Khê, Sơn Trà, Ngũ Hành Sơn, Cẩm Lệ, Liên Chiểu, Hòa Vang,
Hội An, Điện Bàn, Tam Kỳ, Núi Thành
```

**Ranh giới cấp quận cũ — không phải cấp phường, càng không phải cấp thửa.**

### D.4. Ngưỡng 750 m

`ADM2_BOUNDARY_TOLERANCE_METERS = 750.0` — bù sai số của **đường biên giản lược ADM2**
(ranh giới quận được vẽ đơn giản hoá). Đây là dung sai **của bản đồ**, không phải dung
sai **của tọa độ bất động sản**.

### D.5. Ba chiều độc lập

| Chiều | Validator kiểm tra? | Nguồn dữ liệu |
|---|---|---|
| `geographic_validity` — hợp lệ, đúng địa bàn | **Có** | Polygon quận |
| `coordinate_provenance` — tọa độ từ đâu | **Không** | Không có |
| `parcel_accuracy` — đúng thửa đất | **Không** | Không có |

**Không được dùng một trạng thái để suy ra hai trạng thái còn lại.**

### D.6. Chiến lược nâng cấp tương thích ngược

**Không đổi enum trong PR tài liệu này** — sẽ gây breaking change với Frontend, Advisor
và API clients. Kế hoạch cho PR triển khai sau:

| Bước | Hành động | Tương thích |
|---|---|---|
| 1 | Thêm enum mới `ADMIN_DISTRICT_CONTAINED`, `ADMIN_DISTRICT_NEAR_BOUNDARY`, `ADMIN_CITY_CONTAINED` | Không phá vỡ |
| 2 | `DanangSpatialValidator` trả enum mới | Cần cập nhật test |
| 3 | Thêm trường `legacyStatus` trong DTO trả cả tên cũ | Frontend cũ vẫn chạy |
| 4 | Frontend đọc `legacyStatus` nếu `status` không nhận diện được | Không cần deploy đồng thời |
| 5 | Sau 1 chu kỳ phát hành, xoá `legacyStatus` | Breaking change có kiểm soát |

---

## E. Phân loại khả năng dùng cho GIS V2

### E.1. Ba khả năng tách biệt

Báo cáo trước gộp "hiển thị marker" và "đo khoảng cách" vào một nhóm
`ELIGIBLE_FOR_APPROXIMATE_MAP_ONLY`, rồi cho phép đo khoảng cách chỉ dựa trên
`VERIFIED_EXACT` + số chữ số thập phân. **Đó là mâu thuẫn**: số chữ số thập phân
không phải độ chính xác thực tế.

Tách thành ba khả năng độc lập:

#### A. `REFERENCE_MAP_ELIGIBLE` — hiển thị marker tham khảo

Điều kiện tối thiểu:

- Geometry hợp lệ (`ST_IsValid`, SRID 4326, không `(0,0)`, không đảo trục)
- Tọa độ phù hợp phạm vi địa lý được kiểm tra (`VERIFIED_EXACT` hoặc
  `VERIFIED_BOUNDARY_BUFFER`)
- Không có bằng chứng rõ ràng về lỗi vị trí

**Hiển thị nhãn "vị trí tham khảo, chưa xác minh".** Không gọi marker này là vị trí
chính xác của căn nhà.

#### B. `DISTANCE_ANALYSIS_ELIGIBLE` — đủ căn cứ đo khoảng cách

Cần **tất cả**:

- Tọa độ hợp lệ
- **Nguồn gốc xác định được** (`coordinate_source` khác `UNKNOWN`)
- **Có căn cứ về độ chính xác hoặc sai số** (`accuracy_meters` có giá trị)
- Phương pháp đo phù hợp với loại geometry
- Kết quả kèm độ không chắc chắn

**Không cho phép chỉ dựa vào `VERIFIED_EXACT`.** Không cho phép suy `accuracy_meters`
từ số chữ số thập phân.

#### C. `PARCEL_ANALYSIS_ELIGIBLE` — đủ điều kiện phân tích cấp bất động sản

Cần **tất cả**:

- Provenance rõ
- Xác minh độc lập (thực địa hoặc đối chiếu địa chính)
- Độ chính xác đủ cho quyết định cấp bất động sản
- Geometry nguồn GIS được xác minh
- Kiểm tra mức sai số tương ứng

Nếu không có bằng chứng → `FALSE` hoặc `UNKNOWN`.

### E.2. Kết quả đo — bảng chỉ số (có thể giao nhau)

Các chỉ số dưới đây **không loại trừ nhau**. Không cộng chúng.

| Chỉ số | Số tin | Tiêu chí |
|---|---:|---|
| Geometry hợp lệ | **152** | `ST_IsValid`, SRID 4326, không `(0,0)`, không đảo trục |
| `REFERENCE_MAP_ELIGIBLE` | **151** | Hợp lệ + `VERIFIED_EXACT` (140) hoặc `VERIFIED_BOUNDARY_BUFFER` (11) |
| `NEEDS_LOCATION_REVIEW` | **1** | `SP013` — `INVALID_DISTRICT_MISMATCH` |
| `DEMO_OR_TEST` | **1** | `SP256` — tin test, ảnh `baseline.png` |
| Có provenance trực tiếp | **0** | Không có `coordinate_source` nào được ghi |
| Có sai số tọa độ được chứng minh | **0** | Không có `accuracy_meters` |
| `DISTANCE_ANALYSIS_ELIGIBLE` | **0** | Cần provenance + accuracy — không tin nào có |
| `PARCEL_ANALYSIS_ELIGIBLE` | **0** | Cần xác minh độc lập — không tin nào có |
| `LOCATION_ACCURACY_UNVERIFIED` | **152** | Tất cả — chưa có bằng chứng độ chính xác |

**`REFERENCE_MAP_ELIGIBLE = 151`, không phải 152.** Điều kiện chính thức là
`CoordinateStatus IN (VERIFIED_EXACT, VERIFIED_BOUNDARY_BUFFER)`:
`140 + 11 = 151`. `SP013` có `INVALID_DISTRICT_MISMATCH` nên **không** đạt.

**`SP256` nằm trong 151** vì có `VERIFIED_EXACT` — eligibility kỹ thuật của nó hợp lệ.
Nó **đồng thời** thuộc `DEMO_OR_TEST`. Hai nhãn độc lập, không trừ hai lần.

### E.3. Bảng phân nhóm loại trừ nhau — tổng = 152

Thứ tự ưu tiên: `DEMO_OR_TEST` → `NEEDS_LOCATION_REVIEW` → `REFERENCE_MAP_ONLY`.

| Nhóm | Số tin | Tiêu chí |
|---|---:|---|
| `DEMO_OR_TEST` | **1** | `SP256` — tin test, ảnh `baseline.png` |
| `NEEDS_LOCATION_REVIEW` | **1** | `SP013` — `INVALID_DISTRICT_MISMATCH` |
| `REFERENCE_MAP_ONLY` | **150** | `VERIFIED_EXACT`/`VERIFIED_BOUNDARY_BUFFER`, không demo, không review |
| **Tổng** | **152** | |

**Quan hệ giữa hai bảng:**

```text
REFERENCE_MAP_ELIGIBLE (151)
  = REFERENCE_MAP_ONLY (150) + DEMO_OR_TEST đạt điều kiện (1 = SP256)

152 tin
  = REFERENCE_MAP_ELIGIBLE (151) + NEEDS_LOCATION_REVIEW (1 = SP013)
  = REFERENCE_MAP_ONLY (150) + DEMO_OR_TEST (1) + NEEDS_LOCATION_REVIEW (1)
```

**`SP256` xuất hiện ở cả hai bảng** — trong bảng 1 với tư cách đạt điều kiện kỹ thuật,
trong bảng 2 với tư cách là dữ liệu demo. **Không trừ hai lần.**

**Không còn nhóm `UNSUITABLE_OR_UNKNOWN` dựa trên số chữ số thập phân.**

### E.4. Vì sao bỏ tiêu chí số chữ số thập phân

Báo cáo trước phân loại 88 tin là `UNSUITABLE_OR_UNKNOWN` chỉ vì tọa độ có ≤3 chữ số
thập phân. **Đó là suy luận sai:**

| Suy luận sai | Thực tế |
|---|---|
| "3 chữ số thập phân → sai 110 m" | Số chữ số là **độ phân giải biểu diễn**, không phải sai số |
| "Nhiều chữ số → chính xác" | Tọa độ 7 chữ số vẫn có thể sai hoàn toàn nếu ghim nhầm chỗ |
| "Ít chữ số → không dùng được" | Tọa độ 3 chữ số vẫn hiển thị marker tham khảo được |

**Tọa độ chưa được chứng minh chính xác không đồng nghĩa với tọa độ không thể sử dụng.**

Đánh dấu đúng là `LOCATION_ACCURACY_UNVERIFIED` — chưa có bằng chứng về độ chính xác,
không phải "không dùng được".

### E.5. Hai trường hợp ngoại lệ — xử lý riêng

#### `SP013` — `NEEDS_LOCATION_REVIEW`

| Trường hợp | Giá trị |
|---|---|
| `listing_code` | `SP013` |
| `CoordinateStatus` | **`INVALID_DISTRICT_MISMATCH`** |
| Quận khai báo | Liên Chiểu |
| Quận thực tế theo validator | **Hải Châu** |
| Mức lệch | **2 734 m** |
| Ghi chú validator | "ẩn ghim và không tính khoảng cách tiện ích cấp căn để tránh sai lệch vị trí" |

**Xử lý:**

- Đánh dấu `NEEDS_LOCATION_REVIEW`
- **Không** coi điểm đã được xác minh
- **Không** đưa vào phân tích khoảng cách đáng tin cậy
- **Không** đưa vào phân tích ngập cấp bất động sản
- **Không** sửa dữ liệu gốc (không đổi quận để ép validator PASS)

**Đây là lỗi dữ liệu cần người dùng đăng sửa**, không phải lỗi hệ thống. Validator đã
làm đúng: phát hiện và từ chối.

#### `SP256` — `DEMO_OR_TEST`

| Trường hợp | Giá trị |
|---|---|
| `listing_code` | `SP256` |
| Tiêu đề | "AutoScan local baseline" |
| `CoordinateStatus` | **`VERIFIED_EXACT`** (Hải Châu) |
| Ảnh | `baseline.png` (không theo quy ước batch) |
| Owner | `ADMIN` |

**Xử lý — hai nhãn độc lập:**

| Nhãn | Giá trị | Ý nghĩa |
|---|---|---|
| Eligibility kỹ thuật | **Đạt** — nằm trong 151 `REFERENCE_MAP_ELIGIBLE` | Tọa độ hợp lệ về mặt địa giới |
| Loại dữ liệu | **`DEMO_OR_TEST`** | Không phải bất động sản thật |

**Không trừ `SP256` hai lần.** Nó đạt điều kiện kỹ thuật của marker, nhưng **không được
dùng làm bằng chứng về vị trí bất động sản ngoài đời**.

**Không mặc định tin demo là bất động sản thật** chỉ vì tọa độ hợp lệ.

### E.6. Rủi ro cảnh báo ngập sai

| Rủi ro | Mức | Giải thích |
|---|---|---|
| Kết luận "nằm trong vùng ngập" từ tọa độ chưa xác minh | **Cao** | Không có `accuracy_meters` để đánh giá |
| Kết luận từ `VERIFIED_EXACT` | **Cao** | Enum gợi ý chính xác nhưng chỉ là cấp quận |
| Đo khoảng cách khi chưa có provenance | **Cao** | Sai số tọa độ + sai vị trí ngập cộng dồn, không định lượng được |
| Hiển thị marker tham khảo | **Thấp** | Chấp nhận được nếu có nhãn "vị trí tham khảo" |
| Dùng `SP256` làm bằng chứng vị trí | **Cao** | Tin demo, không phải bất động sản thật |
| Dùng `SP013` cho bất kỳ phân tích nào | **Cao** | Lệch 2 734 m so với quận khai báo |

**Không tính thử số tin thuộc vùng ngập** — chưa có polygon vùng ngập thực (xem PR #35).

### E.7. Baseline 10/152

Baseline **10/152 tin có bằng chứng cấp đường** vẫn đúng — khớp theo
`street + current_unit`, **không dùng tọa độ**. Kiểm toán này chứng minh **không thể
nâng 10 lên bằng tọa độ hiện có**.

---

## F. Thiết kế Coordinate Provenance V1

### F.1. Vấn đề cần giải quyết

Nếu chỉ lưu trạng thái xác minh trên `properties`, sẽ xảy ra lỗi:

```text
1. Tọa độ A được xác minh cấp thửa.
2. Người dùng đổi sang tọa độ B.
3. Hệ thống vẫn hiển thị "đã xác minh" cho B.
```

**Mỗi bản ghi audit phải gắn với một phiên bản tọa độ cụ thể.**

### F.2. Kiểm tra kiểu khóa và luồng hiện có

| Thành phần | Kiểu | Ghi chú |
|---|---|---|
| `properties.id` | `CHAR(36)` ascii_bin | UUID |
| `users.id` | `CHAR(36)` ascii_bin | UUID |
| Luồng create | `PropertyService` L53-57 | Tọa độ từ request, tạo POINT |
| Luồng update | `PropertyService` | Ghi đè `location` khi có lat/lon mới |
| Luồng publish | `status='PUBLISHED'` | Không tạo audit |
| Import | Không có script trong repo | UNKNOWN |
| Đổi tọa độ | Ghi đè trực tiếp | **Không có lịch sử** |
| Đổi địa chỉ giữ tọa độ | Không đồng bộ | **Không kiểm chứng được** |
| Admin xác minh | Không có chức năng | — |

### F.3. Schema đề xuất

```sql
CREATE TABLE property_coordinate_audit (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,

  -- Liên kết bất động sản
  property_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,

  -- Bản chụp tọa độ được kiểm toán (không phải tọa độ hiện tại)
  audited_latitude  DECIMAL(10,7) NOT NULL,
  audited_longitude DECIMAL(10,7) NOT NULL,
  -- Fingerprint để so khớp nhanh với tọa độ hiện tại
  coordinate_fingerprint CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,

  -- Nguồn gốc
  coordinate_source VARCHAR(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,

  -- Độ chính xác
  accuracy_level VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  accuracy_meters DECIMAL(8,2) DEFAULT NULL,

  -- Xác minh
  verification_method VARCHAR(40) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,
  verified_at DATETIME(6) DEFAULT NULL,
  verified_by CHAR(36) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,

  -- Kết quả địa lý (lưu lại thay vì tính runtime)
  geographic_validation_status VARCHAR(40) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,
  geographic_validation_note VARCHAR(500) DEFAULT NULL,

  -- Vòng đời
  created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  superseded_at DATETIME(6) DEFAULT NULL,

  CONSTRAINT fk_coord_audit_property FOREIGN KEY (property_id) REFERENCES properties(id),
  CONSTRAINT fk_coord_audit_verifier FOREIGN KEY (verified_by) REFERENCES users(id),
  CONSTRAINT ck_coord_source CHECK(coordinate_source IN (
    'USER_PINNED','GEOCODED','IMPORTED','ADMIN_DEFAULT','FIELD_VERIFIED','UNKNOWN')),
  CONSTRAINT ck_coord_accuracy CHECK(accuracy_level IN (
    'PARCEL','BUILDING','STREET','WARD','DISTRICT','CITY','UNKNOWN'))
);

CREATE INDEX idx_coord_audit_property ON property_coordinate_audit(property_id);
CREATE INDEX idx_coord_audit_current
  ON property_coordinate_audit(property_id, superseded_at);
CREATE INDEX idx_coord_audit_fingerprint
  ON property_coordinate_audit(coordinate_fingerprint);
```

### F.4. Cách xác định bản ghi hiện hành

```sql
-- Bản ghi audit còn hiệu lực cho một tin
SELECT * FROM property_coordinate_audit
WHERE property_id = ?
  AND superseded_at IS NULL
  AND coordinate_fingerprint = SHA2(CONCAT(
      CAST(ST_Latitude(p.location) AS CHAR),
      CAST(ST_Longitude(p.location) AS CHAR)), 256);
```

**Nếu fingerprint không khớp** → tọa độ đã đổi, audit cũ không còn áp dụng. Hệ thống
phải hiển thị `UNKNOWN` cho tọa độ mới, không kế thừa trạng thái cũ.

### F.5. Xử lý dữ liệu cũ — 152 tin

| Việc | Quyết định |
|---|---|
| Backfill `IMPORTED` | **Không** — không có provenance trực tiếp cho từng bản ghi |
| Backfill `PARCEL` | **Không** — không có xác minh thực địa |
| Suy `accuracy_meters` từ số chữ số | **Không** — số chữ số không phải sai số |
| Giá trị dùng | `coordinate_source='UNKNOWN'`, `accuracy_level='UNKNOWN'`, `accuracy_meters=NULL` |
| Sửa dữ liệu cũ | **Không** — lượt này chỉ thiết kế |

### F.6. Tác động tới hệ thống

| Thành phần | Tác động |
|---|---|
| API đăng tin | Thêm trường `coordinateSource` (tuỳ chọn) |
| API cập nhật tin | Ghi audit mới khi tọa độ đổi, đánh dấu `superseded_at` cho bản cũ |
| Import | Ghi `coordinate_source='IMPORTED'` |
| Geocoding | Nếu bật, ghi `GEOCODED` + `accuracy_meters` |
| Cloudinary, listing_code | **Không ảnh hưởng** |
| AI Advisor | Đọc `accuracy_level` để điều chỉnh ngôn ngữ |
| GIS | Dùng `accuracy_level` để quyết định mức bằng chứng |
| Migration | V26 mới, không sửa V3 |

### F.7. Dữ liệu cá nhân và lưu trữ

| Vấn đề | Xử lý |
|---|---|
| Lịch sử vị trí là dữ liệu cá nhân | Chỉ lưu tọa độ đã kiểm toán, không lưu lịch sử di chuyển |
| `verified_by` | Lưu UUID, không lưu tên |
| Thời gian lưu | Đề xuất 24 tháng, sau đó xoá bản `superseded_at` cũ |
| Quyền truy cập | Chỉ admin và chủ tin đọc được audit của tin mình |

### F.8. Test cần bổ sung

| Ca | Kỳ vọng |
|---|---|
| Tọa độ đúng quận nhưng sai địa chỉ | Không được `PARCEL` |
| Tọa độ đúng phường nhưng sai thửa | Không được `PARCEL` |
| Tọa độ geocode tại tâm đường | `accuracy_level='STREET'` |
| Tọa độ người dùng ghim chưa xác minh | `USER_PINNED` + `UNKNOWN` |
| Tọa độ nhập từ crawler | `IMPORTED` |
| Nhiều tin dùng chung vị trí | Cảnh báo, không tự sửa |
| Tọa độ đảo trục | `INVALID_SWAPPED_AXES` |
| Tọa độ ngoài Đà Nẵng | `OUTSIDE_DANANG_BOUNDS` |
| Tọa độ sát ranh giới | `ADMIN_DISTRICT_NEAR_BOUNDARY` |
| Tọa độ không có metadata | `UNKNOWN` |
| **Đổi tọa độ sau khi xác minh** | **Audit cũ `superseded_at`, tọa độ mới `UNKNOWN`** |

---

## G. Kết luận

### `NOT_READY_FOR_PARCEL_LEVEL_ANALYSIS`

| Chỉ số | Giá trị |
|---|---:|
| Tin có tọa độ hợp lệ kỹ thuật | 152/152 |
| Tin có bằng chứng xác minh cấp thửa | **0/152** |
| Tin có metadata nguồn gốc tọa độ | **0/152** |
| Tin do người dùng thật đăng | **0/152** (chưa tìm thấy bằng chứng) |
| Tin nạp hàng loạt (`STRONGLY_INFERRED`) | 151/152 |
| Tin test/demo | 1/152 |
| Tin `VERIFIED_EXACT` (chỉ cấp quận) | 140/152 |
| Tin có độ phân giải ≤3 chữ số | 98/152 |
| Tin đủ dùng cho marker tham khảo | **151/152** |
| Tin cần review địa giới | **1/152** (`SP013`) |
| Tin đủ điều kiện đo khoảng cách | **0/152** |
| Tin đủ điều kiện phân tích cấp thửa | **0/152** |

**Ba lý do không đủ điều kiện:**

1. **Không có provenance.** Không cột nào, không audit log nào ghi tọa độ từ đâu.
2. **`VERIFIED_EXACT` không phải cấp thửa.** Nó chỉ kiểm tra điểm nằm trong polygon quận.
3. **Không có dữ liệu địa chính.** Không ranh giới thửa, không số nhà, không xác minh
   thực địa.

**Điều kết luận này KHÔNG nói:** không khẳng định cả 152 tọa độ đều sai. Nhiều điểm có
thể đúng thực tế — chỉ là **chưa có bằng chứng** để chứng minh.

### Điều kiện chuyển sang `PARTIALLY_READY_NEEDS_PROVENANCE`

- [ ] Thêm bảng `property_coordinate_audit`
- [ ] Ghi `coordinate_source` khi tạo/cập nhật tin
- [ ] Backfill 152 tin thành `UNKNOWN`
- [ ] Đổi tên enum theo kế hoạch tương thích ngược (mục D.6)
- [ ] Có ≥10 tin xác minh thực địa hoặc đối chiếu địa chính

### Điều kiện chuyển sang `COORDINATE_DATA_READY_FOR_SPATIAL_ANALYSIS`

- [ ] Tất cả điều kiện trên
- [ ] Có polygon vùng nguy cơ ngập từ nguồn có thẩm quyền (xem PR #35)
- [ ] Có ≥50% tin đạt `accuracy_level IN ('PARCEL','BUILDING')`

---

## Phụ lục — Truy vấn và harness tái hiện

Tất cả **chỉ đọc**. Chạy trên `3306/smartprop`.

```sql
-- 1. Chênh lệch 153 vs 152
SELECT COUNT(*) FROM properties;                          -- 153
SELECT COUNT(*) FROM properties WHERE status='PUBLISHED'; -- 152
SELECT listing_code, status, title FROM properties WHERE status='DRAFT';
-- -> SP257 | DRAFT | AutoScan local duplicate

-- 2. Bằng chứng nạp hàng loạt qua tên ảnh
SELECT original_filename, COUNT(*) FROM property_images
GROUP BY original_filename HAVING original_filename LIKE 'batch_%';
-- -> 81 ảnh, 6 lô

SELECT storage_provider, COUNT(*) FROM property_images GROUP BY storage_provider;
-- -> LOCAL | 173

SELECT COUNT(*) FROM property_images WHERE cloudinary_secure_url IS NOT NULL;
-- -> 0

-- 3. Một owner
SELECT owner_id, COUNT(*) c FROM properties
WHERE status='PUBLISHED' GROUP BY owner_id ORDER BY c DESC;
-- -> 151 tin một owner, 1 tin owner khác

-- 4. Không có metadata tọa độ
SELECT COLUMN_NAME FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA='smartprop' AND TABLE_NAME='properties'
  AND (COLUMN_NAME LIKE '%coord%' OR COLUMN_NAME LIKE '%accuracy%');
-- -> 0 dòng
```

**Harness Java:** `backend/src/test/java/vn/smartprop/gis/CoordinateAuditHarness.java`

```bash
# Xuất TSV: listing_code, district, ward, city, lat, lon
# Chạy:
java -cp <classpath> vn.smartprop.gis.CoordinateAuditHarness \
  audit-input.tsv harness-out.txt harness-summary.txt
```

**Script kiểm toán** chỉ chạy `SELECT`, không ghi dữ liệu, không log PII. Nằm ngoài
repository (`.scratch/`), không commit.

---

**Tài liệu liên quan**

- [PR #35 — GIS V2 research](https://github.com/manchae19/SmartProp/pull/35)
- `docs/SMARTPROP_GIS_V2_RESEARCH_AND_READINESS.md`
- `backend/src/main/java/vn/smartprop/gis/DanangSpatialValidator.java`
- `backend/src/main/java/vn/smartprop/gis/DanangAdminNormalizer.java`
- `backend/src/main/java/vn/smartprop/modules/property/PropertyService.java`
- `frontend/src/features/map/ManualLocationMap.jsx`
- `database/migrations/V3__properties_images_and_spatial.sql`
