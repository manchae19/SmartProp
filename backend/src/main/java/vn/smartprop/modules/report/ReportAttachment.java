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
@Entity @Table(name="report_attachments")
public class ReportAttachment {

    @Id @JdbcTypeCode(SqlTypes.CHAR) @Column(name="id",length=36,nullable=false) public String id;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name="report_id",length=36,nullable=false) public String reportId;
    @Column(name="storage_key",length=512,nullable=false) public String storageKey;
    @Column(name="mime_type",length=50,nullable=false) public String mimeType;
    @Column(name="byte_size",nullable=false) public Long byteSize;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name="sha256",length=64) public String sha256;
    @CreationTimestamp @Column(name="created_at",nullable=false) public Instant createdAt;
}
