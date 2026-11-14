package vn.smartprop.market;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import vn.smartprop.market.MarketAnalyticsRepository.CohortRow;

/**
 * Pure statistics over an in-memory cohort (no I/O) — medians and quartiles are
 * computed here so the MySQL-side load stays a single scan. Price values are whole
 * VND below 2^53, so {@code double} is exact for them.
 */
public final class MarketAnalyticsCalculator {

    private MarketAnalyticsCalculator() {}

    public record GroupRow(
        String key,
        long count,
        double medianPriceVnd,
        double p25PriceVnd,
        double p75PriceVnd,
        double meanPriceVnd,
        double medianPricePerSqm,
        double medianAreaSqm
    ) {}

    public record Computed(
        GroupRow overall,
        List<GroupRow> districts,
        List<GroupRow> wards,
        List<GroupRow> types,
        List<GroupRow> sources,
        List<GroupRow> months,
        long[] priceBands,
        long[] areaBands
    ) {}

    private static final double[] PRICE_EDGES =
        {1e9, 2e9, 3e9, 5e9, 10e9, 20e9, 50e9};
    private static final double[] AREA_EDGES =
        {30, 50, 80, 120, 200, 500};

    public static Computed compute(List<CohortRow> rows) {
        List<CohortRow> safe = rows == null ? List.of() : rows;
        return new Computed(
            group("ALL", safe),
            groups(safe, r -> r.district() == null || r.district().isBlank() ? "Chưa xác định" : r.district()),
            groups(safe, r -> (r.district() == null ? "" : r.district()) + "|" + (r.ward() == null ? "" : r.ward())),
            groups(safe, r -> r.propertyType() == null || r.propertyType().isBlank() ? "OTHER" : r.propertyType()),
            groups(safe, CohortRow::source),
            groups(safe.stream().filter(r -> r.month() != null && !r.month().isBlank()).toList(), CohortRow::month),
            bandCounts(safe, PRICE_EDGES, true),
            bandCounts(safe, AREA_EDGES, false));
    }

    private static List<GroupRow> groups(List<CohortRow> rows, Function<CohortRow, String> key) {
        Map<String, List<CohortRow>> buckets = new LinkedHashMap<>();
        for (CohortRow row : rows) {
            buckets.computeIfAbsent(key.apply(row), k -> new ArrayList<>()).add(row);
        }
        List<GroupRow> out = new ArrayList<>(buckets.size());
        for (var entry : buckets.entrySet()) out.add(group(entry.getKey(), entry.getValue()));
        return out;
    }

    static GroupRow group(String key, List<CohortRow> rows) {
        int n = rows.size();
        if (n == 0) {
            return new GroupRow(key, 0, Double.NaN, Double.NaN, Double.NaN, Double.NaN, Double.NaN, Double.NaN);
        }
        double[] price = new double[n];
        double[] area = new double[n];
        double[] ppm2 = new double[n];
        double sum = 0;
        for (int i = 0; i < n; i++) {
            CohortRow r = rows.get(i);
            price[i] = r.priceVnd();
            area[i] = r.areaSqm();
            ppm2[i] = r.areaSqm() > 0 ? r.priceVnd() / r.areaSqm() : 0;
            sum += r.priceVnd();
        }
        Arrays.sort(price);
        Arrays.sort(area);
        Arrays.sort(ppm2);
        return new GroupRow(key, n,
            median(price), percentile(price, 0.25), percentile(price, 0.75), sum / n,
            median(ppm2), median(area));
    }

    static double median(double[] sorted) {
        int n = sorted.length;
        if (n == 0) return Double.NaN;
        if (n % 2 == 1) return sorted[n / 2];
        return (sorted[n / 2 - 1] + sorted[n / 2]) / 2.0;
    }

    /** Nearest-rank percentile, 1-based rank ceil(q*n) (matches the SQL window used earlier). */
    static double percentile(double[] sorted, double q) {
        int n = sorted.length;
        if (n == 0) return Double.NaN;
        int rank = (int) Math.ceil(q * n);
        int idx = Math.min(n - 1, Math.max(0, rank - 1));
        return sorted[idx];
    }

    private static long[] bandCounts(List<CohortRow> rows, double[] edges, boolean price) {
        long[] counts = new long[edges.length + 1];
        for (CohortRow r : rows) {
            double v = price ? r.priceVnd() : r.areaSqm();
            int idx = 0;
            while (idx < edges.length && v >= edges[idx]) idx++;
            counts[idx]++;
        }
        return counts;
    }
}
