package vn.smartprop.comparable;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

/** Request/response shapes for the comparable-properties endpoint.
 *  Carries no contact fields: candidates can come from research data, so a
 *  phone number must never travel to the browser. */
public final class ComparableDtos {
    private ComparableDtos() {}

    public enum SourceKind { SMARTPROP, EXTERNAL_LISTING, TINIX_RESEARCH }

    /** Either an existing property id, or a free-form valuation spec. */
    public record Request(
        String propertyId,
        String propertyType,
        String district,
        String ward,
        BigDecimal areaSqm,
        BigDecimal priceVnd,
        Integer bedrooms,
        Integer floors,
        Integer limit
    ) {}

    public record Reference(
        String propertyId,
        String propertyType,
        String district,
        String ward,
        BigDecimal areaSqm,
        BigDecimal priceVnd,
        Integer bedrooms,
        Integer floors
    ) {}

    /** similarityScore is a heuristic match score in [0,1] - never a probability. */
    public record Candidate(
        String candidateId,
        SourceKind sourceKind,
        String sourceLabel,
        String propertyType,
        String district,
        String ward,
        BigDecimal areaSqm,
        BigDecimal askingPriceVnd,
        BigDecimal priceDifferencePct,
        Integer bedrooms,
        Integer floors,
        BigDecimal frontageM,
        BigDecimal roadWidthM,
        double similarityScore,
        Map<String,String> scoreBreakdown,
        String dataQualityStatus,
        String listingUrl,
        String datasetLicense,
        String attribution
    ) {}

    public record Response(
        Reference reference,
        int candidateCount,
        String searchStage,
        List<Candidate> comparables,
        List<String> warnings,
        Map<String,Integer> eligibleCountsBySource
    ) {}
}
