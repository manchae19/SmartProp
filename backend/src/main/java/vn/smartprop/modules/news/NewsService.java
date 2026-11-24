package vn.smartprop.modules.news;

import java.time.Instant;
import java.util.List;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.smartprop.common.ApiInputs;

/**
 * Đọc dữ liệu News cho API công khai và admin.
 *
 * <p>Public chỉ trả bài từ nguồn {@code APPROVED} + {@code enabled}, bài
 * {@code VISIBLE}. Không trả metadata nội bộ.
 *
 * <p>Sắp xếp thực hiện tại DB trước pagination — không đảo danh sách trong Java.
 */
@Service
public class NewsService {
    private final NewsSourceRepository sources;
    private final NewsArticleRepository articles;
    private final NewsIngestionRunRepository runs;
    private final NewsProperties properties;

    public NewsService(NewsSourceRepository sources, NewsArticleRepository articles,
                       NewsIngestionRunRepository runs, NewsProperties properties) {
        this.sources = sources;
        this.articles = articles;
        this.runs = runs;
        this.properties = properties;
    }

    // ---------- Public ----------

    /**
     * Danh sách bài công khai.
     *
     * @param category nhãn tiếng Việt hoặc enum; {@code null}/"Tất cả" = mọi chuyên mục
     * @param q        từ khoá tìm trong title/summary
     * @param sort     {@code newest} hoặc {@code oldest}
     */
    @Transactional(readOnly = true)
    public NewsDtos.Page list(String category, String q, String sort, int page, int size) {
        int safeSize = clampSize(size);
        int safePage = Math.max(page, 0);

        // Nhóm chuyên mục: "Quy hoạch & hạ tầng" gồm cả PLANNING và INFRASTRUCTURE.
        List<NewsSource.Category> categories = NewsClassifier.parseCategoryGroup(category);
        NewsSource.Category single = categories != null && categories.size() == 1
            ? categories.get(0) : null;

        // "Tin tức Đà Nẵng" là bộ lọc khu vực, không phải chuyên mục.
        NewsSource.Region region = null;
        if (category != null && NewsText.foldForMatch(category).contains("da nang")) {
            region = NewsSource.Region.DA_NANG;
            categories = null;
            single = null;
        }

        String keyword = null;
        if (q != null && !q.isBlank()) {
            String trimmed = q.strip();
            if (trimmed.length() > 200) throw ApiInputs.bad("Từ khoá tối đa 200 ký tự");
            keyword = "%" + escapeLike(NewsText.foldForMatch(trimmed)) + "%";
        }

        Pageable pageable = PageRequest.of(safePage, safeSize);
        boolean oldest = "oldest".equalsIgnoreCase(sort);
        if (sort != null && !sort.isBlank() && !oldest && !"newest".equalsIgnoreCase(sort)) {
            throw ApiInputs.bad("sort chỉ nhận 'newest' hoặc 'oldest'");
        }

        Page<NewsArticle> result = oldest
            ? articles.findPublicOldest(single, categories, region, keyword, pageable)
            : articles.findPublic(single, categories, region, keyword, pageable);

        List<NewsDtos.Article> items = result.getContent().stream()
            .map(this::toArticle)
            .toList();

        return new NewsDtos.Page(items, result.getNumber(), result.getSize(),
            result.getTotalElements(), result.getTotalPages(),
            articles.lastPublicUpdate(), false, publicSources());
    }

    /** Bài nổi bật cho trang News và Home preview. */
    @Transactional(readOnly = true)
    public NewsDtos.Page featured() {
        int limit = Math.max(1, Math.min(properties.getFeaturedLimit(), 12));
        Page<NewsArticle> result = articles.findFeatured(PageRequest.of(0, limit));
        List<NewsDtos.Article> items = result.getContent().stream()
            .map(this::toArticle)
            .toList();
        return new NewsDtos.Page(items, 0, limit, result.getTotalElements(),
            result.getTotalPages(), articles.lastPublicUpdate(), false, publicSources());
    }

    /** Metadata nguồn tin công khai. */
    @Transactional(readOnly = true)
    public NewsDtos.Sources sources() {
        return new NewsDtos.Sources(publicSources(), articles.lastPublicUpdate());
    }

    private List<NewsDtos.Source> publicSources() {
        List<NewsSource> ingestible = sources.findIngestible();
        List<NewsDtos.Source> result = new java.util.ArrayList<>(ingestible.size());
        for (NewsSource source : ingestible) {
            result.add(new NewsDtos.Source(
                source.id,
                source.name,
                source.publisher,
                source.websiteUrl,
                source.feedUrl,
                articles.countPublicBySource(source.id),
                source.lastSuccessAt,
                sourceStatus(source)
            ));
        }
        return result;
    }

