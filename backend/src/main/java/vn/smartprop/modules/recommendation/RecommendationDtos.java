package vn.smartprop.modules.recommendation;

import jakarta.validation.constraints.*;
import java.math.BigDecimal;
import java.util.*;

public final class RecommendationDtos {
    private RecommendationDtos() {}
    public enum Purpose { LIVING, INVESTMENT, RENTAL }
    public enum PropertyType { ALL, HOUSE, APARTMENT, LAND, VILLA, ROOM, COMMERCIAL }
    public record Request(
        @NotNull @DecimalMin("1") @DecimalMax("999999999999999") BigDecimal budgetVnd,
        @NotNull Purpose purpose, @NotNull PropertyType propertyType,
        @DecimalMin(value="0",inclusive=false) @DecimalMax("1000000") BigDecimal minAreaSqm,
        @Size(max=100) String district, @Size(max=100) String ward,
        @Min(1) @Max(10) Integer limit) {}
    public record Source(String kind,String name,String recordKey,String detailUrl) {}

    /**
     * Amenity evidence attached to a recommendation. It always states the administrative
     * level the numbers come from; SmartProp never reports a property-to-POI distance
     * because no candidate carries verified property-level GPS.
     */
    public record PoiEvidence(String name,String category) {}

    public record AmenityEvidence(String areaId,String areaLevel,String areaName,String parentDistrict,
        Double areaAmenityScore,Double amenityFit,double confidence,String evidenceBasis,
        Map<String,Double> categoryScores,List<PoiEvidence> poiEvidence,List<String> dataLimitations,
        String coverage,String note) {}

    public record PropertyResult(String id,String title,PropertyType propertyType,BigDecimal priceVnd,
        BigDecimal areaSqm,String district,String ward,double score,Map<String,Double> scoreBreakdown,
        List<String> explanations,Source source,String qualityStatus,String verificationStatus,
        String duplicateGroup,List<String> warnings,AmenityEvidence amenityEvidence) {
        /** V1 compatibility: no amenity evidence. */
        public PropertyResult(String id,String title,PropertyType propertyType,BigDecimal priceVnd,
                BigDecimal areaSqm,String district,String ward,double score,Map<String,Double> scoreBreakdown,
                List<String> explanations,Source source,String qualityStatus,String verificationStatus,
                String duplicateGroup,List<String> warnings) {
            this(id,title,propertyType,priceVnd,areaSqm,district,ward,score,scoreBreakdown,explanations,
                source,qualityStatus,verificationStatus,duplicateGroup,warnings,null);
        }
    }

    public record AreaResult(String district,String ward,int candidateCount,double score,
        BigDecimal averageAskingPriceVnd,List<String> sources,int unverifiedCount,int needsReviewCount,
        List<String> explanations,List<String> warnings,
        Double amenityScore,Double amenityConfidence,String amenityAreaId,String amenityEvidenceBasis,
        String amenityCoverage,List<PoiEvidence> poiEvidence) {
        /** V1 compatibility: no amenity evidence at all. */
        public AreaResult(String district,String ward,int candidateCount,double score,
                BigDecimal averageAskingPriceVnd,List<String> sources,int unverifiedCount,int needsReviewCount,
                List<String> explanations,List<String> warnings) {
            this(district,ward,candidateCount,score,averageAskingPriceVnd,sources,unverifiedCount,needsReviewCount,
                explanations,warnings,null,null,null,null,null,List.of());
        }
    }

    public record Response(String method,String mode,String priceBasis,Request criteria,int eligibleCandidateCount,
        List<AreaResult> topAreas,List<PropertyResult> topProperties,List<String> warnings,
        Map<String,Double> scoringWeights) {
        /** V1 compatibility: no scoring weight map. */
        public Response(String method,String mode,String priceBasis,Request criteria,int eligibleCandidateCount,
                List<AreaResult> topAreas,List<PropertyResult> topProperties,List<String> warnings) {
            this(method,mode,priceBasis,criteria,eligibleCandidateCount,topAreas,topProperties,warnings,null);
        }
    }

    record Candidate(String id,String title,PropertyType type,BigDecimal price,BigDecimal area,String district,
        String ward,Source source,String quality,String verification,String duplicateGroup,boolean duplicate,
        boolean holdout,List<String> issues,boolean groupHasHoldout) {}
    record Scored(Candidate candidate,double score,Map<String,Double> parts,List<String> explanations) {}
}