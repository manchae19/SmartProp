package vn.smartprop.database;

import java.util.*;
import org.junit.jupiter.api.Test;
import org.springframework.mock.env.MockEnvironment;
import static org.junit.jupiter.api.Assertions.*;

class Pr41IsolatedLineageTest {
    private MockEnvironment local() {
        var env = new MockEnvironment();
        env.setActiveProfiles(MigrationProfileEnvironmentGuard.LOCAL);
        return env.withProperty("spring.datasource.url", MigrationProfileEnvironmentGuard.LOCAL_URL)
            .withProperty("spring.flyway.locations", "classpath:database/legacy-hybrid-local,classpath:database/research-migrations")
            .withProperty("spring.flyway.enabled", "false").withProperty("spring.jpa.hibernate.ddl-auto", "validate")
            .withProperty("spring.sql.init.mode", "never");
    }

    @Test void productionLocalAndStagingKeepTheirLiteralDestinations() {
        assertDoesNotThrow(() -> MigrationProfileEnvironmentGuard.check(local()));
        var stagingBase = new MockEnvironment();
        stagingBase.setActiveProfiles(MigrationProfileEnvironmentGuard.STAGING);
        var staging = stagingBase.withProperty("spring.datasource.url", MigrationProfileEnvironmentGuard.STAGING_URL)
            .withProperty("spring.flyway.locations", "classpath:database/legacy-hybrid-local,classpath:database/research-migrations")
            .withProperty("spring.flyway.enabled", "false").withProperty("spring.jpa.hibernate.ddl-auto", "validate")
            .withProperty("spring.sql.init.mode", "never");
        assertDoesNotThrow(() -> MigrationProfileEnvironmentGuard.check(staging));
        assertThrows(IllegalStateException.class, () -> MigrationProfileEnvironmentGuard.check(
            local().withProperty("spring.datasource.url", "jdbc:mysql://127.0.0.1:3311/pr41_local")));
        assertThrows(IllegalStateException.class, () -> MigrationProfileEnvironmentGuard.check(
            staging.withProperty("spring.datasource.url", MigrationProfileEnvironmentGuard.LOCAL_URL)));
    }

    @Test void pr41ProfileIsTestOnlyAndDoesNotAddAnIdentityBypassToProduction() {
        var testProfile = new MockEnvironment();
        testProfile.setActiveProfiles(Pr41TestFixture.PROFILE);
        assertFalse(MigrationProfileEnvironmentGuard.isLocal(testProfile));
        assertDoesNotThrow(() -> MigrationProfileEnvironmentGuard.check(testProfile));
        assertThrows(IllegalStateException.class, () -> MigrationLineageConfiguration.checkHistory(
            new MigrationLineageConfigurationTest().through(28), false, false));
    }

    @Test void v28RequiresAllEarlierLocalVersionsAndStrictOrder() {
        var helper = new MigrationLineageConfigurationTest();
        var valid = helper.through(28);
        assertDoesNotThrow(() -> MigrationLineageConfiguration.checkHistory(valid, true, true));
        for (String missing : List.of("20", "26", "27")) {
            var rows = new ArrayList<>(helper.through(28));
            rows.removeIf(row -> missing.equals(row.get("version")));
            assertThrows(IllegalStateException.class, () -> MigrationLineageConfiguration.checkHistory(rows, true, true));
        }
        var unordered = new ArrayList<>(helper.through(28));
        Collections.swap(unordered, unordered.size() - 1, unordered.size() - 2);
        assertThrows(IllegalStateException.class, () -> MigrationLineageConfiguration.checkHistory(unordered, true, true));
        var duplicate = new ArrayList<>(helper.through(28));
        duplicate.add(helper.row("28", "SQL", 28));
        assertThrows(IllegalStateException.class, () -> MigrationLineageConfiguration.checkHistory(duplicate, true, true));
        var failed = new ArrayList<>(helper.through(28));
        failed.get(failed.size() - 1).put("success", false);
        assertThrows(IllegalStateException.class, () -> MigrationLineageConfiguration.checkHistory(failed, true, true));
    }

    @Test void runtimeRefusesPendingNewsMigrations() {
        for (String version : List.of("26", "27", "28"))
            assertThrows(IllegalStateException.class,
                () -> MigrationLineageConfiguration.checkRuntimePendingLocalMigrations(List.of(version), true));
        assertEquals("28", MigrationLineageConfiguration.target(true));
        assertEquals("23", MigrationLineageConfiguration.target(false));
    }
}
