CREATE TABLE conversations (
 id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
 property_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 inquirer_id BIGINT NOT NULL,
 broker_id BIGINT NOT NULL,
 created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
 updated_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
 UNIQUE KEY uq_conversation_inquiry(property_id,inquirer_id,broker_id),
 CONSTRAINT ck_conversation_parties CHECK(inquirer_id<>broker_id),
 CONSTRAINT fk_conversation_property FOREIGN KEY(property_id) REFERENCES properties(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 CONSTRAINT fk_conversation_inquirer FOREIGN KEY(inquirer_id) REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 CONSTRAINT fk_conversation_broker FOREIGN KEY(broker_id) REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE conversation_participants (
 conversation_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 user_id BIGINT NOT NULL,
 last_read_sequence BIGINT NOT NULL DEFAULT 0,
 PRIMARY KEY(conversation_id,user_id),
 KEY ix_participant_inbox(user_id,conversation_id),
 CONSTRAINT fk_participant_conversation FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 CONSTRAINT fk_participant_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 CONSTRAINT ck_participant_read CHECK(last_read_sequence>=0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE messages (
 sequence BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 conversation_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 sender_id BIGINT NOT NULL,
 client_message_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 body VARCHAR(4000) NOT NULL,
 created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
 UNIQUE KEY uq_message_id(id),
 UNIQUE KEY uq_message_retry(conversation_id,sender_id,client_message_id),
 KEY ix_message_cursor(conversation_id,sequence),
 CONSTRAINT fk_message_participant FOREIGN KEY(conversation_id,sender_id) REFERENCES conversation_participants(conversation_id,user_id) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
