package vn.smartprop.modules.prediction;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * WP-04 B3 — the explanation contract must survive the Java layer unchanged.
 *
 * These are Jackson-level tests: no Spring context, no database, no model. They prove that the
 * additive `explanation` node is passed through byte-for-byte, that legacy payloads still work,
 * and that a missing or malformed explanation never breaks a valuation.
 */
class ValuationExplanationContractTest {

    private final ObjectMapper json = new ObjectMapper();

    private static final String AVAILABLE_PAYLOAD = """
            {
              "explanation_version": "1.0",
              "status": "AVAILABLE",
              "method": "XGBOOST_NATIVE_TREESHAP",
              "target": "ASKING_PRICE_VND",
              "output_space": "LOG1P_PRICE_VND",
              "predicted_margin_log": 22.0842075347900390625,
              "base_value_log": 22.889129638671875,
              "base_price_vnd": 8722132856,
              "naive_price_vnd": 3958293121,
              "calibration": {"policy": "duan_by_band", "factor": 1.05621,
                              "adjusted_price_vnd": 4059447662},
              "factors": [
                {"feature_name": "area", "label_vi": "Diện tích", "input_state": "OBSERVED",
                 "contribution_log_raw": -0.804947854659985845321,
                 "contribution_log_display": -0.8049,
                 "multiplicative_factor": 0.447218, "direction": "DECREASE",
                 "group": "AREA", "context_note_vi": "Thông tin do người dùng cung cấp."}
              ],
              "other_contribution_log": 0.0,
              "grouped_contributions": {"AREA": -0.8049478546599858, "LOCATION": 0.0},
              "feature_provenance": {"area": "OBSERVED", "ward": "MISSING"},
              "limitations": ["Giải thích này mô tả hành vi của mô hình."]
            }
            """;

    private JsonNode node(String text) throws Exception {
        return json.readTree(text);
    }

    private ValuationService.Preview preview(JsonNode explanation) {
        return new ValuationService.Preview(true, null, "v1.3", "run", "4059447662", "VND",
                "basis", Map.of("area", 100.0), List.of(), List.of(), explanation);
    }

    // ---------------------------------------------------------------- round trip
    @Test
    void explanationSurvivesRoundTripWithFullPrecision() throws Exception {
        JsonNode original = node(AVAILABLE_PAYLOAD);
        ValuationService.Preview preview = preview(original);

        String serialized = json.writeValueAsString(preview);
        JsonNode returned = json.readTree(serialized).path("explanation");

        assertEquals("AVAILABLE", returned.path("status").asText());
        assertEquals("XGBOOST_NATIVE_TREESHAP", returned.path("method").asText());
        assertEquals("LOG1P_PRICE_VND", returned.path("output_space").asText());

        // raw contribution must keep every digit, not be re-rounded to the display value
        String raw = returned.path("factors").get(0).path("contribution_log_raw").asText();
        assertEquals(original.path("factors").get(0).path("contribution_log_raw").decimalValue(),
                new java.math.BigDecimal(raw));

        assertEquals(original.path("feature_provenance").toString(),
                returned.path("feature_provenance").toString());
        assertEquals(original.path("grouped_contributions").toString(),
                returned.path("grouped_contributions").toString());
        assertEquals(1.05621, returned.path("calibration").path("factor").asDouble(), 1e-12);
    }

    @Test
    void legacyFieldsAreUntouched() throws Exception {
        ValuationService.Preview preview = preview(node(AVAILABLE_PAYLOAD));
        JsonNode body = json.readTree(json.writeValueAsString(preview));

        assertEquals("4059447662", body.path("predictedAskingPriceVnd").asText());
        assertEquals("VND", body.path("currency").asText());
        assertEquals(true, body.path("available").asBoolean());
        assertNull(body.get("shapExplanation"), "this DTO never carried the SHAP block");
    }

    // ---------------------------------------------------------------- statuses
    @Test
    void everyDocumentedStatusIsPassedThrough() throws Exception {
        for (String status : new String[]{"AVAILABLE", "PARTIAL", "UNAVAILABLE", "NOT_SUPPORTED"}) {
            ObjectNode explanation = json.createObjectNode();
            explanation.put("explanation_version", "1.0");
            explanation.put("status", status);
            if (!"AVAILABLE".equals(status)) {
                explanation.putNull("factors");
            }
            ValuationService.Preview preview = preview(explanation);
            JsonNode returned = json.readTree(json.writeValueAsString(preview)).path("explanation");
            assertEquals(status, returned.path("status").asText());
        }
    }

    // ---------------------------------------------------------------- absence
    @Test
    void legacyPayloadWithoutExplanationSerializesAsNull() throws Exception {
        ValuationService.Preview preview = preview(null);
        JsonNode body = json.readTree(json.writeValueAsString(preview));
        assertTrue(body.has("explanation"));
        assertTrue(body.get("explanation").isNull(), "absent explanation must be JSON null");
    }

    @Test
    void legacyPayloadWithoutExplanationDeserializes() throws Exception {
        String legacy = """
                {"available": true, "modelVersion": "v1.3", "modelRun": "run",
                 "predictedAskingPriceVnd": "4059447662", "currency": "VND",
                 "featuresUsed": {}, "missingFeatures": [], "warnings": []}
                """;
        ValuationService.Preview parsed = json.readValue(legacy,
                ValuationService.Preview.class);
        assertNull(parsed.explanation());
        assertEquals("4059447662", parsed.predictedAskingPriceVnd());
    }

    // ---------------------------------------------------------------- isolation
    @Test
    void missingNullAndMalformedExplanationsBecomeNull() throws Exception {
        assertNull(ValuationService.explanationOf(null));

        ObjectNode body = json.createObjectNode();
        assertNull(ValuationService.explanationOf(body), "absent field");

        body.putNull("explanation");
        assertNull(ValuationService.explanationOf(body), "explicit null");

        body.putArray("explanation");
        assertNull(ValuationService.explanationOf(body), "array is not an object");

        body.put("explanation", "text");
        assertNull(ValuationService.explanationOf(body), "string is not an object");

        body.set("explanation", node(AVAILABLE_PAYLOAD));
        JsonNode kept = ValuationService.explanationOf(body);
        assertNotNull(kept);
        assertEquals("AVAILABLE", kept.path("status").asText());
    }

    @Test
    void malformedExplanationDoesNotBreakTheValuationPayload() throws Exception {
        ObjectNode body = json.createObjectNode();
        body.put("predicted_asking_price_vnd", 4059447662L);
        body.putArray("explanation");

        JsonNode explanation = ValuationService.explanationOf(body);
        ValuationService.Preview preview = new ValuationService.Preview(true, null, "v1.3",
                "run", String.valueOf(body.path("predicted_asking_price_vnd").asLong()), "VND",
                "basis", Map.of(), List.of(), List.of(), explanation);

        JsonNode serialized = json.readTree(json.writeValueAsString(preview));
        assertEquals("4059447662", serialized.path("predictedAskingPriceVnd").asText());
        assertTrue(serialized.get("explanation").isNull());
    }

    @Test
    void unreasonableExplanationNeverBecomesAttribution() throws Exception {
        JsonNode empty = json.createObjectNode().put("explanation_version", "1.0")
                .put("status", "UNAVAILABLE");
        ValuationService.Preview preview = preview(empty);
        JsonNode returned = json.readTree(json.writeValueAsString(preview)).path("explanation");

        assertEquals("UNAVAILABLE", returned.path("status").asText());
        assertFalse(returned.has("factors"), "the Java layer must not synthesise factors");
    }
}
