package vn.smartprop.comparable;
import java.math.BigDecimal;
import java.math.MathContext;
import java.math.RoundingMode;
import java.util.LinkedHashMap;
import java.util.Map;

/** Weighted similarity for one candidate against the reference property.
 *
 *  Weights start from the Step 21.2A proposal (location dominant, then area,
 *  then product type) and are exposed in the breakdown so a reviewer can see
 *  exactly why a candidate ranked where it did. Price is deliberately a very
 *  small term: using it heavily would make the ranking confirm the model's own
 *  output rather than describe the property.
 */
public final class ComparableSimilarityScorer {
    private ComparableSimilarityScorer() {}

    public static final double W_LOCATION = 0.34;
    public static final double W_AREA = 0.30;
    public static final double W_BEDROOMS = 0.12;
    public static final double W_FLOORS = 0.10;
    public static final double W_FRONTAGE = 0.06;
    public static final double W_PRICE = 0.08;

    public record Input(
        String district, String ward, String propertyType,
        BigDecimal areaSqm, BigDecimal priceVnd,
        Integer bedrooms, Integer floors, BigDecimal frontageM
    ) {}

    public record Result(double score, Map<String,String> breakdown) {}

    public static Result score(Input ref, Input cand) {
        Map<String,String> parts = new LinkedHashMap<>();
        double total = 0.0, weightUsed = 0.0;

        double loc = locationScore(ref.district(), ref.ward(), cand.district(), cand.ward());
        parts.put("location", fmt(loc) + (eq(ref.ward(), cand.ward()) ? " (cùng phường)"
                : eq(ref.district(), cand.district()) ? " (cùng quận)" : " (quận lân cận)"));
        total += loc * W_LOCATION; weightUsed += W_LOCATION;

        if (ref.areaSqm() != null && cand.areaSqm() != null
                && ref.areaSqm().signum() > 0 && cand.areaSqm().signum() > 0) {
            double a = ratioScore(ref.areaSqm(), cand.areaSqm());
            parts.put("area", fmt(a) + " (" + round1(cand.areaSqm()) + " m2)");
            total += a * W_AREA; weightUsed += W_AREA;
        }

        if (ref.bedrooms() != null && cand.bedrooms() != null) {
            double b = 1.0 - Math.min(Math.abs(ref.bedrooms() - cand.bedrooms()) / 3.0, 1.0);
            parts.put("bedrooms", fmt(b));
            total += b * W_BEDROOMS; weightUsed += W_BEDROOMS;
        }

        if (ref.floors() != null && cand.floors() != null) {
            double f = 1.0 - Math.min(Math.abs(ref.floors() - cand.floors()) / 4.0, 1.0);
            parts.put("floors", fmt(f));
            total += f * W_FLOORS; weightUsed += W_FLOORS;
        }

        if (ref.frontageM() != null && cand.frontageM() != null
                && ref.frontageM().signum() > 0 && cand.frontageM().signum() > 0) {
            double fr = 1.0 - Math.min(
                Math.abs(ref.frontageM().doubleValue() - cand.frontageM().doubleValue()) / 10.0, 1.0);
            parts.put("frontage", fmt(fr));
            total += fr * W_FRONTAGE; weightUsed += W_FRONTAGE;
        }

        if (ref.priceVnd() != null && cand.priceVnd() != null
                && ref.priceVnd().signum() > 0 && cand.priceVnd().signum() > 0) {
            double p = ratioScore(ref.priceVnd(), cand.priceVnd());
            parts.put("price", fmt(p));
            total += p * W_PRICE; weightUsed += W_PRICE;
        }

        if (eq(ref.propertyType(), cand.propertyType())) {
            parts.put("type", "cùng loại hình");
        } else {
            // A type mismatch is a hard penalty: the caller should have filtered it,
            // so if one survives it must not rank as though it were comparable.
            total *= 0.5;
            parts.put("type", "khác loại hình (giảm 50%)");
        }

        double score = weightUsed > 0 ? total / weightUsed : 0.0;
        return new Result(Math.max(0.0, Math.min(1.0, score)), parts);
    }

    /** 1.0 when equal, falling to 0.0 at a 3x ratio; symmetric in both directions. */
    static double ratioScore(BigDecimal a, BigDecimal b) {
        double da = a.doubleValue(), db = b.doubleValue();
        if (da <= 0 || db <= 0) return 0.0;
        double ratio = Math.max(da, db) / Math.min(da, db);
        return 1.0 - Math.min((ratio - 1.0) / 2.0, 1.0);
    }

    static double locationScore(String d1, String w1, String d2, String w2) {
        if (eq(d1, d2) && eq(w1, w2) && w1 != null) return 1.0;
        if (eq(d1, d2)) return 0.82;
        if (adjacent(d1, d2)) return 0.45;
        return 0.15;
    }

    /** District neighbours, exposed so the ranking service and its tests agree. */
    public static java.util.List<String> neighboursOf(String district) {
        return ADJACENT.getOrDefault(district, java.util.Set.of()).stream().sorted().toList();
    }

    public static boolean areNeighbours(String a, String b) { return adjacent(a, b); }

    /** Da Nang adjacency used only as a coarse fallback tier. */
    static boolean adjacent(String a, String b) {
        if (a == null || b == null) return false;
        return ADJACENT.getOrDefault(a, java.util.Set.of()).contains(b);
    }

    private static final Map<String, java.util.Set<String>> ADJACENT = Map.of(
        "H\u1ea3i Ch\u00e2u", java.util.Set.of("Thanh Kh\u00ea", "S\u01a1n Tr\u00e0", "C\u1ea9m L\u1ec7"),
        "Thanh Kh\u00ea", java.util.Set.of("H\u1ea3i Ch\u00e2u", "Li\u00ean Chi\u1ec3u", "C\u1ea9m L\u1ec7"),
        "S\u01a1n Tr\u00e0", java.util.Set.of("H\u1ea3i Ch\u00e2u", "Ng\u0169 H\u00e0nh S\u01a1n"),
        "Ng\u0169 H\u00e0nh S\u01a1n", java.util.Set.of("S\u01a1n Tr\u00e0", "H\u1ea3i Ch\u00e2u", "C\u1ea9m L\u1ec7"),
        "C\u1ea9m L\u1ec7", java.util.Set.of("H\u1ea3i Ch\u00e2u", "Thanh Kh\u00ea", "Ng\u0169 H\u00e0nh S\u01a1n", "H\u00f2a Vang"),
        "Li\u00ean Chi\u1ec3u", java.util.Set.of("Thanh Kh\u00ea", "H\u00f2a Vang"),
        "H\u00f2a Vang", java.util.Set.of("Li\u00ean Chi\u1ec3u", "C\u1ea9m L\u1ec7", "Ng\u0169 H\u00e0nh S\u01a1n")
    );

    private static boolean eq(String a, String b) {
        return a != null && b != null && a.strip().equalsIgnoreCase(b.strip());
    }

    private static String fmt(double v) {
        return BigDecimal.valueOf(v).setScale(2, RoundingMode.HALF_UP).toPlainString();
    }

    private static String round1(BigDecimal v) {
        return v.round(new MathContext(4, RoundingMode.HALF_UP)).toPlainString();
    }
}
