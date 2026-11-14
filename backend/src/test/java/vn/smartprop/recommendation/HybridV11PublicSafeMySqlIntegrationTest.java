package vn.smartprop.modules.recommendation;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

import java.math.BigDecimal;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Opt-in live test of the PUBLIC SAFE path (no demo/unverified data), read-only.
 * Separate context so the demo flag stays off exactly like production defaults.
 */
@EnabledIfEnvironmentVariable(named = "SMARTPROP_HYBRID_V11_LIVE", matches = "true")
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = {
    "spring.profiles.active=hybrid-local-existing-v13","app.local-lineage.require-complete=true",
    "app.broker-applications.enabled=false","app.profile.avatar-enabled=false","app.google.enabled=false",
    "server.address=127.0.0.1","app.server.transport=NIO2","spring.jpa.hibernate.ddl-auto=validate",
    "spring.flyway.enabled=false","spring.sql.init.mode=never","spring.datasource.hikari.read-only=true",
    "spring.datasource.hikari.connection-init-sql=SET SESSION TRANSACTION READ ONLY",
    "app.recommendation.tinix-enabled=true","app.recommendation.v11-enabled=true",
    "app.recommendation.allow-unverified-external=false","app.seed.enabled=false",
    "app.database-seed.enabled=false","app.import.external-listings=","app.email.enabled=false",
    "app.email.worker-enabled=false","debug=false","app.recommendation.demo-key="})
class HybridV11PublicSafeMySqlIntegrationTest {
    @DynamicPropertySource static void local(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", () -> "jdbc:mysql://127.0.0.1:3306/smartprop?connectionTimeZone=UTC");
        r.add("spring.datasource.username", () -> Objects.requireNonNull(System.getenv("DB_USER")));
        r.add("spring.datasource.password", () -> Objects.requireNonNull(System.getenv("DB_PASSWORD")));
        r.add("app.jwt-secret", () -> UUID.randomUUID().toString() + UUID.randomUUID());
    }

    @Autowired TestRestTemplate http;
    @Autowired JdbcTemplate jdbc;

    @Test void anonymousSafeCallReturnsOnlyVerifiedPublicRows() {
        // Baseline: the table really does contain TiniX research rows and unverified crawler rows.
        assertTrue(jdbc.queryForObject("SELECT COUNT(*) FROM tinix_dataset_records", Integer.class) > 0);
        assertEquals(0, jdbc.queryForObject(
            "SELECT COUNT(*) FROM external_listings WHERE verification_status='VERIFIED'", Integer.class),
            "no verified crawler rows exist locally, so SAFE must not invent any");

        var headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        var body = Map.of("budgetVnd", 2_000_000_000L, "purpose", "LIVING", "propertyType", "ALL", "limit", 10);
        var response = http.postForEntity("/api/v1/recommendations", new HttpEntity<>(body, headers), JsonNode.class);
        assertEquals(HttpStatus.OK, response.getStatusCode(), String.valueOf(response.getBody()));
        var json = Objects.requireNonNull(response.getBody());
        assertEquals("SAFE", json.path("mode").asText());
        assertEquals("HEURISTIC_V1_1", json.path("method").asText());
        assertFalse(json.toString().contains("TINIX_AI"));
        assertFalse(json.toString().contains("tinix:"));
        assertFalse(json.toString().contains("sampleListingCount"));
        for (var p : json.path("topProperties")) {
            assertEquals("PROPERTY", p.path("source").path("kind").asText());
            assertEquals("PLATFORM_PUBLISHED", p.path("verificationStatus").asText());
            assertTrue(p.path("priceVnd").decimalValue().compareTo(BigDecimal.valueOf(2_000_000_000L)) <= 0);
            assertTrue(p.path("score").asDouble() >= 0 && p.path("score").asDouble() <= 100);
            assertFalse(p.path("amenityEvidence").isMissingNode());
        }
        for (var a : json.path("topAreas")) {
            assertEquals(0, a.path("unverifiedCount").asInt());
            assertEquals(0, a.path("needsReviewCount").asInt());
        }
        System.out.println("SMARTPROP_V11_PUBLIC_SAFE: candidates=" + json.path("eligibleCandidateCount").asInt()
            + " returned=" + json.path("topProperties").size()
            + " areas=" + json.path("topAreas").size());
    }

    @Test void unknownBudgetHasNoResultsAndNoFabricatedAreas() {
        var headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        var body = Map.of("budgetVnd", 1_000_000L, "purpose", "LIVING", "propertyType", "ALL", "limit", 10);
        var response = http.postForEntity("/api/v1/recommendations", new HttpEntity<>(body, headers), JsonNode.class);
        assertEquals(HttpStatus.OK, response.getStatusCode());
        var json = Objects.requireNonNull(response.getBody());
        assertTrue(json.path("topProperties").isEmpty());
        assertTrue(json.path("topAreas").isEmpty());
        assertEquals(0, json.path("eligibleCandidateCount").asInt());
    }
}