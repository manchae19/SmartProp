package vn.smartprop.market;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import vn.smartprop.common.ApiException;
import vn.smartprop.market.MarketAnalyticsRepository.CohortRow;
import vn.smartprop.market.MarketDtos.Response;
import vn.smartprop.market.MarketDtos.Stat;

/** Step 21.5B — unit tests for analytics business rules (no database). */
class MarketAnalyticsServiceTest {

    private final MarketAnalyticsRepository repo = mock(MarketAnalyticsRepository.class);
    private final MarketAnalyticsService service = new MarketAnalyticsService(repo);

    private static CohortRow row(String source, String district, String type, String month, double price) {
        return new CohortRow(source, district, "Phước Ninh", type, price, 80.0, month);
    }

    private static List<CohortRow> cohort() {
        List<CohortRow> rows = new ArrayList<>();
        for (int i = 0; i < 5; i++) rows.add(row("SMARTPROP", "Hải Châu", "HOUSE", null, 6_000_000_000d));
        for (int i = 0; i < 100; i++) rows.add(row("SMARTPROP", "Sơn Trà", "HOUSE", null, 5_000_000_000d));
        for (String m : List.of("2025-06", "2025-07", "2025-08")) {
            for (int i = 0; i < 35; i++) rows.add(row("TINIX_RESEARCH", "Cẩm Lệ", "HOUSE", m, 4_000_000_000d));
        }
        return rows;
    }

    @BeforeEach
    void setUp() {
        List<CohortRow> all = cohort();
        List<CohortRow> safe = all.stream().filter(r -> !"TINIX_RESEARCH".equals(r.source())).toList();
        when(repo.loadCohort(false)).thenReturn(safe);
        when(repo.loadCohort(true)).thenReturn(all);
    }

    @Test
    @DisplayName("validates property type and source enums")
    void validatesInputs() {
        assertThrows(ApiException.class, () -> service.analytics(null, null, "HOTEL", null, null));
        assertThrows(ApiException.class, () -> service.analytics(null, null, null, "FACEBOOK", null));
        assertThrows(ApiException.class, () -> service.analytics("x".repeat(101), null, null, null, null));
    }

    @Test
    @DisplayName("research defaults OFF (fast public path); explicit true or TINIX source turns it on")
    void researchDefaults() {
        assertFalse(service.analytics(null, null, null, null, null).meta().researchIncluded());
        assertFalse(service.analytics(null, null, null, null, false).meta().researchIncluded());
        assertTrue(service.analytics(null, null, null, null, true).meta().researchIncluded());
        assertTrue(service.analytics(null, null, null, "TINIX_RESEARCH", false).meta().researchIncluded());
    }

    @Test
    @DisplayName("median/quartiles present when sample >= MIN_SAMPLE; suppressed below")
    void sampleSuppression() {
        Response ok = service.analytics(null, null, null, "SMARTPROP", false);
        assertNotNull(ok.overall().medianAskingPriceVnd());
        assertEquals("OK", ok.overall().dataStatus());

        Response thin = service.analytics("Hải Châu", null, null, "SMARTPROP", false); // 5 rows
        assertEquals("INSUFFICIENT_DATA", thin.overall().dataStatus());
        assertNull(thin.overall().medianAskingPriceVnd());
        assertTrue(thin.overall().qualityFlags().contains("SMALL_SAMPLE"));
    }

    @Test
    @DisplayName("bySource labels research rows and never marks them as live listings")
    void sourceLabels() {
        Response r = service.analytics(null, null, null, null, true);
        var tinix = r.bySource().stream().filter(s -> "TINIX_RESEARCH".equals(s.source())).findFirst().orElseThrow();
        assertTrue(tinix.researchReference());
        assertEquals("CC BY-NC 4.0", tinix.license());
        assertTrue(tinix.label().contains("nghiên cứu"));
        var sp = r.bySource().stream().filter(s -> "SMARTPROP".equals(s.source())).findFirst().orElseThrow();
        assertFalse(sp.researchReference());
    }

    @Test
    @DisplayName("monthly series is insufficient below 30/point; adequate here; never a forecast")
    void temporalStatus() {
        Response r = service.analytics(null, null, null, null, true);
        assertEquals("AVAILABLE", r.meta().temporalStatus());
        assertTrue(r.monthly().stream().allMatch(p -> p.period().matches("\\d{4}-\\d{2}")));
        assertTrue(r.meta().dataQualityWarnings().stream().anyMatch(w -> w.startsWith("NO_FORECAST")));

        Response noResearch = service.analytics(null, null, null, null, false);
        assertEquals("NOT_REQUESTED", noResearch.meta().temporalStatus());
        assertTrue(noResearch.monthly().isEmpty());
    }

    @Test
    @DisplayName("asking-price and no-forecast warnings are always present")
    void warningsAlwaysPresent() {
        Response r = service.analytics(null, null, null, null, true);
        assertTrue(r.meta().dataQualityWarnings().stream().anyMatch(w -> w.startsWith("ASKING_PRICE_ONLY")));
        assertEquals("ASKING_SALE_VND_TOTAL", r.meta().priceBasis());
        assertNotNull(r.meta().disclaimer());
    }

    @Test
    @DisplayName("bands are always fully labelled even when empty")
    void bands() {
        Response r = service.analytics(null, null, null, null, true);
        assertEquals(8, r.priceBands().size());
        assertEquals(7, r.areaBands().size());
        assertEquals("< 1 tỷ", r.priceBands().get(0).label());
    }

    @Test
    @DisplayName("type labels are human readable and source filter narrows")
    void statShapeAndFilter() {
        Response r = service.analytics(null, null, null, null, true);
        Stat house = r.byPropertyType().stream().filter(s -> "HOUSE".equals(s.key())).findFirst().orElseThrow();
        assertEquals("Nhà ở / Nhà phố", house.label());

        Response onlyTinix = service.analytics(null, null, null, "TINIX_RESEARCH", true);
        assertEquals(105, onlyTinix.meta().totalSampleCount());
        assertEquals(0, onlyTinix.bySource().stream().filter(s -> "SMARTPROP".equals(s.source())).mapToLong(s -> s.count()).sum());
    }
}
