package vn.smartprop.gis;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.regex.Pattern;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.lang.Nullable;
import org.springframework.stereotype.Service;
import vn.smartprop.modules.amenity.AmenityCatalogService;
import vn.smartprop.modules.amenity.AmenityDtos.AmenityProfile;
import vn.smartprop.modules.amenity.AmenityDtos.CategoryScores;
import vn.smartprop.modules.amenity.AmenityDtos.PoiCounts;
import vn.smartprop.gis.AdvisorPoiSpatialRepository.RawPropertyCoordinate;
import vn.smartprop.gis.GisDtos.AdminNormalizationResult;
import vn.smartprop.gis.GisDtos.AdminNormalizationStatus;
import vn.smartprop.gis.GisDtos.AreaPurposeInsight;
import vn.smartprop.gis.GisDtos.CoordinateValidationResult;
import vn.smartprop.gis.GisDtos.LocationIntelligence;
import vn.smartprop.gis.GisDtos.NearbyPoiItem;
import vn.smartprop.gis.GisDtos.PurposeLocationFit;
import vn.smartprop.modules.recommendation.AmenityEvidenceService;
import vn.smartprop.modules.recommendation.PropertyLocationResolver;
import vn.smartprop.modules.recommendation.RecommendationDtos.AmenityEvidence;
import vn.smartprop.modules.recommendation.RecommendationDtos.AreaResult;
import vn.smartprop.modules.recommendation.RecommendationDtos.PropertyResult;
import vn.smartprop.modules.recommendation.RecommendationDtos.Purpose;

/**
 * Step 21.4C — Location Intelligence & Purpose-Aware Spatial Explanation Service for AI Advisor.
 *
 * <p>Enriches recommended properties and top areas using:
 * <ul>
 *   <li>{@link DanangAdminNormalizer} — Historical/post-2025 ward & district normalization.</li>
 *   <li>{@link DanangSpatialValidator} — JTS polygon & coordinate validation ({@code SRID 4326}).</li>
 *   <li>{@link AdvisorPoiSpatialRepository} — Exact {@code ST_Distance_Sphere} meter distances to
 *       curated POIs for verified platform properties only.</li>
 *   <li>{@link AmenityCatalogService} — Verified 82-area Da Nang amenity catalog.</li>
 * </ul>
 *
 * <p>Never mutates tested ranking scores, never fabricates coordinates for TiniX/External rows,
 * and never predicts rental yields or capital appreciation.
 */
@Service
public class AdvisorLocationIntelligenceService {

    public static final String DISTANCE_METHOD_SPHERE = "MYSQL_ST_DISTANCE_SPHERE_WGS84_METERS";
    public static final String DISTANCE_METHOD_NONE = "NONE_ADMIN_FALLBACK";

    private static final Pattern LEADING_WARD_PREFIX = Pattern.compile(
        "(?iu)^(?:phường|phuong|xã|xa|thị trấn|thi tran|p\\.|x\\.|tt\\.)\\s*"
    );

    public record NormalizedAdvisorFilter(
        String effectiveDistrict,
        String effectiveWard,
        AdminNormalizationResult normalization,
        String warning
    ) {}

    public record PropertyGisEnrichment(
        LocationIntelligence locationIntelligence,
        AmenityEvidence resolvedAmenityEvidence
    ) {}

    private final DanangAdminNormalizer normalizer;
    private final DanangSpatialValidator spatialValidator;
    @Nullable
    private final AdvisorPoiSpatialRepository spatialRepository;
    private final AmenityCatalogService catalogService;
    private final AmenityEvidenceService amenityEvidenceService;

    @Autowired
    public AdvisorLocationIntelligenceService(
            DanangAdminNormalizer normalizer,
            DanangSpatialValidator spatialValidator,
            @Nullable AdvisorPoiSpatialRepository spatialRepository,
            AmenityCatalogService catalogService,
            AmenityEvidenceService amenityEvidenceService) {
        this.normalizer = normalizer;
        this.spatialValidator = spatialValidator;
        this.spatialRepository = spatialRepository;
        this.catalogService = catalogService;
        this.amenityEvidenceService = amenityEvidenceService;
    }

