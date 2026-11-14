package vn.smartprop.modules.report;

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
@Entity @Table(name="reports")
public class Report {
    public enum Status { OPEN, PROCESSING, RESOLVED, REJECTED }
    @Id @JdbcTypeCode(SqlTypes.CHAR) @Column(name="id",length=36,nullable=false) public String id;
    @Column(name="reporter_id",nullable=false) public Long reporterId;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name="property_id",length=36,nullable=false) public String propertyId;
    @Column(name="reason_code",length=50,nullable=false) public String reasonCode;
    @Column(name="description",columnDefinition="TEXT",nullable=false) public String description;
    @Column(name="contact_email",length=254) public String contactEmail;
    @Enumerated(EnumType.STRING) @JdbcTypeCode(SqlTypes.VARCHAR) @Column(name="status",length=30,nullable=false) public Status status;
    @Column(name="assigned_to") public Long assignedTo;
    @Column(name="resolved_by") public Long resolvedBy;
    @Column(name="resolution_note",columnDefinition="TEXT") public String resolutionNote;
    @Column(name="resolved_at") public Instant resolvedAt;
    @CreationTimestamp @Column(name="created_at",nullable=false) public Instant createdAt;
    @UpdateTimestamp @Column(name="updated_at",nullable=false) public Instant updatedAt;
}
