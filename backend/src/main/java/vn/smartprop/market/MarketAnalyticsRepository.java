package vn.smartprop.market;

import java.util.ArrayList;
import java.util.List;
import org.springframework.jdbc.core.RowCallbackHandler;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

/**
 * Read-only, real-MySQL cohort loader for Step 21.5B.
 *
 * <p>TiniX has only one narrow covering index; any query that also reads
 * district / area / published_at does a clustered lookup per row (~80 s for the
 * whole cohort — the same limit Step 21.2 documented). So the cohort is read
 * <b>once per dataset</b> via a single UNION ALL scan, cached by the service
 * (not re-read per request), and every statistic is then computed in Java.
 * The service applies the user filters (district / ward / type / source) to the
 * cached cohort, so a filtered request never touches MySQL again.
 */
@Repository
public class MarketAnalyticsRepository {

    /** One real listing row with only the columns the statistics need. */
    public record CohortRow(
        String source,
        String district,
        String ward,
        String propertyType,
        double priceVnd,
        double areaSqm,
        String month
    ) {}

    private final NamedParameterJdbcTemplate jdbc;

    public MarketAnalyticsRepository(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    /** One wide scan of the real cohort. Called by the service's long-lived cache. */
    public List<CohortRow> loadCohort(boolean includeResearch) {
        List<CohortRow> out = new ArrayList<>();
        RowCallbackHandler handler = rs -> out.add(new CohortRow(
            rs.getString("src"),
            rs.getString("district"),
            rs.getString("ward"),
            rs.getString("ptype"),
            rs.getDouble("total_price"),
            rs.getDouble("area_sqm"),
            rs.getString("month")));
        jdbc.query(sql(includeResearch), new MapSqlParameterSource(), handler);
        return out;
    }

    private String sql(boolean includeResearch) {
        StringBuilder sb = new StringBuilder();
        sb.append("SELECT 'SMARTPROP' AS src, p.district AS district, p.ward AS ward, "
            + "p.property_type AS ptype, p.price AS total_price, p.area_sqm AS area_sqm, NULL AS month "
            + "FROM properties p WHERE p.status='PUBLISHED' AND p.deleted_at IS NULL "
            + "AND p.transaction_type='SALE' AND p.price_unit='TOTAL' AND p.currency='VND' "
            + "AND p.price > 0 AND p.area_sqm > 0");
        sb.append(" UNION ALL SELECT 'EXTERNAL_LISTING', e.district, NULL, "
            + "CASE e.category WHEN 'Nhà ở' THEN 'HOUSE' WHEN 'Đất nền' THEN 'LAND' "
            + "WHEN 'Căn hộ chung cư' THEN 'APARTMENT' WHEN 'Biệt thự' THEN 'VILLA' ELSE 'OTHER' END, "
            + "e.price, e.area_sqm, NULL "
            + "FROM external_listings e WHERE e.quality_status='VALID' AND e.transaction_type='SALE' "
            + "AND e.is_protected_holdout=0 AND e.is_duplicate=0 AND e.price > 0 AND e.area_sqm > 0");
        if (includeResearch) {
            sb.append(" UNION ALL SELECT 'TINIX_RESEARCH', t.district, t.ward, "
                + "UPPER(COALESCE(t.normalized_type,'OTHER')), t.price_vnd, t.area_sqm, LEFT(t.published_at,7) "
                + "FROM tinix_dataset_records t WHERE t.quality_status='HYBRID_ELIGIBLE_RESEARCH' "
                + "AND t.transaction_type='SALE' AND t.is_protected_holdout=0 AND t.is_duplicate_representative=1 "
                + "AND t.price_vnd > 0 AND t.area_sqm > 0");
        }
        return sb.toString();
    }
}
