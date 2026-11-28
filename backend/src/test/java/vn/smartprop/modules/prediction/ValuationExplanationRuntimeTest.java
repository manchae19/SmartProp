package vn.smartprop.modules.prediction;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.*;

/**
 * WP-04 B3 — real HTTP over loopback between the Spring valuation client and a stub peer that
 * serves a payload with the same shape FastAPI produces (captured from the live V1.3 service).
 *
 * This exercises the production client, real sockets and real Jackson parsing. It deliberately
 * does not boot Tomcat, so it proves the client/transport boundary, not a full servlet stack.
 */
class ValuationExplanationRuntimeTest {

    private final ObjectMapper json = new ObjectMapper();
    private HttpServer server;
    private ValuationClient client;
    private volatile String body;
    private volatile int status;

    private static final String PREDICT_PAYLOAD = """
            {
              "model_version": "v1.3",
              "predicted_asking_price_vnd": 4059447662,
              "calibration_factor": 1.05621,
              "calibration_policy": "duan_by_band",
              "naive_price_vnd": 3958293121,
              "price_band": "3-5 tỷ",
              "features_used": {"area": 120.0},
              "missing_features": [],
              "warnings": [],
              "shap_explanation": {"base_value_log": 22.8891, "base_price_vnd": 8722132856,
                                   "scale": "log(1 + price_vnd)", "top_factors": [],
                                   "method": "TreeSHAP (Native Additive Contribution)",
                                   "status": "AVAILABLE", "summary_vi": "..."},
              "explanation": {
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
                "factors": [{"feature_name": "area", "input_state": "OBSERVED",
                             "contribution_log_raw": -0.8049478546599858,
                             "group": "AREA", "direction": "DECREASE"}],
                "other_contribution_log": 0.0,
                "grouped_contributions": {"AREA": -0.8049478546599858},
                "feature_provenance": {"area": "OBSERVED"},
                "limitations": ["..."]
              }
            }
            """;

    @BeforeEach
    void start() throws Exception {
        server = HttpServer.create(new InetSocketAddress(
                InetAddress.getByName("127.0.0.1"), 0), 0);
        server.createContext("/", exchange -> {
            byte[] bytes = body == null ? new byte[0] : body.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(status, bytes.length);
            try (var out = exchange.getResponseBody()) {
                out.write(bytes);
            }
        });
        server.start();
        int port = server.getAddress().getPort();
        client = new ValuationClient(json, true, "http://127.0.0.1:" + port);
        status = 200;
        body = PREDICT_PAYLOAD;
    }

    @AfterEach
    void stop() {
        if (server != null) {
            server.stop(0);
        }
    }

    @Test
    void explanationSurvivesTheRealHttpHop() {
        JsonNode response = client.exchange("/predict", java.util.Map.of("area_sqm", 120.0));
        JsonNode explanation = ValuationService.explanationOf(response);

        assertNotNull(explanation, "explanation must survive the HTTP hop");
        assertEquals("AVAILABLE", explanation.path("status").asText());
        assertEquals("XGBOOST_NATIVE_TREESHAP", explanation.path("method").asText());

        BigDecimal raw = explanation.path("factors").get(0)
                .path("contribution_log_raw").decimalValue();
        // FastAPI emits IEEE-754 doubles, so the exact double value must survive the hop.
        assertEquals(0, raw.compareTo(new BigDecimal("-0.8049478546599858")),
                "raw contribution must survive the HTTP hop unchanged");
        assertEquals(-0.8049478546599858, raw.doubleValue(), 0.0);
    }

    @Test
    void legacyPayloadWithoutExplanationStaysUsable() {
        body = PREDICT_PAYLOAD.replaceAll("(?s),\\s*\"explanation\".*\\}\\s*$", "}");
        JsonNode response = client.exchange("/predict", java.util.Map.of());

        assertEquals(4059447662L, response.path("predicted_asking_price_vnd").asLong());
        assertNotNull(response.path("shap_explanation").get("top_factors"));
        assertNull(ValuationService.explanationOf(response),
                "a legacy payload has no explanation and must not gain one");
    }

    @Test
    void malformedExplanationIsIgnoredNotFabricated() {
        body = PREDICT_PAYLOAD.replaceAll("(?s)\"explanation\":\\s*\\{.*",
                "\"explanation\": [1,2,3]}");
        JsonNode response = client.exchange("/predict", java.util.Map.of());

        assertEquals(4059447662L, response.path("predicted_asking_price_vnd").asLong());
        assertNull(ValuationService.explanationOf(response));
    }

    @Test
    void peerFailureIsIsolatedFromTheRestOfTheValuation() {
        status = 503;
        body = "{}";
        assertThrows(RuntimeException.class, () -> client.exchange("/predict", java.util.Map.of()),
                "a failing peer must surface as an unavailable valuation, not a wrong price");
    }

    @Test
    void previewRouteCarriesTheSameContract() {
        JsonNode response = client.exchange("/predict/v1_3_preview", java.util.Map.of());
        JsonNode explanation = ValuationService.explanationOf(response);
        assertNotNull(explanation);
        assertEquals("LOG1P_PRICE_VND", explanation.path("output_space").asText());
    }
}
