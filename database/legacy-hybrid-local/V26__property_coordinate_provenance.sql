-- Coordinate Provenance V1: lịch sử nguồn gốc, độ chính xác và xác minh tọa độ.
--
-- Bối cảnh (xem docs/SMARTPROP_COORDINATE_PROVENANCE_AUDIT.md):
--   * 152/152 tin PUBLISHED có POINT SRID 4326 hợp lệ về mặt kỹ thuật.
--   * 0/152 tin có metadata nguồn gốc hay độ chính xác tọa độ.
--   * DanangSpatialValidator chỉ xác nhận điểm nằm trong polygon QUẬN — không phải
--     cấp thửa. Vì vậy kết quả validator KHÔNG được dùng để suy ra accuracy cấp thửa.
--
-- Bảng này tách ba khái niệm độc lập:
--   geographic_validity  — điểm có hợp lệ và đúng địa bàn không (validator)
--   coordinate_provenance — tọa độ đến từ đâu (coordinate_source)
--   parcel_accuracy      — có đúng thửa đất không (accuracy_level + verification)
--
-- Mỗi bản ghi audit gắn với MỘT phiên bản tọa độ cụ thể qua coordinate_fingerprint.
-- Khi tọa độ hoặc địa chỉ đổi, audit cũ bị superseded và audit mới được tạo — không
-- kế thừa trạng thái xác minh của tọa độ cũ.

