package vn.smartprop.advisor;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import vn.smartprop.advisor.AdvisorDtos.AdvisedProperty;
import vn.smartprop.advisor.AdvisorDtos.AdvisorRequest;
import vn.smartprop.advisor.AdvisorDtos.AdvisorResponse;
import vn.smartprop.advisor.AdvisorDtos.ComparableEvidence;
import vn.smartprop.advisor.AdvisorDtos.ComparableItem;
import vn.smartprop.advisor.AdvisorDtos.ResolvedCriteria;
import vn.smartprop.advisor.AdvisorDtos.ServiceStatus;
import vn.smartprop.advisor.AdvisorDtos.ValuationEvidence;
import vn.smartprop.modules.amenity.AmenityCatalogService;
import vn.smartprop.common.ApiInputs;
import vn.smartprop.comparable.ComparableDtos;
import vn.smartprop.comparable.ComparableEligibilityService;
import vn.smartprop.comparable.ComparableRankingService;
import vn.smartprop.comparable.ComparableSourceClassifier;
import vn.smartprop.gis.AdvisorLocationIntelligenceService;
import vn.smartprop.gis.AdvisorLocationIntelligenceService.NormalizedAdvisorFilter;
import vn.smartprop.gis.AdvisorLocationIntelligenceService.PropertyGisEnrichment;
import vn.smartprop.gis.DanangAdminNormalizer;
import vn.smartprop.gis.DanangSpatialValidator;
import vn.smartprop.gis.GisDtos.AreaPurposeInsight;
import vn.smartprop.gis.GisDtos.LocationIntelligence;
import vn.smartprop.modules.recommendation.AmenityEvidenceService;
import vn.smartprop.modules.recommendation.HybridRecommendationService;
import vn.smartprop.modules.recommendation.RecommendationDtos;
import vn.smartprop.modules.recommendation.RecommendationDtos.AmenityEvidence;
import vn.smartprop.modules.recommendation.RecommendationDtos.PropertyResult;
import vn.smartprop.modules.recommendation.RecommendationDtos.PropertyType;
import vn.smartprop.modules.recommendation.RecommendationDtos.Source;

/**
 * Step 21.3B & 21.3C — Unified AI Advisor Orchestrator.
 *
 * <p>Combines existing verified SmartProp subsystems without duplicating business logic:
 * <ol>
 *   <li>{@link HybridRecommendationService} — Purpose-aware property ranking & area recommendation
 *       with V1.1 amenity catalog evidence, deduplication, and strict protected-holdout exclusion.</li>
 *   <li>{@link ComparableRankingService} — Step 21.2 comparable market/research evidence anchored
 *       solely to source attributes and asking price (never to V6 model estimates).</li>
 *   <li>{@link AdvisorValuationAdapter} — Independent XGBoost V1.3 + TreeSHAP valuation for active
 *       listings that satisfy all mandatory model feature constraints, degrading cleanly to partial
 *       results whenever the Python AI service is offline.</li>
 * </ol>
 */
@Service
public class AdvisorOrchestrationService {
    public static final String ADVISOR_VERSION = "ADVISOR_ORCHESTRATOR_V1";
    public static final String SCORE_DISCLAIMER =
        "Điểm phù hợp (0–100) và độ tương đồng (0–1) là thước đo quy tắc tham khảo chưa hiệu chuẩn xác suất; "
        + "giá ước tính XGBoost V1.3 là tham chiếu độc lập trên dữ liệu giá rao, không dùng để tự chứng minh độ chính xác.";

    private static final BigDecimal MAX_CONTRACT_BUDGET = new BigDecimal("999999999999999");
    private static final int DEFAULT_LIMIT = 5;
    private static final int COMPARABLES_PER_PROPERTY = 3;

    private final HybridRecommendationService recommendationService;
    private final ComparableRankingService comparableService;
    private final ComparableEligibilityService comparableEligibility;
    private final AdvisorValuationAdapter valuationAdapter;
    private final AdvisorLocationIntelligenceService locationIntelligenceService;
    private final boolean allowResearchComparables;

