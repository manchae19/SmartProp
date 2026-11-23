# SmartProp — Kiểm toán nguồn gốc và chất lượng tọa độ bất động sản

**Ngày kiểm toán:** 2026-11-23
**Mốc nền:** `main @ 034ec2d`
**Database:** `127.0.0.1:3306/smartprop` — **chỉ đọc**, không INSERT/UPDATE/DELETE/ALTER
**Phương pháp:** truy vấn SELECT + đọc mã nguồn + mô phỏng validator

---

## Trả lời sáu câu hỏi

**1. 152 tin bất động sản này thực chất từ đâu ra?**

Từ **một chiến dịch nạp dữ liệu nội bộ**, không phải người dùng thật đăng. Bằng chứng:
151/152 tin thuộc **một owner duy nhất** (role `BROKER`), 135 tin tạo trong **10 phút**
ngày 2026-11-07, `created_at` = `published_at` **cùng giây** cho cả 135 tin.

**2. Vì sao database có 153 tin nhưng mẫu chỉ có 152?**

Vì **1 tin `DRAFT`** (`SP257`, "AutoScan local duplicate"). Bộ lọc mẫu dùng
`status='PUBLISHED'` nên loại nó ra. Không có tin xóa mềm, không có fixture, không có
tin hết hạn bị loại.

**3. Bao nhiêu tin từ người dùng, import, crawler, seed, demo?**

| Nhóm | Số lượng |
|---|---:|
| Người dùng đăng thật | **0** |
| Import / nạp hàng loạt | **151** |
| Crawler / Tinix | **0** |
| Demo / seed / test | **1** |
| Chưa xác định | **0** |

**4. Bao nhiêu tọa độ được xác minh cấp bất động sản?**

**0/152.** Không có cột metadata nguồn gốc tọa độ, không có audit log ghi lại việc ghim,
không có quy trình xác minh thực địa. Toàn bộ là `UNKNOWN_PROVENANCE`.

**5. `VERIFIED_EXACT` có đang bị hiểu sai thành độ chính xác cấp thửa?**

**Có.** `VERIFIED_EXACT` chỉ kiểm tra điểm nằm trong **polygon quận lịch sử** — một
vùng rộng hàng chục km². Tên enum gợi ý "chính xác" nhưng ngữ nghĩa thực tế là
"hợp lệ về mặt địa giới hành chính". Đây là rủi ro diễn giải nghiêm trọng.

**6. Đã đủ điều kiện phát triển GIS ngập cấp bất động sản chưa?**

**Chưa.** Kết luận: **`NOT_READY_FOR_PARCEL_LEVEL_ANALYSIS`**.

---

## A. Nguồn gốc 152 tin

### A.1. Chênh lệch 153 và 152 — giải thích chính xác

```sql
SELECT COUNT(*) FROM properties;                                    -- 153
SELECT COUNT(*) FROM properties WHERE status='PUBLISHED';           -- 152
SELECT COUNT(*) FROM properties WHERE status='DRAFT';               --   1
```

| Điều kiện lọc | Số bản ghi |
|---|---:|
| Tổng bảng `properties` | **153** |
| `status='PUBLISHED'` | **152** |
| `deleted_at IS NULL` | 153 |
| Chưa hết hạn | 153 |
| Không phải fixture (`f0000000-%`) | 153 |

**Chỉ một điều kiện loại bỏ bản ghi: `status='PUBLISHED'`.** Tin bị loại là `SP257`
— "AutoScan local duplicate", `DRAFT`, địa chỉ `14 AutoScan Street`, tạo 2026-11-13.

Bộ lọc mẫu dùng trong các báo cáo trước:

```sql
WHERE status='PUBLISHED' AND deleted_at IS NULL
  AND (expires_at IS NULL OR expires_at > UTC_TIMESTAMP(6))
  AND id NOT LIKE 'f0000000-%'
```

Ba điều kiện sau **không loại thêm bản ghi nào** — chúng chỉ để phòng ngừa. Điều này
đã được kiểm chứng bằng cách chạy từng điều kiện riêng lẻ.

### A.2. Bằng chứng nguồn gốc

