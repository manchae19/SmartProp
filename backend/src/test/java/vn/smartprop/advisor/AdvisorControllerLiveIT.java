package vn.smartprop.advisor;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.charset.StandardCharsets;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.RequestPostProcessor;
import vn.smartprop.modules.user.User;
import vn.smartprop.modules.user.UserRepository;

/**
 * Live end-to-end Spring Boot + Real MySQL + Live FastAPI V6 integration tests for Step 21.3.
 * Never writes to MySQL, never mocks database candidates, and strictly verifies protected holdout exclusion.
 */
@SpringBootTest(properties = {
    "app.recommendation.v11-enabled=true",
    "app.recommendation.tinix-enabled=true",
    "app.advisor.valuation-enabled=true",
    "app.advisor.valuation-base-url=http://127.0.0.1:8000"
})
@AutoConfigureMockMvc
@EnabledIfEnvironmentVariable(named = "DB_URL", matches = ".+")
class AdvisorControllerLiveIT {

    @Autowired MockMvc mvc;
    @Autowired UserRepository users;
    @Autowired JdbcTemplate jdbc;
    @Autowired ObjectMapper json;

    private RequestPostProcessor roleActor(User.Role role) {
        List<User> matches = users.findAll().stream()
            .filter(u -> u.deletedAt == null && u.status == User.Status.ACTIVE && u.role == role)
            .toList();
        assertThat(matches).as("active user with role " + role + " must exist in MySQL").isNotEmpty();
        User u = matches.get(0);
        return jwt().jwt(j -> j.subject(String.valueOf(u.id)).claim("ver", u.tokenVersion))
            .authorities(new SimpleGrantedAuthority("ROLE_" + u.role.name()));
    }

    @Test
    void researchModeEnforcesStrictAdminAuthorization() throws Exception {
        String payload = """
            {"budgetVnd":4000000000,"purpose":"LIVING","propertyType":"HOUSE","includeResearch":true}
            """;

        // 1. Unauthenticated -> 403
        mvc.perform(post("/api/v1/advisor/consult")
                .contentType(MediaType.APPLICATION_JSON).content(payload))
            .andExpect(status().isForbidden());

        // 2. Non-existent token subject -> 401
        mvc.perform(post("/api/v1/advisor/consult")
                .with(jwt().jwt(j -> j.subject("999999")).authorities(new SimpleGrantedAuthority("ROLE_BUYER")))
                .contentType(MediaType.APPLICATION_JSON).content(payload))
            .andExpect(status().isUnauthorized());

        // 3. Real active BROKER -> 403 (research mode is strictly ADMIN)
        mvc.perform(post("/api/v1/advisor/consult")
                .with(roleActor(User.Role.BROKER))
                .contentType(MediaType.APPLICATION_JSON).content(payload))
            .andExpect(status().isForbidden());
    }