    @Autowired
    public AdvisorOrchestrationService(
            HybridRecommendationService recommendationService,
            ComparableRankingService comparableService,
            ComparableEligibilityService comparableEligibility,
            AdvisorValuationAdapter valuationAdapter,
            AdvisorLocationIntelligenceService locationIntelligenceService,
            @Value("${app.advisor.allow-research-comparables:false}") boolean allowResearchComparables) {
        this.recommendationService = recommendationService;
        this.comparableService = comparableService;
        this.comparableEligibility = comparableEligibility;
        this.valuationAdapter = valuationAdapter;
        this.locationIntelligenceService = locationIntelligenceService;
        this.allowResearchComparables = allowResearchComparables;
    }

    public AdvisorOrchestrationService(
            HybridRecommendationService recommendationService,
            ComparableRankingService comparableService,
            ComparableEligibilityService comparableEligibility,
            AdvisorValuationAdapter valuationAdapter,
            boolean allowResearchComparables) {
        this(
            recommendationService,
            comparableService,
            comparableEligibility,
            valuationAdapter,
            defaultStandaloneLocationService(),
            allowResearchComparables
        );
    }

    private static AdvisorLocationIntelligenceService defaultStandaloneLocationService() {
        ObjectMapper mapper = new ObjectMapper();
        return new AdvisorLocationIntelligenceService(
            new DanangAdminNormalizer(),
            new DanangSpatialValidator(mapper),
            null,
            new AmenityCatalogService(mapper),
            new AmenityEvidenceService()
        );
    }

    public boolean isResearchEnabled() {
        return recommendationService.tinixEnabled();
    }

