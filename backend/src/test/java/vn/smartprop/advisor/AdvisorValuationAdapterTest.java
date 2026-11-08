package vn.smartprop.advisor;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.math.BigDecimal;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import vn.smartprop.advisor.AdvisorDtos.ValuationEvidence;
import vn.smartprop.modules.property.Property;
import vn.smartprop.modules.property.PropertyRepository;
import vn.smartprop.modules.recommendation.RecommendationDtos.PropertyType;

class AdvisorValuationAdapterTest {

    private final ObjectMapper json = new ObjectMapper();
    private final PropertyRepository properties = mock(PropertyRepository.class);

    @Test
    void rejectsNonLoopbackOriginToPreventSsrf() {
        assertThatThrownBy(() -> new AdvisorValuationAdapter(json, properties, true, "http://192.168.1.50:8000"))
            .isInstanceOf(IllegalArgumentException.class)
            .hasMessageContaining("IPv4 loopback");
        assertThatThrownBy(() -> new AdvisorValuationAdapter(json, properties, true, "https://127.0.0.1:8000"))
            .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void neverCallsPredictWhenMandatoryFeaturesAreMissingOrOutOfRange() {
        AtomicInteger predictCalls = new AtomicInteger();
        AdvisorValuationAdapter adapter = new AdvisorValuationAdapter(json, properties, true, "http://127.0.0.1:8000") {
            @Override
            protected JsonNode exchange(String path, Object payload, long timeoutMs) {
                if ("/predict".equals(path)) predictCalls.incrementAndGet();
                return null;
            }
        };
        Map<String, Set<String>> supported = Map.of("Nhà ở", Set.of("Hải Châu", "Sơn Trà"));

        // 1. Unsupported propertyType (ROOM / COMMERCIAL)
        ValuationEvidence room = adapter.evaluate(
            "PROPERTY", "p1", PropertyType.ROOM, new BigDecimal("50"), "Hải Châu", null, new BigDecimal("2000000000"), supported);
        assertThat(room.available()).isFalse();
        assertThat(room.status()).isEqualTo("SKIPPED_UNSUPPORTED_TYPE");
        assertThat(room.predictedAskingPriceVnd()).isNull();

        // 2. Missing area
        ValuationEvidence noArea = adapter.evaluate(
            "PROPERTY", "p2", PropertyType.HOUSE, null, "Hải Châu", null, new BigDecimal("4000000000"), supported);
        assertThat(noArea.available()).isFalse();
        assertThat(noArea.status()).isEqualTo("SKIPPED_MISSING_FEATURES");

        // 3. Area < 20 sqm
        ValuationEvidence tinyArea = adapter.evaluate(
            "PROPERTY", "p3", PropertyType.HOUSE, new BigDecimal("18.5"), "Hải Châu", null, new BigDecimal("2000000000"), supported);
        assertThat(tinyArea.available()).isFalse();
        assertThat(tinyArea.status()).isEqualTo("SKIPPED_OUT_OF_RANGE_AREA");

        // 4. Area > 1000 sqm
        ValuationEvidence hugeArea = adapter.evaluate(
            "PROPERTY", "p4", PropertyType.HOUSE, new BigDecimal("1250"), "Hải Châu", null, new BigDecimal("25000000000"), supported);
        assertThat(hugeArea.available()).isFalse();
        assertThat(hugeArea.status()).isEqualTo("SKIPPED_OUT_OF_RANGE_AREA");

        // 5. Missing district
        ValuationEvidence noDistrict = adapter.evaluate(
            "PROPERTY", "p5", PropertyType.HOUSE, new BigDecimal("80"), "  ", null, new BigDecimal("4000000000"), supported);
        assertThat(noDistrict.available()).isFalse();
        assertThat(noDistrict.status()).isEqualTo("SKIPPED_MISSING_FEATURES");

        // 6. Unsupported location for category
        ValuationEvidence unsupportedLoc = adapter.evaluate(
            "PROPERTY", "p6", PropertyType.HOUSE, new BigDecimal("80"), "Quận Lạ", null, new BigDecimal("4000000000"), supported);
        assertThat(unsupportedLoc.available()).isFalse();
        assertThat(unsupportedLoc.status()).isEqualTo("SKIPPED_UNSUPPORTED_LOCATION");

        // 7. Offline service (supportedLocations == null) -> zero network predict calls, zero fake price
        ValuationEvidence offline = adapter.evaluate(
            "PROPERTY", "p7", PropertyType.HOUSE, new BigDecimal("80"), "Hải Châu", null, new BigDecimal("4000000000"), null);
        assertThat(offline.available()).isFalse();
        assertThat(offline.status()).isEqualTo("SERVICE_UNAVAILABLE");
        assertThat(offline.predictedAskingPriceVnd()).isNull();

        assertThat(predictCalls.get()).as("XGBoost /predict must never be invoked on invalid/offline cases").isZero();
    }

    @Test
    void parsesValidV6PredictionAndTreeShapAndRejectsPinMismatch() throws Exception {
        Property published = new Property();
        published.id = "prop-hc-1";
        published.status = Property.Status.PUBLISHED;
        published.bedrooms = 3;
        published.title = "Nhà 3 tầng Hòa Cường Bắc";
        when(properties.findByIdAndDeletedAtIsNull("prop-hc-1")).thenReturn(Optional.of(published));

        String validJson = """
            {
              "model_version": "v6",
              "model_run": "b4b1339d3f35857e",
              "predicted_asking_price_vnd": 5000000000,
              "features_used": {
                "area_sqm": 80.0,
                "location_feature": "Hải Châu",
                "ward_source": "explicit",
                "rooms": 3
              },
              "missing_features": ["floors"],
              "warnings": [],
              "shap_explanation": {
                "method": "TreeSHAP (Native Additive Contribution)",
                "scale": "log_asking_price",
                "base_value_log": 22.25,
                "base_price_vnd": 4600000000,
                "summary_vi": "Vị trí Hải Châu và diện tích 80 m² làm tăng mức ước tính.",
                "top_factors": [
                  {
                    "feature_name": "location_feature",
                    "label": "Khu vực Hải Châu",
                    "shap_value": 0.12,
                    "impact_pct": 12.7,
                    "direction": "increase",
                    "context_note": "Trung tâm thành phố"
                  }
                ]
              }
            }
            """;

        AdvisorValuationAdapter adapter = new AdvisorValuationAdapter(json, properties, true, "http://127.0.0.1:8000") {
            @Override
            protected JsonNode exchange(String path, Object payload, long timeoutMs) {
                try {
                    return json.readTree(validJson);
                } catch (Exception e) {
                    throw new RuntimeException(e);
                }
            }
        };

        ValuationEvidence ev = adapter.evaluate(
            "PROPERTY",
            "prop-hc-1",
            PropertyType.HOUSE,
            new BigDecimal("80"),
            "Hải Châu",
            "Hòa Cường Bắc",
            new BigDecimal("4750000000"),
            Map.of("Nhà ở", Set.of("Hải Châu"))
        );

        assertThat(ev.available()).isTrue();
        assertThat(ev.status()).isEqualTo("AVAILABLE");
        assertThat(ev.modelVersion()).isEqualTo("v6");
        assertThat(ev.modelRun()).isEqualTo("b4b1339d3f35857e");
        assertThat(ev.predictedAskingPriceVnd()).isEqualByComparingTo("5000000000");
        // (4.75B - 5.00B) / 5.00B = -5.0%
        assertThat(ev.askingVsEstimatePct()).isEqualByComparingTo("-5.0");
        assertThat(ev.shapExplanation()).isNotNull();
        assertThat(ev.shapExplanation().topFactors()).hasSize(1);
        assertThat(ev.shapExplanation().topFactors().get(0).label()).isEqualTo("Khu vực Hải Châu");

        // Pin mismatch must fail closed without fabricating a price
        AdvisorValuationAdapter mismatched = new AdvisorValuationAdapter(json, properties, true, "http://127.0.0.1:8000") {
            @Override
            protected JsonNode exchange(String path, Object payload, long timeoutMs) {
                try {
                    return json.readTree(validJson.replace("b4b1339d3f35857e", "wrong-run-id"));
                } catch (Exception e) {
                    throw new RuntimeException(e);
                }
            }
        };
        ValuationEvidence rejected = mismatched.evaluate(
            "PROPERTY",
            "prop-hc-1",
            PropertyType.HOUSE,
            new BigDecimal("80"),
            "Hải Châu",
            null,
            new BigDecimal("4750000000"),
            Map.of("Nhà ở", Set.of("Hải Châu"))
        );
        assertThat(rejected.available()).isFalse();
        assertThat(rejected.predictedAskingPriceVnd()).isNull();
    }
}

