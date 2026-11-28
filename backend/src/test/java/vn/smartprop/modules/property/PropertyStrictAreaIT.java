package vn.smartprop.modules.property;

import jakarta.persistence.EntityManager;
import java.nio.file.Path;
import java.sql.DriverManager;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.hibernate.SessionFactory;
import org.hibernate.boot.MetadataSources;
import org.hibernate.boot.registry.StandardServiceRegistryBuilder;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.data.jpa.repository.support.JpaRepositoryFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import vn.smartprop.common.Errors;
import vn.smartprop.modules.favorite.SavedProperty;
import vn.smartprop.modules.media.PropertyImageRepository;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Opt-in integration with a fresh, dedicated loopback MySQL instance. No Flyway or app runtime. */
@EnabledIfEnvironmentVariable(named = "RAG_AREA_FIXTURE_UUID", matches = "[a-f0-9-]{36}")
class PropertyStrictAreaIT {
    @Test
    void bindsAndAppliesExactBoundsBeforePaginationAndPreservesPublicEligibility() throws Exception {
        int port = Integer.parseInt(System.getenv("RAG_AREA_FIXTURE_PORT"));
        assertThat(port).isBetween(1024, 65535).isNotIn(3306, 3307, 3311);
        String url = "jdbc:mysql://127.0.0.1:" + port + "/rag_area_fixture?rewriteBatchedStatements=true";
        String user = "rag_area_fixture";
        String password = System.getenv("RAG_AREA_FIXTURE_PASSWORD");
        Path dataDir = Path.of(System.getenv("RAG_AREA_FIXTURE_DATADIR")).toRealPath();
        try (var connection = DriverManager.getConnection(url, user, password);
             var statement = connection.createStatement();
             var identity = statement.executeQuery("SELECT @@port, @@datadir, @@server_uuid, DATABASE()")) {
            assertThat(identity.next()).isTrue();
            assertThat(identity.getInt(1)).isEqualTo(port);
            assertThat(Path.of(identity.getString(2)).toRealPath()).isEqualTo(dataDir);
            assertThat(identity.getString(3)).isEqualTo(System.getenv("RAG_AREA_FIXTURE_UUID"));
            assertThat(identity.getString(4)).isEqualTo("rag_area_fixture");
        }
        var data = new DriverManagerDataSource(url, user, password);
        var jdbc = new JdbcTemplate(data);
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE()",
                                       Integer.class)).isZero();
        var registry = new StandardServiceRegistryBuilder().applySettings(Map.of(
            "hibernate.connection.datasource", data,
            "hibernate.hbm2ddl.auto", "create-drop",
            "hibernate.hbm2ddl.halt_on_error", "true"
        )).build();
        try (SessionFactory factory = new MetadataSources(registry).addAnnotatedClass(Property.class).addAnnotatedClass(SavedProperty.class)
                .buildMetadata().buildSessionFactory();
             EntityManager em = factory.createEntityManager()) {
            seed(jdbc);
            var repository = new JpaRepositoryFactory(em).getRepository(PropertyRepository.class);
            var service = mock(PropertyService.class);
            when(service.imageMap(anyList())).thenReturn(Map.of());
            when(service.coordinates(anyList())).thenReturn(Map.of());
            var api = MockMvcBuilders.standaloneSetup(new PropertySearchController(
                new PropertySearch(repository, service, mock(PropertyImageRepository.class))))
                .setControllerAdvice(new Errors()).build();

            // The 1,000 newer boundary rows cannot fill even the first page of a strict query.
            api.perform(get("/api/v1/properties").param("size", "1").param("maxArea", "80")
                    .param("maxAreaExclusive", "true")).andExpect(status().isOk())
                .andExpect(jsonPath("$.totalElements").value(2))
                .andExpect(jsonPath("$.items[0].areaSqmExact").value("79.00"));
            api.perform(get("/api/v1/properties").param("size", "1").param("minArea", "80")
                    .param("minAreaExclusive", "true")).andExpect(status().isOk())
                .andExpect(jsonPath("$.totalElements").value(2))
                .andExpect(jsonPath("$.items[0].areaSqmExact").value("81.00"));
            api.perform(get("/api/v1/properties").param("size", "1").param("minArea", "79.99")
                    .param("maxArea", "80.01")).andExpect(status().isOk())
                .andExpect(jsonPath("$.totalElements").value(1002))
                .andExpect(jsonPath("$.items[0].areaSqmExact").value("80.00"));
            api.perform(get("/api/v1/properties").param("size", "3").param("minArea", "79.99")
                    .param("minAreaExclusive", "true").param("maxArea", "80.01").param("maxAreaExclusive", "true"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.totalElements").value(1000))
                .andExpect(jsonPath("$.items[0].areaSqmExact").value("80.00"));
            api.perform(get("/api/v1/properties").param("minAreaExclusive", "true"))
                .andExpect(status().isBadRequest());
            api.perform(get("/api/v1/properties").param("maxAreaExclusive", "true"))
                .andExpect(status().isBadRequest());
            api.perform(get("/api/v1/properties").param("minArea", "80").param("maxArea", "80.00")
                    .param("maxAreaExclusive", "true")).andExpect(status().isBadRequest());
            api.perform(get("/api/v1/properties").param("minArea", "81").param("maxArea", "80"))
                .andExpect(status().isBadRequest());
        } finally {
            StandardServiceRegistryBuilder.destroy(registry);
        }
    }

    private static void seed(JdbcTemplate jdbc) {
        List<Object[]> rows = new ArrayList<>();
        for (int i = 1; i <= 1000; i++)
            rows.add(row(i, "80", "PUBLISHED", "2025-02-01 00:00:00", null, null));
        rows.add(row(1001, "79.99", "PUBLISHED", "2025-01-01 00:00:00", null, null));
        rows.add(row(1002, "79", "PUBLISHED", "2025-01-01 00:00:00", null, null));
        rows.add(row(1003, "80.01", "PUBLISHED", "2025-01-01 00:00:00", null, null));
        rows.add(row(1004, "81", "PUBLISHED", "2025-01-01 00:00:00", null, null));
        rows.add(row(1005, "78", "DRAFT", "2025-03-01 00:00:00", null, null));
        rows.add(row(1006, "82", "HIDDEN", "2025-03-01 00:00:00", null, null));
        rows.add(row(1007, "78", "PUBLISHED", "2025-03-01 00:00:00", "2025-04-01 00:00:00", null));
        rows.add(row(1008, "82", "PUBLISHED", "2025-03-01 00:00:00", null, "2025-04-01 00:00:00"));
        jdbc.batchUpdate("""
            INSERT INTO properties(id,listing_code,owner_id,title,property_type,transaction_type,price,currency,
                price_unit,area_sqm,city,location,declared_amenities,status,content_version,created_at,updated_at,
                expires_at,deleted_at)
            VALUES (?, ?, 1, 'Fixture', 'HOUSE', 'SALE', 2000000000, 'VND', 'TOTAL', ?, 'Da Nang',
                ST_GeomFromText('POINT(108.22 16.06)',4326,'axis-order=long-lat'), JSON_ARRAY(), ?, 1, ?,
                '2025-03-01 00:00:00', ?, ?)
            """, rows);
    }

    private static Object[] row(int i, String area, String status, String created, String expires, String deleted) {
        return new Object[] {"aaaaaaaa-bbbb-cccc-dddd-%012d".formatted(i), "FIXTURE-" + i, area, status,
                             created, expires, deleted};
    }
}
