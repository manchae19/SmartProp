package vn.smartprop.comparable;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Map;

import org.springframework.stereotype.Service;

import vn.smartprop.common.ApiInputs;
import vn.smartprop.modules.property.Property;
import vn.smartprop.modules.property.PropertyRepository;

/**
 * Builds the comparable set for one reference property.
 *
 * Everything is read-only and bounded: the research table is 889 MB with only
 * five indexed columns, so candidates are pulled by a price band (two-phase
 * ids-then-details) and every other rule is applied in Java where it can be
 * unit-tested. Nothing here consults XGBoost or the predicted price, so the
 * ranking cannot confirm the model's own output.
 */
@Service
public class ComparableRankingService {

    /** Brief: at most five comparables, and never invent one to fill the list. */
    public static final int MAX_RESULTS = 5;

    /** A candidate must be within this area/price multiple of the reference. */
    static final BigDecimal ENVELOPE = new BigDecimal("2.5");

    /** 12 slices x 25 = 300 ids. A plain ORDER BY .. LIMIT inside a 0.4x-2.5x
     *  band only ever returns the cheapest (or dearest) rows, so the band is cut
     *  into slices and each slice is capped. Measured on the live table: 1,200
     *  ids costs 1.5-7.6 s of cold page reads per band, 300 costs about 2 s once
     *  and ~5 ms afterwards, while still sampling the whole range. */
    private static final int TINIX_PER_BUCKET = 25;
    private static final int TINIX_BUCKETS = 12;
    private static final int MAX_DISTRICTS = 8;

    private final ComparableCandidateRepository candidates;
    private final ComparableEligibilityService eligibility;
    private final PropertyRepository properties;

    public ComparableRankingService(ComparableCandidateRepository candidates,
                                    ComparableEligibilityService eligibility,
                                    PropertyRepository properties) {
        this.candidates = candidates;
        this.eligibility = eligibility;
        this.properties = properties;
    }

    /** Search tiers, ordered. The response reports the deepest tier that reached the result. */
    public enum Stage { WARD, DISTRICT, ADJACENT, NONE }

    public ComparableDtos.Response rank(ComparableDtos.Request request) {
        return rank(request, true);
    }

    public ComparableDtos.Response rank(ComparableDtos.Request request, boolean includeResearch) {
        int limit = limit(request.limit());
        ComparableDtos.Reference reference = reference(request);
        String type = normalizeType(reference.propertyType());
        BigDecimal refArea = reference.areaSqm();
        if (!eligibility.plausibleArea(refArea)) {
            throw ApiInputs.bad("Diện tích tham chiếu phải từ 5 đến 50.000 m².");
        }
        if (reference.priceVnd() != null && !eligibility.plausiblePrice(reference.priceVnd())) {
            throw ApiInputs.bad("Giá tham chiếu phải trong khoảng 200 triệu đến 1.000 tỷ VND.");
        }

        List<String> districts = searchDistricts(reference.district());
        BigDecimal minPrice = reference.priceVnd() == null
            ? ComparableEligibilityService.MIN_TOTAL_PRICE
            : reference.priceVnd().multiply(new BigDecimal("0.4"));
        BigDecimal maxPrice = reference.priceVnd() == null
            ? ComparableEligibilityService.MAX_TOTAL_PRICE
            : reference.priceVnd().multiply(new BigDecimal("2.5"));

        Scored scored = new Scored();
        if (includeResearch) {
            collectTinix(reference, type, districts, minPrice, maxPrice, scored);
        }
        collectExternal(reference, type, districts, minPrice, maxPrice, scored);
        collectSmartProp(reference, type, districts, minPrice, maxPrice, scored);

        // The default band is centred on the caller's price, which for the valuation
        // screen is the V6 estimate. If that band is too thin, widen it and search
        // again rather than answering "nothing comparable" because of our own model.
        // The reference district is still searched first and neighbours only ever
        // fill a shortfall, so a wrong estimate cannot move the answer to another district.
        if (scored.items.size() < limit && reference.priceVnd() != null) {
            BigDecimal wideMin = reference.priceVnd().multiply(new BigDecimal("0.1"));
            BigDecimal wideMax = reference.priceVnd().multiply(new BigDecimal("10"));
            if (includeResearch) {
                collectTinix(reference, type, districts, wideMin, wideMax, scored, true);
            }
            collectExternal(reference, type, districts, wideMin, wideMax, scored, true);
            collectSmartProp(reference, type, districts, wideMin, wideMax, scored, true);
        }

        List<ComparableDtos.Candidate> ranked = scored.items.stream()
            .sorted(Comparator.comparingDouble(Ranked::score).reversed())
            .limit(limit)
            .map(Ranked::candidate)
            .toList();

        Stage deepest = scored.items.stream()
            .sorted(Comparator.comparingDouble(Ranked::score).reversed())
            .limit(limit)
            .map(Ranked::stage)
            .max(Comparator.naturalOrder())
            .orElse(Stage.NONE);

        return new ComparableDtos.Response(
            reference, ranked.size(), deepest.name(), ranked,
            warnings(ranked, type),
            includeResearch ? candidates.eligibleCounts() : candidates.publicEligibleCounts());
    }

