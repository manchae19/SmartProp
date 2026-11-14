-- Forward-only bridge for the canonical V1-V17 lineage.
-- Reuses develop-binh external table definitions without changing applied migrations.
-- Schema only: no imported records or changes to existing properties.

CREATE TABLE external_duplicate_groups (
  group_id VARCHAR(100) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  category VARCHAR(50) NOT NULL,
  district VARCHAR(100),
  listing_count INT NOT NULL DEFAULT 0,
  min_price DECIMAL(18,2),
  max_price DECIMAL(18,2),
  min_area DECIMAL(10,2),
  max_area DECIMAL(10,2),
  created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE external_listings (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  record_key VARCHAR(100) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  source VARCHAR(50) NOT NULL,
  source_listing_id VARCHAR(100),
  title VARCHAR(500) NOT NULL,
  detail_url TEXT NOT NULL,
  category VARCHAR(50) NOT NULL,
  transaction_type VARCHAR(30) NOT NULL,
  transaction_basis VARCHAR(100),
  price DECIMAL(18,2) NOT NULL,
  price_million DECIMAL(14,2) NOT NULL,
  area_sqm DECIMAL(10,2) NOT NULL,
  price_per_sqm_million DECIMAL(14,4),
  district VARCHAR(100),
  address_raw TEXT,
  quality_status VARCHAR(50) NOT NULL DEFAULT 'NEEDS_REVIEW',
  quality_issues JSON NOT NULL DEFAULT (JSON_ARRAY()),
  verification_status VARCHAR(50) NOT NULL DEFAULT 'UNVERIFIED',
  duplicate_group VARCHAR(100),
  is_duplicate BOOLEAN NOT NULL DEFAULT FALSE,
  is_protected_holdout BOOLEAN NOT NULL DEFAULT FALSE,
  collected_at DATETIME(6),
  raw_metadata JSON NOT NULL DEFAULT (JSON_OBJECT()),
  created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  updated_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  UNIQUE KEY uq_ext_record_key (record_key),
  KEY ix_ext_source (source),
  KEY ix_ext_quality_status (quality_status),
  KEY ix_ext_verification_status (verification_status),
  KEY ix_ext_district_category (district, category),
  KEY ix_ext_duplicate_group (duplicate_group)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