    /**
     * Normalizes user-supplied district/ward filters without ever guessing ambiguous cross-district wards.
     */
    public NormalizedAdvisorFilter normalizeAdvisorFilter(String rawDistrict, String rawWard) {
        String cleanDist = cleanFilter(rawDistrict);
        String cleanWard = cleanFilter(rawWard);
        if (cleanDist == null && cleanWard == null) {
            return new NormalizedAdvisorFilter(null, null, null, null);
        }

        AdminNormalizationResult norm = normalizer.normalize(cleanDist, cleanWard, "Đà Nẵng");
        AdminNormalizationStatus st = norm.status();

        if (st == AdminNormalizationStatus.AMBIGUOUS_CROSS_DISTRICT_WARD
                || st == AdminNormalizationStatus.CONFLICTING_ADMIN_HIERARCHY
                || st == AdminNormalizationStatus.EXTENDED_QUANG_NAM_JURISDICTION
                || st == AdminNormalizationStatus.EXCLUDED_ISLAND_DISTRICT
                || st == AdminNormalizationStatus.OUTSIDE_DANANG
                || st == AdminNormalizationStatus.INCOMPLETE_LOCATION) {
            String warn = "LOCATION_NORMALIZATION: " + (norm.provenanceNote() != null
                ? norm.provenanceNote()
                : "Không thể chuẩn hóa đơn trị địa bàn từ bộ lọc đã nhập.");
            return new NormalizedAdvisorFilter(cleanDist, stripWardPrefix(cleanWard), norm, warn);
        }

        if (st == AdminNormalizationStatus.RESOLVED_POST_2025_NEW_WARD) {
            String warn = "LOCATION_NORMALIZATION: " + (norm.provenanceNote() != null
                ? norm.provenanceNote()
                : ("Đơn vị hành chính mới '" + norm.displayWard() + "' thuộc " + norm.canonicalDistrict() + "."));
            return new NormalizedAdvisorFilter(norm.canonicalDistrict(), null, norm, warn);
        }

        String effDistrict = norm.canonicalDistrict() != null ? norm.canonicalDistrict() : cleanDist;
        String effWard = stripWardPrefix(cleanWard);
        String warn = (st == AdminNormalizationStatus.RESOLVED_HISTORICAL_MERGED_WARD
                || st == AdminNormalizationStatus.HISTORICAL_SPLIT_WARD_AMBIGUOUS)
                && norm.provenanceNote() != null
            ? "LOCATION_NORMALIZATION: " + norm.provenanceNote()
            : null;
        return new NormalizedAdvisorFilter(effDistrict, effWard, norm, warn);
    }

    /**
     * Batch-enriches recommended properties with verified coordinates, nearby POI spherical distances,
     * administrative fallbacks, bridged catalog profiles, and purpose-aware spatial explanations.
     */
    public Map<String, PropertyGisEnrichment> enrichProperties(List<PropertyResult> properties, Purpose purpose) {
        if (properties == null || properties.isEmpty()) {
            return Map.of();
        }

        List<String> platformIds = properties.stream()
            .filter(p -> p.source() != null
                && "PROPERTY".equals(p.source().kind())
                && "PLATFORM_PUBLISHED".equals(p.qualityStatus()))
            .map(p -> p.source().recordKey())
            .filter(k -> k != null && !k.isBlank())
            .distinct()
            .toList();

        Map<String, RawPropertyCoordinate> coordsById = (spatialRepository != null && !platformIds.isEmpty())
            ? safeLoadCoordinates(platformIds)
            : Map.of();

        Map<String, PropertyGisEnrichment> result = new LinkedHashMap<>();
        for (PropertyResult prop : properties) {
            result.put(prop.id(), enrichSingleProperty(prop, purpose, coordsById));
        }
        return Map.copyOf(result);
    }

