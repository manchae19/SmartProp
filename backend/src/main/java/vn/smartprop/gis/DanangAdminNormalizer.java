package vn.smartprop.gis;

import java.text.Normalizer;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;
import org.springframework.stereotype.Service;
import vn.smartprop.gis.GisDtos.AdminNormalizationResult;
import vn.smartprop.gis.GisDtos.AdminNormalizationStatus;

/**
 * Authoritative Da Nang Administrative Location Normalizer (Step 21.4B).
 *
 * <p>Grounded in official Vietnamese administrative legislation:
 * <ul>
 *   <li>Pre-2024 baseline: 7 mainland districts (56 wards/communes) + Hoàng Sa island district.</li>
 *   <li>Nghị định 24/2005/NĐ-CP (02/03/2005): split former {@code Phường Bắc Mỹ An} (Ngũ Hành Sơn)
 *       into {@code Phường Mỹ An} and {@code Phường Khuê Mỹ}.</li>
 *   <li>Nghị quyết 1251/NQ-UBTVQH15 (24/10/2024, effective 01/01/2025): ward mergers in Hải Châu,
 *       Thanh Khê, and Sơn Trà (reducing 56 to 47 commune-level units).</li>
 *   <li>Nghị quyết 1659/NQ-UBTVQH15 (16/06/2025): 2025 commune-level reorganization, distinguishing
 *       single-district new wards from cross-district merged wards ({@code An Khê}, {@code Hòa Xuân},
 *       {@code Hòa Khánh}, {@code Liên Chiểu}, {@code Hải Vân}).</li>
 *   <li>Post-07/2025 provincial merger guard: distinguishes former Quảng Nam localities ({@code Hội An},
 *       {@code Điện Bàn}, {@code Tam Kỳ}, {@code Núi Thành}, etc.) from the 7 core Da Nang districts.</li>
 * </ul>
 *
 * <p>Strict non-guessing rule: ambiguous cross-district wards, split historical wards, conflicting
 * district-ward pairs, and street-only incomplete addresses are explicitly flagged and never guessed.
 */
@Service
public class DanangAdminNormalizer {

    public static final List<String> CORE_DISTRICTS = List.of(
        "Hải Châu",
        "Thanh Khê",
        "Sơn Trà",
        "Ngũ Hành Sơn",
        "Liên Chiểu",
        "Cẩm Lệ",
        "Hòa Vang"
    );

    private record WardSpec(
        String displayWard,
        String parentDistrict,
        String catalogWard,
        boolean romanVariantAllowed,
        String historicalMergerNote
    ) {}

    private static final Map<String, String> DISTRICT_BY_KEY;
    private static final Map<String, Map<String, WardSpec>> WARDS_BY_DISTRICT;
    private static final Map<String, WardSpec> UNAMBIGUOUS_LEGACY_WARD_LOOKUP;
    private static final Map<String, String> POST_2025_SINGLE_DISTRICT_WARDS;
    private static final Map<String, String> POST_2025_SINGLE_DISTRICT_NOTES;
    private static final Map<String, List<String>> CROSS_DISTRICT_NEW_WARDS;

    private static final Set<String> EXTENDED_QUANG_NAM_KEYS = Set.of(
        "hoi an", "hoi an tay", "hoi an dong", "cam ha", "cam chau", "cam an", "cam thanh", "minh an", "cam pho", "son phong", "tan an", "cua dai",
        "dien ban", "dien ban dong", "dien ban bac", "dien ban tay", "dien ngoc", "dien duong", "dien nam bac", "dien nam trung", "dien nam dong", "dien thang",
        "tam ky", "quang phu", "huong tra", "ban thach",
        "nui thanh", "tam xuan", "tam anh", "tam hai", "tam tien", "tam hiep", "tam nghia",
        "thang binh", "thang an", "thang truong", "thang phu", "thang dien", "ha lam",
        "duy xuyen", "duy nghia", "duy hai", "nam phuoc",
        "dai loc", "ai nghia", "ha nha", "que son", "tien phuoc", "phu ninh",
        "bac tra my", "nam tra my", "hiep duc", "nong son", "dong giang", "tay giang", "nam giang", "phuoc son"
    );

    private static final Set<String> OTHER_PROVINCE_KEYS = Set.of(
        "ha noi", "ho chi minh", "tp ho chi minh", "sai gon", "hai phong", "can tho",
        "thua thien hue", "hue", "quang ngai", "binh dinh", "khanh hoa", "nha trang",
        "binh duong", "dong nai", "ba ria vung tau", "vung tau", "lam dong", "da lat",
        "dak lak", "nghe an", "thanh hoa", "quang binh", "quang tri", "quang ninh", "bac ninh"
    );

    private static final Pattern ADMIN_PREFIX = Pattern.compile(
        "^(?:thanh pho|thi xa|thi tran|huyen dao|tp|tx|tt|quan|huyen|dao|phuong|xa|ward|district|commune|city|province)\\b\\.?\\s+"
        + "|^(?:q|p|h|x)\\.\\s*"
        + "|^(?:q|p)\\s+(?=[a-z0-9])"
    );

    private static final Pattern PROXIMITY_OUTSIDE_DANANG = Pattern.compile(
        "\\b(?:sat|giap|gan)\\s+(?:tp\\s+|thanh pho\\s+)?da nang\\b"
    );

