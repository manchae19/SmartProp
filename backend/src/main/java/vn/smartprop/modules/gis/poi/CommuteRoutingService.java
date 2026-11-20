package vn.smartprop.modules.gis.poi;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import vn.smartprop.common.ApiException;
import vn.smartprop.common.RequestLimits;

/**
 * Computes the trip to work, with the routing vendor chosen by configuration.
 *
 * <p>Two vendors are supported and only one is addressed per request:
 * <ul>
 *   <li>{@code openrouteservice} (HeiGIT) — one Matrix call ranks every candidate,
 *       one Directions call draws a single route.</li>
 *   <li>{@code geoapify} — the previous behaviour, one Directions call per pair.</li>
 * </ul>
 *
 * <p>The API key is read here, sent as a request header, and never logged, echoed in a
 * response, or placed in a URL.
 */
@Service
public class CommuteRoutingService {
    private static final Logger log = LoggerFactory.getLogger(CommuteRoutingService.class);
    public static final String OPENROUTESERVICE = "OPENROUTESERVICE";
    public static final String GEOAPIFY = "GEOAPIFY";
    static final int MAX_BYTES = 1_048_576;
    private static final Duration TIMEOUT = Duration.ofSeconds(12);

    /** One measured trip. {@code geometry} is null when only a summary was requested. */
    public record Measured(double distanceMeters, double durationSeconds, JsonNode geometry, String provider) {}
    /**
     * Wall-clock budget for one Geoapify matrix batch. RAG abandons the call after ten
     * seconds, so measuring must finish inside that window and return partial results.
     */
    static final long GEOAPIFY_MATRIX_BUDGET_SECONDS = 8;
    /** One cell of a matrix result; a missing cell means the vendor had no route. */
    public record Cell(String propertyId, Double distanceMeters, Double durationSeconds, boolean measured) {
        public Cell(String propertyId, Double distanceMeters, Double durationSeconds) {
            this(propertyId, distanceMeters, durationSeconds, true);
        }
    }
    public record Origin(String propertyId, double latitude, double longitude) {}

    private final ObjectMapper json;
    private final String configured;
    private final String orsKey;
    private final String orsBase;
    private final GeoapifyPlacesClient geoapify;
    private final HttpClient client;

