-- SmartProp: MySQL 8.4.9 target; SQL also verified separately on available 8.0.43.
-- Defaults use UTC; enum/check values not shown in the PNG are proposed decisions.
CREATE TABLE amenity_analysis_results (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
  task_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  attempt_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  property_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  result_kind VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'AMENITY',
  declared_amenities_snapshot JSON NOT NULL DEFAULT (JSON_ARRAY()),
  comparison JSON NOT NULL DEFAULT (JSON_ARRAY()),
  latency_ms INT NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  CONSTRAINT fk_amenity_task_kind FOREIGN KEY (result_kind,task_id) REFERENCES ai_tasks (task_type,id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_amenity_attempt FOREIGN KEY (task_id,attempt_id) REFERENCES ai_task_attempts (task_id,id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_amenity_task_property FOREIGN KEY (task_id,property_id) REFERENCES ai_tasks (id,property_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  UNIQUE KEY uq_amenity_attempt (attempt_id),
  UNIQUE KEY uq_amenity_property (id,property_id),
  CONSTRAINT ck_amenity_kind CHECK (result_kind='AMENITY'),
  CONSTRAINT ck_amenity_latency CHECK (latency_ms >= 0),
  CONSTRAINT ck_amenity_snapshot_array CHECK (JSON_TYPE(declared_amenities_snapshot)='ARRAY'),
  CONSTRAINT ck_amenity_comparison_array CHECK (JSON_TYPE(comparison)='ARRAY')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE amenity_detections (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
  analysis_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  property_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  image_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  class_name VARCHAR(100) NOT NULL,
  confidence DOUBLE NOT NULL,
  bounding_box JSON,
  created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  CONSTRAINT fk_detection_analysis FOREIGN KEY (analysis_id,property_id) REFERENCES amenity_analysis_results (id,property_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_detection_image FOREIGN KEY (image_id,property_id) REFERENCES property_images (id,property_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT ck_detection_confidence CHECK (confidence BETWEEN 0 AND 1),
  KEY ix_detection_class (analysis_id,class_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