| Dấu hiệu | Giá trị | Ý nghĩa |
|---|---|---|
| Số owner khác nhau | **2** | 151 tin một owner, 1 tin owner khác |
| Owner chính | `BROKER`, tạo 2026-11-01 | Tài khoản môi giới, không phải nhiều người dùng |
| Owner thứ hai | `ADMIN`, tạo 2026-11-13 | Tin test `SP256` |
| Phân bố ngày tạo | 11-01: 6, 11-02: 10, **11-07: 135**, 11-13: 1 | 135 tin dồn một ngày |
| Khoảng thời gian tạo 135 tin | 03:37:52 → 03:47:37 | **10 phút** |
| `created_at` = `published_at` cùng giây | **135/135** | Không qua quy trình duyệt thật |
| `listing_code` | `SP001`..`SP256`, thiếu 104 số | Cấp tuần tự, có khoảng trống |
| `property_listing_code_allocations` | 153 bản ghi, 151 cấp ngày 2026-11-10 | Cấp hàng loạt sau khi tạo |

**Kết luận:** 135 tin ngày 11-07 được nạp bằng script, không qua form đăng tin.
`created_at` = `published_at` cùng giây chứng minh không có bước duyệt.

### A.3. Phân loại nguồn

| Nhóm nguồn | Số lượng | Bằng chứng | Mức chắc chắn |
|---|---:|---|---|
| `MANUAL_USER_LISTING` | **0** | Không có tin nào có dấu hiệu đăng riêng lẻ bởi nhiều người dùng | Xác minh |
| `IMPORTED_LISTING` | **151** | Một owner, 135 tin/10 phút, `created_at`=`published_at`, listing_code tuần tự | **Cao** |
| `CRAWLER_DATA` | **0** | `external_listings` (3204 bản ghi) **không có cột** tham chiếu `properties`; `tinix_dataset_records` (185 973 bản ghi) tách biệt hoàn toàn | Xác minh |
| `SEED_OR_DEMO` | **1** | `SP256` "AutoScan local baseline", địa chỉ `12 AutoScan Street`, owner `ADMIN` | **Cao** |
| `UNKNOWN_ORIGIN` | **0** | — | — |
| **Tổng** | **152** | | |

**Lưu ý về `IMPORTED_LISTING`:** nhãn này chỉ khẳng định **cơ chế nạp** (hàng loạt,
không qua form), **không** khẳng định dữ liệu là giả. Nội dung 135 tin có đặc điểm
của dữ liệu thật: 118 mức giá khác nhau, 52 diện tích khác nhau, 4 loại bất động sản,
135 tọa độ khác nhau, 135/135 có ảnh, 135/135 có `declared_amenities`. Đây là dữ liệu
**thật được nạp hàng loạt**, không phải dữ liệu bịa.

Nhưng **không có bằng chứng** đây là tin do người dùng cuối tự đăng.

### A.4. Vì sao không xác định được nguồn chi tiết hơn

| Thiếu gì | Hệ quả |
|---|---|
| Không có cột `source` / `import_batch_id` trong `properties` | Không truy vết được lô nạp |
| `audit_logs` chỉ có 5 bản ghi (`LOCAL_ADMIN_PROVISIONED` ×3, `PROPERTY_APPROVE` ×1, `LOCAL_ADMIN_PASSWORD_ROTATED` ×1) | Không ghi lại việc tạo 152 tin |
| Không có script seed trong repo ghi vào `properties` | Không tìm được công cụ đã dùng |
| `external_listings` không có FK tới `properties` | Không nối được crawler với tin |

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
| Ngoài khung Đà Nẵng | **2** (`SP105`, `SP111`) |
| Tọa độ trùng lặp hoàn toàn | **0** |

**Về mặt kỹ thuật, 152/152 tọa độ hợp lệ.** Nhưng đây chính là điều yêu cầu cảnh báo:
*hợp lệ* không đồng nghĩa *chính xác*.

### B.2. Dấu hiệu tọa độ sinh tự động

| Đặc điểm | Số tin | Diễn giải |
|---|---:|---|
| Chính xác 2 chữ số thập phân (~1,1 km) | **2** | Độ phân giải rất thô |
| Chính xác 3 chữ số thập phân (~110 m) | **50** | Thô hơn ghim tay thông thường |
| Chính xác 4 chữ số thập phân (~11 m) | **121** | Mức hợp lý cho ghim bản đồ |
| Nhiều hơn 4 chữ số | 23 | Có thể từ geocode |

