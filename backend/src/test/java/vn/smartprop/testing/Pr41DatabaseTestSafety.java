package vn.smartprop.testing;

import org.springframework.jdbc.core.JdbcTemplate;

/** News tests use the same independently provisioned identity boundary as other integration tests. */
public final class Pr41DatabaseTestSafety {
    private Pr41DatabaseTestSafety() {}
    public static void require(JdbcTemplate jdbc) { IsolatedDatabaseTestSafety.require(jdbc); }
}
