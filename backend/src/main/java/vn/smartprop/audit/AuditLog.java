package vn.smartprop.audit;

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
@Entity @Table(name="audit_logs")
public class AuditLog {
    public enum ActorType { USER, SYSTEM }
    @Id @JdbcTypeCode(SqlTypes.CHAR) @Column(name="id",length=36,nullable=false) public String id;
    @Column(name="actor_id") public Long actorId;
    @Enumerated(EnumType.STRING) @JdbcTypeCode(SqlTypes.VARCHAR) @Column(name="actor_type",length=15,nullable=false) public ActorType actorType;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name="request_id",length=36) public String requestId;
    @Column(name="action",length=100,nullable=false) public String action;
    @Column(name="entity_type",length=50,nullable=false) public String entityType;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name="entity_id",length=36) public String entityId;
    @Column(name="entity_numeric_id") public Long entityNumericId;
    @JdbcTypeCode(SqlTypes.JSON) @Column(name="old_values",columnDefinition="JSON") public JsonNode oldValues;
    @JdbcTypeCode(SqlTypes.JSON) @Column(name="new_values",columnDefinition="JSON") public JsonNode newValues;
    @Column(name="ip_address",length=45) public String ipAddress;
    @CreationTimestamp @Column(name="created_at",nullable=false) public Instant createdAt;
}