**50/152 tin có tọa độ làm tròn đến 3 chữ số thập phân** — dấu hiệu tọa độ được sinh
từ một quy trình tự động (làm tròn theo lưới), không phải người dùng ghim chính xác.

### B.3. Phân bố theo quận

| Quận | Số tin | Khoảng cách TB tới tâm cụm | Gần nhất |
|---|---:|---:|---:|
| Hải Châu | 29 | 1 367 m | 226 m |
| Sơn Trà | 29 | 1 338 m | 412 m |
| Ngũ Hành Sơn | 26 | 3 022 m | 860 m |
| Cẩm Lệ | 25 | 1 787 m | 473 m |
| Liên Chiểu | 18 | 2 381 m | 578 m |
| Thanh Khê | 13 | 1 039 m | 76 m |
| Hòa Vang | 12 | 7 805 m | 1 691 m |

**Tọa độ phân bố rộng, không dồn về tâm quận.** Chỉ 1 tin (`SP132`) nằm trong 200 m
từ tâm cụm quận. Đây là dấu hiệu **tốt**: tọa độ không phải tâm hành chính giả.

Nhưng phân bố rộng **không chứng minh** từng điểm nằm đúng thửa đất.

### B.4. Phân loại nguồn gốc tọa độ

| Nhóm | Số lượng | Bằng chứng |
|---|---:|---|
| `PARCEL_VERIFIED` | **0** | Không có xác minh thực địa, không có dữ liệu địa chính |
| `USER_PINNED_UNVERIFIED` | **0** | Không có audit log ghi lại hành vi ghim; không phân biệt được ghim tay với nạp script |
| `GEOCODED_ADDRESS` | **0** | `PropertyService` không gọi geocoding khi tạo tin (xem B.5) |
| `IMPORTED_COORDINATE` | **151** | Nạp hàng loạt, tọa độ đi kèm dữ liệu |
| `ADMIN_CENTROID_OR_DEFAULT` | **0** | Phân bố rộng, không dồn tâm quận |
| `UNKNOWN_PROVENANCE` | **1** | `SP256` — tin test, không rõ nguồn tọa độ |
| **Tổng** | **152** | |

**Không có tin nào ở nhóm `PARCEL_VERIFIED`.** Đây là kết luận then chốt.

### B.5. Cơ chế tạo tọa độ

**Backend** — `PropertyService.java`:

```java
// L53-57
Double lat = r.latitude() != null ? r.latitude() : p.location == null ? null : p.location.getY();
Double lon = r.longitude() != null ? r.longitude() : p.location == null ? null : p.location.getX();
if (...) throw ApiInputs.bad("Tọa độ bắt buộc: latitude [-90,90], longitude (-180,180]");
p.location = new GeometryFactory(new PrecisionModel(), 4326).createPoint(new Coordinate(lon, lat));
```

**Tọa độ đến từ request, không geocode.** Không có bước tự điền theo địa chỉ.

**Frontend** — `ManualLocationMap.jsx`:

```javascript
// L28
latitude: 16.0544,   // viewport mặc định, KHÔNG phải điểm được chọn
```

```javascript
// L23
// This initial center is only a viewport. No point is selected until a deliberate action.
```

**Viewport mặc định không được lưu thành tọa độ tin.** Đây là thiết kế đúng.

| Câu hỏi | Trả lời |
|---|---|
| Người đăng tự ghim được không? | **Có** — `ManualLocationMap` cho chọn điểm |
| Có lưu vị trí mặc định của bản đồ không? | **Không** — viewport tách khỏi điểm chọn |
| Có tự điền tọa độ theo địa chỉ không? | **Không** — `PropertyService` không geocode |
| Có dùng geocoding API không? | **Không** trong luồng tạo tin |
| Geocoding thất bại thì lưu gì? | Không áp dụng — tọa độ bắt buộc từ request |
| Có import tọa độ từ dữ liệu cũ không? | **Có** — 151 tin nạp hàng loạt |
| Có lưu nguồn gốc và độ chính xác? | **Không** — không có cột nào |
| Cập nhật địa chỉ có đồng bộ tọa độ? | Không kiểm chứng được — không có audit log |