    public AdvisorResponse consult(AdvisorRequest rawRequest) {
        if (rawRequest == null || rawRequest.budgetVnd() == null || rawRequest.purpose() == null || rawRequest.propertyType() == null) {
            throw ApiInputs.bad("Thiếu thông tin bắt buộc: ngân sách, mục đích mua và loại bất động sản.");
        }
        ResolvedCriteria baseCriteria = resolveCriteria(rawRequest);
        if (baseCriteria.includeResearch() && !isResearchEnabled()) {
            throw ApiInputs.forbidden();
        }
        NormalizedAdvisorFilter normFilter = locationIntelligenceService.normalizeAdvisorFilter(
            baseCriteria.district(), baseCriteria.ward());
        ResolvedCriteria criteria = new ResolvedCriteria(
            baseCriteria.statedBudgetVnd(),
            baseCriteria.budgetFlexibilityPct(),
            baseCriteria.effectiveCeilingVnd(),
            baseCriteria.purpose(),
            baseCriteria.propertyType(),
            baseCriteria.minAreaSqm(),
            normFilter.effectiveDistrict(),
            normFilter.effectiveWard(),
            baseCriteria.limit(),
            baseCriteria.includeComparables(),
            baseCriteria.includeValuation(),
            baseCriteria.includeResearch()
        );

        RecommendationDtos.Request recReq = new RecommendationDtos.Request(
            criteria.effectiveCeilingVnd(),
            criteria.purpose(),
            criteria.propertyType(),
            criteria.minAreaSqm(),
            criteria.district(),
            criteria.ward(),
            criteria.limit()
        );

        RecommendationDtos.Response recRes = criteria.includeResearch()
            ? recommendationService.recommendResearch(recReq)
            : recommendationService.recommendPublic(recReq);

        LinkedHashSet<String> warnings = new LinkedHashSet<>();
        for (String w : recRes.warnings()) {
            if (criteria.includeResearch() || !containsNonPublicMetadata(w)) {
                warnings.add(w);
            }
        }
        if (normFilter.warning() != null) {
            warnings.add(normFilter.warning());
        }
        if (criteria.budgetFlexibilityPct() > 0) {
            warnings.add("FLEXIBLE_BUDGET: Đã mở rộng trần tìm kiếm thêm +" + criteria.budgetFlexibilityPct()
                + "% (tối đa " + criteria.effectiveCeilingVnd().toPlainString()
                + " VND); các tin vượt ngân sách gốc được gắn nhãn rõ ràng.");
        }

        List<PropertyResult> candidateProps = criteria.includeResearch()
            ? recRes.topProperties()
            : recRes.topProperties().stream().filter(AdvisorOrchestrationService::isPublicLiveCandidate).toList();
        List<RecommendationDtos.AreaResult> effectiveAreas = criteria.includeResearch()
            ? recRes.topAreas()
            : recRes.topAreas().stream()
                .filter(a -> a.unverifiedCount() == 0 && a.needsReviewCount() == 0)
                .toList();

        // Batch-enrich location intelligence & purpose-aware GIS insights (1 SQL round-trip for coordinates)
        Map<String, PropertyGisEnrichment> gisByPropertyId = locationIntelligenceService.enrichProperties(
            candidateProps, criteria.purpose());
        List<AreaPurposeInsight> areaLocationInsights = locationIntelligenceService.buildAreaPurposeInsights(
            effectiveAreas, criteria.purpose());

        // Probe FastAPI Valuation service once per consultation for fast partial-result fallback.
        String valuationStatus;
        Map<String, Set<String>> supportedV6Locations = null;
        if (!criteria.includeValuation()) {
            valuationStatus = "SKIPPED";
        } else {
            supportedV6Locations = valuationAdapter.probeSupportedLocations();
            if (supportedV6Locations == null) {
                valuationStatus = "UNAVAILABLE";
                warnings.add("VALUATION_SERVICE_UNAVAILABLE: Dịch vụ định giá AI (XGBoost V1.3) hiện không khả dụng; "
                    + "hệ thống trả kết quả tư vấn một phần (khu vực, bất động sản phù hợp và bằng chứng tương đồng vẫn đầy đủ).");
            } else {
                valuationStatus = "AVAILABLE";
            }
        }

        String comparableServiceStatus = criteria.includeComparables() ? "AVAILABLE" : "SKIPPED";
        boolean comparableDegraded = false;
        boolean hasResearchComparable = false;

        List<AdvisedProperty> advisedProperties = new ArrayList<>();
        for (PropertyResult prop : candidateProps) {
            boolean isTinix = "TINIX_AI".equals(prop.source().kind())
                || "HYBRID_ELIGIBLE_RESEARCH".equals(prop.qualityStatus());
            boolean isPlatform = "PROPERTY".equals(prop.source().kind()) && "PLATFORM_PUBLISHED".equals(prop.qualityStatus());
            boolean isVerifiedExt = "EXTERNAL".equals(prop.source().kind())
                && "VALID".equals(prop.qualityStatus())
                && "VERIFIED".equals(prop.verificationStatus());
            boolean liveListing = isPlatform || isVerifiedExt;
            if (!criteria.includeResearch() && (isTinix || !liveListing)) {
                // Defense in depth: SAFE mode never surfaces research or unverified/needs-review records.
                continue;
            }
            boolean researchRef = isTinix;
            String availabilityStatus = isPlatform ? "PUBLISHED_ACTIVE"
                : (isVerifiedExt ? "VERIFIED_EXTERNAL"
                : (isTinix ? "UNKNOWN_HISTORICAL_RESEARCH" : "UNVERIFIED_REFERENCE"));

            // Budget vs flexible ceiling calculations
            boolean withinStated = prop.priceVnd().compareTo(criteria.statedBudgetVnd()) <= 0;
            boolean withinFlexible = prop.priceVnd().compareTo(criteria.effectiveCeilingVnd()) <= 0;
            BigDecimal budgetDeltaPct = prop.priceVnd().subtract(criteria.statedBudgetVnd())
                .multiply(new BigDecimal("100"))
                .divide(criteria.statedBudgetVnd(), 1, RoundingMode.HALF_UP);

            List<String> fitReasons = new ArrayList<>();
            if (!withinStated && withinFlexible) {
                fitReasons.add("Nằm trong biên ngân sách linh hoạt (+" + budgetDeltaPct.toPlainString()
                    + "% so với ngân sách mục tiêu " + criteria.statedBudgetVnd().toPlainString() + " VND).");
            } else {
                fitReasons.add("Phù hợp trong trần ngân sách mục tiêu (" + budgetDeltaPct.toPlainString() + "% so với trần).");
            }
            for (String exp : prop.explanations()) {
                if (criteria.includeResearch() || !containsResearchMetadata(exp)) {
                    fitReasons.add(exp);
                }
            }

            // Sanitize listing source URL & enforce null URL for research observations
            Source safeSource = sanitizeSource(prop.source(), researchRef);

            // Comparable evidence (anchored strictly to source property attributes, NEVER V1.3 output)
            ComparableEvidence compEvidence;
            if (!criteria.includeComparables()) {
                compEvidence = new ComparableEvidence("SKIPPED_BY_REQUEST", 0, "NONE", List.of(), List.of());
            } else {
                try {
                    compEvidence = buildComparableEvidence(prop, criteria.includeResearch(), ComparableDtos.Purpose.SIMILAR_LISTING);
                    if (compEvidence.comparables().stream().anyMatch(ComparableItem::researchReference)) {
                        hasResearchComparable = true;
                    }
                } catch (Exception ex) {
                    comparableDegraded = true;
                    compEvidence = new ComparableEvidence(
                        "DEGRADED", 0, "NONE", List.of(),
                        List.of("Không thể truy vấn bằng chứng bất động sản tương đồng cho tin này."));
                }
            }

            // Valuation + TreeSHAP evidence (never run on research rows or rows missing required features)
            ValuationEvidence valEvidence;
            if (!criteria.includeValuation()) {
                valEvidence = AdvisorValuationAdapter.skipped("SKIPPED_BY_REQUEST",
                    "Người dùng không yêu cầu định giá tham khảo AI trong lượt tư vấn này.");
            } else if (researchRef) {
                valEvidence = AdvisorValuationAdapter.skipped("SKIPPED_RESEARCH_RECORD",
                    "Bản ghi TiniX là dữ liệu tham chiếu nghiên cứu lịch sử (CC BY-NC 4.0), không chạy định giá chào bán trực tiếp.");
            } else {
                valEvidence = valuationAdapter.evaluate(
                    prop.source().kind(),
                    prop.source().recordKey(),
                    prop.propertyType(),
                    prop.areaSqm(),
                    prop.district(),
                    prop.ward(),
                    prop.priceVnd(),
                    supportedV6Locations
                );
            }

            ComparableEvidence valuationComparables = null;
            if (criteria.includeComparables() && valEvidence != null && valEvidence.available()) {
                try {
                    // Price from the model never enters the comparable request.
                    valuationComparables = buildComparableEvidence(prop, false, ComparableDtos.Purpose.VALUATION_SUPPORT);
                } catch (RuntimeException ex) {
                    comparableDegraded = true;
                    valuationComparables = new ComparableEvidence("DEGRADED", 0, "NONE", List.of(),
                        List.of("Chưa tải được dữ liệu đối chiếu định giá."));
                }
            }

            List<String> itemWarnings = new ArrayList<>();
            for (String w : prop.warnings()) {
                if (criteria.includeResearch() || !containsResearchMetadata(w)) {
                    itemWarnings.add(w);
                }
            }
            if (researchRef && itemWarnings.stream().noneMatch(w -> w.contains("CC BY-NC 4.0"))) {
                itemWarnings.add(ComparableSourceClassifier.TINIX_ATTRIBUTION);
            }
            if (!withinStated) {
                itemWarnings.add("FLEXIBLE_BUDGET_ITEM: Giá rao cao hơn ngân sách gốc nhưng thuộc biên linh hoạt đã chọn.");
            }

            PropertyGisEnrichment gisEnrichment = gisByPropertyId.get(prop.id());
            LocationIntelligence locationIntel = gisEnrichment != null ? gisEnrichment.locationIntelligence() : null;
            AmenityEvidence effectiveAmenity = gisEnrichment != null && gisEnrichment.resolvedAmenityEvidence() != null
                ? gisEnrichment.resolvedAmenityEvidence()
                : prop.amenityEvidence();
            if (locationIntel != null
                    && !locationIntel.mapEligible()
                    && isPlatform
                    && "INVALID_DISTRICT_MISMATCH".equals(locationIntel.coordinateStatus())) {
                itemWarnings.add("GIS_COORDINATE_MISMATCH: " + locationIntel.fallbackReason());
            }

            advisedProperties.add(new AdvisedProperty(
                prop.id(),
                prop.title(),
                prop.propertyType(),
                prop.priceVnd(),
                prop.areaSqm(),
                prop.district(),
                prop.ward(),
                withinStated,
                withinFlexible,
                budgetDeltaPct,
                prop.score(),
                "HEURISTIC_FIT_UNCALIBRATED",
                prop.scoreBreakdown(),
                List.copyOf(fitReasons),
                safeSource,
                liveListing,
                researchRef,
                availabilityStatus,
                prop.qualityStatus(),
                prop.verificationStatus(),
                effectiveAmenity,
                locationIntel,
                compEvidence,
                valEvidence,
                valuationComparables,
                List.copyOf(itemWarnings)
            ));
        }

        if (comparableDegraded) {
            comparableServiceStatus = "DEGRADED";
            warnings.add("COMPARABLE_DEGRADED: Một phần truy vấn bất động sản tương đồng bị gián đoạn; kết quả đề xuất chính vẫn giữ nguyên.");
        }
        if (hasResearchComparable) {
            warnings.add("RESEARCH_COMPARABLES_LABEL: Các dòng so sánh mang nhãn TiniX (CC BY-NC 4.0) chỉ là dữ liệu tham chiếu nghiên cứu lịch sử, không phải tin đang rao bán.");
        }
        if (advisedProperties.isEmpty()) {
            warnings.add("NO_ELIGIBLE_CANDIDATES: Không có bất động sản đủ điều kiện khớp nhu cầu hiện tại; hệ thống không tự sinh dữ liệu giả để lấp đầy.");
        }

        boolean partial = "UNAVAILABLE".equals(valuationStatus) || "DEGRADED".equals(comparableServiceStatus);
        ServiceStatus serviceStatus = new ServiceStatus(
            "AVAILABLE",
            "AVAILABLE",
            comparableServiceStatus,
            valuationStatus,
            partial
        );

        int effectiveEligibleCount = criteria.includeResearch()
            ? recRes.eligibleCandidateCount()
            : (recRes.topProperties().size() == candidateProps.size()
                ? recRes.eligibleCandidateCount()
                : candidateProps.size());

        return new AdvisorResponse(
            ADVISOR_VERSION,
            criteria.includeResearch() ? "INTERNAL_RESEARCH" : "SAFE",
            recRes.method(),
            recRes.priceBasis(),
            SCORE_DISCLAIMER,
            criteria,
            serviceStatus,
            effectiveEligibleCount,
            recRes.scoringWeights(),
            effectiveAreas,
            areaLocationInsights,
            List.copyOf(advisedProperties),
            List.copyOf(warnings)
        );
    }

