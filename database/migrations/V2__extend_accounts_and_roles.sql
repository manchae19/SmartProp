-- SmartProp: MySQL 8.4.9 target; SQL also verified separately on available 8.0.43.
-- Defaults use UTC; enum/check values not shown in the PNG are proposed decisions.
-- Additive extension of V1. Existing Java Long user IDs and role remain authoritative.
SET time_zone = '+00:00';
ALTER TABLE users
 ADD COLUMN email_verified_at DATETIME(6),
 ADD COLUMN locked_at DATETIME(6),
 ADD COLUMN lock_reason TEXT,
 ADD COLUMN token_version INT NOT NULL DEFAULT 0,
 ADD COLUMN notification_preferences JSON,
 ADD COLUMN deleted_at DATETIME(6),
 ADD CONSTRAINT ck_user_token_version CHECK (token_version >= 0);
ALTER TABLE auth_sessions
 ADD COLUMN refresh_token_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 ADD COLUMN revoked_at DATETIME(6),
 ADD COLUMN last_used_at DATETIME(6),
 ADD COLUMN user_agent TEXT,
 ADD COLUMN updated_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
 ADD UNIQUE KEY uq_session_refresh (refresh_token_hash);
CREATE TABLE roles (
  code VARCHAR(20) NOT NULL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  CONSTRAINT ck_roles_code CHECK (code IN ('BUYER', 'BROKER', 'ADMIN'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE user_roles (
  user_id BIGINT NOT NULL,
  role_code VARCHAR(20) NOT NULL,
  granted_by BIGINT,
  created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  PRIMARY KEY (user_id, role_code),
  CONSTRAINT fk_user_roles_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_user_roles_role FOREIGN KEY (role_code) REFERENCES roles (code) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_user_roles_grantor FOREIGN KEY (granted_by) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE password_reset_tokens (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
  user_id BIGINT NOT NULL,
  token_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  expires_at DATETIME(6) NOT NULL,
  consumed_at DATETIME(6),
  created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  CONSTRAINT fk_password_reset_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  UNIQUE KEY uq_reset_hash (token_hash),
  KEY ix_reset_expiry (expires_at),
  CONSTRAINT ck_reset_expiry CHECK (expires_at > created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO roles(code,name) VALUES ('BUYER','Buyer/renter'),('BROKER','Owner/broker'),('ADMIN','Administrator');
INSERT INTO user_roles(user_id,role_code,created_at) SELECT id,role,created_at FROM users;
-- Compatibility bridge: current auth still reads users.role. Multi-role grants are deferred.
DELIMITER $$
CREATE TRIGGER users_role_insert AFTER INSERT ON users FOR EACH ROW
BEGIN
 INSERT INTO user_roles(user_id,role_code,created_at) VALUES(NEW.id,NEW.role,NEW.created_at);
END$$
CREATE TRIGGER users_role_update AFTER UPDATE ON users FOR EACH ROW
BEGIN
 IF OLD.role <> NEW.role THEN
  DELETE FROM user_roles WHERE user_id=NEW.id;
  INSERT INTO user_roles(user_id,role_code,created_at) VALUES(NEW.id,NEW.role,UTC_TIMESTAMP(6));
 END IF;
END$$
CREATE TRIGGER session_revoke_update BEFORE UPDATE ON auth_sessions FOR EACH ROW
BEGIN
 IF NEW.revoked=TRUE AND NEW.revoked_at IS NULL THEN SET NEW.revoked_at=UTC_TIMESTAMP(6); END IF;
 SET NEW.updated_at=UTC_TIMESTAMP(6);
END$$
DELIMITER ;
