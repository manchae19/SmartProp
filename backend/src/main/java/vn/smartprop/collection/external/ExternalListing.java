package vn.smartprop.collection.external;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.annotations.UpdateTimestamp;
import org.hibernate.type.SqlTypes;

import java.math.BigDecimal;
import java.time.Instant;

@Entity
@Table(name = "external_listings")
public class ExternalListing {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    public Long id;

    @Column(name = "record_key", length = 100, nullable = false, unique = true)
    public String recordKey;

    @Column(name = "source", length = 50, nullable = false)
    public String source;

    @Column(name = "source_listing_id", length = 100)
    public String sourceListingId;

    @Column(name = "title", length = 500, nullable = false)
    public String title;

    @Column(name = "detail_url", columnDefinition = "TEXT", nullable = false)
    public String detailUrl;

    @Column(name = "category", length = 50, nullable = false)
    public String category;

    @Column(name = "transaction_type", length = 30, nullable = false)
    public String transactionType;

    @Column(name = "transaction_basis", length = 100)
    public String transactionBasis;

    @Column(name = "price", precision = 18, scale = 2, nullable = false)
    public BigDecimal price;

    @Column(name = "price_million", precision = 14, scale = 2, nullable = false)
    public BigDecimal priceMillion;

    @Column(name = "area_sqm", precision = 10, scale = 2, nullable = false)
    public BigDecimal areaSqm;

    @Column(name = "price_per_sqm_million", precision = 14, scale = 4)
    public BigDecimal pricePerSqmMillion;

    @Column(name = "district", length = 100)
    public String district;

    @Column(name = "address_raw", columnDefinition = "TEXT")
    public String addressRaw;

    @Column(name = "quality_status", length = 50, nullable = false)
    public String qualityStatus;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "quality_issues", columnDefinition = "JSON", nullable = false)
    public JsonNode qualityIssues;

    @Column(name = "verification_status", length = 50, nullable = false)
    public String verificationStatus;

    @Column(name = "duplicate_group", length = 100)
    public String duplicateGroup;

    @Column(name = "is_duplicate", nullable = false)
    public boolean isDuplicate;

    @Column(name = "is_protected_holdout", nullable = false)
    public boolean isProtectedHoldout;

    @Column(name = "collected_at")
    public Instant collectedAt;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "raw_metadata", columnDefinition = "JSON", nullable = false)
    public JsonNode rawMetadata;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false)
    public Instant createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    public Instant updatedAt;
}
