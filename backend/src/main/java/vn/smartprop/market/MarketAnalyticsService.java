package vn.smartprop.market;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Service;
import vn.smartprop.common.ApiInputs;
import vn.smartprop.market.MarketAnalyticsCalculator.GroupRow;
import vn.smartprop.market.MarketAnalyticsRepository.CohortRow;
import vn.smartprop.market.MarketDtos.Band;
import vn.smartprop.market.MarketDtos.Filters;
import vn.smartprop.market.MarketDtos.Meta;
import vn.smartprop.market.MarketDtos.MonthlyPoint;
import vn.smartprop.market.MarketDtos.Query;
import vn.smartprop.market.MarketDtos.Response;
import vn.smartprop.market.MarketDtos.Source;
import vn.smartprop.market.MarketDtos.SourceCount;
import vn.smartprop.market.MarketDtos.Stat;

/**
 * Step 21.5B — Real-Data Market Analytics service.
 *
 * <p>Reports descriptive statistics of <b>asking prices</b> from live MySQL rows.
 * There is deliberately <b>no forecasting</b> and no growth-rate claim: the temporal
 * series only describes asking prices recorded in a single research snapshot.
 *
 * <p>The real cohort is loaded once per dataset (with/without research) and cached
 * for {@link #COHORT_TTL_MILLIS}; user filters are applied in memory and statistics
 * are computed in Java. A request therefore never re-scans TiniX.
 */
@Service
public class MarketAnalyticsService {

    public static final int MIN_SAMPLE = 30;
    private static final int MAX_WARD_CELLS = 50;
    private static final long RESPONSE_TTL_MILLIS = 10 * 60 * 1000L;
    private static final long COHORT_TTL_MILLIS = 6 * 60 * 60 * 1000L;
    private static final int MAX_CACHE_ENTRIES = 64;

    private static final Set<String> ALLOWED_TYPES = Set.of("HOUSE", "APARTMENT", "LAND", "VILLA");

    private static final String DISCLAIMER =
        "Tất cả số liệu là GIÁ RAO BÁN tổng hợp từ dữ liệu thật trong MySQL, không phải giá giao dịch. "
        + "Trung vị (median) được dùng thay cho trung bình cộng để giảm ảnh hưởng của outlier. "
        + "Đây là thống kê mô tả, KHÔNG phải dự báo giá và không phải chỉ số tăng giá thị trường.";

    private static final String RESEARCH_LICENSE = "CC BY-NC 4.0";

    private static final String[] PRICE_BAND_LABELS = {
        "< 1 tỷ", "1–2 tỷ", "2–3 tỷ", "3–5 tỷ", "5–10 tỷ", "10–20 tỷ", "20–50 tỷ", "≥ 50 tỷ"
    };
    private static final String[] AREA_BAND_LABELS = {
        "< 30 m²", "30–50 m²", "50–80 m²", "80–120 m²", "120–200 m²", "200–500 m²", "≥ 500 m²"
    };

    private record Cached(Response response, long expiresAt) {}

    private record Cohort(List<CohortRow> rows, long loadedAt) {}

    private record CacheKey(
        boolean researchScope,
        String district,
        String ward,
        String propertyType,
        Source source,
        boolean includeResearch
    ) {}

    private final MarketAnalyticsRepository repository;
    private final boolean researchEnabled;
    private final ConcurrentHashMap<CacheKey, Cached> publicResponseCache = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<CacheKey, Cached> researchResponseCache = new ConcurrentHashMap<>();
    private volatile Cohort researchCohort;
    private volatile Cohort safeCohort;

    @org.springframework.beans.factory.annotation.Autowired
    public MarketAnalyticsService(
            MarketAnalyticsRepository repository,
            @org.springframework.beans.factory.annotation.Value("${app.market.research-enabled:false}") boolean researchEnabled) {
        this.repository = repository;
        this.researchEnabled = researchEnabled;
    }

    public MarketAnalyticsService(MarketAnalyticsRepository repository) {
        this(repository, false);
    }

    public boolean isResearchEnabled() {
        return researchEnabled;
    }

    public static boolean requestsResearch(String source, Boolean includeResearch) {
        if (Boolean.TRUE.equals(includeResearch)) return true;
        return source != null && "TINIX_RESEARCH".equalsIgnoreCase(source.strip());
    }

