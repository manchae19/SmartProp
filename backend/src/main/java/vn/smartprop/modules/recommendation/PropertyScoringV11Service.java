package vn.smartprop.modules.recommendation;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import vn.smartprop.modules.amenity.AmenityDtos.AmenityProfile;
import vn.smartprop.modules.recommendation.PropertyLocationResolver.Resolution;
import vn.smartprop.modules.recommendation.RecommendationDtos.*;

import java.text.DecimalFormat;
import java.text.DecimalFormatSymbols;
import java.util.*;

/**
 * Hybrid Recommendation V1.1 scoring.
 *
 * <pre>
 * score = budgetFit*wBudget + areaFit*wArea + propertyTypeFit*wType + amenityFit*wAmenity - qualityPenalty
 * </pre>
 *
 * Components are only weighted in when they have real evidence. When an amenity profile is
 * missing, the amenity term is dropped and the remaining weights are renormalised, so a
 * data gap is reported as "no evidence" instead of being scored as a bad neighbourhood.
 * Every component stays in [0,100] and the final score is clamped to [0,100].
 */
@Service
public class PropertyScoringV11Service {
    /** Ideal asking/budget ratio: leaving a margin below the stated ceiling. */
    static final double TARGET_BUDGET_RATIO = 0.80;
    /** Evidence strength: a ward profile describes the property's own ward; a district profile is shared. */
    static final double WARD_EVIDENCE_TRUST = 0.80;
    static final double DISTRICT_EVIDENCE_TRUST = 0.45;

    private final PropertyLocationResolver locationResolver;
    private final Weights weights;

    public PropertyScoringV11Service(PropertyLocationResolver locationResolver,
            @Value("${app.recommendation.v11.living.budget:0.38}") double livingBudget,
            @Value("${app.recommendation.v11.living.area:0.17}") double livingArea,
            @Value("${app.recommendation.v11.living.type:0.20}") double livingType,
            @Value("${app.recommendation.v11.living.amenity:0.25}") double livingAmenity,
            @Value("${app.recommendation.v11.investment.budget:0.45}") double investmentBudget,
            @Value("${app.recommendation.v11.investment.area:0.25}") double investmentArea,
            @Value("${app.recommendation.v11.investment.type:0.20}") double investmentType,
            @Value("${app.recommendation.v11.investment.amenity:0.10}") double investmentAmenity,
            @Value("${app.recommendation.v11.rental.budget:0.40}") double rentalBudget,
            @Value("${app.recommendation.v11.rental.area:0.20}") double rentalArea,
            @Value("${app.recommendation.v11.rental.type:0.25}") double rentalType,
            @Value("${app.recommendation.v11.rental.amenity:0.15}") double rentalAmenity) {
        this.locationResolver = locationResolver;
        this.weights = new Weights(
            new ComponentWeights(livingBudget, livingArea, livingType, livingAmenity),
            new ComponentWeights(investmentBudget, investmentArea, investmentType, investmentAmenity),
            new ComponentWeights(rentalBudget, rentalArea, rentalType, rentalAmenity));
        this.weights.validate();
    }

    public Weights weights() { return weights; }

    /** Base V1.1 score, without amenity evidence (used when the flag is on but no profile exists). */
    public Scored11 score(Candidate c, Request r) {
        return score(c, r, locationResolver.resolve(c.district(), c.ward()));
    }

    /** Ranking pass: identical maths, but explanations are deferred to the winners only. */
    public Scored11 scoreForRanking(Candidate c, Request r, Resolution resolution) {
        return score(c, r, resolution, false);
    }

    public Scored11 score(Candidate c, Request r, Resolution resolution) {
        return score(c, r, resolution, true);
    }

