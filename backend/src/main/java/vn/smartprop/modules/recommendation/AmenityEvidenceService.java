package vn.smartprop.modules.recommendation;

import org.springframework.stereotype.Service;
import vn.smartprop.modules.amenity.AmenityDtos.AmenityProfile;
import vn.smartprop.modules.amenity.AmenityDtos.CategoryScores;
import vn.smartprop.modules.amenity.AmenityDtos.PoiCounts;
import vn.smartprop.modules.recommendation.PropertyLocationResolver.Resolution;
import vn.smartprop.modules.recommendation.RecommendationDtos.*;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * Builds the public-safe amenity payload for recommendations.
 *
 * <p>Deliberately omitted: {@code sampleListingCount} (derived from the TiniX research set)
 * and raw POI coordinates. Only category scores, verified POI names/categories and the
 * catalog's own limitations cross the API boundary.
 */
@Service
public class AmenityEvidenceService {
    static final int MAX_EVIDENCE_ITEMS = 6;

    public AmenityEvidence build(AmenityProfile p, Resolution resolution, Double amenityFit) {
        if (p == null) return null;
        Map<String, Double> categories = new LinkedHashMap<>();
        CategoryScores cs = p.categoryScores();
        if (cs != null) {
            categories.put("essentials", round(cs.essentials()));
            categories.put("education", round(cs.education()));
            categories.put("healthcare", round(cs.healthcare()));
            categories.put("transit", round(cs.transit()));
            categories.put("recreation", round(cs.recreation()));
        }
        List<PoiEvidence> evidence = new ArrayList<>();
        if (p.poiEvidence() != null) {
            for (var item : p.poiEvidence()) {
                if (evidence.size() >= MAX_EVIDENCE_ITEMS) break;
                String name = item.name() == null ? "" : item.name().strip();
                if (name.isEmpty()) continue;
                evidence.add(new PoiEvidence(name, item.category()));
            }
        }
        PoiCounts counts = p.poiCounts();
        String coverage = coverageTier(p.completenessTier(), p.hasCriticalGaps());
        String note = resolution.wardLevel()
            ? "Tiện ích được xác định theo phường/xã của bất động sản; đây là đặc điểm khu vực, không phải khoảng cách từ căn nhà."
            : "Tiện ích được xác định theo quận/huyện; không suy ra rằng tiện ích nằm sát bất động sản.";
        if (p.areaLevel() != null && !p.areaLevel().equals(resolution.wardLevel() ? "WARD" : "DISTRICT")) {
            note = "Hồ sơ tiện ích ở cấp " + p.areaLevel() + "; không quy đổi thành vị trí căn nhà.";
        }
        return new AmenityEvidence(p.areaId(), p.areaLevel(), p.areaName(), p.parentDistrict(),
            round(p.livingScore()), amenityFit == null ? null : round(amenityFit), round4(resolution.confidence()),
            resolution.evidenceBasis(), categories, List.copyOf(evidence), resolution.limitations(),
            coverage, note + countsNote(counts));
    }

    /** Explicit "no evidence" payload: never substituted with an optimistic default value. */
    public AmenityEvidence unavailable(Resolution resolution) {
        Resolution r = resolution == null
            ? new Resolution(null, PropertyLocationResolver.BASIS_UNKNOWN, 0.0, false,
                "Chưa xác định được địa bàn của bất động sản.")
            : resolution;
        return new AmenityEvidence(null, "UNKNOWN", null, null, null, null, 0.0,
            r.evidenceBasis(), Map.of(), List.of(), r.limitations(), "UNKNOWN",
            "Không có bằng chứng tiện ích cho địa bàn này; điểm tổng không cộng thành phần tiện ích.");
    }

    private static String countsNote(PoiCounts c) {
        if (c == null) return "";
        return " Đã số hóa " + c.total() + " POI: " + c.school() + " trường, " + c.hospital() + " bệnh viện, "
            + c.pharmacy() + " nhà thuốc, " + c.market() + " chợ, " + c.supermarket() + " siêu thị, "
            + c.park() + " công viên, " + c.beach() + " bãi biển, " + c.transit() + " trạm giao thông công cộng.";
    }

    static String coverageTier(String completenessTier, String criticalGaps) {
        String tier = completenessTier == null ? "" : completenessTier.strip().toUpperCase(Locale.ROOT);
        boolean gaps = criticalGaps != null && !criticalGaps.isBlank()
            && !"NO".equalsIgnoreCase(criticalGaps.strip());
        if (tier.isEmpty()) return gaps ? "LIMITED" : "UNKNOWN";
        return gaps ? tier + "_WITH_GAPS" : tier;
    }

    static double round(double v) { return Math.round(v * 100d) / 100d; }
    static double round4(double v) { return Math.round(v * 10000d) / 10000d; }
}