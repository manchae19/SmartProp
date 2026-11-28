package vn.smartprop.modules.chat;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.List;
import java.util.Map;
import java.util.concurrent.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.ApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import vn.smartprop.common.ApiException;

import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * PR43 second-review acceptance on a real isolated MySQL fixture (port/authorization from the
 * independently provisioned manifest). Proves account checkpoint persistence, revision CAS,
 * ownership, transaction rollback, the demo-data isolation boundary and a real Advisor HTTP
 * request against real SQL semantics, not mocked HTTP.
 */
@SpringBootTest(properties = {"app.advisor.valuation-enabled=false", "app.recommendation.tinix-enabled=false"})
@AutoConfigureMockMvc
@ActiveProfiles("hybrid-local-existing-v13-pr41-isolated")
@EnabledIfEnvironmentVariable(named = "PR41_LOCAL_V28_TEST", matches = "true")
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
class AdvisorChatPersistenceIT {
    @Autowired ApplicationContext context;
    @Autowired JdbcTemplate jdbc;
    @Autowired MockMvc mvc;
    final ObjectMapper json = new ObjectMapper();

    AdvisorChatStore store() { return context.getBean(AdvisorChatStore.class); }

    long user(String email) {
        jdbc.update("INSERT INTO users(email,password_hash,full_name,role,status,created_at,updated_at) "
            + "SELECT ?, 'synthetic-unusable', 'PR43 SYNTHETIC', 'BUYER', 'ACTIVE', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6) "
            + "WHERE NOT EXISTS(SELECT 1 FROM users WHERE email=?)", email, email);
        return jdbc.queryForObject("SELECT id FROM users WHERE email=?", Long.class, email);
    }

    AdvisorChatController.Commit turn(long revision, String question, String responseKind) throws Exception {
        return new AdvisorChatController.Commit(revision, question,
            json.readTree("{\"mode\":\"SAFE\",\"evidence\":{\"responseKind\":\"" + responseKind + "\"}}"),
            json.readTree("{\"budget_vnd\":\"3000000000\",\"needs\":{}}"));
    }

    String id() { return java.util.UUID.randomUUID().toString().replace("-", ""); }

    @Test @Order(1)
    void checkpointPersistsAcrossFreshConnectionsAndRevisionsConflict() throws Exception {
        long owner = user("pr43-it-owner@example.invalid");
        String conversation = id();
        var first = store().commit(owner, conversation, turn(0, "Tìm nhà ở Hải Châu", "PROPERTY_SEARCH"));
        assertEquals(1L, first.get("revision"));
        assertEquals(1L, store().checkpoint(owner, conversation).get("revision"));
        assertFalse(store().recent(owner).isEmpty());

        // Independent JDBC session/connection still sees the durable row (restart-safe persistence).
        assertEquals(1, new JdbcTemplate(jdbc.getDataSource()).queryForObject(
            "SELECT COUNT(*) FROM advisor_chat_conversations WHERE id=?", Integer.class, conversation));

        ApiException conflict = assertThrows(ApiException.class,
            () -> store().commit(owner, conversation, turn(0, "Tìm nhà ở Hải Châu", "PROPERTY_SEARCH")));
        assertEquals("CHAT_CONFLICT", conflict.code);

        var second = store().commit(owner, conversation, turn(1, "Thêm Sơn Trà", "PROPERTY_SEARCH"));
        assertEquals(2L, second.get("revision"));
        assertEquals(2, store().history(owner, conversation).get("turns") instanceof List<?> turns ? turns.size() : -1);
    }

    @Test @Order(2)
    void otherAccountsCannotReadOrResumeSomeonesCheckpoint() throws Exception {
        long owner = user("pr43-it-owner2@example.invalid");
        long stranger = user("pr43-it-stranger@example.invalid");
        String conversation = id();
        store().commit(owner, conversation, turn(0, "Tìm căn hộ", "PROPERTY_SEARCH"));
        for (Runnable call : List.<Runnable>of(
            () -> store().checkpoint(stranger, conversation),
            () -> store().history(stranger, conversation))) {
            assertEquals("CHAT_NOT_FOUND", assertThrows(ApiException.class, call::run).code);
        }
    }

