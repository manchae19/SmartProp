package vn.smartprop.market;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import vn.smartprop.market.MarketAnalyticsCalculator.Computed;
import vn.smartprop.market.MarketAnalyticsCalculator.GroupRow;
import vn.smartprop.market.MarketAnalyticsRepository.CohortRow;

/** Step 21.5B — pure statistics tests (median / quartiles / bands). */
class MarketAnalyticsCalculatorTest {

    private static CohortRow row(String src, String district, String type, String month, double price, double area) {
        return new CohortRow(src, district, "W", type, price, area, month);
    }

    @Test
    @DisplayName("median of odd and even counts matches the SQL definition")
    void median() {
        assertEquals(3.0, MarketAnalyticsCalculator.median(new double[]{1, 2, 3, 4, 5}));
        assertEquals(2.5, MarketAnalyticsCalculator.median(new double[]{1, 2, 3, 4}));
        assertEquals(7.0, MarketAnalyticsCalculator.median(new double[]{7}));
    }

    @Test
    @DisplayName("nearest-rank percentiles (ceil(q*n), 1-based)")
    void percentiles() {
        double[] sorted = {10, 20, 30, 40, 50, 60, 70, 80, 90, 100};
        assertEquals(30.0, MarketAnalyticsCalculator.percentile(sorted, 0.25));
        assertEquals(80.0, MarketAnalyticsCalculator.percentile(sorted, 0.75));
    }

    @Test
    @DisplayName("overall median price/per-m², mean and grouping are correct")
    void computesGroups() {
        List<CohortRow> rows = new ArrayList<>();
        rows.add(row("SMARTPROP", "Hải Châu", "HOUSE", null, 4_000_000_000d, 100));
        rows.add(row("SMARTPROP", "Hải Châu", "HOUSE", null, 6_000_000_000d, 100));
        rows.add(row("EXTERNAL_LISTING", "Sơn Trà", "LAND", null, 8_000_000_000d, 200));
        Computed c = MarketAnalyticsCalculator.compute(rows);

        assertEquals(3, c.overall().count());
        assertEquals(6_000_000_000d, c.overall().medianPriceVnd());
        // ppm2 = [4e7, 6e7, 4e7] -> sorted [4e7, 4e7, 6e7] -> median 4e7
        assertEquals(4_000_000_000d / 100, c.overall().medianPricePerSqm(), 0.001);
        assertEquals(6_000_000_000d, c.overall().meanPriceVnd(), 0.001);
        assertEquals(2, c.districts().size());
        assertEquals(3, c.types().stream().mapToLong(GroupRow::count).sum());
    }

    @Test
    @DisplayName("price and area bands partition all rows exactly once")
    void bands() {
        List<CohortRow> rows = List.of(
            row("SMARTPROP", "A", "HOUSE", null, 500_000_000d, 20),     // price band 0, area band 0
            row("SMARTPROP", "A", "HOUSE", null, 3_500_000_000d, 65),   // price band 3, area band 2
            row("SMARTPROP", "A", "HOUSE", null, 60_000_000_000d, 800)); // price band 7, area band 6
        Computed c = MarketAnalyticsCalculator.compute(rows);
        assertEquals(1, c.priceBands()[0]);
        assertEquals(1, c.priceBands()[3]);
        assertEquals(1, c.priceBands()[7]);
        assertEquals(1, c.areaBands()[0]);
        assertEquals(1, c.areaBands()[2]);
        assertEquals(1, c.areaBands()[6]);
        long sum = 0;
        for (long b : c.priceBands()) sum += b;
        assertEquals(3, sum);
    }

    @Test
    @DisplayName("empty cohort yields zero counts and no NaN crash")
    void empty() {
        Computed c = MarketAnalyticsCalculator.compute(List.of());
        assertEquals(0, c.overall().count());
        assertEquals(0, c.districts().size());
    }
}
