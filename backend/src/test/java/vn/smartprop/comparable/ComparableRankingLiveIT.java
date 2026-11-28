package vn.smartprop.comparable;

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
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.jdbc.datasource.SingleConnectionDataSource;

import vn.smartprop.modules.property.PropertyRepository;

/**
 * Runs the real engine against the local read-only MySQL instance.
 *
 * Skipped (not failed) when .env is absent on a teammate machine, so a clone
 * without the research database still builds. Never prints credential values.
 */
class ComparableRankingLiveIT {

    private static NamedParameterJdbcTemplate jdbc;
    private static ComparableRankingService service;

    @BeforeAll
    static void connect() throws Exception {
        Path env = Path.of("..", ".env");
        assumeTrue(Files.exists(env), "local .env with DB settings is required for live comparable tests");
        Properties props = new Properties();
        for (String line : Files.readAllLines(env)) {
            Matcher m = Pattern.compile("^([A-Za-z0-9_]+)=(.*)$").matcher(line.strip());
            if (m.matches()) {
                props.setProperty(m.group(1), m.group(2).strip().replaceAll("^[\"']|[\"']$", ""));
            }
        }
        Matcher url = Pattern.compile("//([^:/]+):(\\d+)/([^?]+)").matcher(props.getProperty("DB_URL", ""));
        assumeTrue(url.find(), "DB_URL must look like jdbc:mysql://host:port/db");
        String conn = "jdbc:mysql://" + url.group(1) + ":" + url.group(2) + "/" + url.group(3)
            + "?useSSL=false&serverTimezone=UTC&allowPublicKeyRetrieval=true";
        Connection connection = DriverManager.getConnection(conn,
            props.getProperty("DB_USER"), props.getProperty("DB_PASSWORD"));
        connection.setReadOnly(true);
        jdbc = new NamedParameterJdbcTemplate(new SingleConnectionDataSource(connection, true));
        ComparableCandidateRepository repository = new ComparableCandidateRepository(jdbc);
        service = new ComparableRankingService(repository, new ComparableEligibilityService(),
            Mockito.mock(PropertyRepository.class), true);
    }

    private static Number scalar(String sql) {
        Number value = jdbc.queryForObject(sql, new java.util.HashMap<>(), Number.class);
        return value == null ? 0 : value;
    }

    @Test
    void eligibleCountsMatchTheDocumentedCohort() {
        Map<String, Integer> counts = service.rankResearch(request("Hải Châu", "HOUSE", "80", "5000000000")).eligibleCountsBySource();
        assertEquals(55816, counts.get("TINIX_RESEARCH"), "TiniX eligible + representative + SALE cohort");
        assertEquals(151, counts.get("SMARTPROP"), "published SmartProp sale listings");
        assertTrue(counts.get("EXTERNAL_LISTING") > 1000, "valid external sale listings");

        Map<String, Integer> pubCounts = service.rank(request("Hải Châu", "HOUSE", "80", "5000000000")).eligibleCountsBySource();
        assertFalse(pubCounts.containsKey("TINIX_RESEARCH"), "public rank() must never expose TINIX_RESEARCH count");
    }

    @Test
    void tinixCandidatesNeverComeFromHoldoutsDuplicatesOrRentals() {
        assertEquals(0, scalar("SELECT COUNT(*) FROM tinix_dataset_records "
            + "WHERE quality_status='HYBRID_ELIGIBLE_RESEARCH' AND is_duplicate_representative=1 "
            + "AND transaction_type='SALE' AND is_protected_holdout=1").intValue(),
            "the ranked filter and the holdout flag must be mutually exclusive");

        var response = service.rankResearch(request("Cẩm Lệ", "HOUSE", "90", "6000000000"));
        assertFalse(response.comparables().isEmpty(), "Cẩm Lệ has eligible houses");
        for (var candidate : response.comparables()) {
            if (candidate.sourceKind() == ComparableDtos.SourceKind.TINIX_RESEARCH) {
                assertNotNull(candidate.candidateId());
                assertEquals("CC BY-NC 4.0", candidate.datasetLicense());
                assertEquals(ComparableSourceClassifier.TINIX_ATTRIBUTION, candidate.attribution());
                assertTrue(candidate.listingUrl() == null, "TiniX rows must never carry a URL");
                Integer held = jdbc.queryForObject(
                    "SELECT is_protected_holdout FROM tinix_dataset_records WHERE internal_id = :id",
                    Map.of("id", candidate.candidateId()), Integer.class);
                assertEquals(0, held);
                String tx = jdbc.queryForObject(
                    "SELECT transaction_type FROM tinix_dataset_records WHERE internal_id = :id",
                    Map.of("id", candidate.candidateId()), String.class);
                assertEquals("SALE", tx);
            }
        }
    }