    /** Public entrypoint: fails closed if research data or source is requested. */
    public Response analytics(String district, String ward, String propertyType, String source, Boolean includeResearch) {
        if (requestsResearch(source, includeResearch)) {
            throw ApiInputs.forbidden();
        }
        Query q = validate(district, ward, propertyType, source, false);
        return cachedOrCompute(q, false, publicResponseCache);
    }

    /** Authorized research entrypoint: requires server-side research flag to be enabled. */
    public Response analyticsResearch(String district, String ward, String propertyType, String source, Boolean includeResearch) {
        if (!researchEnabled) {
            throw ApiInputs.forbidden();
        }
        Query q = validate(district, ward, propertyType, source, includeResearch);
        if (!q.includeResearch()) {
            return cachedOrCompute(q, false, publicResponseCache);
        }
        return cachedOrCompute(q, true, researchResponseCache);
    }

    private Response cachedOrCompute(Query q, boolean researchScope, ConcurrentHashMap<CacheKey, Cached> cache) {
        CacheKey key = new CacheKey(researchScope, q.district(), q.ward(), q.propertyType(), q.source(), q.includeResearch());
        long now = System.currentTimeMillis();
        Cached cached = cache.get(key);
        if (cached != null && cached.expiresAt() > now) {
            return cached.response();
        }
        Response response = compute(q);
        if (cache.size() >= MAX_CACHE_ENTRIES) cache.clear();
        cache.put(key, new Cached(response, now + RESPONSE_TTL_MILLIS));
        return response;
    }

    private Response compute(Query q) {
        List<CohortRow> cohort = filtered(cohort(q.includeResearch()), q);
        MarketAnalyticsCalculator.Computed c = MarketAnalyticsCalculator.compute(cohort);

        Stat overall = toStat("ALL", "Toàn bộ phạm vi", c.overall());
        List<Stat> districts = c.districts().stream()
            .filter(r -> r.key() != null && !r.key().isBlank())
            .map(r -> toStat(r.key(), r.key(), r))
            .sorted((a, b) -> Long.compare(b.count(), a.count()))
            .toList();
        List<Stat> types = c.types().stream()
            .filter(r -> r.key() != null && !r.key().isBlank())
            .map(r -> toStat(r.key(), typeLabel(r.key()), r))
            .sorted((a, b) -> Long.compare(b.count(), a.count()))
            .toList();
        List<Stat> wards = c.wards().stream()
            .filter(r -> r.key() != null && r.key().contains("|"))
            .map(r -> toStat(r.key(), wardLabel(r.key()), r))
            .sorted((a, b) -> Long.compare(b.count(), a.count()))
            .limit(MAX_WARD_CELLS)
            .toList();

        Map<String, Long> sourceCounts = new LinkedHashMap<>();
        for (GroupRow r : c.sources()) {
            if (r.key() != null) sourceCounts.put(r.key(), r.count());
        }
        List<Source> visibleSources = q.includeResearch()
            ? List.of(Source.SMARTPROP, Source.EXTERNAL_LISTING, Source.TINIX_RESEARCH)
            : List.of(Source.SMARTPROP, Source.EXTERNAL_LISTING);
        List<SourceCount> bySource = new ArrayList<>();
        for (Source s : visibleSources) {
            long n = sourceCounts.getOrDefault(s.name(), 0L);
            bySource.add(new SourceCount(s.name(), sourceLabel(s), n, s == Source.TINIX_RESEARCH,
                s == Source.TINIX_RESEARCH ? RESEARCH_LICENSE : null));
        }

        List<Band> priceBands = new ArrayList<>();
        for (int i = 0; i < PRICE_BAND_LABELS.length; i++) priceBands.add(new Band(PRICE_BAND_LABELS[i], c.priceBands()[i]));
        List<Band> areaBands = new ArrayList<>();
        for (int i = 0; i < AREA_BAND_LABELS.length; i++) areaBands.add(new Band(AREA_BAND_LABELS[i], c.areaBands()[i]));

        List<MonthlyPoint> monthly = new ArrayList<>();
        String temporalStatus;
        if (q.includeResearch()) {
            for (GroupRow r : c.months()) {
                if (r.key() == null || !r.key().matches("\\d{4}-\\d{2}")) continue;
                monthly.add(new MonthlyPoint(r.key(), r.count(),
                    round(r.medianPriceVnd()), round(r.medianPricePerSqm()), status(r.count())));
            }
            monthly.sort((a, b) -> a.period().compareTo(b.period()));
            boolean adequate = monthly.size() >= 3 && monthly.stream().allMatch(p -> "OK".equals(p.dataStatus()));
            temporalStatus = adequate ? "AVAILABLE" : "INSUFFICIENT_DATA";
        } else {
            temporalStatus = "NOT_REQUESTED";
        }

        Meta meta = buildMeta(q, overall.count(), bySource, temporalStatus);
        return new Response(meta, overall, districts, wards, types, bySource, priceBands, areaBands, monthly);
    }