    /**
     * Builds purpose-aware spatial explanations for the top recommended areas using verified catalog profiles.
     */
    public List<AreaPurposeInsight> buildAreaPurposeInsights(List<AreaResult> topAreas, Purpose purpose) {
        if (topAreas == null || topAreas.isEmpty()) {
            return List.of();
        }
        Purpose effectivePurpose = purpose == null ? Purpose.LIVING : purpose;
        List<AreaPurposeInsight> insights = new ArrayList<>();
        for (AreaResult area : topAreas) {
            AdminNormalizationResult norm = normalizer.normalize(area.district(), area.ward(), "Đà Nẵng");
            Optional<AmenityProfile> profileOpt = resolveCatalogProfile(norm, area.district(), area.ward());
            String areaKey = (area.district() == null ? "" : area.district()) + ":" + (area.ward() == null ? "" : area.ward());

            if (profileOpt.isEmpty()) {
                insights.add(new AreaPurposeInsight(
                    areaKey,
                    area.district(),
                    area.ward(),
                    effectivePurpose.name(),
                    "Đánh giá theo mật độ tin rao đủ điều kiện (chưa có hồ sơ tiện ích riêng)",
                    List.of("Khu vực có " + area.candidateCount() + " bất động sản phù hợp tiêu chí ngân sách và loại hình."),
                    Map.of(),
                    null,
                    "CANDIDATE_AGGREGATION_ONLY"
                ));
                continue;
            }

            AmenityProfile p = profileOpt.get();
            PoiCounts c = p.poiCounts();
            Map<String, Integer> counts = c == null ? Map.of() : Map.of(
                "total", c.total(),
                "school", c.school(),
                "hospital", c.hospital(),
                "market", c.market(),
                "supermarket", c.supermarket(),
                "park", c.park(),
                "beach", c.beach(),
                "transit", c.transit()
            );
            String basis = "WARD".equals(p.areaLevel()) ? "DIRECT_WARD_CATALOG" : "DISTRICT_CATALOG";
            PurposeLocationFit fit = buildPurposeFitFromSignals(
                effectivePurpose,
                p,
                List.of(),
                area.averageAskingPriceVnd(),
                null,
                norm.displayLabel(),
                false
            );
            insights.add(new AreaPurposeInsight(
                areaKey,
                area.district(),
                area.ward(),
                effectivePurpose.name(),
                fit.headlineVi(),
                fit.highlightsVi(),
                counts,
                p.densityPerKm2(),
                basis
            ));
        }
        return List.copyOf(insights);
    }

