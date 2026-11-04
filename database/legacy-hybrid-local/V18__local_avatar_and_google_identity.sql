-- LOCAL LEGACY LINEAGE ONLY. Forward-only completion after original crawler V14.
-- Copied DDL from standard V15__profile_avatar_and_google_identity.sql; never run with standard migrations.
-- Additive only. Roll out separately after V14; never grants roles to existing accounts.
CREATE TABLE user_avatars (
 user_id BIGINT NOT NULL PRIMARY KEY,
 revision CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 storage_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 mime_type VARCHAR(40) NOT NULL,
 sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 width INT NOT NULL, height INT NOT NULL,
 updated_at DATETIME(6) NOT NULL,
 CONSTRAINT fk_avatar_owner FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,
 UNIQUE KEY uq_avatar_storage (storage_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE user_external_identities (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 user_id BIGINT NOT NULL,
 provider VARCHAR(20) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 subject_id VARCHAR(255) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 created_at DATETIME(6) NOT NULL,
 CONSTRAINT fk_external_identity_owner FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,
 CONSTRAINT ck_external_provider CHECK (provider='GOOGLE'),
 UNIQUE KEY uq_external_subject (provider,subject_id),
 UNIQUE KEY uq_external_user_provider (user_id,provider)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