    static {
        Map<String, String> dMap = new LinkedHashMap<>();
        for (String d : CORE_DISTRICTS) {
            dMap.put(asciiFold(d), d);
        }
        DISTRICT_BY_KEY = Map.copyOf(dMap);

        Map<String, Map<String, WardSpec>> byDist = new LinkedHashMap<>();
        for (String d : CORE_DISTRICTS) {
            byDist.put(d, new LinkedHashMap<>());
        }

        // 1. Quận Hải Châu (13 pre-2024 wards + NQ 1251 Phường Hải Châu)
        reg(byDist, "Hải Châu", "Hải Châu I", "Hải Châu I", true,
            "Từ 01/01/2025 (NQ 1251/NQ-UBTVQH15), Hải Châu I và Hải Châu II sáp nhập thành Phường Hải Châu.");
        reg(byDist, "Hải Châu", "Hải Châu II", "Hải Châu II", true,
            "Từ 01/01/2025 (NQ 1251/NQ-UBTVQH15), Hải Châu I và Hải Châu II sáp nhập thành Phường Hải Châu.");
        reg(byDist, "Hải Châu", "Hải Châu", "Hải Châu", false,
            "Phường Hải Châu (NQ 1251/NQ-UBTVQH15 & NQ 1659/NQ-UBTVQH15) thuộc Quận Hải Châu.");
        reg(byDist, "Hải Châu", "Thạch Thang", "Thạch Thang", false, null);
        reg(byDist, "Hải Châu", "Thanh Bình", "Thanh Bình", false, null);
        reg(byDist, "Hải Châu", "Thuận Phước", "Thuận Phước", false, null);
        reg(byDist, "Hải Châu", "Phước Ninh", "Phước Ninh", false, null);
        reg(byDist, "Hải Châu", "Nam Dương", "Phước Ninh", false,
            "Phường Nam Dương cũ sáp nhập vào Phường Phước Ninh từ 01/01/2025 theo NQ 1251/NQ-UBTVQH15.");
        reg(byDist, "Hải Châu", "Bình Hiên", "Bình Hiên", false,
            "Từ 01/01/2025 (NQ 1251/NQ-UBTVQH15), Bình Hiên sáp nhập vào Phường Phước Ninh; vẫn có hồ sơ tiện ích cấp phường riêng.");
        reg(byDist, "Hải Châu", "Bình Thuận", "Bình Thuận", false, null);
        reg(byDist, "Hải Châu", "Hòa Thuận Đông", "Hòa Thuận Đông", false,
            "Từ 01/01/2025 (NQ 1251/NQ-UBTVQH15), Hòa Thuận Đông sáp nhập vào Phường Bình Thuận; vẫn có hồ sơ tiện ích cấp phường riêng.");
        reg(byDist, "Hải Châu", "Hòa Thuận Tây", "Hòa Thuận Tây", false, null);
        reg(byDist, "Hải Châu", "Hòa Cường Bắc", "Hòa Cường Bắc", false, null);
        reg(byDist, "Hải Châu", "Hòa Cường Nam", "Hòa Cường Nam", false, null);

        // 2. Quận Thanh Khê (10 pre-2024 wards)
        reg(byDist, "Thanh Khê", "Tam Thuận", "Xuân Hà", false,
            "Phường Tam Thuận cũ sáp nhập vào Phường Xuân Hà từ 01/01/2025 theo NQ 1251/NQ-UBTVQH15.");
        reg(byDist, "Thanh Khê", "Xuân Hà", "Xuân Hà", false, null);
        reg(byDist, "Thanh Khê", "Tân Chính", "Chính Gián", false,
            "Phường Tân Chính cũ sáp nhập vào Phường Chính Gián từ 01/01/2025 theo NQ 1251/NQ-UBTVQH15.");
        reg(byDist, "Thanh Khê", "Chính Gián", "Chính Gián", false, null);
        reg(byDist, "Thanh Khê", "Vĩnh Trung", "Vĩnh Trung", false,
            "Từ 01/01/2025 (NQ 1251/NQ-UBTVQH15), Vĩnh Trung sáp nhập vào Phường Thạc Gián; vẫn có hồ sơ tiện ích cấp phường riêng.");
        reg(byDist, "Thanh Khê", "Thạc Gián", "Thạc Gián", false, null);
        reg(byDist, "Thanh Khê", "Hòa Khê", "Hòa Khê", false,
            "Từ 01/01/2025 (NQ 1251/NQ-UBTVQH15), Hòa Khê sáp nhập vào Phường Thanh Khê Đông; vẫn có hồ sơ tiện ích cấp phường riêng.");
        reg(byDist, "Thanh Khê", "Thanh Khê Đông", "Thanh Khê Đông", false, null);
        reg(byDist, "Thanh Khê", "Thanh Khê Tây", "Thanh Khê Tây", false, null);
        reg(byDist, "Thanh Khê", "An Khê", "An Khê", false, null);

        // 3. Quận Sơn Trà (7 pre-2024 wards + NQ 1251 An Hải Nam)
        reg(byDist, "Sơn Trà", "Thọ Quang", "Thọ Quang", false, null);
        reg(byDist, "Sơn Trà", "Nại Hiên Đông", "Nại Hiên Đông", false, null);
        reg(byDist, "Sơn Trà", "Mân Thái", "Mân Thái", false, null);
        reg(byDist, "Sơn Trà", "An Hải Bắc", "An Hải Bắc", false, null);
        reg(byDist, "Sơn Trà", "Phước Mỹ", "Phước Mỹ", false, null);
        reg(byDist, "Sơn Trà", "An Hải Đông", "An Hải Đông", false,
            "Từ 01/01/2025 (NQ 1251/NQ-UBTVQH15), An Hải Đông và An Hải Tây sáp nhập thành Phường An Hải Nam.");
        reg(byDist, "Sơn Trà", "An Hải Tây", "An Hải Tây", false,
            "Từ 01/01/2025 (NQ 1251/NQ-UBTVQH15), An Hải Đông và An Hải Tây sáp nhập thành Phường An Hải Nam.");
        reg(byDist, "Sơn Trà", "An Hải Nam", "An Hải Nam", false,
            "Phường An Hải Nam được thành lập từ An Hải Đông và An Hải Tây theo NQ 1251/NQ-UBTVQH15.");

        // 4. Quận Ngũ Hành Sơn (4 pre-2025 wards)
        reg(byDist, "Ngũ Hành Sơn", "Mỹ An", "Mỹ An", false, null);
        reg(byDist, "Ngũ Hành Sơn", "Khuê Mỹ", "Khuê Mỹ", false, null);
        reg(byDist, "Ngũ Hành Sơn", "Hòa Hải", "Hòa Hải", false, null);
        reg(byDist, "Ngũ Hành Sơn", "Hòa Quý", "Hòa Quý", false, null);

        // 5. Quận Liên Chiểu (5 pre-2025 wards)
        reg(byDist, "Liên Chiểu", "Hòa Hiệp Bắc", "Hòa Hiệp Bắc", false, null);
        reg(byDist, "Liên Chiểu", "Hòa Hiệp Nam", "Hòa Hiệp Nam", false, null);
        reg(byDist, "Liên Chiểu", "Hòa Khánh Bắc", "Hòa Khánh Bắc", false, null);
        reg(byDist, "Liên Chiểu", "Hòa Khánh Nam", "Hòa Khánh Nam", false, null);
        reg(byDist, "Liên Chiểu", "Hòa Minh", "Hòa Minh", false, null);

        // 6. Quận Cẩm Lệ (6 pre-2025 wards)
        reg(byDist, "Cẩm Lệ", "Khuê Trung", "Khuê Trung", false, null);
        reg(byDist, "Cẩm Lệ", "Hòa Phát", "Hòa Phát", false, null);
        reg(byDist, "Cẩm Lệ", "Hòa An", "Hòa An", false, null);
        reg(byDist, "Cẩm Lệ", "Hòa Thọ Tây", "Hòa Thọ Tây", false, null);
        reg(byDist, "Cẩm Lệ", "Hòa Thọ Đông", "Hòa Thọ Đông", false, null);
        reg(byDist, "Cẩm Lệ", "Hòa Xuân", "Hòa Xuân", false, null);

        // 7. Huyện Hòa Vang (11 pre-2025 communes)
        reg(byDist, "Hòa Vang", "Hòa Bắc", "Hòa Bắc", false, null);
        reg(byDist, "Hòa Vang", "Hòa Liên", "Hòa Liên", false, null);
        reg(byDist, "Hòa Vang", "Hòa Ninh", "Hòa Ninh", false, null);
        reg(byDist, "Hòa Vang", "Hòa Sơn", "Hòa Sơn", false, null);
        reg(byDist, "Hòa Vang", "Hòa Nhơn", "Hòa Nhơn", false, null);
        reg(byDist, "Hòa Vang", "Hòa Phú", "Hòa Phú", false, null);
        reg(byDist, "Hòa Vang", "Hòa Phong", "Hòa Phong", false, null);
        reg(byDist, "Hòa Vang", "Hòa Châu", "Hòa Châu", false, null);
        reg(byDist, "Hòa Vang", "Hòa Tiến", "Hòa Tiến", false, null);
        reg(byDist, "Hòa Vang", "Hòa Phước", "Hòa Phước", false, null);
        reg(byDist, "Hòa Vang", "Hòa Khương", "Hòa Khương", false, null);

        Map<String, Map<String, WardSpec>> immutableByDist = new LinkedHashMap<>();
        byDist.forEach((k, v) -> immutableByDist.put(k, Map.copyOf(v)));
        WARDS_BY_DISTRICT = Map.copyOf(immutableByDist);

        // Cross-district post-2025 wards under NQ 1659/NQ-UBTVQH15 (cannot infer single district without context)
        CROSS_DISTRICT_NEW_WARDS = Map.of(
            "an khe", List.of("Thanh Khê", "Cẩm Lệ"),
            "hoa xuan", List.of("Cẩm Lệ", "Hòa Vang"),
            "hoa khanh", List.of("Liên Chiểu", "Hòa Vang"),
            "lien chieu", List.of("Liên Chiểu", "Hòa Vang"),
            "hai van", List.of("Liên Chiểu", "Hòa Vang")
        );

        // Post-2025 NQ 1659 single-district wards/communes (map uniquely to 1 historical district, multi-ward scope)
        Map<String, String> postSingle = new LinkedHashMap<>();
        Map<String, String> postNotes = new LinkedHashMap<>();
        postSingle.put("hoa cuong", "Hải Châu");
        postNotes.put("hoa cuong", "Phường Hòa Cường mới (NQ 1659/NQ-UBTVQH15) gộp Bình Thuận, Hòa Thuận Tây, Hòa Cường Bắc, Hòa Cường Nam (Quận Hải Châu cũ) — dùng hồ sơ cấp Quận Hải Châu thay vì tự gán một phường cũ.");

        postSingle.put("thanh khe", "Thanh Khê");
        postNotes.put("thanh khe", "Phường Thanh Khê mới (NQ 1659/NQ-UBTVQH15) gộp Xuân Hà, Chính Gián, Thạc Gián, Thanh Khê Tây, Thanh Khê Đông (Quận Thanh Khê cũ) — dùng hồ sơ cấp Quận Thanh Khê.");

        postSingle.put("an hai", "Sơn Trà");
        postNotes.put("an hai", "Phường An Hải mới (NQ 1659/NQ-UBTVQH15) gộp Phước Mỹ, An Hải Bắc, An Hải Nam (Quận Sơn Trà cũ) — dùng hồ sơ cấp Quận Sơn Trà.");

        postSingle.put("son tra", "Sơn Trà");
        postNotes.put("son tra", "Phường Sơn Trà mới (NQ 1659/NQ-UBTVQH15) gộp Thọ Quang, Nại Hiên Đông, Mân Thái (Quận Sơn Trà cũ) — dùng hồ sơ cấp Quận Sơn Trà.");

        postSingle.put("ngu hanh son", "Ngũ Hành Sơn");
        postNotes.put("ngu hanh son", "Phường Ngũ Hành Sơn mới (NQ 1659/NQ-UBTVQH15) tương đương toàn bộ 4 phường Mỹ An, Khuê Mỹ, Hòa Hải, Hòa Quý của Quận Ngũ Hành Sơn cũ.");

        postSingle.put("cam le", "Cẩm Lệ");
        postNotes.put("cam le", "Phường Cẩm Lệ mới (NQ 1659/NQ-UBTVQH15) gộp Hòa Thọ Tây, Hòa Thọ Đông, Khuê Trung (Quận Cẩm Lệ cũ) — dùng hồ sơ cấp Quận Cẩm Lệ.");

        postSingle.put("hoa vang", "Hòa Vang");
        postNotes.put("hoa vang", "Xã Hòa Vang mới (NQ 1659/NQ-UBTVQH15) gộp Hòa Phong và Hòa Phú (Huyện Hòa Vang cũ) — dùng hồ sơ cấp Huyện Hòa Vang.");

        postSingle.put("ba na", "Hòa Vang");
        postNotes.put("ba na", "Xã Bà Nà mới (NQ 1659/NQ-UBTVQH15) gộp Hòa Ninh và Hòa Nhơn (Huyện Hòa Vang cũ) — dùng hồ sơ cấp Huyện Hòa Vang.");

        POST_2025_SINGLE_DISTRICT_WARDS = Map.copyOf(postSingle);
        POST_2025_SINGLE_DISTRICT_NOTES = Map.copyOf(postNotes);

        // Unambiguous ward -> district lookup (excludes cross-district NQ 1659 names and NQ 1659 Hòa Tiến which merged Hòa Khương)
        Map<String, WardSpec> unambig = new LinkedHashMap<>();
        for (var dEntry : WARDS_BY_DISTRICT.entrySet()) {
            for (var wEntry : dEntry.getValue().entrySet()) {
                String wk = wEntry.getKey();
                if (!CROSS_DISTRICT_NEW_WARDS.containsKey(wk) && !"hoa tien".equals(wk)) {
                    unambig.put(wk, wEntry.getValue());
                }
            }
        }
        UNAMBIGUOUS_LEGACY_WARD_LOOKUP = Map.copyOf(unambig);
    }