    private Scored11 score(Candidate c, Request r, Resolution resolution, boolean withExplanations) {
        ComponentWeights w = weights.forPurpose(r.purpose());
        double budgetFit = round(budgetFit(c, r));
        double areaFit = round(areaFit(c, r));
        double typeFit = round(typeFit(c.type(), r.purpose()));
        AmenityProfile profile = resolution != null && resolution.available() ? resolution.profile() : null;
        Double amenityFit = amenityFit(profile, r);

        Map<String, Double> parts = new LinkedHashMap<>();
        Map<String, Double> appliedWeights = new LinkedHashMap<>();
        double sum = 0;
        parts.put("budgetFit", budgetFit); appliedWeights.put("budgetFit", w.budget()); sum += budgetFit * w.budget();
        parts.put("areaFit", areaFit); appliedWeights.put("areaFit", w.area()); sum += areaFit * w.area();
        parts.put("propertyTypeFit", typeFit); appliedWeights.put("propertyTypeFit", w.type()); sum += typeFit * w.type();
        double amenityContribution = 0;
        if (amenityFit != null) {
            double trust = resolution.wardLevel() ? WARD_EVIDENCE_TRUST : DISTRICT_EVIDENCE_TRUST;
            double effective = w.amenity() * trust;
            parts.put("amenityFit", amenityFit);
            appliedWeights.put("amenityFit", round4(effective));
            amenityContribution = amenityFit * effective;
            sum += amenityContribution;
        }
        double totalWeight = appliedWeights.values().stream().mapToDouble(Double::doubleValue).sum();
        double normalised = totalWeight > 0 ? sum / totalWeight : 0;
        double penalty = qualityPenalty(c);
        double score = round(clamp(normalised - penalty));

        if (!withExplanations) {
            return new Scored11(c, score, parts, List.of(), resolution, amenityFit, appliedWeights, penalty);
        }
        List<String> explanations = new ArrayList<>();
        explanations.add("Giá rao " + vnd(c.price()) + " nằm trong ngân sách " + vnd(r.budgetVnd())
            + "; độ hợp ngân sách " + num(budgetFit) + "/100 (so với mức chi tiêu mục tiêu "
            + num(TARGET_BUDGET_RATIO * 100) + "% ngân sách).");
        explanations.add("Diện tích nguồn " + plain(c.area()) + " m²; độ hợp diện tích "
            + num(areaFit) + "/100" + (r.minAreaSqm() == null ? " (chưa đặt diện tích tối thiểu, dùng mốc tham chiếu 100 m²)."
            : " (yêu cầu tối thiểu " + plain(r.minAreaSqm()) + " m²)."));
        explanations.add(typeExplanation(c.type(), r.purpose(), typeFit));
        if (amenityFit == null) {
            explanations.add("Chưa có hồ sơ tiện ích cho địa bàn này nên điểm tiện ích không được tính; "
                + "điểm tổng chỉ dựa trên ngân sách, diện tích và loại bất động sản.");
        } else {
            explanations.add(amenityExplanation(profile, resolution, amenityFit, w.amenity()));
            explanations.addAll(priorityExplanations(profile, r));
        }
        if (penalty > 0) {
            explanations.add("Trừ " + num(penalty) + " điểm do cờ chất lượng dữ liệu nguồn"
                + ("UNVERIFIED".equals(c.verification()) ? " (UNVERIFIED)" : "")
                + ("NEEDS_REVIEW".equals(c.quality()) ? " (NEEDS_REVIEW)" : "") + ".");
        }
        explanations.add("Điểm tổng " + num(score) + "/100 = trung bình có trọng số của các thành phần "
            + "đã có bằng chứng" + (penalty > 0 ? ", sau khi trừ điểm chất lượng" : "") + ".");
        return new Scored11(c, score, parts, List.copyOf(explanations), resolution, amenityFit, appliedWeights, penalty);
    }

