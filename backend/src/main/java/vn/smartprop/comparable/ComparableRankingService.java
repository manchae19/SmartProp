package vn.smartprop.comparable;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import vn.smartprop.common.ApiInputs;
import vn.smartprop.modules.property.Property;
import vn.smartprop.modules.property.PropertyRepository;

import static vn.smartprop.comparable.ComparableDtos.*;
import static vn.smartprop.comparable.ComparableEligibilityService.*;

/** Strict locality and eligibility precede the per-source caps. Research is separately opt-in. */
@Service
public class ComparableRankingService {
    public static final int MAX_RESULTS = 5;
    static final BigDecimal ENVELOPE = new BigDecimal("2.5");
    private static final BigDecimal MIN_RATIO = new BigDecimal("0.4");
    private static final SubjectIdentity EMPTY_SUBJECT = new SubjectIdentity(null, null, null, null, null);

    private final ComparableCandidateRepository candidates;
    private final ComparableEligibilityService eligibility;
    private final PropertyRepository properties;
    private final boolean researchEnabled;

    @Autowired
    public ComparableRankingService(ComparableCandidateRepository candidates,
                                    ComparableEligibilityService eligibility,
                                    PropertyRepository properties,
                                    @Value("${app.comparable.research-enabled:false}") boolean researchEnabled) {
        this.candidates = candidates;
        this.eligibility = eligibility;
        this.properties = properties;
        this.researchEnabled = researchEnabled;
    }

    public ComparableRankingService(ComparableCandidateRepository candidates,
                                    ComparableEligibilityService eligibility,
                                    PropertyRepository properties) {
        this(candidates, eligibility, properties, false);
    }

    public boolean isResearchEnabled() {
        return researchEnabled;
    }

    /** ADJACENT is retained for response compatibility. Strict retrieval never produces it. */
    public enum Stage { WARD, DISTRICT, ADJACENT, NONE }

    public Response rank(Request request) {
        if (request != null && Boolean.TRUE.equals(request.includeResearch())) throw ApiInputs.forbidden();
        return computeRank(request, false);
    }

    public Response rankResearch(Request request) {
        if (!researchEnabled) throw ApiInputs.forbidden();
        return computeRank(request, true);
    }

    public Response rank(Request request, boolean includeResearch) {
        return includeResearch ? rankResearch(request) : rank(request);
    }

    private Response computeRank(Request request, boolean includeResearch) {
        if (request == null) throw ApiInputs.bad("Thiếu tiêu chí tìm tin tương đồng.");
        int limit = request.limit() == null ? MAX_RESULTS : request.limit();
        if (limit < 1 || limit > MAX_RESULTS) throw ApiInputs.bad("limit phải từ 1 đến " + MAX_RESULTS + ".");
        // Legacy callers supplied an asking price for similar-listing lookup.
        Purpose purpose = request.purpose() == null ? Purpose.SIMILAR_LISTING : request.purpose();
        Reference reference = reference(request, purpose);
        BigDecimal price = reference.priceVnd();
        BigDecimal budget = buyerBudget(request, purpose);
        SubjectIdentity raw = request.subjectIdentity() == null ? EMPTY_SUBJECT : request.subjectIdentity();
        SubjectIdentity subject = new SubjectIdentity(raw.externalId(), ComparableIdentity.text(raw.externalSource()),
            ComparableIdentity.text(raw.sourceListingId()), ComparableIdentity.text(raw.tinixId()), raw.canonicalUrl());
        Set<ComparableIdentity.Key> subjectKeys = ComparableIdentity.subject(reference.propertyId(), subject);

        BigDecimal minPrice = price == null ? MIN_TOTAL_PRICE : MIN_TOTAL_PRICE.max(price.multiply(MIN_RATIO));
        BigDecimal maxPrice = price == null ? MAX_TOTAL_PRICE : MAX_TOTAL_PRICE.min(price.multiply(ENVELOPE));
        if (budget != null) maxPrice = maxPrice.min(budget);
        var search = new ComparableCandidateRepository.Search(reference.district(), reference.ward(), reference.propertyType(),
            reference.areaSqm(), MIN_AREA.max(reference.areaSqm().multiply(MIN_RATIO)),
            MAX_AREA.min(reference.areaSqm().multiply(ENVELOPE)), minPrice, maxPrice, reference.propertyId(), subject);

        List<Ranked> rows = new ArrayList<>();
        collect(reference, search, includeResearch, rows);
        List<Ranked> unique = dedupe(rows, reference, subjectKeys);
        // Only SIMILAR_LISTING can use the older asking-price widening policy.
        if (unique.size() < limit && price != null) {
            var wider = new ComparableCandidateRepository.Search(search.district(), search.ward(), search.type(), search.area(),
                search.minArea(), search.maxArea(), MIN_TOTAL_PRICE.max(price.movePointLeft(1)),
                MAX_TOTAL_PRICE.min(price.movePointRight(1)), search.propertyId(), search.subject());
            collect(reference, wider, includeResearch, rows);
            unique = dedupe(rows, reference, subjectKeys);
        }

        List<Ranked> top = unique.stream().limit(limit).toList();
        List<Candidate> ranked = top.stream().map(Ranked::candidate).toList();
        Stage deepest = top.stream().map(Ranked::stage).max(Comparator.naturalOrder()).orElse(Stage.NONE);
        return new Response(reference, ranked.size(), deepest.name(), ranked, warnings(ranked, reference.propertyType()),
            includeResearch ? candidates.eligibleCounts() : candidates.publicEligibleCounts());
    }

