-- Durable advisor history, independent of broker/buyer messaging.
CREATE TABLE advisor_chat_conversations (
 id CHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
 user_id BIGINT NOT NULL,
 title VARCHAR(120) NOT NULL,
 revision BIGINT NOT NULL,
 checkpoint JSON NOT NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 CONSTRAINT fk_advisor_chat_user FOREIGN KEY (user_id) REFERENCES users(id),
 INDEX ix_advisor_chat_recent(user_id, updated_at DESC, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE advisor_chat_turns (
 conversation_id CHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 turn_number BIGINT NOT NULL,
 question TEXT NOT NULL,
 response JSON NOT NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 PRIMARY KEY(conversation_id, turn_number),
 CONSTRAINT fk_advisor_chat_turn FOREIGN KEY(conversation_id) REFERENCES advisor_chat_conversations(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
