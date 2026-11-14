package vn.smartprop.comparable;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.math.BigDecimal;

import org.junit.jupiter.api.Test;

class ComparableEligibilityServiceTest {

    private final ComparableEligibilityService service = new ComparableEligibilityService();

    @Test
    void onlyKnownPropertyTypesPass() {
        assertTrue(service.supportedType("HOUSE"));
        assertTrue(service.supportedType("land"));
        assertFalse(service.supportedType("ROOM"));
        assertFalse(service.supportedType("COMMERCIAL"));
        assertFalse(service.supportedType(null));
    }

    @Test
    void priceBoundsAreInclusiveAndRejectNull() {
        assertTrue(service.plausiblePrice(new BigDecimal("200000000")));
        assertTrue(service.plausiblePrice(new BigDecimal("1000000000000")));
        assertFalse(service.plausiblePrice(new BigDecimal("199999999")));
        assertFalse(service.plausiblePrice(new BigDecimal("1000000000001")));
        assertFalse(service.plausiblePrice(null));
    }

    @Test
    void areaBoundsRejectZeroAndAbsurd() {
        assertTrue(service.plausibleArea(new BigDecimal("5")));
        assertFalse(service.plausibleArea(new BigDecimal("4.9")));
        assertFalse(service.plausibleArea(new BigDecimal("50000.01")));
        assertFalse(service.plausibleArea(null));
    }

    @Test
    void rentalsAndUnknownsAreNotSales() {
        assertTrue(service.saleTransaction("SALE"));
        assertTrue(service.saleTransaction(" sale "));
        assertFalse(service.saleTransaction("RENT"));
        assertFalse(service.saleTransaction("UNKNOWN"));
        assertFalse(service.saleTransaction(null));
    }

    @Test
    void holdoutAndNonRepresentativeRowsAreExcluded() {
        assertTrue(service.researchEligible("HYBRID_ELIGIBLE_RESEARCH", true, false));
        assertFalse(service.researchEligible("HYBRID_ELIGIBLE_RESEARCH", true, true), "protected holdout must never train or rank");
        assertFalse(service.researchEligible("HYBRID_ELIGIBLE_RESEARCH", false, false), "duplicates are not representatives");
        assertFalse(service.researchEligible("NEEDS_REVIEW", true, false));
        assertFalse(service.researchEligible("EXCLUDED", true, false));
    }

    @Test
    void referenceIsNeverItsOwnComparable() {
        assertFalse(service.notSelf("a", "a"));
        assertTrue(service.notSelf("a", "b"));
        assertTrue(service.notSelf(null, "b"));
    }

    @Test
    void envelopeIsTwoSided() {
        BigDecimal ref = new BigDecimal("80");
        assertTrue(service.withinEnvelope(ref, new BigDecimal("120"), new BigDecimal("2.5")));
        assertTrue(service.withinEnvelope(ref, new BigDecimal("40"), new BigDecimal("2.5")));
        assertFalse(service.withinEnvelope(ref, new BigDecimal("201"), new BigDecimal("2.5")));
        assertFalse(service.withinEnvelope(ref, new BigDecimal("31"), new BigDecimal("2.5")));
        assertFalse(service.withinEnvelope(BigDecimal.ZERO, new BigDecimal("40"), new BigDecimal("2.5")));
    }
}
