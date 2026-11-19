package vn.smartprop.market;

import java.math.BigDecimal;
import java.util.List;

/**
 * Step 21.5B — Real-Data Market Analytics contracts.
 *
 * <p>All figures are <b>asking prices</b> derived from live MySQL rows (no hardcoded
 * numbers). Research rows (TiniX, CC BY-NC 4.0) are always labelled per source and are
 * never presented as verified listings or as a market forecast.
 */
public final class MarketDtos {
    private MarketDtos() {}

    public enum Source { ALL, SMARTPROP, EXTERNAL_LISTING, TINIX_RESEARCH }

    /** Normalized, validated filter for one analytics request. */
    public record Query(String district, String ward, String propertyType, Source source, boolean includeResearch) {}

    public record Filters(String district, String ward, String propertyType, String source, boolean includeResearch) {}

    /** One aggregated cell (overall, per district, per type, per source …). */
    public record Stat(
        String key,
        String label,
        long count,
        BigDecimal medianAskingPriceVnd,
        BigDecimal medianPricePerSqm,
        BigDecimal p25AskingPriceVnd,
        BigDecimal p75AskingPriceVnd,
        BigDecimal meanAskingPriceVnd,
        BigDecimal medianAreaSqm,
        String dataStatus,
        List<String> qualityFlags
    ) {}

    public record Band(String label, long count) {}

    public record SourceCount(String source, String label, long count, boolean researchReference, String license) {}

    public record MonthlyPoint(String period, long count, BigDecimal medianAskingPriceVnd, BigDecimal medianPricePerSqm, String dataStatus) {}

    public record Meta(
        String generatedAt,
        Filters filters,
        long totalSampleCount,
        int minSample,
        String priceBasis,
        String disclaimer,
        boolean researchIncluded,
        String researchLicense,
        String temporalStatus,
        List<String> dataQualityWarnings
    ) {}

    public record Response(
        Meta meta,
        Stat overall,
        List<Stat> byDistrict,
        List<Stat> byWard,
        List<Stat> byPropertyType,
        List<SourceCount> bySource,
        List<Band> priceBands,
        List<Band> areaBands,
        List<MonthlyPoint> monthly
    ) {}
}
