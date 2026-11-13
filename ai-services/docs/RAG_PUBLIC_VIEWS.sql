-- SmartProp RAG public views (staging first; do not run on production without approval).
-- Replace smartprop_staging with the target database. The view owner must be an
-- administrative account; the RAG account receives SELECT on the three views only.
--
-- SQL SECURITY DEFINER is intentional: the RAG reader never receives SELECT on
-- properties, property_images, projects, property_legal_documents or private tables.

CREATE OR REPLACE SQL SECURITY DEFINER VIEW rag_public_properties AS
SELECT
    p.id,
    p.listing_code,
    p.title,
    p.description,
    p.price,
    p.area_sqm,
    p.property_type,
    p.transaction_type,
    p.district,
    p.ward,
    p.address,
    p.city,
    p.bedrooms,
    p.bathrooms,
    p.floor,
    p.direction,
    p.declared_amenities,
    p.project_id,
    p.status,
    p.deleted_at,
    p.expires_at,
    p.currency,
    p.price_unit,
    p.location,
    pr.name AS project_name,
    pr.developer AS project_developer,
    pr.address AS project_address,
    pr.handover_year AS project_handover_year,
    pr.scale AS project_scale,
    pr.amenities AS project_amenities
FROM properties p
LEFT JOIN projects pr
       ON pr.id = p.project_id
      AND pr.deleted_at IS NULL
WHERE p.status = 'PUBLISHED'
  AND p.deleted_at IS NULL
  AND (p.expires_at IS NULL OR p.expires_at > UTC_TIMESTAMP(6))
  AND p.transaction_type = 'SALE'
  AND p.currency = 'VND'
  AND p.price_unit = 'TOTAL'
  AND p.price > 0
  AND p.area_sqm > 0;

CREATE OR REPLACE SQL SECURITY DEFINER VIEW rag_public_property_images AS
SELECT
    i.property_id,
    i.id,
    i.sort_order,
    i.is_cover,
    i.mime_type,
    i.storage_provider,
    i.cloudinary_secure_url,
    i.deleted_at
FROM property_images i
JOIN rag_public_properties p ON p.id = i.property_id
WHERE i.deleted_at IS NULL;

CREATE OR REPLACE SQL SECURITY DEFINER VIEW rag_public_legal_status AS
SELECT
    d.property_id,
    d.status,
    d.deleted_at
FROM property_legal_documents d
JOIN rag_public_properties p ON p.id = d.property_id
WHERE d.deleted_at IS NULL;

-- Staging-only reader (replace password via secret store; never commit it):
-- CREATE USER 'rag_view_reader'@'127.0.0.1' IDENTIFIED BY '<staging-secret>';
-- GRANT SELECT ON smartprop_staging.rag_public_properties TO 'rag_view_reader'@'127.0.0.1';
-- GRANT SELECT ON smartprop_staging.rag_public_property_images TO 'rag_view_reader'@'127.0.0.1';
-- GRANT SELECT ON smartprop_staging.rag_public_legal_status TO 'rag_view_reader'@'127.0.0.1';
-- FLUSH PRIVILEGES;