    // ---------------------------------------------------------------- sources

    private void collectTinix(ComparableDtos.Reference ref, String type, List<String> districts,
                              BigDecimal minPrice, BigDecimal maxPrice, Scored out) {
        collectTinix(ref, type, districts, minPrice, maxPrice, out, false);
    }

    private void collectTinix(ComparableDtos.Reference ref, String type, List<String> districts,
                              BigDecimal minPrice, BigDecimal maxPrice, Scored out, boolean wide) {
        List<String> ids = candidates.tinixIdsInPriceBand(minPrice, maxPrice, TINIX_PER_BUCKET, TINIX_BUCKETS);
        if (ids.isEmpty()) return;

        ComparableSimilarityScorer.Input reference = input(ref);
        for (ComparableCandidateRepository.TinixRow row : candidates.tinixDetails(ids)) {
            String rowType = normalizeType(row.propertyType());
            if (!eligibility.supportedType(rowType) || !rowType.equals(type)) continue;
            if (!eligibility.plausiblePrice(row.priceVnd()) || !eligibility.plausibleArea(row.areaSqm())) continue;
            if (!eligibility.notSelf(ref.propertyId(), row.internalId())) continue;
            if (!eligibility.withinEnvelope(ref.areaSqm(), row.areaSqm(), ENVELOPE)) continue;
            if (!wide && ref.priceVnd() != null
                    && !eligibility.withinEnvelope(ref.priceVnd(), row.priceVnd(), ENVELOPE)) continue;
            Stage stage = stageOf(ref.district(), ref.ward(), row.district(), row.ward());
            if (stage == Stage.NONE) continue;
            if (out.contains(row.internalId())) continue;

            ComparableSimilarityScorer.Result result = ComparableSimilarityScorer.score(
                reference, new ComparableSimilarityScorer.Input(
                    row.district(), row.ward(), rowType, row.areaSqm(), row.priceVnd(),
                    wholeOrNull(row.bedrooms()), wholeOrNull(row.floors()), row.frontageM()));
            out.add(new Ranked(new ComparableDtos.Candidate(
                row.internalId(),
                ComparableDtos.SourceKind.TINIX_RESEARCH,
                ComparableSourceClassifier.TINIX_ATTRIBUTION,
                rowType, row.district(), row.ward(), row.areaSqm(), row.priceVnd(),
                differencePct(ref.priceVnd(), row.priceVnd()),
                wholeOrNull(row.bedrooms()), wholeOrNull(row.floors()), row.frontageM(), row.roadWidthM(),
                round(result.score()), result.breakdown(),
                "HYBRID_ELIGIBLE_RESEARCH", null, "CC BY-NC 4.0",
                ComparableSourceClassifier.TINIX_ATTRIBUTION), stage, result.score()));
        }
    }

    private void collectExternal(ComparableDtos.Reference ref, String type, List<String> districts,
                                 BigDecimal minPrice, BigDecimal maxPrice, Scored out) {
        collectExternal(ref, type, districts, minPrice, maxPrice, out, false);
    }

    private void collectExternal(ComparableDtos.Reference ref, String type, List<String> districts,
                                 BigDecimal minPrice, BigDecimal maxPrice, Scored out, boolean wide) {
        String category = externalCategory(type);
        if (category == null) return;
        ComparableSimilarityScorer.Input reference = input(ref);
        for (String district : districts) {
            for (ComparableCandidateRepository.ExternalRow row :
                    candidates.externalCandidates(district, category, minPrice, maxPrice, 400)) {
                if (!eligibility.plausiblePrice(row.priceVnd()) || !eligibility.plausibleArea(row.areaSqm())) continue;
                if (!eligibility.withinEnvelope(ref.areaSqm(), row.areaSqm(), ENVELOPE)) continue;
                if (!wide && ref.priceVnd() != null
                        && !eligibility.withinEnvelope(ref.priceVnd(), row.priceVnd(), ENVELOPE)) continue;
                Stage stage = stageOf(ref.district(), ref.ward(), row.district(), null);
                if (stage == Stage.NONE) continue;
                if (out.contains("external:" + row.id())) continue;

                ComparableSimilarityScorer.Result result = ComparableSimilarityScorer.score(
                    reference, new ComparableSimilarityScorer.Input(
                        row.district(), null, type, row.areaSqm(), row.priceVnd(), null, null, null));
                out.add(new Ranked(new ComparableDtos.Candidate(
                    "external:" + row.id(),
                    ComparableDtos.SourceKind.EXTERNAL_LISTING,
                    ComparableSourceClassifier.externalLabel(row.source()),
                    type, row.district(), null, row.areaSqm(), row.priceVnd(),
                    differencePct(ref.priceVnd(), row.priceVnd()),
                    null, null, null, null,
                    round(result.score()), result.breakdown(),
                    row.qualityStatus(), ComparableSourceClassifier.safeUrl(row.detailUrl()), null, null),
                    stage, result.score()));
            }
        }
    }