    private ComparableEvidence buildComparableEvidence(PropertyResult prop, boolean includeResearchMode,
                                                       ComparableDtos.Purpose purpose) {
        String typeName = prop.propertyType() == null ? null : prop.propertyType().name();
        if (!comparableEligibility.supportedType(typeName)) {
            return new ComparableEvidence(
                "SKIPPED_UNSUPPORTED_INPUT", 0, "NONE", List.of(),
                List.of("Loại bất động sản (" + typeName + ") chưa hỗ trợ đối chiếu tin tương đồng."));
        }
        String district = cleanFilter(prop.district());
        if (district == null) {
            return new ComparableEvidence(
                "SKIPPED_UNSUPPORTED_INPUT", 0, "NONE", List.of(),
                List.of("Thiếu thông tin quận/huyện để đối chiếu bất động sản tương đồng."));
        }
        boolean similar = purpose == ComparableDtos.Purpose.SIMILAR_LISTING;
        if (!comparableEligibility.plausibleArea(prop.areaSqm())
                || (similar && !comparableEligibility.plausiblePrice(prop.priceVnd()))) {
            return new ComparableEvidence(
                "SKIPPED_UNSUPPORTED_INPUT", 0, "NONE", List.of(),
                List.of("Diện tích hoặc giá rao nằm ngoài khung tham chiếu tương đồng tiêu chuẩn."));
        }

        // Compare the recommended listing's asking price, never the valuation evidence.
        String propertyId = "PROPERTY".equals(prop.source().kind()) ? prop.source().recordKey() : null;
        ComparableDtos.Request compReq = new ComparableDtos.Request(
            propertyId,
            typeName,
            district,
            cleanFilter(prop.ward()),
            prop.areaSqm(),
            similar ? prop.priceVnd() : null,
            null,
            null,
            COMPARABLES_PER_PROPERTY,
            null,
            purpose,
            null,
            comparableSubject(prop)
        );

        boolean allowTinix = includeResearchMode
            && isResearchEnabled()
            && allowResearchComparables
            && comparableService.isResearchEnabled();
        ComparableDtos.Response raw = comparableService.rank(compReq, allowTinix);

        List<ComparableItem> mapped = new ArrayList<>();
        for (ComparableDtos.Candidate c : raw.comparables()) {
            boolean isTinix = c.sourceKind() == ComparableDtos.SourceKind.TINIX_RESEARCH;
            if (isTinix && !allowTinix) continue;
            boolean isSmartProp = c.sourceKind() == ComparableDtos.SourceKind.SMARTPROP;
            String verification = isSmartProp ? "PLATFORM_PUBLISHED"
                : (isTinix ? "RESEARCH_REFERENCE_ONLY" : "EXTERNAL_VERIFIED");
            String url = sanitizeComparableUrl(c);
            mapped.add(new ComparableItem(
                c.candidateId(),
                c.sourceKind().name(),
                c.sourceLabel(),
                isSmartProp,
                isTinix,
                verification,
                c.propertyType(),
                c.district(),
                c.ward(),
                c.areaSqm(),
                c.askingPriceVnd(),
                c.priceDifferencePct(),
                c.bedrooms(),
                c.floors(),
                c.frontageM(),
                c.similarityScore(),
                "HEURISTIC_SIMILARITY_UNCALIBRATED",
                c.scoreBreakdown(),
                url,
                c.datasetLicense(),
                c.attribution()
            ));
        }

        List<String> compWarnings = raw.warnings().stream()
            .filter(w -> allowTinix || !containsResearchMetadata(w))
            .toList();
        String status = mapped.isEmpty() ? "EMPTY_NO_MATCHES" : "AVAILABLE";
        String stage = mapped.isEmpty() ? "NONE" : raw.searchStage();
        var cohort = raw.evidence();
        if (!allowTinix && cohort != null && (mapped.size() != raw.comparables().size()
                || cohort.caps().containsKey(ComparableDtos.SourceKind.TINIX_RESEARCH)
                || cohort.provenance().containsKey(ComparableDtos.SourceKind.TINIX_RESEARCH))) {
            cohort = null;
        }
        return new ComparableEvidence(status, mapped.size(), stage, List.copyOf(mapped), compWarnings, cohort);
    }

