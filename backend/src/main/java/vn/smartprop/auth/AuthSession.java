package vn.smartprop.auth;
import jakarta.persistence.*;
import java.time.Instant;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
@Entity @Table(name="auth_sessions")
public class AuthSession {
    @Id @Column(length=36) public String id;
    @Column(nullable=false) public Long userId;
    @Column(nullable=false) public Instant createdAt;
    @Column(nullable=false) public Instant expiresAt;
    @Column(nullable=false) public boolean revoked;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name="refresh_token_hash",length=64) public String refreshTokenHash;
    @Column(name="revoked_at",insertable=false,updatable=false) public Instant revokedAt;
    @Column(name="last_used_at") public Instant lastUsedAt;
    @Column(name="user_agent",columnDefinition="TEXT") public String userAgent;
    @Column(name="updated_at",nullable=false,insertable=false,updatable=false) public Instant updatedAt;
}
