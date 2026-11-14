-- YOLOv8 property image object analysis.
--
-- Separate from property_image_scan on purpose: duplicate detection is one row
-- per image, while object analysis keeps one row per image *per model version*
-- so a model upgrade adds a row instead of destroying the previous verdict.
--
-- Additive only: no ALTER of existing tables, no DML, no FK cascade. The scan
-- tables are evidence logs; a cascade delete would silently destroy history.
--
-- Staging first. Do not apply to production 3306 until the integration and
-- browser E2E are approved.

CREATE TABLE property_image_analysis (
    id CHAR(36) NOT NULL,
    property_id CHAR(36) NOT NULL,
    property_image_id CHAR(36) NOT NULL,
    analysis_status VARCHAR(24) NOT NULL,
    algorithm_version VARCHAR(32) NOT NULL,
    model_version VARCHAR(64) NOT NULL,
    detection_count INT NOT NULL DEFAULT 0,
    detections JSON NOT NULL,
    counts_by_label JSON NOT NULL,
    document_hint JSON NULL,
    document_like BOOLEAN NOT NULL DEFAULT FALSE,
    image_width INT NULL,
    image_height INT NULL,
    image_format VARCHAR(16) NULL,
    image_sha256 CHAR(64) NULL,
    inference_ms DECIMAL(10,2) NULL,
    error_code VARCHAR(64) NULL,
    attempt_count INT NOT NULL DEFAULT 0,
    analyzed_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    UNIQUE KEY uq_image_analysis_version (property_image_id, model_version),
    KEY ix_image_analysis_property (property_id, analysis_status),
    KEY ix_image_analysis_status (analysis_status, detection_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
