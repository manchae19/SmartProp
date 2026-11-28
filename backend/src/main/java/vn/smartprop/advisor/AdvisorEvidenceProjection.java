package vn.smartprop.advisor;

import com.fasterxml.jackson.databind.JsonNode;
import java.math.BigDecimal;
import java.util.List;
import vn.smartprop.advisor.AdvisorDtos.ComparableEvidence;
import vn.smartprop.advisor.AdvisorDtos.Evidence;
import vn.smartprop.advisor.AdvisorDtos.EvidenceFreshness;
import vn.smartprop.advisor.AdvisorDtos.EvidenceKind;
import vn.smartprop.advisor.AdvisorDtos.EvidenceLimitation;
import vn.smartprop.advisor.AdvisorDtos.EvidenceSource;
import vn.smartprop.advisor.AdvisorDtos.EvidenceStatus;
import vn.smartprop.advisor.AdvisorDtos.ValuationEvidence;
import vn.smartprop.comparable.ComparableDtos;
import vn.smartprop.gis.GisDtos.LocationIntelligence;
import vn.smartprop.modules.recommendation.RecommendationDtos.Source;

import static vn.smartprop.advisor.AdvisorDtos.EvidenceKind.*;
import static vn.smartprop.advisor.AdvisorDtos.EvidenceLimitation.*;
import static vn.smartprop.advisor.AdvisorDtos.EvidenceSource.*;
import static vn.smartprop.advisor.AdvisorDtos.EvidenceStatus.*;

/** Projects only metadata from already-authorized results. It performs no lookups. */
final class AdvisorEvidenceProjection {
    private AdvisorEvidenceProjection() {}

    static List<Evidence> project(Source listing, ValuationEvidence valuation, ComparableEvidence similar,
                                  ComparableEvidence valuationComparables, LocationIntelligence location,
                                  boolean comparablesRequested) {
        EvidenceStatus valuationStatus = valuationStatus(valuation);
        return List.of(
            entry(VALUATION, XGBOOST_V1_3, valuationStatus, ESTIMATED_ASKING_PRICE),
            entry(EXPLANATION, WP04_TREESHAP, explanationStatus(valuation, valuationStatus), MODEL_ATTRIBUTION),
            comparable(SIMILAR_LISTING, similar, comparablesRequested),
            comparable(VALUATION_SUPPORT, valuationComparables, comparablesRequested),
            location(location),
            recommendation(listing)
        );
    }

    private static EvidenceStatus valuationStatus(ValuationEvidence value) {
        if (value == null || value.status() == null) return MISSING;
        if (value.available()) {
            return "AVAILABLE".equals(value.status()) && "v1.3".equals(value.modelVersion())
                && positive(value.predictedAskingPriceVnd())
                ? AVAILABLE : INVALID;
        }
        if (value.predictedAskingPriceVnd() != null) return INVALID;
        return switch (value.status()) {
            case "SKIPPED_BY_REQUEST" -> NOT_REQUESTED;
            case "SKIPPED_MISSING_FEATURES" -> MISSING;
            case "SERVICE_UNAVAILABLE", "SKIPPED_UNSUPPORTED_TYPE", "SKIPPED_OUT_OF_RANGE_AREA",
                "SKIPPED_UNSUPPORTED_LOCATION", "SKIPPED_RESEARCH_RECORD" -> UNAVAILABLE;
            default -> INVALID;
        };
    }

    private static EvidenceStatus explanationStatus(ValuationEvidence value, EvidenceStatus valuationStatus) {
        if (valuationStatus != AVAILABLE) return valuationStatus;
        JsonNode explanation = value.explanation();
        if (explanation == null || explanation.isNull()) return MISSING;
        if (!explanation.isObject() || !"1.0".equals(explanation.path("explanation_version").asText())
                || !explanation.path("limitations").isArray()) return INVALID;

        return switch (explanation.path("status").asText()) {
            case "AVAILABLE", "PARTIAL" -> "XGBOOST_NATIVE_TREESHAP".equals(explanation.path("method").asText())
                && "ASKING_PRICE_VND".equals(explanation.path("target").asText())
                && "LOG1P_PRICE_VND".equals(explanation.path("output_space").asText())
                && explanation.path("predicted_margin_log").isNumber() && explanation.path("base_value_log").isNumber()
                    ? EvidenceStatus.valueOf(explanation.path("status").asText()) : INVALID;
            case "UNAVAILABLE", "NOT_SUPPORTED" -> UNAVAILABLE;
            default -> INVALID;
        };
    }

