-- Staging-first schema for automatic property image duplicate scans.
-- Do not apply to production 3306 until the integration and browser E2E are approved.
CREATE TABLE property_image_scan (
    id CHAR(36) NOT NULL,
    property_id CHAR(36) NOT NULL,
    property_image_id CHAR(36) NOT NULL,
    scan_status VARCHAR(24) NOT NULL,
    classification VARCHAR(24) NULL,
    similarity DECIMAL(5,4) NULL,
    matched_property_id CHAR(36) NULL,
    matched_property_image_id CHAR(36) NULL,
    matched_listing_code VARCHAR(32) NULL,
    detection_method VARCHAR(80) NULL,
    evidence JSON NOT NULL,
    algorithm_version VARCHAR(32) NOT NULL,
    error_code VARCHAR(64) NULL,
    scanned_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    UNIQUE KEY uq_property_image_scan_image (property_image_id),
    KEY ix_property_image_scan_property (property_id, scan_status),
    KEY ix_property_image_scan_status (scan_status, classification)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