    /**
     * Trạng thái nguồn theo nghĩa freshness.
     *
     * <p>{@code AVAILABLE} chỉ khi lần sync gần nhất thành công và còn trong ngưỡng.
     * {@code STALE} khi quá ngưỡng. {@code FAILED} khi lần thử gần nhất lỗi.
     * {@code NEVER_SYNCED} khi chưa từng sync.
     */
    static String sourceStatus(NewsSource source) {
        if (source.lastSuccessAt == null) return "NEVER_SYNCED";
        if (source.lastError != null
                && (source.lastAttemptAt == null
                    || source.lastAttemptAt.isAfter(source.lastSuccessAt))) {
            return "FAILED";
        }
        Instant threshold = Instant.now().minusSeconds(90 * 60);
        return source.lastSuccessAt.isBefore(threshold) ? "STALE" : "AVAILABLE";
    }

    private NewsDtos.Article toArticle(NewsArticle article) {
        NewsSource source = sources.findById(article.sourceId).orElse(null);
        return new NewsDtos.Article(
            article.id,
            article.title,
            article.summary,
            NewsClassifier.categoryLabel(article.category),
            NewsClassifier.regionLabel(article.region),
            article.canonicalUrl,
            source == null ? "Không xác định" : source.name,
            source == null ? null : source.websiteUrl,
            article.publishedAt,
            article.fetchedAt,
            article.locationTags
        );
    }

    private int clampSize(int size) {
        int max = Math.max(1, properties.getMaxPageSize());
        if (size < 1) return 12;
        return Math.min(size, max);
    }

    /** Escape ký tự đặc biệt của LIKE để người dùng không chèn wildcard. */
    private static String escapeLike(String value) {
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_");
    }

    // ---------- Admin ----------

    @Transactional(readOnly = true)
    public List<NewsDtos.AdminSource> adminSources() {
        return sources.findAll().stream().map(this::toAdminSource).toList();
    }

    @Transactional(readOnly = true)
    public NewsDtos.AdminSource adminSource(String id) {
        return toAdminSource(sources.findById(id)
            .orElseThrow(() -> ApiInputs.missing()));
    }

    @Transactional(readOnly = true)
    public org.springframework.data.domain.Page<NewsDtos.AdminArticle> adminArticles(
            int page, int size) {
        Pageable pageable = PageRequest.of(Math.max(page, 0), clampSize(size));
        return articles.findAllByOrderByFirstSeenAtDesc(pageable).map(this::toAdminArticle);
    }

    @Transactional(readOnly = true)
    public org.springframework.data.domain.Page<NewsDtos.AdminRun> adminRuns(int page, int size) {
        Pageable pageable = PageRequest.of(Math.max(page, 0), clampSize(size));
        return runs.findAllByOrderByStartedAtDesc(pageable).map(this::toAdminRun);
    }

    /** Thống kê bằng aggregate query — không load toàn bảng vào RAM. */
    @Transactional(readOnly = true)
    public NewsDtos.Stats stats() {
        long totalSources = sources.count();
        long enabled = sources.countEnabled();
        long approved = sources.countByRightsStatus(NewsSource.RightsStatus.APPROVED);
        long pending = sources.countByRightsStatus(NewsSource.RightsStatus.PENDING_REVIEW);

        long total = articles.count();
        long visible = articles.countByPublicationStatus(NewsArticle.PublicationStatus.VISIBLE);
        long daNang = articles.countByRegion(NewsSource.Region.DA_NANG);

        return new NewsDtos.Stats(totalSources, enabled, approved, pending,
            total, visible, total - visible, daNang, sources.lastSuccessAcrossSources());
    }

    private NewsDtos.AdminSource toAdminSource(NewsSource source) {
        return new NewsDtos.AdminSource(
            source.id, source.sourceCode, source.name, source.publisher,
            source.websiteUrl, source.feedUrl,
            source.defaultCategory.name(), source.defaultRegion.name(),
            source.rightsReviewStatus.name(), source.rightsReference,
            source.rightsCheckedAt, source.usageRestrictions,
            source.allowSummary, source.allowImages,
            source.enabled, source.fetchIntervalMinutes,
            source.lastAttemptAt, source.lastSuccessAt, source.lastError,
            source.nextFetchAt, source.sourceRevision,
            articles.countPublicBySource(source.id)
        );
    }

    private NewsDtos.AdminArticle toAdminArticle(NewsArticle article) {
        NewsSource source = sources.findById(article.sourceId).orElse(null);
        return new NewsDtos.AdminArticle(
            article.id, article.sourceId,
            source == null ? null : source.name,
            article.title, article.summary,
            article.category.name(), article.region.name(),
            article.canonicalUrl, article.publishedAt, article.fetchedAt,
            article.firstSeenAt, article.lastSeenAt,
            article.publicationStatus.name(), article.featured
        );
    }

    private NewsDtos.AdminRun toAdminRun(NewsIngestionRun run) {
        NewsSource source = sources.findById(run.sourceId).orElse(null);
        return new NewsDtos.AdminRun(
            run.id, run.sourceId, source == null ? null : source.name,
            run.startedAt, run.finishedAt, run.status.name(),
            run.httpStatus == null ? null : run.httpStatus.intValue(),
            run.itemsReceived, run.itemsInserted, run.itemsUpdated,
            run.itemsDuplicate, run.itemsRejected,
            run.errorCode, run.errorMessage, run.durationMs
        );
    }
}
