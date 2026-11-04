-- LOCAL LEGACY LINEAGE ONLY. Forward-only completion after original crawler V14.
-- Copied DDL from standard V13__broker_applications.sql; never run with standard migrations.
-- Additive, opt-in rollout. Never grants roles or changes existing accounts.
CREATE TABLE broker_applications (
 id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
 user_id BIGINT NOT NULL,
 applicant_type VARCHAR(20) NOT NULL,
 display_name VARCHAR(150) NOT NULL,
 contact_phone VARCHAR(30) NOT NULL,
 operating_area VARCHAR(200) NOT NULL,
 request_message VARCHAR(2000) NOT NULL,
 responsibility_accepted BOOLEAN NOT NULL,
 consented_at DATETIME(6) NOT NULL,
 status VARCHAR(30) NOT NULL,
 content_version INT NOT NULL DEFAULT 1,
 reviewed_by BIGINT,
 review_action VARCHAR(30),
 review_reason VARCHAR(2000),
 reviewed_at DATETIME(6),
 created_at DATETIME(6) NOT NULL,
 updated_at DATETIME(6) NOT NULL,
 CONSTRAINT uq_broker_application_user UNIQUE(user_id),
 CONSTRAINT fk_broker_application_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE RESTRICT,
 CONSTRAINT fk_broker_application_reviewer FOREIGN KEY(reviewed_by) REFERENCES users(id) ON DELETE RESTRICT,
 CONSTRAINT ck_broker_applicant_type CHECK (applicant_type IN ('OWNER','AGENT')),
 CONSTRAINT ck_broker_application_status CHECK (status IN ('PENDING','APPROVED','REJECTED','NEEDS_INFORMATION','SUSPENDED')),
 CONSTRAINT ck_broker_application_version CHECK (content_version > 0),
 CONSTRAINT ck_broker_application_consent CHECK (responsibility_accepted = TRUE),
 CONSTRAINT ck_broker_review_action CHECK (review_action IS NULL OR review_action IN ('APPROVE','REJECT','REQUEST_INFORMATION','SUSPEND')),
 KEY ix_broker_application_queue(status,updated_at,id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
