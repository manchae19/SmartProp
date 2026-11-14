package vn.smartprop.advisor;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import vn.smartprop.advisor.AdvisorDtos.AdvisedProperty;
import vn.smartprop.advisor.AdvisorDtos.AdvisorRequest;
import vn.smartprop.advisor.AdvisorDtos.AdvisorResponse;
import vn.smartprop.advisor.AdvisorDtos.ValuationEvidence;
import vn.smartprop.common.ApiException;
import vn.smartprop.comparable.ComparableDtos;
import vn.smartprop.comparable.ComparableEligibilityService;
import vn.smartprop.comparable.ComparableRankingService;
import vn.smartprop.modules.recommendation.HybridRecommendationService;
import vn.smartprop.modules.recommendation.RecommendationDtos;
import vn.smartprop.modules.recommendation.RecommendationDtos.AreaResult;
import vn.smartprop.modules.recommendation.RecommendationDtos.PropertyResult;
import vn.smartprop.modules.recommendation.RecommendationDtos.PropertyType;
import vn.smartprop.modules.recommendation.RecommendationDtos.Purpose;
import vn.smartprop.modules.recommendation.RecommendationDtos.Source;

class AdvisorOrchestrationServiceTest {

    private final HybridRecommendationService recService = mock(HybridRecommendationService.class);
    private final ComparableRankingService compService = mock(ComparableRankingService.class);
    private final ComparableEligibilityService compEligibility = new ComparableEligibilityService();
    private final AdvisorValuationAdapter valAdapter = mock(AdvisorValuationAdapter.class);

    private AdvisorOrchestrationService newOrchestrator(boolean allowResearchComparables) {
        return new AdvisorOrchestrationService(recService, compService, compEligibility, valAdapter, allowResearchComparables);
    }

