CREATE TABLE user_advisor_preferences (
    user_id BIGINT NOT NULL PRIMARY KEY,
    preferences JSON NOT NULL,
    updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_advisor_preferences_user FOREIGN KEY (user_id) REFERENCES users(id)
);
