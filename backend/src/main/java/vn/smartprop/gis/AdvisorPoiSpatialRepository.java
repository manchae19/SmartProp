package vn.smartprop.gis;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import vn.smartprop.gis.GisDtos.NearbyPoiItem;

/**
 * Read-only MySQL 8 Spatial repository for Step 21.4C — Advisor GIS Integration.
 *
 * <p>Uses {@code MBRContains(ST_GeomFromText(bbox, 4326, 'axis-order=long-lat'), p.location)}
 * on {@code points_of_interest FORCE INDEX (sx_poi_location)} combined with exact spherical
 * {@code ST_Distance_Sphere} filtering and {@code poi_taxonomy_enrichment} curation metadata.
 */
@Repository
public class AdvisorPoiSpatialRepository {

    public static final int DEFAULT_RADIUS_METERS = 1500;
    public static final int DEFAULT_MAX_POIS = 8;
    private static final int SQL_CANDIDATE_FETCH_LIMIT = 60;
    private static final long CACHE_TTL_SECONDS = 300L;
    private static final int MAX_CACHE_ENTRIES = 512;

    private static final List<String> PRIORITY_CATEGORIES = List.of(
        "SCHOOL",
        "HOSPITAL",
        "SUPERMARKET",
        "MARKET",
        "PARK",
        "BEACH",
        "PHARMACY",
        "PUBLIC_TRANSPORT",
        "TRANSPORT"
    );

    private static final Map<String, String> CATEGORY_LABELS_VI = Map.ofEntries(
        Map.entry("SCHOOL", "Trường học"),
        Map.entry("HOSPITAL", "Bệnh viện / Cơ sở y tế"),
        Map.entry("PHARMACY", "Nhà thuốc"),
        Map.entry("SUPERMARKET", "Siêu thị / Cửa hàng tiện lợi"),
        Map.entry("MARKET", "Chợ dân sinh"),
        Map.entry("PARK", "Công viên / Không gian xanh"),
        Map.entry("BEACH", "Bãi biển"),
        Map.entry("PUBLIC_TRANSPORT", "Giao thông công cộng"),
        Map.entry("TRANSPORT", "Giao thông")
    );

    public record RawPropertyCoordinate(String propertyId, double latitude, double longitude, int srid) {}

    private record CacheEntry(List<NearbyPoiItem> items, Instant expiresAt) {}

    private final JdbcTemplate jdbc;
    private final ConcurrentHashMap<String, CacheEntry> nearbyCache = new ConcurrentHashMap<>();

    public AdvisorPoiSpatialRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    /**
     * Batch-loads WGS84 coordinates for active published platform properties in a single SQL query.
     */
    public Map<String, RawPropertyCoordinate> loadPlatformCoordinates(Collection<String> propertyIds) {
        if (propertyIds == null || propertyIds.isEmpty()) {
            return Map.of();
        }
        List<String> cleanIds = propertyIds.stream()
            .filter(id -> id != null && !id.isBlank() && id.length() <= 64)
            .distinct()
            .toList();
        if (cleanIds.isEmpty()) {
            return Map.of();
        }

        String placeholders = cleanIds.stream().map(x -> "?").collect(Collectors.joining(","));
        String sql = """
            SELECT p.id,
                   ST_Latitude(p.location) AS lat,
                   ST_Longitude(p.location) AS lon,
                   ST_SRID(p.location) AS srid
            FROM properties p
            WHERE p.id IN (%s)
              AND p.status = 'PUBLISHED'
              AND p.deleted_at IS NULL
              AND (p.expires_at IS NULL OR p.expires_at > UTC_TIMESTAMP(6))
              AND p.location IS NOT NULL
            """.formatted(placeholders);

        Map<String, RawPropertyCoordinate> out = new LinkedHashMap<>();
        jdbc.query(
            sql,
            rs -> {
                RawPropertyCoordinate row = mapPropertyCoord(rs);
                out.put(row.propertyId(), row);
            },
            cleanIds.toArray()
        );
        return Map.copyOf(out);
    }