    private static Evidence comparable(EvidenceKind kind, ComparableEvidence value, boolean requested) {
        if (!requested) return entry(kind, WP02_COMPARABLE, NOT_REQUESTED, ASKING_PRICE_ONLY);
        if (value == null || value.status() == null) return entry(kind, WP02_COMPARABLE, MISSING, ASKING_PRICE_ONLY);
        return switch (value.status()) {
            case "DEGRADED", "SKIPPED_UNSUPPORTED_INPUT" -> entry(kind, WP02_COMPARABLE, UNAVAILABLE, ASKING_PRICE_ONLY);
            case "EMPTY_NO_MATCHES" -> entry(kind, WP02_COMPARABLE, INSUFFICIENT_EVIDENCE, ASKING_PRICE_ONLY, TOO_FEW_COMPARABLES);
            case "AVAILABLE" -> comparableCohort(kind, value.cohort());
            default -> entry(kind, WP02_COMPARABLE, INVALID, ASKING_PRICE_ONLY);
        };
    }

    private static Evidence comparableCohort(EvidenceKind kind, ComparableDtos.Evidence cohort) {
        if (cohort == null) return entry(kind, WP02_COMPARABLE, MISSING, ASKING_PRICE_ONLY);
        if (cohort.purpose() == null || !kind.name().equals(cohort.purpose().name())
                || cohort.status() == null || cohort.uniqueEligibleCandidateCount() < 0) {
            return entry(kind, WP02_COMPARABLE, INVALID, ASKING_PRICE_ONLY);
        }
        if (cohort.uniqueEligibleCandidateCount() < 3) {
            return entry(kind, WP02_COMPARABLE, INSUFFICIENT_EVIDENCE, ASKING_PRICE_ONLY, TOO_FEW_COMPARABLES);
        }
        if (cohort.status() != ComparableDtos.EvidenceStatus.AVAILABLE) {
            return entry(kind, WP02_COMPARABLE, PARTIAL, ASKING_PRICE_ONLY, COMPARABLE_EXAMPLES_ONLY);
        }
        var stats = cohort.scannedCohortAskingPrice();
        boolean valid = cohort.scanComplete() && stats != null && stats.observations() >= 5
            && stats.observations() <= cohort.uniqueEligibleCandidateCount()
            && positive(stats.medianPriceVnd()) && positive(stats.medianPricePerSqmVnd());
        return entry(kind, WP02_COMPARABLE, valid ? AVAILABLE : INVALID, ASKING_PRICE_ONLY);
    }

    private static boolean positive(BigDecimal price) {
        return price != null && price.signum() > 0;
    }

    private static Evidence location(LocationIntelligence value) {
        if (value == null) return entry(LOCATION, SMARTPROP_GIS_POI, MISSING, AREA_CONTEXT_ONLY);
        return value.mapEligible()
            ? entry(LOCATION, SMARTPROP_GIS_POI, AVAILABLE, STRAIGHT_LINE_DISTANCE)
            : entry(LOCATION, SMARTPROP_GIS_POI, PARTIAL, AREA_CONTEXT_ONLY);
    }

    private static Evidence recommendation(Source listing) {
        EvidenceSource source = listing == null || listing.kind() == null ? null : switch (listing.kind()) {
            case "PROPERTY" -> SMARTPROP_LISTING;
            case "EXTERNAL" -> EXTERNAL_LISTING;
            case "TINIX_AI" -> TINIX_RESEARCH;
            default -> null;
        };
        return entry(RECOMMENDATION, source, source == null ? MISSING : AVAILABLE, HEURISTIC_FIT, ASKING_PRICE_ONLY);
    }

    private static Evidence entry(EvidenceKind kind, EvidenceSource source, EvidenceStatus status,
                                  EvidenceLimitation... limitations) {
        // None of the current Advisor inputs carries an authoritative observation or generation timestamp.
        return new Evidence(kind, source, status, null, null, EvidenceFreshness.UNKNOWN, List.of(limitations),
            kind.reference());
    }
}