    private void collect(Reference ref, ComparableCandidateRepository.Search search, boolean includeResearch, List<Ranked> rows) {
        if (search.maxPrice().compareTo(search.minPrice()) < 0) return;
        for (var row : candidates.propertyCandidates(search, 200)) {
            if (ComparableIdentity.text(row.id()) == null) continue;
            add(rows, ref, search, new Listing("property:" + row.id(), SourceKind.SMARTPROP, ComparableSourceClassifier.smartPropLabel(),
                row.propertyType(), row.district(), row.ward(), row.areaSqm(), row.priceVnd(), row.bedrooms(),
                null, null, null, "PUBLISHED", "/properties/" + row.id(), null, null,
                ComparableIdentity.keys("property:" + row.id(), null, null, null, null)));
        }
        String category = externalCategory(search.type());
        if (search.ward() == null && category != null) {
            for (var row : candidates.externalCandidates(search, category, 400)) {
                if (!"VALID".equals(row.qualityStatus()) || !category.equals(row.propertyType())) continue;
                String id = "external:" + row.id();
                add(rows, ref, search, new Listing(id, SourceKind.EXTERNAL_LISTING,
                    ComparableSourceClassifier.externalLabel(row.source()), search.type(), row.district(), null,
                    row.areaSqm(), row.priceVnd(), null, null, null, null, row.qualityStatus(),
                    ComparableSourceClassifier.safeUrl(row.detailUrl()), null, null,
                    ComparableIdentity.keys(id, ComparableIdentity.externalNamespace(row.source()),
                        row.sourceListingId(), row.duplicateGroup(), row.detailUrl())));
            }
        }
        if (includeResearch) {
            for (var row : candidates.tinixCandidates(search, 300)) {
                if (ComparableIdentity.text(row.internalId()) == null) continue;
                String id = "tinix:" + row.internalId();
                add(rows, ref, search, new Listing(id, SourceKind.TINIX_RESEARCH, ComparableSourceClassifier.TINIX_ATTRIBUTION,
                    row.propertyType(), row.district(), row.ward(), row.areaSqm(), row.priceVnd(), wholeOrNull(row.bedrooms()),
                    wholeOrNull(row.floors()), row.frontageM(), row.roadWidthM(), "HYBRID_ELIGIBLE_RESEARCH", null,
                    "CC BY-NC 4.0", ComparableSourceClassifier.TINIX_ATTRIBUTION,
                    ComparableIdentity.keys(id, "tinix", row.internalId(), row.duplicateGroup(), null)));
            }
        }
    }

