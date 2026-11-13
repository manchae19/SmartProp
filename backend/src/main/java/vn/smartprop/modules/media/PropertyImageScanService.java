package vn.smartprop.modules.media;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import vn.smartprop.modules.property.Property;
import vn.smartprop.modules.property.PropertyRepository;

import java.math.BigDecimal;
import java.net.URI;
import java.net.http.*;
import java.time.Duration;
import java.time.Instant;
import java.util.*;

/** Automatic, bounded, read-only scan coordinator for property images. */
@Service
public class PropertyImageScanService {
    static final String ALGORITHM_VERSION = "imagecheck-v1";
    private static final int MAX_IMAGES = 30;
    private final PropertyImageRepository images;
    private final PropertyImageScanRepository scans;
    private final PropertyRepository properties;
    private final LocalFileStore files;
    private final CloudinaryImageDelivery cloudinary;
    private final ObjectMapper mapper;
    private final URI scanBase;
    private final HttpClient http;
    private final Set<String> inFlight = java.util.concurrent.ConcurrentHashMap.newKeySet();

    public PropertyImageScanService(PropertyImageRepository images, PropertyImageScanRepository scans,
            PropertyRepository properties, LocalFileStore files, CloudinaryImageDelivery cloudinary,
            ObjectMapper mapper, @Value("${app.image-scan.base-url:http://127.0.0.1:8001}") String scanBase) {
        this.images = images;
        this.scans = scans;
        this.properties = properties;
        this.files = files;
        this.cloudinary = cloudinary;
        this.mapper = mapper;
        this.scanBase = validateBase(scanBase);
        this.http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3))
            .followRedirects(HttpClient.Redirect.NEVER).build();
    }

    private static URI validateBase(String value) {
        try {
            URI uri = URI.create(value);
            if (!"http".equals(uri.getScheme()) || !Set.of("127.0.0.1", "localhost").contains(uri.getHost())
                || uri.getPort() < 1 || uri.getUserInfo() != null || uri.getQuery() != null || uri.getFragment() != null)
                throw new IllegalArgumentException();
            return uri;
        } catch (Exception e) {
            throw new IllegalArgumentException("Invalid image scan base URL", e);
        }
    }

    @Async("imageScanExecutor")
    public void schedule(String propertyId) {
        if (!inFlight.add(propertyId)) return;
        try {
            scan(propertyId);
        } catch (Exception ignored) {
            // scan() persists a visible failure state; never mark a failed scan as clean.
        } finally {
            inFlight.remove(propertyId);
        }
    }

    private byte[] read(PropertyImage image) {
        if ("CLOUDINARY".equals(image.storageProvider)) {
            return cloudinary.fetch(image.cloudinaryCloudName, image.cloudinarySecureUrl).bytes();
        }
        return files.read(image.storageKey);
    }

    private PropertyImageScan row(String propertyId, PropertyImage image, Map<String, PropertyImageScan> existing) {
        PropertyImageScan value = existing.get(image.id);
        if (value == null) {
            value = new PropertyImageScan();
            value.id = UUID.randomUUID().toString();
            value.propertyId = propertyId;
            value.propertyImageId = image.id;
            value.scanStatus = "PENDING";
            value.algorithmVersion = ALGORITHM_VERSION;
            value.evidence = mapper.createObjectNode();
            value.createdAt = Instant.now();
            value.updatedAt = value.createdAt;
        }
        value.scanStatus = "SCANNING";
        value.errorCode = null;
        value.algorithmVersion = ALGORITHM_VERSION;
        return value;
    }

    private void fail(List<PropertyImageScan> rows, String error) {
        Instant now = Instant.now();
        for (var row : rows) {
            row.scanStatus = "PENDING_RETRY";
            row.errorCode = error;
            row.classification = null;
            row.similarity = null;
            row.matchedPropertyId = null;
            row.matchedPropertyImageId = null;
            row.matchedListingCode = null;
            row.detectionMethod = null;
            row.evidence = mapper.createObjectNode();
            row.scannedAt = now;
        }
        scans.saveAll(rows);
    }

    private void scan(String propertyId) {
        List<PropertyImage> current = images.findByPropertyIdAndDeletedAtIsNullOrderBySortOrderAscIdAsc(propertyId);
        if (current.isEmpty()) return;
        if (current.size() > MAX_IMAGES) {
            return;
        }
        Map<String, PropertyImageScan> existing = new HashMap<>();
        scans.findByPropertyIdOrderByCreatedAtAsc(propertyId).forEach(row -> existing.put(row.propertyImageId, row));
        boolean allFresh = current.stream().allMatch(image -> {
            PropertyImageScan row = existing.get(image.id);
            return row != null && "COMPLETED".equals(row.scanStatus) && row.scannedAt != null
                && !row.scannedAt.isBefore(image.updatedAt) && ALGORITHM_VERSION.equals(row.algorithmVersion);
        });
        if (allFresh) return;

        List<PropertyImageScan> rows = new ArrayList<>();
        List<ObjectNode> payloadImages = new ArrayList<>();
        try {
            for (PropertyImage image : current) {
                PropertyImageScan row = row(propertyId, image, existing);
                rows.add(row);
                byte[] bytes = read(image);
                if (bytes == null || bytes.length == 0) throw new IllegalStateException("IMAGE_READ_FAILED");
                ObjectNode payload = mapper.createObjectNode();
                payload.put("imageId", image.id);
                payload.put("mimeType", image.mimeType);
                payload.put("data", Base64.getEncoder().encodeToString(bytes));
                payloadImages.add(payload);
            }
            scans.saveAll(rows);
            ObjectNode body = mapper.createObjectNode();
            body.put("propertyId", propertyId);
            ArrayNode array = body.putArray("images");
            payloadImages.forEach(array::add);
            HttpRequest request = HttpRequest.newBuilder(scanBase.resolve("/image-duplicates/scan"))
                .timeout(Duration.ofSeconds(30)).header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(mapper.writeValueAsString(body))).build();
            HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() != 200) throw new IllegalStateException("SCAN_HTTP_" + response.statusCode());
            JsonNode result = mapper.readTree(response.body());
            if (!"COMPLETED".equals(result.path("status").asText())) throw new IllegalStateException("SCAN_INCOMPLETE");
            Map<String, JsonNode> byImage = new HashMap<>();
            result.path("images").forEach(image -> byImage.put(image.path("imageId").asText(), image));
            Instant now = Instant.now();
            for (PropertyImageScan row : rows) {
                JsonNode value = byImage.get(row.propertyImageId);
                if (value == null) throw new IllegalStateException("SCAN_RESULT_MISSING");
                String classification = value.path("classification").asText("NONE");
                JsonNode matches = value.path("matches");
                JsonNode intra = value.path("intraMatches");
                JsonNode best = intra.size() > 0 && "INTRA_DUPLICATE".equals(classification)
                    ? intra.get(0) : matches.size() > 0 ? matches.get(0) : intra.size() > 0 ? intra.get(0) : null;
                row.scanStatus = "COMPLETED";
                row.classification = classification;
                row.similarity = value.path("similarity").isNumber() ? value.path("similarity").decimalValue() : null;
                row.detectionMethod = value.path("method").isTextual() ? value.path("method").asText() : null;
                row.matchedPropertyId = best == null ? null : best.path("propertyId").asText(null);
                row.matchedPropertyImageId = best == null ? null : best.path("imageId").asText(null);
                row.matchedListingCode = best == null ? null : best.path("listingCode").asText(null);
                if (value instanceof ObjectNode stored) {
                    for (JsonNode intraMatch : stored.path("intraMatches")) {
                        if (intraMatch instanceof ObjectNode match && match.path("imageUrl").asText("").isEmpty()) {
                            match.put("imageUrl", "/api/v1/properties/" + propertyId + "/images/"
                                + match.path("imageId").asText() + "/content");
                        }
                    }
                }
                row.evidence = value;
                row.errorCode = null;
                row.scannedAt = now;
            }
            scans.saveAll(rows);
        } catch (Exception error) {
            if (!rows.isEmpty()) fail(rows, error.getMessage() == null ? "SCAN_FAILED" : error.getMessage());
        }
    }

    public ImageScanDtos.ScanView view(String propertyId) {
        List<PropertyImage> current = images.findByPropertyIdAndDeletedAtIsNullOrderBySortOrderAscIdAsc(propertyId);
        Set<String> currentImageIds = current.stream().map(image -> image.id).collect(java.util.stream.Collectors.toSet());
        Map<String, PropertyImageScan> byImage = new HashMap<>();
        scans.findByPropertyIdOrderByCreatedAtAsc(propertyId).forEach(row -> byImage.put(row.propertyImageId, row));
        List<ImageScanDtos.ImageResult> results = new ArrayList<>();
        for (PropertyImage image : current) {
            PropertyImageScan row = byImage.get(image.id);
            if (row == null) {
                results.add(new ImageScanDtos.ImageResult(image.id, "PENDING", null, null, null, null, List.of(), List.of()));
                continue;
            }
            List<ImageScanDtos.Evidence> matches = evidence(row.evidence, "matches");
            List<ImageScanDtos.Evidence> intra = evidence(row.evidence, "intraMatches").stream()
                .filter(item -> currentImageIds.contains(item.imageId())).toList();
            String classification = matches.isEmpty() && intra.isEmpty() ? "NONE" : row.classification;
            results.add(new ImageScanDtos.ImageResult(image.id, row.scanStatus, classification,
                row.similarity, row.detectionMethod, row.errorCode, matches, intra));
        }
        String status = results.isEmpty() ? "NO_IMAGES"
            : results.stream().anyMatch(item -> "SCANNING".equals(item.status()) || "PENDING".equals(item.status())) ? "SCANNING"
            : results.stream().anyMatch(item -> "PENDING_RETRY".equals(item.status()) || "FAILED".equals(item.status())) ? "FAILED"
            : results.stream().anyMatch(item -> item.classification() != null && !"NONE".equals(item.classification())) ? "MATCHES"
            : "CLEAN";
        Instant scannedAt = results.stream().map(item -> byImage.get(item.imageId()))
            .filter(Objects::nonNull).map(row -> row.scannedAt).filter(Objects::nonNull)
            .max(Comparator.naturalOrder()).orElse(null);
        String error = results.stream().map(ImageScanDtos.ImageResult::errorCode).filter(Objects::nonNull).findFirst().orElse(null);
        return new ImageScanDtos.ScanView(propertyId, status, scannedAt, ALGORITHM_VERSION, error, results,
            List.of("Chỉ so khớp ảnh nội bộ SmartProp; không phải kết luận ảnh bị đánh cắp.",
                    "Không có reverse image search Internet.",
                    "Không tự động từ chối hoặc công khai tin chỉ dựa trên điểm tương đồng."));
    }

    private List<ImageScanDtos.Evidence> evidence(JsonNode row, String field) {
        if (row == null || !row.path(field).isArray()) return List.of();
        List<ImageScanDtos.Evidence> result = new ArrayList<>();
        for (JsonNode item : row.path(field)) {
            result.add(new ImageScanDtos.Evidence(
                item.path("propertyId").asText(null), item.path("listingCode").asText(null),
                item.path("title").asText(null), item.path("imageId").asText(null),
                item.path("imageUrl").asText(null), item.path("listingUrl").asText(null),
                item.path("similarity").isNumber() ? item.path("similarity").decimalValue() : null,
                item.path("classification").asText(null), item.path("method").asText(null),
                mapper.convertValue(item.path("evidence"), Map.class)));
        }
        return result;
    }

    public List<ImageScanDtos.AdminItem> adminList() {
        List<PropertyImageScan> rows = scans.findByScanStatusInAndClassificationIn(
            List.of("COMPLETED"), List.of("EXACT_DUPLICATE", "NEAR_DUPLICATE", "SIMILAR", "INTRA_DUPLICATE"));
        Map<String, Property> propertiesById = new HashMap<>();
        properties.findAllById(rows.stream().map(row -> row.propertyId).distinct().toList())
            .forEach(property -> propertiesById.put(property.id, property));
        Set<String> liveImages = images.findByPropertyIdInAndDeletedAtIsNullOrderBySortOrderAscIdAsc(
            rows.stream().map(row -> row.propertyId).distinct().toList())
            .stream().map(image -> image.id).collect(java.util.stream.Collectors.toSet());
        return rows.stream().filter(row -> liveImages.contains(row.propertyImageId)).map(row -> {
            Property property = propertiesById.get(row.propertyId);
            return new ImageScanDtos.AdminItem(row.propertyId, row.propertyImageId,
                property == null ? null : property.getListingCode(), property == null ? null : property.title,
                row.scanStatus, row.classification, row.similarity, row.matchedPropertyId,
                row.matchedListingCode, row.detectionMethod, row.scannedAt, row.errorCode);
        }).toList();
    }
}
