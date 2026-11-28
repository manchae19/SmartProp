package vn.smartprop.advisor;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import vn.smartprop.advisor.AdvisorDtos.ComparableEvidence;
import vn.smartprop.advisor.AdvisorDtos.Evidence;
import vn.smartprop.advisor.AdvisorDtos.EvidenceKind;
import vn.smartprop.advisor.AdvisorDtos.ValuationEvidence;
import vn.smartprop.comparable.ComparableDtos;
import vn.smartprop.modules.recommendation.RecommendationDtos.Source;

import static org.assertj.core.api.Assertions.assertThat;
import static vn.smartprop.advisor.AdvisorDtos.EvidenceKind.*;
import static vn.smartprop.advisor.AdvisorDtos.EvidenceStatus.*;

class AdvisorEvidenceProjectionTest {
    private final ObjectMapper mapper = new ObjectMapper();

    @Test
    void availableValuationHasNoInventedAgeOrCopiedPrice() throws Exception {
        var price = new BigDecimal("7432198765");
        var valuation = valuation(price, """
            {"explanation_version":"1.0","status":"UNAVAILABLE","limitations":["fixture"]}
            """);
        var projected = project(valuation, null, null);
        assertThat(entry(projected, VALUATION).status()).isEqualTo(AVAILABLE);
        assertThat(entry(projected, EXPLANATION).status()).isEqualTo(UNAVAILABLE);
        assertThat(valuation.predictedAskingPriceVnd()).isEqualTo(price);
        assertThat(projected).allSatisfy(evidence -> {
            assertThat(evidence.source()).isNotNull();
            assertThat(evidence.observedAt()).isNull();
            assertThat(evidence.generatedAt()).isNull();
            assertThat(evidence.freshness()).isEqualTo(AdvisorDtos.EvidenceFreshness.UNKNOWN);
            assertThat(evidence.reference()).isNotBlank();
            assertThat(evidence.limitations()).isNotEmpty();
        });
        assertThat(mapper.writeValueAsString(projected))
            .doesNotContain(price.toPlainString(), "fixture", "private-address", "private-record-key");
    }

    @Test
    void missingAndMalformedExplanationKeepTheValuationAvailable() throws Exception {
        var price = new BigDecimal("7400000000");
        for (String explanation : new String[] {null, "[]", """
            {"explanation_version":"1.0","status":"AVAILABLE","limitations":[],"method":"unexpected"}
            """}) {
            var projected = project(valuation(price, explanation), null, null);
            assertThat(entry(projected, VALUATION).status()).isEqualTo(AVAILABLE);
            assertThat(entry(projected, EXPLANATION).status()).isEqualTo(explanation == null ? MISSING : INVALID);
        }
    }

    @Test
    void comparablePurposesAndSampleThresholdsAreIndependent() {
        for (int count : List.of(0, 2, 3, 4, 5)) {
            var similar = comparable(ComparableDtos.Purpose.SIMILAR_LISTING, count);
            var support = comparable(ComparableDtos.Purpose.VALUATION_SUPPORT, 5);
            var projected = project(null, similar, support);
            assertThat(entry(projected, SIMILAR_LISTING).status()).isEqualTo(
                count < 3 ? INSUFFICIENT_EVIDENCE : count < 5 ? PARTIAL : AVAILABLE);
            assertThat(entry(projected, VALUATION_SUPPORT).status()).isEqualTo(AVAILABLE);
            assertThat(entry(projected, SIMILAR_LISTING).reference()).isEqualTo("comparableEvidence");
            assertThat(entry(projected, VALUATION_SUPPORT).reference()).isEqualTo("valuationComparableEvidence");
        }
        var wrongPurpose = comparable(ComparableDtos.Purpose.SIMILAR_LISTING, 5);
        assertThat(entry(project(null, null, wrongPurpose), VALUATION_SUPPORT).status()).isEqualTo(INVALID);
    }

    @Test
    void missingSourceAndUnavailableValuationDoNotSuppressOtherEvidence() {
        var valuation = AdvisorValuationAdapter.skipped("SERVICE_UNAVAILABLE", "fixture");
        var similar = comparable(ComparableDtos.Purpose.SIMILAR_LISTING, 5);
        var projected = AdvisorEvidenceProjection.project(null, valuation, similar, null, null, true);

        assertThat(entry(projected, RECOMMENDATION).source()).isNull();
        assertThat(entry(projected, RECOMMENDATION).status()).isEqualTo(MISSING);
        assertThat(entry(projected, VALUATION).status()).isEqualTo(UNAVAILABLE);
        assertThat(entry(projected, SIMILAR_LISTING).status()).isEqualTo(AVAILABLE);
        assertThat(entry(projected, VALUATION_SUPPORT).status()).isEqualTo(MISSING);
    }

    private ValuationEvidence valuation(BigDecimal price, String explanation) throws Exception {
        return new ValuationEvidence("AVAILABLE", true, null, "v1.3", null, price, null, null,
            Map.of(), List.of(), null, List.of(), explanation == null ? null : mapper.readTree(explanation));
    }

    private static List<Evidence> project(ValuationEvidence valuation, ComparableEvidence similar,
                                         ComparableEvidence support) {
        return AdvisorEvidenceProjection.project(new Source("PROPERTY", "private-address", "private-record-key", null),
            valuation, similar, support, null, true);
    }

    private static Evidence entry(List<Evidence> entries, EvidenceKind kind) {
        return entries.stream().filter(item -> item.kind() == kind).findFirst().orElseThrow();
    }

    private static ComparableEvidence comparable(ComparableDtos.Purpose purpose, int count) {
        var stats = new ComparableDtos.AskingPriceStats(count,
            count >= 5 ? new BigDecimal("4500000000") : null,
            count >= 5 ? new BigDecimal("52000000") : null);
        var cohort = new ComparableDtos.Evidence(purpose,
            count >= 5 ? ComparableDtos.EvidenceStatus.AVAILABLE : ComparableDtos.EvidenceStatus.INSUFFICIENT_EVIDENCE,
            count, count, 0, null, true, Map.of(), Map.of(), stats, List.of());
        return new ComparableEvidence(count == 0 ? "EMPTY_NO_MATCHES" : "AVAILABLE", 0, "DISTRICT",
            List.of(), List.of(), cohort);
    }
}