    private void add(List<Ranked> rows, Reference ref, ComparableCandidateRepository.Search search, Listing row) {
        String type = normalizeType(row.type());
        if (!ref.propertyType().equals(type) || !sameLocality(ref.district(), row.district())
                || (ref.ward() != null && !sameLocality(ref.ward(), row.ward()))
                || !eligibility.plausibleArea(row.area()) || !eligibility.plausiblePrice(row.price())
                || row.area().compareTo(search.minArea()) < 0 || row.area().compareTo(search.maxArea()) > 0
                || row.price().compareTo(search.minPrice()) < 0 || row.price().compareTo(search.maxPrice()) > 0) return;

        var result = ComparableSimilarityScorer.score(
            new ComparableSimilarityScorer.Input(ref.district(), ref.ward(), type, ref.areaSqm(),
                ref.priceVnd(), ref.bedrooms(), ref.floors(), null),
            new ComparableSimilarityScorer.Input(row.district(), row.ward(), type, row.area(), row.price(),
                row.bedrooms(), row.floors(), row.frontage()));
        var candidate = new Candidate(row.id(), row.kind(), row.sourceLabel(), type, row.district(), row.ward(),
            row.area(), row.price(), differencePct(ref.priceVnd(), row.price()), row.bedrooms(), row.floors(),
            row.frontage(), row.roadWidth(), BigDecimal.valueOf(result.score()).setScale(4, RoundingMode.HALF_UP).doubleValue(),
            result.breakdown(), row.quality(), row.url(), row.license(), row.attribution());
        Stage stage = ref.ward() == null ? Stage.DISTRICT : Stage.WARD;
        rows.add(new Ranked(candidate, stage, result.score(), row.keys()));
    }

    private static List<Ranked> dedupe(List<Ranked> rows, Reference ref, Set<ComparableIdentity.Key> subjectKeys) {
        // Connect all trusted aliases before selecting winners. A dropped bridge row may carry a new key.
        int[] parent = new int[rows.size() + 1];
        int subject = rows.size();
        for (int i = 0; i < parent.length; i++) parent[i] = i;
        Map<ComparableIdentity.Key, Integer> owners = new HashMap<>();
        subjectKeys.forEach(key -> owners.put(key, subject));
        for (int i = 0; i < rows.size(); i++) {
            for (var key : rows.get(i).keys()) {
                Integer previous = owners.putIfAbsent(key, i);
                if (previous != null) parent[root(parent, previous)] = root(parent, i);
            }
        }

        Comparator<Ranked> order = Comparator.comparingDouble(Ranked::score).reversed()
            .thenComparing(Ranked::stage)
            .thenComparing(r -> r.candidate().areaSqm().subtract(ref.areaSqm()).abs())
            .thenComparing(r -> r.candidate().sourceKind())
            .thenComparing(r -> r.candidate().candidateId());
        int subjectRoot = root(parent, subject);
        Map<Integer, Ranked> winners = new HashMap<>();
        for (int i = 0; i < rows.size(); i++) {
            int group = root(parent, i);
            if (group != subjectRoot) winners.merge(group, rows.get(i), (a, b) -> order.compare(a, b) <= 0 ? a : b);
        }
        return winners.values().stream().sorted(order).toList();
    }

    private static int root(int[] parent, int item) {
        while (parent[item] != item) {
            parent[item] = parent[parent[item]];
            item = parent[item];
        }
        return item;
    }

    private Reference reference(Request request, Purpose purpose) {
        String id = ComparableIdentity.text(request.propertyId());
        if (id != null) {
            Instant now = Instant.now();
            Property property = properties.findByIdAndDeletedAtIsNull(ApiInputs.uuid(id))
                .filter(item -> item.status == Property.Status.PUBLISHED && item.deletedAt == null)
                .filter(item -> item.expiresAt == null || item.expiresAt.isAfter(now))
                .filter(item -> item.transactionType == Property.Transaction.SALE
                    && item.priceUnit == Property.PriceUnit.TOTAL && "VND".equals(item.currency))
                .orElseThrow(ApiInputs::missing);
            return checkedReference(property.id, property.propertyType == null ? null : property.propertyType.name(),
                property.district, property.ward, property.areaSqm, purpose == Purpose.SIMILAR_LISTING ? property.price : null,
                property.bedrooms == null ? null : property.bedrooms.intValue(), null);
        }
        return checkedReference(null, request.propertyType(), request.district(), request.ward(), request.areaSqm(),
            purpose == Purpose.SIMILAR_LISTING ? request.priceVnd() : null, request.bedrooms(), request.floors());
    }

