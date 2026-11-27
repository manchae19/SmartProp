package vn.smartprop.testing;

import org.springframework.jdbc.core.JdbcTemplate;
import static org.junit.jupiter.api.Assertions.*;

/** Refuse writes to any shared MySQL or a schema not owned by this test run. */
public final class Pr41DatabaseTestSafety {
    private Pr41DatabaseTestSafety() {}
    public static void require(JdbcTemplate jdbc) {
        assertEquals(3311,jdbc.queryForObject("SELECT @@port",Integer.class));
        assertTrue(java.util.Set.of("pr41_news","pr41_local").contains(jdbc.queryForObject("SELECT DATABASE()",String.class)));
        assertEquals("0f29afde-ea54-11f1-bcac-088fc36287dc",jdbc.queryForObject("SELECT @@server_uuid",String.class));
        String datadir=jdbc.queryForObject("SELECT @@datadir",String.class).replace('\\','/');
        assertTrue(datadir.endsWith("/SmartProp-News-Backend/.scratch/mysql-pr41/data/"));
    }
}