    private static ComparableDtos.SubjectIdentity comparableSubject(PropertyResult prop) {
        var source = prop.source();
        if ("TINIX_AI".equals(source.kind())) {
            return new ComparableDtos.SubjectIdentity(null, null, null, source.recordKey(), null);
        }
        if (!"EXTERNAL".equals(source.kind())) return null;
        Long externalId = null;
        if (prop.id() != null && prop.id().matches("external:[0-9]{1,18}")) {
            externalId = Long.valueOf(prop.id().substring("external:".length()));
        }
        return new ComparableDtos.SubjectIdentity(externalId, null, null, null, source.detailUrl());
    }

    private static boolean isPublicLiveCandidate(PropertyResult prop) {
        if (prop == null || prop.source() == null) return false;
        if ("TINIX_AI".equals(prop.source().kind()) || "HYBRID_ELIGIBLE_RESEARCH".equals(prop.qualityStatus())) {
            return false;
        }
        if ("PROPERTY".equals(prop.source().kind())) {
            return "PLATFORM_PUBLISHED".equals(prop.qualityStatus());
        }
        if ("EXTERNAL".equals(prop.source().kind())) {
            return "VALID".equals(prop.qualityStatus()) && "VERIFIED".equals(prop.verificationStatus());
        }
        return false;
    }