    @org.springframework.beans.factory.annotation.Autowired
    public CommuteRoutingService(ObjectMapper json,
        @Value("${app.routing.provider:GEOAPIFY}") String configured,
        @Value("${app.routing.openrouteservice-key:}") String orsKey,
        @Value("${app.routing.openrouteservice-url:https://api.heigit.org/openrouteservice}") String orsBase,
        GeoapifyPlacesClient geoapify) {
        this(json, configured, orsKey, orsBase, geoapify,
            HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3))
                .followRedirects(HttpClient.Redirect.NEVER).build());
    }
    CommuteRoutingService(ObjectMapper json, String configured, String orsKey, String orsBase,
                          GeoapifyPlacesClient geoapify, HttpClient client) {
        this.json = json; this.configured = configured; this.orsKey = orsKey;
        // Paths are appended as "/v2/...", so a trailing slash on the base would double it.
        this.orsBase = normaliseBase(orsBase);
        this.geoapify = geoapify; this.client = client;
    }

    /** The hosted API lives under /openrouteservice; the prefix must appear exactly once. */
    static String normaliseBase(String base) {
        String value = base == null ? "" : base.strip();
        if (value.isEmpty()) return "https://api.heigit.org/openrouteservice";
        while (value.endsWith("/")) value = value.substring(0, value.length() - 1);
        return value;
    }

    /** The vendor that will actually serve the next call, or null when none is configured. */
    public String provider() {
        // An explicit OPENROUTESERVICE without a key is a misconfiguration, not a reason to
        // quietly bill Geoapify instead; the caller sees "not configured".
        if (openRouteServiceConfigured()) return orsUsable() ? OPENROUTESERVICE : null;
        return geoapifyUsable() ? GEOAPIFY : null;
    }

    public boolean available() { return provider() != null; }

    private boolean openRouteServiceConfigured() {
        return "OPENROUTESERVICE".equalsIgnoreCase(configured == null ? "" : configured.strip());
    }
    private boolean orsUsable() {
        return orsKey != null && !orsKey.isBlank();
    }
    private boolean geoapifyUsable() {
        return geoapify != null && geoapify.configured();
    }

    /** openrouteservice profile for a UI mode. */
    static String orsProfile(String mode) {
        return "walk".equals(mode) ? "foot-walking" : "driving-car";
    }

    /** A single routed pair with geometry, used by /commute. */
    public Measured directions(double fromLat, double fromLon, double toLat, double toLon, String mode) {
        if (!NearbyService.valid(fromLat, fromLon) || !NearbyService.valid(toLat, toLon)
            || !Set.of("walk", "drive").contains(mode))
            throw new ApiException(400, "VALIDATION_ERROR", "Điểm hoặc phương tiện không hợp lệ.");
        String vendor = provider();
        if (vendor == null)
            throw new ApiException(503, "ROUTE_NOT_CONFIGURED", "Dịch vụ tính tuyến chưa được cấu hình.");
        return OPENROUTESERVICE.equals(vendor)
            ? orsDirections(fromLat, fromLon, toLat, toLon, mode)
            : geoapifyDirections(fromLat, fromLon, toLat, toLon, mode,
                System.nanoTime() + java.util.concurrent.TimeUnit.SECONDS.toNanos(GEOAPIFY_MATRIX_BUDGET_SECONDS));
    }

    /**
     * Durations from every origin to one destination in a single vendor call when the
     * vendor supports it, otherwise one call per origin. Result order matches input.
     */
    public List<Cell> matrix(List<Origin> origins, double destLat, double destLon, String mode) {
        return matrix(origins, destLat, destLon, mode,
            System.nanoTime() + java.util.concurrent.TimeUnit.SECONDS.toNanos(GEOAPIFY_MATRIX_BUDGET_SECONDS));
    }

    /**
     * Same batch, with a deadline the caller already started. The caller's clock is the
     * one that matters: time spent waiting for a concurrent batch is time it also waits.
     */
    public List<Cell> matrix(List<Origin> origins, double destLat, double destLon, String mode,
                             long deadline) {
        if (origins == null || origins.isEmpty()) return List.of();
        if (!NearbyService.valid(destLat, destLon) || !Set.of("walk", "drive").contains(mode))
            throw new ApiException(400, "VALIDATION_ERROR", "Điểm hoặc phương tiện không hợp lệ.");
        for (Origin origin : origins)
            if (!NearbyService.valid(origin.latitude(), origin.longitude()))
                throw new ApiException(400, "VALIDATION_ERROR", "Điểm xuất phát không hợp lệ.");
        String vendor = provider();
        if (vendor == null)
            throw new ApiException(503, "ROUTE_NOT_CONFIGURED", "Dịch vụ tính tuyến chưa được cấu hình.");
        return OPENROUTESERVICE.equals(vendor)
            ? orsMatrix(origins, destLat, destLon, mode)
            : geoapifyMatrix(origins, destLat, destLon, mode, deadline);
    }

    // ---------------------------------------------------------------- openrouteservice

    private List<Cell> orsMatrix(List<Origin> origins, double destLat, double destLon, String mode) {
        List<List<Double>> locations = new ArrayList<>();
        for (Origin origin : origins) locations.add(List.of(origin.longitude(), origin.latitude()));
        locations.add(List.of(destLon, destLat));
        int destinationIndex = locations.size() - 1;
        List<String> sources = new ArrayList<>();
        for (int i = 0; i < destinationIndex; i++) sources.add(String.valueOf(i));
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("locations", locations);
        body.put("sources", sources);
        body.put("destinations", List.of(String.valueOf(destinationIndex)));
        body.put("metrics", List.of("distance", "duration"));
        JsonNode payload = orsPost("/v2/matrix/" + orsProfile(mode), body);
        JsonNode durations = payload.path("durations");
        JsonNode distances = payload.path("distances");
        List<Cell> cells = new ArrayList<>();
        for (int i = 0; i < origins.size(); i++) {
            Double seconds = cellValue(durations, i);
            Double meters = cellValue(distances, i);
            cells.add(new Cell(origins.get(i).propertyId(), meters, seconds));
        }
        return cells;
    }

    /** A cell can be a number or null when no route exists; null stays null, never zero. */
    private static Double cellValue(JsonNode matrix, int row) {
        if (!matrix.isArray() || row >= matrix.size()) return null;
        JsonNode line = matrix.get(row);
        if (!line.isArray() || line.isEmpty()) return null;
        JsonNode value = line.get(0);
        if (value == null || !value.isNumber()) return null;
        double number = value.asDouble();
        return Double.isFinite(number) && number >= 0 ? number : null;
    }

    private Measured orsDirections(double fromLat, double fromLon, double toLat, double toLon, String mode) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("coordinates", List.of(List.of(fromLon, fromLat), List.of(toLon, toLat)));
        JsonNode payload = orsPost("/v2/directions/" + orsProfile(mode) + "/geojson", body);
        JsonNode feature = payload.path("features").path(0);
        JsonNode summary = feature.path("properties").path("summary");
        double meters = summary.path("distance").asDouble(Double.NaN);
        double seconds = summary.path("duration").asDouble(Double.NaN);
        JsonNode geometry = feature.path("geometry");
        if (!Double.isFinite(meters) || !Double.isFinite(seconds)
            || meters < 0 || seconds < 0 || !geometry.path("coordinates").isArray())
            throw unavailable();
        return new Measured(meters, seconds, geometry.deepCopy(), OPENROUTESERVICE);
    }

    private JsonNode orsPost(String path, Map<String, Object> body) {
        HttpRequest request;
        try {
            request = HttpRequest.newBuilder(URI.create(orsBase + path)).timeout(TIMEOUT)
                .header("Authorization", orsKey)
                .header("Content-Type", "application/json; charset=utf-8")
                .header("Accept", "application/geo+json, application/json")
                .POST(HttpRequest.BodyPublishers.ofString(
                    json.writeValueAsString(body), StandardCharsets.UTF_8))
                .build();
        } catch (Exception e) {
            throw unavailable();
        }
        HttpResponse<byte[]> response;
        try {
            response = client.send(request, HttpResponse.BodyHandlers.ofByteArray());
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new ApiException(503, "ROUTE_INTERRUPTED", "Yêu cầu tính tuyến đã bị gián đoạn.");
        } catch (Exception e) {
            throw unavailable();
        }
        int code = response.statusCode();
        if (code == 401 || code == 403)
            throw new ApiException(503, "ROUTE_PROVIDER_AUTH", "Cấu hình truy cập dịch vụ tính tuyến chưa hợp lệ.");
        if (code == 429) {
            long retry = retryAfterSeconds(response);
            throw new ApiException(429, "ROUTE_PROVIDER_RATE_LIMITED",
                "Dịch vụ tính tuyến đang giới hạn truy cập. Vui lòng thử lại sau.");
        }
        if (code != 200)
            throw unavailable();
        byte[] bytes = response.body();
        if (bytes == null || bytes.length == 0 || bytes.length > MAX_BYTES)
            throw unavailable();
        try {
            JsonNode parsed = json.readTree(bytes);
            if (parsed == null || !parsed.isObject()) throw unavailable();
            return parsed;
        } catch (java.io.IOException e) {
            throw unavailable();
        }
    }

    private static long retryAfterSeconds(HttpResponse<?> response) {
        return response.headers().firstValue("Retry-After").map(value -> {
            try { return Math.max(1, Long.parseLong(value.strip())); } catch (NumberFormatException ignored) { return 60L; }
        }).orElse(60L);
    }

    // ---------------------------------------------------------------------- geoapify

    private List<Cell> geoapifyMatrix(List<Origin> origins, double destLat, double destLon, String mode,
                                      long deadline) {
        List<Cell> cells = new ArrayList<>();
        for (Origin origin : origins) {
            Measured measured = null;
            // Three outcomes must stay distinct: a route, a vendor-confirmed absence of a
            // route, and a listing the batch never reached because the budget ran out.
            boolean noRoute = false;
            // The shared egress bucket allows one provider call per second, so a batch of
            // pairs must be paced. Without this the second listing always trips our own
            // limiter and the whole matrix is reported as rate limited.
            for (int attempt = 0; attempt < 3 && measured == null; attempt++) {
                if (System.nanoTime() > deadline) break;
                try {
                    measured = geoapifyDirections(origin.latitude(), origin.longitude(), destLat, destLon, mode, deadline);
                } catch (ApiException error) {
                    if (isEgressThrottle(error)) {
                        // Only the one-second egress window clears by itself. The daily quota
                        // and the per-IP endpoint cap cannot, so the batch stops and the caller
                        // reports the limit instead of sleeping through it.
                        if (attempt == 2) throw error;
                        // Waiting must fit in what is left, otherwise the retry itself would
                        // push the batch past the caller's window.
                        if (System.nanoTime() + java.util.concurrent.TimeUnit.MILLISECONDS.toNanos(1100L) > deadline) break;
                        try {
                            Thread.sleep(1100L);
                        } catch (InterruptedException interrupted) {
                            Thread.currentThread().interrupt();
                            throw new ApiException(503, "ROUTE_INTERRUPTED", "Yêu cầu tính tuyến đã bị gián đoạn.");
                        }
                    } else if (isRateLimited(error)) {
                        // A limit we cannot wait out, or one we cannot attribute.
                        throw error;
                    } else {
                        // The vendor answered and has no route for this listing.
                        noRoute = true;
                        break;
                    }
                }
            }
            if (measured != null) {
                cells.add(new Cell(origin.propertyId(), measured.distanceMeters(), measured.durationSeconds()));
            } else if (noRoute) {
                cells.add(new Cell(origin.propertyId(), null, null, true));
            } else {
                // Never reached: the budget ran out. Reported as unmeasured, not as absent.
                cells.add(new Cell(origin.propertyId(), null, null, false));
            }
        }
        return cells;
    }

    /** True when the failure is our own budget or the provider throttling us. */
    private static boolean isRateLimited(ApiException error) {
        return "RATE_LIMITED".equals(error.code) || 429 == error.status;
    }

    /**
     * True only for the one-second egress bucket, which clears on its own.
     *
     * The decision uses the counter that refused, not Retry-After: that header is the time
     * left in the current window, so the daily quota also reports 1 second just before its
     * window rolls over. An unattributed 429 is never retried.
     */
    static boolean isEgressThrottle(ApiException error) {
        return isRateLimited(error)
            && error instanceof RequestLimits.Exceeded limited
            && "geo:egress".equals(limited.bucket);
    }

    /**
     * Delegates to the existing provider client so the shared egress/daily budget keeps
     * applying exactly as before this change.
     */
    private Measured geoapifyDirections(double fromLat, double fromLon, double toLat, double toLon, String mode,
                                        long deadline) {
        if (!geoapifyUsable())
            throw new ApiException(503, "ROUTE_NOT_CONFIGURED", "Dịch vụ tính tuyến chưa được cấu hình.");
        JsonNode body = geoapify.route(fromLat, fromLon, toLat, toLon, mode, deadline);
        JsonNode feature = body.path("features").path(0);
        JsonNode properties = feature.path("properties");
        double meters = properties.path("distance").asDouble(Double.NaN);
        double seconds = properties.path("time").asDouble(Double.NaN);
        JsonNode geometry = feature.path("geometry");
        if (!Double.isFinite(meters) || !Double.isFinite(seconds)
            || meters < 0 || seconds < 0 || !geometry.path("coordinates").isArray())
            throw unavailable();
        return new Measured(meters, seconds, geometry.deepCopy(), GEOAPIFY);
    }

    private static ApiException unavailable() {
        return new ApiException(502, "ROUTE_UNAVAILABLE",
            "Chưa tìm được tuyến đường phù hợp. Không thay bằng đường thẳng.");
    }
}