    private static void reg(
            Map<String, Map<String, WardSpec>> byDist,
            String district,
            String displayWard,
            String catalogWard,
            boolean romanVariant,
            String note) {
        WardSpec spec = new WardSpec(displayWard, district, catalogWard, romanVariant, note);
        Map<String, WardSpec> map = byDist.get(district);
        String baseKey = stripPrefix(asciiFold(displayWard));
        map.put(baseKey, spec);
        if (romanVariant && baseKey.endsWith(" ii")) {
            String stem = baseKey.substring(0, baseKey.length() - 3);
            map.put(stem + " 2", spec);
            map.put(stem + " 02", spec);
        } else if (romanVariant && baseKey.endsWith(" i")) {
            String stem = baseKey.substring(0, baseKey.length() - 2);
            map.put(stem + " 1", spec);
            map.put(stem + " 01", spec);
        }
    }

    /**
     * Normalizes structured (district, ward, city) administrative fields without guessing.
     */
    public AdminNormalizationResult normalize(String rawDistrict, String rawWard, String rawCity) {
        String cityFold = stripPrefix(asciiFold(rawCity));
        if (!cityFold.isEmpty() && !isDanangCityKey(cityFold)) {
            if ("quang nam".equals(cityFold)) {
                return new AdminNormalizationResult(
                    AdminNormalizationStatus.EXTENDED_QUANG_NAM_JURISDICTION,
                    null, cleanText(rawWard), null,
                    cleanText(rawCity),
                    List.of(),
                    "Thuộc tỉnh Quảng Nam cũ; nằm ngoài 7 quận/huyện Đà Nẵng lịch sử của danh mục tiện ích V1 và mô hình V6."
                );
            }
            return new AdminNormalizationResult(
                AdminNormalizationStatus.OUTSIDE_DANANG,
                null, null, null,
                cleanText(rawCity),
                List.of(),
                "Địa phương '" + cleanText(rawCity) + "' nằm ngoài phạm vi thành phố Đà Nẵng."
            );
        }

        String dKey = stripPrefix(asciiFold(rawDistrict));
        String wKey = stripPrefix(asciiFold(rawWard));

        // Guard Hoàng Sa island district
        if ("hoang sa".equals(dKey) || "hoang sa".equals(wKey)) {
            return new AdminNormalizationResult(
                AdminNormalizationStatus.EXCLUDED_ISLAND_DISTRICT,
                null, null, null,
                "Huyện đảo Hoàng Sa, Đà Nẵng",
                List.of(),
                "Huyện đảo Hoàng Sa không có đơn vị hành chính cấp xã dân cư và không áp dụng tư vấn bất động sản dân dụng."
            );
        }

        // Guard former Quảng Nam localities (post-07/2025 provincial merger)
        if (isQuangNamKey(dKey) || isQuangNamKey(wKey)) {
            String label = !cleanText(rawWard).isEmpty() && !cleanText(rawDistrict).isEmpty()
                ? cleanText(rawWard) + ", " + cleanText(rawDistrict)
                : (!cleanText(rawDistrict).isEmpty() ? cleanText(rawDistrict) : cleanText(rawWard));
            return new AdminNormalizationResult(
                AdminNormalizationStatus.EXTENDED_QUANG_NAM_JURISDICTION,
                null, cleanTextOrNull(rawWard), null,
                label,
                List.of(),
                "Đơn vị hành chính thuộc địa bàn Quảng Nam cũ sáp nhập sau 07/2025; chưa thuộc 7 quận/huyện Đà Nẵng lịch sử của danh mục tiện ích V1 và mô hình định giá V6."
            );
        }

        // Guard other Vietnamese provinces accidentally placed in district/ward
        if (OTHER_PROVINCE_KEYS.contains(dKey) || OTHER_PROVINCE_KEYS.contains(wKey)) {
            return new AdminNormalizationResult(
                AdminNormalizationStatus.OUTSIDE_DANANG,
                null, null, null,
                !cleanText(rawDistrict).isEmpty() ? cleanText(rawDistrict) : cleanText(rawWard),
                List.of(),
                "Địa danh nằm ngoài phạm vi thành phố Đà Nẵng."
            );
        }

        // Both blank -> incomplete location
        if (dKey.isEmpty() && wKey.isEmpty()) {
            return new AdminNormalizationResult(
                AdminNormalizationStatus.INCOMPLETE_LOCATION,
                null, null, null,
                "Chưa xác định quận/phường tại Đà Nẵng",
                List.of(),
                "Thiếu thông tin quận/huyện và phường/xã; hệ thống không tự suy đoán địa bàn."
            );
        }

        String canonicalDistrict = dKey.isEmpty() ? null : DISTRICT_BY_KEY.get(dKey);
        if (!dKey.isEmpty() && canonicalDistrict == null) {
            // Check if user put a post-2025 ward or legacy ward inside the district field!
            if (wKey.isEmpty()) {
                return resolveBareWardOrUnknown(dKey, cleanText(rawDistrict), false);
            }
            return new AdminNormalizationResult(
                AdminNormalizationStatus.INCOMPLETE_LOCATION,
                null, cleanTextOrNull(rawWard), null,
                cleanText(rawDistrict),
                List.of(),
                "Không nhận diện được quận/huyện '" + cleanText(rawDistrict) + "' trong 7 quận/huyện Đà Nẵng lịch sử."
            );
        }

        // District is known, Ward is blank -> RESOLVED_DISTRICT_ONLY
        if (wKey.isEmpty()) {
            return new AdminNormalizationResult(
                AdminNormalizationStatus.RESOLVED_DISTRICT_ONLY,
                canonicalDistrict,
                null,
                null,
                districtDisplayLabel(canonicalDistrict) + ", Đà Nẵng",
                List.of(),
                null
            );
        }

        // Special historical split ward: Bắc Mỹ An (NĐ 24/2005/NĐ-CP -> Mỹ An + Khuê Mỹ in Ngũ Hành Sơn)
        if ("bac my an".equals(wKey)) {
            if (canonicalDistrict != null && !"Ngũ Hành Sơn".equals(canonicalDistrict)) {
                return conflictResult(canonicalDistrict, cleanText(rawWard), "Ngũ Hành Sơn");
            }
            return new AdminNormalizationResult(
                AdminNormalizationStatus.HISTORICAL_SPLIT_WARD_AMBIGUOUS,
                "Ngũ Hành Sơn",
                "Bắc Mỹ An (cũ)",
                null,
                "Khu vực Bắc Mỹ An cũ, Quận Ngũ Hành Sơn, Đà Nẵng",
                List.of("Ngũ Hành Sơn"),
                "Phường Bắc Mỹ An cũ (Nghị định 24/2005/NĐ-CP) đã tách thành Phường Mỹ An và Phường Khuê Mỹ; giữ cấp Quận Ngũ Hành Sơn, không tự suy đoán một trong hai phường."
            );
        }

        // Case A: Both canonicalDistrict and ward are provided
        if (canonicalDistrict != null) {
            Map<String, WardSpec> districtWards = WARDS_BY_DISTRICT.get(canonicalDistrict);
            WardSpec matched = districtWards == null ? null : districtWards.get(wKey);
            if (matched != null) {
                boolean romanConverted = matched.romanVariantAllowed()
                    && (wKey.endsWith(" 1") || wKey.endsWith(" 01") || wKey.endsWith(" 2") || wKey.endsWith(" 02"));
                boolean mergedBridge = !matched.displayWard().equals(matched.catalogWard());
                AdminNormalizationStatus st = mergedBridge
                    ? AdminNormalizationStatus.RESOLVED_HISTORICAL_MERGED_WARD
                    : (romanConverted ? AdminNormalizationStatus.RESOLVED_ROMAN_VARIANT : AdminNormalizationStatus.RESOLVED_CANONICAL);
                String note = matched.historicalMergerNote();
                if (romanConverted) {
                    String romanNote = "Chuẩn hóa chữ số '" + cleanText(rawWard) + "' thành '" + matched.displayWard() + "' theo danh mục hành chính Đà Nẵng.";
                    note = note == null ? romanNote : romanNote + " " + note;
                }
                return new AdminNormalizationResult(
                    st,
                    canonicalDistrict,
                    matched.displayWard(),
                    matched.catalogWard(),
                    wardPrefix(canonicalDistrict) + " " + matched.displayWard() + ", " + districtDisplayLabel(canonicalDistrict) + ", Đà Nẵng",
                    List.of(),
                    note
                );
            }

            // Check if ward is a valid post-2025 NQ 1659 new ward belonging to (or spanning into) canonicalDistrict
            String singlePostDist = POST_2025_SINGLE_DISTRICT_WARDS.get(wKey);
            if (canonicalDistrict.equals(singlePostDist)) {
                return new AdminNormalizationResult(
                    AdminNormalizationStatus.RESOLVED_POST_2025_NEW_WARD,
                    canonicalDistrict,
                    cleanText(rawWard),
                    null,
                    wardPrefix(canonicalDistrict) + " " + cleanText(rawWard) + " (mới), " + districtDisplayLabel(canonicalDistrict) + ", Đà Nẵng",
                    List.of(),
                    POST_2025_SINGLE_DISTRICT_NOTES.get(wKey)
                );
            }
            List<String> crossDists = CROSS_DISTRICT_NEW_WARDS.get(wKey);
            if (crossDists != null && crossDists.contains(canonicalDistrict)) {
                return new AdminNormalizationResult(
                    AdminNormalizationStatus.RESOLVED_POST_2025_NEW_WARD,
                    canonicalDistrict,
                    cleanText(rawWard),
                    null,
                    "Phường " + cleanText(rawWard) + " (phần thuộc " + districtDisplayLabel(canonicalDistrict) + "), Đà Nẵng",
                    crossDists,
                    "Đơn vị hành chính mới '" + cleanText(rawWard) + "' (NQ 1659/NQ-UBTVQH15) trải trên "
                        + String.join(" & ", crossDists) + "; giữ đúng địa bàn " + canonicalDistrict + " đã khai báo ở cấp quận/huyện."
                );
            }

            // Check if wKey actually belongs to ANOTHER Da Nang district -> CONFLICTING_ADMIN_HIERARCHY!
            String actualOwner = findOwningDistrictForWardKey(wKey);
            if (actualOwner != null && !actualOwner.equals(canonicalDistrict)) {
                return conflictResult(canonicalDistrict, cleanText(rawWard), actualOwner);
            }

            // Unknown ward within valid Da Nang district -> fall back safely to canonicalDistrict without inventing ward
            return new AdminNormalizationResult(
                AdminNormalizationStatus.RESOLVED_DISTRICT_ONLY,
                canonicalDistrict,
                null,
                null,
                districtDisplayLabel(canonicalDistrict) + ", Đà Nẵng",
                List.of(),
                "Phường/xã '" + cleanText(rawWard) + "' không khớp danh mục chuẩn của " + districtDisplayLabel(canonicalDistrict)
                    + "; chỉ sử dụng dữ liệu cấp quận/huyện, không tự suy đoán phường."
            );
        }

        // Case B: Ward is provided WITHOUT district
        return resolveBareWardOrUnknown(wKey, cleanText(rawWard), true);
    }

