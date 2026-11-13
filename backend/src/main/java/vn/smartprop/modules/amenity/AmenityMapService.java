package vn.smartprop.modules.amenity;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.http.HttpStatus;
import java.util.*;

/** Public, bounded, read-only projection of independently collected POIs, never listing data. */
@Service
public class AmenityMapService {
    static final Set<String> CATEGORIES = Set.of("SCHOOL", "HOSPITAL", "PHARMACY", "MARKET",
        "SUPERMARKET", "PARK", "BEACH", "PUBLIC_TRANSPORT", "MALL");
    private final GeoapifyDistrictPlaces fallback;
    private final JdbcTemplate jdbc;
    private final AmenityCatalogService catalog;
    private final AmenityMapBoundaryCatalog boundaries;
    public AmenityMapService(JdbcTemplate jdbc, AmenityCatalogService catalog, AmenityMapBoundaryCatalog boundaries,GeoapifyDistrictPlaces fallback) {
        this.fallback=fallback; this.jdbc = jdbc; this.catalog = catalog; this.boundaries = boundaries;
    }
    public record MapPoi(String id, String name, String category, String district,
        double latitude, double longitude, String coordinateBasis, String reviewStatus,
        String sourceName, String sourceUrl, String attribution, String sourceLicense, String observedAt) {}
    public record MapEvidence(String version, String visibility, String district, String category,
        List<MapPoi> items, int eligibleCount, boolean truncated, AmenityMapBoundaryCatalog.Boundary boundary, List<String> dataLimitations) {}

    @Transactional(readOnly=true)
    public MapEvidence find(String district, String category) {
        String cat = category == null ? "ALL" : category.strip().toUpperCase(Locale.ROOT);
        if (!cat.equals("ALL") && !CATEGORIES.contains(cat)) throw badRequest();
        var area = catalog.lookup(district, null, null).filter(p -> "DISTRICT".equals(p.areaLevel()))
            .orElseThrow(AmenityMapService::badRequest);
        String canonicalDistrict = area.areaName();
        if (cat.equals("MALL")) return fallback.find(canonicalDistrict,cat);
        // The historical district attribution was checked during POI collection, not
        // inferred from a property, Qwen output, or an area centroid. No distances.
        List<MapPoi> candidates;
        try { candidates = jdbc.query("""
            SELECT poi_id,name,taxonomy_category,district_historical,latitude,longitude,
                   location_basis,review_status,source_name,external_id,attribution,source_license,observed_at
            FROM poi_effective_v1
            WHERE district_historical=? AND review_status='VALID'
              AND source_name='openstreetmap_overpass'
              AND (?='ALL' OR taxonomy_category=?)
            ORDER BY taxonomy_category,name,poi_id LIMIT 400
            """, (rs, row) -> new MapPoi(rs.getString("poi_id"), rs.getString("name"),
                rs.getString("taxonomy_category"), rs.getString("district_historical"),
                rs.getDouble("latitude"), rs.getDouble("longitude"), rs.getString("location_basis"),
                rs.getString("review_status"), rs.getString("source_name"),
                "https://www.openstreetmap.org/" + rs.getString("external_id"),
                rs.getString("attribution"), rs.getString("source_license"), rs.getString("observed_at")),
            canonicalDistrict, cat, cat);
        } catch(org.springframework.dao.DataAccessException unavailable){return fallback.find(canonicalDistrict,cat); }
        List<MapPoi> eligible = candidates.stream().filter(AmenityMapService::eligible).toList();
        Map<String,Integer> perCategory = new HashMap<>();
        int cap = cat.equals("ALL") ? 8 : 80;
        List<MapPoi> items = eligible.stream()
            .filter(p -> perCategory.merge(p.category(), 1, Integer::sum) <= cap).toList();
        return new MapEvidence("POI_MAP_V1", "PUBLIC", canonicalDistrict, cat, items,
            eligible.size(), items.size() < eligible.size() || candidates.size() == 400,
            items.isEmpty() ? boundaries.find(canonicalDistrict) : null, List.of(
                "Dữ liệu OpenStreetMap đã qua kiểm tra nguồn và phân loại; chưa xác minh thực địa hoặc giờ hoạt động.",
                "Điểm của way/relation đại diện đối tượng OSM, không phải cổng vào; không phải tâm khu vực.",
                "Địa bàn theo ranh giới quận/huyện lịch sử. Không suy ra khoảng cách tới bất động sản.",
                "Bản đồ chỉ dùng POI trạng thái VALID; không dùng dữ liệu tin đăng nghiên cứu hoặc điểm legacy chưa xác minh."));
    }
    static boolean eligible(MapPoi p) {
        if (!"VALID".equals(p.reviewStatus()) || !"openstreetmap_overpass".equals(p.sourceName())
            || p.category() == null || !CATEGORIES.contains(p.category()) || p.name() == null || p.name().isBlank()
            || p.coordinateBasis() == null || p.sourceUrl() == null
            || !Double.isFinite(p.latitude()) || !Double.isFinite(p.longitude())
            || p.latitude() < 15 || p.latitude() > 17 || p.longitude() < 107 || p.longitude() > 109
            || p.attribution() == null || p.attribution().isBlank() || p.sourceLicense() == null || p.sourceLicense().isBlank()) return false;
        String kind = switch (p.coordinateBasis()) {
            case "OSM_NODE" -> "node"; case "OSM_WAY_CENTER" -> "way";
            case "OSM_RELATION_CENTER" -> "relation"; default -> "invalid";
        };
        return p.sourceUrl().matches("https://www\\.openstreetmap\\.org/" + kind + "/[1-9][0-9]*");
    }
    private static ResponseStatusException badRequest() {
        return new ResponseStatusException(HttpStatus.BAD_REQUEST, "Unsupported amenity district/category");
    }
}