    private PropertyGisEnrichment enrichSingleProperty(
            PropertyResult prop,
            Purpose purpose,
            Map<String, RawPropertyCoordinate> coordsById) {

        String sourceKind = prop.source() == null ? "UNKNOWN" : prop.source().kind();
        boolean isTinix = "TINIX_AI".equals(sourceKind);
        boolean isPlatform = "PROPERTY".equals(sourceKind) && "PLATFORM_PUBLISHED".equals(prop.qualityStatus()) && !isTinix;

        AdminNormalizationResult norm = normalizer.normalize(prop.district(), prop.ward(), "Đà Nẵng");

        Double candLat = null;
        Double candLon = null;
        String sridFailureNote = null;
        if (isPlatform && prop.source().recordKey() != null) {
            RawPropertyCoordinate raw = coordsById.get(prop.source().recordKey());
            if (raw != null) {
                if (raw.srid() == 4326) {
                    candLat = raw.latitude();
                    candLon = raw.longitude();
                } else {
                    sridFailureNote = "Hệ quy chiếu không gian SRID=" + raw.srid() + " khác chuẩn WGS84 (4326); ẩn ghim bản đồ.";
                }
            }
        }

        CoordinateValidationResult coordVal = sridFailureNote != null
            ? new CoordinateValidationResult(
                GisDtos.CoordinateStatus.INVALID_COORDINATES, false, null, null, null, null, sridFailureNote)
            : spatialValidator.validate(candLat, candLon, norm.canonicalDistrict(), isPlatform);

        boolean mapEligible = isPlatform && coordVal.usableForPinAndPoi()
            && coordVal.verifiedLatitude() != null && coordVal.verifiedLongitude() != null;

        List<NearbyPoiItem> nearbyPois = List.of();
        Integer radiusUsed = null;
        String distanceMethod = DISTANCE_METHOD_NONE;
        if (mapEligible && spatialRepository != null) {
            radiusUsed = AdvisorPoiSpatialRepository.DEFAULT_RADIUS_METERS;
            distanceMethod = DISTANCE_METHOD_SPHERE;
            nearbyPois = safeFindNearbyPois(coordVal.verifiedLatitude(), coordVal.verifiedLongitude(), radiusUsed);
        }

        String locationPrecision;
        if (mapEligible) {
            locationPrecision = "VERIFIED_PROPERTY_PIN";
        } else if (norm.catalogWard() != null || norm.displayWard() != null) {
            locationPrecision = "WARD_FALLBACK";
        } else if (norm.canonicalDistrict() != null) {
            locationPrecision = "DISTRICT_FALLBACK";
        } else {
            locationPrecision = "CITY_FALLBACK";
        }

        String fallbackReason = mapEligible
            ? null
            : buildFallbackReason(sourceKind, isPlatform, coordsById.containsKey(prop.source() != null ? prop.source().recordKey() : ""), coordVal);

        // Resolve AmenityProfile (bridging Roman numerals & NQ 1251 merged wards when needed)
        Optional<AmenityProfile> profileOpt = resolveCatalogProfile(norm, prop.district(), prop.ward());
        AmenityEvidence effectiveAmenity = upgradeAmenityEvidenceIfBridged(prop.amenityEvidence(), norm, profileOpt);

        Purpose effectivePurpose = purpose == null ? Purpose.LIVING : purpose;
        PurposeLocationFit purposeFit = buildPurposeFitFromSignals(
            effectivePurpose,
            profileOpt.orElse(null),
            nearbyPois,
            prop.priceVnd(),
            prop.areaSqm(),
            norm.displayLabel(),
            mapEligible
        );

        LocationIntelligence locIntel = new LocationIntelligence(
            locationPrecision,
            coordVal.status().name(),
            mapEligible,
            mapEligible ? coordVal.verifiedLatitude() : null,
            mapEligible ? coordVal.verifiedLongitude() : null,
            norm.canonicalDistrict(),
            norm.displayWard(),
            norm.displayLabel(),
            norm.status().name(),
            norm.provenanceNote(),
            fallbackReason,
            radiusUsed,
            distanceMethod,
            nearbyPois,
            purposeFit
        );

        return new PropertyGisEnrichment(locIntel, effectiveAmenity);
    }

    private Optional<AmenityProfile> resolveCatalogProfile(
            AdminNormalizationResult norm,
            String rawDistrict,
            String rawWard) {
        String dist = norm.canonicalDistrict() != null ? norm.canonicalDistrict() : cleanFilter(rawDistrict);
        if (dist == null) {
            return Optional.empty();
        }
        if (norm.catalogWard() != null) {
            Optional<AmenityProfile> wardProf = catalogService.lookup(dist, norm.catalogWard(), null);
            if (wardProf.isPresent() && "WARD".equals(wardProf.get().areaLevel())) {
                return wardProf;
            }
        }
        if (rawWard != null && !rawWard.isBlank() && norm.status() == AdminNormalizationStatus.RESOLVED_CANONICAL) {
            Optional<AmenityProfile> rawWardProf = catalogService.lookup(dist, rawWard, null);
            if (rawWardProf.isPresent() && "WARD".equals(rawWardProf.get().areaLevel())) {
                return rawWardProf;
            }
        }
        return catalogService.lookup(dist, null, null);
    }

