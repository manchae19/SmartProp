-- SmartProp: MySQL 8.4.9 target; SQL also verified separately on available 8.0.43.
-- Defaults use UTC; enum/check values not shown in the PNG are proposed decisions.
CREATE TABLE data_sources (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  source_type VARCHAR(30) NOT NULL,
  base_url TEXT,
  license_basis TEXT NOT NULL,
  permitted_use TEXT NOT NULL,
  retention_policy TEXT,
  reviewed_at DATETIME(6),
  created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  updated_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE dataset_versions (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  version VARCHAR(50) NOT NULL,
  status VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'DRAFT',
  window_start DATE NOT NULL,
  train_end DATE NOT NULL,
  validation_end DATE NOT NULL,
  window_end DATE NOT NULL,
  manifest_key TEXT,
  checksum CHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
  preprocessing_version VARCHAR(100) NOT NULL,
  validation_report JSON NOT NULL DEFAULT (JSON_OBJECT()),
  created_by BIGINT NOT NULL,
  frozen_at DATETIME(6),
  created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  CONSTRAINT fk_dataset_creator FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  UNIQUE KEY uq_dataset_version (name,version),
  CONSTRAINT ck_dataset_status CHECK (status IN ('DRAFT', 'VALIDATED', 'FROZEN', 'RETIRED')),
  CONSTRAINT ck_dataset_window CHECK (window_start <= train_end AND train_end < validation_end AND validation_end < window_end)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE dataset_records (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
  source_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  source_record_key VARCHAR(255) NOT NULL,
  source_url TEXT,
  observed_at DATETIME(6) NOT NULL,
  collected_at DATETIME(6) NOT NULL,
  country_code CHAR(2) NOT NULL DEFAULT 'VN',
  city VARCHAR(100) NOT NULL,
  target_type VARCHAR(30) NOT NULL,
  normalized_price_vnd DECIMAL(18,2),
  transaction_type VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  price_unit VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  features JSON NOT NULL DEFAULT (JSON_OBJECT()),
  raw_storage_key TEXT,
  quality_status VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'PENDING',
  rejection_reason TEXT,
  entity_group_key VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  content_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  CONSTRAINT fk_record_source FOREIGN KEY (source_id) REFERENCES data_sources (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  UNIQUE KEY uq_record_source (source_id,source_record_key,content_hash),
  UNIQUE KEY uq_record_group (id,entity_group_key),
  CONSTRAINT ck_record_price CHECK (normalized_price_vnd IS NULL OR normalized_price_vnd >= 0),
  CONSTRAINT ck_record_transaction CHECK (transaction_type IN ('SALE', 'RENT')),
  CONSTRAINT ck_record_price_unit CHECK (price_unit IN ('TOTAL', 'PER_MONTH', 'PER_YEAR', 'PER_DAY')),
  CONSTRAINT ck_record_quality CHECK (quality_status IN ('PENDING', 'ACCEPTED', 'REJECTED', 'DUPLICATE')),
  KEY ix_record_time (city,quality_status,observed_at),
  KEY ix_record_group (entity_group_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE dataset_memberships (
  dataset_version_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  record_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  entity_group_key VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  split VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  PRIMARY KEY (dataset_version_id,record_id),
  CONSTRAINT fk_membership_version FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_membership_record FOREIGN KEY (record_id,entity_group_key) REFERENCES dataset_records (id,entity_group_key) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT ck_membership_split CHECK (split IN ('TRAIN', 'VALIDATION', 'TEST')),
  KEY ix_membership_split (dataset_version_id,split,entity_group_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE model_versions (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
  kind VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  name VARCHAR(100) NOT NULL,
  version VARCHAR(50) NOT NULL,
  status VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'DRAFT',
  dataset_version_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin,
  artifact_key TEXT NOT NULL,
  artifact_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  metrics JSON NOT NULL DEFAULT (JSON_OBJECT()),
  feature_schema JSON NOT NULL DEFAULT (JSON_OBJECT()),
  runtime_metadata JSON NOT NULL DEFAULT (JSON_OBJECT()),
  approved_by BIGINT,
  approved_at DATETIME(6),
  created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  CONSTRAINT fk_model_dataset FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_model_approver FOREIGN KEY (approved_by) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  UNIQUE KEY uq_model_name_version (kind,name,version),
  UNIQUE KEY uq_model_kind_id (kind,id),
  CONSTRAINT ck_model_kind CHECK (kind IN ('VALUATION', 'SIMILARITY', 'AMENITY')),
  CONSTRAINT ck_model_status CHECK (status IN ('DRAFT', 'VALIDATED', 'APPROVED', 'RETIRED')),
  CONSTRAINT ck_model_approval CHECK (status <> 'APPROVED' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE ai_config_versions (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
  kind VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  version VARCHAR(50) NOT NULL,
  parameters JSON NOT NULL DEFAULT (JSON_OBJECT()),
  approved_by BIGINT NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  CONSTRAINT fk_config_approver FOREIGN KEY (approved_by) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  UNIQUE KEY uq_config_kind_version (kind,version),
  UNIQUE KEY uq_config_kind_id (kind,id),
  CONSTRAINT ck_config_kind CHECK (kind IN ('VALUATION', 'SIMILARITY', 'AMENITY'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE ai_deployments (
  kind VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  model_version_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  config_version_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  updated_by BIGINT NOT NULL,
  updated_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  PRIMARY KEY (kind),
  CONSTRAINT fk_deployment_model FOREIGN KEY (kind,model_version_id) REFERENCES model_versions (kind,id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_deployment_config FOREIGN KEY (kind,config_version_id) REFERENCES ai_config_versions (kind,id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_deployment_updater FOREIGN KEY (updated_by) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT ck_deployment_kind CHECK (kind IN ('VALUATION', 'SIMILARITY', 'AMENITY'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

