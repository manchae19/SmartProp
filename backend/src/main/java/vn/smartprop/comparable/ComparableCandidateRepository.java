package vn.smartprop.comparable;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

/** Read-only candidate queries against the research tables.
 *
 *  TiniX holds 185,973 rows (889 MB) but only five columns are indexed
 *  (quality_status, is_duplicate_representative, is_protected_holdout,
 *  transaction_type, price_vnd). Selecting the wide columns directly forces a
 *  clustered-index lookup per matching row: measured 82 s for one district.
 *  So every query here is two-phase - scan the covering index for ids, then
 *  fetch details for a bounded id list. Measured 0.06 s for the same filter.
 */
@Repository
public class ComparableCandidateRepository {
    private final NamedParameterJdbcTemplate jdbc;

    public ComparableCandidateRepository(NamedParameterJdbcTemplate jdbc) { this.jdbc = jdbc; }

    /** Row shapes returned to the ranking service. Public so tests can build them. */
    public record TinixRow(
        String internalId, String propertyType, String district, String ward,
        BigDecimal areaSqm, BigDecimal priceVnd, BigDecimal floors, BigDecimal frontageM,
        BigDecimal bedrooms, BigDecimal roadWidthM, String duplicateGroup) {}

    public record PropertyRow(
        String id, String propertyType, String district, String ward,
        BigDecimal areaSqm, BigDecimal priceVnd, Integer bedrooms) {}

    public record ExternalRow(
        long id, String source, String propertyType, String district,
        BigDecimal areaSqm, BigDecimal priceVnd, String qualityStatus, String detailUrl) {}

    private static final String TINIX_ELIGIBLE =
        " quality_status = 'HYBRID_ELIGIBLE_RESEARCH' "
      + " AND is_duplicate_representative = 1 "
      + " AND is_protected_holdout = 0 "
      + " AND transaction_type = 'SALE' ";

    /** Phase 1: ids from the covering index only, constrained by the price band.
     *
     *  The band is wide (0.4x-2.5x the reference), so a single ORDER BY .. LIMIT
     *  would only ever return the cheapest or the dearest rows in it. Instead
     *  the band is cut into {@code buckets} equal slices and each slice is
     *  capped, which samples the whole range at a deterministic cost. Measured
     *  12 slices x 100 ids = 0.10-0.57 s on the live table. */
    public List<String> tinixIdsInPriceBand(BigDecimal minPrice, BigDecimal maxPrice, int perBucket, int buckets) {
        if (minPrice == null || maxPrice == null || maxPrice.compareTo(minPrice) <= 0 || buckets < 1) {
            return List.of();
        }
        String sql = "SELECT internal_id FROM tinix_dataset_records WHERE " + TINIX_ELIGIBLE
                   + " AND price_vnd >= :min AND price_vnd <= :max LIMIT :cap";
        BigDecimal step = maxPrice.subtract(minPrice).divide(BigDecimal.valueOf(buckets), 0, java.math.RoundingMode.FLOOR);
        if (step.signum() <= 0) step = BigDecimal.ONE;
        java.util.LinkedHashSet<String> ids = new java.util.LinkedHashSet<>();
        for (int i = 0; i < buckets; i++) {
            BigDecimal from = minPrice.add(step.multiply(BigDecimal.valueOf(i)));
            BigDecimal to = i == buckets - 1 ? maxPrice : minPrice.add(step.multiply(BigDecimal.valueOf(i + 1))).subtract(BigDecimal.ONE);
            MapSqlParameterSource p = new MapSqlParameterSource()
                .addValue("min", from).addValue("max", to).addValue("cap", perBucket);
            ids.addAll(jdbc.queryForList(sql, p, String.class));
        }
        return List.copyOf(ids);
    }

    /** Phase 2: the columns the filters and the scorer need, for a bounded id list.
     *  Deliberately narrow: the wide row also carries duplicate_group, which the
     *  ranking never reads, and dropping it saves a page read per candidate. */
    public List<TinixRow> tinixDetails(List<String> ids) {
        if (ids == null || ids.isEmpty()) return List.of();
        String sql = "SELECT internal_id, normalized_type, district, ward, area_sqm, price_vnd,"
                   + " floor_count, frontage_width, bedroom_count, road_width"
                   + " FROM tinix_dataset_records WHERE internal_id IN (:ids)";
        return jdbc.query(sql, new MapSqlParameterSource("ids", ids), (rs, i) -> new TinixRow(
            rs.getString("internal_id"), rs.getString("normalized_type"),
            rs.getString("district"), rs.getString("ward"),
            rs.getBigDecimal("area_sqm"), rs.getBigDecimal("price_vnd"),
            rs.getBigDecimal("floor_count"), rs.getBigDecimal("frontage_width"),
            rs.getBigDecimal("bedroom_count"), rs.getBigDecimal("road_width"),
            null));
    }

