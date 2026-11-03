package vn.smartprop.recommendation;

import org.springframework.stereotype.Service;
import vn.smartprop.amenity.AmenityCatalogService;
import vn.smartprop.amenity.AmenityDtos.AmenityProfile;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import static vn.smartprop.recommendation.RecommendationDtos.*;

/**
 * Maps a recommendation candidate to the precomputed amenity catalog.
 *
 * <p>Contract: this adapter never invents coordinates or distances. TiniX rows carry no
 * verified property-level GPS, so only the administrative level actually present in the
 * candidate is used. A STREET precision in the source does not prove the unit sits on a
 * POI corridor, therefore corridors are deliberately not applied here.
 */
@Service
public class PropertyLocationResolver {
    public static final String BASIS_DIRECT_WARD = "DIRECT_WARD_EVIDENCE";
    public static final String BASIS_DISTRICT = "DISTRICT_SHARED_AMENITY";
    public static final String BASIS_UNKNOWN = "NO_AREA_MATCH";

    /** Confidence ceilings: a district profile is shared by every ward of that district. */
    static final double WARD_CEILING = 1.0;
    static final double DISTRICT_CEILING = 0.80;

    private final AmenityCatalogService catalog;
    /** Catalog is immutable after startup, so resolved lookups can be reused across requests. */
    private final java.util.concurrent.ConcurrentHashMap<String, Resolution> cache =
        new java.util.concurrent.ConcurrentHashMap<>();

    public PropertyLocationResolver(AmenityCatalogService catalog) {
        this.catalog = catalog;
    }

    /** Resolves district/ward only. Never guesses from title, description or raw address. */
    public Resolution resolve(String district, String ward) {
        String key = (district == null ? "" : district.strip()) + "\u0000"
            + (ward == null ? "" : ward.strip());
        Resolution cached = cache.get(key);
        if (cached != null) return cached;
        Resolution computed = resolveUncached(district, ward);
        cache.putIfAbsent(key, computed);
        return computed;
    }

    private Resolution resolveUncached(String district, String ward) {
        String cleanDistrict = blank(district);
        String cleanWard = blank(ward);
        if (cleanDistrict == null) {
            return unknown("Thiếu quận/huyện chuẩn hóa trong dữ liệu nguồn nên không xác định được khu vực tiện ích.");
        }
        if (cleanWard != null) {
            Optional<AmenityProfile> profile = catalog.lookup(cleanDistrict, cleanWard, null);
            if (profile.isPresent() && isWardOf(profile.get(), cleanDistrict)) {
                AmenityProfile p = profile.get();
                return new Resolution(p, BASIS_DIRECT_WARD, Math.min(WARD_CEILING, p.confidence()), true);
            }
        }
        Optional<AmenityProfile> districtProfile = catalog.lookup(cleanDistrict, null, null);
        if (districtProfile.isPresent() && "DISTRICT".equals(districtProfile.get().areaLevel())) {
            AmenityProfile p = districtProfile.get();
            return new Resolution(p, BASIS_DISTRICT, Math.min(DISTRICT_CEILING, p.confidence()), false);
        }
        return unknown(cleanWard == null
            ? "Quận/huyện không có trong danh mục tiện ích đã kiểm chứng."
            : "Phường/xã chưa có hồ sơ tiện ích riêng và quận/huyện cũng không khớp danh mục.");
    }

    /**
     * Guards the catalog's prefix-based ward fallback: a ward profile may belong to another
     * district with the same ward name, which would silently misattribute amenities.
     */
    static boolean isWardOf(AmenityProfile profile, String district) {
        if (profile == null || !"WARD".equals(profile.areaLevel())) return false;
        String parent = AmenityCatalogService.normalize(profile.parentDistrict());
        String wanted = AmenityCatalogService.normalize(district);
        if (parent.isEmpty() || wanted.isEmpty()) return false;
        return parent.equals(wanted);
    }

    private static Resolution unknown(String reason) {
        return new Resolution(null, BASIS_UNKNOWN, 0.0, false, reason);
    }

    private static String blank(String value) {
        return value == null || value.isBlank() ? null : value.strip();
    }

    /** Either a resolved profile or an explicit "not enough data" outcome. */
    public record Resolution(AmenityProfile profile, String evidenceBasis, double confidence,
                             boolean wardLevel, String unavailableReason) {
        public Resolution(AmenityProfile profile, String evidenceBasis, double confidence, boolean wardLevel) {
            this(profile, evidenceBasis, confidence, wardLevel, null);
        }

        public boolean available() {
            return profile != null;
        }

        public List<String> limitations() {
            List<String> out = new ArrayList<>();
            if (!available()) {
                out.add(unavailableReason == null
                    ? "Không đủ dữ liệu vị trí để chấm điểm tiện ích; không dùng điểm thay thế."
                    : unavailableReason);
            } else {
                out.addAll(profile.dataLimitations());
                if (!wardLevel) {
                    out.add("Chỉ khớp được cấp quận/huyện: tiện ích là đặc điểm chung của địa bàn, "
                        + "không phải tiện ích nằm sát bất động sản.");
                }
            }
            out.add("Không có tọa độ GPS cấp căn nên SmartProp không tính khoảng cách mét tới tiện ích.");
            return List.copyOf(out);
        }
    }
}