    /**
     * When a property had ward "Hải Châu 1/2" or NQ 1251 merged ward "Nam Dương"/"Tam Thuận"/"Tân Chính",
     * {@code PropertyLocationResolver} fell back to DISTRICT_SHARED_AMENITY during V1.1 ranking.
     * Here we upgrade the explanatory {@link AmenityEvidence} to the authoritative WARD profile
     * while preserving {@code amenityFit} so ranking scores remain 100% invariant.
     */
    private AmenityEvidence upgradeAmenityEvidenceIfBridged(
            AmenityEvidence current,
            AdminNormalizationResult norm,
            Optional<AmenityProfile> profileOpt) {
        if (current == null || profileOpt.isEmpty() || norm.catalogWard() == null) {
            return current;
        }
        AmenityProfile p = profileOpt.get();
        if (!"WARD".equals(p.areaLevel()) || "WARD".equals(current.areaLevel())) {
            return current;
        }
        PropertyLocationResolver.Resolution bridgedRes = new PropertyLocationResolver.Resolution(
            p,
            PropertyLocationResolver.BASIS_DIRECT_WARD,
            p.confidence(),
            true
        );
        return amenityEvidenceService.build(p, bridgedRes, current.amenityFit());
    }

    private static String buildFallbackReason(
            String sourceKind,
            boolean isPlatform,
            boolean foundInDb,
            CoordinateValidationResult coordVal) {
        if ("TINIX_AI".equals(sourceKind)) {
            return "Bản ghi nghiên cứu lịch sử TiniX (CC BY-NC 4.0) chỉ có thông tin hành chính cấp phường/quận, không có tọa độ GPS từng căn; SmartProp tuyệt đối không tạo tọa độ giả hay tính khoảng cách mét.";
        }
        if ("EXTERNAL".equals(sourceKind)) {
            return "Tin tham chiếu nguồn ngoài không có tọa độ GPS đã xác thực; chỉ đối chiếu hồ sơ tiện ích ở cấp hành chính.";
        }
        if (isPlatform && !foundInDb) {
            return "Chưa tải được tọa độ không gian đã xác thực của tin đăng; hiển thị đối chiếu hành chính cấp phường/quận.";
        }
        return coordVal.validationNote();
    }

