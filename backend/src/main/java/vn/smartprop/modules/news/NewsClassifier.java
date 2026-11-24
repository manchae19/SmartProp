package vn.smartprop.modules.news;

import java.util.List;
import java.util.Locale;

/**
 * Phân loại bài viết theo luật — deterministic, không dùng LLM.
 *
 * <p>Hai bước:
 * <ol>
 *   <li><b>Liên quan bất động sản?</b> Nếu không, bài bị loại. Không đưa tin xã hội,
 *       thể thao, giải trí vào SmartProp chỉ vì cùng một feed.</li>
 *   <li><b>Chuyên mục + khu vực.</b> Chấm điểm theo cụm từ khoá; không phân loại chỉ
 *       vì một từ chung chung như "cầu" hay "đường" xuất hiện.</li>
 * </ol>
 *
 * <p>Không suy toạ độ GIS, không suy ranh giới thửa đất từ nội dung bài viết.
 */
public final class NewsClassifier {
    private NewsClassifier() {}

    /**
     * Cụm từ cho thấy bài liên quan bất động sản. Cần ít nhất một cụm khớp.
     *
     * <p>Bao gồm cả cụm hạ tầng vì hạ tầng giao thông là chủ đề bất động sản hợp lệ
     * (ảnh hưởng giá đất, quy hoạch). Không đưa từ đơn chung chung như "cầu" hay
     * "đường" vào đây — chỉ cụm đủ nghĩa.
     */
    private static final List<String> RELEVANCE = List.of(
        "bat dong san", "nha dat", "nha o", "chung cu", "can ho", "biet thu",
        "lien ke", "dat nen", "du an", "khu do thi", "quy hoach", "gia dat",
        "gia nha", "thi truong dia oc", "dau tu bat dong san", "phap ly nha dat",
        "so hong", "so do", "giay chung nhan quyen su dung dat", "luat dat dai",
        "giai phong mat bang", "den bu", "thu hoi dat", "cho thue nha", "mat bang",
        "van phong cho thue", "trung tam thuong mai", "ha tang do thi",
        "bat dong san cong nghiep",
        // Hạ tầng giao thông — chủ đề bất động sản hợp lệ khi là cụm đủ nghĩa.
        "cao toc", "san bay", "cang bien", "tuyen duong", "cau vuot",
        "ha tang giao thong", "duong ven bien", "tuyen metro", "duong sat do thi",
        "nang cap quoc lo", "khu cong nghiep", "khu kinh te"
    );

    /** Từ khoá theo chuyên mục. Cụm dài hơn được ưu tiên hơn từ đơn. */
    private static final List<Rule> RULES = List.of(
        new Rule(NewsSource.Category.PLANNING, List.of(
            "quy hoach phan khu", "quy hoach do thi", "dieu chinh quy hoach",
            "ke hoach su dung dat", "quy hoach 1/500", "quy hoach 1/2000",
            "do an quy hoach", "phe duyet quy hoach", "quy hoach chung")),
        new Rule(NewsSource.Category.LEGAL, List.of(
            "luat dat dai", "nghi dinh", "thong tu", "giay chung nhan",
            "quyen su dung dat", "thu tuc phap ly", "so hong", "so do",
            "tranh chap dat dai", "khoi kien", "hop dong mua ban nha")),
        new Rule(NewsSource.Category.INFRASTRUCTURE, List.of(
            "cao toc", "san bay", "cang bien", "tuyen duong", "cau vuot",
            "ha tang giao thong", "ha tang do thi", "duong ven bien",
            "tuyen metro", "duong sat do thi", "nang cap quoc lo")),
        new Rule(NewsSource.Category.PROJECTS, List.of(
            "du an nha o", "khu do thi moi", "du an chung cu", "du an bat dong san",
            "khoi cong du an", "ban giao du an", "chu dau tu du an", "phoi canh du an")),
        new Rule(NewsSource.Category.RESIDENTIAL, List.of(
            "nha o xa hoi", "nha o thuong mai", "chung cu", "can ho",
            "biet thu", "lien ke", "nha pho", "dat nen")),
        new Rule(NewsSource.Category.COMMERCIAL, List.of(
            "mat bang thuong mai", "trung tam thuong mai", "van phong cho thue",
            "bat dong san thuong mai", "shophouse", "condotel")),
        new Rule(NewsSource.Category.MARKET, List.of(
            "gia nha", "gia dat", "nguon cung", "giao dich bat dong san",
            "thanh khoan", "thi truong bat dong san", "bang gia", "chi so gia",
            "luong giao dich", "ton kho bat dong san"))
    );

    /** Địa danh Đà Nẵng — quận, phường tiêu biểu, công trình nhận diện. */
    private static final List<String> DA_NANG = List.of(
        "da nang", "hai chau", "thanh khe", "son tra", "ngu hanh son",
        "lien chieu", "cam le", "hoa vang", "hoang sa",
        "cau rong", "cau song han", "bien my khe", "ban dao son tra",
        "khu cong nghe cao da nang", "san bay da nang", "cang tien sa"
    );