    /**
     * Queries curated nearby POIs within {@code radiusMeters} using R-tree {@code sx_poi_location}
     * + exact {@code ST_Distance_Sphere} spherical distance in meters.
     */
    public List<NearbyPoiItem> findNearbyPois(double latitude, double longitude, int radiusMeters, int maxItems) {
        if (!Double.isFinite(latitude) || !Double.isFinite(longitude)
                || Math.abs(latitude) > 90.0 || Math.abs(longitude) > 180.0
                || (Math.abs(latitude) < 1e-6 && Math.abs(longitude) < 1e-6)) {
            return List.of();
        }
        int clampedRadius = Math.max(100, Math.min(5000, radiusMeters));
        int clampedMax = Math.max(1, Math.min(20, maxItems));

        String cacheKey = String.format(
            Locale.ROOT, "%.4f:%.4f:%d:%d", latitude, longitude, clampedRadius, clampedMax);
        Instant now = Instant.now();
        CacheEntry cached = nearbyCache.get(cacheKey);
        if (cached != null && cached.expiresAt().isAfter(now)) {
            return cached.items();
        }

        String pointWkt = String.format(Locale.ROOT, "POINT(%.6f %.6f)", longitude, latitude);
        String bboxWkt = buildBoundingBoxWkt(latitude, longitude, clampedRadius);

        String sql = """
            SELECT p.id,
                   p.name,
                   COALESCE(e.taxonomy_category, UPPER(p.category)) AS eff_category,
                   ST_Latitude(p.location) AS lat,
                   ST_Longitude(p.location) AS lon,
                   ROUND(ST_Distance_Sphere(
                       p.location,
                       ST_GeomFromText(?, 4326, 'axis-order=long-lat')
                   )) AS distance_meters,
                   p.source_name
            FROM points_of_interest p FORCE INDEX (sx_poi_location)
            LEFT JOIN poi_taxonomy_enrichment e ON e.poi_id = p.id
            WHERE MBRContains(
                      ST_GeomFromText(?, 4326, 'axis-order=long-lat'),
                      p.location
                  )
              AND (e.review_status IS NULL OR e.review_status IN ('VALID', 'LEGACY_RECLASSIFIED', 'LEGACY_UNVERIFIED'))
              AND ST_Distance_Sphere(
                      p.location,
                      ST_GeomFromText(?, 4326, 'axis-order=long-lat')
                  ) <= ?
            ORDER BY distance_meters ASC, p.id ASC
            LIMIT ?
            """;

        List<NearbyPoiItem> candidates = jdbc.query(
            sql,
            (rs, rowNum) -> mapPoiItem(rs),
            pointWkt,
            bboxWkt,
            pointWkt,
            clampedRadius,
            SQL_CANDIDATE_FETCH_LIMIT
        );

        List<NearbyPoiItem> selected = selectDiverseNearbyPois(candidates, clampedMax);
        if (nearbyCache.size() >= MAX_CACHE_ENTRIES) {
            nearbyCache.clear();
        }
        nearbyCache.put(cacheKey, new CacheEntry(selected, now.plusSeconds(CACHE_TTL_SECONDS)));
        return selected;
    }

