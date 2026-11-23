-- Backfill Coordinate Provenance V1 cho dữ liệu cũ.
--
-- Nguyên tắc: KHÔNG suy nguồn từ tên ảnh, KHÔNG tự xác minh cấp thửa.
-- Mọi tin chưa có audit nhận: coordinate_source=UNKNOWN, accuracy_level=UNKNOWN,
-- accuracy_meters=NULL, verification_status=UNVERIFIED.
--
-- Chạy lại nhiều lần không tạo bản ghi trùng: chỉ chèn cho tin CHƯA có audit hiện hành.
-- Không sửa properties.location, listing_code, status hay owner.
--
-- FINGERPRINT: phải khớp CHÍNH XÁC PropertyCoordinateAuditRepository.fingerprint():
--   String.format(Locale.ROOT, "%.7f|%.7f|%s|%s|%s|%s", lat, lon, address, district, ward, scope)
--   rồi SHA-256 hex.
--
-- KHÔNG dùng FORMAT(x, 7): MySQL FORMAT thêm dấu phẩy phân cách hàng nghìn
-- (FORMAT(1234.5,7) = '1,234.5000000'), Java String.format thì không.
-- Dùng CAST(... AS DECIMAL(10,7)) để có biểu diễn không phân cách, khớp Java.
--
-- GIỚI HẠN DECIMAL(10,7): tối đa 3 chữ số nguyên (999.9999999). Đà Nẵng có
-- lat 15–16, lon 107–108 nên an toàn. Nếu dùng cho toạ độ ngoài khoảng này,
-- phải nâng lên DECIMAL(12,7) ở cả migration và backfill.
--
-- Scope version: dùng 'BACKFILL_V1' — khác runtime validator.scopeVersion().
-- Vì vậy fingerprint backfill KHÔNG BAO GIỜ khớp fingerprint runtime. Đây là chủ ý:
-- lần đầu người dùng lưu tin, fingerprint runtime khác → audit backfill bị supersede
-- và revision mới được tạo với provenance/accuracy đúng. Không có revision giả vì
-- backfill chỉ tạo MỘT bản cho mỗi tin, và bản đó mang trạng thái UNKNOWN an toàn.

INSERT INTO property_coordinate_audit (
  id, property_id, revision, audited_latitude, audited_longitude, srid,
  coordinate_fingerprint, fingerprint_version,
  address_snapshot, district_snapshot, ward_snapshot,
  coordinate_source, accuracy_level, accuracy_meters,
  verification_status, geographic_validation_status, geographic_validation_note,
  validator_scope_version, validated_at)
SELECT
  UUID(),
  p.id,
  1,
  CAST(ROUND(ST_Latitude(p.location), 7) AS DECIMAL(10,7)),
  CAST(ROUND(ST_Longitude(p.location), 7) AS DECIMAL(10,7)),
  4326,
  SHA2(CONCAT(
    CAST(CAST(ROUND(ST_Latitude(p.location), 7) AS DECIMAL(10,7)) AS CHAR), '|',
    CAST(CAST(ROUND(ST_Longitude(p.location), 7) AS DECIMAL(10,7)) AS CHAR), '|',
    COALESCE(TRIM(p.address), ''), '|',
    COALESCE(TRIM(p.district), ''), '|',
    COALESCE(TRIM(p.ward), ''), '|',
    'BACKFILL_V1'), 256),
  1,
  p.address, p.district, p.ward,
  'UNKNOWN', 'UNKNOWN', NULL,
  'UNVERIFIED', NULL, NULL,
  'BACKFILL_V1', UTC_TIMESTAMP(6)
FROM properties p
WHERE p.location IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM property_coordinate_audit a
    WHERE a.property_id = p.id AND a.superseded_at IS NULL
  );

SELECT ROW_COUNT() AS backfilled_rows;
