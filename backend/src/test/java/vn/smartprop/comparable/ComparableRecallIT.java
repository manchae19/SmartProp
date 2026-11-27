package vn.smartprop.comparable;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
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
 * Recall and bias checks on the real dataset.
 *
 * The engine samples the price band in 12 slices x 25 ids. This proves that
 * sampling did not break district recall, that the result cap holds, and that
 * a nonsense reference price still falls back to real rows instead of an
 * empty card.
 */
class ComparableRecallIT {

    private static ComparableRankingService service;

    @BeforeAll
    static void connect() throws Exception {
        Path env = Path.of("..", ".env");
        assumeTrue(Files.exists(env), "local .env with DB settings is required");
        Properties props = new Properties();
        for (String line : Files.readAllLines(env)) {
            Matcher m = Pattern.compile("^([A-Za-z0-9_]+)=(.*)$").matcher(line.strip());
            if (m.matches()) props.setProperty(m.group(1), m.group(2).strip().replaceAll("^[\"']|[\"']$", ""));
        }
        Matcher url = Pattern.compile("//([^:/]+):(\\d+)/([^?]+)").matcher(props.getProperty("DB_URL", ""));
        assumeTrue(url.find(), "DB_URL must look like jdbc:mysql://host:port/db");
        Connection c = DriverManager.getConnection(
            "jdbc:mysql://" + url.group(1) + ":" + url.group(2) + "/" + url.group(3)
                + "?useSSL=false&serverTimezone=UTC&allowPublicKeyRetrieval=true",
            props.getProperty("DB_USER"), props.getProperty("DB_PASSWORD"));
        c.setReadOnly(true);
        service = new ComparableRankingService(
            new ComparableCandidateRepository(new NamedParameterJdbcTemplate(new SingleConnectionDataSource(c, true))),
            new ComparableEligibilityService(), Mockito.mock(PropertyRepository.class), true);
    }

    private static ComparableDtos.Response rank(String district, String type, String area, String price) {
        return service.rankResearch(new ComparableDtos.Request(null, type, district, null,
            new BigDecimal(area), new BigDecimal(price), null, null, null));
    }

    @Test
    void everyDistrictReturnsItsOwnDistrictFirstAndNeverExceedsFive() {
        String[][] cases = {
            {"Hải Châu", "HOUSE", "80", "5000000000"},
            {"Cẩm Lệ", "HOUSE", "90", "6000000000"},
            {"Sơn Trà", "APARTMENT", "70", "4000000000"},
            {"Ngũ Hành Sơn", "LAND", "120", "3000000000"},
            {"Thanh Khê", "HOUSE", "60", "3500000000"},
            {"Liên Chiểu", "HOUSE", "100", "4000000000"},
            {"Hòa Vang", "LAND", "300", "2000000000"},
        };
        for (String[] c : cases) {
            var r = rank(c[0], c[1], c[2], c[3]);
            assertThat(r.candidateCount()).as("%s result count", c[0]).isBetween(1, 5);
            assertThat(r.searchStage()).as("%s stage", c[0]).isNotEqualTo("NONE");
            long sameDistrict = r.comparables().stream()
                .filter(x -> c[0].equalsIgnoreCase(x.district())).count();
            // Sampling must not push the engine out of the reference district when
            // that district has eligible rows (all seven do, verified separately).
            assertThat(sameDistrict).as("%s same-district recall", c[0]).isGreaterThanOrEqualTo(4);
        }
    }

    @Test
    void resultsAreSortedAndEveryRowExplainsItself() {
        var r = rank("Hải Châu", "HOUSE", "80", "5000000000");
        double previous = 2.0;
        for (var c : r.comparables()) {
            assertThat(c.similarityScore()).isLessThanOrEqualTo(previous);
            previous = c.similarityScore();
            assertThat(c.scoreBreakdown()).isNotEmpty();
            assertThat(c.sourceKind()).isNotNull();
        }
    }

    @Test
    void nonsenseReferencePriceFallsBackToRealRowsRatherThanEmpty() {
        // 300 billion for a 90 m2 house in Cẩm Lệ is absurd on purpose: the narrow
        // band finds nothing, so the widened fallback must still answer with data.
        var r = rank("Cẩm Lệ", "HOUSE", "90", "300000000000");
        assertThat(r.candidateCount()).isGreaterThan(0);
        assertThat(r.comparables()).allSatisfy(c -> {
            assertThat(c.areaSqm().doubleValue()).isBetween(90 / 2.5, 90 * 2.5);
            assertThat(c.askingPriceVnd()).isNotNull();
        });
        System.out.println("FALLBACK stage=" + r.searchStage() + " n=" + r.candidateCount()
            + " sources=" + r.comparables().stream().map(x -> x.sourceKind().name()).toList());
    }

    @Test
    void priceIsNotDominantSoTheV6EstimateCannotSelfConfirm() {
        var r = rank("Sơn Trà", "APARTMENT", "70", "4000000000");
        assertThat(r.candidateCount()).isEqualTo(5);
        // Price carries 8% of the weight: a candidate with a very different price
        // can still outrank one with a matching price if it matches better elsewhere.
        var spread = r.comparables().stream()
            .map(x -> x.askingPriceVnd().doubleValue() / 4_000_000_000.0).toList();
        System.out.println("PRICE_SPREAD " + spread);
        assertThat(spread).anySatisfy(ratio -> assertThat(Math.abs(ratio - 1.0)).isGreaterThan(0.2));
    }
}