    private Reference checkedReference(String id, String type, String district, String ward, BigDecimal area,
                                       BigDecimal price, Integer bedrooms, Integer floors) {
        String locality = ComparableIdentity.text(district), normalizedType = normalizeType(type);
        if (locality == null) throw ApiInputs.bad("Cần chọn địa bàn (quận/huyện) cho bất động sản tham chiếu.");
        if (!eligibility.supportedType(normalizedType)) {
            throw ApiInputs.bad("Loại bất động sản phải là HOUSE, APARTMENT, LAND hoặc VILLA.");
        }
        if (!eligibility.plausibleArea(area)) throw ApiInputs.bad("Diện tích tham chiếu phải từ 5 đến 50.000 m².");
        if (price != null && !eligibility.plausiblePrice(price)) {
            throw ApiInputs.bad("Giá tham chiếu phải trong khoảng 200 triệu đến 1.000 tỷ VND.");
        }
        return new Reference(id, normalizedType, locality, ComparableIdentity.text(ward), area, price, bedrooms, floors);
    }

    private static BigDecimal buyerBudget(Request request, Purpose purpose) {
        if (purpose != Purpose.BUYER_BUDGET_SEARCH) return null;
        BigDecimal budget = request.buyerBudgetVnd() == null ? request.priceVnd() : request.buyerBudgetVnd();
        if (budget == null || budget.signum() <= 0) throw ApiInputs.bad("Cần ngân sách mua hợp lệ.");
        return budget;
    }

    private static String normalizeType(String type) {
        return type == null ? null : type.strip().toUpperCase(Locale.ROOT);
    }

    private static boolean sameLocality(String a, String b) {
        return a.equalsIgnoreCase(ComparableIdentity.text(b));
    }

    private static String externalCategory(String type) {
        return switch (type) {
            case "HOUSE" -> "Nhà ở";
            case "LAND" -> "Đất nền";
            case "APARTMENT" -> "Căn hộ chung cư";
            default -> null;
        };
    }

    private static BigDecimal differencePct(BigDecimal reference, BigDecimal candidate) {
        if (reference == null) return null;
        return candidate.subtract(reference).movePointRight(2).divide(reference, 1, RoundingMode.HALF_UP);
    }

    private static Integer wholeOrNull(BigDecimal value) {
        return value == null ? null : value.setScale(0, RoundingMode.HALF_UP).intValue();
    }

    private static List<String> warnings(List<Candidate> ranked, String type) {
        List<String> out = new ArrayList<>();
        if (ranked.isEmpty()) {
            out.add("Không tìm thấy bất động sản tương đồng nào trong dữ liệu hiện có. Hãy nới diện tích hoặc chọn địa bàn khác.");
        }
        if (ranked.stream().anyMatch(c -> c.sourceKind() == SourceKind.TINIX_RESEARCH)) {
            out.add(ComparableSourceClassifier.TINIX_ATTRIBUTION);
            out.add("Dòng TiniX là dữ liệu nghiên cứu, không phải tin đang rao bán; không có thông tin liên hệ và không xác minh được tình trạng giao dịch.");
        }
        if (ranked.stream().anyMatch(c -> c.sourceKind() == SourceKind.EXTERNAL_LISTING && c.listingUrl() == null)) {
            out.add("Một số tin bên ngoài không có liên kết gốc hợp lệ nên chỉ hiển thị dạng tham khảo.");
        }
        if ("LAND".equals(type) && ranked.stream().anyMatch(c -> c.bedrooms() != null)) {
            out.add("Đất nền thường không có số phòng ngủ; các trường trống được bỏ khỏi điểm tương đồng.");
        }
        for (int i = 0; i < ranked.size(); i++) {
            for (int j = i + 1; j < ranked.size(); j++) {
                Candidate a = ranked.get(i), b = ranked.get(j);
                if (close(a.areaSqm(), b.areaSqm(), "0.02") && close(a.askingPriceVnd(), b.askingPriceVnd(), "0.03")) {
                    out.add("POSSIBLE_SAME_ENTITY: " + a.candidateId() + " / " + b.candidateId());
                }
            }
        }
        return List.copyOf(out);
    }

    private static boolean close(BigDecimal a, BigDecimal b, String tolerance) {
        return a.subtract(b).abs().compareTo(a.max(b).multiply(new BigDecimal(tolerance))) <= 0;
    }

    private record Ranked(Candidate candidate, Stage stage, double score, Set<ComparableIdentity.Key> keys) {}

    private record Listing(String id, SourceKind kind, String sourceLabel, String type, String district, String ward,
                           BigDecimal area, BigDecimal price, Integer bedrooms, Integer floors, BigDecimal frontage,
                           BigDecimal roadWidth, String quality, String url, String license, String attribution,
                           Set<ComparableIdentity.Key> keys) {}
}