    static PurposeLocationFit buildPurposeFitFromSignals(
            Purpose purpose,
            @Nullable AmenityProfile profile,
            List<NearbyPoiItem> nearbyPois,
            @Nullable BigDecimal priceVnd,
            @Nullable BigDecimal areaSqm,
            String displayLabel,
            boolean hasVerifiedPin) {

        List<String> highlights = new ArrayList<>();
        CategoryScores cs = profile != null ? profile.categoryScores() : null;
        PoiCounts pc = profile != null ? profile.poiCounts() : null;

        NearbyPoiItem closestSchool = firstOfCategories(nearbyPois, "SCHOOL");
        NearbyPoiItem closestMedical = firstOfCategories(nearbyPois, "HOSPITAL", "PHARMACY");
        NearbyPoiItem closestShopping = firstOfCategories(nearbyPois, "SUPERMARKET", "MARKET");
        NearbyPoiItem closestLeisure = firstOfCategories(nearbyPois, "PARK", "BEACH");
        NearbyPoiItem closestTransit = firstOfCategories(nearbyPois, "PUBLIC_TRANSPORT", "TRANSPORT");

        String headline;
        switch (purpose) {
            case INVESTMENT -> {
                headline = "Đánh giá nền tảng hạ tầng & thanh khoản khu vực (" + displayLabel + ")";
                if (hasVerifiedPin && !nearbyPois.isEmpty()) {
                    List<String> anchors = new ArrayList<>();
                    if (closestTransit != null) anchors.add(closestTransit.name() + " (" + closestTransit.distanceMeters() + " m)");
                    if (closestShopping != null) anchors.add(closestShopping.name() + " (" + closestShopping.distanceMeters() + " m)");
                    if (closestSchool != null) anchors.add(closestSchool.name() + " (" + closestSchool.distanceMeters() + " m)");
                    if (!anchors.isEmpty()) {
                        highlights.add("Kết nối thực tế quanh tọa độ tin rao (bán kính 1,5 km, đường chim bay): " + String.join("; ", anchors) + ".");
                    }
                }
                if (profile != null && pc != null) {
                    String densityText = profile.densityPerKm2() != null
                        ? String.format(Locale.ROOT, "%.1f POI/km²", profile.densityPerKm2()).replace('.', ',')
                        : pc.total() + " POI đã số hóa";
                    highlights.add("Mật độ hạ tầng " + scopeNameVi(profile) + ": " + densityText
                        + " (điểm giao thông " + fmt1(cs.transit()) + "/100, thương mại thiết yếu " + fmt1(cs.essentials()) + "/100).");
                }
                if (priceVnd != null && areaSqm != null && areaSqm.signum() > 0) {
                    BigDecimal m2Million = priceVnd.divide(areaSqm, 0, RoundingMode.HALF_UP)
                        .divide(new BigDecimal("1000000"), 1, RoundingMode.HALF_UP);
                    highlights.add("Đơn giá rao hiện tại khoảng " + m2Million.toPlainString().replace('.', ',')
                        + " triệu VNĐ/m² — đối chiếu độc lập với mẫu tương đồng và định giá V6 trước khi ra quyết định.");
                }
                highlights.add("Lưu ý đầu tư: Phân tích phản ánh mật độ tiện ích và kết nối hiện hữu, không dự báo hay cam kết biên độ tăng giá vốn.");
            }
            case RENTAL -> {
                headline = "Đánh giá khả năng tiếp cận tiện ích phục vụ khách thuê (" + displayLabel + ")";
                if (hasVerifiedPin && !nearbyPois.isEmpty()) {
                    List<String> tenantNodes = new ArrayList<>();
                    if (closestTransit != null) tenantNodes.add(closestTransit.categoryLabelVi() + ": " + closestTransit.name() + " (" + closestTransit.distanceMeters() + " m)");
                    if (closestShopping != null) tenantNodes.add(closestShopping.categoryLabelVi() + ": " + closestShopping.name() + " (" + closestShopping.distanceMeters() + " m)");
                    if (closestLeisure != null) tenantNodes.add(closestLeisure.categoryLabelVi() + ": " + closestLeisure.name() + " (" + closestLeisure.distanceMeters() + " m)");
                    if (closestSchool != null && tenantNodes.size() < 3) tenantNodes.add("Trường học: " + closestSchool.name() + " (" + closestSchool.distanceMeters() + " m)");
                    if (!tenantNodes.isEmpty()) {
                        highlights.add("Tiện ích hỗ trợ nhu cầu lưu trú/thuê dài hạn trong 1,5 km: " + String.join("; ", tenantNodes) + ".");
                    }
                }
                if (profile != null && pc != null && cs != null) {
                    highlights.add("Hồ sơ " + scopeNameVi(profile) + " ghi nhận " + pc.transit() + " điểm giao thông công cộng, "
                        + (pc.supermarket() + pc.market()) + " chợ/siêu thị"
                        + (pc.beach() > 0 ? (", " + pc.beach() + " bãi biển du lịch") : "")
                        + " (điểm kết nối " + fmt1(cs.transit()) + "/100, giải trí/không gian mở " + fmt1(cs.recreation()) + "/100).");
                }
                highlights.add("Lưu ý khai thác thuê: Ngân sách là tổng giá mua tài sản; hệ thống đánh giá tiện ích thu hút người thuê chứ không dự báo giá thuê tháng hay lợi suất.");
            }
            case LIVING -> {
                headline = "Đánh giá tiện ích sinh hoạt gia đình hằng ngày (" + displayLabel + ")";
                if (hasVerifiedPin && !nearbyPois.isEmpty()) {
                    List<String> daily = new ArrayList<>();
                    if (closestSchool != null) daily.add("Trường học gần nhất: " + closestSchool.name() + " (" + closestSchool.distanceMeters() + " m)");
                    if (closestMedical != null) daily.add("Y tế gần nhất: " + closestMedical.name() + " (" + closestMedical.distanceMeters() + " m)");
                    if (closestShopping != null) daily.add("Mua sắm/chợ: " + closestShopping.name() + " (" + closestShopping.distanceMeters() + " m)");
                    if (closestLeisure != null) daily.add("Không gian xanh/biển: " + closestLeisure.name() + " (" + closestLeisure.distanceMeters() + " m)");
                    if (!daily.isEmpty()) {
                        highlights.add(String.join(" · ", daily) + ".");
                    }
                }
                if (profile != null && pc != null && cs != null) {
                    highlights.add("Hồ sơ tiện ích " + scopeNameVi(profile) + " đạt " + fmt1(profile.livingScore()) + "/100: "
                        + pc.school() + " trường học (giáo dục " + fmt1(cs.education()) + "), "
                        + (pc.hospital() + pc.pharmacy()) + " cơ sở y tế/nhà thuốc (y tế " + fmt1(cs.healthcare()) + "), "
                        + (pc.market() + pc.supermarket()) + " chợ & siêu thị (thiết yếu " + fmt1(cs.essentials()) + ").");
                }
                if (!hasVerifiedPin) {
                    highlights.add("Chưa có tọa độ GPS cấp căn đã xác thực nên đánh giá dựa trên hồ sơ hành chính khu vực, không quy đổi thành khoảng cách đi bộ từ cửa nhà.");
                }
            }
            default -> headline = "Phân tích vị trí (" + displayLabel + ")";
        }

        if (highlights.isEmpty()) {
            highlights.add("Khu vực chưa có dữ liệu tiện ích số hóa chi tiết; chỉ đối chiếu theo địa giới hành chính hiện có.");
        }

        String basisNote = hasVerifiedPin
            ? "Khoảng cách mét được tính trực tiếp trên mặt cầu WGS84 (MySQL ST_Distance_Sphere, đường chim bay, không phải lộ trình giao thông hay thời gian di chuyển)."
            : (profile != null
                ? ("Đối chiếu theo hồ sơ danh mục tiện ích cấp " + ("WARD".equals(profile.areaLevel()) ? "phường/xã" : "quận/huyện") + " (" + profile.areaName() + "); không có tọa độ GPS từng căn.")
                : "Đối chiếu giới hạn ở cấp hành chính; chưa có hồ sơ tiện ích hoặc tọa độ GPS cấp căn.");

        return new PurposeLocationFit(purpose.name(), headline, List.copyOf(highlights), basisNote);
    }