    @Test
    void safeConsultAcrossBudgetsPurposesAndAllFiltersWithLiveV6AndHoldoutProof() throws Exception {
        // Scenario A: Medium budget (4.5B) + 15% flexible ceiling, LIVING, propertyType=ALL, district=ALL
        long t0 = System.nanoTime();
        String bodyMedium = mvc.perform(post("/api/v1/advisor/consult")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "budgetVnd": 4500000000,
                      "budgetFlexibilityPct": 15,
                      "purpose": "LIVING",
                      "propertyType": "ALL",
                      "district": "ALL",
                      "limit": 5,
                      "includeComparables": true,
                      "includeValuation": true,
                      "includeResearch": false
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(header().string("Cache-Control", "no-store"))
            .andExpect(jsonPath("$.advisorVersion").value("ADVISOR_ORCHESTRATOR_V1"))
            .andExpect(jsonPath("$.mode").value("SAFE"))
            .andExpect(jsonPath("$.recommendationMethod").value("HEURISTIC_V1_1"))
            .andExpect(jsonPath("$.criteria.effectiveCeilingVnd").value(5175000000L))
            .andExpect(jsonPath("$.serviceStatus.valuationService").value("AVAILABLE"))
            .andExpect(jsonPath("$.serviceStatus.partialResult").value(false))
            .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        long coldMs = (System.nanoTime() - t0) / 1_000_000L;

        // Warm call latency measurement
        long t1 = System.nanoTime();
        mvc.perform(post("/api/v1/advisor/consult")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"budgetVnd":4500000000,"budgetFlexibilityPct":15,"purpose":"LIVING","propertyType":"ALL","limit":5}
                    """))
            .andExpect(status().isOk());
        long warmMs = (System.nanoTime() - t1) / 1_000_000L;
        System.out.printf("[STEP 21.3 BENCHMARK] SAFE consult cold=%dms, warm=%dms%n", coldMs, warmMs);

        JsonNode root = json.readTree(bodyMedium);
        assertThat(root.path("topAreas").size()).isBetween(1, 5);
        assertThat(root.path("recommendedProperties").size()).isBetween(1, 5);
        JsonNode firstProp = root.path("recommendedProperties").get(0);
        System.out.printf(
            "[STEP 21.3 REAL DATA] eligible=%d, topArea=%s (score=%.1f), topProp=%s price=%s v6Est=%s comps=%d%n",
            root.path("eligibleCandidateCount").asInt(),
            root.path("topAreas").get(0).path("district").asText(),
            root.path("topAreas").get(0).path("score").asDouble(),
            firstProp.path("id").asText(),
            firstProp.path("priceVnd").asText(),
            firstProp.path("valuationEvidence").path("predictedAskingPriceVnd").asText(),
            firstProp.path("comparableEvidence").path("candidateCount").asInt()
        );

        // Zero PII leak check
        assertThat(bodyMedium)
            .doesNotContain("contactPhone", "contactEmail", "streetAddress", "addressText", "sampleListingCount");

        int liveValuations = 0;
        for (JsonNode prop : root.path("recommendedProperties")) {
            // SAFE mode must never return TINIX_AI as a recommended listing
            assertThat(prop.path("liveListing").asBoolean()).isTrue();
            assertThat(prop.path("researchReference").asBoolean()).isFalse();
            assertThat(prop.path("source").path("kind").asText()).isNotEqualTo("TINIX_AI");
            assertNoProtectedHoldoutProperty(prop);

            JsonNode val = prop.path("valuationEvidence");
            if (val.path("available").asBoolean()) {
                liveValuations++;
                assertThat(val.path("modelVersion").asText()).isEqualTo("v6");
                assertThat(val.path("modelRun").asText()).isEqualTo("b4b1339d3f35857e");
                assertThat(val.path("predictedAskingPriceVnd").asLong()).isGreaterThan(0L);
                assertThat(val.path("shapExplanation").path("topFactors").isArray()).isTrue();
                assertThat(val.path("shapExplanation").path("topFactors").size()).isGreaterThan(0);
            }

            JsonNode comp = prop.path("comparableEvidence");
            for (JsonNode c : comp.path("comparables")) {
                assertNoProtectedHoldoutComparable(c);
                if ("TINIX_RESEARCH".equals(c.path("sourceKind").asText())) {
                    assertThat(c.path("researchReference").asBoolean()).isTrue();
                    assertThat(c.path("liveListing").asBoolean()).isFalse();
                    assertThat(c.path("listingUrl").isNull()).isTrue();
                    assertThat(c.path("datasetLicense").asText()).isEqualTo("CC BY-NC 4.0");
                }
            }
        }
        assertThat(liveValuations).as("at least one real property must receive live V6 + TreeSHAP valuation").isGreaterThan(0);

        // Scenario B: Small budget (900M) + INVESTMENT purpose
        String bodySmall = mvc.perform(post("/api/v1/advisor/consult")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"budgetVnd":900000000,"budgetFlexibilityPct":10,"purpose":"INVESTMENT","propertyType":"ALL","limit":5}
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.criteria.purpose").value("INVESTMENT"))
            .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        JsonNode smallNode = json.readTree(bodySmall);
        assertThat(smallNode.path("recommendedProperties").size()).isGreaterThan(0);

        // Scenario C: Large budget (25B) + RENTAL purpose
        String bodyLarge = mvc.perform(post("/api/v1/advisor/consult")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"budgetVnd":25000000000,"budgetFlexibilityPct":0,"purpose":"RENTAL","propertyType":"ALL","limit":5}
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.criteria.purpose").value("RENTAL"))
            .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        JsonNode largeNode = json.readTree(bodyLarge);
        assertThat(largeNode.path("recommendedProperties").size()).isGreaterThan(0);

        // Scenario D: Zero-candidate budget (50M VND) -> graceful empty result, zero fabrication
        mvc.perform(post("/api/v1/advisor/consult")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"budgetVnd":50000000,"budgetFlexibilityPct":0,"purpose":"LIVING","propertyType":"HOUSE","limit":5}
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.recommendedProperties").isEmpty())
            .andExpect(jsonPath("$.eligibleCandidateCount").value(0));
    }

    @Test
    void adminInternalResearchModeLabelsTinixStrictlyAndExcludesAllHoldouts() throws Exception {
        String body = mvc.perform(post("/api/v1/advisor/consult")
                .with(roleActor(User.Role.ADMIN))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "budgetVnd": 3200000000,
                      "budgetFlexibilityPct": 0,
                      "purpose": "INVESTMENT",
                      "propertyType": "HOUSE",
                      "district": "Thanh Khê",
                      "limit": 10,
                      "includeComparables": true,
                      "includeValuation": true,
                      "includeResearch": true
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.mode").value("INTERNAL_RESEARCH"))
            .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);

        JsonNode root = json.readTree(body);
        assertThat(root.path("recommendedProperties").size()).isGreaterThan(0);

        for (JsonNode prop : root.path("recommendedProperties")) {
            assertNoProtectedHoldoutProperty(prop);
            if ("TINIX_AI".equals(prop.path("source").path("kind").asText())) {
                assertThat(prop.path("researchReference").asBoolean()).isTrue();
                assertThat(prop.path("liveListing").asBoolean()).isFalse();
                assertThat(prop.path("source").path("detailUrl").isNull()).isTrue();
                assertThat(prop.path("valuationEvidence").path("status").asText()).isEqualTo("SKIPPED_RESEARCH_RECORD");
                assertThat(prop.path("valuationEvidence").path("available").asBoolean()).isFalse();
            }
            for (JsonNode c : prop.path("comparableEvidence").path("comparables")) {
                assertNoProtectedHoldoutComparable(c);
            }
        }
    }

    private void assertNoProtectedHoldoutProperty(JsonNode prop) {
        String kind = prop.path("source").path("kind").asText();
        String key = prop.path("source").path("recordKey").asText();
        if ("PROPERTY".equals(kind)) {
            var row = jdbc.queryForMap("SELECT status, deleted_at FROM properties WHERE id = ?", key);
            assertThat(row.get("status")).isEqualTo("PUBLISHED");
            assertThat(row.get("deleted_at")).isNull();
        } else if ("EXTERNAL".equals(kind)) {
            var row = jdbc.queryForMap("SELECT is_protected_holdout FROM external_listings WHERE id = ?", Long.valueOf(key));
            assertThat(asIntFlag(row.get("is_protected_holdout"))).isZero();
        } else if ("TINIX_AI".equals(kind)) {
            var row = jdbc.queryForMap(
                "SELECT is_protected_holdout, quality_status FROM tinix_dataset_records WHERE internal_id = ?", key);
            assertThat(asIntFlag(row.get("is_protected_holdout"))).isZero();
            assertThat(row.get("quality_status")).isEqualTo("HYBRID_ELIGIBLE_RESEARCH");
        }
    }

    private void assertNoProtectedHoldoutComparable(JsonNode comp) {
        String kind = comp.path("sourceKind").asText();
        String id = comp.path("candidateId").asText();
        if ("SMARTPROP".equals(kind)) {
            String rawId = id.startsWith("property:") ? id.substring("property:".length()) : id;
            var row = jdbc.queryForMap("SELECT status, deleted_at FROM properties WHERE id = ?", rawId);
            assertThat(row.get("status")).isEqualTo("PUBLISHED");
            assertThat(row.get("deleted_at")).isNull();
        } else if ("EXTERNAL_LISTING".equals(kind)) {
            String rawId = id.replaceFirst("^(external:|ext-)", "");
            long extId = Long.parseLong(rawId);
            var row = jdbc.queryForMap("SELECT is_protected_holdout FROM external_listings WHERE id = ?", extId);
            assertThat(asIntFlag(row.get("is_protected_holdout"))).isZero();
        } else if ("TINIX_RESEARCH".equals(kind)) {
            var row = jdbc.queryForMap(
                "SELECT is_protected_holdout, is_duplicate_representative FROM tinix_dataset_records WHERE internal_id = ?", id);
            assertThat(asIntFlag(row.get("is_protected_holdout"))).isZero();
            assertThat(asIntFlag(row.get("is_duplicate_representative"))).isEqualTo(1);
        }
    }

    private static int asIntFlag(Object value) {
        if (value instanceof Boolean b) return b ? 1 : 0;
        if (value instanceof Number n) return n.intValue();
        throw new IllegalArgumentException("Unexpected flag type: " + value);
    }
}