    /** Rebuilds explanations for one already-ranked candidate (Top N only). */
    public List<String> explain(Candidate c, Request r, Scored11 ranked) {
        Resolution resolution = ranked.resolution();
        AmenityProfile profile = resolution != null && resolution.available() ? resolution.profile() : null;
        ComponentWeights w = weights.forPurpose(r.purpose());
        double budgetFit = ranked.parts().getOrDefault("budgetFit", 0d);
        double areaFit = ranked.parts().getOrDefault("areaFit", 0d);
        double typeFit = ranked.parts().getOrDefault("propertyTypeFit", 0d);
        var explanations = new ArrayList<String>();
        explanations.add("Giá rao " + vnd(c.price()) + " nằm trong ngân sách " + vnd(r.budgetVnd())
            + "; độ hợp ngân sách " + num(budgetFit) + "/100 (so với mức chi tiêu mục tiêu "
            + num(TARGET_BUDGET_RATIO * 100) + "% ngân sách).");
        explanations.add("Diện tích nguồn " + plain(c.area()) + " m²; độ hợp diện tích "
            + num(areaFit) + "/100" + (r.minAreaSqm() == null ? " (chưa đặt diện tích tối thiểu, dùng mốc tham chiếu 100 m²)."
            : " (yêu cầu tối thiểu " + plain(r.minAreaSqm()) + " m²)."));
        explanations.add(typeExplanation(c.type(), r.purpose(), typeFit));
        if (profile == null) {
            explanations.add("Chưa có hồ sơ tiện ích cho địa bàn này nên điểm tiện ích không được tính; "
                + "điểm tổng chỉ dựa trên ngân sách, diện tích và loại bất động sản.");
        } else {
            if (ranked.amenityFit() != null) explanations.add(amenityExplanation(profile, resolution, ranked.amenityFit(), w.amenity()));
            explanations.addAll(priorityExplanations(profile, r));
        }
        if (ranked.qualityPenalty() > 0) {
            explanations.add("Trừ " + num(ranked.qualityPenalty()) + " điểm do cờ chất lượng dữ liệu nguồn"
                + ("UNVERIFIED".equals(c.verification()) ? " (UNVERIFIED)" : "")
                + ("NEEDS_REVIEW".equals(c.quality()) ? " (NEEDS_REVIEW)" : "") + ".");
        }
        explanations.add("Điểm tổng " + num(ranked.score()) + "/100 = trung bình có trọng số của các thành phần "
            + "đã có bằng chứng" + (ranked.qualityPenalty() > 0 ? ", sau khi trừ điểm chất lượng" : "") + ".");
        return List.copyOf(explanations);
    }

    /** Preference scores are applied to EVERY eligible candidate, before top-N and dedup. */
    static Double amenityFit(AmenityProfile profile, Request request) {
        if (profile == null) return null;
        if (request.amenityPriorities().isEmpty()) return round(clamp(profile.livingScore()));
        if (profile.categoryScores() == null || profile.poiCounts() == null) return null;
        double sum=0, weight=0;
        var priorities = request.amenityPriorities().stream().distinct().toList();
        for(int i=0;i<priorities.size();i++) {
            AmenityPriority priority=priorities.get(i);
            if(!hasEvidence(profile,priority)) continue;
            double w=Math.pow(0.5,i); // main 1, secondary 0.5, then 0.25 / 0.125
            double value=switch(priority) {
                case SCHOOL -> profile.categoryScores().education();
                case SUPERMARKET, MARKET -> profile.categoryScores().essentials();
                case HOSPITAL, PHARMACY -> profile.categoryScores().healthcare();
                case PARK, BEACH -> profile.categoryScores().recreation();
                case PUBLIC_TRANSPORT -> profile.categoryScores().transit();
            };
            if(!Double.isFinite(value)) continue;
            sum+=clamp(value)*w;weight+=w;
        }
        return weight==0?null:round(sum/weight);
    }
    static boolean hasEvidence(AmenityProfile p,AmenityPriority priority) {
        if(p.poiCounts()==null)return false;
        return switch(priority) {
            case SCHOOL -> p.poiCounts().school()>0;
            case SUPERMARKET -> p.poiCounts().supermarket()>0;
            case MARKET -> p.poiCounts().market()>0;
            case HOSPITAL -> p.poiCounts().hospital()>0;
            case PHARMACY -> p.poiCounts().pharmacy()>0;
            case PARK -> p.poiCounts().park()>0;
            case BEACH -> p.poiCounts().beach()>0;
            case PUBLIC_TRANSPORT -> p.poiCounts().transit()>0;
        };
    }
    static List<String> priorityExplanations(AmenityProfile p,Request request) {
        if(request.amenityPriorities().isEmpty())return List.of();
        List<String> notes=new ArrayList<>();
        notes.add("Ưu tiên do người dùng chọn theo thứ tự: "+request.amenityPriorities()+". Chấm theo nhóm tiện ích ở "+p.areaLevel()+", không phải khoảng cách từ căn nhà; điểm chợ/siêu thị dùng nhóm nhu yếu phẩm, không phải điểm siêu thị riêng.");
        if(request.amenityPriorities().contains(AmenityPriority.SCHOOL))notes.add("Bằng chứng SCHOOL là trường học nói chung, chưa xác nhận trường tiểu học hoặc trường phù hợp cho từng trẻ.");
        for(var priority:request.amenityPriorities())if(!hasEvidence(p,priority))notes.add("Chưa có bằng chứng về "+priority+" trong hồ sơ khu vực; bỏ thành phần này và chuẩn hóa lại trọng số, không kết luận khu vực không có tiện ích.");
        return List.copyOf(notes);
    }

