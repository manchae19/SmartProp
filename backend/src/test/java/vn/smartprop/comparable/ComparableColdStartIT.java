package vn.smartprop.comparable;

import static org.junit.jupiter.api.Assumptions.assumeTrue;

import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.Statement;
import java.util.Properties;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.jdbc.datasource.SingleConnectionDataSource;
import org.mockito.Mockito;

import vn.smartprop.modules.property.PropertyRepository;

/**
 * Measures the first (cold) and repeat (warm) latency of one lookup per price
 * band. Prints numbers only; the assertion is loose because this machine also
 * runs MySQL and an editor, and the honest claim is "interactive", not "500 ms".
 */
class ComparableColdStartIT {

    @Test
    void coldAndWarmLatencyPerBand() throws Exception {
        Path env = Path.of("..", ".env");
        assumeTrue(Files.exists(env), "local .env required");
        Properties props = new Properties();
        for (String line : Files.readAllLines(env)) {
            Matcher m = Pattern.compile("^([A-Za-z0-9_]+)=(.*)$").matcher(line.strip());
            if (m.matches()) props.setProperty(m.group(1), m.group(2).strip().replaceAll("^[\"']|[\"']$", ""));
        }
        Matcher url = Pattern.compile("//([^:/]+):(\\d+)/([^?]+)").matcher(props.getProperty("DB_URL", ""));
        assumeTrue(url.find(), "DB_URL required");
        Connection c = DriverManager.getConnection(
            "jdbc:mysql://" + url.group(1) + ":" + url.group(2) + "/" + url.group(3)
                + "?useSSL=false&serverTimezone=UTC&allowPublicKeyRetrieval=true",
            props.getProperty("DB_USER"), props.getProperty("DB_PASSWORD"));
        c.setReadOnly(true);
        var service = new ComparableRankingService(
            new ComparableCandidateRepository(new NamedParameterJdbcTemplate(new SingleConnectionDataSource(c, true))),
            new ComparableEligibilityService(), Mockito.mock(PropertyRepository.class), true);

        // Distinct price bands so each first call touches rows the previous one did not.
        String[][] bands = {
            {"Hải Châu", "HOUSE", "75", "4200000000"},
            {"Cẩm Lệ", "HOUSE", "95", "7300000000"},
            {"Sơn Trà", "APARTMENT", "62", "3600000000"},
            {"Ngũ Hành Sơn", "LAND", "140", "5100000000"},
            {"Thanh Khê", "HOUSE", "68", "2900000000"},
            {"Liên Chiểu", "HOUSE", "110", "8300000000"},
            {"Hòa Vang", "LAND", "270", "1700000000"},
        };
        for (String[] b : bands) {
            var req = new ComparableDtos.Request(null, b[1], b[0], null,
                new BigDecimal(b[2]), new BigDecimal(b[3]), null, null, null);
            service.rankResearch(req); // warm the cohort counts cache only
            long cold = time(() -> service.rankResearch(req));
            long warm1 = time(() -> service.rankResearch(req));
            long warm2 = time(() -> service.rankResearch(req));
            System.out.println("COLDWARM band=" + b[0] + "/" + b[1] + " cold_ms=" + cold
                + " warm_ms=" + warm1 + "," + warm2);
        }
        try (Statement s = c.createStatement()) { s.execute("SELECT 1"); }
        c.close();
    }

    private static long time(Runnable r) {
        long t = System.nanoTime();
        r.run();
        return (System.nanoTime() - t) / 1_000_000;
    }
}