    /**
     * Parses and normalizes a free-text address combined with optional district/ward/city inputs.
     * Refuses to guess district/ward from street-only text (e.g. "123 Nguyễn Văn Linh").
     */
    public AdminNormalizationResult normalizeAddress(
            String rawAddress,
            String rawDistrict,
            String rawWard,
            String rawCity) {

        String addr = cleanText(rawAddress);
        String addrFold = asciiFold(addr);

        // Guard explicit proximity outside Da Nang ("Sát Đà Nẵng, Điện Bàn, Quảng Nam")
        if (PROXIMITY_OUTSIDE_DANANG.matcher(addrFold).find()) {
            return new AdminNormalizationResult(
                AdminNormalizationStatus.OUTSIDE_DANANG,
                null, null, null,
                addr,
                List.of(),
                "Địa chỉ mô tả vị trí giáp/sát Đà Nẵng chứ không thuộc địa giới hành chính Đà Nẵng."
            );
        }

        String extractedDistrict = cleanText(rawDistrict);
        String extractedWard = cleanText(rawWard);
        String extractedCity = cleanText(rawCity);

        if (!addr.isEmpty()) {
            String[] parts = addr.split(",");
            // Check tail segment for explicit non-Da-Nang province (e.g. "Đường Đà Nẵng, Ngô Quyền, Hải Phòng")
            if (parts.length >= 2 && extractedCity.isEmpty()) {
                String tail = parts[parts.length - 1].strip();
                String tailKey = stripPrefix(asciiFold(tail));
                if (OTHER_PROVINCE_KEYS.contains(tailKey) || "quang nam".equals(tailKey)) {
                    extractedCity = tail;
                } else if (isDanangCityKey(tailKey)) {
                    extractedCity = "Đà Nẵng";
                }
            }

            List<String> explicitDistricts = new ArrayList<>();
            List<String> explicitWards = new ArrayList<>();
            for (String rawPart : parts) {
                String part = rawPart.strip();
                if (part.isEmpty()) continue;
                String lowerFold = asciiFold(part);
                if (lowerFold.matches("^(?:quan|q|huyen|h|thi xa|tx)\\b\\.?\\s+.+")) {
                    explicitDistricts.add(part);
                } else if (lowerFold.matches("^(?:phuong|p|xa|x|thi tran|tt)\\b\\.?\\s+.+")) {
                    explicitWards.add(part);
                } else if (isQuangNamKey(stripPrefix(lowerFold)) && explicitDistricts.isEmpty() && extractedDistrict.isEmpty()) {
                    explicitDistricts.add(part);
                }
            }

            if (explicitDistricts.size() > 1) {
                return new AdminNormalizationResult(
                    AdminNormalizationStatus.CONFLICTING_ADMIN_HIERARCHY,
                    null, null, null,
                    addr,
                    List.of(),
                    "Địa chỉ chứa nhiều tên quận/huyện khác nhau; không tự chọn địa bàn."
                );
            }
            if (explicitWards.size() > 1) {
                return new AdminNormalizationResult(
                    AdminNormalizationStatus.CONFLICTING_ADMIN_HIERARCHY,
                    null, null, null,
                    addr,
                    List.of(),
                    "Địa chỉ chứa nhiều tên phường/xã khác nhau; không tự chọn phường/xã."
                );
            }
            if (extractedDistrict.isEmpty() && explicitDistricts.size() == 1) {
                extractedDistrict = explicitDistricts.getFirst();
            }
            if (extractedWard.isEmpty() && explicitWards.size() == 1) {
                extractedWard = explicitWards.getFirst();
            }

            // Also inspect comma-separated administrative segments (excluding street segment index 0) when prefixes are omitted
            if (extractedDistrict.isEmpty() && extractedWard.isEmpty() && parts.length >= 2) {
                for (int i = parts.length - 1; i >= 1; i--) {
                    String seg = parts[i].strip();
                    String segKey = stripPrefix(asciiFold(seg));
                    if (isDanangCityKey(segKey) || "viet nam".equals(segKey) || "vn".equals(segKey)) continue;
                    if (extractedDistrict.isEmpty() && DISTRICT_BY_KEY.containsKey(segKey)) {
                        extractedDistrict = seg;
                    } else if (extractedDistrict.isEmpty() && isQuangNamKey(segKey)) {
                        extractedDistrict = seg;
                    } else if (extractedWard.isEmpty() && (UNAMBIGUOUS_LEGACY_WARD_LOOKUP.containsKey(segKey)
                            || CROSS_DISTRICT_NEW_WARDS.containsKey(segKey)
                            || POST_2025_SINGLE_DISTRICT_WARDS.containsKey(segKey)
                            || "bac my an".equals(segKey))) {
                        extractedWard = seg;
                    }
                }
            }
        }

        return normalize(extractedDistrict, extractedWard, extractedCity);
    }

