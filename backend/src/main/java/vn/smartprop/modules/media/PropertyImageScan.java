package vn.smartprop.modules.media;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.annotations.UpdateTimestamp;
import org.hibernate.type.SqlTypes;
import java.math.BigDecimal;
import java.time.Instant;

/** Persistence result for one property image; updated in place by the scanner. */
@Entity @Table(name="property_image_scan")
public class PropertyImageScan {
    @Id @JdbcTypeCode(SqlTypes.CHAR) @Column(name="id",length=36,nullable=false) public String id;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name="property_id",length=36,nullable=false) public String propertyId;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name="property_image_id",length=36,nullable=false) public String propertyImageId;
    @Column(name="scan_status",length=24,nullable=false) public String scanStatus;
    @Column(name="classification",length=24) public String classification;
    @Column(name="similarity",precision=5,scale=4) public BigDecimal similarity;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name="matched_property_id",length=36) public String matchedPropertyId;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name="matched_property_image_id",length=36) public String matchedPropertyImageId;
    @Column(name="matched_listing_code",length=32) public String matchedListingCode;
    @Column(name="detection_method",length=80) public String detectionMethod;
    @JdbcTypeCode(SqlTypes.JSON) @Column(name="evidence",columnDefinition="JSON",nullable=false) public JsonNode evidence;
    @Column(name="algorithm_version",length=32,nullable=false) public String algorithmVersion;
    @Column(name="error_code",length=64) public String errorCode;
    @Column(name="scanned_at") public Instant scannedAt;
    @CreationTimestamp @Column(name="created_at",nullable=false) public Instant createdAt;
    @UpdateTimestamp @Column(name="updated_at",nullable=false) public Instant updatedAt;
}