    @Test
    void resultsAreCappedAtFiveAndOrderedByScore() {
        var response = service.rank(request("Sơn Trà", "APARTMENT", "70", "4000000000"));
        assertTrue(response.candidateCount() <= 5);
        assertTrue(response.comparables().size() <= 5, "hard cap of five comparables");
        double previous = Double.MAX_VALUE;
        for (var candidate : response.comparables()) {
            assertTrue(candidate.similarityScore() <= previous + 1e-9, "descending similarity order");
            previous = candidate.similarityScore();
            assertTrue(candidate.similarityScore() >= 0 && candidate.similarityScore() <= 1);
            assertFalse(candidate.scoreBreakdown().isEmpty(), "every candidate explains its score");
        }
        assertEquals("Sơn Trà", response.reference().district());
    }

    @Test
    void referencePriceAndAreaEnvelopeAreRespected() {
        var response = service.rank(request("Ngũ Hành Sơn", "LAND", "120", "3000000000"));
        for (var candidate : response.comparables()) {
            double areaRatio = candidate.areaSqm().doubleValue() / 120.0;
            assertTrue(areaRatio <= 2.5 && areaRatio >= 1 / 2.5, "area must stay inside the envelope: " + candidate.candidateId());
            if (candidate.askingPriceVnd() != null) {
                double priceRatio = candidate.askingPriceVnd().doubleValue() / 3_000_000_000.0;
                assertTrue(priceRatio <= 2.5 && priceRatio >= 1 / 2.5, "price must stay inside the envelope: " + candidate.candidateId());
            }
        }
    }

    @Test
    void unknownDistrictYieldsEmptyResultWithAnExplanation() {
        var response = service.rank(request("Quận Không Tồn Tại", "HOUSE", "80", "5000000000"));
        assertEquals(0, response.candidateCount());
        assertEquals("NONE", response.searchStage());
        assertTrue(response.warnings().stream().anyMatch(w -> w.startsWith("Không tìm thấy")));
    }

    @Test
    void invalidInputIsRejectedBeforeTouchingTheDatabase() {
        var missingDistrict = new ComparableDtos.Request(null, "HOUSE", null, null,
            new BigDecimal("80"), new BigDecimal("5000000000"), null, null, null);
        var badType = new ComparableDtos.Request(null, "ROOM", "Hải Châu", null,
            new BigDecimal("80"), new BigDecimal("5000000000"), null, null, null);
        var badLimit = new ComparableDtos.Request(null, "HOUSE", "Hải Châu", null,
            new BigDecimal("80"), new BigDecimal("5000000000"), null, null, 9);
        assertEquals(400, org.junit.jupiter.api.Assertions.assertThrows(
            vn.smartprop.common.ApiException.class, () -> service.rank(missingDistrict)).status);
        assertEquals(400, org.junit.jupiter.api.Assertions.assertThrows(
            vn.smartprop.common.ApiException.class, () -> service.rank(badType)).status);
        assertEquals(400, org.junit.jupiter.api.Assertions.assertThrows(
            vn.smartprop.common.ApiException.class, () -> service.rank(badLimit)).status);
    }

    @Test
    void latenciesStayInsideTheInteractiveBudget() {
        // Two effects are measured separately:
        //  * COLD  - first touch of a price band. MySQL must read ~1,200 random
        //            rows out of the 889 MB research table with no usable
        //            secondary index (only the 5-column covering index exists,
        //            and adding a better one is a schema change this task may
        //            not perform). Measured 4-6 s here.
        //  * WARM  - the buffer pool now holds the band; this is what a broker
        //            sees on the second and later lookups. Measured 25-100 ms.
        String[][] cases = {
            {"Hải Châu", "HOUSE", "80", "5000000000"},
            {"Cẩm Lệ", "HOUSE", "90", "6000000000"},
            {"Sơn Trà", "APARTMENT", "70", "4000000000"},
            {"Ngũ Hành Sơn", "LAND", "120", "3000000000"},
            {"Thanh Khê", "HOUSE", "60", "3500000000"},
        };
        List<Long> cold = new ArrayList<>();
        List<Long> warm = new ArrayList<>();
        for (int round = 0; round < 3; round++) {
            for (String[] c : cases) {
                long start = System.nanoTime();
                service.rank(request(c[0], c[1], c[2], c[3]));
                long elapsed = (System.nanoTime() - start) / 1_000_000;
                (round == 0 ? cold : warm).add(elapsed);
            }
        }
        warm.sort(Long::compare);
        cold.sort(Long::compare);
        long p50 = warm.get(warm.size() / 2), p95 = warm.get(warm.size() - 1);
        long coldMax = cold.get(cold.size() - 1);
        System.out.println("COMPARABLE_LATENCY_MS warmP50=" + p50 + " warmP95=" + p95
            + " coldMax=" + coldMax + " cold=" + cold + " warm=" + warm);
        assertTrue(p95 < 1000, "warm comparable lookup must stay interactive, got p95=" + p95 + "ms");
        assertTrue(coldMax < 15000, "cold first touch must stay bounded, got " + coldMax + "ms");
    }

    private static ComparableDtos.Request request(String district, String type, String area, String price) {
        return new ComparableDtos.Request(null, type, district, null,
            new BigDecimal(area), new BigDecimal(price), null, null, null);
    }
}
