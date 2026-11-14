package vn.smartprop.market;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.jdbc.datasource.SingleConnectionDataSource;
import vn.smartprop.market.MarketDtos.Response;
import vn.smartprop.market.MarketDtos.SourceCount;

/**
 * Step 21.5B — real-MySQL integration test for Market Analytics.
 *
 * <p>Read-only against the local {@code smartprop} database. Verified facts:
 * the pooled counts equal independent SQL counts, the median matches a
 * Java-computed median for the (small) SmartProp cohort, research rows are
 * excluded unless requested, and the temporal series is TiniX-only.
 * Skipped (not failed) when {@code ../.env} is absent. Never prints credentials.
 */
class MarketAnalyticsLiveIT {

    private static NamedParameterJdbcTemplate jdbc;
    private static MarketAnalyticsService service;

    @BeforeAll
    static void connect() throws Exception {
        Path env = Path.of("..", ".env");
        assumeTrue(Files.exists(env), "local .env with DB settings is required for live market tests");
        Properties props = new Properties();
        for (String line : Files.readAllLines(env)) {
            Matcher m = Pattern.compile("^([A-Za-z0-9_]+)=(.*)$").matcher(line.strip());
            if (m.matches()) props.setProperty(m.group(1), m.group(2).strip().replaceAll("^[\"']|[\"']$", ""));
        }
        Matcher url = Pattern.compile("//([^:/]+):(\\d+)/([^?]+)").matcher(props.getProperty("DB_URL", ""));
        assumeTrue(url.find(), "DB_URL must look like jdbc:mysql://host:port/db");
        Connection connection = DriverManager.getConnection(
            "jdbc:mysql://" + url.group(1) + ":" + url.group(2) + "/" + url.group(3)
                + "?useSSL=false&serverTimezone=UTC&allowPublicKeyRetrieval=true",
            props.getProperty("DB_USER"), props.getProperty("DB_PASSWORD"));
        connection.setReadOnly(true);
        jdbc = new NamedParameterJdbcTemplate(new SingleConnectionDataSource(connection, true));
        service = new MarketAnalyticsService(new MarketAnalyticsRepository(jdbc));
    }

    private static long count(String sql) {
        Long v = jdbc.queryForObject(sql, new java.util.HashMap<>(), Long.class);
        return v == null ? 0 : v;
    }

    private static final String SP_COUNT =
        "SELECT COUNT(*) FROM properties WHERE status='PUBLISHED' AND deleted_at IS NULL "
      + "AND transaction_type='SALE' AND price_unit='TOTAL' AND currency='VND' AND price>0 AND area_sqm>0";
    private static final String EXT_COUNT =
        "SELECT COUNT(*) FROM external_listings WHERE quality_status='VALID' AND transaction_type='SALE' "
      + "AND is_protected_holdout=0 AND is_duplicate=0 AND price>0 AND area_sqm>0";
    private static final String TINIX_COUNT =
        "SELECT COUNT(*) FROM tinix_dataset_records WHERE quality_status='HYBRID_ELIGIBLE_RESEARCH' "
      + "AND transaction_type='SALE' AND is_protected_holdout=0 AND is_duplicate_representative=1 "
      + "AND price_vnd>0 AND area_sqm>0";

    @Test
    @DisplayName("pooled count equals the sum of the three real source counts")
    void pooledCountMatchesSources() {
        long sp = count(SP_COUNT), ext = count(EXT_COUNT), tinix = count(TINIX_COUNT);
        Response r = service.analytics(null, null, null, null, true);
        assertEquals(sp + ext + tinix, r.meta().totalSampleCount());
        assertEquals(sp, r.bySource().stream().filter(s -> "SMARTPROP".equals(s.source())).map(SourceCount::count).reduce(0L, Long::sum));
        assertEquals(tinix, r.bySource().stream().filter(s -> "TINIX_RESEARCH".equals(s.source())).map(SourceCount::count).reduce(0L, Long::sum));
        System.out.printf("[STEP-21.5B] pooled=%d smartprop=%d external=%d tinix=%d%n", r.meta().totalSampleCount(), sp, ext, tinix);
    }

