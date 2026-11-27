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
    public enum Purpose { BUYER_BUDGET_SEARCH, SIMILAR_LISTING, VALUATION_SUPPORT }

    /** Observable identities of the subject listing, when the caller has them. */
    public record SubjectIdentity(Long externalId, String externalSource, String sourceListingId,
                                  String tinixId, String canonicalUrl) {}

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
        Integer limit,
        Boolean includeResearch,
        Purpose purpose,
        BigDecimal buyerBudgetVnd,
        SubjectIdentity subjectIdentity
    ) {
        public Request(String propertyId, String propertyType, String district, String ward,
                       BigDecimal areaSqm, BigDecimal priceVnd, Integer bedrooms, Integer floors,
                       Integer limit, Boolean includeResearch) {
            this(propertyId, propertyType, district, ward, areaSqm, priceVnd, bedrooms, floors,
                limit, includeResearch, null, null, null);
        }

        public Request(
            String propertyId,
            String propertyType,
            String district,
            String ward,
            BigDecimal areaSqm,
            BigDecimal priceVnd,
            Integer bedrooms,
            Integer floors,
            Integer limit
        ) {
            this(propertyId, propertyType, district, ward, areaSqm, priceVnd, bedrooms, floors, limit, null);
        }
    }

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
