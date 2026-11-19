package vn.smartprop.modules.media;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;

/**
 * Projections for YOLOv8 object analysis.
 *
 * <p>The wording is deliberately factual: these DTOs describe what a model
 * reported, never what a property is worth, how many bedrooms it has, or
 * whether its paperwork is valid.
 */
public final class ImageAnalysisDtos {
    private ImageAnalysisDtos() {}

    /** One detected object, already filtered to the property allowlist. */
    public record Detection(
        int cocoId,
        String cocoName,
        String label,
        String group,
        BigDecimal confidence,
        List<BigDecimal> box,
        List<Integer> boxPixels
    ) {}

    /** Document-likeness hint; never a legal verdict. */
    public record DocumentHint(
        boolean likelyDocument,
        BigDecimal brightFraction,
        BigDecimal lowSaturationFraction,
        BigDecimal contrast,
        String reason
    ) {}

    public record ImageResult(
        String imageId,
        String status,
        String modelVersion,
        String algorithmVersion,
        int detectionCount,
        Map<String, Integer> countsByLabel,
        List<Detection> detections,
        DocumentHint documentHint,
        BigDecimal inferenceMs,
        Instant analyzedAt,
        String errorCode
    ) {}

    public record AnalysisView(
        String propertyId,
        String status,
        Instant analyzedAt,
        String algorithmVersion,
        String modelVersion,
        String errorCode,
        List<ImageResult> images,
        List<String> limitations
    ) {}

    /** Admin projection: adds listing identity so a moderator can navigate. */
    public record AdminItem(
        String propertyId,
        String propertyImageId,
        String listingCode,
        String title,
        String analysisStatus,
        int detectionCount,
        Map<String, Integer> countsByLabel,
        boolean documentLike,
        String modelVersion,
        Instant analyzedAt,
        String errorCode
    ) {}
}
