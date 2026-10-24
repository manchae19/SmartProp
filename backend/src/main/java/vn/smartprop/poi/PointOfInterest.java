package vn.smartprop.poi;

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
@Entity @Table(name="points_of_interest")
public class PointOfInterest {

    @Id @JdbcTypeCode(SqlTypes.CHAR) @Column(name="id",length=36,nullable=false) public String id;
    @Column(name="name",length=255,nullable=false) public String name;
    @Column(name="category",length=50,nullable=false) public String category;
    @JdbcTypeCode(SqlTypes.GEOMETRY) @Column(name="location",columnDefinition="POINT SRID 4326",nullable=false) public Point location;
    @Column(name="source_name",length=255) public String sourceName;
    @Column(name="external_id",length=255) public String externalId;
    @Column(name="source_url",columnDefinition="TEXT") public String sourceUrl;
    @Column(name="observed_at") public Instant observedAt;
    @CreationTimestamp @Column(name="created_at",nullable=false) public Instant createdAt;
    @UpdateTimestamp @Column(name="updated_at",nullable=false) public Instant updatedAt;
}