    private void collectSmartProp(ComparableDtos.Reference ref, String type, List<String> districts,
                                  BigDecimal minPrice, BigDecimal maxPrice, Scored out) {
        collectSmartProp(ref, type, districts, minPrice, maxPrice, out, false);
    }

    private void collectSmartProp(ComparableDtos.Reference ref, String type, List<String> districts,
                                  BigDecimal minPrice, BigDecimal maxPrice, Scored out, boolean wide) {
        ComparableSimilarityScorer.Input reference = input(ref);
        for (ComparableCandidateRepository.PropertyRow row :
                candidates.propertyCandidates(districts, type, minPrice, maxPrice, 200)) {
            if (!eligibility.notSelf(ref.propertyId(), row.id())) continue;
            if (!eligibility.plausiblePrice(row.priceVnd()) || !eligibility.plausibleArea(row.areaSqm())) continue;
            if (!eligibility.withinEnvelope(ref.areaSqm(), row.areaSqm(), ENVELOPE)) continue;
            if (!wide && ref.priceVnd() != null
                    && !eligibility.withinEnvelope(ref.priceVnd(), row.priceVnd(), ENVELOPE)) continue;
            Stage stage = stageOf(ref.district(), ref.ward(), row.district(), row.ward());
            if (stage == Stage.NONE) continue;
            if (out.contains("property:" + row.id())) continue;

            ComparableSimilarityScorer.Result result = ComparableSimilarityScorer.score(
                reference, new ComparableSimilarityScorer.Input(
                    row.district(), row.ward(), type, row.areaSqm(), row.priceVnd(),
                    row.bedrooms(), null, null));
            out.add(new Ranked(new ComparableDtos.Candidate(
                "property:" + row.id(),
                ComparableDtos.SourceKind.SMARTPROP,
                ComparableSourceClassifier.smartPropLabel(),
                type, row.district(), row.ward(), row.areaSqm(), row.priceVnd(),
                differencePct(ref.priceVnd(), row.priceVnd()),
                row.bedrooms(), null, null, null,
                round(result.score()), result.breakdown(),
                "PUBLISHED", "/properties/" + row.id(), null, null), stage, result.score()));
        }
    }

    // --------------------------------------------------------------- reference

    private ComparableDtos.Reference reference(ComparableDtos.Request request) {
        if (request.propertyId() != null && !request.propertyId().isBlank()) {
            String id = ApiInputs.uuid(request.propertyId());
            Property property = properties.findByIdAndDeletedAtIsNull(id)
                .filter(item -> item.status == Property.Status.PUBLISHED)
                .filter(item -> item.transactionType == Property.Transaction.SALE)
                .filter(item -> item.priceUnit == Property.PriceUnit.TOTAL)
                .orElseThrow(ApiInputs::missing);
            return new ComparableDtos.Reference(
                property.id, property.propertyType.name(), property.district, property.ward,
                property.areaSqm, property.price, (int) (property.bedrooms == null ? 0 : property.bedrooms), null);
        }
        String district = trimmed(request.district());
        if (district == null) throw ApiInputs.bad("Cần chọn địa bàn (quận/huyện) cho bất động sản tham chiếu.");
        String type = normalizeType(request.propertyType());
        if (!eligibility.supportedType(type)) {
            throw ApiInputs.bad("Loại bất động sản phải là HOUSE, APARTMENT, LAND hoặc VILLA.");
        }
        if (!eligibility.plausibleArea(request.areaSqm())) {
            throw ApiInputs.bad("Diện tích tham chiếu phải từ 5 đến 50.000 m².");
        }
        return new ComparableDtos.Reference(null, type, district, trimmed(request.ward()),
            request.areaSqm(), request.priceVnd(),
            request.bedrooms(), request.floors());
    }

    private static ComparableSimilarityScorer.Input input(ComparableDtos.Reference ref) {
        return new ComparableSimilarityScorer.Input(
            ref.district(), ref.ward(), normalizeType(ref.propertyType()),
            ref.areaSqm(), ref.priceVnd(), ref.bedrooms(), ref.floors(), null);
    }

