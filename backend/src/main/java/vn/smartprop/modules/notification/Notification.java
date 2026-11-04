package vn.smartprop.modules.notification;

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
@Entity @Table(name="notifications")
public class Notification {

    @Id @JdbcTypeCode(SqlTypes.CHAR) @Column(name="id",length=36,nullable=false) public String id;
    @Column(name="user_id",nullable=false) public Long userId;
    @Column(name="kind",length=50,nullable=false) public String kind;
    @Column(name="title",length=255,nullable=false) public String title;
    @Column(name="body",columnDefinition="TEXT",nullable=false) public String body;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name="property_id",length=36) public String propertyId;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name="report_id",length=36) public String reportId;
    @Column(name="read_at") public Instant readAt;
    @Column(name="dedupe_key",length=255) public String dedupeKey;
    @CreationTimestamp @Column(name="created_at",nullable=false) public Instant createdAt;
}
