package vn.smartprop.database;

import javax.sql.DataSource;
import java.nio.file.*;
import java.util.*;
import org.flywaydb.core.Flyway;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.beans.factory.InitializingBean;
import org.springframework.beans.factory.config.BeanFactoryPostProcessor;
import org.springframework.beans.factory.support.AbstractBeanDefinition;
import org.springframework.core.env.Environment;
import org.springframework.jdbc.core.JdbcTemplate;

/** Explicit isolated simulation: replace only deployment identity binding, keep real policy,
 * ordered/pending/checksum validation, real capability resolution and Hibernate validation. */
@TestConfiguration(proxyBeanMethods=false)
@ConditionalOnProperty(name="smartprop.test.native-profile")
public class AdvisorFixtureRuntimeConfiguration {
    @Bean static BeanFactoryPostProcessor isolatedRuntimeBinding() {
        return factory -> {
            ((AbstractBeanDefinition)factory.getBeanDefinition("newsSchemaCapabilities")).setInstanceSupplier(()->{
                var env=factory.getBean(Environment.class);var jdbc=new JdbcTemplate(factory.getBean(DataSource.class));
                var history=validate(jdbc,env);
                return NewsSchemaCapabilities.resolveValidated(jdbc,history,true,env.getProperty("app.local-lineage.require-complete",Boolean.class,true));
            });
            ((AbstractBeanDefinition)factory.getBeanDefinition("validateSelectedMigrationLineage")).setInstanceSupplier(()->
                (InitializingBean)()->validate(new JdbcTemplate(factory.getBean(DataSource.class)),factory.getBean(Environment.class)));
        };
    }
    static List<Map<String,Object>> validate(JdbcTemplate jdbc,Environment env) {
        String url=env.getProperty("spring.datasource.url");
        var fixture=AdvisorFixtureBoundary.AUTHORIZED.get(url);if(fixture==null)throw new IllegalStateException("No pre-connection authorization");
        vn.smartprop.testing.IsolatedDatabaseTestSafety.require(jdbc,Path.of(env.getProperty("smartprop.test.fixture-manifest")),System.getenv("SMARTPROP_TEST_FIXTURE_AUTHORIZATION"),url);
        boolean complete=env.getProperty("app.local-lineage.require-complete",Boolean.class,true);
        var history=jdbc.queryForList("SELECT version,type,checksum,success FROM flyway_schema_history ORDER BY installed_rank");
        MigrationLineageConfiguration.checkHistory(history,true,complete);
        String locations=env.getProperty("smartprop.test.validation-locations","classpath:database/legacy-hybrid-local,classpath:database/research-migrations");
        var flyway=Flyway.configure().dataSource(jdbc.getDataSource()).locations(locations.split(","))
            .target(MigrationLineageConfiguration.target(true)).createSchemas(false).baselineOnMigrate(false).cleanDisabled(true)
            .ignoreMigrationPatterns("*:pending").validateMigrationNaming(true).load();
        var pending=Arrays.stream(flyway.info().pending()).map(m->m.getVersion().getVersion()).toList();
        MigrationLineageConfiguration.checkPendingLocalMigrations(pending,complete,env.getProperty("app.recommendation.tinix-enabled",Boolean.class,false));
        MigrationLineageConfiguration.checkRuntimePendingLocalMigrations(pending,complete);
        flyway.validate();return history;
    }
}
