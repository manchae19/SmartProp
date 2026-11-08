package vn.smartprop.advisor;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

/**
 * Verifies against real MySQL that when the FastAPI valuation peer is unreachable,
 * the Advisor returns HTTP 200 with partialResult=true, full area/property/comparable
 * recommendations, and zero fabricated valuation numbers.
 */
@SpringBootTest(properties = {
    "app.recommendation.v11-enabled=true",
    "app.advisor.valuation-enabled=true",
    "app.advisor.valuation-base-url=http://127.0.0.1:18099"
})
@AutoConfigureMockMvc
@EnabledIfEnvironmentVariable(named = "DB_URL", matches = ".+")
class AdvisorPartialResultLiveIT {

    @Autowired MockMvc mvc;
    @Autowired ObjectMapper json;

    @Test
    void returnsRealMySqlRecommendationsAndComparablesWhenAiValuationIsOffline() throws Exception {
        String body = mvc.perform(post("/api/v1/advisor/consult")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "budgetVnd": 5000000000,
                      "budgetFlexibilityPct": 10,
                      "purpose": "LIVING",
                      "propertyType": "HOUSE",
                      "district": "Hải Châu",
                      "limit": 5,
                      "includeComparables": true,
                      "includeValuation": true
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.serviceStatus.recommendationService").value("AVAILABLE"))
            .andExpect(jsonPath("$.serviceStatus.areaService").value("AVAILABLE"))
            .andExpect(jsonPath("$.serviceStatus.comparableService").value("AVAILABLE"))
            .andExpect(jsonPath("$.serviceStatus.valuationService").value("UNAVAILABLE"))
            .andExpect(jsonPath("$.serviceStatus.partialResult").value(true))
            .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);

        JsonNode root = json.readTree(body);
        assertThat(root.path("recommendedProperties").size()).isGreaterThan(0);
        for (JsonNode prop : root.path("recommendedProperties")) {
            JsonNode val = prop.path("valuationEvidence");
            assertThat(val.path("available").asBoolean()).isFalse();
            assertThat(val.path("predictedAskingPriceVnd").isNull()).isTrue();
        }
    }
}

