package vn.smartprop.project;

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
@Entity @Table(name="projects")
public class Project {

    @Id @JdbcTypeCode(SqlTypes.CHAR) @Column(name="id",length=36,nullable=false) public String id;
    @Column(name="name",length=255,nullable=false) public String name;
    @Column(name="developer",length=255) public String developer;
    @Column(name="handover_year") public Short handoverYear;
    @Column(name="scale",columnDefinition="TEXT") public String scale;
    @Column(name="address",columnDefinition="TEXT") public String address;
    @JdbcTypeCode(SqlTypes.GEOMETRY) @Column(name="location",columnDefinition="POINT SRID 4326") public Point location;
    @JdbcTypeCode(SqlTypes.JSON) @Column(name="amenities",columnDefinition="JSON",nullable=false) public JsonNode amenities;
    @CreationTimestamp @Column(name="created_at",nullable=false) public Instant createdAt;
    @UpdateTimestamp @Column(name="updated_at",nullable=false) public Instant updatedAt;
}
