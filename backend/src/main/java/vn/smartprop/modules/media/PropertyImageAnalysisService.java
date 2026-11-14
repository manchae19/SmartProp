package vn.smartprop.modules.media;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import vn.smartprop.modules.property.Property;
import vn.smartprop.modules.property.PropertyRepository;

import java.math.BigDecimal;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Automatic YOLOv8 object analysis for property images.
 *
 * <p>Runs beside {@link PropertyImageScanService}, never instead of it. The two
 * share no state, no executor and no failure mode: a vision outage must not
 * mark a duplicate scan clean, and a duplicate failure must not block analysis.
 *
 * <p>Safety rules carried over from the duplicate scanner because they are what
 * made it trustworthy:
 * <ol>
 *   <li>A failed call writes {@code PENDING_RETRY} plus an error code. It never
 *       writes {@code detectionCount = 0}, which would read as "nothing here".</li>
 *   <li>Re-analysis is skipped only when the stored row is genuinely fresh for
 *       the current image bytes and model version.</li>
 *   <li>Nothing is inferred beyond what the model reported. No bedroom count,
 *       no area, no condition, no legal status.</li>
 * </ol>
 */
@Service
public class PropertyImageAnalysisService {
    private static final Logger log = LoggerFactory.getLogger(PropertyImageAnalysisService.class);

    static final String ALGORITHM_VERSION = "yolov8n-property-v1";
    private static final int MAX_IMAGES = 30;
    private static final String STATUS_PENDING = "PENDING";
    private static final String STATUS_SCANNING = "SCANNING";
    private static final String STATUS_COMPLETED = "COMPLETED";
    private static final String STATUS_RETRY = "PENDING_RETRY";
    private static final String STATUS_FAILED = "FAILED";
    /** Bounds automatic retries so a permanently broken image cannot loop forever. */
    private static final int MAX_ATTEMPTS = 3;

    private final PropertyImageRepository images;
    private final PropertyImageAnalysisRepository analyses;
    private final PropertyRepository properties;
    private final LocalFileStore files;
    private final CloudinaryImageDelivery cloudinary;
    private final ObjectMapper mapper;
    private final URI visionBase;
    private final HttpClient http;
    private final boolean enabled;
    private final Set<String> inFlight = ConcurrentHashMap.newKeySet();

