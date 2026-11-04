package vn.smartprop.modules.auth;

import jakarta.persistence.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;
import org.hibernate.type.SqlTypes;
import java.time.*;
import java.math.BigDecimal;
import com.fasterxml.jackson.databind.JsonNode;
import org.locationtech.jts.geom.Point;

/** Persistence mapping only. Foreign-key IDs do not imply cascade operations. */
@Entity @Table(name="password_reset_tokens")
public class PasswordResetToken {

    @Id @JdbcTypeCode(SqlTypes.CHAR) @Column(name="id",length=36,nullable=false) public String id;
    @Column(name="user_id",nullable=false) public Long userId;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name="token_hash",length=64,nullable=false) public String tokenHash;
    @Column(name="expires_at",nullable=false) public Instant expiresAt;
    @Column(name="consumed_at") public Instant consumedAt;
    @CreationTimestamp @Column(name="created_at",nullable=false) public Instant createdAt;
}