    private static boolean containsNonPublicMetadata(String text) {
        if (text == null) return false;
        return containsResearchMetadata(text)
            || text.startsWith("UNVERIFIED:")
            || text.startsWith("NEEDS_REVIEW:");
    }

    private static boolean containsResearchMetadata(String text) {
        if (text == null) return false;
        return text.contains("TiniX") || text.contains("TINIX") || text.contains("CC BY-NC")
            || text.startsWith("INTERNAL_DEMO:");
    }

    static ResolvedCriteria resolveCriteria(AdvisorRequest req) {
        int flex = req.budgetFlexibilityPct() == null ? 0 : req.budgetFlexibilityPct();
        if (flex < 0 || flex > 30) {
            throw ApiInputs.bad("Biên ngân sách linh hoạt phải từ 0% đến 30%.");
        }
        BigDecimal ceiling = flex == 0
            ? req.budgetVnd()
            : req.budgetVnd()
                .multiply(BigDecimal.valueOf(100L + flex))
                .divide(BigDecimal.valueOf(100L), 0, RoundingMode.HALF_UP)
                .min(MAX_CONTRACT_BUDGET);

        int limit = req.limit() == null ? DEFAULT_LIMIT : req.limit();
        if (limit < 1 || limit > 10) {
            throw ApiInputs.bad("Số lượng đề xuất tối đa phải từ 1 đến 10.");
        }
        String district = cleanFilter(req.district());
        String ward = district == null ? cleanFilter(req.ward()) : cleanFilter(req.ward());

        return new ResolvedCriteria(
            req.budgetVnd(),
            flex,
            ceiling,
            req.purpose(),
            req.propertyType() == null ? PropertyType.ALL : req.propertyType(),
            req.minAreaSqm(),
            district,
            ward,
            limit,
            req.includeComparables() == null || req.includeComparables(),
            req.includeValuation() == null || req.includeValuation(),
            Boolean.TRUE.equals(req.includeResearch())
        );
    }