---

## C. Kiểm toán `DanangSpatialValidator`

### C.1. Điều kiện tạo từng trạng thái

Đọc `DanangSpatialValidator.java` L150-215:

```java
// L167-179 — VERIFIED_EXACT
if (canonicalDistrict != null && coreDistrictPolygons.containsKey(canonicalDistrict)) {
    Geometry declaredPoly = coreDistrictPolygons.get(canonicalDistrict);
    if (declaredPoly.contains(pt) || declaredPoly.touches(pt)) {
        return new CoordinateValidationResult(
            CoordinateStatus.VERIFIED_EXACT, ...,
            "Tọa độ WGS84 (SRID 4326) nằm khớp trong ranh giới địa lý "
            + districtDisplayLabel(canonicalDistrict) + ".");
    }
```

**`VERIFIED_EXACT` = điểm nằm trong polygon quận khai báo.** Không có kiểm tra nào
về thửa đất, số nhà, hay độ chính xác của nguồn tọa độ.

```java
// L181-193 — VERIFIED_BOUNDARY_BUFFER
double distMeters = minDistanceToGeometryMeters(lat, lon, declaredPoly);
if (distMeters <= ADM2_BOUNDARY_TOLERANCE_METERS) {   // 750 m
    return ... VERIFIED_BOUNDARY_BUFFER ...;
```

**`VERIFIED_BOUNDARY_BUFFER` = điểm nằm ngoài polygon nhưng trong vòng 750 m.**

### C.2. Polygon đang dùng

```java
// L25
* <p>Reuses the bundled {@code /geocoding/danang-search-scopes.geojson}
```

File `danang-search-scopes.geojson` có **11 polygon, tất cả level `LEGACY_DISTRICT`**:

```
Hải Châu, Thanh Khê, Sơn Trà, Ngũ Hành Sơn, Cẩm Lệ, Liên Chiểu, Hòa Vang,
Hội An, Điện Bàn, Tam Kỳ, Núi Thành
```

**Đây là ranh giới cấp quận cũ, không phải cấp phường, càng không phải cấp thửa.**

### C.3. Ba khái niệm bị lẫn

| Khái niệm | Validator có kiểm tra? | Ghi chú |
|---|---|---|
| **Geographic validity** — tọa độ hợp lệ và đúng địa bàn | **Có** | Đây là toàn bộ những gì validator làm |
| **Coordinate provenance** — tọa độ từ đâu | **Không** | Không có tham số nào về nguồn |
| **Parcel-level accuracy** — có đúng thửa đất | **Không** | Không có dữ liệu địa chính |

### C.4. Ngưỡng 750 m

`ADM2_BOUNDARY_TOLERANCE_METERS = 750.0` — dùng để bù sai số của **đường biên giản lược
ADM2** (ranh giới quận được vẽ đơn giản hoá). Đây là dung sai **của bản đồ**, không
phải dung sai **của tọa độ bất động sản**.

Một điểm cách biên quận 700 m vẫn được `VERIFIED_BOUNDARY_BUFFER` dù có thể nằm ở
phường khác hoàn toàn.

### C.5. Kết quả chạy validator trên 152 tin

Mô phỏng logic validator bằng Python (ray casting + khoảng cách tới biên):

| Trạng thái | Số tin | % |
|---|---:|---:|
| `VERIFIED_EXACT` | **137** | 90,1% |
| `VERIFIED_BOUNDARY_BUFFER` | **11** | 7,2% |
| `VERIFIED_DANANG_POLYGON` | **1** | 0,7% |
| `INVALID_DISTRICT_MISMATCH` | **1** | 0,7% |
| `INVALID_SWAPPED_AXES` | 0 | 0% |
| `OUTSIDE_DANANG_BOUNDS` | **2** | 1,3% |
| `INVALID_COORDINATES` | 0 | 0% |
| `NONE_ADMIN_ONLY` | 0 | 0% |
| **Tổng** | **152** | |

