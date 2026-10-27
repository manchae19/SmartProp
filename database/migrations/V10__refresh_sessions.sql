ALTER TABLE auth_sessions ADD COLUMN issued_token_version INT NULL,
 ADD CONSTRAINT ck_session_issued_version CHECK (issued_token_version IS NULL OR issued_token_version>=0);
CREATE TABLE auth_refresh_token_history (
 id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
 session_id VARCHAR(36) NOT NULL,
 token_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 used_at DATETIME(6) NOT NULL,
 expires_at DATETIME(6) NOT NULL,
 UNIQUE KEY uq_refresh_history_hash(token_hash),
 KEY ix_refresh_history_session(session_id,expires_at),
 CONSTRAINT fk_refresh_history_session FOREIGN KEY(session_id) REFERENCES auth_sessions(id) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