    /** The real cohort, read from MySQL at most once per dataset per TTL window. */
    private List<CohortRow> cohort(boolean includeResearch) {
        Cohort current = includeResearch ? researchCohort : safeCohort;
        long now = System.currentTimeMillis();
        if (current != null && now - current.loadedAt() < COHORT_TTL_MILLIS) {
            return current.rows();
        }
        synchronized (this) {
            current = includeResearch ? researchCohort : safeCohort;
            if (current != null && System.currentTimeMillis() - current.loadedAt() < COHORT_TTL_MILLIS) {
                return current.rows();
            }
            List<CohortRow> loaded = repository.loadCohort(includeResearch);
            if (!includeResearch) {
                loaded = loaded.stream()
                    .filter(r -> r != null && !"TINIX_RESEARCH".equalsIgnoreCase(r.source()))
                    .toList();
            }
            Cohort fresh = new Cohort(loaded, System.currentTimeMillis());
            if (includeResearch) researchCohort = fresh;
            else safeCohort = fresh;
            return fresh.rows();
        }
    }

    private static List<CohortRow> filtered(List<CohortRow> all, Query q) {
        String src = q.source() == null || q.source() == Source.ALL ? null : q.source().name();
        return all.stream().filter(r ->
            (q.includeResearch() || !"TINIX_RESEARCH".equalsIgnoreCase(r.source()))
                && (q.district() == null || q.district().equals(r.district()))
                && (q.ward() == null || q.ward().equals(r.ward()))
                && (q.propertyType() == null || q.propertyType().equalsIgnoreCase(r.propertyType()))
                && (src == null || src.equals(r.source())))
            .toList();
    }

    private Meta buildMeta(Query q, long total, List<SourceCount> bySource, String temporalStatus) {
        List<String> warnings = new ArrayList<>();
        warnings.add("ASKING_PRICE_ONLY: số liệu là giá rao bán, không phải giá giao dịch đã công chứng; chênh lệch thương lượng chưa được đo.");
        if (total < MIN_SAMPLE) {
            warnings.add("SMALL_SAMPLE: tổng mẫu " + total + " dưới ngưỡng " + MIN_SAMPLE + " — các ô bị ẩn số liệu (INSUFFICIENT_DATA).");
        }
        long smartprop = bySource.stream().filter(s -> "SMARTPROP".equals(s.source())).mapToLong(SourceCount::count).sum();
        long tinix = bySource.stream().filter(s -> "TINIX_RESEARCH".equals(s.source())).mapToLong(SourceCount::count).sum();
        if (q.includeResearch()) {
            warnings.add("TINIX_RESEARCH_INCLUDED: có " + tinix + " dòng nghiên cứu TiniX (CC BY-NC 4.0) trong tổng hợp — "
                + "dữ liệu lịch sử một lần trích xuất, không phải tin đang rao bán và không xác minh được tình trạng giao dịch.");
            warnings.add("SINGLE_SNAPSHOT: TiniX không có vintage được ghi lại; biến động theo tháng có thể phản ánh "
                + "thành phần nguồn/duplicate hơn là tăng giá thị trường — không diễn giải thành xu hướng giá.");
        }
        if (smartprop > 0 && smartprop <= MIN_SAMPLE) {
            warnings.add("PLATFORM_SAMPLE_SMALL: chỉ có " + smartprop + " tin SmartProp đã duyệt trong phạm vi lọc.");
        }
        warnings.add("NO_FORECAST: hệ thống không tạo dự báo, không tạo tỷ lệ tăng giá và không ngoại suy xu hướng.");
        if ("INSUFFICIENT_DATA".equals(temporalStatus)) {
            warnings.add("TEMPORAL_INSUFFICIENT: dữ liệu thời gian (TiniX) dưới ngưỡng để mô tả theo tháng; trả INSUFFICIENT_DATA thay vì vẽ xu hướng.");
        }
        Filters filters = new Filters(q.district(), q.ward(),
            q.propertyType(), q.source() == null ? "ALL" : q.source().name(), q.includeResearch());
        return new Meta(Instant.now().toString(), filters, total, MIN_SAMPLE,
            "ASKING_SALE_VND_TOTAL", DISCLAIMER, q.includeResearch(),
            q.includeResearch() ? RESEARCH_LICENSE : null, temporalStatus, List.copyOf(warnings));
    }

