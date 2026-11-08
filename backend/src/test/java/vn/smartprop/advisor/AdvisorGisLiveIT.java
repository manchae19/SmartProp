package vn.smartprop.advisor;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.charset.StandardCharsets;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.RequestPostProcessor;
import vn.smartprop.modules.user.User;
import vn.smartprop.modules.user.UserRepository;

/**
 * Step 21.4D (REAL MYSQL 8.0.46 INTEGRATION SUITE) — End-to-End Advisor GIS Contract,
 * Purpose-Aware Spatial Explanations, Administrative Normalization & Research Fallback Proof.
 */
@SpringBootTest(properties = {
    "app.recommendation.v11-enabled=true",
    "app.recommendation.tinix-enabled=true",
    "app.advisor.valuation-enabled=false"
})
@AutoConfigureMockMvc
@EnabledIfEnvironmentVariable(named = "DB_URL", matches = ".+")
class AdvisorGisLiveIT {

    @Autowired MockMvc mvc;
    @Autowired ObjectMapper json;
    @Autowired UserRepository users;

    private RequestPostProcessor adminActor() {
        List<User> admins = users.findAll().stream()
            .filter(u -> u.deletedAt == null && u.status == User.Status.ACTIVE && u.role == User.Role.ADMIN)
            .toList();
        assertThat(admins).isNotEmpty();
        User u = admins.getFirst();
        return jwt().jwt(j -> j.subject(String.valueOf(u.id)).claim("ver", u.tokenVersion))
            .authorities(new SimpleGrantedAuthority("ROLE_ADMIN"));
    }