    private AdminNormalizationResult resolveBareWardOrUnknown(String key, String rawLabel, boolean fromWardField) {
        // 1. Cross-district NQ 1659 wards MUST NOT be guessed without historical district!
        List<String> crossDists = CROSS_DISTRICT_NEW_WARDS.get(key);
        if (crossDists != null) {
            return new AdminNormalizationResult(
                AdminNormalizationStatus.AMBIGUOUS_CROSS_DISTRICT_WARD,
                null,
                rawLabel,
                null,
                rawLabel + " (chưa rõ quận/huyện lịch sử)",
                crossDists,
                "Địa danh '" + rawLabel + "' theo NQ 1659/NQ-UBTVQH15 trải trên "
                    + String.join(" và ", crossDists)
                    + "; cần chỉ rõ quận/huyện lịch sử hoặc tọa độ xác thực, không tự suy đoán."
            );
        }

        // 2. Hòa Tiến without explicit Huyện Hòa Vang: still uniquely inside Hòa Vang, but spans Hòa Tiến + Hòa Khương under NQ 1659
        if ("hoa tien".equals(key)) {
            return new AdminNormalizationResult(
                AdminNormalizationStatus.RESOLVED_POST_2025_NEW_WARD,
                "Hòa Vang",
                "Hòa Tiến",
                null,
                "Xã Hòa Tiến, Huyện Hòa Vang, Đà Nẵng",
                List.of("Hòa Vang"),
                "Xã Hòa Tiến khi không ghi kèm địa giới cũ có thể là Xã Hòa Tiến mới (gộp Hòa Tiến & Hòa Khương theo NQ 1659/NQ-UBTVQH15) — dùng hồ sơ cấp Huyện Hòa Vang."
            );
        }

        // 3. Unambiguous pre-2025 ward (incl. Hải Châu 1/2 Roman variants and NQ 1251 wards)
        WardSpec unambig = UNAMBIGUOUS_LEGACY_WARD_LOOKUP.get(key);
        if (unambig != null) {
            String note = "Xác định quận/huyện '" + unambig.parentDistrict() + "' từ phường/xã đơn trị '" + unambig.displayWard() + "'.";
            if (unambig.historicalMergerNote() != null) {
                note = note + " " + unambig.historicalMergerNote();
            }
            return new AdminNormalizationResult(
                AdminNormalizationStatus.RESOLVED_WARD_INFERRED_DISTRICT,
                unambig.parentDistrict(),
                unambig.displayWard(),
                unambig.catalogWard(),
                wardPrefix(unambig.parentDistrict()) + " " + unambig.displayWard() + ", "
                    + districtDisplayLabel(unambig.parentDistrict()) + ", Đà Nẵng",
                List.of(),
                note
            );
        }

        // 4. Single-district post-2025 NQ 1659 new ward/commune (e.g. Hòa Cường, An Hải, Bà Nà, Ngũ Hành Sơn)
        String singlePostDist = POST_2025_SINGLE_DISTRICT_WARDS.get(key);
        if (singlePostDist != null) {
            return new AdminNormalizationResult(
                AdminNormalizationStatus.RESOLVED_POST_2025_NEW_WARD,
                singlePostDist,
                rawLabel,
                null,
                wardPrefix(singlePostDist) + " " + rawLabel + " (mới), " + districtDisplayLabel(singlePostDist) + ", Đà Nẵng",
                List.of(singlePostDist),
                POST_2025_SINGLE_DISTRICT_NOTES.get(key)
            );
        }

        return new AdminNormalizationResult(
            AdminNormalizationStatus.INCOMPLETE_LOCATION,
            null,
            fromWardField ? rawLabel : null,
            null,
            rawLabel.isEmpty() ? "Chưa xác định địa bàn Đà Nẵng" : rawLabel,
            List.of(),
            "Không thể xác định đơn trị quận/huyện Đà Nẵng từ '" + rawLabel + "'; hệ thống không tự suy đoán."
        );
    }

