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

**Thiếu là dữ liệu, không phải mã.** Không có nguồn nào cung cấp geometry nguy cơ
ngập tại Đà Nẵng với quyền sử dụng rõ ràng. Cụ thể:

| Thành phần | Trạng thái |
|---|---|
| Tọa độ bất động sản | **Có** — 152/152 tin |
| Hạ tầng spatial MySQL | **Có** — POINT SRID 4326 + SPATIAL KEY |
| Validator chất lượng tọa độ | **Có** — 8 mức, đang dùng |
| Pattern truy vấn khoảng cách | **Có** — `ST_Distance_Sphere` |
| Polygon ranh giới phường | **Không** — chỉ có cấp quận cũ |
| Geometry vị trí ngập | **Không** — `flood_records` không có cột geometry |
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
VERIFIED_EXACT,              // ghim chính xác cấp thửa
VERIFIED_BOUNDARY_BUFFER,    // trong vùng đệm ranh giới (750 m)
VERIFIED_DANANG_POLYGON,     // trong polygon Đà Nẵng
INVALID_DISTRICT_MISMATCH,   // toạ độ lệch quận khai báo
INVALID_SWAPPED_AXES,        // lat/lon hoán đổi
OUTSIDE_DANANG_BOUNDS,       // ngoài Đà Nẵng
INVALID_COORDINATES,         // toạ độ không hợp lệ
NONE_ADMIN_ONLY              // chỉ có địa bàn, không có ghim
```

Đây chính là "xác định chất lượng tọa độ" mà mục tiêu GIS V2 cần — **đã có sẵn**.

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

**Kết luận B.1:** Không có nguồn geometry nguy cơ ngập nào tải được hợp pháp.
Bài viết HĐND ngày 03/06/2026 nêu rõ thành phố đang xây dựng cơ sở dữ liệu ngập
lịch sử và sẽ công khai qua nền tảng số thống nhất — **chưa có**.

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

**Không tạo bảng mới.** Mở rộng `flood_records` bằng migration V26:

```sql
ALTER TABLE flood_records
  ADD COLUMN geometry_type VARCHAR(20) CHARACTER SET ascii COLLATE ascii_bin
      DEFAULT 'UNKNOWN' NOT NULL,
  ADD COLUMN geometry GEOMETRY SRID 4326 DEFAULT NULL,
  ADD COLUMN location_accuracy VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin
      DEFAULT NULL,
  ADD COLUMN evidence_level VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin
      DEFAULT NULL,
  ADD COLUMN observation_date DATE DEFAULT NULL,
  ADD COLUMN data_license VARCHAR(100) DEFAULT NULL,
  ADD COLUMN verification_status VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin
      DEFAULT 'UNVERIFIED' NOT NULL,
  ADD CONSTRAINT ck_flood_geometry_type CHECK(geometry_type IN (
      'POINT','LINESTRING','POLYGON','MULTIPOLYGON','UNKNOWN')),
  ADD CONSTRAINT ck_flood_evidence_level CHECK(evidence_level IS NULL OR evidence_level IN (
      'VERIFIED_AREA_OVERLAP','NEAR_VERIFIED_LOCATION','SAME_STREET_WARD',
      'INSUFFICIENT_EVIDENCE')),
  ADD CONSTRAINT ck_flood_verification CHECK(verification_status IN (
      'UNVERIFIED','SOURCE_CITED','FIELD_VERIFIED','SYNTHETIC_TEST_ONLY'));

-- Spatial index chỉ khi có geometry thật; MySQL yêu cầu cột NOT NULL.
-- Giữ NULL-able, dùng index thường trên geometry_type thay vì SPATIAL KEY.
CREATE INDEX idx_flood_geometry_type ON flood_records(geometry_type);
```

**Vì sao không `SPATIAL KEY`:** MySQL 8 yêu cầu cột spatial index phải `NOT NULL`.
124 bản ghi hiện tại không có geometry, nên `SPATIAL KEY` sẽ chặn migration. Khi có
dữ liệu thật, thêm index ở migration riêng.

**Vì sao `GEOMETRY` không phải `POINT`:** cần chứa cả LINESTRING và POLYGON.

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
   AND ST_Contains(geometry, property.location)
   AND property coordinateStatus IN (VERIFIED_EXACT, VERIFIED_BOUNDARY_BUFFER)
   -> "Vị trí bất động sản được đối chiếu nằm trong khu vực nguy cơ ngập
       theo nguồn dữ liệu được dẫn."

2. NEAR_VERIFIED_LOCATION
   geometry_type IN (POINT, LINESTRING)
   AND ST_Distance_Sphere(geometry, property.location) <= radiusMeters
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

**Ngưỡng `radiusMeters`:** tham số cấu hình, mặc định 200 m, phải ghi rõ trong
response. Không chuyển thành xác suất ngập.

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

**Không có đối tượng geometry thực tế nào để thử nghiệm.**

| Chỉ số | Giá trị |
|---|---|
| Số geometry nguy cơ ngập dùng được | **0** |
| Số điểm/đoạn ngập xác minh được | **0** |
| Số tin có tọa độ | **152/152** |
| Số tin có tọa độ đủ chính xác cấp thửa | **Chưa đo được** — không có cột lưu trạng thái |
| Số tin đối chiếu được cấp vị trí | **0** |
| Số tin phải fallback về cùng tuyến đường | **10** (giữ nguyên) |
| Ca không đủ bằng chứng | **142** |

**Vì sao không đo được "tọa độ đủ chính xác":** `DanangSpatialValidator` đánh giá
lúc chạy, không lưu. Muốn biết phân bố `VERIFIED_EXACT` phải chạy validator cho
152 tin — việc này cần dựng service, nằm ngoài phạm vi báo cáo nghiên cứu.

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

**3. Lưu trạng thái chất lượng tọa độ**

Thêm cột `coordinate_status` vào `properties`, ghi kết quả
`DanangSpatialValidator` lúc tạo tin. Không có cột này thì không phân biệt được
ghim chính xác với geocode ước lượng ở tầng truy vấn.

**4. Chỉ triển khai khi có ít nhất một trong hai**

- Toạ độ POINT/LINESTRING cho ≥ 10 vị trí ngập, có nguồn và license rõ ràng
- Polygon vùng ngập cho ít nhất một phường

### Việc có thể làm ngay (không cần dữ liệu mới)

| Việc | Giá trị | Rủi ro |
|---|---|---|
| Thêm cột `coordinate_status` vào `properties` | Chuẩn bị cho GIS V2, đo được phân bố chất lượng | Thấp |
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
