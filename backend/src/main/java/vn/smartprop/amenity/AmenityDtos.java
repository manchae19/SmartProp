package vn.smartprop.amenity;

import com.fasterxml.jackson.annotation.JsonIgnore;
import java.util.List;
import java.util.Map;

public final class AmenityDtos {
    private AmenityDtos() {}

    public record CategoryScores(
        double essentials,
        double education,
        double healthcare,
        double transit,
        double recreation
    ) {}

    public record PoiCounts(
        int total,
        int school,
        int hospital,
        int pharmacy,
        int market,
        int supermarket,
        int park,
        int beach,
        int transit
    ) {}

    public record PoiEvidenceItem(
        String name,
        String category,
        String attributionBasis
    ) {}

    public record AmenityProfile(
        String areaId,
        String areaLevel,
        String areaName,
        String parentDistrict,
        double livingScore,
        CategoryScores categoryScores,
        double confidence,
        double diversityIndex,
        /**
         * Research-only count derived from the TiniX dataset. Never serialised on the
         * public amenities API; see ResearchAmenityController for the guarded view.
         */
        @JsonIgnore int sampleListingCount,
        PoiCounts poiCounts,
        Double areaKm2,
        Double densityPerKm2,
        String completenessTier,
        String hasCriticalGaps,
        List<PoiEvidenceItem> poiEvidence,
        String amenitySummary,
        List<String> sources,
        List<String> dataLimitations
    ) {}

    public record AreaSummary(
        String areaId,
        String areaLevel,
        String areaName,
        String parentDistrict,
        double livingScore,
        double confidence,
        @JsonIgnore int sampleListingCount,
        String completenessTier
    ) {}

    /** Internal research view: identical profile plus the restricted sample count. */
    public record ResearchAmenityProfile(AmenityProfile profile, int sampleListingCount) {}

    public record CatalogSummary(
        String catalogVersion,
        String jurisdiction,
        int totalEffectivePois,
        int totalAreasAnalyzed,
        Map<String, Integer> countsByLevel,
        Map<String, Double> livingPurposeWeights
    ) {}
}
