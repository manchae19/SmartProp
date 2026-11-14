package vn.smartprop.gis;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.locationtech.jts.geom.Coordinate;
import org.locationtech.jts.geom.Geometry;
import org.locationtech.jts.geom.GeometryFactory;
import org.locationtech.jts.geom.LinearRing;
import org.locationtech.jts.geom.Point;
import org.locationtech.jts.geom.Polygon;
import org.locationtech.jts.geom.PrecisionModel;
import org.springframework.stereotype.Component;
import vn.smartprop.gis.GisDtos.CoordinateStatus;
import vn.smartprop.gis.GisDtos.CoordinateValidationResult;

/**
 * Spatial Coordinate & Polygon Validator for Da Nang (Step 21.4B).
 *
 * <p>Reuses the bundled {@code /geocoding/danang-search-scopes.geojson}
 * ({@code OCHA-2020-geoBoundaries-9469f09}, CC BY 3.0 IGO) JTS polygons to verify:
 * <ul>
 *   <li>Finite WGS84 bounds, rejecting {@code NaN}, {@code Infinity}, and {@code (0, 0)}.</li>
 *   <li>Swapped latitude/longitude axes (e.g. {@code lat=108.22, lon=16.06}).</li>
 *   <li>Containment within Da Nang's 7 historical mainland district polygons, with a documented
 *       {@code 750 m} ADM2 vector-simplification buffer along river/road borders.</li>
 *   <li>Detection of misplaced default-viewport pins (e.g. declared {@code Liên Chiểu} but pinned
 *       {@code > 750 m} away in {@code Hải Châu}), preventing false map pins and false POI distances.</li>
 * </ul>
 */
@Component
public class DanangSpatialValidator {

    /**
     * OCHA 2020 ADM2 polygons are simplified along rivers/corridors by up to ~510m in Da Nang.
     * Any pin > 750m outside its declared district polygon is flagged as a district mismatch.
     */
    public static final double ADM2_BOUNDARY_TOLERANCE_METERS = 750.0;

    private static final double DANANG_MIN_LAT = 15.90;
    private static final double DANANG_MAX_LAT = 16.25;
    private static final double DANANG_MIN_LON = 107.80;
    private static final double DANANG_MAX_LON = 108.40;

    private final GeometryFactory geometryFactory = new GeometryFactory(new PrecisionModel(), 4326);
    private final Map<String, Geometry> coreDistrictPolygons;
    private final Map<String, Geometry> extendedPolygons;
    private final String scopeVersion;

    public DanangSpatialValidator(ObjectMapper mapper) {
        try (InputStream in = DanangSpatialValidator.class.getResourceAsStream("/geocoding/danang-search-scopes.geojson")) {
            if (in == null) {
                throw new IllegalStateException("Missing /geocoding/danang-search-scopes.geojson on classpath");
            }
            JsonNode root = mapper.readTree(in);
            this.scopeVersion = root.path("version").asText("UNKNOWN");
            Map<String, Geometry> core = new LinkedHashMap<>();
            Map<String, Geometry> ext = new LinkedHashMap<>();
            for (JsonNode feature : root.path("features")) {
                String name = feature.path("properties").path("name").asText("").strip();
                Geometry geom = parseGeometry(feature.path("geometry"));
                if (name.isEmpty() || geom.isEmpty() || !geom.isValid()) {
                    throw new IllegalStateException("Invalid geometry in danang-search-scopes.geojson for " + name);
                }
                if (DanangAdminNormalizer.CORE_DISTRICTS.contains(name)) {
                    core.put(name, geom);
                } else {
                    ext.put(name, geom);
                }
            }
            if (core.size() != DanangAdminNormalizer.CORE_DISTRICTS.size()) {
                throw new IllegalStateException("Expected 7 core Da Nang district polygons, found " + core.size());
            }
            this.coreDistrictPolygons = Map.copyOf(core);
            this.extendedPolygons = Map.copyOf(ext);
        } catch (IOException e) {
            throw new IllegalStateException("Failed to load Da Nang spatial polygons", e);
        }
    }

    public String scopeVersion() {
        return scopeVersion;
    }

