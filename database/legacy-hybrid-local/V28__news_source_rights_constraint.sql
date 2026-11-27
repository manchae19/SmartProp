-- Forward-only rights invariant. Does not repair or approve existing sources.
-- Deployment must preflight existing rows and stop if any APPROVED reference is invalid.
ALTER TABLE news_sources
  ADD CONSTRAINT ck_news_sources_approved_reference CHECK (
    rights_review_status <> 'APPROVED'
    OR (rights_reference IS NOT NULL AND REGEXP_LIKE(rights_reference, '[^[:space:]]'))
  );
