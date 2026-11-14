package vn.smartprop.modules.moderation;

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
@Entity @Table(name="moderation_actions")
public class ModerationAction {

    @Id @JdbcTypeCode(SqlTypes.CHAR) @Column(name="id",length=36,nullable=false) public String id;
    @Column(name="admin_id",nullable=false) public Long adminId;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name="property_id",length=36) public String propertyId;
    @Column(name="user_id") public Long userId;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name="report_id",length=36) public String reportId;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name="flag_id",length=36) public String flagId;
    @Column(name="action",length=40,nullable=false) public String action;
    @Column(name="reason",columnDefinition="TEXT",nullable=false) public String reason;
    @Column(name="previous_status",length=30) public String previousStatus;
    @Column(name="new_status",length=30) public String newStatus;
    @CreationTimestamp @Column(name="created_at",nullable=false) public Instant createdAt;
}