    private Map<String, RawPropertyCoordinate> safeLoadCoordinates(List<String> ids) {
        try {
            return spatialRepository.loadPlatformCoordinates(ids);
        } catch (Exception ex) {
            return Map.of();
        }
    }

    private List<NearbyPoiItem> safeFindNearbyPois(double lat, double lon, int radiusMeters) {
        try {
            return spatialRepository.findNearbyPois(lat, lon, radiusMeters, AdvisorPoiSpatialRepository.DEFAULT_MAX_POIS);
        } catch (Exception ex) {
            return List.of();
        }
    }

    private static NearbyPoiItem firstOfCategories(List<NearbyPoiItem> items, String... categories) {
        if (items == null || items.isEmpty()) return null;
        for (NearbyPoiItem item : items) {
            for (String c : categories) {
                if (c.equals(item.category())) {
                    return item;
                }
            }
        }
        return null;
    }

    private static String scopeNameVi(AmenityProfile profile) {
        return ("WARD".equals(profile.areaLevel()) ? "cấp phường (" : "cấp quận/huyện (") + profile.areaName() + ")";
    }

    private static String fmt1(double val) {
        return String.format(Locale.ROOT, "%.0f", val);
    }

    private static String cleanFilter(String raw) {
        if (raw == null) return null;
        String t = raw.strip();
        if (t.isEmpty() || "ALL".equalsIgnoreCase(t) || "Tất cả".equalsIgnoreCase(t)) {
            return null;
        }
        return t;
    }

    private static String stripWardPrefix(String raw) {
        String c = cleanFilter(raw);
        if (c == null) return null;
        String stripped = LEADING_WARD_PREFIX.matcher(c).replaceFirst("").strip();
        return stripped.isEmpty() ? c : stripped;
    }
}

