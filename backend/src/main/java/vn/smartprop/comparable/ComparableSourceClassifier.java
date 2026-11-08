package vn.smartprop.comparable;
import java.util.Locale;

/** Maps raw source flags into the three kinds the UI must keep apart. */
public final class ComparableSourceClassifier {
    private ComparableSourceClassifier() {}

    public static final String TINIX_ATTRIBUTION =
        "TiniX \u2014 D\u1eef li\u1ec7u tham chi\u1ebfu nghi\u00ean c\u1ee9u, ch\u01b0a x\u00e1c minh c\u00f2n giao d\u1ecbch (CC BY-NC 4.0)";

    public static String smartPropLabel() { return "SmartProp"; }

    public static String externalLabel(String source) {
        if (source == null || source.isBlank()) return "Tin \u0111\u0103ng b\u00ean ngo\u00e0i";
        return switch (source.toUpperCase(Locale.ROOT)) {
            case "CHOTOT" -> "Ch\u1ee3 T\u1ed1t";
            case "CAFELAND" -> "CafeLand";
            case "NHADAT24H" -> "Nh\u00e0 \u0110\u1ea5t 24h";
            case "HOMEDY" -> "Homedy";
            case "ALONHADAT" -> "Alonhadat";
            default -> "Tin \u0111\u0103ng b\u00ean ngo\u00e0i";
        };
    }

    /** Only http(s) links leave the server; anything else becomes null. */
    public static String safeUrl(String url) {
        if (url == null) return null;
        String trimmed = url.strip();
        if (trimmed.isEmpty()) return null;
        String lower = trimmed.toLowerCase(Locale.ROOT);
        if (!lower.startsWith("http://") && !lower.startsWith("https://")) return null;
        return trimmed.length() > 2048 ? null : trimmed;
    }
}
