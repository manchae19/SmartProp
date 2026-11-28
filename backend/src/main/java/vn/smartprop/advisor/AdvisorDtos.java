package vn.smartprop.advisor;

import com.fasterxml.jackson.annotation.JsonInclude;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import com.fasterxml.jackson.databind.JsonNode;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import vn.smartprop.gis.GisDtos.AreaPurposeInsight;
import vn.smartprop.gis.GisDtos.LocationIntelligence;
import vn.smartprop.modules.recommendation.RecommendationDtos.AmenityEvidence;
import vn.smartprop.modules.recommendation.RecommendationDtos.AreaResult;
import vn.smartprop.modules.recommendation.RecommendationDtos.PropertyType;
import vn.smartprop.modules.recommendation.RecommendationDtos.Purpose;
import vn.smartprop.modules.recommendation.RecommendationDtos.Source;

/**
 * Unified API contracts for Step 21.3 — AI Advisor Integration.
 *
 * <p>Guarantees:
 * <ul>
 *   <li>No PII fields (phone, email, owner identity, raw street address) exist anywhere in the DTO tree.</li>
 *   <li>Heuristic scores carry explicit uncalibrated labels and are never presented as probabilities.</li>
 *   <li>Research observations (TiniX CC BY-NC 4.0) carry {@code researchReference=true},
 *       {@code liveListing=false}, {@code availabilityStatus="UNKNOWN_HISTORICAL_RESEARCH"}, and {@code null} URLs.</li>
 *   <li>Valuation (XGBoost V1.3) and Comparable Evidence are independent signals; V1.3 output is never fed into
 *       Comparable Ranking or used to self-confirm accuracy.</li>
 * </ul>
 */
public final class AdvisorDtos {
    private AdvisorDtos() {}

    public record AdvisorRequest(
        @NotNull @DecimalMin("1") @DecimalMax("999999999999999") BigDecimal budgetVnd,
        @Min(0) @Max(30) Integer budgetFlexibilityPct,
        @NotNull Purpose purpose,
        @NotNull PropertyType propertyType,
        @DecimalMin(value = "0", inclusive = false) @DecimalMax("1000000") BigDecimal minAreaSqm,
        @Size(max = 100) String district,
        @Size(max = 100) String ward,
        @Min(1) @Max(10) Integer limit,
        Boolean includeComparables,
        Boolean includeValuation,
        Boolean includeResearch
    ) {}

    public record ResolvedCriteria(
        BigDecimal statedBudgetVnd,
        int budgetFlexibilityPct,
        BigDecimal effectiveCeilingVnd,
        Purpose purpose,
        PropertyType propertyType,
        BigDecimal minAreaSqm,
        String district,
        String ward,
        int limit,
        boolean includeComparables,
        boolean includeValuation,
        boolean includeResearch
    ) {}

    public record ServiceStatus(
        String recommendationService,
        String areaService,
        String comparableService,
        String valuationService,
        boolean partialResult
    ) {}

    public record ShapFactorItem(
        String featureName,
        String label,
        double shapValue,
        double impactPct,
        String direction,
        String contextNote
    ) {}

    public record ShapSummary(
        String method,
        String scale,
        double baseValueLog,
        long basePriceVnd,
        String summaryVi,
        List<ShapFactorItem> topFactors
    ) {}

    public record ValuationEvidence(
        String status,
        boolean available,
        String reason,
        String modelVersion,
        String modelRun,
        BigDecimal predictedAskingPriceVnd,
        BigDecimal askingVsEstimatePct,
        String priceBasis,
        Map<String, Object> featuresUsed,
        List<String> missingFeatures,
        ShapSummary shapExplanation,
        List<String> warnings,
// WP-04: FastAPI explanation passed through unchanged (null when absent).
JsonNode explanation
    ) {
        /** Backward-compatible: callers that predate WP-04 carry no explanation. */
        public ValuationEvidence(String status, boolean available, String reason,
                String modelVersion, String modelRun, BigDecimal predictedAskingPriceVnd,
                BigDecimal askingVsEstimatePct, String priceBasis,
                Map<String, Object> featuresUsed, List<String> missingFeatures,
                ShapSummary shapExplanation, List<String> warnings) {
            this(status, available, reason, modelVersion, modelRun, predictedAskingPriceVnd,
                    askingVsEstimatePct, priceBasis, featuresUsed, missingFeatures,
                    shapExplanation, warnings, null);
        }
    }

