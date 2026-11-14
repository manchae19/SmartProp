package vn.smartprop.comparable;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

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
    void neighboursAreSymmetric() {
        assertTrue(ComparableSimilarityScorer.areNeighbours("Hải Châu", "Cẩm Lệ"));
        assertTrue(ComparableSimilarityScorer.areNeighbours("Cẩm Lệ", "Hải Châu"));
        assertTrue(!ComparableSimilarityScorer.areNeighbours("Sơn Trà", "Hòa Vang"));
        assertTrue(!ComparableSimilarityScorer.areNeighbours("Hải Châu", "Hoàng Sa"));
    }
}