    private static AdminNormalizationResult conflictResult(String declaredDistrict, String rawWard, String trueOwnerDistrict) {
        return new AdminNormalizationResult(
            AdminNormalizationStatus.CONFLICTING_ADMIN_HIERARCHY,
            null,
            rawWard,
            null,
            rawWard + " ≠ " + declaredDistrict,
            List.of(declaredDistrict, trueOwnerDistrict),
            "Mâu thuẫn hành chính: '" + rawWard + "' thuộc " + districtDisplayLabel(trueOwnerDistrict)
                + ", không thuộc " + districtDisplayLabel(declaredDistrict) + "."
        );
    }

    private static String findOwningDistrictForWardKey(String wardKey) {
        for (var entry : WARDS_BY_DISTRICT.entrySet()) {
            if (entry.getValue().containsKey(wardKey)) {
                return entry.getKey();
            }
        }
        return POST_2025_SINGLE_DISTRICT_WARDS.get(wardKey);
    }

    private static boolean isDanangCityKey(String key) {
        return key.isEmpty()
            || "da nang".equals(key)
            || "thanh pho da nang".equals(key)
            || "tp da nang".equals(key)
            || "danang".equals(key);
    }

    private static boolean isQuangNamKey(String key) {
        if (key == null || key.isEmpty()) return false;
        if (EXTENDED_QUANG_NAM_KEYS.contains(key)) return true;
        return key.startsWith("hoi an ")
            || key.startsWith("dien ban ")
            || key.startsWith("tam ky ")
            || key.startsWith("nui thanh ")
            || key.startsWith("thang binh ")
            || key.startsWith("duy xuyen ")
            || key.startsWith("dai loc ");
    }