    @Test
    @DisplayName("SmartProp median matches a Java-computed median for the same cohort")
    void smartPropMedianMatchesJava() {
        Response r = service.analytics(null, null, null, "SMARTPROP", false);
        List<BigDecimal> prices = jdbc.queryForList(
            "SELECT price FROM properties WHERE status='PUBLISHED' AND deleted_at IS NULL AND transaction_type='SALE' "
          + "AND price_unit='TOTAL' AND currency='VND' AND price>0 AND area_sqm>0", new java.util.HashMap<>(), BigDecimal.class);
        assumeTrue(prices.size() >= 30, "need >= 30 SmartProp rows for a stable median check");
        prices.sort(BigDecimal::compareTo);
        BigDecimal median = median(prices);
        assertEquals(0, r.overall().medianAskingPriceVnd().compareTo(median.setScale(0, java.math.RoundingMode.HALF_UP)),
            "window-function median must equal Java median");
    }

    @Test
    @DisplayName("research rows are excluded unless requested")
    void researchGating() {
        Response off = service.analytics(null, null, null, null, false);
        assertEquals(0, off.bySource().stream().filter(s -> "TINIX_RESEARCH".equals(s.source())).map(SourceCount::count).reduce(0L, Long::sum));
        assertTrue(off.monthly().isEmpty());

        Response on = service.analytics(null, null, null, null, true);
        assertTrue(on.bySource().stream().filter(s -> "TINIX_RESEARCH".equals(s.source())).map(SourceCount::count).reduce(0L, Long::sum) > 0);
    }

    @Test
    @DisplayName("temporal series is TiniX-only and inside the documented snapshot window")
    void temporalSeriesIsTinixOnly() {
        Response r = service.analytics(null, null, null, "TINIX_RESEARCH", true);
        assertFalse(r.monthly().isEmpty());
        for (var p : r.monthly()) {
            assertTrue(p.period().compareTo("2025-01") >= 0 && p.period().compareTo("2026-12") <= 0, p.period());
            assertNotNull(p.dataStatus());
        }
        assertTrue(r.meta().dataQualityWarnings().stream().anyMatch(w -> w.startsWith("SINGLE_SNAPSHOT")));
    }

    @Test
    @DisplayName("district filter narrows the pooled cohort")
    void districtFilter() {
        Response all = service.analytics(null, null, null, "SMARTPROP", false);
        Response hc = service.analytics("Hải Châu", null, null, "SMARTPROP", false);
        assertTrue(hc.meta().totalSampleCount() <= all.meta().totalSampleCount());
        long direct = count(SP_COUNT.replace("COUNT(*)", "COUNT(*)") + " AND district='Hải Châu'");
        assertEquals(direct, hc.meta().totalSampleCount());
    }

    @Test
    @DisplayName("warm (cached) call is fast")
    void cacheIsFast() {
        long t0 = System.nanoTime();
        service.analytics(null, null, null, "SMARTPROP", false);
        long firstMs = (System.nanoTime() - t0) / 1_000_000;
        long t1 = System.nanoTime();
        service.analytics(null, null, null, "SMARTPROP", false);
        long secondMs = (System.nanoTime() - t1) / 1_000_000;
        System.out.printf("[STEP-21.5B] smartprop first=%dms cached=%dms%n", firstMs, secondMs);
        assertTrue(secondMs < 50, "cached call should be sub-50ms, got " + secondMs);
    }

    private static BigDecimal median(List<BigDecimal> sorted) {
        int n = sorted.size();
        if (n == 0) return BigDecimal.ZERO;
        if (n % 2 == 1) return sorted.get(n / 2);
        return sorted.get(n / 2 - 1).add(sorted.get(n / 2)).divide(BigDecimal.valueOf(2), java.math.RoundingMode.HALF_UP);
    }
}
