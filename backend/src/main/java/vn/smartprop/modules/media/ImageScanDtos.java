package vn.smartprop.modules.media;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;

/** Public/owner/admin projections for automatic image scans. */
public final class ImageScanDtos {
    private ImageScanDtos() {}

    public record Evidence(
        String propertyId,
        String listingCode,
        String title,
        String imageId,
        String imageUrl,
        String listingUrl,
        BigDecimal similarity,
        String classification,
        String method,
        Map<String, Object> evidence
    ) {}

    public record ImageResult(
        String imageId,
        String status,
        String classification,
        BigDecimal similarity,
        String method,
        String errorCode,
        List<Evidence> matches,
        List<Evidence> intraMatches
    ) {}

    public record ScanView(
        String propertyId,
        String status,
        Instant scannedAt,
        String algorithmVersion,
        String errorCode,
        List<ImageResult> images,
        List<String> limitations
    ) {}

    public record AdminItem(
        String propertyId,
        String propertyImageId,
        String listingCode,
        String title,
        String scanStatus,
        String classification,
        BigDecimal similarity,
        String matchedPropertyId,
        String matchedListingCode,
        String method,
        Instant scannedAt,
        String errorCode
    ) {}
}
