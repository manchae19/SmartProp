package vn.smartprop.comparable;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertFalse;

import java.math.BigDecimal;

import org.junit.jupiter.api.Test;

class ComparableSimilarityScorerTest {

    private static ComparableSimilarityScorer.Input house(String district, String ward, String area, String price, Integer rooms) {
        return new ComparableSimilarityScorer.Input(district, ward, "HOUSE",
            new BigDecimal(area), new BigDecimal(price), rooms, 3, new BigDecimal("5"));
    }

    @Test
    void identicalPropertiesScoreOne() {
        var a = house("Hải Châu", "Hải Châu 1", "80", "5000000000", 3);
        assertEquals(1.0, ComparableSimilarityScorer.score(a, a).score(), 1e-9);
    }

    @Test
    void sameWardBeatsSameDistrictBeatsNeighbour() {
        var ref = house("Hải Châu", "Hải Châu 1", "80", "5000000000", 3);
        double ward = ComparableSimilarityScorer.score(ref, house("Hải Châu", "Hải Châu 1", "80", "5000000000", 3)).score();
        double district = ComparableSimilarityScorer.score(ref, house("Hải Châu", "Thạch Thang", "80", "5000000000", 3)).score();
        double neighbour = ComparableSimilarityScorer.score(ref, house("Thanh Khê", "Tân Chính", "80", "5000000000", 3)).score();
        assertTrue(ward > district, "same ward must outrank same district");
        assertTrue(district > neighbour, "same district must outrank a neighbouring district");
    }

    @Test
    void districtComparisonIgnoresCaseAndPadding() {
        assertEquals(1.0, ComparableSimilarityScorer.locationScore("Hải Châu", "A", "HẢI CHÂU ", "A"), 1e-9);
    }

    @Test
    void areaRatioMakesLargerDifferencesScoreLower() {
        var ref = house("Sơn Trà", "An Hải Bắc", "80", "5000000000", 3);
        double close = ComparableSimilarityScorer.score(ref, house("Sơn Trà", "An Hải Bắc", "85", "5000000000", 3)).score();
        double far = ComparableSimilarityScorer.score(ref, house("Sơn Trà", "An Hải Bắc", "200", "5000000000", 3)).score();
        assertTrue(close > far);
    }

    @Test
    void priceIsOnlyATinyTerm() {
        var ref = house("Cẩm Lệ", "Hòa Thọ Đông", "80", "5000000000", 3);
        double samePrice = ComparableSimilarityScorer.score(ref, house("Cẩm Lệ", "Hòa Thọ Đông", "80", "5000000000", 3)).score();
        double doubledPrice = ComparableSimilarityScorer.score(ref, house("Cẩm Lệ", "Hòa Thọ Đông", "80", "10000000000", 3)).score();
        assertTrue(samePrice - doubledPrice > 0, "price difference must lower the score");
        // Doubling the price may only cost the price weight (0.08), never dominate the ranking.
        assertTrue(samePrice - doubledPrice <= ComparableSimilarityScorer.W_PRICE + 1e-9);
    }

    @Test
    void unknownWardDoesNotCountAsSameWard() {
        assertEquals(0.82, ComparableSimilarityScorer.locationScore("Hải Châu", null, "Hải Châu", null), 1e-9);
    }

    @Test
    void breakdownExplainsNonGeometricTerms() {
        var ref = house("Hải Châu", "Hải Châu 1", "80", "5000000000", 3);
        var result = ComparableSimilarityScorer.score(ref, house("Hải Châu", "Hải Châu 1", "80", "5000000000", 3));
        assertTrue(result.breakdown().containsKey("location"));
        assertTrue(result.breakdown().containsKey("area"));
        assertTrue(result.breakdown().containsKey("bedrooms"));
        assertEquals("cùng loại hình", result.breakdown().get("type"));
    }

    @Test
    void typeMismatchIsPenalisedHard() {
        var ref = house("Hải Châu", "Hải Châu 1", "80", "5000000000", 3);
        var land = new ComparableSimilarityScorer.Input("Hải Châu", "Hải Châu 1", "LAND",
            new BigDecimal("80"), new BigDecimal("5000000000"), 3, 3, new BigDecimal("5"));
        double same = ComparableSimilarityScorer.score(ref, ref).score();
        double mixed = ComparableSimilarityScorer.score(ref, land).score();
        assertEquals(same / 2, mixed, 1e-9);
    }

    @Test
    void missingOptionalFieldsAreSkippedNotPenalised() {
        var ref = new ComparableSimilarityScorer.Input("Hải Châu", "Hải Châu 1", "HOUSE",
            new BigDecimal("80"), new BigDecimal("5000000000"), null, null, null);
        var cand = new ComparableSimilarityScorer.Input("Hải Châu", "Hải Châu 1", "HOUSE",
            new BigDecimal("80"), new BigDecimal("5000000000"), 4, 2, new BigDecimal("6"));
        assertEquals(1.0, ComparableSimilarityScorer.score(ref, cand).score(), 1e-9);
    }

