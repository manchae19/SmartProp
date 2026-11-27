package vn.smartprop.database;

import javax.sql.DataSource;
import org.flywaydb.core.Flyway;
import org.springframework.core.env.Environment;
import org.springframework.jdbc.core.JdbcTemplate;

/** Read-only capability discovery, before Hibernate builds its validation plan. */
public record NewsSchemaCapabilities(boolean newsEnabled) {
    public static NewsSchemaCapabilities inspect(DataSource source, Environment env) throws Exception {
        JdbcTemplate jdbc = new JdbcTemplate(source);
        var history = jdbc.queryForList("SELECT version,type,checksum,success FROM flyway_schema_history ORDER BY installed_rank");
        boolean local = MigrationProfileEnvironmentGuard.isLocal(env);
        if (local) {
            new MigrationLineageConfiguration().validateSelectedMigrationLineage(source, env).afterPropertiesSet();
            if (history.size() != 14 || !"28".equals(history.getLast().get("version")))
                throw new IllegalStateException("News requires the completed Local V28 lineage.");
        } else {
            if (history.size() != 23) throw new IllegalStateException("Unknown schema lineage; refusing capability discovery.");
            for (int i = 0; i < history.size(); i++) {
                var row = history.get(i);
                if (!Integer.toString(i + 1).equals(row.get("version")) || !"SQL".equals(row.get("type"))
                    || !(Boolean.TRUE.equals(row.get("success")) || Integer.valueOf(1).equals(row.get("success"))))
                    throw new IllegalStateException("Invalid Standard V23 history.");
            }
            Flyway.configure().dataSource(source)
                .locations("classpath:database/migrations", "classpath:database/research-migrations/poi")
                .target("23").createSchemas(false).baselineOnMigrate(false).cleanDisabled(true)
                .ignoreMigrationPatterns(new String[]{}).validateMigrationNaming(true).load().validate();
        }
        Integer tables = jdbc.queryForObject("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name IN ('news_sources','news_articles','news_ingestion_runs')", Integer.class);
        if (!Integer.valueOf(local ? 3 : 0).equals(tables))
            throw new IllegalStateException("News tables do not match the validated schema lineage.");
        if (local && !Integer.valueOf(1).equals(jdbc.queryForObject("SELECT COUNT(*) FROM information_schema.table_constraints WHERE constraint_schema=DATABASE() AND constraint_name='ck_news_sources_approved_reference' AND enforced='YES'", Integer.class)))
            throw new IllegalStateException("Required V28 rights constraint is missing.");
        return new NewsSchemaCapabilities(local);
    }
}