    /**
     * Validates candidate coordinates without ever mutating or fabricating coordinates.
     *
     * @param latitude          candidate WGS84 latitude (nullable)
     * @param longitude         candidate WGS84 longitude (nullable)
     * @param canonicalDistrict normalized historical Da Nang district (nullable)
     * @param allowPublicPin    true only for published live platform properties
     */
    public CoordinateValidationResult validate(
            Double latitude,
            Double longitude,
            String canonicalDistrict,
            boolean allowPublicPin) {

        if (latitude == null || longitude == null) {
            return new CoordinateValidationResult(
                CoordinateStatus.NONE_ADMIN_ONLY,
                false,
                null,
                null,
                null,
                null,
                "Bản ghi không có tọa độ GPS cấp bất động sản; sử dụng đối chiếu hành chính cấp phường/quận, không tạo tọa độ giả."
            );
        }

        double lat = latitude;
        double lon = longitude;

        if (!Double.isFinite(lat) || !Double.isFinite(lon)) {
            return new CoordinateValidationResult(
                CoordinateStatus.INVALID_COORDINATES,
                false, null, null, null, null,
                "Tọa độ không hợp lệ (NaN/Infinity) — bị loại khỏi bản đồ và tính khoảng cách tiện ích."
            );
        }

        if (Math.abs(lat) < 1e-6 && Math.abs(lon) < 1e-6) {
            return new CoordinateValidationResult(
                CoordinateStatus.INVALID_COORDINATES,
                false, null, null, null, null,
                "Tọa độ (0, 0) mặc định không hợp lệ — không hiển thị ghim và không tính khoảng cách tiện ích."
            );
        }

        // Check swapped axes BEFORE standard [-90, 90] check because lat=108.22 exceeds 90!
        if (lat >= 107.0 && lat <= 109.5 && lon >= 15.0 && lon <= 17.0) {
            return new CoordinateValidationResult(
                CoordinateStatus.INVALID_SWAPPED_AXES,
                false, null, null, null, null,
                "Phát hiện tọa độ bị đảo trục Vĩ độ/Kinh độ (" + lat + ", " + lon + ") — hệ thống từ chối tự ý đảo dữ liệu gốc."
            );
        }

        if (lat < -90.0 || lat > 90.0 || lon <= -180.0 || lon > 180.0) {
            return new CoordinateValidationResult(
                CoordinateStatus.INVALID_COORDINATES,
                false, null, null, null, null,
                "Tọa độ nằm ngoài hệ quy chiếu WGS84 hợp lệ."
            );
        }

        Point pt = geometryFactory.createPoint(new Coordinate(lon, lat));
        String containingCore = findContainingPolygon(pt, coreDistrictPolygons);

        if (lat < DANANG_MIN_LAT || lat > DANANG_MAX_LAT || lon < DANANG_MIN_LON || lon > DANANG_MAX_LON) {
            String extMatch = findContainingPolygon(pt, extendedPolygons);
            String note = extMatch != null
                ? "Tọa độ nằm tại khu vực '" + extMatch + "' (ngoài 7 quận/huyện Đà Nẵng lịch sử)."
                : "Tọa độ (" + round6(lat) + ", " + round6(lon) + ") nằm ngoài khung bao địa lý Đà Nẵng.";
            return new CoordinateValidationResult(
                CoordinateStatus.OUTSIDE_DANANG_BOUNDS,
                false, null, null, extMatch, null,
                note
            );
        }

        if (canonicalDistrict != null && coreDistrictPolygons.containsKey(canonicalDistrict)) {
            Geometry declaredPoly = coreDistrictPolygons.get(canonicalDistrict);
            if (declaredPoly.contains(pt) || declaredPoly.touches(pt)) {
                return new CoordinateValidationResult(
                    CoordinateStatus.VERIFIED_EXACT,
                    allowPublicPin,
                    allowPublicPin ? lat : null,
                    allowPublicPin ? lon : null,
                    canonicalDistrict,
                    0.0,
                    "Tọa độ WGS84 (SRID 4326) nằm khớp trong ranh giới địa lý " + DanangAdminNormalizer.districtDisplayLabel(canonicalDistrict) + "."
                );
            }

            double distMeters = minDistanceToGeometryMeters(lat, lon, declaredPoly);
            if (distMeters <= ADM2_BOUNDARY_TOLERANCE_METERS) {
                return new CoordinateValidationResult(
                    CoordinateStatus.VERIFIED_BOUNDARY_BUFFER,
                    allowPublicPin,
                    allowPublicPin ? lat : null,
                    allowPublicPin ? lon : null,
                    containingCore != null ? containingCore : canonicalDistrict,
                    Math.round(distMeters * 10.0) / 10.0,
                    "Tọa độ nằm sát ranh giới hành chính " + DanangAdminNormalizer.districtDisplayLabel(canonicalDistrict)
                        + " (sai số đường biên giản lược ADM2 ~" + Math.round(distMeters) + " m)."
                );
            }

            String wherePinFell = containingCore != null
                ? "thuộc địa phận " + DanangAdminNormalizer.districtDisplayLabel(containingCore)
                : "nằm ngoài ranh giới đất liền đã kiểm chứng";
            return new CoordinateValidationResult(
                CoordinateStatus.INVALID_DISTRICT_MISMATCH,
                false,
                null,
                null,
                containingCore,
                Math.round(distMeters * 10.0) / 10.0,
                "Tọa độ ghim (" + wherePinFell + ") lệch " + Math.round(distMeters) + " m so với "
                    + DanangAdminNormalizer.districtDisplayLabel(canonicalDistrict)
                    + " đã khai báo — ẩn ghim và không tính khoảng cách tiện ích cấp căn để tránh sai lệch vị trí."
            );
        }

        // No declared district, check if inside any of the 7 Da Nang core district polygons
        if (containingCore != null) {
            return new CoordinateValidationResult(
                CoordinateStatus.VERIFIED_DANANG_POLYGON,
                allowPublicPin,
                allowPublicPin ? lat : null,
                allowPublicPin ? lon : null,
                containingCore,
                0.0,
                "Tọa độ nằm trong ranh giới địa lý " + DanangAdminNormalizer.districtDisplayLabel(containingCore) + ", Đà Nẵng."
            );
        }

        String extMatch = findContainingPolygon(pt, extendedPolygons);
        return new CoordinateValidationResult(
            CoordinateStatus.OUTSIDE_DANANG_BOUNDS,
            false,
            null,
            null,
            extMatch,
            null,
            extMatch != null
                ? "Tọa độ nằm tại '" + extMatch + "', ngoài 7 quận/huyện Đà Nẵng lịch sử."
                : "Tọa độ không nằm trong ranh giới đất liền 7 quận/huyện Đà Nẵng đã kiểm chứng."
        );
    }

