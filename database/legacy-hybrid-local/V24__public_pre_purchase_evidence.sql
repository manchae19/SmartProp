-- Public pre-purchase evidence: planning documents and flood records.
--
-- Both tables hold only reviewed, publicly published material. Every row carries the
-- source URL it came from, so the listing page can show where a claim came from and
-- how wide its scope is. Nothing here is inferred from an address alone.

CREATE TABLE planning_publications (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
  -- What the document is: a publication notice, a consultation draft or an approval.
  event_type VARCHAR(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  project_name VARCHAR(255) NOT NULL,
  lot_code VARCHAR(60),
  land_parcel VARCHAR(120),
  ward VARCHAR(100),
  district VARCHAR(100),
  document_number VARCHAR(150),
  document_date DATE,
  publication_date DATE NOT NULL,
  -- How wide the evidence is: REGION, PROJECT or LAND_PARCEL.
  scope VARCHAR(20) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  source_url VARCHAR(1024) NOT NULL,
  source_title VARCHAR(500) NOT NULL,
  source_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
  checked_at DATE NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  CONSTRAINT ck_planning_event CHECK(event_type IN (
    'PUBLICATION_NOTICE','PUBLIC_CONSULTATION','APPROVAL_DECISION','OTHER')),
  CONSTRAINT ck_planning_scope CHECK(scope IN ('REGION','PROJECT','LAND_PARCEL')),
  CONSTRAINT ck_planning_url CHECK(source_url LIKE 'https://%')
);

CREATE INDEX idx_planning_project ON planning_publications(project_name);
CREATE INDEX idx_planning_lot ON planning_publications(lot_code);
CREATE INDEX idx_planning_ward ON planning_publications(ward, district);

CREATE TABLE flood_records (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
  -- A recorded flood point, a risk area, or a time-bound weather warning.
  record_type VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  location_text VARCHAR(500) NOT NULL,
  street VARCHAR(200),
  ward VARCHAR(100),
  district VARCHAR(100),
  -- How wide the evidence is: POINT, ROAD_SEGMENT, AREA or WARNING.
  scope VARCHAR(20) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  depth_note VARCHAR(200),
  event_date DATE,
  publication_date DATE NOT NULL,
  source_url VARCHAR(1024) NOT NULL,
  source_title VARCHAR(500) NOT NULL,
  source_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
  checked_at DATE NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  CONSTRAINT ck_flood_type CHECK(record_type IN (
    'RECORDED_POINT','RISK_AREA','WEATHER_WARNING','OTHER')),
  CONSTRAINT ck_flood_scope CHECK(scope IN ('POINT','ROAD_SEGMENT','AREA','WARNING')),
  CONSTRAINT ck_flood_url CHECK(source_url LIKE 'https://%')
);

CREATE INDEX idx_flood_street ON flood_records(street);
CREATE INDEX idx_flood_ward ON flood_records(ward, district);
