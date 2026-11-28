package vn.smartprop.database;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;
import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles(Pr41TestFixture.PROFILE)
@EnabledIfEnvironmentVariable(named="PR41_LOCAL_V28_TEST",matches="true")
class NewsLocalLineageIT {
    @Autowired JdbcTemplate jdbc;
    @Autowired MockMvc mvc;
    @Autowired jakarta.persistence.EntityManagerFactory emf;
    @Test void completedLegacyLineageStartsWithFullHibernateValidationAndExactIdentity() throws Exception {
        vn.smartprop.testing.IsolatedDatabaseTestSafety.require(jdbc);assertTrue(emf.isOpen());
        try(var connection=jdbc.getDataSource().getConnection()){
            var properties=new java.util.Properties();
            try(var stream=java.nio.file.Files.newInputStream(java.nio.file.Path.of(System.getenv("SMARTPROP_TEST_FIXTURE_MANIFEST")))){properties.load(stream);}
            assertEquals(properties.getProperty("jdbcUrl"),connection.getMetaData().getURL());
        }
        var rows=jdbc.queryForList("SELECT version,type,checksum,success FROM flyway_schema_history ORDER BY installed_rank");
        MigrationLineageConfiguration.checkHistory(rows,true,true);
        assertEquals(java.util.List.of("13","14","17","18","19","20","21","22","23","24","25","26","27","28"),rows.stream().map(row->row.get("version")).toList());
        assertEquals(1,jdbc.queryForObject("SELECT COUNT(*) FROM information_schema.table_constraints WHERE constraint_schema=DATABASE() AND constraint_name='ck_news_sources_approved_reference' AND enforced='YES'",Integer.class));
        mvc.perform(get("/api/v1/news")).andExpect(status().isOk());
        mvc.perform(get("/api/v1/admin/news/sources")).andExpect(status().isUnauthorized());
    }
}
