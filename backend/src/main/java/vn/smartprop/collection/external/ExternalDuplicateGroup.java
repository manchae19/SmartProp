package vn.smartprop.collection.external;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;

import java.math.BigDecimal;
import java.time.Instant;

@Entity
@Table(name = "external_duplicate_groups")
public class ExternalDuplicateGroup {

    @Id
    @Column(name = "group_id", length = 100, nullable = false)
    public String groupId;

    @Column(name = "name", length = 255, nullable = false)
    public String name;

    @Column(name = "category", length = 50, nullable = false)
    public String category;

    @Column(name = "district", length = 100)
    public String district;

    @Column(name = "listing_count", nullable = false)
    public int listingCount;

    @Column(name = "min_price", precision = 18, scale = 2)
    public BigDecimal minPrice;

    @Column(name = "max_price", precision = 18, scale = 2)
    public BigDecimal maxPrice;

    @Column(name = "min_area", precision = 10, scale = 2)
    public BigDecimal minArea;

    @Column(name = "max_area", precision = 10, scale = 2)
    public BigDecimal maxArea;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false)
    public Instant createdAt;
}
