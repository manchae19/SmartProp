package vn.smartprop.database;

import java.util.*;
import org.flywaydb.core.Flyway;
import org.springframework.beans.factory.InitializingBean;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import vn.smartprop.testing.IsolatedDatabaseTestSafety;

/** Test-only bootstrap for the shared Coordinate regression, independent of deployment endpoint literals.
 * Replaces endpoint identity with the provisioner's ownership manifest, retaining strict Local history,
 * checksum and full Hibernate validation. This class is never included in the production artifact.
 */
public final class IsolatedCoordinateFixture {
    private IsolatedCoordinateFixture() {}
    public static NewsSchemaCapabilities capability() { validate();return new NewsSchemaCapabilities(true); }
    public static InitializingBean lineage() { return IsolatedCoordinateFixture::validate; }
    private static void validate() {
        var source=new DriverManagerDataSource(System.getenv("DB_URL"),System.getenv("DB_USER"),System.getenv("DB_PASSWORD"));
        var jdbc=new JdbcTemplate(source);
        IsolatedDatabaseTestSafety.require(jdbc);
        var history=jdbc.queryForList("SELECT version,type,checksum,success FROM flyway_schema_history ORDER BY installed_rank");
        MigrationLineageConfiguration.checkHistory(history,true,true);
        if(history.size()!=14||!"28".equals(history.getLast().get("version")))
            throw new IllegalStateException("Coordinate fixture requires completed Local V28 history");
        var flyway=Flyway.configure().dataSource(source)
            .locations("classpath:database/legacy-hybrid-local","classpath:database/research-migrations")
            .target("28").createSchemas(false).baselineOnMigrate(false).cleanDisabled(true)
            .ignoreMigrationPatterns(new String[]{}).validateMigrationNaming(true).load();
        flyway.validate();
        if(!Integer.valueOf(3).equals(jdbc.queryForObject("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name IN ('news_sources','news_articles','news_ingestion_runs')",Integer.class))
            ||!Integer.valueOf(1).equals(jdbc.queryForObject("SELECT COUNT(*) FROM information_schema.table_constraints WHERE constraint_schema=DATABASE() AND constraint_name='ck_news_sources_approved_reference' AND enforced='YES'",Integer.class)))
            throw new IllegalStateException("Incomplete isolated News schema");
    }
}