    private Stat toStat(String key, String label, GroupRow r) {
        long count = r == null ? 0 : r.count();
        List<String> flags = new ArrayList<>();
        String status = status(count);
        boolean suppress = count < MIN_SAMPLE;
        if (count == 0) flags.add("NO_DATA");
        else if (suppress) flags.add("SMALL_SAMPLE");
        return new Stat(
            key, label, count,
            suppress || r == null ? null : round(r.medianPriceVnd()),
            suppress || r == null ? null : round(r.medianPricePerSqm()),
            suppress || r == null ? null : round(r.p25PriceVnd()),
            suppress || r == null ? null : round(r.p75PriceVnd()),
            suppress || r == null ? null : round(r.meanPriceVnd()),
            suppress || r == null ? null : round1(r.medianAreaSqm()),
            status, List.copyOf(flags)
        );
    }

    private static String status(long count) {
        return count >= MIN_SAMPLE ? "OK" : "INSUFFICIENT_DATA";
    }

    private Query validate(String district, String ward, String propertyType, String source, Boolean includeResearch) {
        String d = clean(district);
        String w = clean(ward);
        if (d != null && d.length() > 100) throw ApiInputs.bad("district tối đa 100 ký tự.");
        if (w != null && w.length() > 100) throw ApiInputs.bad("ward tối đa 100 ký tự.");

        String type = propertyType == null || propertyType.isBlank() || "ALL".equalsIgnoreCase(propertyType.strip())
            ? null : propertyType.strip().toUpperCase(Locale.ROOT);
        if (type != null && !ALLOWED_TYPES.contains(type)) {
            throw ApiInputs.bad("propertyType phải là HOUSE, APARTMENT, LAND hoặc VILLA.");
        }

        Source src;
        if (source == null || source.isBlank() || "ALL".equalsIgnoreCase(source.strip())) {
            src = Source.ALL;
        } else {
            try {
                src = Source.valueOf(source.strip().toUpperCase(Locale.ROOT));
            } catch (IllegalArgumentException e) {
                throw ApiInputs.bad("source phải là ALL, SMARTPROP, EXTERNAL_LISTING hoặc TINIX_RESEARCH.");
            }
        }

        boolean research = Boolean.TRUE.equals(includeResearch);
        if (src == Source.TINIX_RESEARCH) research = true;
        return new Query(d, w, type, src, research);
    }

    private static String clean(String value) {
        if (value == null) return null;
        String t = value.strip();
        if (t.isEmpty() || "ALL".equalsIgnoreCase(t) || "Tất cả".equalsIgnoreCase(t)) return null;
        return t;
    }

    private static String sourceLabel(Source s) {
        return switch (s) {
            case SMARTPROP -> "Tin SmartProp đã duyệt (giá rao)";
            case EXTERNAL_LISTING -> "Tin ngoài đã kiểm định (VALID, giá rao)";
            case TINIX_RESEARCH -> "TiniX — dữ liệu nghiên cứu lịch sử (CC BY-NC 4.0)";
            default -> "Tất cả nguồn";
        };
    }

    private static String typeLabel(String type) {
        return switch (type) {
            case "HOUSE" -> "Nhà ở / Nhà phố";
            case "APARTMENT" -> "Căn hộ chung cư";
            case "LAND" -> "Đất nền";
            case "VILLA" -> "Biệt thự";
            default -> type;
        };
    }

    private static String wardLabel(String key) {
        String[] parts = key.split("\\|", -1);
        String district = parts.length > 0 ? parts[0] : "";
        String ward = parts.length > 1 ? parts[1] : "";
        if (ward.isBlank()) return district.isBlank() ? "Chưa xác định" : district + " (chưa rõ phường)";
        return ward + (district.isBlank() ? "" : ", " + district);
    }

    private static BigDecimal round(double value) {
        return Double.isFinite(value) ? BigDecimal.valueOf(value).setScale(0, RoundingMode.HALF_UP) : null;
    }

    private static BigDecimal round1(double value) {
        return Double.isFinite(value) ? BigDecimal.valueOf(value).setScale(1, RoundingMode.HALF_UP) : null;
    }
}