    static String cleanFilter(String raw) {
        if (raw == null) return null;
        String trimmed = raw.strip();
        if (trimmed.isEmpty() || "ALL".equalsIgnoreCase(trimmed) || "Tất cả".equalsIgnoreCase(trimmed)) {
            return null;
        }
        return trimmed;
    }

    private static Source sanitizeSource(Source src, boolean researchRef) {
        if (src == null) return new Source("UNKNOWN", "Không rõ", "", null);
        if (researchRef || "TINIX_AI".equals(src.kind())) {
            return new Source("TINIX_AI", src.name(), src.recordKey(), null);
        }
        if ("PROPERTY".equals(src.kind())) {
            String safePath = src.recordKey() != null && src.recordKey().matches("[\\w-]{1,64}")
                ? "/listing/" + src.recordKey()
                : null;
            return new Source("PROPERTY", src.name(), src.recordKey(), safePath);
        }
        return new Source(src.kind(), src.name(), src.recordKey(), ComparableSourceClassifier.safeUrl(src.detailUrl()));
    }

    private static String sanitizeComparableUrl(ComparableDtos.Candidate c) {
        if (c.sourceKind() == ComparableDtos.SourceKind.TINIX_RESEARCH) {
            return null;
        }
        if (c.sourceKind() == ComparableDtos.SourceKind.SMARTPROP && c.listingUrl() != null) {
            if (c.listingUrl().startsWith("/properties/")) {
                String id = c.listingUrl().substring("/properties/".length());
                return id.matches("[\\w-]{1,64}") ? "/listing/" + id : null;
            }
            return c.listingUrl().matches("/listing/[\\w-]{1,64}") ? c.listingUrl() : null;
        }
        return ComparableSourceClassifier.safeUrl(c.listingUrl());
    }
}