    /** Externals are only 3,204 rows with an index on (district, category), so a
     *  single-stage query is fine here. note: this table has no duplicate_group
     *  filter beyond the is_duplicate flag because it carries no holdout twins. */
    public List<ExternalRow> externalCandidates(String district, String category, BigDecimal minPrice,
                                                BigDecimal maxPrice, int cap) {
        // external_listings has no price_vnd column; price is already absolute VND.
        String sql = "SELECT id, source, category, district, area_sqm, price, quality_status, detail_url"
                   + " FROM external_listings WHERE quality_status = 'VALID'"
                   + " AND is_protected_holdout = 0 AND is_duplicate = 0"
                   + " AND transaction_type = 'SALE'"
                   + " AND district = :district AND category = :category"
                   + " AND price BETWEEN :min AND :max LIMIT :cap";
        MapSqlParameterSource p = new MapSqlParameterSource()
            .addValue("district", district).addValue("category", category)
            .addValue("min", minPrice).addValue("max", maxPrice).addValue("cap", cap);
        return jdbc.query(sql, p, (rs, i) -> new ExternalRow(
            rs.getLong("id"), rs.getString("source"), rs.getString("category"),
            rs.getString("district"), rs.getBigDecimal("area_sqm"), rs.getBigDecimal("price"),
            rs.getString("quality_status"), rs.getString("detail_url")));
    }

    /** SmartProp's own published listings. Only 151 rows exist in total, so a
     *  plain filtered select is cheaper than any two-phase dance. */
    public List<PropertyRow> propertyCandidates(List<String> districts, String type,
                                                BigDecimal minPrice, BigDecimal maxPrice, int cap) {
        if (districts == null || districts.isEmpty()) return List.of();
        String sql = "SELECT id, property_type, district, ward, area_sqm, price, bedrooms"
                   + " FROM properties WHERE status = 'PUBLISHED' AND deleted_at IS NULL"
                   + " AND transaction_type = 'SALE' AND price_unit = 'TOTAL'"
                   + " AND property_type = :type AND district IN (:districts)"
                   + " AND price BETWEEN :min AND :max LIMIT :cap";
        MapSqlParameterSource p = new MapSqlParameterSource()
            .addValue("districts", districts).addValue("type", type)
            .addValue("min", minPrice).addValue("max", maxPrice).addValue("cap", cap);
        return jdbc.query(sql, p, (rs, i) -> new PropertyRow(
            rs.getString("id"), rs.getString("property_type"), rs.getString("district"),
            rs.getString("ward"), rs.getBigDecimal("area_sqm"), rs.getBigDecimal("price"),
            intOrNull(rs.getObject("bedrooms"))));
    }

    /** Counts per source, for the response header.
     *
     *  A COUNT over the 889 MB research table measured 4-12 s cold, which would
     *  dominate a lookup that otherwise runs in about a second. The cohort only
     *  changes when the dataset is re-imported, so the numbers are cached for
     *  ten minutes rather than recomputed per request. */
    private volatile Map<String,Integer> cachedCounts = Map.of();
    private volatile long cachedCountsAt;

    public Map<String,Integer> eligibleCounts() {
        long now = System.currentTimeMillis();
        Map<String,Integer> cached = cachedCounts;
        if (now - cachedCountsAt < 600_000 && !cached.isEmpty()) return cached;
        synchronized (this) {
            if (System.currentTimeMillis() - cachedCountsAt < 600_000 && !cachedCounts.isEmpty()) {
                return cachedCounts;
            }
            cachedCounts = computeCounts();
            cachedCountsAt = System.currentTimeMillis();
            return cachedCounts;
        }
    }

    private Map<String,Integer> computeCounts() {
        Integer tinix = jdbc.queryForObject(
            "SELECT COUNT(*) FROM tinix_dataset_records WHERE " + TINIX_ELIGIBLE, new MapSqlParameterSource(), Integer.class);
        Integer ext = jdbc.queryForObject(
            "SELECT COUNT(*) FROM external_listings WHERE quality_status = 'VALID'"
          + " AND is_protected_holdout = 0 AND is_duplicate = 0 AND transaction_type = 'SALE'",
            new MapSqlParameterSource(), Integer.class);
        Integer props = jdbc.queryForObject(
            "SELECT COUNT(*) FROM properties WHERE status = 'PUBLISHED' AND deleted_at IS NULL"
          + " AND transaction_type = 'SALE'", new MapSqlParameterSource(), Integer.class);
        return Map.of("SMARTPROP", props == null ? 0 : props,
                      "EXTERNAL_LISTING", ext == null ? 0 : ext,
                      "TINIX_RESEARCH", tinix == null ? 0 : tinix);
    }

    private static Integer intOrNull(Object value) {
        if (value == null) return null;
        if (value instanceof Number n) return n.intValue();
        return null;
    }
}