    private static String findContainingPolygon(Point pt, Map<String, Geometry> map) {
        for (var entry : map.entrySet()) {
            if (entry.getValue().contains(pt) || entry.getValue().touches(pt)) {
                return entry.getKey();
            }
        }
        return null;
    }

    /**
     * Exact local equirectangular segment-projection distance in meters around ~16°N.
     */
    static double minDistanceToGeometryMeters(double lat, double lon, Geometry geom) {
        double metersPerDegLon = 111_320.0 * Math.cos(Math.toRadians(lat));
        double metersPerDegLat = 110_574.0;
        double best = Double.POSITIVE_INFINITY;
        for (int g = 0; g < geom.getNumGeometries(); g++) {
            Geometry sub = geom.getGeometryN(g);
            if (sub instanceof Polygon poly) {
                best = Math.min(best, minRingDistanceMeters(lat, lon, poly.getExteriorRing().getCoordinates(), metersPerDegLon, metersPerDegLat));
                for (int h = 0; h < poly.getNumInteriorRing(); h++) {
                    best = Math.min(best, minRingDistanceMeters(lat, lon, poly.getInteriorRingN(h).getCoordinates(), metersPerDegLon, metersPerDegLat));
                }
            }
        }
        return best;
    }

    private static double minRingDistanceMeters(
            double lat,
            double lon,
            Coordinate[] coords,
            double kx,
            double ky) {
        double best = Double.POSITIVE_INFINITY;
        for (int i = 0; i < coords.length - 1; i++) {
            double x1 = coords[i].x, y1 = coords[i].y;
            double x2 = coords[i + 1].x, y2 = coords[i + 1].y;
            double px = (lon - x1) * kx;
            double py = (lat - y1) * ky;
            double dx = (x2 - x1) * kx;
            double dy = (y2 - y1) * ky;
            double denom = dx * dx + dy * dy;
            double t = denom == 0.0 ? 0.0 : Math.max(0.0, Math.min(1.0, (px * dx + py * dy) / denom));
            double dist = Math.hypot(px - t * dx, py - t * dy);
            if (dist < best) best = dist;
        }
        return best;
    }

    private Geometry parseGeometry(JsonNode node) {
        String type = node.path("type").asText("");
        if ("Polygon".equals(type)) {
            return parsePolygon(node.path("coordinates"));
        }
        if ("MultiPolygon".equals(type)) {
            List<Polygon> polys = new ArrayList<>();
            for (JsonNode p : node.path("coordinates")) {
                polys.add(parsePolygon(p));
            }
            return geometryFactory.createMultiPolygon(polys.toArray(Polygon[]::new));
        }
        throw new IllegalArgumentException("Unsupported geometry type: " + type);
    }

    private Polygon parsePolygon(JsonNode rings) {
        LinearRing shell = parseRing(rings.get(0));
        LinearRing[] holes = new LinearRing[Math.max(0, rings.size() - 1)];
        for (int i = 1; i < rings.size(); i++) {
            holes[i - 1] = parseRing(rings.get(i));
        }
        return geometryFactory.createPolygon(shell, holes);
    }

    private LinearRing parseRing(JsonNode coordsNode) {
        Coordinate[] coords = new Coordinate[coordsNode.size()];
        for (int i = 0; i < coordsNode.size(); i++) {
            coords[i] = new Coordinate(coordsNode.get(i).get(0).asDouble(), coordsNode.get(i).get(1).asDouble());
        }
        return geometryFactory.createLinearRing(coords);
    }

    private static double round6(double v) {
        return Math.round(v * 1_000_000.0) / 1_000_000.0;
    }
}