    @Test
    void flexibleBudgetExpandsCeilingAndAnchorsComparablesToSourcePriceNeverV6() {
        AdvisorOrchestrationService orchestrator = newOrchestrator(true);

        PropertyResult prop = new PropertyResult(
            "prop:hc-01",
            "Nhà phố Hải Châu 3 tầng",
            PropertyType.HOUSE,
            new BigDecimal("4400000000"), // +10% above 4.0B stated budget
            new BigDecimal("85"),
            "Hải Châu",
            "Hòa Cường Bắc",
            84.5,
            Map.of("budgetFit", 82.0, "areaFit", 90.0),
            List.of("Diện tích 85 m² phù hợp nhu cầu ở gia đình"),
            new Source("PROPERTY", "SmartProp", "hc-01", "https://ignored/raw"),
            "PLATFORM_PUBLISHED",
            "VERIFIED",
            null,
            List.of(),
            null
        );

        ArgumentCaptor<RecommendationDtos.Request> recCaptor = ArgumentCaptor.forClass(RecommendationDtos.Request.class);
        when(recService.recommend(recCaptor.capture())).thenReturn(new RecommendationDtos.Response(
            "HEURISTIC_V1_1",
            "SAFE",
            "ASKING_SALE_VND_TOTAL",
            new RecommendationDtos.Request(new BigDecimal("4600000000"), Purpose.LIVING, PropertyType.ALL, null, null, null, 5),
            1,
            List.of(new AreaResult("Hải Châu", "Hòa Cường Bắc", 1, 85.0, new BigDecimal("4400000000"),
                List.of("SmartProp"), 1, 0, List.of("Khu trung tâm"), List.of())),
            List.of(prop),
            List.of("HEURISTIC_V1_1: weighted"),
            Map.of("budgetFit", 0.35)
        ));

        when(valAdapter.probeSupportedLocations()).thenReturn(Map.of("Nhà ở", Set.of("Hải Châu")));
        // V6 returns 5.2B — ComparableRankingService MUST still receive 4.4B (source asking price), never 5.2B!
        when(valAdapter.evaluate(any(), any(), any(), any(), any(), any(), any(), any())).thenReturn(
            new ValuationEvidence("AVAILABLE", true, null, "v6", "b4b1339d3f35857e",
                new BigDecimal("5200000000"), new BigDecimal("-15.4"), "V6 basis",
                Map.of("areaSqm", 85.0), List.of(), null, List.of())
        );

        ArgumentCaptor<ComparableDtos.Request> compCaptor = ArgumentCaptor.forClass(ComparableDtos.Request.class);
        when(compService.rank(compCaptor.capture())).thenReturn(new ComparableDtos.Response(
            new ComparableDtos.Reference("hc-01", "HOUSE", "Hải Châu", "Hòa Cường Bắc", new BigDecimal("85"), new BigDecimal("4400000000"), null, null),
            2,
            "WARD",
            List.of(
                new ComparableDtos.Candidate(
                    "hc-02", ComparableDtos.SourceKind.SMARTPROP, "SmartProp", "HOUSE", "Hải Châu", "Hòa Cường Bắc",
                    new BigDecimal("82"), new BigDecimal("4350000000"), new BigDecimal("-1.1"), 3, 3, null, null,
                    0.92, Map.of("location", "Cùng phường/xã"), "PLATFORM_PUBLISHED", "/properties/hc-02", null, null
                ),
                new ComparableDtos.Candidate(
                    "tnx-99", ComparableDtos.SourceKind.TINIX_RESEARCH, "TiniX", "HOUSE", "Hải Châu", "Hòa Cường Bắc",
                    new BigDecimal("88"), new BigDecimal("4500000000"), new BigDecimal("2.3"), 3, 3, null, null,
                    0.86, Map.of("location", "Cùng phường/xã"), "HYBRID_ELIGIBLE_RESEARCH", "https://must-be-stripped",
                    "CC BY-NC 4.0", "TiniX — CC BY-NC 4.0"
                )
            ),
            List.of(),
            Map.of("SMARTPROP", 10, "TINIX_RESEARCH", 100)
        ));

        AdvisorResponse response = orchestrator.consult(new AdvisorRequest(
            new BigDecimal("4000000000"),
            15, // +15% -> 4.6B effective ceiling
            Purpose.LIVING,
            PropertyType.ALL,
            null,
            "Tất cả",
            " ",
            5,
            true,
            true,
            false
        ));

        // 1. Effective ceiling & ALL normalization
        assertThat(recCaptor.getValue().budgetVnd()).isEqualByComparingTo("4600000000");
        assertThat(recCaptor.getValue().district()).isNull();
        assertThat(recCaptor.getValue().propertyType()).isEqualTo(PropertyType.ALL);

        // 2. Anti-circularity check: ComparableRankingService anchored to 4.4B source asking price & self-exclusion ID
        assertThat(compCaptor.getValue().priceVnd()).isEqualByComparingTo("4400000000");
        assertThat(compCaptor.getValue().propertyId()).isEqualTo("hc-01");

        // 3. Property response flags & URL sanitization
        assertThat(response.recommendedProperties()).hasSize(1);
        AdvisedProperty item = response.recommendedProperties().get(0);
        assertThat(item.withinStatedBudget()).isFalse();
        assertThat(item.withinFlexibleBudget()).isTrue();
        assertThat(item.budgetDeltaPct()).isEqualByComparingTo("10.0");
        assertThat(item.liveListing()).isTrue();
        assertThat(item.researchReference()).isFalse();
        assertThat(item.source().detailUrl()).isEqualTo("/listing/hc-01");

        // 4. Comparable SMARTPROP route rewritten to /listing/{id}; TINIX_RESEARCH stripped of any URL
        assertThat(item.comparableEvidence().comparables()).hasSize(2);
        assertThat(item.comparableEvidence().comparables().get(0).listingUrl()).isEqualTo("/listing/hc-02");
        assertThat(item.comparableEvidence().comparables().get(1).researchReference()).isTrue();
        assertThat(item.comparableEvidence().comparables().get(1).liveListing()).isFalse();
        assertThat(item.comparableEvidence().comparables().get(1).listingUrl()).isNull();
        assertThat(item.comparableEvidence().comparables().get(1).datasetLicense()).isEqualTo("CC BY-NC 4.0");
    }

    @Test
    void offlineValuationServiceDegradesToPartialResultWithoutFakePrices() {
        AdvisorOrchestrationService orchestrator = newOrchestrator(true);

        PropertyResult prop = new PropertyResult(
            "prop:st-01", "Căn hộ Sơn Trà", PropertyType.APARTMENT,
            new BigDecimal("2800000000"), new BigDecimal("68"), "Sơn Trà", "An Hải Bắc",
            88.0, Map.of("budgetFit", 90.0), List.of("Phù hợp đầu tư cho thuê"),
            new Source("PROPERTY", "SmartProp", "st-01", null), "PLATFORM_PUBLISHED", "VERIFIED", null, List.of(), null
        );
        when(recService.recommend(any())).thenReturn(new RecommendationDtos.Response(
            "HEURISTIC_V1_1", "SAFE", "ASKING_SALE_VND_TOTAL",
            new RecommendationDtos.Request(new BigDecimal("3000000000"), Purpose.RENTAL, PropertyType.APARTMENT, null, "Sơn Trà", null, 5),
            1, List.of(), List.of(prop), List.of(), Map.of()
        ));
        when(valAdapter.probeSupportedLocations()).thenReturn(null); // FastAPI offline!
        when(valAdapter.evaluate(any(), any(), any(), any(), any(), any(), any(), any()))
            .thenReturn(AdvisorValuationAdapter.skipped("SERVICE_UNAVAILABLE", "AI offline"));
        when(compService.rank(any())).thenReturn(new ComparableDtos.Response(
            null, 0, "NONE", List.of(), List.of(), Map.of()
        ));

        AdvisorResponse res = orchestrator.consult(new AdvisorRequest(
            new BigDecimal("3000000000"), 0, Purpose.RENTAL, PropertyType.APARTMENT, null, "Sơn Trà", null, 5, true, true, false
        ));

        assertThat(res.serviceStatus().valuationService()).isEqualTo("UNAVAILABLE");
        assertThat(res.serviceStatus().partialResult()).isTrue();
        assertThat(res.recommendedProperties()).hasSize(1);
        assertThat(res.recommendedProperties().get(0).valuationEvidence().available()).isFalse();
        assertThat(res.recommendedProperties().get(0).valuationEvidence().predictedAskingPriceVnd()).isNull();
        assertThat(res.warnings()).anyMatch(w -> w.startsWith("VALUATION_SERVICE_UNAVAILABLE:"));
    }