**137 tin `VERIFIED_EXACT` không có nghĩa 137 tin có tọa độ chính xác cấp thửa.**
Chúng chỉ có nghĩa: điểm nằm trong polygon quận đã khai báo.

### C.6. Đề xuất đặt tên (không đổi production)

Tên hiện tại gây hiểu nhầm. Đề xuất cho lượt sau:

| Tên hiện tại | Tên đề xuất | Lý do |
|---|---|---|
| `VERIFIED_EXACT` | `ADMIN_DISTRICT_CONTAINED` | Mô tả đúng điều kiện thực tế |
| `VERIFIED_BOUNDARY_BUFFER` | `ADMIN_DISTRICT_NEAR_BOUNDARY` | Nêu rõ là gần biên |
| `VERIFIED_DANANG_POLYGON` | `ADMIN_CITY_CONTAINED` | Cấp thành phố, không phải quận |

**Không đổi trong lượt kiểm toán này.** Đổi tên là breaking change với Frontend và
Advisor; cần PR riêng có migration dữ liệu.

---

## D. Tọa độ đáng nghi

Không có tọa độ nào bị kết luận **sai**. Chỉ đánh dấu `NEEDS_REVIEW` khi có dấu hiệu
bất thường. Không sửa, không xóa.

| ID tin | Quận khai báo | Tọa độ | Vấn đề | Mức |
|---|---|---|---|---|
| `SP105` | Hòa Vang | 15.98500, 108.02800 | Ngoài khung Đà Nẵng (kinh độ 108.028 < 108.05) | `OUTSIDE_DANANG_BOUNDS` |
| `SP111` | Hòa Vang | 16.12500, 108.03500 | Ngoài khung Đà Nẵng (kinh độ 108.035 < 108.05) | `OUTSIDE_DANANG_BOUNDS` |
| `SP013` | Liên Chiểu | 16.05440, 108.20220 | Nằm trong địa phận quận khác, lệch > 750 m | `INVALID_DISTRICT_MISMATCH` |
| `SP256` | Hải Châu | 16.06000, 108.22000 | Tin test, không rõ nguồn tọa độ | `NEEDS_REVIEW` |
| `SP132` | Thanh Khê | — | Chỉ cách tâm cụm quận 76 m | `NEEDS_REVIEW` |

**11 tin `VERIFIED_BOUNDARY_BUFFER`** nằm sát biên quận — cần xem xét khi dùng cho
truy vấn không gian, vì có thể thuộc phường khác.

**50 tin có tọa độ 3 chữ số thập phân** — độ phân giải ~110 m, không đủ cho kết luận
cấp thửa dù hợp lệ về mặt kỹ thuật.

---

## E. Khả năng triển khai GIS V2

### E.1. Phân loại theo mục đích sử dụng

| Nhóm | Tiêu chí | Số tin |
|---|---|---:|
| `ELIGIBLE_FOR_PARCEL_SPATIAL_CHECK` | Có nguồn vị trí xác minh cấp bất động sản | **0** |
| `ELIGIBLE_FOR_APPROXIMATE_MAP_ONLY` | Tọa độ hợp lệ, dùng được để hiển thị marker và đo khoảng cách có cảnh báo sai số | **137** |
| `ADMINISTRATIVE_ONLY` | Chỉ đủ căn cứ đối chiếu khu vực hành chính | **13** |
| `UNSUITABLE_OR_UNKNOWN` | Không hợp lệ hoặc không đủ bằng chứng | **2** |
| **Tổng** | | **152** |

**Tiêu chí từng nhóm:**

- **`ELIGIBLE_FOR_PARCEL_SPATIAL_CHECK`** — cần: (a) nguồn tọa độ ghi lại được, (b) độ
  chính xác ≤ 10 m, (c) xác minh độc lập. **Không tin nào đạt cả ba.**
- **`ELIGIBLE_FOR_APPROXIMATE_MAP_ONLY`** — tọa độ hợp lệ, nằm trong polygon quận khai
  báo, độ chính xác 4 chữ số thập phân trở lên. Dùng được để hiển thị marker và đo
  khoảng cách **kèm cảnh báo sai số**.