    public static String districtDisplayLabel(String canonicalDistrict) {
        if (canonicalDistrict == null || canonicalDistrict.isBlank()) return "Đà Nẵng";
        return "Hòa Vang".equals(canonicalDistrict)
            ? "Huyện Hòa Vang"
            : "Quận " + canonicalDistrict;
    }

    public static String wardPrefix(String canonicalDistrict) {
        return "Hòa Vang".equals(canonicalDistrict) ? "Xã" : "Phường";
    }

    public static String asciiFold(String raw) {
        if (raw == null) return "";
        String nfd = Normalizer.normalize(raw, Normalizer.Form.NFD)
            .replaceAll("\\p{M}+", "")
            .replace('đ', 'd')
            .replace('Đ', 'd')
            .toLowerCase(Locale.ROOT);
        return nfd.replaceAll("[^a-z0-9. ]", " ").replaceAll("\\s+", " ").strip();
    }

    public static String stripPrefix(String folded) {
        if (folded == null || folded.isEmpty()) return "";
        String cur = folded.strip();
        for (int i = 0; i < 2; i++) {
            String next = ADMIN_PREFIX.matcher(cur).replaceFirst("").replace('.', ' ').replaceAll("\\s+", " ").strip();
            if (next.equals(cur)) break;
            cur = next;
        }
        return cur;
    }

    private static String cleanText(String raw) {
        if (raw == null) return "";
        String t = Normalizer.normalize(raw.strip(), Normalizer.Form.NFC).replaceAll("\\s+", " ");
        if ("null".equalsIgnoreCase(t) || "nan".equalsIgnoreCase(t) || "none".equalsIgnoreCase(t)) return "";
        return t;
    }

    private static String cleanTextOrNull(String raw) {
        String c = cleanText(raw);
        return c.isEmpty() ? null : c;
    }
}