    /** Same district first, then its neighbours - the widest tier we will ever search. */
    static List<String> searchDistricts(String district) {
        List<String> out = new ArrayList<>();
        String own = trimmed(district);
        if (own == null) return out;
        out.add(own);
        for (String neighbour : ComparableSimilarityScorer.neighboursOf(own)) {
            if (out.size() >= MAX_DISTRICTS) break;
            if (!out.contains(neighbour)) out.add(neighbour);
        }
        return out;
    }

    private static Stage stageOf(String refDistrict, String refWard, String district, String ward) {
        String own = trimmed(refDistrict);
        if (own == null || district == null) return Stage.NONE;
        // The two tables disagree on casing, and TiniX ward is often NULL.
        boolean sameDistrict = own.equalsIgnoreCase(district.strip());
        if (!sameDistrict) {
            return ComparableSimilarityScorer.areNeighbours(own, district.strip()) ? Stage.ADJACENT : Stage.NONE;
        }
        String refW = trimmed(refWard), rowW = trimmed(ward);
        return refW != null && refW.equalsIgnoreCase(rowW) ? Stage.WARD : Stage.DISTRICT;
    }

    // ------------------------------------------------------------------ utils

    private static int limit(Integer requested) {
        if (requested == null) return MAX_RESULTS;
        if (requested < 1 || requested > MAX_RESULTS) {
            throw ApiInputs.bad("limit phải từ 1 đến " + MAX_RESULTS + ".");
        }
        return requested;
    }

    private static String normalizeType(String type) {
        return type == null ? null : type.strip().toUpperCase(Locale.ROOT);
    }

    private static String externalCategory(String type) {
        return switch (type == null ? "" : type) {
            case "HOUSE", "VILLA" -> "Nhà ở";
            case "LAND" -> "Đất nền";
            case "APARTMENT" -> "Căn hộ chung cư";
            default -> null;
        };
    }

    private static String trimmed(String value) {
        if (value == null) return null;
        String out = value.strip();
        return out.isEmpty() ? null : out;
    }

    private static BigDecimal differencePct(BigDecimal reference, BigDecimal candidate) {
        if (reference == null || candidate == null || reference.signum() <= 0) return null;
        return candidate.subtract(reference)
            .multiply(new BigDecimal("100"))
            .divide(reference, 1, RoundingMode.HALF_UP);
    }

    /** TiniX stores these as DOUBLE; round half up so 3.4 floors is not silently 3. */
    private static Integer wholeOrNull(BigDecimal value) {
        return value == null ? null : value.setScale(0, RoundingMode.HALF_UP).intValue();
    }

    private static double round(double value) {
        return new BigDecimal(value).setScale(4, RoundingMode.HALF_UP).doubleValue();
    }

    private static List<String> warnings(List<ComparableDtos.Candidate> ranked, String type) {
        List<String> out = new ArrayList<>();
        if (ranked.isEmpty()) {
            out.add("Không tìm thấy bất động sản tương đồng nào trong dữ liệu hiện có. "
                  + "Hãy nới diện tích hoặc chọn địa bàn khác.");
        }
        boolean tinix = ranked.stream().anyMatch(c -> c.sourceKind() == ComparableDtos.SourceKind.TINIX_RESEARCH);
        if (tinix) {
            out.add(ComparableSourceClassifier.TINIX_ATTRIBUTION);
            out.add("Dòng TiniX là dữ liệu nghiên cứu, không phải tin đang rao bán; "
                  + "không có thông tin liên hệ và không xác minh được tình trạng giao dịch.");
        }
        if (ranked.stream().anyMatch(c -> "EXTERNAL_LISTING".equals(c.sourceKind().name())
                && c.listingUrl() == null)) {
            out.add("Một số tin bên ngoài không có liên kết gốc hợp lệ nên chỉ hiển thị dạng tham khảo.");
        }
        if ("LAND".equals(type) && ranked.stream().anyMatch(c -> c.bedrooms() != null)) {
            out.add("Đất nền thường không có số phòng ngủ; các trường trống được bỏ khỏi điểm tương đồng.");
        }
        return List.copyOf(out);
    }

    private record Ranked(ComparableDtos.Candidate candidate, Stage stage, double score) {}

    private static final class Scored {
        private final List<Ranked> items = new ArrayList<>();
        void add(Ranked value) { items.add(value); }
        /** Different sources share ids only by accident; this only dedupes the wide re-scan. */
        boolean contains(String candidateId) {
            return items.stream().anyMatch(r -> r.candidate().candidateId().equals(candidateId));
        }
    }
}