    @Test
    void scoreStaysInsideUnitInterval() {
        var ref = house("Hòa Vang", null, "1000", "1000000000", 2);
        var cand = house("Sơn Trà", "Thọ Quang", "20", "100000000000", 8);
        double score = ComparableSimilarityScorer.score(ref, cand).score();
        assertTrue(score >= 0.0 && score <= 1.0);
    }

    @Test
    void fractionalFrontageIsNotTruncated() {
        var ref = new ComparableSimilarityScorer.Input("Hải Châu", "Hải Châu 1", "HOUSE",
            new BigDecimal("80"), new BigDecimal("5000000000"), 3, 3, new BigDecimal("5.5"));
        var near = new ComparableSimilarityScorer.Input("Hải Châu", "Hải Châu 1", "HOUSE",
            new BigDecimal("80"), new BigDecimal("5000000000"), 3, 3, new BigDecimal("5.6"));
        var far = new ComparableSimilarityScorer.Input("Hải Châu", "Hải Châu 1", "HOUSE",
            new BigDecimal("80"), new BigDecimal("5000000000"), 3, 3, new BigDecimal("9.5"));
        double nearScore = ComparableSimilarityScorer.score(ref, near).score();
        double farScore = ComparableSimilarityScorer.score(ref, far).score();
        assertTrue(nearScore > farScore, "0.1 m difference must beat a 4 m difference");
    }

    @Test
    void landUsesOnlyPhysicalLandAttributesAndIgnoresPriceInValuation() {
        var land = typed("LAND", 3, 2, "5", "8", "ABC");
        var result = ComparableSimilarityScorer.score(land, land, ComparableDtos.Purpose.VALUATION_SUPPORT);
        assertEquals(java.util.Set.of("location", "area", "frontage", "roadWidth", "type"), result.breakdown().keySet());
        assertEquals(1.0, result.featureCoverage(), 1e-9);
    }

    @Test
    void apartmentsUseProjectAndBedroomsWhileVillaUsesStructuralAttributes() {
        var apartment = typed("APARTMENT", 3, 2, "5", "8", "project-one");
        var other = typed("APARTMENT", 3, 3, "7", "2", "project-two");
        var same = ComparableSimilarityScorer.score(apartment, apartment, ComparableDtos.Purpose.VALUATION_SUPPORT);
        var moved = ComparableSimilarityScorer.score(apartment, other, ComparableDtos.Purpose.VALUATION_SUPPORT);
        assertEquals(java.util.Set.of("location", "area", "bedrooms", "project", "type"), moved.breakdown().keySet());
        assertTrue(same.score() > moved.score());
        var villa = typed("VILLA", 0, 3, "7", "8", "project-one");
        var result = ComparableSimilarityScorer.score(villa, villa, ComparableDtos.Purpose.BUYER_BUDGET_SEARCH);
        assertTrue(result.breakdown().keySet().containsAll(java.util.Set.of("bedrooms", "floors", "frontage", "roadWidth")));
        assertFalse(result.breakdown().containsKey("price"));
        assertFalse(result.breakdown().containsKey("project"));
    }

    @Test
    void coverageShrinkageChangesOrderOnSparseFixturesAndIsKeptOutsideProductionScore() {
        var reference = typed("HOUSE", 3, 2, "5", "8", null);
        var complete = typed("HOUSE", 4, 2, "5", "8", null);
        var sparse = typed("HOUSE", null, null, null, null, null);
        var purpose = ComparableDtos.Purpose.VALUATION_SUPPORT;
        var wide = ComparableSimilarityScorer.score(reference, complete, purpose);
        var thin = ComparableSimilarityScorer.score(reference, sparse, purpose);
        assertTrue(thin.score() > wide.score());
        assertTrue(thin.featureCoverage() < wide.featureCoverage());
        assertTrue(adjusted(thin, 0.05) > adjusted(wide, 0.05));
        assertTrue(adjusted(thin, 0.25) < adjusted(wide, 0.25));
        assertTrue(adjusted(thin, 0.50) < adjusted(wide, 0.50));
        assertFalse(thin.breakdown().containsKey("bedrooms"));
    }

    private static double adjusted(ComparableSimilarityScorer.Result value, double weight) {
        return value.score() * ((1 - weight) + weight * value.featureCoverage());
    }

    private static ComparableSimilarityScorer.Input typed(String type, Integer bedrooms, Integer floors, String frontage,
                                                          String road, String project) {
        return new ComparableSimilarityScorer.Input("Hải Châu", "Hải Châu 1", type, new BigDecimal("80"),
            new BigDecimal("3000000000"), bedrooms, floors, frontage == null ? null : new BigDecimal(frontage),
            road == null ? null : new BigDecimal(road), project);
    }

    @Test
    void neighboursAreSymmetric() {
        assertTrue(ComparableSimilarityScorer.areNeighbours("Hải Châu", "Cẩm Lệ"));
        assertTrue(ComparableSimilarityScorer.areNeighbours("Cẩm Lệ", "Hải Châu"));
        assertTrue(!ComparableSimilarityScorer.areNeighbours("Sơn Trà", "Hòa Vang"));
        assertTrue(!ComparableSimilarityScorer.areNeighbours("Hải Châu", "Hoàng Sa"));
    }
}