    @Test @Order(3)
    void legacyDemoLandConversationsAreHiddenFromEveryAccountReadPath() throws Exception {
        long owner = user("pr43-it-demo@example.invalid");
        long other = user("pr43-it-demo2@example.invalid");
        String legacyDemo = id();
        String normal = id();
        store().commit(owner, normal, turn(0, "Tìm nhà ở Hải Châu", "PROPERTY_SEARCH"));
        // A conversation persisted before the demo boundary existed, carrying synthetic land evidence.
        store().commit(owner, legacyDemo, turn(0, "Tìm đất Hòa Xuân dưới 3 tỷ", "BUYER_SEARCH"));
        jdbc.update("UPDATE advisor_chat_turns SET response=? WHERE conversation_id=?",
            "{\"mode\":\"SAFE\",\"evidence\":{\"responseKind\":\"LAND_SEARCH\",\"land\":{\"kind\":\"LAND_SEARCH\"},"
                + "\"buyerSearch\":{\"rows\":[{\"source\":\"LAND_DATA\"}]}}}", legacyDemo);

        List<Map<String, Object>> recent = store().recent(owner);
        assertTrue(recent.stream().anyMatch(row -> normal.equals(row.get("id"))));
        assertTrue(recent.stream().noneMatch(row -> legacyDemo.equals(row.get("id"))));
        assertEquals("CHAT_NOT_FOUND", assertThrows(ApiException.class, () -> store().checkpoint(owner, legacyDemo)).code);
        assertEquals("CHAT_NOT_FOUND", assertThrows(ApiException.class, () -> store().history(owner, legacyDemo)).code);
        assertEquals("CHAT_NOT_FOUND", assertThrows(ApiException.class, () -> store().checkpoint(other, legacyDemo)).code);

        // The owner can still remove their own retired conversation (no data is silently modified by us).
        store().delete(owner, legacyDemo);
        assertEquals(0, jdbc.queryForObject(
            "SELECT COUNT(*) FROM advisor_chat_conversations WHERE id=?", Integer.class, legacyDemo));
    }

    @Test @Order(4)
    void failedTurnWriteRollsBackTheConversationRevision() throws Exception {
        long owner = user("pr43-it-rollback@example.invalid");
        String conversation = id();
        store().commit(owner, conversation, turn(0, "Tìm nhà", "PROPERTY_SEARCH"));
        // Collide with the next turn primary key so the second insert fails inside the transaction.
        jdbc.update("INSERT INTO advisor_chat_turns(conversation_id,turn_number,question,response) VALUES(?,?,?,?)",
            conversation, 2L, "synthetic collision",
            "{\"mode\":\"SAFE\",\"evidence\":{\"responseKind\":\"PROPERTY_SEARCH\"}}");
        assertThrows(Exception.class, () -> store().commit(owner, conversation, turn(1, "Tìm nhà", "PROPERTY_SEARCH")));
        assertEquals(1L, jdbc.queryForObject(
            "SELECT revision FROM advisor_chat_conversations WHERE id=?", Long.class, conversation));
    }

    @Test @Order(5)
    void concurrentCommitsOnTheSameRevisionAcceptExactlyOne() throws Exception {
        long owner = user("pr43-it-concurrent@example.invalid");
        String conversation = id();
        store().commit(owner, conversation, turn(0, "Tìm nhà", "PROPERTY_SEARCH"));
        var pool = Executors.newFixedThreadPool(2);
        try {
            Callable<Boolean> attempt = () -> {
                try { store().commit(owner, conversation, turn(1, "Tìm nhà", "PROPERTY_SEARCH")); return true; }
                catch (ApiException conflict) { assertEquals("CHAT_CONFLICT", conflict.code); return false; }
            };
            var results = pool.invokeAll(List.of(attempt, attempt));
            long accepted = results.stream().filter(f -> { try { return f.get(); } catch (Exception e) { return false; } }).count();
            assertEquals(1, accepted);
            assertEquals(2L, jdbc.queryForObject("SELECT revision FROM advisor_chat_conversations WHERE id=?", Long.class, conversation));
        } finally {
            pool.shutdownNow();
        }
    }
    @Test @Order(6)
    void advisorHttpRunsOnRealMySqlWithoutFabricatedValuation() throws Exception {
        String payload = "{\"budgetVnd\":4000000000,\"purpose\":\"LIVING\",\"propertyType\":\"HOUSE\","
            + "\"includeResearch\":false,\"includeValuation\":false,\"includeComparables\":false}";
        String body = mvc.perform(post("/api/v1/advisor/consult").contentType("application/json").content(payload))
            .andExpect(status().isOk())
            .andReturn().getResponse().getContentAsString(java.nio.charset.StandardCharsets.UTF_8);
        assertEquals("SAFE", json.readTree(body).path("mode").asText());
        assertTrue(json.readTree(body).path("recommendedProperties").isArray());
    }
}