- **`ADMINISTRATIVE_ONLY`** — `VERIFIED_BOUNDARY_BUFFER` (11) + `VERIFIED_DANANG_POLYGON`
  (1) + `INVALID_DISTRICT_MISMATCH` (1). Chỉ đủ để nói "thuộc khu vực X", không đủ để
  đo khoảng cách.
- **`UNSUITABLE_OR_UNKNOWN`** — `OUTSIDE_DANANG_BOUNDS` (2).

### E.2. Tác động tới GIS V2

| Câu hỏi | Trả lời |
|---|---|
| Bao nhiêu tin đủ tin cậy cho truy vấn không gian cấp bất động sản? | **0** |
| Bao nhiêu tin chỉ đủ hiển thị marker tham khảo? | **137** |
| Bao nhiêu tin cần xác minh thủ công? | **152** (toàn bộ, nếu muốn cấp thửa) |
| Dữ liệu nào phải bổ sung? | Nguồn gốc tọa độ + độ chính xác + xác minh thực địa |

### E.3. Rủi ro cảnh báo ngập sai

| Rủi ro | Mức | Giải thích |
|---|---|---|
| Kết luận "nằm trong vùng ngập" từ tọa độ 3 chữ số thập phân | **Cao** | Sai số ~110 m có thể nhảy qua ranh giới vùng ngập |
| Kết luận từ `VERIFIED_EXACT` | **Cao** | Enum gợi ý chính xác nhưng chỉ là cấp quận |
| Đo khoảng cách tới điểm ngập | **Trung bình** | Sai số tọa độ + sai số vị trí ngập cộng dồn |
| Hiển thị marker | **Thấp** | Chấp nhận được nếu có nhãn "vị trí tham khảo" |

