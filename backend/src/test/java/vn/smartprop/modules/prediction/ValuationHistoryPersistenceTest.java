package vn.smartprop.modules.prediction;

import com.fasterxml.jackson.databind.*;
import java.util.*;
import java.util.concurrent.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import static org.junit.jupiter.api.Assertions.*;

/** Opt-in only: the harness supplies a new schema on a workspace-local MySQL instance. */
@EnabledIfEnvironmentVariable(named="SMARTPROP_HISTORY_TEST_URL",matches="jdbc:mysql://127\\.0\\.0\\.1:13[0-9]{3}/smartprop_history_[a-z0-9]+.*")
class ValuationHistoryPersistenceTest {
    static JdbcTemplate jdbc;
    static final ObjectMapper json=new ObjectMapper();
    ValuationHistoryRepository repository;
    long owner;
    @BeforeAll static void connect() {
        var source=new DriverManagerDataSource(System.getenv("SMARTPROP_HISTORY_TEST_URL"),"root","");
        jdbc=new JdbcTemplate(source);
    }
    @BeforeEach void prepareOwner() {
        repository=new ValuationHistoryRepository(jdbc,json);
        String email=UUID.randomUUID()+"@example.test";
        jdbc.update("INSERT INTO users(email,password_hash,full_name,role,status,created_at,updated_at) VALUES(?,?,?,'BUYER','ACTIVE',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6))",
            email,"SYNTHETIC_NOT_A_LOGIN_HASH","Synthetic history owner");
        owner=jdbc.queryForObject("SELECT id FROM users WHERE email=?",Long.class,email);
    }
    JsonNode value(String text) throws Exception { return json.readTree(text); }
    @Test void snapshotSurvivesRepositoryReopenAndIsPrivateToTheOwner() throws Exception {
        String key=UUID.randomUUID().toString();
        repository.insert(owner,key,"a".repeat(64),value("{\"area_sqm\":80}"),value("{\"predicted_asking_price_vnd\":3000000000}"));
        var reopened=new ValuationHistoryRepository(jdbc,json);
        var entry=reopened.byKey(owner,key).orElseThrow().entry();
        assertTrue(java.time.Duration.between(entry.createdAt(),java.time.Instant.now()).abs().toSeconds()<60,
            "DATETIME snapshot must round-trip in UTC independently of the JVM timezone");
        assertTrue(entry.prediction().isObject());
        assertEquals(3000000000L,entry.prediction().path("predicted_asking_price_vnd").asLong());
        assertTrue(reopened.byId(owner+1000000,entry.id()).isEmpty());
        assertFalse(reopened.delete(owner+1000000,entry.id()));
        assertEquals(1,reopened.list(owner,0,10).totalElements());
        assertTrue(reopened.delete(owner,entry.id()));
        assertEquals(0,reopened.list(owner,0,10).totalElements());
    }
    @Test void concurrentRetriesProduceOneImmutableSnapshot() throws Exception {
        String key=UUID.randomUUID().toString();
        JsonNode input=value("{\"area_sqm\":80}"), prediction=value("{\"predicted_asking_price_vnd\":3000000000}");
        try(var workers=Executors.newFixedThreadPool(4)) {
            List<Future<?>> requests=new ArrayList<>();
            for(int i=0;i<8;i++) requests.add(workers.submit(()->repository.insert(owner,key,"b".repeat(64),input,prediction)));
            for(var result:requests)result.get(10,TimeUnit.SECONDS);
        }
        assertEquals(1,repository.list(owner,0,10).totalElements());
        String id=repository.byKey(owner,key).orElseThrow().entry().id();
        repository.insert(owner,key,"c".repeat(64),value("{\"area_sqm\":90}"),value("{\"predicted_asking_price_vnd\":1}"));
        var unchanged=repository.byKey(owner,key).orElseThrow();
        assertEquals(id,unchanged.entry().id());
        assertEquals("b".repeat(64),unchanged.fingerprint());
        assertEquals(3000000000L,unchanged.entry().prediction().path("predicted_asking_price_vnd").asLong());
    }
    @Test void foreignKeyPreventsHistoryForANonexistentUser() throws Exception {
        assertThrows(DataIntegrityViolationException.class,()->repository.insert(-1L,UUID.randomUUID().toString(),"d".repeat(64),json.createObjectNode(),json.createObjectNode()));
    }
}
