package vn.smartprop.comparable;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

/** Bounded, read-only retrieval. Public calls use only the two public source queries. */
@Repository
public class ComparableCandidateRepository {
    private final NamedParameterJdbcTemplate jdbc;

    public ComparableCandidateRepository(NamedParameterJdbcTemplate jdbc) { this.jdbc = jdbc; }

    public record Search(String district, String ward, String type, BigDecimal area, BigDecimal minArea, BigDecimal maxArea,
                  BigDecimal minPrice, BigDecimal maxPrice, String propertyId, ComparableDtos.SubjectIdentity subject) {}

    public record TinixRow(String internalId, String propertyType, String district, String ward,
                           BigDecimal areaSqm, BigDecimal priceVnd, BigDecimal floors, BigDecimal frontageM,
                           BigDecimal bedrooms, BigDecimal roadWidthM, String duplicateGroup) {}

    public record PropertyRow(String id, String propertyType, String district, String ward,
                              BigDecimal areaSqm, BigDecimal priceVnd, Integer bedrooms, String projectId) {
        public PropertyRow(String id, String propertyType, String district, String ward,
                           BigDecimal areaSqm, BigDecimal priceVnd, Integer bedrooms) {
            this(id, propertyType, district, ward, areaSqm, priceVnd, bedrooms, null);
        }
    }

    public record ExternalRow(long id, String source, String propertyType, String district,
                              BigDecimal areaSqm, BigDecimal priceVnd, String qualityStatus, String detailUrl,
                              String sourceListingId, String duplicateGroup) {}

    private static final String PROPERTY_ELIGIBLE = """
        p.status = 'PUBLISHED' AND p.deleted_at IS NULL
        AND (p.expires_at IS NULL OR p.expires_at > UTC_TIMESTAMP(6))
        AND p.transaction_type = 'SALE' AND p.price_unit = 'TOTAL' AND p.currency = 'VND'
        """;

    private static final String EXTERNAL_ELIGIBLE = """
        l.quality_status = 'VALID' AND l.verification_status = 'VERIFIED'
        AND JSON_LENGTH(l.quality_issues) = 0 AND JSON_TYPE(l.quality_issues) = 'ARRAY'
        AND l.is_protected_holdout = 0 AND l.is_duplicate = 0 AND l.transaction_type = 'SALE'
        AND (NULLIF(TRIM(l.duplicate_group), '') IS NULL OR NOT EXISTS (
            SELECT 1 FROM external_listings h WHERE h.duplicate_group = l.duplicate_group
                AND h.is_protected_holdout = 1))
        """;

    private static final String TINIX_ELIGIBLE = """
        t.quality_status = 'HYBRID_ELIGIBLE_RESEARCH' AND t.is_duplicate_representative = 1
        AND t.is_protected_holdout = 0 AND t.transaction_type = 'SALE'
        AND t.research_only = 1 AND t.verification_status = 'UNVERIFIED' AND t.listing_availability = 'UNKNOWN'
        AND JSON_LENGTH(t.quality_issues) = 0 AND JSON_TYPE(t.quality_issues) = 'ARRAY'
        AND NULLIF(TRIM(t.duplicate_group), '') IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM tinix_dataset_records h
            WHERE h.duplicate_group = t.duplicate_group AND h.is_protected_holdout = 1)
        """;

    public List<TinixRow> tinixCandidates(Search search, int cap) {
        String sql = """
            SELECT t.internal_id, t.normalized_type, t.district, t.ward, t.area_sqm, t.price_vnd,
                   t.floor_count, t.frontage_width, t.bedroom_count, t.road_width, t.duplicate_group
            FROM tinix_dataset_records t WHERE
            """ + TINIX_ELIGIBLE + """
            AND CAST(t.normalized_type AS BINARY) = CAST(:type AS BINARY)
            AND t.area_sqm BETWEEN :minArea AND :maxArea AND t.price_vnd BETWEEN :minPrice AND :maxPrice
            AND (:tinixId IS NULL OR t.internal_id <> :tinixId)
            """ + locality("t", search.ward())
            + " ORDER BY ABS(t.area_sqm - :area), t.internal_id ASC LIMIT :cap";
        return jdbc.query(sql, params(search, cap), (rs, i) -> new TinixRow(
            rs.getString("internal_id"), rs.getString("normalized_type"), rs.getString("district"),
            rs.getString("ward"), rs.getBigDecimal("area_sqm"), rs.getBigDecimal("price_vnd"),
            rs.getBigDecimal("floor_count"), rs.getBigDecimal("frontage_width"), rs.getBigDecimal("bedroom_count"),
            rs.getBigDecimal("road_width"), rs.getString("duplicate_group")));
    }