    @Test
    void researchRecordsSkipXGBoostValuationAndCarryStrictResearchLabels() {
        AdvisorOrchestrationService orchestrator = newOrchestrator(true);

        PropertyResult tinixProp = new PropertyResult(
            "tinix:tnx-500", "Quan sát lịch sử Thanh Khê", PropertyType.HOUSE,
            new BigDecimal("3200000000"), new BigDecimal("70"), "Thanh Khê", "Chính Gián",
            79.0, Map.of("budgetFit", 85.0), List.of("Khớp tiêu chí nghiên cứu"),
            new Source("TINIX_AI", "TiniX AI Research", "tnx-500", "https://should-be-removed"),
            "HYBRID_ELIGIBLE_RESEARCH", "UNVERIFIED", null, List.of(), null
        );
        when(recService.recommendResearch(any())).thenReturn(new RecommendationDtos.Response(
            "HEURISTIC_V1_1", "INTERNAL_DEMO", "ASKING_SALE_VND_TOTAL",
            new RecommendationDtos.Request(new BigDecimal("3500000000"), Purpose.INVESTMENT, PropertyType.HOUSE, null, null, null, 5),
            1, List.of(), List.of(tinixProp), List.of(), Map.of()
        ));
        when(valAdapter.probeSupportedLocations()).thenReturn(Map.of("Nhà ở", Set.of("Thanh Khê")));
        when(compService.rank(any())).thenReturn(new ComparableDtos.Response(
            null, 0, "NONE", List.of(), List.of(), Map.of()
        ));

        AdvisorResponse res = orchestrator.consult(new AdvisorRequest(
            new BigDecimal("3500000000"), 0, Purpose.INVESTMENT, PropertyType.HOUSE, null, null, null, 5, true, true, true
        ));

        verify(valAdapter, never()).evaluate(any(), any(), any(), any(), any(), any(), any(), any());
        AdvisedProperty item = res.recommendedProperties().get(0);
        assertThat(item.researchReference()).isTrue();
        assertThat(item.liveListing()).isFalse();
        assertThat(item.availabilityStatus()).isEqualTo("UNKNOWN_HISTORICAL_RESEARCH");
        assertThat(item.source().detailUrl()).isNull();
        assertThat(item.valuationEvidence().status()).isEqualTo("SKIPPED_RESEARCH_RECORD");
        assertThat(item.warnings()).anyMatch(w -> w.contains("CC BY-NC 4.0"));
    }

    @Test
    void emptyCandidatesAndInvalidFlexibilityHandledCleanly() {
        AdvisorOrchestrationService orchestrator = newOrchestrator(true);
        when(recService.recommend(any())).thenReturn(new RecommendationDtos.Response(
            "HEURISTIC_V1_1", "SAFE", "ASKING_SALE_VND_TOTAL",
            new RecommendationDtos.Request(new BigDecimal("50000000"), Purpose.LIVING, PropertyType.HOUSE, null, null, null, 5),
            0, List.of(), List.of(), List.of(), Map.of()
        ));
        when(valAdapter.probeSupportedLocations()).thenReturn(Map.of("Nhà ở", Set.of("Hải Châu")));

        AdvisorResponse empty = orchestrator.consult(new AdvisorRequest(
            new BigDecimal("50000000"), 0, Purpose.LIVING, PropertyType.HOUSE, null, null, null, 5, true, true, false
        ));
        assertThat(empty.recommendedProperties()).isEmpty();
        assertThat(empty.warnings()).anyMatch(w -> w.startsWith("NO_ELIGIBLE_CANDIDATES:"));

        assertThatThrownBy(() -> orchestrator.consult(new AdvisorRequest(
            new BigDecimal("3000000000"), 45, Purpose.LIVING, PropertyType.HOUSE, null, null, null, 5, true, true, false
        ))).isInstanceOf(ApiException.class);
    }
}
