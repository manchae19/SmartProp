package vn.smartprop.database;

import java.util.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.WebApplicationType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import static org.junit.jupiter.api.Assertions.*;

/** Actual Spring/Hibernate startup on deliberately broken, owned synthetic schema; restore in finally. */
@EnabledIfEnvironmentVariable(named="PR41_LOCAL_V28_TEST",matches="true")
class NewsBrokenSchemaRuntimeIT {
    JdbcTemplate jdbc;
    @BeforeEach void isolated() {
        jdbc=new JdbcTemplate(new DriverManagerDataSource(System.getenv("DB_URL"),System.getenv("DB_USER"),System.getenv("DB_PASSWORD")));
        vn.smartprop.testing.IsolatedDatabaseTestSafety.require(jdbc);
        assertEquals(0,jdbc.queryForObject("SELECT COUNT(*) FROM news_articles",Integer.class));
    }
    void refused(String expected) {
        Exception error=assertThrows(Exception.class,()->{
            try(var context=new SpringApplicationBuilder(vn.smartprop.SmartPropApplication.class)
                .web(WebApplicationType.SERVLET).profiles(Pr41TestFixture.PROFILE)
                .run("--server.address=127.0.0.1","--server.port=0","--spring.main.banner-mode=off")) {
                fail("Broken schema started");
            }
        });
        StringBuilder messages=new StringBuilder();for(Throwable t=error;t!=null;t=t.getCause())messages.append(t.getMessage()).append('\n');
        assertTrue(messages.toString().contains(expected),messages.toString());
    }
    @Test void actualMysqlNormalizedV28DefinitionIsAccepted() {
        vn.smartprop.testing.IsolatedDatabaseTestSafety.require(jdbc);
        NewsRightsConstraintVerifier.requireValid(jdbc);
        String clause=jdbc.queryForObject("SELECT check_clause FROM information_schema.check_constraints WHERE constraint_schema=DATABASE() AND constraint_name=?",String.class,NewsRightsConstraintVerifier.CONSTRAINT);
        assertNotNull(clause);
    }
    @Test void sameNameCheckOnWrongTableFailsClosed() {
        jdbc.execute("ALTER TABLE news_sources DROP CHECK ck_news_sources_approved_reference");
        jdbc.execute("ALTER TABLE news_articles ADD CONSTRAINT ck_news_sources_approved_reference CHECK (1=1)");
        try { refused("Required V28 rights constraint is attached to the wrong table"); }
        finally {
            jdbc.execute("ALTER TABLE news_articles DROP CHECK ck_news_sources_approved_reference");
            jdbc.execute("ALTER TABLE news_sources ADD CONSTRAINT ck_news_sources_approved_reference CHECK (rights_review_status <> 'APPROVED' OR (rights_reference IS NOT NULL AND REGEXP_LIKE(rights_reference, '[^[:space:]]')))");
        }
    }
    @Test void sameNameEnforcedButIncorrectExpressionFailsClosed() {
        jdbc.execute("ALTER TABLE news_sources DROP CHECK ck_news_sources_approved_reference");
        jdbc.execute("ALTER TABLE news_sources ADD CONSTRAINT ck_news_sources_approved_reference CHECK (1=1)");
        try { refused("Required V28 rights constraint has an invalid definition"); }
        finally {
            jdbc.execute("ALTER TABLE news_sources DROP CHECK ck_news_sources_approved_reference");
            jdbc.execute("ALTER TABLE news_sources ADD CONSTRAINT ck_news_sources_approved_reference CHECK (rights_review_status <> 'APPROVED' OR (rights_reference IS NOT NULL AND REGEXP_LIKE(rights_reference, '[^[:space:]]')))");
        }
    }
    @Test void weakenedSameNameExpressionFailsClosed() {
        jdbc.execute("ALTER TABLE news_sources DROP CHECK ck_news_sources_approved_reference");
        jdbc.execute("ALTER TABLE news_sources ADD CONSTRAINT ck_news_sources_approved_reference CHECK (rights_review_status <> 'APPROVED' OR rights_reference IS NOT NULL)");
        try { refused("Required V28 rights constraint has an incorrect definition"); }
        finally {
            jdbc.execute("ALTER TABLE news_sources DROP CHECK ck_news_sources_approved_reference");
            jdbc.execute("ALTER TABLE news_sources ADD CONSTRAINT ck_news_sources_approved_reference CHECK (rights_review_status <> 'APPROVED' OR (rights_reference IS NOT NULL AND REGEXP_LIKE(rights_reference, '[^[:space:]]')))");
        }
    }
    @Test void missingNewsTableCannotEnableAValidationFilter() {
        jdbc.execute("RENAME TABLE news_articles TO pr41_held_news_articles");
        try{refused("News tables do not match");}
        finally{jdbc.execute("RENAME TABLE pr41_held_news_articles TO news_articles");}
    }
    @Test void newsColumnsRemainSubjectToRealHibernateValidation() {
        jdbc.execute("ALTER TABLE news_articles RENAME COLUMN title TO pr41_held_title");
        try{refused("missing column [title]");}
        finally{jdbc.execute("ALTER TABLE news_articles RENAME COLUMN pr41_held_title TO title");}
    }
    @Test void missingV28ConstraintFailsClosedEvenWithIntactHistory() {
        jdbc.execute("ALTER TABLE news_sources ALTER CHECK ck_news_sources_approved_reference NOT ENFORCED");
        try{refused("unenforced");}
        finally{jdbc.execute("ALTER TABLE news_sources ALTER CHECK ck_news_sources_approved_reference ENFORCED");}
    }
}
