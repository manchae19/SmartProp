package vn.smartprop.modules.news;

import java.net.URI;
import java.net.URISyntaxException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.text.Normalizer;
import java.util.HexFormat;
import java.util.Locale;
import java.util.Set;

/**
 * Chuẩn hoá text và URL từ feed — đầu vào không tin cậy.
 *
 * <p>Text: bỏ HTML tag, giải entity, gộp whitespace, giới hạn độ dài. Giữ nguyên dấu
 * tiếng Việt trên dữ liệu hiển thị; chỉ dùng dạng NFD khi cần so khớp.
 *
 * <p>URL: bỏ tracking parameters, chuẩn hoá host/scheme, bỏ fragment. Không xoá query
 * parameter mang ý nghĩa định danh bài viết.
 */
public final class NewsText {
    private NewsText() {}

    /** Query parameter chỉ dùng để tracking — bỏ khỏi canonical URL. */
    private static final Set<String> TRACKING_PARAMS = Set.of(
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "utm_id", "utm_name", "utm_reader", "utm_social", "utm_brand",
        "fbclid", "gclid", "dclid", "msclkid", "yclid", "twclid",
        "mc_cid", "mc_eid", "ref", "referrer", "source", "spm", "from"
    );

    /**
     * Làm sạch text từ feed: bỏ tag HTML, giải entity cơ bản, gộp whitespace.
     *
     * @param maxLength cắt bớt nếu dài hơn; {@code <= 0} nghĩa là không cắt
     */
    public static String clean(String raw, int maxLength) {
        if (raw == null) return null;
        String value = raw;

        // Bỏ CDATA wrapper nếu parser giữ lại.
        value = value.replaceAll("(?s)<!\\[CDATA\\[(.*?)]]>", "$1");
        // Bỏ script/style kèm nội dung trước khi bỏ tag.
        value = value.replaceAll("(?is)<(script|style)[^>]*>.*?</\\1>", " ");
        // Bỏ mọi tag HTML.
        value = value.replaceAll("<[^>]{0,2000}>", " ");
        // Giải entity phổ biến.
        value = value.replace("&nbsp;", " ")
                     .replace("&amp;", "&")
                     .replace("&lt;", "<")
                     .replace("&gt;", ">")
                     .replace("&quot;", "\"")
                     .replace("&#39;", "'")
                     .replace("&apos;", "'");
        // Bỏ entity số còn lại.
        value = value.replaceAll("&#?[a-zA-Z0-9]{1,8};", " ");
        // Gộp whitespace.
        value = value.replaceAll("\\s+", " ").strip();

        if (value.isEmpty()) return null;
        if (maxLength > 0 && value.length() > maxLength) {
            value = value.substring(0, maxLength).strip();
        }
        return value;
    }

    /** Chuẩn hoá Unicode NFC cho hiển thị — giữ dấu tiếng Việt. */
    public static String nfc(String value) {
        return value == null ? null : Normalizer.normalize(value, Normalizer.Form.NFC);
    }

    /**
     * Dạng không dấu, dùng cho so khớp keyword. Không dùng để hiển thị.
     *
     * <p>{@code Đ/đ} (U+0110/U+0111) là chữ cái riêng, NFD không tách thành {@code D}.
     * Phải thay thủ công trước khi bỏ dấu, nếu không "Đà Nẵng" thành "?à Nẵng".
     */
    public static String foldForMatch(String value) {
        if (value == null) return "";
        String replaced = value.replace('Đ', 'D').replace('đ', 'd');
        String decomposed = Normalizer.normalize(replaced, Normalizer.Form.NFD);
        return decomposed.replaceAll("\\p{M}+", "").toLowerCase(Locale.ROOT);
    }

    /**
     * Canonical URL: bỏ tracking params, bỏ fragment, chuẩn hoá scheme/host.
     *
     * @return URL đã chuẩn hoá, hoặc {@code null} nếu không hợp lệ
     */
    public static String canonicalUrl(String raw) {
        if (raw == null || raw.isBlank()) return null;
        URI uri;
        try {
            uri = new URI(raw.strip());
        } catch (URISyntaxException e) {
            return null;
        }
        String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase(Locale.ROOT);
        if (!scheme.equals("http") && !scheme.equals("https")) return null;
        if (uri.getHost() == null || uri.getHost().isBlank()) return null;

        String host = uri.getHost().toLowerCase(Locale.ROOT);
        if (host.startsWith("www.")) host = host.substring(4);
        if (host.endsWith(".")) host = host.substring(0, host.length() - 1);

        String path = uri.getPath() == null || uri.getPath().isEmpty() ? "/" : uri.getPath();
        // Bỏ dấu / cuối thừa (nhưng giữ "/" đơn).
        if (path.length() > 1 && path.endsWith("/")) path = path.substring(0, path.length() - 1);

        String query = filterQuery(uri.getRawQuery());

        StringBuilder out = new StringBuilder();
        out.append(scheme).append("://").append(host);
        if (uri.getPort() != -1 && uri.getPort() != 80 && uri.getPort() != 443) {
            out.append(':').append(uri.getPort());
        }
        out.append(path);
        if (query != null && !query.isEmpty()) out.append('?').append(query);
        return out.toString();
    }

    /** Giữ query param không phải tracking, giữ nguyên thứ tự. */
    private static String filterQuery(String rawQuery) {
        if (rawQuery == null || rawQuery.isBlank()) return null;
        StringBuilder kept = new StringBuilder();
        for (String pair : rawQuery.split("&")) {
            if (pair.isEmpty()) continue;
            int eq = pair.indexOf('=');
            String key = (eq < 0 ? pair : pair.substring(0, eq)).toLowerCase(Locale.ROOT);
            if (TRACKING_PARAMS.contains(key)) continue;
            if (kept.length() > 0) kept.append('&');
            kept.append(pair);
        }
        return kept.length() == 0 ? null : kept.toString();
    }

    /** SHA-256 hex của canonical URL — dùng làm khoá chống trùng. */
    public static String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception e) {
            throw new IllegalStateException("SHA-256 không khả dụng", e);
        }
    }
}