    /**
     * Builds a generous WGS84 lon-lat bounding-box polygon WKT guaranteed to enclose all points
     * within {@code radiusMeters} on the sphere so MySQL's {@code sx_poi_location} R-tree index is used
     * without ever missing a true spherical neighbor.
     */
    public static String buildBoundingBoxWkt(double latitude, double longitude, double radiusMeters) {
        // Add 5% safety margin over 110.574 km/deg lat and cos(lat)*111.320 km/deg lon
        double paddedMeters = radiusMeters * 1.05;
        double dLat = paddedMeters / 110_574.0;
        double cosLat = Math.max(0.1, Math.cos(Math.toRadians(latitude)));
        double dLon = paddedMeters / (111_320.0 * cosLat);

        double minLon = Math.max(-180.0, longitude - dLon);
        double maxLon = Math.min(180.0, longitude + dLon);
        double minLat = Math.max(-90.0, latitude - dLat);
        double maxLat = Math.min(90.0, latitude + dLat);

        return String.format(
            Locale.ROOT,
            "POLYGON((%.6f %.6f, %.6f %.6f, %.6f %.6f, %.6f %.6f, %.6f %.6f))",
            minLon, minLat,
            maxLon, minLat,
            maxLon, maxLat,
            minLon, maxLat,
            minLon, minLat
        );
    }

    /**
     * Selects up to {@code maxItems} verified POIs while ensuring essential categories (school,
     * hospital, supermarket/market, park/beach, pharmacy, transit) are represented before filling
     * remaining slots by strict ascending distance.
     */
    static List<NearbyPoiItem> selectDiverseNearbyPois(List<NearbyPoiItem> sortedCandidates, int maxItems) {
        if (sortedCandidates == null || sortedCandidates.isEmpty()) {
            return List.of();
        }
        Set<String> pickedIds = new LinkedHashSet<>();
        List<NearbyPoiItem> chosen = new ArrayList<>();
        int transitCount = 0;

        // Pass 1: closest item per priority category
        for (String cat : PRIORITY_CATEGORIES) {
            if (chosen.size() >= maxItems) break;
            for (NearbyPoiItem item : sortedCandidates) {
                if (cat.equals(item.category()) && !pickedIds.contains(item.id())) {
                    if (isTransit(cat) && transitCount >= 1) break;
                    pickedIds.add(item.id());
                    chosen.add(item);
                    if (isTransit(cat)) transitCount++;
                    break;
                }
            }
        }

        // Pass 2: fill remaining slots by ascending distance (capping transit at 2 if other categories exist)
        for (NearbyPoiItem item : sortedCandidates) {
            if (chosen.size() >= maxItems) break;
            if (pickedIds.contains(item.id())) continue;
            if (isTransit(item.category()) && transitCount >= 2) continue;
            pickedIds.add(item.id());
            chosen.add(item);
            if (isTransit(item.category())) transitCount++;
        }

        // Pass 3: if still below maxItems (e.g. only transit stops exist nearby), fill remaining by distance
        for (NearbyPoiItem item : sortedCandidates) {
            if (chosen.size() >= maxItems) break;
            if (pickedIds.add(item.id())) {
                chosen.add(item);
            }
        }

        chosen.sort(Comparator.comparingLong(NearbyPoiItem::distanceMeters).thenComparing(NearbyPoiItem::id));
        return List.copyOf(chosen);
    }

    public static String categoryLabelVi(String category) {
        if (category == null) return "Tiện ích";
        return CATEGORY_LABELS_VI.getOrDefault(category.strip().toUpperCase(Locale.ROOT), category);
    }

    private static boolean isTransit(String category) {
        return "PUBLIC_TRANSPORT".equals(category) || "TRANSPORT".equals(category);
    }

    private static RawPropertyCoordinate mapPropertyCoord(ResultSet rs) throws SQLException {
        return new RawPropertyCoordinate(
            rs.getString("id"),
            rs.getDouble("lat"),
            rs.getDouble("lon"),
            rs.getInt("srid")
        );
    }

    private static NearbyPoiItem mapPoiItem(ResultSet rs) throws SQLException {
        String cat = rs.getString("eff_category");
        String normCat = cat == null ? "OTHER" : cat.strip().toUpperCase(Locale.ROOT);
        return new NearbyPoiItem(
            rs.getString("id"),
            rs.getString("name"),
            normCat,
            categoryLabelVi(normCat),
            rs.getDouble("lat"),
            rs.getDouble("lon"),
            rs.getLong("distance_meters"),
            rs.getString("source_name")
        );
    }
}