    @Test
    @DisplayName("SAFE consult across LIVING, INVESTMENT, RENTAL returns verified pins, real ST_Distance_Sphere POIs, and purpose-specific insights")
    void safeConsultAcrossPurposesReturnsVerifiedGisAndPurposeSpecificExplanations() throws Exception {
        for (String purpose : List.of("LIVING", "INVESTMENT", "RENTAL")) {
            String raw = mvc.perform(post("/api/v1/advisor/consult")
                    .contentType(MediaType.APPLICATION_JSON)
                    .content("""
                        {
                          "budgetVnd": 6000000000,
                          "budgetFlexibilityPct": 15,
                          "purpose": "%s",
                          "propertyType": "ALL",
                          "district": "Quận Hải Châu",
                          "limit": 5,
                          "includeComparables": true,
                          "includeValuation": false,
                          "includeResearch": false
                        }
                        """.formatted(purpose)))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);

            assertThat(raw).doesNotContain("contactPhone", "contactEmail", "address_raw", "sampleListingCount");
            JsonNode root = json.readTree(raw);
            assertThat(root.path("criteria").path("district").asText()).isEqualTo("Hải Châu");
            assertThat(root.path("areaLocationInsights").isArray()).isTrue();
            assertThat(root.path("areaLocationInsights").size()).isEqualTo(root.path("topAreas").size());

            for (JsonNode areaInsight : root.path("areaLocationInsights")) {
                assertThat(areaInsight.path("purpose").asText()).isEqualTo(purpose);
                assertThat(areaInsight.path("headlineVi").asText()).isNotBlank();
                assertThat(areaInsight.path("highlightsVi").isArray()).isTrue();
                assertThat(areaInsight.path("highlightsVi")).isNotEmpty();
            }

            JsonNode props = root.path("recommendedProperties");
            assertThat(props.size()).isGreaterThan(0);

            int locatedCount = 0;
            for (JsonNode p : props) {
                JsonNode loc = p.path("locationIntelligence");
                assertThat(loc.isObject()).isTrue();
                assertThat(loc.path("purposeLocationFit").path("purpose").asText()).isEqualTo(purpose);
                assertThat(loc.path("purposeLocationFit").path("highlightsVi")).isNotEmpty();

                if (loc.path("mapEligible").asBoolean()) {
                    locatedCount++;
                    assertThat(loc.path("locationPrecision").asText()).isEqualTo("VERIFIED_PROPERTY_PIN");
                    assertThat(loc.path("latitude").asDouble()).isBetween(15.90, 16.25);
                    assertThat(loc.path("longitude").asDouble()).isBetween(107.80, 108.40);
                    assertThat(loc.path("distanceMethod").asText()).isEqualTo("MYSQL_ST_DISTANCE_SPHERE_WGS84_METERS");
                    assertThat(loc.path("nearbyPois").size()).isGreaterThan(0);
                    for (JsonNode poi : loc.path("nearbyPois")) {
                        assertThat(poi.path("distanceMeters").asLong()).isBetween(0L, 1500L);
                        assertThat(poi.path("name").asText()).isNotBlank();
                    }
                } else {
                    assertThat(loc.path("latitude").isNull()).isTrue();
                    assertThat(loc.path("longitude").isNull()).isTrue();
                    assertThat(loc.path("nearbyPois")).isEmpty();
                }
            }
            assertThat(locatedCount).as("Hải Châu platform properties must have verified pins").isGreaterThan(0);
        }
    }

    @Test
    @DisplayName("Ambiguous cross-district NQ 1659 ward (Phường Hòa Khánh without district) refuses to guess and emits warning")
    void ambiguousCrossDistrictWardEmitsNormalizationWarningWithoutGuessing() throws Exception {
        String raw = mvc.perform(post("/api/v1/advisor/consult")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "budgetVnd": 5000000000,
                      "purpose": "LIVING",
                      "propertyType": "ALL",
                      "ward": "Phường Hòa Khánh",
                      "limit": 5,
                      "includeComparables": false,
                      "includeValuation": false
                    }
                    """))
            .andExpect(status().isOk())
            .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);

        JsonNode root = json.readTree(raw);
        assertThat(root.path("criteria").path("district").isNull()).isTrue();
        boolean hasAmbiguousWarning = false;
        for (JsonNode w : root.path("warnings")) {
            if (w.asText().startsWith("LOCATION_NORMALIZATION:") && w.asText().contains("1659")) {
                hasAmbiguousWarning = true;
                break;
            }
        }
        assertThat(hasAmbiguousWarning).isTrue();
    }

    @Test
    @DisplayName("INTERNAL_RESEARCH mode: TiniX historical records strictly receive administrative fallback with ZERO coordinates or POI distances")
    void internalResearchTinixRecordsNeverCarryCoordinatesOrNearbyPois() throws Exception {
        String raw = mvc.perform(post("/api/v1/advisor/consult")
                .with(adminActor())
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "budgetVnd": 3800000000,
                      "purpose": "INVESTMENT",
                      "propertyType": "HOUSE",
                      "district": "Thanh Khê",
                      "limit": 10,
                      "includeComparables": false,
                      "includeValuation": false,
                      "includeResearch": true
                    }
                    """))
            .andExpect(status().isOk())
            .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);

        JsonNode root = json.readTree(raw);
        assertThat(root.path("mode").asText()).isEqualTo("INTERNAL_RESEARCH");
        int tinixSeen = 0;
        for (JsonNode prop : root.path("recommendedProperties")) {
            if ("TINIX_AI".equals(prop.path("source").path("kind").asText())) {
                tinixSeen++;
                JsonNode loc = prop.path("locationIntelligence");
                assertThat(loc.path("mapEligible").asBoolean()).isFalse();
                assertThat(loc.path("coordinateStatus").asText()).isEqualTo("NONE_ADMIN_ONLY");
                assertThat(loc.path("locationPrecision").asText()).isIn("WARD_FALLBACK", "DISTRICT_FALLBACK");
                assertThat(loc.path("latitude").isNull()).isTrue();
                assertThat(loc.path("longitude").isNull()).isTrue();
                assertThat(loc.path("nearbyPois")).isEmpty();
                assertThat(loc.path("fallbackReason").asText()).contains("TiniX");
            }
        }
        assertThat(tinixSeen).as("Must observe real TiniX candidates in Thanh Khê HOUSE research query").isGreaterThan(0);
    }
}

