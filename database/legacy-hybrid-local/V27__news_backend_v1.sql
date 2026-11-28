-- SmartProp News Backend V1 — nguồn tin, bài viết, lịch sử đồng bộ.
--
-- Nguyên tắc:
--   * Chỉ lưu metadata + summary ngắn. KHÔNG lưu toàn văn bài báo.
--   * Không lưu ảnh báo chí. Ảnh do Frontend chọn theo newsImagePolicy.js.
--   * Nguồn mới mặc định PENDING_REVIEW + enabled=0. Không tự động thu thập.
--   * published_at là ngày publisher đăng; fetched_at là lúc hệ thống tải.
--     Không bao giờ dùng fetched_at thay cho published_at.

CREATE TABLE news_sources (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  source_code VARCHAR(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  name VARCHAR(200) NOT NULL,
  publisher VARCHAR(200) NOT NULL,
  website_url VARCHAR(500) NOT NULL,
  feed_url VARCHAR(500) NOT NULL,

  -- Phân loại mặc định khi nguồn không khai báo rõ.
  default_category VARCHAR(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'MARKET',
  default_region VARCHAR(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'UNKNOWN',

  -- Quyền sử dụng: tách khỏi trạng thái bật/tắt.
  rights_review_status VARCHAR(20) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'PENDING_REVIEW',
  rights_reference VARCHAR(500) DEFAULT NULL,
  rights_checked_at DATETIME(6) DEFAULT NULL,
  usage_restrictions VARCHAR(1000) DEFAULT NULL,

  -- Quyền theo từng loại nội dung. Mặc định: cho phép summary, KHÔNG cho ảnh.
  allow_summary TINYINT(1) NOT NULL DEFAULT 1,
  allow_images TINYINT(1) NOT NULL DEFAULT 0,

  enabled TINYINT(1) NOT NULL DEFAULT 0,
  fetch_interval_minutes SMALLINT UNSIGNED NOT NULL DEFAULT 30,

  -- Lease chống hai job fetch cùng nguồn. Token do job giữ; hết hạn thì job khác claim.
  sync_lease_token CHAR(36) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,
  sync_lease_until DATETIME(6) DEFAULT NULL,

  -- Thời điểm được phép fetch tiếp. Thực thi Retry-After và backoff.
  next_fetch_at DATETIME(6) DEFAULT NULL,

  -- Tăng mỗi lần admin sửa nguồn. Job đang chạy phát hiện thay đổi và bỏ kết quả.
  source_revision INT NOT NULL DEFAULT 1,
  consecutive_failures SMALLINT UNSIGNED NOT NULL DEFAULT 0,

  last_attempt_at DATETIME(6) DEFAULT NULL,
  last_success_at DATETIME(6) DEFAULT NULL,
  last_error VARCHAR(500) DEFAULT NULL,

  -- Conditional GET.
  http_etag VARCHAR(200) DEFAULT NULL,
  http_last_modified VARCHAR(100) DEFAULT NULL,

  created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  updated_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),

  PRIMARY KEY (id),
  UNIQUE KEY uq_news_sources_code (source_code),
  UNIQUE KEY uq_news_sources_feed (feed_url),
  KEY idx_news_sources_schedule (enabled, rights_review_status, last_attempt_at),
  KEY idx_news_sources_due (enabled, rights_review_status, next_fetch_at),
  KEY idx_news_sources_lease (sync_lease_until),

  CONSTRAINT ck_news_sources_rights CHECK (
    rights_review_status IN ('PENDING_REVIEW','APPROVED','REJECTED')),
  CONSTRAINT ck_news_sources_interval CHECK (
    fetch_interval_minutes BETWEEN 5 AND 1440),
  CONSTRAINT ck_news_sources_category CHECK (
    default_category IN ('MARKET','PLANNING','LEGAL','INFRASTRUCTURE','PROJECTS','RESIDENTIAL','COMMERCIAL','OTHER')),
  CONSTRAINT ck_news_sources_region CHECK (
    default_region IN ('DA_NANG','CENTRAL','VIETNAM','UNKNOWN'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE news_articles (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  source_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,

  -- Danh tính bài viết. external_id là GUID từ feed; canonical_url_hash là SHA-256
  -- của canonical_url đã chuẩn hoá. Cả hai đều unique theo nguồn.
  external_id VARCHAR(500) DEFAULT NULL,
  canonical_url VARCHAR(1000) NOT NULL,
  canonical_url_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,

  title VARCHAR(500) NOT NULL,
  summary VARCHAR(2000) DEFAULT NULL,

  category VARCHAR(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  region VARCHAR(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'UNKNOWN',
  location_tags VARCHAR(500) DEFAULT NULL,

  -- published_at NULL nghĩa là feed không cung cấp ngày đăng. Không suy đoán.
  published_at DATETIME(6) DEFAULT NULL,
  fetched_at DATETIME(6) NOT NULL,
  first_seen_at DATETIME(6) NOT NULL,
  last_seen_at DATETIME(6) NOT NULL,

  content_fingerprint CHAR(64) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,

  -- Admin kiểm soát hiển thị. Mặc định VISIBLE; admin có thể HIDDEN.
  publication_status VARCHAR(20) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'VISIBLE',
  featured TINYINT(1) NOT NULL DEFAULT 0,

  created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  updated_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),

  PRIMARY KEY (id),
  KEY idx_news_articles_feed (source_id, published_at),
  KEY idx_news_articles_public (publication_status, published_at),
  KEY idx_news_articles_category (category, published_at),
  KEY idx_news_articles_region (region, published_at),
  KEY idx_news_articles_featured (featured, publication_status, published_at),
  KEY idx_news_articles_url_hash (canonical_url_hash),

  -- Chống trùng ở tầng DB: cùng nguồn + cùng URL không thể có hai bản ghi.
  UNIQUE KEY uq_news_articles_source_url (source_id, canonical_url_hash),
  -- GUID trùng trong cùng nguồn cũng bị chặn. NULL được phép nhiều.
  UNIQUE KEY uq_news_articles_source_external (source_id, external_id),

  CONSTRAINT fk_news_articles_source FOREIGN KEY (source_id)
    REFERENCES news_sources (id) ON DELETE CASCADE,
  CONSTRAINT ck_news_articles_status CHECK (
    publication_status IN ('VISIBLE','HIDDEN')),
  CONSTRAINT ck_news_articles_category CHECK (
    category IN ('MARKET','PLANNING','LEGAL','INFRASTRUCTURE','PROJECTS','RESIDENTIAL','COMMERCIAL','OTHER')),
  CONSTRAINT ck_news_articles_region CHECK (
    region IN ('DA_NANG','CENTRAL','VIETNAM','UNKNOWN'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE news_ingestion_runs (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  source_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,

  started_at DATETIME(6) NOT NULL,
  finished_at DATETIME(6) DEFAULT NULL,
  status VARCHAR(20) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,

  http_status SMALLINT DEFAULT NULL,
  items_received INT NOT NULL DEFAULT 0,
  items_inserted INT NOT NULL DEFAULT 0,
  items_updated INT NOT NULL DEFAULT 0,
  items_duplicate INT NOT NULL DEFAULT 0,
  items_rejected INT NOT NULL DEFAULT 0,

  error_code VARCHAR(60) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,
  error_message VARCHAR(500) DEFAULT NULL,
  duration_ms INT DEFAULT NULL,

  PRIMARY KEY (id),
  KEY idx_news_runs_source (source_id, started_at),
  KEY idx_news_runs_status (status, started_at),

  CONSTRAINT fk_news_runs_source FOREIGN KEY (source_id)
    REFERENCES news_sources (id) ON DELETE CASCADE,
  CONSTRAINT ck_news_runs_status CHECK (
    status IN ('RUNNING','SUCCESS','PARTIAL_SUCCESS','FAILED','NOT_MODIFIED','SKIPPED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
