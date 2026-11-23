-- Backfill Coordinate Provenance V1 cho dữ liệu cũ.
--
-- Nguyên tắc: KHÔNG suy nguồn từ tên ảnh, KHÔNG tự xác minh cấp thửa.
-- Mọi tin chưa có audit nhận: coordinate_source=UNKNOWN, accuracy_level=UNKNOWN,
-- accuracy_meters=NULL, verification_status=UNVERIFIED.
--
-- Chạy lại nhiều lần không tạo bản ghi trùng: chỉ chèn cho tin CHƯA có audit hiện hành.
-- Không sửa properties.location, listing_code, status hay owner.

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
  -- Fingerprint tính trong SQL phải khớp PropertyCoordinateAuditRepository.fingerprint:
  -- SHA-256 của "lat|lon|address|district|ward|scopeVersion" với 7 chữ số thập phân.
  SHA2(CONCAT(
    FORMAT(ROUND(ST_Latitude(p.location), 7), 7), '|',
    FORMAT(ROUND(ST_Longitude(p.location), 7), 7), '|',
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