    private static String amenityExplanation(AmenityProfile p, Resolution res, double fit, double baseWeight) {
        String level = res.wardLevel() ? "cấp phường/xã" : "cấp quận/huyện";
        return "Điểm tiện ích an cư " + num(fit) + "/100 theo " + level + " (" + p.areaName() + ", bằng chứng "
            + res.evidenceBasis() + ", độ tin cậy " + num(res.confidence() * 100) + "%); trọng số hiệu dụng "
            + num(res.wardLevel() ? baseWeight * WARD_EVIDENCE_TRUST * 100 : baseWeight * DISTRICT_EVIDENCE_TRUST * 100)
            + "% do " + (res.wardLevel() ? "khớp đúng phường/xã" : "chỉ khớp được quận/huyện") + ".";
    }

    static String typeExplanation(PropertyType type, Purpose purpose, double fit) {
        String label = switch (type) {
            case HOUSE -> "nhà ở"; case APARTMENT -> "căn hộ"; case LAND -> "đất nền";
            case VILLA -> "biệt thự/nhà liền kề"; case ROOM -> "phòng"; case COMMERCIAL -> "bất động sản thương mại";
            case ALL -> "tất cả loại";
        };
        String reason = switch (purpose) {
            case LIVING -> switch (type) {
                case HOUSE, APARTMENT -> "có thể sử dụng để ở ngay, phù hợp nhu cầu an cư.";
                case VILLA -> "phù hợp an cư nhưng thường vượt ngân sách phổ thông.";
                case ROOM -> "diện tích nhỏ, phù hợp ở một người hơn là gia đình.";
                case COMMERCIAL -> "mục đích chính là kinh doanh, không tối ưu cho an cư.";
                case LAND -> "cần đầu tư xây dựng trước khi ở được nên chỉ được tính điểm thấp, không bị loại.";
                case ALL -> "";
            };
            case RENTAL -> switch (type) {
                case APARTMENT, HOUSE -> "dễ khai thác cho thuê nhờ nhu cầu thuê phổ biến.";
                case ROOM -> "phù hợp cho thuê phòng nhưng giá trị tài sản thấp.";
                case VILLA -> "tệp khách thuê hẹp, thanh khoản cho thuê thấp hơn.";
                case COMMERCIAL -> "có thể cho thuê mặt bằng nhưng phụ thuộc vị trí kinh doanh.";
                case LAND -> "không tạo dòng tiền thuê trực tiếp.";
                case ALL -> "";
            };
            case INVESTMENT -> switch (type) {
                case LAND -> "thanh khoản và biên tăng giá thường tốt ở đô thị đang mở rộng.";
                case HOUSE, APARTMENT -> "cân bằng giữa khai thác và tăng giá.";
                case COMMERCIAL -> "phụ thuộc chất lượng vị trí kinh doanh.";
                case VILLA, ROOM -> "tệp người mua hẹp hơn nên thanh khoản kém hơn.";
                case ALL -> "";
            };
        };
        return "Loại " + label + ": " + reason + " Điểm hợp loại " + num(fit) + "/100.";
    }

