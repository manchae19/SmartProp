package vn.smartprop.database;

import org.hibernate.boot.model.relational.Namespace;
import org.hibernate.boot.model.relational.Sequence;
import org.hibernate.mapping.Table;
import org.hibernate.tool.schema.spi.SchemaFilter;
import org.hibernate.tool.schema.spi.SchemaFilterProvider;
import org.springframework.boot.autoconfigure.orm.jpa.HibernatePropertiesCustomizer;
import org.springframework.context.annotation.*;

/** Customizer depends on validated database capability before Hibernate validation. */
@Configuration(proxyBeanMethods = false)
public class StandardNewsSchemaConfiguration {
    @Bean NewsSchemaCapabilities newsSchemaCapabilities(javax.sql.DataSource source,
            org.springframework.core.env.Environment environment) throws Exception {
        return NewsSchemaCapabilities.inspect(source, environment);
    }
    @Bean HibernatePropertiesCustomizer standardNewsValidation(NewsSchemaCapabilities capability) {
        return properties -> {
            if (!capability.newsEnabled())
                properties.put("hibernate.hbm2ddl.schema_filter_provider", new NewsFilterProvider());
        };
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
