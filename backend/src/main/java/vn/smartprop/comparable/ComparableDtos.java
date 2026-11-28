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
    public enum EvidenceStatus { AVAILABLE, INSUFFICIENT_EVIDENCE }
    public record PhysicalFeatures(BigDecimal frontageM, BigDecimal roadWidthM, String projectId) {}

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
        SubjectIdentity subjectIdentity,
        PhysicalFeatures physicalFeatures
    ) {
        public Request(String propertyId, String propertyType, String district, String ward,
                       BigDecimal areaSqm, BigDecimal priceVnd, Integer bedrooms, Integer floors,
                       Integer limit, Boolean includeResearch, Purpose purpose, BigDecimal buyerBudgetVnd,
                       SubjectIdentity subjectIdentity) {
            this(propertyId, propertyType, district, ward, areaSqm, priceVnd, bedrooms, floors, limit,
                includeResearch, purpose, buyerBudgetVnd, subjectIdentity, null);
        }
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
        Integer floors,
        PhysicalFeatures physicalFeatures
    ) {
        public Reference(String propertyId, String propertyType, String district, String ward,
                         BigDecimal areaSqm, BigDecimal priceVnd, Integer bedrooms, Integer floors) {
            this(propertyId, propertyType, district, ward, areaSqm, priceVnd, bedrooms, floors, null);
        }
    }

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
        String attribution,
        Double featureCoverage
    ) {
        public Candidate(String candidateId, SourceKind sourceKind, String sourceLabel, String propertyType,
                         String district, String ward, BigDecimal areaSqm, BigDecimal askingPriceVnd,
                         BigDecimal priceDifferencePct, Integer bedrooms, Integer floors, BigDecimal frontageM,
                         BigDecimal roadWidthM, double similarityScore, Map<String,String> scoreBreakdown,
                         String dataQualityStatus, String listingUrl, String datasetLicense, String attribution) {
            this(candidateId, sourceKind, sourceLabel, propertyType, district, ward, areaSqm, askingPriceVnd,
                priceDifferencePct, bedrooms, floors, frontageM, roadWidthM, similarityScore, scoreBreakdown,
                dataQualityStatus, listingUrl, datasetLicense, attribution, null);
        }
    }

    public record DedupeStats(int eligibleBeforeDedupe, int exactSelfExcluded, int duplicateRowsRemoved) {}
    public record Cap(int initialLimit, int scanLimit, boolean complete) {}
    public record Provenance(int uniqueEligible, int returned, String attribution) {}
    public record AskingPriceStats(int observations, BigDecimal medianPriceVnd, BigDecimal medianPricePerSqmVnd) {}
    public record Evidence(Purpose purpose, EvidenceStatus status, int retrievedCandidateCount,
                           int uniqueEligibleCandidateCount, int returnedSampleCount, DedupeStats dedupe,
                           boolean scanComplete, Map<SourceKind,Cap> caps, Map<SourceKind,Provenance> provenance,
                           AskingPriceStats scannedCohortAskingPrice, List<String> limitations) {}

    public record Response(
        Reference reference,
        int candidateCount,
        String searchStage,
        List<Candidate> comparables,
        List<String> warnings,
        Map<String,Integer> eligibleCountsBySource,
        Evidence evidence
    ) {
        public Response(Reference reference, int candidateCount, String searchStage, List<Candidate> comparables,
                        List<String> warnings, Map<String,Integer> eligibleCountsBySource) {
            this(reference, candidateCount, searchStage, comparables, warnings, eligibleCountsBySource, null);
        }
    }
}