    static double budgetFit(Candidate c, Request r) {
        double ratio = c.price().divide(r.budgetVnd(), 12, java.math.RoundingMode.HALF_UP).doubleValue();
        return 100 * Math.max(0, 1 - Math.abs(ratio - TARGET_BUDGET_RATIO) / TARGET_BUDGET_RATIO);
    }

    static double areaFit(Candidate c, Request r) {
        double target = r.minAreaSqm() == null ? 100 : r.minAreaSqm().doubleValue() * 1.5;
        return 100 * Math.min(1, c.area().doubleValue() / target);
    }

    static double typeFit(PropertyType type, Purpose purpose) {
        if (type == null) return 0;
        return switch (purpose) {
            case LIVING -> switch (type) {
                case HOUSE, APARTMENT -> 100; case VILLA -> 85; case ROOM -> 60; case LAND -> 45; case COMMERCIAL -> 35; case ALL -> 60; };
            case RENTAL -> switch (type) {
                case APARTMENT -> 100; case HOUSE -> 90; case ROOM -> 80; case VILLA -> 60; case COMMERCIAL -> 55; case LAND -> 35; case ALL -> 60; };
            case INVESTMENT -> switch (type) {
                case LAND -> 95; case HOUSE -> 85; case APARTMENT -> 80; case COMMERCIAL -> 75; case VILLA -> 55; case ROOM -> 30; case ALL -> 60; };
        };
    }

    static double qualityPenalty(Candidate c) {
        return ("UNVERIFIED".equals(c.verification()) ? 10 : 0) + ("NEEDS_REVIEW".equals(c.quality()) ? 15 : 0);
    }

    static double clamp(double v) { return Math.max(0, Math.min(100, v)); }
    static double round(double v) { return Math.round(v * 100d) / 100d; }
    static double round4(double v) { return Math.round(v * 10000d) / 10000d; }

    private static final DecimalFormat PLAIN = new DecimalFormat("0.##", DecimalFormatSymbols.getInstance(Locale.ROOT));
    static String plain(java.math.BigDecimal v) { return v == null ? "?" : PLAIN.format(v); }
    static String num(double v) { return PLAIN.format(v); }
    static String vnd(java.math.BigDecimal v) {
        return v == null ? "?" : new java.text.DecimalFormat("#,##0", DecimalFormatSymbols.getInstance(Locale.US)).format(v) + " VND";
    }

    public record ComponentWeights(double budget, double area, double type, double amenity) {
        double sum() { return budget + area + type + amenity; }
    }

    public record Weights(ComponentWeights living, ComponentWeights investment, ComponentWeights rental) {
        void validate() {
            for (var w : List.of(living, investment, rental)) {
                if (w == null || !(w.budget() >= 0 && w.area() >= 0 && w.type() >= 0 && w.amenity() >= 0))
                    throw new IllegalStateException("Hybrid V1.1 weights must be non-negative");
                if (Math.abs(w.sum() - 1d) > 1e-6)
                    throw new IllegalStateException("Hybrid V1.1 weights must sum to 1.0, got " + w.sum());
            }
        }
        ComponentWeights forPurpose(Purpose p) {
            return switch (p) { case LIVING -> living; case INVESTMENT -> investment; case RENTAL -> rental; };
        }
        Map<String, Double> asMap(Purpose p) {
            var w = forPurpose(p);
            var out = new LinkedHashMap<String, Double>();
            out.put("budgetFit", w.budget()); out.put("areaFit", w.area());
            out.put("propertyTypeFit", w.type()); out.put("amenityFit", w.amenity());
            return out;
        }
    }

    public record Scored11(Candidate candidate, double score, Map<String, Double> parts,
                           List<String> explanations, Resolution resolution, Double amenityFit,
                           Map<String, Double> appliedWeights, double qualityPenalty) {}
}