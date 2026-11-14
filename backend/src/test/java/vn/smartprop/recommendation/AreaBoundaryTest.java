package vn.smartprop.modules.recommendation;

import org.junit.jupiter.api.Test;
import java.math.BigDecimal;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static vn.smartprop.modules.recommendation.RecommendationDtos.*;

class AreaBoundaryTest {
    @Test void strictMinimumExcludesEqualAreaAndInclusiveIncludesIt() {
        var service = service(area("80"));
        assertTrue(service.recommend(request(new BigDecimal("80"), true, null, false)).topProperties().isEmpty());
        assertEquals(1, service.recommend(request(new BigDecimal("80"), false, null, false)).topProperties().size());
        assertTrue(service.recommend(request(new BigDecimal("80.01"), true, null, false)).topProperties().isEmpty());
    }

    @Test void maximumBoundaryIsRespected() {
        var service = service(area("80"));
        assertTrue(service.recommend(request(null, false, new BigDecimal("80"), true)).topProperties().isEmpty());
        assertEquals(1, service.recommend(request(null, false, new BigDecimal("80"), false)).topProperties().size());
        assertEquals(1, service.recommend(request(null, false, new BigDecimal("80.01"), true)).topProperties().size());
    }

    private static HybridRecommendationService service(Candidate candidate) {
        var repository = mock(RecommendationCandidateRepository.class);
        when(repository.find(any(), eq(false))).thenReturn(List.of(candidate));
        return new HybridRecommendationService(repository, new PropertyScoringService(), new AreaScoringService(), false);
    }

    private static Request request(BigDecimal min, boolean minExclusive, BigDecimal max, boolean maxExclusive) {
        return new Request(new BigDecimal("2000000000"), Purpose.LIVING, PropertyType.HOUSE,
            min, max, minExclusive, maxExclusive, null, null, 10, List.of());
    }

    private static Candidate area(String area) {
        return new Candidate("property-80", "Boundary", PropertyType.HOUSE,
            new BigDecimal("1500000000"), new BigDecimal(area), "Hải Châu", null,
            new Source("EXTERNAL", "fixture", "property-80", "https://example.invalid/property-80"),
            "VALID", "VERIFIED", null, false, false, List.of(), false);
    }
}
