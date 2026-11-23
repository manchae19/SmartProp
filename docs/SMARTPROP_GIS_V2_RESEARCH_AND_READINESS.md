# SmartProp GIS V2 — Nghiên cứu và mức độ sẵn sàng

**Ngày khảo sát:** 2026-11-23
**Mốc nền:** `main @ 034ec2d` (sau merge PR #34)
**Trạng thái:** nghiên cứu — chưa triển khai tính năng

---

## Kết luận trước

**`NEEDS_VERIFIED_GIS_DATA`**

SmartProp đã có hạ tầng không gian tốt hơn mức cần thiết cho GIS V2: MySQL 8 Spatial
với `POINT SRID 4326`, spatial index, validator chất lượng tọa độ 8 mức, và pattern
truy vấn `MBRContains` + `ST_Distance_Sphere` đang chạy production.

**Thiếu là dữ liệu, không phải mã.** Trong phạm vi khảo sát và tại thời điểm kiểm tra,
chưa xác minh được nguồn geometry nguy cơ ngập có quyền sử dụng phù hợp. Cụ thể:

| Thành phần | Trạng thái |
|---|---|
| Tọa độ bất động sản | **Có** — 152/152 tin |
| Hạ tầng spatial MySQL | **Có** — POINT SRID 4326 + SPATIAL KEY |
| Validator chất lượng tọa độ | **Có** — 8 mức, đang dùng |
| Pattern truy vấn khoảng cách | **Có** — `ST_Distance_Sphere` cho POINT |
| Polygon ranh giới phường | **Không** — chỉ có cấp quận cũ |
| Geometry vị trí ngập | **Không** — `flood_records` không có cột geometry |
| Provenance tọa độ BĐS | **Không** — xem `SMARTPROP_COORDINATE_PROVENANCE_AUDIT.md` |

> **Đọc kèm:** `docs/SMARTPROP_COORDINATE_PROVENANCE_AUDIT.md` (PR #36) kiểm toán
> nguồn gốc tọa độ 152 tin. Kết luận: **0/152 tin có bằng chứng xác minh cấp thửa**,
> và `VERIFIED_EXACT` chỉ xác nhận điểm nằm trong polygon **quận**, không phải cấp
> thửa. Hai tài liệu dùng chung thuật ngữ `geographic_validity`,
> `coordinate_provenance`, `parcel_accuracy`.
| Polygon vùng nguy cơ ngập | **Không** — nguồn chính thức chưa công khai |

Xây GIS V2 lúc này sẽ buộc phải bịa geometry từ mô tả chữ — đúng điều cấm trong
yêu cầu. Vì vậy PR này chỉ bàn giao báo cáo, không kèm mã tính năng.

---

## A. Hiện trạng GIS SmartProp

### A.1. Hạ tầng không gian

**MySQL 8 Spatial đã dùng từ migration V3:**

```sql
-- database/migrations/V3__properties_images_and_spatial.sql
location POINT SRID 4326,              -- properties
SPATIAL KEY sx_properties_location (location)
location POINT NOT NULL SRID 4326,     -- points_of_interest
SPATIAL KEY sx_poi_location (location)
```

Không cần PostGIS. MySQL 8 đáp ứng đủ cho POINT và khoảng cách; `ST_Contains`
với POLYGON cũng có nhưng chưa dùng.

### A.2. Tọa độ bất động sản

| Câu hỏi | Trả lời |
|---|---|
| Tin có latitude/longitude chưa? | **Có** — 152/152 tin thật |
| Tọa độ lấy từ đâu? | Người đăng chọn trên bản đồ (`ManualLocationMap.jsx`), hoặc geocode |
| Có lưu mức độ chính xác? | **Không** — bảng `properties` không có cột chất lượng |
| Đã dùng MySQL Spatial? | **Có** — `POINT SRID 4326` + `SPATIAL KEY` |
| Có index không gian? | **Có** — `sx_properties_location` |
| Có API GeoJSON? | **Có** — `danang-search-scopes.geojson` (ranh giới quận) |
| Phân biệt vị trí chính xác vs ước lượng? | **Có, nhưng ở tầng service** — `DanangSpatialValidator` |

**Điểm quan trọng:** chất lượng tọa độ được đánh giá **lúc chạy**, không lưu vào DB.
`DanangSpatialValidator.validate()` trả `CoordinateValidationResult` với 8 trạng thái:

```java
// backend/src/main/java/vn/smartprop/gis/GisDtos.java L50-59
VERIFIED_EXACT,              // điểm nằm trong polygon QUẬN đã khai báo
VERIFIED_BOUNDARY_BUFFER,    // trong vùng đệm ranh giới quận (750 m)
VERIFIED_DANANG_POLYGON,     // trong polygon thành phố, không khớp quận khai báo
INVALID_DISTRICT_MISMATCH,   // toạ độ lệch quận khai báo
INVALID_SWAPPED_AXES,        // lat/lon hoán đổi
OUTSIDE_DANANG_BOUNDS,       // ngoài khung bao địa lý Đà Nẵng
INVALID_COORDINATES,         // toạ độ không hợp lệ
NONE_ADMIN_ONLY              // chỉ có địa bàn, không có ghim
```

> **`VERIFIED_EXACT` KHÔNG có nghĩa "chính xác cấp thửa".** Điều kiện tạo là
> `declaredPoly.contains(pt) || declaredPoly.touches(pt)` với `declaredPoly` là polygon
> **quận lịch sử** — vùng rộng hàng chục km². Nó xác nhận **geographic validity**
> (hợp lệ về địa giới hành chính), **không** xác nhận **coordinate provenance**
> (tọa độ từ đâu) và **không** xác nhận **parcel accuracy** (đúng thửa đất).
> Xem `docs/SMARTPROP_COORDINATE_PROVENANCE_AUDIT.md` mục D.

Ba chiều này độc lập và không được suy ra lẫn nhau:

| Chiều | Validator kiểm tra? | Nguồn dữ liệu |
|---|---|---|
| `geographic_validity` | **Có** | Polygon quận trong `danang-search-scopes.geojson` |
| `coordinate_provenance` | **Không** | Không có cột metadata nào |
| `parcel_accuracy` | **Không** | Không có dữ liệu địa chính |

**Hệ quả cho GIS V2:** không được kết luận `VERIFIED_AREA_OVERLAP` chỉ vì
`coordinateStatus = VERIFIED_EXACT`. Cần thêm metadata nguồn gốc và độ chính xác
(mục C.6).

### A.3. Cách đối chiếu nguy cơ ngập hiện tại

```java
// PrePurchaseRepository.flood(street, currentUnit)
SELECT ... FROM flood_records
WHERE street IS NOT NULL AND street = ? AND current_unit = ?
ORDER BY publication_date DESC, id
LIMIT 10
```

Khớp **chính xác** theo `street` + `current_unit`. Không có không gian.

`PrePurchaseService.floodMatch()` trả `Match.STREET` chỉ khi cả hai điều kiện đúng.
Nhãn hiển thị: *"Có vị trí nguy cơ ngập trên cùng tuyến đường"* — không khẳng định
căn nhà nằm trong vùng ngập.

### A.4. Bản ghi nguy cơ ngập

`flood_records` (V24 + V25) **không có cột geometry**:

```
id, record_type, location_text, street, ward, district, scope, depth_note,
event_date, publication_date, source_url, source_title, source_sha256,
checked_at, created_at, source_district, current_unit, area_basis,
area_note, decision_number, source_page
```

`scope` là enum chữ: `POINT`, `ROAD_SEGMENT`, `AREA`, `WARNING` — mô tả **độ rộng
bằng chứng**, không phải hình học. Không có toạ độ nào trong 124 bản ghi.

### A.5. Pattern truy vấn không gian đang dùng

`AdvisorPoiSpatialRepository` đã giải đúng bài toán GIS V2 cần:

```java
// L150-155
WHERE MBRContains(
    ST_GeomFromText(bbox, 4326, 'axis-order=long-lat'),
    p.location)
  AND ST_Distance_Sphere(p.location, point) <= ?
```

`MBRContains` lọc thô bằng spatial index, `ST_Distance_Sphere` tính chính xác.
**Tái sử dụng được nguyên vẹn** cho flood GIS V2.

### A.6. Frontend

| Thành phần | Hiện có |
|---|---|
| Thư viện bản đồ | **Leaflet 1.9.4** |
| Component bản đồ | `MapView.jsx`, `HomeGIS.jsx`, `LeafletNearbyMap.jsx`, `ManualLocationMap.jsx`, `ChatAmenityMap.jsx`, `BrowseTileMap.jsx` |
| Marker bất động sản | Có |
| Popup / bảng thông tin | Có (`AdvisorLocationCard.jsx`) |
| Lớp GIS | Có — POI, amenity |

Không cần thêm thư viện. Lớp flood chỉ là thêm một `LayerGroup` Leaflet.

### A.7. Phần tái sử dụng được

| Cần cho GIS V2 | Đã có | Ghi chú |
|---|---|---|
| Lưu POINT SRID 4326 | ✅ | `properties.location` |
| Spatial index | ✅ | `sx_properties_location` |
| Đánh giá chất lượng tọa độ | ✅ | `DanangSpatialValidator` |
| Truy vấn khoảng cách | ✅ | `AdvisorPoiSpatialRepository` |
| Polygon ranh giới | ⚠️ | có cấp quận, **thiếu cấp phường** |
| Bản đồ Leaflet | ✅ | 6 component |
| Geometry vị trí ngập | ❌ | **phải bổ sung** |

---

## B. Danh sách nguồn GIS

### B.1. Dữ liệu nguy cơ ngập

| Nguồn | Loại | Định dạng | Phạm vi | Quyền sử dụng | Chính xác | Kết luận |
|---|---|---|---|---|---|---|
| [QĐ 2322/QĐ-UBND + Phụ lục VIII](https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf) | Danh mục 124 vị trí ngập | PDF (bảng chữ) | Đà Nẵng | Văn bản công khai | Địa chỉ chữ, **không toạ độ** | **Đã dùng** — nguồn hiện tại |
| [muangap.danang.gov.vn](https://muangap.danang.gov.vn/) | Bản đồ mưa ngập realtime | SPA web | Đà Nẵng | Không công bố | Không rõ | **Không dùng được** — không có API công khai, mọi path trả HTML |
| [sotandan.danang.gov.vn](https://sotandan.danang.gov.vn/300) | Bản đồ thiên tai (lũ, ngập) | Ứng dụng web ASP.NET | Đà Nẵng | Không công bố | Không rõ | **Không dùng được** — `/api/*` trả HTTP 500, không có endpoint công khai |
| [opendata.danang.gov.vn](https://opendata.danang.gov.vn/) | Cổng dữ liệu mở | Web + API | Đà Nẵng | Chưa rõ | — | **Không dùng được** — `/api/dataset` trả **HTTP 401**, cần đăng ký |
| [HĐND Đà Nẵng — công khai bản đồ ngập](https://hdnd.danang.gov.vn/chi-tiet-tin/group/157/nid/23678) | Nghị luận chính sách | Bài viết | Đà Nẵng | — | — | **Bằng chứng then chốt**: xác nhận bản đồ ngập **chưa được công khai**, đang trong lộ trình |

**Kết luận B.1:** Trong phạm vi khảo sát và tại thời điểm kiểm tra (2026-11-23),
**chưa xác minh được nguồn geometry nguy cơ ngập có quyền sử dụng phù hợp** để đưa vào
SmartProp.

Bài viết HĐND ngày 03/06/2026 nêu rõ thành phố đang xây dựng cơ sở dữ liệu ngập lịch
sử và sẽ công khai qua nền tảng số thống nhất — **chưa có tại thời điểm khảo sát**.

**Phân biệt các tình huống đã gặp — không quy chụp về một kết luận:**

| Tình huống | Nguồn gặp phải | Ý nghĩa |
|---|---|---|
| API chưa tìm thấy | `muangap.danang.gov.vn` | SPA trả HTML cho mọi path; có thể có API nội bộ chưa công bố |
| API cần xác thực | `opendata.danang.gov.vn` | HTTP 401 — cần đăng ký tài khoản, **không phải dữ liệu không tồn tại** |
| API trả lỗi tạm thời | `sotandan.danang.gov.vn` | HTTP 500 — có thể lỗi cấu hình, **không phải bằng chứng vĩnh viễn** |
| Website có dữ liệu nhưng không công bố quyền | `sotandan`, `muangap` | Hiển thị bản đồ nhưng không nêu license |
| Dữ liệu thực sự chưa công khai | HĐND Đà Nẵng | Thành phố xác nhận đang trong lộ trình |
| Nguồn có geometry nhưng thiếu căn cứ phạm vi ngập | OSM Overpass | Có đường nhưng không có vùng ngập |

**Không coi HTTP 401, 500 hoặc lỗi SSL là bằng chứng dữ liệu không tồn tại vĩnh viễn.**
Các nguồn này cần được kiểm tra lại khi có thông tin mới hoặc khi liên hệ được cơ quan
chủ quản.

**Không thu thập trái phép hoặc vượt qua cơ chế bảo vệ website.**

### B.2. Dữ liệu địa hình

| Nguồn | Loại | Định dạng | Phạm vi | Quyền sử dụng | Chính xác | Kết luận |
|---|---|---|---|---|---|---|
| [Copernicus DEM GLO-30](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM) | DSM 30 m | GeoTIFF | Toàn cầu | Miễn phí, có đăng ký | ±2–4 m độ cao | **Không dùng cho ngập** |
| [OpenTopography — Copernicus GLO-30](https://portal.opentopography.org/raster?opentopoID=OTSDEM.032021.4326.3) | DSM 30 m | GeoTIFF | Toàn cầu | Miễn phí | ±2–4 m | **Không dùng cho ngập** |

**Kết luận B.2:** DEM 30 m là **DSM** (bề mặt, gồm cả nhà và cây), không phải DEM
địa hình trần. Sai số ±2–4 m lớn hơn chênh lệch cao độ đô thị Đà Nẵng ở nhiều khu vực.
Không thể dùng để kết luận ngập — đúng như cảnh báo trong yêu cầu.

### B.3. Dữ liệu đường và địa giới

| Nguồn | Loại | Định dạng | Phạm vi | Quyền sử dụng | Chính xác | Kết luận |
|---|---|---|---|---|---|---|
| [OpenStreetMap — Overpass API](https://overpass-api.de/) | Đường, toà nhà, thuỷ hệ | JSON / GeoJSON | Toàn cầu | **ODbL** — cho phép dùng, phải ghi nguồn | Tốt ở trung tâm, thưa ở ngoại vi | **Dùng được** — hỗ trợ định vị |
| [zuydd/vn-geo](https://github.com/zuydd/vn-geo) | Đơn vị hành chính sau 2025 | JSON, CSV, XLSX | Việt Nam | **Không có license** | Danh sách, không polygon | **Không dùng được** |
| [adminvsrm/GISData](https://github.com/adminvsrm/GISData) | Ranh giới hành chính | GeoJSON, SHP | Việt Nam | **Không có license** | Không rõ nguồn gốc | **Không dùng được** |
| [Cổng dữ liệu nền địa lý quốc gia](https://dosm.vnsdi.gov.vn/) | Dữ liệu nền địa lý | Web portal | Việt Nam | Cần kiểm tra | Có thẩm quyền | **Cần đăng ký** |
| [Cổng không gian địa lý VN](https://vnsdi.mae.gov.vn/infomation) | Dữ liệu không gian | Web portal | Việt Nam | Cần kiểm tra | Có thẩm quyền | **Lỗi chứng chỉ SSL** khi truy cập |

**Kết luận B.3:** OSM là nguồn khả dụng duy nhất có license rõ ràng (ODbL). Nhưng
kiểm tra thực tế cho thấy OSM **thiếu geometry** cho nhiều tuyến:

```
Tôn Đản          : 2 way, 10 điểm — chỉ phủ một đoạn ngắn
Trần Cao Vân     : 0 way
Nguyễn Lương Bằng: HTTP 502 (Overpass quá tải)
```

Không đủ để dựng LINESTRING cho 124 vị trí ngập.

### B.4. Tổng hợp khả dụng

| Nguồn | Dùng được? | Lý do |
|---|---|---|
| QĐ 2322 Phụ lục VIII | ✅ Đang dùng | Nguồn chính thức, nhưng chỉ chữ |
| OSM Overpass | ⚠️ Hạn chế | ODbL tốt, nhưng thiếu geometry nhiều tuyến |
| Copernicus DEM | ❌ | DSM 30 m, không kết luận được ngập |
| opendata.danang.gov.vn | ❌ | HTTP 401 |
| muangap.danang.gov.vn | ❌ | Không có API |
| sotandan.danang.gov.vn | ❌ | API trả 500 |
| vn-geo, GISData | ❌ | Không license |
| vnsdi.mae.gov.vn | ❌ | Lỗi SSL |

---

## C. Phương án kiến trúc

### C.1. Schema đề xuất

**Nguyên tắc tách biệt:** `evidence_level` **không** phải thuộc tính cố định của bản
ghi ngập. Cùng một polygon ngập nhưng hai bất động sản khác nhau có thể nhận hai mức
bằng chứng khác nhau — một căn nằm trong polygon, một căn cách 500 m.

Vì vậy phải tách hai khái niệm:

| Khái niệm | Thuộc về | Lưu ở đâu |
|---|---|---|
| **Source evidence** — bằng chứng về nguồn dữ liệu ngập | Bản ghi ngập | `flood_records` |
| **Spatial match result** — kết quả đối chiếu BĐS ↔ nguồn | Cặp (bất động sản, bản ghi ngập) | Tính lúc chạy, **không lưu** |

**Không lưu kết quả so khớp của một bất động sản như thuộc tính cố định của nguồn ngập.**

#### Phần 1 — mở rộng `flood_records` (source evidence)

```sql
ALTER TABLE flood_records
  ADD COLUMN geometry_type VARCHAR(20) CHARACTER SET ascii COLLATE ascii_bin
      DEFAULT 'UNKNOWN' NOT NULL,
  ADD COLUMN geometry GEOMETRY SRID 4326 DEFAULT NULL,
  ADD COLUMN location_accuracy VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin
      DEFAULT NULL,
  ADD COLUMN observation_date DATE DEFAULT NULL,
  ADD COLUMN data_license VARCHAR(100) DEFAULT NULL,
  ADD COLUMN verification_status VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin
      DEFAULT 'UNVERIFIED' NOT NULL,
  ADD CONSTRAINT ck_flood_geometry_type CHECK(geometry_type IN (
      'POINT','LINESTRING','POLYGON','MULTIPOLYGON','UNKNOWN')),
  ADD CONSTRAINT ck_flood_location_accuracy CHECK(
      location_accuracy IS NULL OR location_accuracy IN (
      'PARCEL','BUILDING','STREET','SEGMENT','WARD','DISTRICT','CITY','UNKNOWN')),
  ADD CONSTRAINT ck_flood_verification CHECK(verification_status IN (
      'UNVERIFIED','SOURCE_CITED','FIELD_VERIFIED','SYNTHETIC_TEST_ONLY'));

-- Spatial index chỉ khi có geometry thật; MySQL yêu cầu cột NOT NULL.
-- Giữ NULL-able, dùng index thường trên geometry_type thay vì SPATIAL KEY.
CREATE INDEX idx_flood_geometry_type ON flood_records(geometry_type);
```

**Đã bỏ `evidence_level` khỏi `flood_records`** — nó là kết quả so khớp, không phải
thuộc tính nguồn.

#### Phần 2 — kết quả so khớp tính lúc chạy

`evidence_level` nằm trong response API, không nằm trong DB:

```java
public record FloodEvidenceMatch(
    String recordId,
    String evidenceLevel,        // VERIFIED_AREA_OVERLAP | NEAR_VERIFIED_LOCATION
                                 // | SAME_STREET_WARD | INSUFFICIENT_EVIDENCE
    String geometryType,         // POINT | LINESTRING | POLYGON | UNKNOWN
    Double distanceMeters,       // null khi không đo được
    String distanceMethod,       // ST_Distance_Sphere | ST_Transform+ST_Distance | null
    String locationAccuracy,     // từ flood_records
    String verificationStatus,   // từ flood_records
    String sourceName,
    String sourceUrl,
    LocalDate observationDate,
    String dataLicense,
    String messageVi
) {}
```

**Vì sao không lưu:** nếu lưu `evidence_level` vào `flood_records`, mọi bất động sản
khớp với bản ghi đó sẽ nhận cùng một mức — sai bản chất. Nếu lưu vào bảng riêng theo
cặp (property, record), dữ liệu sẽ phình rất nhanh và lỗi thời khi tọa độ đổi.

**Vì sao không `SPATIAL KEY`:** MySQL 8 yêu cầu cột spatial index phải `NOT NULL`.
124 bản ghi hiện tại không có geometry, nên `SPATIAL KEY` sẽ chặn migration. Khi có
dữ liệu thật, thêm index ở migration riêng.

**Vì sao `GEOMETRY` không phải `POINT`:** cần chứa cả LINESTRING và POLYGON.

**Tương thích với 124 bản ghi hiện tại:** tất cả cột mới đều nullable hoặc có DEFAULT,
nên migration không phá vỡ dữ liệu cũ. `geometry_type='UNKNOWN'` cho 124 bản ghi cũ.

### C.2. API đề xuất

```
GET /api/v1/flood/evidence?lat={lat}&lon={lon}&radiusMeters={r}
```

Trả về danh sách bằng chứng có thứ hạng:

```json
{
  "evidenceLevel": "NEAR_VERIFIED_LOCATION",
  "items": [{
    "recordId": "PL8-VI-04",
    "geometryType": "LINESTRING",
    "distanceMeters": 87,
    "locationAccuracy": "STREET_SEGMENT",
    "sourceName": "QĐ 2322/QĐ-UBND — Phụ lục VIII",
    "sourceUrl": "https://pctt.danang.gov.vn/...",
    "observationDate": "2026-05-26",
    "dataLicense": "public-document",
    "verificationStatus": "SOURCE_CITED",
    "message": "Có vị trí được ghi nhận nguy cơ ngập cách 87 m"
  }]
}
```

**Không thay `pre-purchase-checks` hiện tại.** API mới chạy song song cho tới khi
được kiểm chứng.

### C.3. Thuật toán 4 mức

```text
1. VERIFIED_AREA_OVERLAP
   geometry_type IN (POLYGON, MULTIPOLYGON)
   AND ST_Intersects(geometry, property.location)      -- KHÔNG dùng ST_Contains
   AND property coordinateStatus = VERIFIED_EXACT
   AND property có provenance + accuracy đủ tin cậy    -- điều kiện MỚI
   -> "Vị trí bất động sản được đối chiếu nằm trong khu vực nguy cơ ngập
       theo nguồn dữ liệu được dẫn."

2. NEAR_VERIFIED_LOCATION
   geometry_type = POINT
     AND ST_Distance_Sphere(geometry, property.location) <= radiusMeters
   geometry_type = LINESTRING
     AND ST_Distance(geometry_metric, property.location_metric) <= radiusMeters
   -> hiển thị khoảng cách thực + nguồn + cảnh báo "gần không đồng nghĩa nằm trong"

3. SAME_STREET_WARD
   logic hiện tại: street = ? AND current_unit = ?
   -> "Có vị trí được ghi nhận nguy cơ ngập trên cùng tuyến đường."

4. INSUFFICIENT_EVIDENCE
   không có bản ghi phù hợp
   -> "Chưa có đủ dữ liệu để đánh giá nguy cơ ngập tại vị trí này."
   KHÔNG hiển thị "Không có nguy cơ ngập".
```

**Điều kiện chặn:** nếu `coordinateStatus = NONE_ADMIN_ONLY` hoặc
`VERIFIED_DANANG_POLYGON` (chỉ biết trong thành phố), **không** dùng để kết luận
mức 1 hay 2 — hạ xuống mức 3.

**Điều kiện chặn mới cho mức 1:** `VERIFIED_EXACT` **một mình không đủ**. Nó chỉ xác
nhận điểm nằm trong polygon quận. Muốn kết luận `VERIFIED_AREA_OVERLAP` phải có thêm
`coordinate_provenance` và `accuracy_level` từ bảng audit (mục C.6). Hiện tại **0/152
tin** đáp ứng — nên mức 1 chưa thể kích hoạt.

**Ngưỡng `radiusMeters`:** tham số cấu hình, mặc định 200 m, phải ghi rõ trong
response. Không chuyển thành xác suất ngập.

### C.3b. Khoảng cách tới LINESTRING — sửa lỗi thiết kế

**Thiết kế trước SAI:** dùng `ST_Distance_Sphere(geometry, property.location)` cho cả
`POINT` và `LINESTRING`. Đã kiểm chứng trên MySQL 8.4.13:

```sql
SELECT ST_Distance_Sphere(
  ST_GeomFromText('LINESTRING(108.20 16.05, 108.21 16.06)', 4326, 'axis-order=long-lat'),
  ST_GeomFromText('POINT(108.205 16.055)', 4326, 'axis-order=long-lat'));
-- ERROR 3618 (22S00): st_distance_sphere(LINESTRING, POINT) has not been
-- implemented for geographic spatial reference systems.
```

**MySQL 8 không hỗ trợ `ST_Distance_Sphere` cho LINESTRING với SRID 4326.** Chỉ hỗ trợ
POINT↔POINT.

#### Phương án đúng cho LINESTRING

**Bước 1 — chiếu sang hệ mét.** Đà Nẵng nằm trong UTM zone 48N (EPSG:32648), phù hợp
cho khoảng cách cục bộ:

```sql
-- Chiếu điểm và đường sang EPSG:32648 (mét)
ST_Transform(geometry, 32648)
```

**Bước 2 — tính khoảng cách trong hệ mét:**

```sql
SELECT ST_Distance(
         ST_Transform(flood_geometry, 32648),
         ST_Transform(property_location, 32648)
       ) AS distance_meters
FROM ...
WHERE ST_Distance(
        ST_Transform(flood_geometry, 32648),
        ST_Transform(property_location, 32648)
      ) <= ?
```

**Kiểm chứng `ST_Distance` trả mét trong hệ chiếu:**

```sql
-- Trong SRID 4326, ST_Distance trả ĐỘ, không phải mét:
SELECT ST_Distance(
  ST_GeomFromText('LINESTRING(108.20 16.05, 108.21 16.06)', 4326, 'axis-order=long-lat'),
  ST_GeomFromText('POINT(108.205 16.055)', 4326, 'axis-order=long-lat'));
-- -> 0  (độ, không phải mét — điểm nằm trên đường)
```

**Không được** tính khoảng cách bằng độ rồi gọi là mét.

#### Phương án dự phòng — JTS trong Java

Nếu `ST_Transform` không khả dụng trên MySQL đang chạy (cần kiểm tra extension), dùng
JTS đã có sẵn trong project (`org.locationtech.jts`):

```java
// Chiếu thủ công sang UTM 48N rồi tính khoảng cách phẳng
// hoặc dùng GeodeticCalculator của GeoTools nếu được thêm vào
double distanceMeters = JTS.orthodromicDistance(
    propertyCoordinate, nearestPointOnLine, CRS.decode("EPSG:4326"));
```

**Ưu tiên phương án MySQL** vì giữ truy vấn trong DB, dùng được spatial index.
Phương án JTS chỉ dùng khi `ST_Transform` không khả dụng.

#### Bảng chọn hàm theo geometry

| Geometry | Hàm khoảng cách | Đơn vị | Ghi chú |
|---|---|---|---|
| `POINT` | `ST_Distance_Sphere` | mét | Hỗ trợ SRID 4326 |
| `LINESTRING` | `ST_Distance(ST_Transform(...,32648), ...)` | mét | **Không** dùng `ST_Distance_Sphere` |
| `POLYGON` | `ST_Intersects` (quan hệ) | boolean | Không tính khoảng cách |

#### `ST_Contains` vs `ST_Intersects` cho POLYGON

Đã kiểm chứng: điểm nằm **trên biên** polygon cho kết quả khác nhau:

```sql
SELECT ST_Contains(polygon, point_on_boundary);   -- -> 0  (KHÔNG chứa)
SELECT ST_Intersects(polygon, point_on_boundary); -- -> 1  (CÓ giao)
```

**Dùng `ST_Intersects`** cho kiểm tra "nằm trong hoặc trên biên". Nếu nghiệp vụ muốn
loại trừ biên, dùng `ST_Contains` và ghi rõ trong tài liệu.

**Geometry không hợp lệ:** kiểm tra `ST_IsValid(geometry)` trước khi dùng. Polygon tự
giao có thể cho kết quả `ST_Intersects` không xác định.

### C.4. Tích hợp Frontend

Thêm `FloodEvidenceLayer.jsx` dùng Leaflet `LayerGroup`:

- Marker bất động sản (đã có)
- Marker điểm ngập — chỉ khi `geometry_type = POINT`
- Polyline đoạn ngập — chỉ khi `LINESTRING`
- Polygon vùng ngập — chỉ khi `POLYGON`
- Popup: nguồn, ngày, license, mức bằng chứng
- Chú giải 4 màu theo `evidenceLevel`

**Chỉ render lớp có dữ liệu thật.** Không vẽ vùng đỏ giả.

### C.5. Tích hợp Advisor

`AdvisorLocationIntelligenceService` đã có `LocationIntelligence` record. Thêm
trường `floodEvidence` với cùng 4 mức. Prompt Advisor phải nêu rõ mức — không cho
suy diễn "chắc chắn an toàn" hoặc "chắc chắn ngập".

---

## D. Kết quả thử nghiệm

**Không có đối tượng geometry nguy cơ ngập thực tế nào để thử nghiệm.**

| Chỉ số | Giá trị |
|---|---|
| Số geometry nguy cơ ngập dùng được | **0** |
| Số điểm/đoạn ngập xác minh được | **0** |
| Số tin có tọa độ | **152/152** |
| Số tin có bằng chứng xác minh cấp thửa | **0/152** |
| Số tin đối chiếu được cấp vị trí | **0** |
| Số tin phải fallback về cùng tuyến đường | **10** (giữ nguyên) |
| Ca không đủ bằng chứng | **142** |

### Phân bố `CoordinateStatus` — chạy Java thật

Đã chạy `DanangSpatialValidator` production trên 152 tin (xem
`SMARTPROP_COORDINATE_PROVENANCE_AUDIT.md` mục C):

| Trạng thái | Số tin |
|---|---:|
| `VERIFIED_EXACT` | **140** |
| `VERIFIED_BOUNDARY_BUFFER` | **11** |
| `INVALID_DISTRICT_MISMATCH` | **1** |
| Các trạng thái khác | 0 |
| **Tổng** | **152** |

**`VERIFIED_EXACT` không phải cấp thửa** — nó chỉ xác nhận điểm nằm trong polygon
quận. Vì vậy "140 tin `VERIFIED_EXACT`" **không** đồng nghĩa "140 tin có tọa độ chính
xác cấp thửa".

### Phân loại khả năng dùng cho GIS V2

| Nhóm | Số tin |
|---|---:|
| `ELIGIBLE_FOR_PARCEL_SPATIAL_CHECK` | **0** |
| `ELIGIBLE_FOR_APPROXIMATE_MAP_ONLY` | **52** |
| `ADMINISTRATIVE_ONLY` | **11** |
| `NEEDS_REVIEW` | **1** |
| `UNSUITABLE_OR_UNKNOWN` | **88** |
| **Tổng** | **152** |

**Vì sao 88 tin `UNSUITABLE_OR_UNKNOWN`:** `VERIFIED_EXACT` nhưng độ phân giải tọa độ
≤3 chữ số thập phân (~110 m) — không đủ chính xác để đo khoảng cách tới vị trí ngập.
Chi tiết tiêu chí ở `SMARTPROP_COORDINATE_PROVENANCE_AUDIT.md` mục E.

---

## E. Độ phủ

Baseline: **10/152 tin có bằng chứng đối chiếu** (8 `PLANNED_RISK` + 2 `RECORDED_POINT`).

| Nhóm | Số tin | Ghi chú |
|---|---:|---|
| Có khớp bằng chứng cấp đường (`SAME_STREET_WARD`) | **10** | giữ nguyên từ PR #33/#34 |
| Có vị trí gần điểm/đoạn đã xác minh | **0** | không có geometry |
| Có chồng lấn polygon | **0** | không có polygon nguy cơ ngập |
| Không đủ dữ liệu | **142** | |

**Không cộng trùng:** 10 tin thuộc nhóm 1, không tin nào thuộc nhóm 2 hoặc 3.
Tổng duy nhất vẫn là **10/152**.

GIS V2 **không tăng độ phủ** cho tới khi có geometry thật.

---

## F. Rủi ro

| Rủi ro | Mức | Ghi chú |
|---|---|---|
| Sai số tọa độ bất động sản | **Cao** | Không lưu trạng thái chất lượng; geocode ước lượng có thể lệch hàng trăm mét |
| Thiếu polygon cấp phường | **Cao** | Chỉ có 11 polygon cấp quận cũ; không xác định được phường hiện tại bằng không gian |
| Dữ liệu ngập lịch sử ≠ dự báo | **Cao** | QĐ 2322 là **nguy cơ dự báo**, không phải ngập đã xảy ra |
| DEM không đủ phân giải | **Cao** | DSM 30 m, ±2–4 m — không kết luận được |
| Thiếu polygon vùng ngập | **Blocker** | Không có nguồn hợp pháp |
| Điều kiện sử dụng API | **Trung bình** | opendata cần đăng ký; OSM ODbL phải ghi nguồn |
| Cảnh báo sai cho người mua | **Cao** | Nếu hiển thị "nằm trong vùng ngập" từ dữ liệu không đủ, hậu quả pháp lý và uy tín |

**Rủi ro lớn nhất không phải kỹ thuật mà là diễn giải.** Một chấm đỏ trên bản đồ
được người mua hiểu là "nhà này chắc chắn ngập". Mọi mức bằng chứng phải kèm câu
giải thích, và mức 4 không được hiển thị như "an toàn".

---

## G. Đề xuất tiếp theo

### `NEEDS_VERIFIED_GIS_DATA`

**Lý do:** hạ tầng đã sẵn sàng, dữ liệu chưa có. Viết mã lúc này chỉ tạo ra
đường ống dẫn dữ liệu rỗng, hoặc tệ hơn — buộc phải suy geometry từ mô tả chữ.

### Việc cần làm trước khi triển khai

**1. Xin dữ liệu từ cơ quan có thẩm quyền** (ưu tiên cao nhất)

| Cơ quan | Dữ liệu cần | Định dạng mong muốn |
|---|---|---|
| Ban Chỉ huy Phòng thủ dân sự TP Đà Nẵng ([pctt.danang.gov.vn](https://pctt.danang.gov.vn/)) | Toạ độ 124 vị trí Phụ lục VIII | GeoJSON / Shapefile |
| Sở Xây dựng Đà Nẵng | Bản đồ ngập lụt trung tâm đã xây dựng (báo 10/2025) | GeoJSON / WMS |
| Sở Khoa học & Công nghệ | API Cổng dữ liệu mở (đã có dự thảo đặc tả API v1.0) | REST API |
| Cục Đo đạc, Bản đồ và TTĐL | Ranh giới phường sau sắp xếp 2025 | GeoJSON / Shapefile |

**2. Bổ sung polygon cấp phường**

Hiện chỉ có 11 polygon cấp quận cũ. Cần 16 đơn vị cấp xã hiện tại (theo NQ 1659)
để xác định phường bằng không gian thay vì bảng ánh xạ chữ.

**3. Lưu provenance và độ chính xác tọa độ**

Thiết kế đầy đủ ở `docs/SMARTPROP_COORDINATE_PROVENANCE_AUDIT.md` mục F — bảng
`property_coordinate_audit` gắn mỗi lần xác minh với **một phiên bản tọa độ cụ thể**
qua `coordinate_fingerprint`, để tọa độ mới không kế thừa trạng thái đã xác minh của
tọa độ cũ.

Không có bảng này thì không phân biệt được ghim chính xác với geocode ước lượng ở
tầng truy vấn, và **mức 1 `VERIFIED_AREA_OVERLAP` không thể kích hoạt an toàn**.

**4. Chỉ triển khai khi có đủ cả ba**

- Toạ độ POINT/LINESTRING cho ≥ 10 vị trí ngập, có nguồn và license rõ ràng
- Polygon vùng ngập cho ít nhất một phường
- Bảng `property_coordinate_audit` đã có dữ liệu provenance cho ≥ 50% tin

**Lý do thêm điều kiện thứ ba:** `VERIFIED_EXACT` chỉ xác nhận điểm nằm trong polygon
quận. Kết luận "nằm trong vùng ngập" từ nó mà không có provenance sẽ tạo cảnh báo sai
cho người mua — rủi ro cao hơn lợi ích của tính năng.

### Việc có thể làm ngay (không cần dữ liệu mới)

| Việc | Giá trị | Rủi ro |
|---|---|---|
| Thêm bảng `property_coordinate_audit` | Chuẩn bị cho GIS V2, đo được phân bố chất lượng | Thấp |
| Thêm cột geometry (nullable) vào `flood_records` | Sẵn sàng nhập dữ liệu khi có | Thấp |
| API `flood/evidence` trả mức 3 + 4 | Không đổi hành vi hiện tại | Thấp |

Ba việc này là **chuẩn bị schema**, không phải tính năng. Có thể làm thành PR riêng
khi có yêu cầu — báo cáo này không tự thực hiện.

---

## Phụ lục — Lệnh kiểm chứng

```bash
# Hạ tầng spatial
grep -n "SPATIAL KEY\|POINT SRID" database/migrations/V3__properties_images_and_spatial.sql

# flood_records không có geometry
mysql -e "SELECT COLUMN_NAME FROM information_schema.COLUMNS
          WHERE TABLE_SCHEMA='smartprop_fc' AND TABLE_NAME='flood_records';"

# Polygon hiện có chỉ cấp quận
python -c "import json; d=json.load(open('backend/src/main/resources/geocoding/danang-search-scopes.geojson'));
           print({f['properties']['level'] for f in d['features']})"

# Nguồn dữ liệu mở yêu cầu auth
curl -s -o /dev/null -w "%{http_code}" https://opendata.danang.gov.vn/api/dataset
# -> 401

# OSM thiếu geometry
curl -s "https://overpass-api.de/api/interpreter" --data-urlencode \
  'data=[out:json];way["name"="Trần Cao Vân"]["highway"](15.95,108.10,16.15,108.30);out geom;'
# -> elements: []
```

---

**Tài liệu tham khảo**

- [QĐ 2322/QĐ-UBND ngày 26/05/2026 — Phụ lục VIII](https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf)
- [HĐND Đà Nẵng — Sớm công khai bản đồ ngập lụt](https://hdnd.danang.gov.vn/chi-tiet-tin/group/157/nid/23678)
- [Cổng dịch vụ dữ liệu Đà Nẵng](https://opendata.danang.gov.vn/)
- [Bản đồ mưa ngập Đà Nẵng](https://muangap.danang.gov.vn/)
- [Copernicus DEM](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM)
- [OpenStreetMap copyright / ODbL](https://www.openstreetmap.org/copyright)
- [Cổng dữ liệu nền địa lý quốc gia](https://dosm.vnsdi.gov.vn/)
