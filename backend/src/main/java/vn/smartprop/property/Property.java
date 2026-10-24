package vn.smartprop.property;

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
@Entity @Table(name="properties")
public class Property {
    public enum Type { HOUSE, APARTMENT, LAND, VILLA, ROOM, COMMERCIAL }
    public enum Transaction { SALE, RENT }
    public enum PriceUnit { TOTAL, PER_MONTH, PER_YEAR, PER_DAY }
    public enum Status { DRAFT, PENDING, PUBLISHED, REJECTED, HIDDEN, EXPIRED, CLOSED }
    @Id @JdbcTypeCode(SqlTypes.CHAR) @Column(name="id",length=36,nullable=false) public String id;
    @Column(name="owner_id",nullable=false) public Long ownerId;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name="project_id",length=36) public String projectId;
    @Column(name="title",length=255,nullable=false) public String title;
    @Column(name="description",columnDefinition="TEXT") public String description;
    @Enumerated(EnumType.STRING) @JdbcTypeCode(SqlTypes.VARCHAR) @Column(name="property_type",length=30,nullable=false) public Type propertyType;
    @Enumerated(EnumType.STRING) @JdbcTypeCode(SqlTypes.VARCHAR) @Column(name="transaction_type",length=30,nullable=false) public Transaction transactionType;
    @Column(name="price",precision=18,scale=2,nullable=false) public BigDecimal price;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name="currency",length=3,nullable=false) public String currency;
    @Enumerated(EnumType.STRING) @JdbcTypeCode(SqlTypes.VARCHAR) @Column(name="price_unit",length=30,nullable=false) public PriceUnit priceUnit;
    @Column(name="area_sqm",precision=12,scale=2,nullable=false) public BigDecimal areaSqm;
    @Column(name="bedrooms") public Short bedrooms;
    @Column(name="bathrooms") public Short bathrooms;
    @Column(name="floor",length=30) public String floor;
    @Column(name="block",length=50) public String block;
    @Column(name="direction",length=30) public String direction;
    @Column(name="address",columnDefinition="TEXT") public String address;
    @Column(name="city",length=100,nullable=false) public String city;
    @Column(name="district",length=100) public String district;
    @Column(name="ward",length=100) public String ward;
    @JdbcTypeCode(SqlTypes.GEOMETRY) @Column(name="location",columnDefinition="POINT SRID 4326",nullable=false) public Point location;
    @Column(name="contact_name",length=150) public String contactName;
    @Column(name="contact_phone",length=30) public String contactPhone;
    @Column(name="contact_email",length=254) public String contactEmail;
    @JdbcTypeCode(SqlTypes.JSON) @Column(name="declared_amenities",columnDefinition="JSON",nullable=false) public JsonNode declaredAmenities;
    @Enumerated(EnumType.STRING) @JdbcTypeCode(SqlTypes.VARCHAR) @Column(name="status",length=30,nullable=false) public Status status;
    @Column(name="content_version",nullable=false) public Integer contentVersion;
    @Column(name="published_at") public Instant publishedAt;
    @Column(name="expires_at") public Instant expiresAt;
    @Column(name="closed_at") public Instant closedAt;
    @Column(name="deleted_at") public Instant deletedAt;
    @CreationTimestamp @Column(name="created_at",nullable=false) public Instant createdAt;
    @UpdateTimestamp @Column(name="updated_at",nullable=false) public Instant updatedAt;
}