    public List<ExternalRow> externalCandidates(Search search, String category, int cap) {
        // The external schema has no verified ward or explicit VILLA category.
        if (search.ward() != null || category == null) return List.of();
        String sql = """
            SELECT l.id, l.source, l.category, l.district, l.area_sqm, l.price, l.quality_status,
                   l.detail_url, l.source_listing_id, l.duplicate_group
            FROM external_listings l WHERE
            """ + EXTERNAL_ELIGIBLE + """
            AND l.category = :category AND CAST(l.category AS BINARY) = CAST(:category AS BINARY)
            AND l.area_sqm BETWEEN :minArea AND :maxArea
            AND l.price BETWEEN :minPrice AND :maxPrice
            AND (:externalId IS NULL OR l.id <> :externalId)
            AND (:sourceListingId IS NULL OR :externalSource IS NULL
                OR l.source IS NULL OR l.source_listing_id IS NULL
                OR CAST(LOWER(TRIM(l.source)) AS BINARY) <> CAST(LOWER(:externalSource) AS BINARY)
                OR CAST(TRIM(l.source_listing_id) AS BINARY) <> CAST(:sourceListingId AS BINARY))
            """ + locality("l", null)
            + " ORDER BY ABS(l.area_sqm - :area), l.id ASC LIMIT :cap";
        return jdbc.query(sql, params(search, cap).addValue("category", category), (rs, i) -> new ExternalRow(
            rs.getLong("id"), rs.getString("source"), rs.getString("category"), rs.getString("district"),
            rs.getBigDecimal("area_sqm"), rs.getBigDecimal("price"), rs.getString("quality_status"),
            rs.getString("detail_url"), rs.getString("source_listing_id"), rs.getString("duplicate_group")));
    }

    public List<PropertyRow> propertyCandidates(Search search, int cap) {
        String sql = """
            SELECT p.id, p.property_type, p.district, p.ward, p.area_sqm, p.price, p.bedrooms, p.project_id
            FROM properties p WHERE
            """ + PROPERTY_ELIGIBLE + """
            AND CAST(p.property_type AS BINARY) = CAST(:type AS BINARY)
            AND p.area_sqm BETWEEN :minArea AND :maxArea AND p.price BETWEEN :minPrice AND :maxPrice
            AND (:propertyId IS NULL OR p.id <> :propertyId)
            """ + locality("p", search.ward())
            + " ORDER BY ABS(p.area_sqm - :area), p.id ASC LIMIT :cap";
        return jdbc.query(sql, params(search, cap), (rs, i) -> new PropertyRow(
            rs.getString("id"), rs.getString("property_type"), rs.getString("district"), rs.getString("ward"),
            rs.getBigDecimal("area_sqm"), rs.getBigDecimal("price"), rs.getObject("bedrooms", Integer.class),
            rs.getString("project_id")));
    }

    private static String locality(String table, String ward) {
        // Keep district equality available to the index, and disambiguate accents on ai_ci schemas.
        return " AND " + table + ".district = :district AND " + sameLocality(table + ".district", "district")
            + (ward == null ? "" : " AND " + sameLocality(table + ".ward", "ward"));
    }

    private static String sameLocality(String column, String parameter) {
        return "CAST(LOWER(TRIM(" + column + ")) AS BINARY) = CAST(LOWER(:" + parameter + ") AS BINARY)";
    }

    private static MapSqlParameterSource params(Search search, int cap) {
        var subject = search.subject();
        return new MapSqlParameterSource()
            .addValue("district", search.district()).addValue("ward", search.ward()).addValue("type", search.type())
            .addValue("area", search.area()).addValue("minArea", search.minArea()).addValue("maxArea", search.maxArea())
            .addValue("minPrice", search.minPrice()).addValue("maxPrice", search.maxPrice()).addValue("cap", cap)
            .addValue("propertyId", search.propertyId())
            .addValue("externalId", subject.externalId()).addValue("externalSource", subject.externalSource())
            .addValue("sourceListingId", subject.sourceListingId()).addValue("tinixId", subject.tinixId());
    }

    private final Object publicCountLock = new Object();
    private Map<String, Integer> cachedCounts = Map.of();
    private long cachedCountsAt;
    private Map<String, Integer> cachedPublicCounts = Map.of();
    private long cachedPublicCountsAt;

    public synchronized Map<String, Integer> eligibleCounts() {
        long now = System.currentTimeMillis();
        if (now - cachedCountsAt >= 600_000 || cachedCounts.isEmpty()) {
            var pub = publicEligibleCounts();
            cachedCounts = Map.of("SMARTPROP", pub.get("SMARTPROP"), "EXTERNAL_LISTING", pub.get("EXTERNAL_LISTING"),
                "TINIX_RESEARCH", count("tinix_dataset_records t", TINIX_ELIGIBLE));
            cachedCountsAt = now;
        }
        return cachedCounts;
    }

    public Map<String, Integer> publicEligibleCounts() {
        synchronized (publicCountLock) {
            long now = System.currentTimeMillis();
            if (now - cachedPublicCountsAt >= 600_000 || cachedPublicCounts.isEmpty()) {
                cachedPublicCounts = Map.of("SMARTPROP", count("properties p", PROPERTY_ELIGIBLE),
                    "EXTERNAL_LISTING", count("external_listings l", EXTERNAL_ELIGIBLE));
                cachedPublicCountsAt = now;
            }
            return cachedPublicCounts;
        }
    }

    private int count(String table, String eligible) {
        Integer count = jdbc.queryForObject("SELECT COUNT(*) FROM " + table + " WHERE " + eligible,
            new MapSqlParameterSource(), Integer.class);
        return count == null ? 0 : count;
    }
}
