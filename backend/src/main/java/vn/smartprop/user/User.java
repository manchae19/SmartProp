package vn.smartprop.user;
import jakarta.persistence.*;
import java.time.Instant;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import com.fasterxml.jackson.databind.JsonNode;
@Entity @Table(name="users")
public class User {
    public enum Role { BUYER, BROKER, ADMIN }
    public enum Status { ACTIVE, LOCKED }
    @Id @GeneratedValue(strategy=GenerationType.IDENTITY) public Long id;
    @Column(nullable=false,unique=true,length=254) public String email;
    @Column(nullable=false,length=100) public String passwordHash;
    @Column(nullable=false,length=100) public String fullName;
    @Column(length=30) public String phone;
    @Column(length=100) public String district;
    @Column(length=255) public String address;
    @Enumerated(EnumType.STRING) @JdbcTypeCode(SqlTypes.VARCHAR) @Column(nullable=false,length=20) public Role role;
    @Enumerated(EnumType.STRING) @JdbcTypeCode(SqlTypes.VARCHAR) @Column(nullable=false,length=20) public Status status;
    @Column(nullable=false) public Instant createdAt;
    @Column(nullable=false) public Instant updatedAt;
    @Column(name="email_verified_at") public Instant emailVerifiedAt;
    @Column(name="locked_at") public Instant lockedAt;
    @Column(name="lock_reason",columnDefinition="TEXT") public String lockReason;
    @Column(name="token_version",nullable=false) public int tokenVersion;
    @JdbcTypeCode(SqlTypes.JSON) @Column(name="notification_preferences",columnDefinition="JSON") public JsonNode notificationPreferences;
    @Column(name="deleted_at") public Instant deletedAt;
    @PrePersist void created() { createdAt=updatedAt=Instant.now(); }
    @PreUpdate void updated() { updatedAt=Instant.now(); }
}
