package vn.smartprop.gis;

import java.util.List;
import java.util.Map;

/**
 * Data contracts for Step 21.4 — GIS & Location Intelligence Integration.
 *
 * <p>Guarantees:
 * <ul>
 *   <li>Zero raw street addresses or owner contact PII.</li>
 *   <li>Zero fabricated coordinates, centroids, POI points, road distances, or travel times.</li>
 *   <li>Explicit separation between verified property-level WGS84 pins ({@code SRID 4326}) and
 *       administrative-only fallbacks for external/research records.</li>
 * </ul>
 */
public final class GisDtos {
    private GisDtos() {}

    public enum AdminNormalizationStatus {
        RESOLVED_CANONICAL,
        RESOLVED_ROMAN_VARIANT,
        RESOLVED_HISTORICAL_MERGED_WARD,
        RESOLVED_POST_2025_NEW_WARD,
        RESOLVED_WARD_INFERRED_DISTRICT,
        RESOLVED_DISTRICT_ONLY,
        HISTORICAL_SPLIT_WARD_AMBIGUOUS,
        AMBIGUOUS_CROSS_DISTRICT_WARD,
        CONFLICTING_ADMIN_HIERARCHY,
        EXTENDED_QUANG_NAM_JURISDICTION,
        EXCLUDED_ISLAND_DISTRICT,
        OUTSIDE_DANANG,
        INCOMPLETE_LOCATION
    }

    public record AdminNormalizationResult(
        AdminNormalizationStatus status,
        String canonicalDistrict,
        String displayWard,
        String catalogWard,
        String displayLabel,
        List<String> candidateDistricts,
        String provenanceNote
    ) {
        public boolean isResolvedDanangCore() {
            return canonicalDistrict != null && !canonicalDistrict.isBlank();
        }
    }

    public enum CoordinateStatus {
        VERIFIED_EXACT,
        VERIFIED_BOUNDARY_BUFFER,
        VERIFIED_DANANG_POLYGON,
        INVALID_DISTRICT_MISMATCH,
        INVALID_SWAPPED_AXES,
        OUTSIDE_DANANG_BOUNDS,
        INVALID_COORDINATES,
        NONE_ADMIN_ONLY
    }

    public record CoordinateValidationResult(
        CoordinateStatus status,
        boolean usableForPinAndPoi,
        Double verifiedLatitude,
        Double verifiedLongitude,
        String matchedPolygonDistrict,
        Double distanceToDeclaredPolygonMeters,
        String validationNote
    ) {}

    public record NearbyPoiItem(
        String id,
        String name,
        String category,
        String categoryLabelVi,
        double latitude,
        double longitude,
        long distanceMeters,
        String sourceName
    ) {}

    public record PurposeLocationFit(
        String purpose,
        String headlineVi,
        List<String> highlightsVi,
        String spatialBasisNote
    ) {}

    public record LocationIntelligence(
        String locationPrecision,
        String coordinateStatus,
        boolean mapEligible,
        Double latitude,
        Double longitude,
        String canonicalDistrict,
        String canonicalWard,
        String displayLabel,
        String normalizationStatus,
        String adminHierarchyNote,
        String fallbackReason,
        Integer nearbyPoiRadiusMeters,
        String distanceMethod,
        List<NearbyPoiItem> nearbyPois,
        PurposeLocationFit purposeLocationFit
    ) {}

    public record AreaPurposeInsight(
        String areaKey,
        String district,
        String ward,
        String purpose,
        String headlineVi,
        List<String> highlightsVi,
        Map<String, Integer> keyPoiCounts,
        Double poiDensityPerKm2,
        String spatialBasis
    ) {}
}
