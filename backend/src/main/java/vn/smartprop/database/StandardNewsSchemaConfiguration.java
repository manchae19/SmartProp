package vn.smartprop.database;

import org.hibernate.boot.model.relational.Namespace;
import org.hibernate.boot.model.relational.Sequence;
import org.hibernate.mapping.Table;
import org.hibernate.tool.schema.spi.SchemaFilter;
import org.hibernate.tool.schema.spi.SchemaFilterProvider;
import org.springframework.boot.autoconfigure.orm.jpa.HibernatePropertiesCustomizer;
import org.springframework.context.annotation.*;

/** Standard V23 validates every existing entity; only the three Local-only News tables are excluded. */
@Configuration(proxyBeanMethods = false)
@Profile(MigrationProfileEnvironmentGuard.STANDARD)
public class StandardNewsSchemaConfiguration {
    @Bean HibernatePropertiesCustomizer standardNewsValidation() {
        return properties -> properties.put("hibernate.hbm2ddl.schema_filter_provider", new NewsFilterProvider());
    }
    public static final class NewsFilterProvider implements SchemaFilterProvider {
        private final SchemaFilter validation = new SchemaFilter() {
            public boolean includeNamespace(Namespace namespace) { return true; }
            public boolean includeSequence(Sequence sequence) { return true; }
            public boolean includeTable(Table table) {
                return !java.util.Set.of("news_sources", "news_articles", "news_ingestion_runs").contains(table.getName());
            }
        };
        public SchemaFilter getValidateFilter() { return validation; }
        public SchemaFilter getCreateFilter() { return SchemaFilter.ALL; }
        public SchemaFilter getDropFilter() { return SchemaFilter.ALL; }
        public SchemaFilter getTruncatorFilter() { return SchemaFilter.ALL; }
        public SchemaFilter getMigrateFilter() { return SchemaFilter.ALL; }
    }
}
