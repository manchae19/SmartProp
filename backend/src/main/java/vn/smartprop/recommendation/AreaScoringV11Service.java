package vn.smartprop.recommendation;

import org.springframework.stereotype.Service;
import vn.smartprop.amenity.AmenityDtos.AmenityProfile;
import vn.smartprop.recommendation.PropertyLocationResolver.Resolution;
import vn.smartprop.recommendation.RecommendationDtos.*;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;

/**
 * Hybrid V1.1 area ranking: candidate fit plus the area's own amenity profile.
 *
 * <p>The amenity share of an area score is scaled by evidence quality. A district-level
 * profile never counts as strongly as a ward-level profile, and an area without a profile
 * keeps its candidate-only score instead of receiving a low amenity value.
 */
@Service
public class AreaScoringV11Service {
    static final int MAX_AREAS = 5;
    static final int MAX_AREA_EVIDENCE = 4;

    private final PropertyLocationResolver locationResolver;
    private final AmenityEvidenceService evidenceService;

    public AreaScoringV11Service(PropertyLocationResolver locationResolver, AmenityEvidenceService evidenceService) {
        this.locationResolver = locationResolver;
        this.evidenceService = evidenceService;
    }

    public List<AreaResult> top(List<PropertyScoringV11Service.Scored11> candidates) {
        Map<String, List<PropertyScoringV11Service.Scored11>> grouped = new TreeMap<>();
        for (var s : candidates) {
            var c = s.candidate();
            if (c.district() == null || c.district().isBlank()) continue;
            String key = HybridRecommendationService.normalize(c.district()) + "|" + HybridRecommendationService.normalize(c.ward());
            grouped.computeIfAbsent(key, k -> new ArrayList<>()).add(s);
        }
        List<AreaResult> results = new ArrayList<>();
        for (var group : grouped.values()) {
            var first = group.getFirst().candidate();
            int unverified = (int) group.stream().filter(s -> "UNVERIFIED".equals(s.candidate().verification())).count();
            int review = (int) group.stream().filter(s -> "NEEDS_REVIEW".equals(s.candidate().quality())).count();
            BigDecimal sum = group.stream().map(s -> s.candidate().price()).reduce(BigDecimal.ZERO, BigDecimal::add);
            double candidateScore = group.stream().mapToDouble(PropertyScoringV11Service.Scored11::score).average().orElse(0);
            Resolution resolution = locationResolver.resolve(first.district(), first.ward());
            AmenityProfile profile = resolution.available() ? resolution.profile() : null;
            double amenityShare = resolution.wardLevel() ? 0.5 : (resolution.available() ? 0.3 : 0.0);
            Double amenityScore = profile == null ? null : PropertyScoringV11Service.round(profile.livingScore());
            double areaScore = profile == null ? candidateScore
                : PropertyScoringV11Service.round(candidateScore * (1 - amenityShare) + profile.livingScore() * amenityShare);

            List<String> explanations = new ArrayList<>();
            explanations.add("Điểm trung bình của " + group.size()
                + " ứng viên sau lọc và khử nhóm trùng; địa bàn theo nguồn dữ liệu.");
            if (profile != null) {
                explanations.add("Điểm tiện ích an cư cấp " + (resolution.wardLevel() ? "phường/xã" : "quận/huyện")
                    + ": " + PropertyScoringV11Service.num(profile.livingScore()) + "/100 (bằng chứng "
                    + resolution.evidenceBasis() + ").");
            } else {
                explanations.add("Chưa có hồ sơ tiện ích đã kiểm chứng cho địa bàn này; "
                    + "điểm khu vực chỉ từ các tiêu chí của ứng viên.");
            }
            explanations.add("Trung bình giá rao của mẫu, không phải giá thị trường hay dự báo tăng giá.");

            List<String> warnings = new ArrayList<>();
            if (unverified > 0 || review > 0) {
                warnings.add("Mẫu demo nội bộ chứa tin chưa xác minh/cần rà soát; không coi là nguồn cung đã xác minh.");
            }
            if (profile == null) warnings.add("NO_AMENITY_EVIDENCE: khu vực không có bằng chứng tiện ích; điểm không phản ánh chất lượng sống.");
            else if (!resolution.wardLevel()) warnings.add("AMENITY_IS_DISTRICT_SHARED: tiện ích là đặc điểm chung của quận/huyện.");
            String coverage = profile == null ? "UNKNOWN"
                : AmenityEvidenceService.coverageTier(profile.completenessTier(), profile.hasCriticalGaps());
            if (profile != null && coverage.contains("WITH_GAPS")) {
                warnings.add("AMENITY_COVERAGE_GAPS: hồ sơ tiện ích còn thiếu trụ cột, điểm có thể thấp hơn thực tế do thiếu dữ liệu số hóa.");
            }

            List<PoiEvidence> evidence = new ArrayList<>();
            if (profile != null && profile.poiEvidence() != null) {
                for (var item : profile.poiEvidence()) {
                    if (evidence.size() >= MAX_AREA_EVIDENCE) break;
                    if (item.name() != null && !item.name().isBlank()) evidence.add(new PoiEvidence(item.name(), item.category()));
                }
            }
            results.add(new AreaResult(first.district(), first.ward(), group.size(), areaScore,
                sum.divide(BigDecimal.valueOf(group.size()), 2, RoundingMode.HALF_UP),
                group.stream().map(s -> s.candidate().source().name()).distinct().sorted().toList(), unverified, review,
                List.copyOf(explanations), List.copyOf(warnings),
                amenityScore, profile == null ? null : PropertyScoringV11Service.round4(resolution.confidence()),
                profile == null ? null : profile.areaId(), resolution.evidenceBasis(), coverage, List.copyOf(evidence)));
        }
        return results.stream()
            .sorted(Comparator.comparingDouble(AreaResult::score).reversed()
                .thenComparing(AreaResult::district)
                .thenComparing(a -> a.ward() == null ? "" : a.ward()))
            .limit(MAX_AREAS).toList();
    }
}