    public PropertyImageAnalysisService(
            PropertyImageRepository images,
            PropertyImageAnalysisRepository analyses,
            PropertyRepository properties,
            LocalFileStore files,
            CloudinaryImageDelivery cloudinary,
            ObjectMapper mapper,
            @Value("${app.image-analysis.base-url:http://127.0.0.1:18002}") String visionBase,
            @Value("${app.image-analysis.enabled:false}") boolean enabled) {
        this.images = images;
        this.analyses = analyses;
        this.properties = properties;
        this.files = files;
        this.cloudinary = cloudinary;
        this.mapper = mapper;
        this.visionBase = validateBase(visionBase);
        this.enabled = enabled;
        this.http = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(3))
            .followRedirects(HttpClient.Redirect.NEVER)
            .build();
    }

    /** Only a loopback HTTP origin is accepted; the vision service is never remote. */
    private static URI validateBase(String value) {
        try {
            URI uri = URI.create(value);
            if (!"http".equals(uri.getScheme())
                || !Set.of("127.0.0.1", "localhost").contains(uri.getHost())
                || uri.getPort() < 1
                || uri.getUserInfo() != null
                || uri.getQuery() != null
                || uri.getFragment() != null) {
                throw new IllegalArgumentException();
            }
            return uri;
        } catch (Exception e) {
            throw new IllegalArgumentException("Invalid image analysis base URL", e);
        }
    }

    public boolean enabled() {
        return enabled;
    }

    /**
     * Queue analysis for every image of a listing.
     *
     * <p>Never throws: a caller in the upload path must not fail because the
     * vision service is down.
     */
    @Async("imageAnalysisExecutor")
    public void schedule(String propertyId) {
        if (!enabled) return;
        // V22 may not be applied yet (MySQL 3306 today). Without the table there
        // is nowhere to persist a result, so stay silent rather than fail.
        if (!analyses.tablePresent()) return;
        if (!inFlight.add(propertyId)) return;
        try {
            analyze(propertyId);
        } catch (Exception error) {
            // analyze() already persisted a visible failure state.
            log.debug("Image analysis failed for property {}: {}", propertyId, error.getClass().getSimpleName());
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

    private void analyze(String propertyId) {
        List<PropertyImage> current = images.findByPropertyIdAndDeletedAtIsNullOrderBySortOrderAscIdAsc(propertyId);
        if (current.isEmpty() || current.size() > MAX_IMAGES) return;

        Map<String, PropertyImageAnalysis> existing = new HashMap<>();
        analyses.findByPropertyId(propertyId)
            .forEach(row -> existing.put(row.propertyImageId, row));

        List<PropertyImageAnalysis> rows = new ArrayList<>();
        for (PropertyImage image : current) {
            PropertyImageAnalysis row = existing.get(image.id);
            // Fresh means: completed, same algorithm, and analysed after the
            // image bytes last changed. Anything else is re-analysed.
            boolean fresh = row != null
                && STATUS_COMPLETED.equals(row.analysisStatus)
                && row.analyzedAt != null
                && !row.analyzedAt.isBefore(image.updatedAt)
                && ALGORITHM_VERSION.equals(row.algorithmVersion);
            if (fresh) continue;

            // A failed row is only re-queued once its backoff has elapsed and it
            // still has attempts left. Otherwise it stays visible as FAILED.
            if (row != null && (STATUS_RETRY.equals(row.analysisStatus) || STATUS_FAILED.equals(row.analysisStatus))) {
                if (!retryDue(row)) continue;
            }

            if (row == null) {
                row = new PropertyImageAnalysis();
                row.id = UUID.randomUUID().toString();
                row.propertyId = propertyId;
                row.propertyImageId = image.id;
                row.detections = mapper.createArrayNode();
                row.countsByLabel = mapper.createObjectNode();
                // model_version is NOT NULL: a row exists before the model has
                // answered, so it carries an explicit placeholder rather than a
                // null that would fail the insert.
                row.modelVersion = "pending";
                row.createdAt = Instant.now();
            }
            row.analysisStatus = STATUS_SCANNING;
            row.algorithmVersion = ALGORITHM_VERSION;
            row.errorCode = null;
            rows.add(row);
        }
        if (rows.isEmpty()) return;

        // Persist SCANNING first so a crash leaves a visible, recoverable state.
        analyses.saveAll(rows);

        for (PropertyImageAnalysis row : rows) {
            PropertyImage image = current.stream()
                .filter(item -> item.id.equals(row.propertyImageId))
                .findFirst().orElse(null);
            if (image == null) {
                fail(row, "IMAGE_MISSING");
                continue;
            }
            try {
                byte[] bytes = read(image);
                if (bytes == null || bytes.length == 0) {
                    fail(row, "IMAGE_READ_FAILED");
                    continue;
                }
                apply(row, callVision(bytes, image.mimeType));
            } catch (Exception error) {
                fail(row, error.getMessage() == null ? "ANALYSIS_FAILED" : error.getMessage());
            }
        }
        analyses.saveAll(rows);
    }

    /** POST the raw bytes; the vision service never receives a URL. */
    private JsonNode callVision(byte[] bytes, String mimeType) throws Exception {
        String contentType = mimeType == null || mimeType.isBlank() ? "image/jpeg" : mimeType;
        HttpRequest request = HttpRequest.newBuilder(visionBase.resolve("/image-analysis/analyze"))
            .timeout(Duration.ofSeconds(30))
            .header("Content-Type", contentType)
            .POST(HttpRequest.BodyPublishers.ofByteArray(bytes))
            .build();
        HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());
        if (response.statusCode() != 200) {
            throw new IllegalStateException("VISION_HTTP_" + response.statusCode());
        }
        JsonNode result = mapper.readTree(response.body());
        if (!"COMPLETED".equals(result.path("status").asText())) {
            throw new IllegalStateException("VISION_INCOMPLETE");
        }
        return result;
    }

    private void apply(PropertyImageAnalysis row, JsonNode result) {
        row.analysisStatus = STATUS_COMPLETED;
        row.modelVersion = result.path("modelVersion").asText("unknown");
        row.detectionCount = result.path("detectionCount").asInt(0);
        row.detections = result.path("detections").isArray() ? result.path("detections") : mapper.createArrayNode();
        row.countsByLabel = result.path("countsByLabel").isObject() ? result.path("countsByLabel") : mapper.createObjectNode();
        row.documentLike = result.path("documentHint").path("likelyDocument").asBoolean(false);
        row.documentHint = result.path("documentHint").isObject() ? result.path("documentHint") : null;
        row.imageWidth = result.path("image").path("width").isNumber() ? result.path("image").path("width").asInt() : null;
        row.imageHeight = result.path("image").path("height").isNumber() ? result.path("image").path("height").asInt() : null;
        row.imageFormat = result.path("image").path("format").asText(null);
        row.imageSha256 = result.path("image").path("sha256").asText(null);
        row.inferenceMs = result.path("timing").path("inferenceMs").isNumber()
            ? BigDecimal.valueOf(result.path("timing").path("inferenceMs").asDouble())
            : null;
        row.errorCode = null;
        row.analyzedAt = Instant.now();
    }

    /**
     * Record a failure without ever implying a clean result.
     *
     * <p>Clearing the detections is intentional: a stale detection list shown
     * next to a failed status would be worse than showing nothing.
     *
     * <p>Retries are bounded: after {@link #MAX_ATTEMPTS} the row becomes
     * {@code FAILED} and only a manual retry can move it again. Without this a
     * permanently broken image (dead Cloudinary URL, unsupported format) would
     * be re-queued forever.
     */
    private void fail(PropertyImageAnalysis row, String error) {
        row.attemptCount += 1;
        row.analysisStatus = row.attemptCount >= MAX_ATTEMPTS ? STATUS_FAILED : STATUS_RETRY;
        row.errorCode = error;
        row.detectionCount = 0;
        row.detections = mapper.createArrayNode();
        row.countsByLabel = mapper.createObjectNode();
        row.documentLike = false;
        row.documentHint = null;
        row.analyzedAt = Instant.now();
    }

    /**
     * Whether a failed row may be retried now.
     *
     * <p>Exponential backoff: 30 s, 2 min, 8 min. A rate-limited or briefly
     * offline vision service recovers on its own; a permanently broken image
     * stops after {@link #MAX_ATTEMPTS}.
     */
    private boolean retryDue(PropertyImageAnalysis row) {
        if (row.attemptCount >= MAX_ATTEMPTS) return false;
        if (row.analyzedAt == null) return true;
        long backoffSeconds = 30L * (1L << Math.min(row.attemptCount, 4));
        return Instant.now().isAfter(row.analyzedAt.plusSeconds(backoffSeconds));
    }

    // -- read side ---------------------------------------------------------

    public ImageAnalysisDtos.AnalysisView view(String propertyId) {
        List<PropertyImage> current = images.findByPropertyIdAndDeletedAtIsNullOrderBySortOrderAscIdAsc(propertyId);
        // V22 not applied: report the feature as unavailable rather than
        // pretending every image is still queued. Nothing is persisted, so
        // "ANALYZING" would be a lie that never resolves.
        if (!analyses.tablePresent()) {
            return new ImageAnalysisDtos.AnalysisView(
                propertyId, "UNAVAILABLE", null, ALGORITHM_VERSION, null, "SCHEMA_NOT_READY",
                List.of(), limitations());
        }
        Set<String> liveIds = current.stream().map(image -> image.id).collect(java.util.stream.Collectors.toSet());
        Map<String, PropertyImageAnalysis> byImage = new HashMap<>();
        analyses.findByPropertyId(propertyId)
            .forEach(row -> byImage.put(row.propertyImageId, row));

        List<ImageAnalysisDtos.ImageResult> results = new ArrayList<>();
        for (PropertyImage image : current) {
            PropertyImageAnalysis row = byImage.get(image.id);
            if (row == null) {
                results.add(new ImageAnalysisDtos.ImageResult(
                    image.id, STATUS_PENDING, null, ALGORITHM_VERSION, 0,
                    Map.of(), List.of(), null, null, null, null));
                continue;
            }
            results.add(new ImageAnalysisDtos.ImageResult(
                image.id,
                row.analysisStatus,
                row.modelVersion,
                row.algorithmVersion,
                row.detectionCount,
                toCounts(row.countsByLabel),
                toDetections(row.detections),
                toHint(row),
                row.inferenceMs,
                row.analyzedAt,
                row.errorCode));
        }

        String status = results.isEmpty() ? "NO_IMAGES"
            : results.stream().anyMatch(item -> STATUS_SCANNING.equals(item.status()) || STATUS_PENDING.equals(item.status())) ? "ANALYZING"
            : results.stream().anyMatch(item -> STATUS_RETRY.equals(item.status()) || "FAILED".equals(item.status())) ? "FAILED"
            : results.stream().anyMatch(item -> item.detectionCount() > 0) ? "HAS_OBJECTS"
            : "NO_OBJECTS";

        Instant analyzedAt = results.stream()
            .map(ImageAnalysisDtos.ImageResult::analyzedAt)
            .filter(Objects::nonNull)
            .max(Comparator.naturalOrder())
            .orElse(null);
        String error = results.stream()
            .map(ImageAnalysisDtos.ImageResult::errorCode)
            .filter(Objects::nonNull)
            .findFirst().orElse(null);
        String modelVersion = results.stream()
            .map(ImageAnalysisDtos.ImageResult::modelVersion)
            .filter(Objects::nonNull)
            .findFirst().orElse(null);

        return new ImageAnalysisDtos.AnalysisView(
            propertyId, status, analyzedAt, ALGORITHM_VERSION, modelVersion, error, results, limitations());
    }

    public List<ImageAnalysisDtos.AdminItem> adminList() {
        // The repository already restricts to COMPLETED rows with findings.
        List<PropertyImageAnalysis> rows = analyses.findCompletedWithFindings();
        if (rows.isEmpty()) return List.of();

        Map<String, Property> byId = new HashMap<>();
        properties.findAllById(rows.stream().map(row -> row.propertyId).distinct().toList())
            .forEach(property -> byId.put(property.id, property));
        Set<String> liveImages = images.findByPropertyIdInAndDeletedAtIsNullOrderBySortOrderAscIdAsc(
                rows.stream().map(row -> row.propertyId).distinct().toList())
            .stream().map(image -> image.id).collect(java.util.stream.Collectors.toSet());

        return rows.stream()
            .filter(row -> liveImages.contains(row.propertyImageId))
            .map(row -> {
                Property property = byId.get(row.propertyId);
                return new ImageAnalysisDtos.AdminItem(
                    row.propertyId,
                    row.propertyImageId,
                    property == null ? null : property.getListingCode(),
                    property == null ? null : property.title,
                    row.analysisStatus,
                    row.detectionCount,
                    toCounts(row.countsByLabel),
                    row.documentLike,
                    row.modelVersion,
                    row.analyzedAt,
                    row.errorCode);
            })
            .toList();
    }

    private Map<String, Integer> toCounts(JsonNode node) {
        if (node == null || !node.isObject()) return Map.of();
        Map<String, Integer> counts = new LinkedHashMap<>();
        node.fields().forEachRemaining(entry -> counts.put(entry.getKey(), entry.getValue().asInt()));
        return counts;
    }

    private List<ImageAnalysisDtos.Detection> toDetections(JsonNode node) {
        if (node == null || !node.isArray()) return List.of();
        List<ImageAnalysisDtos.Detection> result = new ArrayList<>();
        for (JsonNode item : node) {
            List<BigDecimal> box = new ArrayList<>();
            item.path("box").forEach(value -> box.add(BigDecimal.valueOf(value.asDouble())));
            List<Integer> pixels = new ArrayList<>();
            item.path("boxPixels").forEach(value -> pixels.add(value.asInt()));
            result.add(new ImageAnalysisDtos.Detection(
                item.path("cocoId").asInt(),
                item.path("cocoName").asText(null),
                item.path("label").asText(null),
                item.path("group").asText(null),
                item.path("confidence").isNumber() ? BigDecimal.valueOf(item.path("confidence").asDouble()) : null,
                box,
                pixels));
        }
        return result;
    }

    private ImageAnalysisDtos.DocumentHint toHint(PropertyImageAnalysis row) {
        JsonNode hint = row.documentHint;
        if (hint == null || !hint.isObject()) {
            // Older rows only carry the boolean; expose the minimal projection.
            return new ImageAnalysisDtos.DocumentHint(
                row.documentLike, null, null, null,
                row.documentLike ? "DOCUMENT_LIKE" : "PHOTOGRAPH_LIKE");
        }
        return new ImageAnalysisDtos.DocumentHint(
            hint.path("likelyDocument").asBoolean(false),
            hint.path("brightFraction").isNumber() ? BigDecimal.valueOf(hint.path("brightFraction").asDouble()) : null,
            hint.path("lowSaturationFraction").isNumber() ? BigDecimal.valueOf(hint.path("lowSaturationFraction").asDouble()) : null,
            hint.path("contrast").isNumber() ? BigDecimal.valueOf(hint.path("contrast").asDouble()) : null,
            hint.path("reason").asText(null));
    }

    static List<String> limitations() {
        return List.of(
            "Chỉ nhận diện các lớp COCO có trong danh sách hỗ trợ; vật dụng khác không được báo cáo.",
            "Đây là nhận diện đối tượng, không phải xác nhận nội thất, chất lượng hay pháp lý của bất động sản.",
            "Không suy ra số phòng ngủ, diện tích hay tình trạng căn nhà từ số đồ vật phát hiện.",
            "Ảnh giấy tờ có thể sinh nhận diện sai; kết quả chỉ mang tính tham khảo.");
    }
}