CREATE TABLE property_coordinate_audit (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,

  -- Liên kết bất động sản. FK chặn audit mồ côi.
  property_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,

  -- Revision tăng dần theo từng tin. Dùng để xác định bản ghi hiện hành và
  -- phát hiện ghi đồng thời.
  revision INT NOT NULL,

  -- Bản chụp tọa độ được kiểm toán. DECIMAL(10,7) giữ đủ ~1 cm, khớp độ phân giải
  -- thực tế của POINT SRID 4326 và tránh sai số biểu diễn DOUBLE.
  audited_latitude DECIMAL(10,7) NOT NULL,
  audited_longitude DECIMAL(10,7) NOT NULL,
  srid SMALLINT NOT NULL DEFAULT 4326,

  -- Fingerprint của (tọa độ + địa chỉ + phiên bản validator). Đổi bất kỳ thành phần
  -- nào cũng làm fingerprint đổi, nên audit cũ không thể áp dụng cho trạng thái mới.
  coordinate_fingerprint CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  fingerprint_version SMALLINT NOT NULL DEFAULT 1,

  -- Bản chụp địa chỉ tại thời điểm audit. Cần thiết vì đổi địa chỉ mà giữ tọa độ
  -- vẫn có thể làm kết luận cũ hết hiệu lực.
  address_snapshot VARCHAR(500) DEFAULT NULL,
  district_snapshot VARCHAR(100) DEFAULT NULL,
  ward_snapshot VARCHAR(100) DEFAULT NULL,

  -- Provenance: tọa độ đến từ đâu.
  coordinate_source VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  source_reference VARCHAR(255) DEFAULT NULL,
  source_recorded_at DATETIME(6) DEFAULT NULL,
  source_recorded_by BIGINT DEFAULT NULL,

  -- Accuracy: độ chính xác được CHỨNG MINH, không suy từ số chữ số thập phân.
  accuracy_level VARCHAR(20) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'UNKNOWN',
  accuracy_meters DECIMAL(10,2) DEFAULT NULL,
  accuracy_method VARCHAR(40) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,

  -- Verification: xác minh độc lập, có kiểm soát quyền.
  verification_status VARCHAR(20) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'UNVERIFIED',
  verification_method VARCHAR(40) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,
  verified_at DATETIME(6) DEFAULT NULL,
  verified_by BIGINT DEFAULT NULL,
  evidence_reference VARCHAR(500) DEFAULT NULL,

  -- Geographic validation: kết quả DanangSpatialValidator, lưu lại thay vì tính runtime.
  geographic_validation_status VARCHAR(40) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,
  geographic_validation_note VARCHAR(500) DEFAULT NULL,
  validator_scope_version VARCHAR(40) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,
  validated_at DATETIME(6) DEFAULT NULL,

  -- Lifecycle.
  created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  superseded_at DATETIME(6) DEFAULT NULL,
  superseded_reason VARCHAR(40) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,

  -- Một tin chỉ có tối đa một audit hiện hành. MySQL 8 không có partial index,
  -- nên dùng cột sinh: current_key = property_id khi chưa superseded, NULL khi đã.
  -- UNIQUE cho phép nhiều NULL nên chỉ bản ghi hiện hành bị ràng buộc.
  -- VIRTUAL (không phải STORED): MySQL cấm FK ON DELETE CASCADE trên base column
  -- của stored generated column. VIRTUAL vẫn đánh được UNIQUE index trong MySQL 8.
  current_key CHAR(36) CHARACTER SET ascii COLLATE ascii_bin
    GENERATED ALWAYS AS (IF(superseded_at IS NULL, property_id, NULL)) VIRTUAL,

  CONSTRAINT fk_coord_audit_property FOREIGN KEY (property_id)
    REFERENCES properties(id) ON DELETE CASCADE,
  CONSTRAINT fk_coord_audit_verifier FOREIGN KEY (verified_by)
    REFERENCES users(id) ON DELETE SET NULL,
  CONSTRAINT fk_coord_audit_recorder FOREIGN KEY (source_recorded_by)
    REFERENCES users(id) ON DELETE SET NULL,

  CONSTRAINT ck_coord_audit_revision CHECK (revision >= 1),
  CONSTRAINT ck_coord_audit_srid CHECK (srid = 4326),
  CONSTRAINT ck_coord_audit_lat CHECK (audited_latitude BETWEEN -90 AND 90),
  CONSTRAINT ck_coord_audit_lon CHECK (audited_longitude > -180 AND audited_longitude <= 180),
  CONSTRAINT ck_coord_audit_source CHECK (coordinate_source IN (
    'USER_PINNED','GEOCODED','IMPORTED','ADMIN_DEFAULT','UNKNOWN')),
  CONSTRAINT ck_coord_audit_accuracy CHECK (accuracy_level IN (
    'UNKNOWN','CITY','DISTRICT','WARD','STREET','BUILDING','PARCEL')),
  CONSTRAINT ck_coord_audit_verification CHECK (verification_status IN (
    'UNVERIFIED','PENDING_REVIEW','VERIFIED','REJECTED','STALE')),
  -- Accuracy cấp thửa chỉ hợp lệ khi đã xác minh độc lập.
  CONSTRAINT ck_coord_audit_parcel_requires_verification CHECK (
    accuracy_level <> 'PARCEL' OR verification_status = 'VERIFIED'),
  -- accuracy_meters chỉ có khi accuracy_level khác UNKNOWN.
  CONSTRAINT ck_coord_audit_accuracy_meters CHECK (
    (accuracy_level = 'UNKNOWN' AND accuracy_meters IS NULL)
    OR (accuracy_level <> 'UNKNOWN')),
  -- VERIFIED phải có phương pháp và thời điểm.
  CONSTRAINT ck_coord_audit_verified_fields CHECK (
    verification_status <> 'VERIFIED'
    OR (verification_method IS NOT NULL AND verified_at IS NOT NULL)),

  CONSTRAINT uq_coord_audit_current UNIQUE (current_key),
  -- Chặn hai request đồng thời cùng tính ra maxRevision()+1 giống nhau.
  CONSTRAINT uq_coord_audit_revision UNIQUE (property_id, revision)
);

CREATE INDEX idx_coord_audit_property ON property_coordinate_audit(property_id, revision);
CREATE INDEX idx_coord_audit_fingerprint ON property_coordinate_audit(coordinate_fingerprint);
CREATE INDEX idx_coord_audit_pending ON property_coordinate_audit(verification_status, created_at);
-- Index cho FK: MySQL yêu cầu index trên cột FK trước khi tạo constraint.
CREATE INDEX idx_coord_audit_verifier ON property_coordinate_audit(verified_by);
CREATE INDEX idx_coord_audit_recorder ON property_coordinate_audit(source_recorded_by);