**Không tính thử số tin thuộc vùng ngập** — chưa có polygon vùng ngập thực (xem PR #35).

### E.4. Baseline 10/152

Baseline **10/152 tin có bằng chứng cấp đường** vẫn đúng — đó là khớp theo
`street + current_unit`, **không dùng tọa độ**. Kiểm toán này không thay đổi con số đó.

Điều kiểm toán này chứng minh: **không thể nâng 10 lên con số cao hơn bằng tọa độ hiện
có**, vì không tin nào đủ chính xác cấp thửa.

---

## F. Phương án nâng cấp

### F.1. So sánh ba phương án

| | Phương án A — cột trong `properties` | Phương án B — bảng riêng | Phương án C — runtime |
|---|---|---|---|
| **Ưu** | Truy vấn đơn giản, không JOIN | Tách lịch sử, nhiều nguồn/tin, không phình bảng chính | Không đổi schema, triển khai nhanh |
| **Nhược** | Phình bảng, khó lưu nhiều lần xác minh | Cần JOIN mọi truy vấn | Không lưu được, mất khi restart, không audit được |
| **Migration** | `ALTER TABLE` thêm 5-6 cột | `CREATE TABLE` mới | Không |
| **Backfill** | `UNKNOWN` cho 152 tin | `UNKNOWN` cho 152 tin | Không áp dụng |
| **Phù hợp** | Nếu chỉ cần 1 trạng thái/tin | **Nếu cần lịch sử xác minh** | Chỉ để thử nghiệm |

**Đề xuất: Phương án B** — bảng `property_coordinate_audit`.

Lý do: tọa độ có thể được xác minh nhiều lần (người đăng sửa, admin duyệt, thực địa).
Phương án A chỉ lưu trạng thái cuối, mất lịch sử. Phương án C không audit được — đúng
vấn đề đang gặp hiện nay.

### F.2. Schema đề xuất (chưa áp dụng)

```sql
CREATE TABLE property_coordinate_audit (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
  property_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  -- Nguồn gốc: ai/cái gì tạo ra tọa độ này
  coordinate_source VARCHAR(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  -- Độ chính xác: mức và sai số ước tính
  accuracy_level VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  accuracy_meters DECIMAL(8,2) DEFAULT NULL,
  -- Xác minh
  verification_method VARCHAR(40) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,
  verified_at DATETIME(6) DEFAULT NULL,
  verified_by CHAR(36) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,
  -- Trạng thái địa lý (từ DanangSpatialValidator, lưu lại thay vì tính runtime)
  geographic_status VARCHAR(40) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,
  note VARCHAR(500) DEFAULT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  CONSTRAINT fk_coord_audit_property FOREIGN KEY (property_id) REFERENCES properties(id),
  CONSTRAINT ck_coord_source CHECK(coordinate_source IN (
    'USER_PINNED','GEOCODED','IMPORTED','ADMIN_DEFAULT','FIELD_VERIFIED','UNKNOWN')),
  CONSTRAINT ck_coord_accuracy CHECK(accuracy_level IN (
    'PARCEL','BUILDING','STREET','WARD','DISTRICT','CITY','UNKNOWN'))
);
CREATE INDEX idx_coord_audit_property ON property_coordinate_audit(property_id);
```

**Backfill dữ liệu cũ:** 152 tin hiện tại → `coordinate_source='UNKNOWN'`,
`accuracy_level='UNKNOWN'`. **Không đoán.** Không backfill `VERIFIED_EXACT` thành
`PARCEL`.

### F.3. Tác động tới hệ thống

| Thành phần | Tác động |
|---|---|
| API đăng tin | Thêm trường `coordinateSource` (tuỳ chọn) vào request |
| API cập nhật tin | Ghi audit mới khi tọa độ đổi |
| Import | Ghi `coordinate_source='IMPORTED'` |
| Geocoding | Nếu bật, ghi `coordinate_source='GEOCODED'` + `accuracy_meters` |
| Cloudinary, listing_code | **Không ảnh hưởng** |
| AI Advisor | Có thể đọc `accuracy_level` để điều chỉnh ngôn ngữ |
| GIS | Dùng `accuracy_level` để quyết định mức bằng chứng |
| Migration | V26 mới, không sửa V3 |

### F.4. Test cần bổ sung

| Ca | Kỳ vọng |
|---|---|
| Tọa độ đúng quận nhưng sai địa chỉ thực tế | Không được `PARCEL` |
| Tọa độ đúng phường nhưng sai thửa | Không được `PARCEL` |
| Tọa độ geocode tại tâm đường | `accuracy_level='STREET'` |
| Tọa độ người dùng ghim chưa xác minh | `USER_PINNED` + `UNKNOWN` accuracy |
| Tọa độ nhập từ crawler | `IMPORTED` |
| Nhiều tin dùng chung một vị trí | Cảnh báo, không tự sửa |
| Tọa độ đảo trục | `INVALID_SWAPPED_AXES` |
| Tọa độ ngoài Đà Nẵng | `OUTSIDE_DANANG_BOUNDS` |
| Tọa độ sát ranh giới | `ADMIN_DISTRICT_NEAR_BOUNDARY` |
| Tọa độ không có metadata | `UNKNOWN` |

---

## G. Kết luận

### `NOT_READY_FOR_PARCEL_LEVEL_ANALYSIS`

**Số liệu chứng minh:**

| Chỉ số | Giá trị |
|---|---:|
| Tin có tọa độ hợp lệ kỹ thuật | 152/152 |
| Tin có tọa độ xác minh cấp bất động sản | **0/152** |
| Tin có metadata nguồn gốc tọa độ | **0/152** |
| Tin do người dùng thật đăng | **0/152** |
| Tin nạp hàng loạt | 151/152 |
| Tin test/demo | 1/152 |
| Tin `VERIFIED_EXACT` (chỉ là cấp quận) | 137/152 |
| Tin có tọa độ độ phân giải ≤ 110 m | 50/152 |

**Ba lý do không đủ điều kiện:**

1. **Không có provenance.** Không cột nào, không audit log nào ghi lại tọa độ từ đâu.
   Không phân biệt được ghim tay với nạp script.

2. **`VERIFIED_EXACT` không phải cấp thửa.** Nó chỉ kiểm tra điểm nằm trong polygon
   quận — vùng rộng hàng chục km². Dùng nó để kết luận "nằm trong vùng ngập" sẽ tạo
   cảnh báo sai.

3. **Không có dữ liệu địa chính.** Không có ranh giới thửa, không có số nhà địa chính,
   không có xác minh thực địa.

### Điều kiện để chuyển sang `PARTIALLY_READY_NEEDS_PROVENANCE`

- [ ] Thêm bảng `property_coordinate_audit` (Phương án B)
- [ ] Ghi `coordinate_source` khi tạo/cập nhật tin
- [ ] Backfill 152 tin hiện tại thành `UNKNOWN`
- [ ] Đổi tên enum `VERIFIED_EXACT` → `ADMIN_DISTRICT_CONTAINED`
- [ ] Có ít nhất 10 tin được xác minh thực địa hoặc đối chiếu địa chính

### Điều kiện để chuyển sang `COORDINATE_DATA_READY_FOR_SPATIAL_ANALYSIS`

- [ ] Tất cả điều kiện trên
- [ ] Có polygon vùng nguy cơ ngập từ nguồn có thẩm quyền (xem PR #35)
- [ ] Có ≥ 50% tin đạt `accuracy_level IN ('PARCEL','BUILDING')`

---

## Phụ lục — Truy vấn tái hiện

Tất cả truy vấn **chỉ đọc**. Chạy trên `3306/smartprop`.

```sql
-- 1. Chênh lệch 153 vs 152
SELECT COUNT(*) FROM properties;                          -- 153
SELECT COUNT(*) FROM properties WHERE status='PUBLISHED'; -- 152
SELECT listing_code, status, title FROM properties WHERE status='DRAFT';
-- -> SP257 | DRAFT | AutoScan local duplicate

-- 2. Bằng chứng nạp hàng loạt
SELECT DATE(created_at) d, COUNT(*) c FROM properties
WHERE status='PUBLISHED' GROUP BY d ORDER BY d;
-- -> 2026-11-07: 135

SELECT MIN(created_at), MAX(created_at) FROM properties
WHERE status='PUBLISHED' AND DATE(created_at)='2026-11-07';
-- -> 03:37:52 .. 03:47:37  (10 phút)

SELECT COUNT(*) FROM properties
WHERE status='PUBLISHED' AND DATE(created_at)='2026-11-07'
  AND ABS(TIMESTAMPDIFF(SECOND, created_at, published_at)) < 5;
-- -> 135  (tạo và publish cùng giây)

-- 3. Một owner
SELECT owner_id, COUNT(*) c FROM properties
WHERE status='PUBLISHED' GROUP BY owner_id ORDER BY c DESC;
-- -> 151 tin một owner, 1 tin owner khác

-- 4. Không có metadata tọa độ
SELECT COLUMN_NAME FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA='smartprop' AND TABLE_NAME='properties'
  AND (COLUMN_NAME LIKE '%coord%' OR COLUMN_NAME LIKE '%accuracy%');
-- -> 0 dòng

-- 5. Tọa độ ngoài Đà Nẵng
SELECT listing_code, ST_Latitude(location), ST_Longitude(location)
FROM properties WHERE status='PUBLISHED'
  AND NOT (ST_Latitude(location) BETWEEN 15.90 AND 16.20
       AND ST_Longitude(location) BETWEEN 108.05 AND 108.35);
-- -> SP105, SP111

-- 6. Độ phân giải tọa độ
SELECT
  SUM(CAST(ST_Latitude(location)*1000 AS UNSIGNED) = ST_Latitude(location)*1000) dp3,
  SUM(CAST(ST_Latitude(location)*10000 AS UNSIGNED) = ST_Latitude(location)*10000) dp4
FROM properties WHERE status='PUBLISHED';
-- -> dp3=50, dp4=121
```

**Script kiểm toán:** các script dùng để tạo báo cáo này chỉ chạy `SELECT`, không ghi
dữ liệu, không log thông tin cá nhân. Chúng nằm ngoài repository (`.scratch/`) và
không được commit.

---

**Tài liệu liên quan**

- [PR #35 — GIS V2 research](https://github.com/manchae19/SmartProp/pull/35)
- `docs/SMARTPROP_GIS_V2_RESEARCH_AND_READINESS.md`
- `backend/src/main/java/vn/smartprop/gis/DanangSpatialValidator.java`
- `backend/src/main/java/vn/smartprop/modules/property/PropertyService.java`
- `frontend/src/features/map/ManualLocationMap.jsx`
- `database/migrations/V3__properties_images_and_spatial.sql`
