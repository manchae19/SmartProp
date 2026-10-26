-- Personal snapshots of standalone estimates; independent of property-linked AI tasks.
CREATE TABLE valuation_history (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
  user_id BIGINT NOT NULL,
  request_key CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  request_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  input_snapshot JSON NOT NULL,
  prediction_snapshot JSON NOT NULL,
  created_at DATETIME(6) NOT NULL,
  CONSTRAINT fk_history_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  UNIQUE KEY uq_history_retry (user_id, request_key),
  KEY ix_history_user_time (user_id, created_at, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
