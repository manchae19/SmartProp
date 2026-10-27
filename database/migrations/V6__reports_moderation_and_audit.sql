-- SmartProp: MySQL 8.4.9 target; SQL also verified separately on available 8.0.43.
-- Defaults use UTC; enum/check values not shown in the PNG are proposed decisions.
CREATE TABLE reports (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
  reporter_id BIGINT NOT NULL,
  property_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  reason_code VARCHAR(50) NOT NULL,
  description TEXT NOT NULL,
  contact_email VARCHAR(254),
  status VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'OPEN',
  assigned_to BIGINT,
  resolved_by BIGINT,
  resolution_note TEXT,
  resolved_at DATETIME(6),
  created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  updated_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  CONSTRAINT fk_report_user FOREIGN KEY (reporter_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_report_property FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_report_assignee FOREIGN KEY (assigned_to) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_report_resolver FOREIGN KEY (resolved_by) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT ck_report_status CHECK (status IN ('OPEN', 'PROCESSING', 'RESOLVED', 'REJECTED')),
  CONSTRAINT ck_report_resolved CHECK (status NOT IN ('RESOLVED','REJECTED') OR (resolved_by IS NOT NULL AND resolved_at IS NOT NULL AND resolution_note IS NOT NULL)),
  KEY ix_report_queue (status,created_at),
  KEY ix_report_owner (reporter_id,created_at),
  KEY ix_report_property (property_id,status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE report_attachments (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
  report_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  storage_key VARCHAR(512) NOT NULL,
  mime_type VARCHAR(50) NOT NULL,
  byte_size BIGINT NOT NULL,
  sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
  created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  CONSTRAINT fk_attachment_report FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT ck_attachment_size CHECK (byte_size > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE audit_logs (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
  actor_id BIGINT,
  actor_type VARCHAR(15) NOT NULL,
  request_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin,
  action VARCHAR(100) NOT NULL,
  entity_type VARCHAR(50) NOT NULL,
  entity_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin,
  entity_numeric_id BIGINT,
  old_values JSON,
  new_values JSON,
  ip_address VARCHAR(45) CHARACTER SET ascii COLLATE ascii_bin,
  created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  CONSTRAINT fk_audit_actor FOREIGN KEY (actor_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT ck_audit_actor_type CHECK (actor_type IN ('USER', 'SYSTEM')),
  KEY ix_audit_entity (entity_type,entity_id,created_at),
  KEY ix_audit_actor (actor_id,created_at),
  KEY ix_audit_request (request_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE notifications (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
  user_id BIGINT NOT NULL,
  kind VARCHAR(50) NOT NULL,
  title VARCHAR(255) NOT NULL,
  body TEXT NOT NULL,
  property_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin,
  report_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin,
  read_at DATETIME(6),
  dedupe_key VARCHAR(255) CHARACTER SET ascii COLLATE ascii_bin,
  created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  CONSTRAINT fk_notification_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_notification_property FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_notification_report FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  UNIQUE KEY uq_notification_dedupe (user_id,dedupe_key),
  KEY ix_notification_inbox (user_id,read_at,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE review_flags (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
  property_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  ai_task_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin,
  flag_type VARCHAR(50) NOT NULL,
  severity VARCHAR(20) NOT NULL,
  status VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'OPEN',
  evidence JSON NOT NULL DEFAULT (JSON_OBJECT()),
  dedupe_key VARCHAR(255) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  reviewed_by BIGINT,
  reviewed_at DATETIME(6),
  created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  updated_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  CONSTRAINT fk_flag_property FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_flag_task_property FOREIGN KEY (ai_task_id,property_id) REFERENCES ai_tasks (id,property_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_flag_reviewer FOREIGN KEY (reviewed_by) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  UNIQUE KEY uq_flag_dedupe (dedupe_key),
  CONSTRAINT ck_flag_status CHECK (status IN ('OPEN', 'REVIEWED', 'DISMISSED')),
  CONSTRAINT ck_flag_severity CHECK (severity IN ('INFO', 'LOW', 'MEDIUM', 'HIGH')),
  KEY ix_flag_queue (status,severity,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE moderation_actions (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
  admin_id BIGINT NOT NULL,
  property_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin,
  user_id BIGINT,
  report_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin,
  flag_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin,
  action VARCHAR(40) NOT NULL,
  reason TEXT NOT NULL,
  previous_status VARCHAR(30),
  new_status VARCHAR(30),
  created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  CONSTRAINT fk_moderation_admin FOREIGN KEY (admin_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_moderation_property FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_moderation_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_moderation_report FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_moderation_flag FOREIGN KEY (flag_id) REFERENCES review_flags (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT ck_moderation_target CHECK (property_id IS NOT NULL OR user_id IS NOT NULL OR report_id IS NOT NULL OR flag_id IS NOT NULL),
  KEY ix_moderation_property (property_id,created_at),
  KEY ix_moderation_report (report_id,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