    /** Địa danh miền Trung (không phải Đà Nẵng). */
    private static final List<String> CENTRAL = List.of(
        "quang nam", "hoi an", "quang ngai", "hue", "thua thien hue",
        "binh dinh", "quy nhon", "phu yen", "khanh hoa", "nha trang",
        "quang tri", "quang binh", "ha tinh", "nghe an", "thanh hoa",
        "gia lai", "kon tum", "dak lak", "dak nong", "lam dong", "da lat",
        "mien trung", "mien trung bo", "duyen hai mien trung"
    );

    public record Rule(NewsSource.Category category, List<String> phrases) {}

    public record Classification(boolean relevant, NewsSource.Category category,
                                 NewsSource.Region region, String locationTags) {}

    /**
     * Phân loại một bài.
     *
     * @param title   tiêu đề đã làm sạch
     * @param summary summary đã làm sạch, có thể null
     * @param fallbackCategory chuyên mục mặc định của nguồn
     * @param fallbackRegion   khu vực mặc định của nguồn
     */
    public static Classification classify(String title, String summary,
                                          NewsSource.Category fallbackCategory,
                                          NewsSource.Region fallbackRegion) {
        String haystack = NewsText.foldForMatch(
            (title == null ? "" : title) + " " + (summary == null ? "" : summary));

        if (!isRelevant(haystack)) {
            return new Classification(false, fallbackCategory, fallbackRegion, null);
        }

        NewsSource.Category category = bestCategory(haystack, fallbackCategory);
        RegionResult region = detectRegion(haystack, fallbackRegion);
        return new Classification(true, category, region.region(), region.tags());
    }

    /** Bài có liên quan bất động sản không. */
    static boolean isRelevant(String foldedText) {
        for (String phrase : RELEVANCE) {
            if (foldedText.contains(phrase)) return true;
        }
        return false;
    }

    /** Chọn chuyên mục có nhiều cụm khớp nhất; hoà thì giữ thứ tự ưu tiên trong RULES. */
    static NewsSource.Category bestCategory(String foldedText, NewsSource.Category fallback) {
        NewsSource.Category best = null;
        int bestScore = 0;
        for (Rule rule : RULES) {
            int score = 0;
            for (String phrase : rule.phrases()) {
                if (foldedText.contains(phrase)) score++;
            }
            if (score > bestScore) {
                bestScore = score;
                best = rule.category();
            }
        }
        return best != null ? best : fallback;
    }

    private record RegionResult(NewsSource.Region region, String tags) {}

    static RegionResult detectRegion(String foldedText, NewsSource.Region fallback) {
        StringBuilder tags = new StringBuilder();
        boolean daNang = false;
        for (String place : DA_NANG) {
            if (foldedText.contains(place)) {
                daNang = true;
                if (tags.length() > 0) tags.append(',');
                tags.append(place);
            }
        }
        if (daNang) {
            return new RegionResult(NewsSource.Region.DA_NANG,
                tags.length() > 0 ? tags.toString() : null);
        }
        for (String place : CENTRAL) {
            if (foldedText.contains(place)) {
                return new RegionResult(NewsSource.Region.CENTRAL, place);
            }
        }
        // Không nhận diện được địa danh: dùng mặc định của nguồn, không đoán.
        return new RegionResult(fallback, null);
    }

    /** Nhãn tiếng Việt cho chuyên mục — Frontend PR #37 dùng các nhãn này. */
    public static String categoryLabel(NewsSource.Category category) {
        return switch (category) {
            case MARKET -> "Thị trường BĐS";
            case PLANNING -> "Quy hoạch & hạ tầng";
            case LEGAL -> "Chính sách & pháp lý";
            case PROJECTS -> "Dự án";
            case INFRASTRUCTURE -> "Quy hoạch & hạ tầng";
            case RESIDENTIAL -> "Thị trường BĐS";
            case COMMERCIAL -> "Thị trường BĐS";
            case OTHER -> "Thị trường BĐS";
        };
    }

    /** Nhãn khu vực cho Frontend. */
    public static String regionLabel(NewsSource.Region region) {
        return switch (region) {
            case DA_NANG -> "Đà Nẵng";
            case CENTRAL -> "Miền Trung";
            case VIETNAM -> "Việt Nam";
            case UNKNOWN -> "Không xác định";
        };
    }

    /** Chuẩn hoá category từ query param của Frontend (nhãn tiếng Việt → enum). */
    public static NewsSource.Category parseCategory(String raw) {
        if (raw == null || raw.isBlank()) return null;
        String value = raw.strip();
        if (value.equalsIgnoreCase("Tất cả") || value.equalsIgnoreCase("all")) return null;
        String folded = NewsText.foldForMatch(value);
        if (folded.contains("thi truong")) return NewsSource.Category.MARKET;
        if (folded.contains("quy hoach") || folded.contains("ha tang")) return NewsSource.Category.PLANNING;
        if (folded.contains("chinh sach") || folded.contains("phap ly")) return NewsSource.Category.LEGAL;
        if (folded.contains("du an")) return NewsSource.Category.PROJECTS;
        if (folded.contains("da nang")) return null; // lọc theo khu vực, không theo chuyên mục
        try {
            return NewsSource.Category.valueOf(value.toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException e) {
            return null;
        }
    }
}