    public record ComparableItem(
        String candidateId,
        String sourceKind,
        String sourceLabel,
        boolean liveListing,
        boolean researchReference,
        String verificationStatus,
        String propertyType,
        String district,
        String ward,
        BigDecimal areaSqm,
        BigDecimal askingPriceVnd,
        BigDecimal priceDifferencePct,
        Integer bedrooms,
        Integer floors,
        BigDecimal frontageM,
        double similarityScore,
        String scoreType,
        Map<String, String> scoreBreakdown,
        String listingUrl,
        String datasetLicense,
        String attribution,
        Double featureCoverage
    ) {
        public ComparableItem(String candidateId, String sourceKind, String sourceLabel,
                              boolean liveListing, boolean researchReference, String verificationStatus,
                              String propertyType, String district, String ward, BigDecimal areaSqm,
                              BigDecimal askingPriceVnd, BigDecimal priceDifferencePct, Integer bedrooms,
                              Integer floors, BigDecimal frontageM, double similarityScore, String scoreType,
                              Map<String, String> scoreBreakdown, String listingUrl, String datasetLicense,
                              String attribution) {
            this(candidateId, sourceKind, sourceLabel, liveListing, researchReference, verificationStatus,
                propertyType, district, ward, areaSqm, askingPriceVnd, priceDifferencePct, bedrooms, floors,
                frontageM, similarityScore, scoreType, scoreBreakdown, listingUrl, datasetLicense, attribution, null);
        }
    }

    public record ComparableEvidence(
        String status,
        int candidateCount,
        String searchStage,
        List<ComparableItem> comparables,
        List<String> warnings,
        vn.smartprop.comparable.ComparableDtos.Evidence cohort
    ) {
        public ComparableEvidence(String status, int candidateCount, String searchStage,
                                  List<ComparableItem> comparables, List<String> warnings) {
            this(status, candidateCount, searchStage, comparables, warnings, null);
        }
    }

    public enum EvidenceKind {
        VALUATION("valuationEvidence"),
        EXPLANATION("valuationEvidence.explanation"),
        SIMILAR_LISTING("comparableEvidence"),
        VALUATION_SUPPORT("valuationComparableEvidence"),
        LOCATION("locationIntelligence"),
        RECOMMENDATION("source");

        private final String reference;

        EvidenceKind(String reference) {
            this.reference = reference;
        }

        public String reference() {
            return reference;
        }
    }

    public enum EvidenceSource {
        XGBOOST_V1_3, WP04_TREESHAP, WP02_COMPARABLE, SMARTPROP_GIS_POI,
        SMARTPROP_LISTING, EXTERNAL_LISTING, TINIX_RESEARCH
    }

    public enum EvidenceStatus {
        AVAILABLE, PARTIAL, MISSING, UNAVAILABLE, INVALID, NOT_REQUESTED, INSUFFICIENT_EVIDENCE
    }

    public enum EvidenceFreshness { UNKNOWN, RECENT, STALE }

    public enum EvidenceLimitation {
        ESTIMATED_ASKING_PRICE, MODEL_ATTRIBUTION, ASKING_PRICE_ONLY, TOO_FEW_COMPARABLES,
        COMPARABLE_EXAMPLES_ONLY, AREA_CONTEXT_ONLY, STRAIGHT_LINE_DISTANCE, HEURISTIC_FIT
    }

    /** Metadata for one existing field on an advised property. */
    public record Evidence(
        EvidenceKind kind,
        EvidenceSource source,
        EvidenceStatus status,
        Instant observedAt,
        Instant generatedAt,
        EvidenceFreshness freshness,
        List<EvidenceLimitation> limitations,
        String reference
    ) {}

    public record AdvisedProperty(
        String id,
        String title,
        PropertyType propertyType,
        BigDecimal priceVnd,
        BigDecimal areaSqm,
        String district,
        String ward,
        boolean withinStatedBudget,
        boolean withinFlexibleBudget,
        BigDecimal budgetDeltaPct,
        double recommendationScore,
        String scoreSemantics,
        Map<String, Double> scoreBreakdown,
        List<String> fitReasons,
        Source source,
        boolean liveListing,
        boolean researchReference,
        String availabilityStatus,
        String qualityStatus,
        String verificationStatus,
        AmenityEvidence amenityEvidence,
        LocationIntelligence locationIntelligence,
        ComparableEvidence comparableEvidence,
        ValuationEvidence valuationEvidence,
        ComparableEvidence valuationComparableEvidence,
        List<String> warnings,
        @JsonInclude(JsonInclude.Include.NON_NULL) List<Evidence> evidence
    ) {}

    public record AdvisorResponse(
        String advisorVersion,
        String mode,
        String recommendationMethod,
        String priceBasis,
        String scoreDisclaimer,
        ResolvedCriteria criteria,
        ServiceStatus serviceStatus,
        int eligibleCandidateCount,
        Map<String, Double> scoringWeights,
        List<AreaResult> topAreas,
        List<AreaPurposeInsight> areaLocationInsights,
        List<AdvisedProperty> recommendedProperties,
        List<String> warnings
    ) {}
}
