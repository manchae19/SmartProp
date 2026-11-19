-- Step 19.4.1B: POI taxonomy enrichment (additive only).
-- Does NOT alter or rewrite points_of_interest, TiniX tables, Quality Gate data or Hybrid V1 objects.
-- Legacy rows keep their original `category`; the effective taxonomy lives in this companion table.
CREATE TABLE IF NOT EXISTS poi_taxonomy_enrichment (
  poi_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  taxonomy_version VARCHAR(32) NOT NULL,
  taxonomy_category VARCHAR(32) NOT NULL,
  taxonomy_subcategory VARCHAR(48) NULL,
  legacy_category VARCHAR(50) NULL,
  district_historical VARCHAR(48) NULL,
  location_basis VARCHAR(32) NOT NULL,
  location_confidence DECIMAL(3,2) NULL,
  review_status VARCHAR(40) NOT NULL,
  review_reasons JSON NULL,
  source_license VARCHAR(160) NOT NULL,
  attribution VARCHAR(255) NOT NULL,
  source_object_ref VARCHAR(80) NULL,
  collected_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  PRIMARY KEY (poi_id),
  KEY ix_poi_enrich_cat (taxonomy_category, review_status),
  KEY ix_poi_enrich_district (district_historical, taxonomy_category),
  CONSTRAINT fk_poi_enrich_poi FOREIGN KEY (poi_id) REFERENCES points_of_interest (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE OR REPLACE VIEW poi_effective_v1 AS
SELECT p.id AS poi_id,
       p.name,
       p.category AS legacy_category,
       e.taxonomy_category,
       e.taxonomy_subcategory,
       e.district_historical,
       e.location_basis,
       e.location_confidence,
       e.review_status,
       p.source_name,
       p.external_id,
       e.source_license,
       e.attribution,
       p.observed_at,
       ST_Latitude(p.location) AS latitude,
       ST_Longitude(p.location) AS longitude,
       p.location
FROM points_of_interest p
JOIN poi_taxonomy_enrichment e ON e.poi_id = p.id
WHERE e.review_status IN ('VALID', 'LEGACY_RECLASSIFIED', 'LEGACY_UNVERIFIED');
