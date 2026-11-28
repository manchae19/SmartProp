package vn.smartprop.database;

import javax.sql.DataSource;
import org.flywaydb.core.Flyway;
import org.springframework.core.env.Environment;
import org.springframework.jdbc.core.JdbcTemplate;

/** Read-only capability discovery, before Hibernate builds its validation plan. */
public record NewsSchemaCapabilities(boolean newsEnabled, boolean validateNewsTables) {
    /** Compatibility constructor for already validated full/Standard test fixtures. */
    public NewsSchemaCapabilities(boolean newsEnabled) { this(newsEnabled, newsEnabled); }
    public static NewsSchemaCapabilities inspect(DataSource source, Environment env) throws Exception {
        JdbcTemplate jdbc = new JdbcTemplate(source);
        var history = jdbc.queryForList("SELECT version,type,checksum,success FROM flyway_schema_history ORDER BY installed_rank");
        boolean local = MigrationProfileEnvironmentGuard.isLocal(env);
        if (local) {
            new MigrationLineageConfiguration().validateSelectedMigrationLineage(source, env).afterPropertiesSet();
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
        return resolveValidated(jdbc, history, local,
            env.getProperty("app.local-lineage.require-complete", Boolean.class, true));
    }
    /** The caller must first validate identity, ordered history, pending policy and Flyway checksums. */
    static NewsSchemaCapabilities resolveValidated(JdbcTemplate jdbc, java.util.List<java.util.Map<String,Object>> history,
            boolean local, boolean requireComplete) {
        if (history.isEmpty()) throw new IllegalStateException("Unknown schema lineage; refusing capability discovery.");
        String version = String.valueOf(history.getLast().get("version"));
        if (!local && !"23".equals(version))
            throw new IllegalStateException("Unknown Standard schema lineage; refusing capability discovery.");
        if (local && !java.util.Set.of("21", "26", "27", "28").contains(version))
            throw new IllegalStateException("Unsupported Local lineage for capability discovery.");
        if (local && requireComplete && !"28".equals(version))
            throw new IllegalStateException("Local News schema migration is pending; use the separately reviewed Flyway workflow.");
        Integer objects = jdbc.queryForObject("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name IN ('news_sources','news_articles','news_ingestion_runs')", Integer.class);
        Integer tables = jdbc.queryForObject("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_type='BASE TABLE' AND table_name IN ('news_sources','news_articles','news_ingestion_runs')", Integer.class);
        Integer namedConstraints = NewsRightsConstraintVerifier.countNamed(jdbc);
        if (!local) {
            if (!Integer.valueOf(0).equals(objects) || !Integer.valueOf(0).equals(namedConstraints))
                throw new IllegalStateException("News tables do not match the validated Standard schema lineage.");
            return new NewsSchemaCapabilities(false, false);
        }
        if ("21".equals(version) || "26".equals(version)) {
            if (!Integer.valueOf(0).equals(objects) || !Integer.valueOf(0).equals(namedConstraints))
                throw new IllegalStateException("News tables do not match the validated Local V" + version + " lineage.");
            return new NewsSchemaCapabilities(false, false);
        }
        if (!Integer.valueOf(3).equals(objects) || !Integer.valueOf(3).equals(tables))
            throw new IllegalStateException("News tables do not match the validated Local V" + version + " lineage.");
        if ("27".equals(version)) {
            if (!Integer.valueOf(0).equals(namedConstraints))
                throw new IllegalStateException("V27 cannot contain the V28 rights constraint.");
            return new NewsSchemaCapabilities(false, true);
        }
        NewsRightsConstraintVerifier.requireValid(jdbc);
        return new NewsSchemaCapabilities(true, true);
    }
}
