CREATE TABLE users (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 email VARCHAR(254) COLLATE utf8mb4_unicode_ci NOT NULL,
 password_hash VARCHAR(100) NOT NULL,
 full_name VARCHAR(100) NOT NULL,
 phone VARCHAR(30), district VARCHAR(100), address VARCHAR(255),
 role VARCHAR(20) NOT NULL, status VARCHAR(20) NOT NULL,
 created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
 CONSTRAINT uq_users_email UNIQUE(email),
 CONSTRAINT ck_user_role CHECK (role IN ('BUYER','BROKER','ADMIN')),
 CONSTRAINT ck_user_status CHECK (status IN ('ACTIVE','LOCKED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE auth_sessions (
 id VARCHAR(36) NOT NULL PRIMARY KEY,
 user_id BIGINT NOT NULL,
 created_at DATETIME(6) NOT NULL,
 expires_at DATETIME(6) NOT NULL,
 revoked BOOLEAN NOT NULL DEFAULT FALSE,
 CONSTRAINT fk_session_user FOREIGN KEY(user_id) REFERENCES users(id),
 INDEX ix_sessions_user(user_id), INDEX ix_sessions_expiry(expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
