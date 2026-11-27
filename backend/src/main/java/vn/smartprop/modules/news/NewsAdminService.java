package vn.smartprop.modules.news;

import java.time.Instant;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.smartprop.common.ApiInputs;

/**
 * Quản trị nguồn tin và bài viết.
 *
 * <p>Quy tắc bất biến:
 * <ul>
 *   <li>Nguồn mới luôn {@code PENDING_REVIEW} + {@code enabled=false}.</li>
 *   <li>Chuyển sang {@code APPROVED} bắt buộc có {@code rightsReference}.</li>
 *   <li>Không có endpoint nào nhận URL tùy ý để fetch — chỉ sync nguồn đã lưu.</li>
 *   <li>Không cho sửa nội dung bài (title/summary) — tránh mạo danh publisher.</li>
 * </ul>
 */
@Service
public class NewsAdminService {
    private final NewsSourceRepository sources;
    private final NewsArticleRepository articles;
    private final NewsIngestionService ingestion;
    private final NewsService read;

    public NewsAdminService(NewsSourceRepository sources, NewsArticleRepository articles,
                            NewsIngestionService ingestion, NewsService read) {
        this.sources = sources;
        this.articles = articles;
        this.ingestion = ingestion;
        this.read = read;
    }

    /** Tạo nguồn. Luôn PENDING_REVIEW + disabled, bất kể client gửi gì. */
    @Transactional
    public NewsDtos.AdminSource create(NewsDtos.CreateSource input) {
        if (sources.findBySourceCode(input.sourceCode()).isPresent()) {
            throw ApiInputs.conflict("Mã nguồn đã tồn tại");
        }
        if (sources.findByFeedUrl(input.feedUrl()).isPresent()) {
            throw ApiInputs.conflict("Feed URL đã được dùng bởi nguồn khác");
        }
        // Kiểm tra SSRF ngay khi tạo — không chờ đến lúc fetch.
        NewsUrlSafety.Result safety = NewsUrlSafety.check(input.feedUrl(), false, false);
        if (!safety.allowed()) {
            throw ApiInputs.bad("Feed URL không hợp lệ: " + safety.reason());
        }

        Instant now = Instant.now();
        NewsSource source = new NewsSource();
        source.id = UUID.randomUUID().toString();
        source.sourceCode = input.sourceCode();
        source.name = input.name();
        source.publisher = input.publisher();
        source.websiteUrl = input.websiteUrl();
        source.feedUrl = input.feedUrl();
        source.defaultCategory = input.defaultCategory() == null
            ? NewsSource.Category.MARKET : input.defaultCategory();
        source.defaultRegion = input.defaultRegion() == null
            ? NewsSource.Region.UNKNOWN : input.defaultRegion();
        // Không bao giờ tạo ở trạng thái đã duyệt.
        source.rightsReviewStatus = NewsSource.RightsStatus.PENDING_REVIEW;
        source.rightsReference = input.rightsReference();
        source.usageRestrictions = input.usageRestrictions();
        source.enabled = false;
        source.fetchIntervalMinutes = (short) (input.fetchIntervalMinutes() == null
            ? 30 : input.fetchIntervalMinutes());
        source.createdAt = now;
        source.updatedAt = now;
        sources.save(source);
        return read.adminSource(source.id);
    }

    /** Cập nhật nguồn. Duyệt quyền phải kèm căn cứ. */
    @Transactional
    public NewsDtos.AdminSource update(String id, NewsDtos.UpdateSource input) {
        NewsSource source = sources.lockById(id).orElseThrow(() -> ApiInputs.missing());

        // Thay đổi định danh nguồn (feed URL hoặc publisher) làm approval cũ không
        // còn áp dụng: quyền sử dụng đã được xét cho một nguồn cụ thể. Đưa về
        // PENDING_REVIEW + tắt ingestion, buộc admin duyệt lại có căn cứ mới.
        boolean identityChanged = false;

        if (input.publisher() != null && !input.publisher().equals(source.publisher)) {
            source.publisher = input.publisher();
            identityChanged = true;
        }
        if (input.websiteUrl() != null && !input.websiteUrl().equals(source.websiteUrl)) {
            source.websiteUrl = input.websiteUrl();
            identityChanged = true;
        }
        if (input.feedUrl() != null && !input.feedUrl().equals(source.feedUrl)) {
            NewsUrlSafety.Result safety = NewsUrlSafety.check(input.feedUrl(), false, false);
            if (!safety.allowed()) {
                throw ApiInputs.bad("Feed URL không hợp lệ: " + safety.reason());
            }
            sources.findByFeedUrl(input.feedUrl()).ifPresent(other -> {
                if (!other.id.equals(id)) throw ApiInputs.conflict("Feed URL đã được dùng");
            });
            source.feedUrl = input.feedUrl();
            // Đổi URL thì bỏ cache conditional GET.
            source.httpEtag = null;
            source.httpLastModified = null;
            identityChanged = true;
        }
        if (input.name() != null) source.name = input.name();
        if (input.defaultCategory() != null) source.defaultCategory = input.defaultCategory();
        if (input.defaultRegion() != null) source.defaultRegion = input.defaultRegion();
        if (input.usageRestrictions() != null) source.usageRestrictions = input.usageRestrictions();
        if (input.allowSummary() != null) source.allowSummary = input.allowSummary();
        if (input.allowImages() != null) source.allowImages = input.allowImages();
        if (input.fetchIntervalMinutes() != null) {
            source.fetchIntervalMinutes = input.fetchIntervalMinutes().shortValue();
        }

        boolean referenceChanged = input.rightsReference() != null
            && !java.util.Objects.equals(input.rightsReference(), source.rightsReference)
            && source.rightsReviewStatus == NewsSource.RightsStatus.APPROVED;
        if (identityChanged || referenceChanged) {
            // Đổi định danh làm approval cũ không còn áp dụng. Đưa về PENDING và
            // từ chối mọi nỗ lực approve/enable trong CÙNG request — approval mới
            // phải là hành động riêng, có căn cứ cho nguồn mới.
            source.rightsReviewStatus = NewsSource.RightsStatus.PENDING_REVIEW;
            source.rightsCheckedAt = null;
            source.rightsReference = null;
            source.allowSummary = false;
            source.allowImages = false;
            source.httpEtag = null;
            source.httpLastModified = null;
            source.enabled = false;
            if (identityChanged) articles.hideBySource(id, Instant.now());
            source.nextFetchAt = null;
            if (input.rightsReviewStatus() == NewsSource.RightsStatus.APPROVED) {
                throw ApiInputs.bad(
                    "Đổi feed URL hoặc publisher cần duyệt lại quyền ở request riêng");
            }
            if (Boolean.TRUE.equals(input.enabled())) {
                throw ApiInputs.bad(
                    "Đổi feed URL hoặc publisher cần duyệt lại quyền trước khi bật");
            }
        }

        if (input.rightsReviewStatus() != null
                && input.rightsReviewStatus() != source.rightsReviewStatus) {
            if (input.rightsReviewStatus() == NewsSource.RightsStatus.APPROVED) {
                String reference = input.rightsReference() != null
                    ? input.rightsReference() : source.rightsReference;
                if (reference == null || reference.isBlank()) {
                    throw ApiInputs.bad(
                        "Duyệt quyền sử dụng cần rightsReference (căn cứ pháp lý hoặc văn bản)");
                }
                source.rightsReference = reference;
                source.rightsCheckedAt = Instant.now();
            }
            source.rightsReviewStatus = input.rightsReviewStatus();
            // Thu hồi quyền thì tắt luôn ingestion và xoá cooldown cũ.
            if (input.rightsReviewStatus() != NewsSource.RightsStatus.APPROVED) {
                source.enabled = false;
                source.nextFetchAt = null;
            }
        } else if (input.rightsReference() != null) {
            if (input.rightsReference().isBlank()
                    && source.rightsReviewStatus == NewsSource.RightsStatus.APPROVED) {
                throw ApiInputs.bad(
                    "Không thể xoá rightsReference khi nguồn đang APPROVED; thu hồi quyền trước");
            }
            source.rightsReference = input.rightsReference();
        }

        if (input.enabled() != null) {
            if (input.enabled() && source.rightsReviewStatus != NewsSource.RightsStatus.APPROVED) {
                throw ApiInputs.bad("Chỉ bật được nguồn đã duyệt quyền sử dụng");
            }
            source.enabled = input.enabled();
        }

        NewsRightsPolicy.validate(source);
        // Tăng revision để job đang chạy phát hiện thay đổi và bỏ kết quả.
        source.sourceRevision = source.sourceRevision + 1;

        source.updatedAt = Instant.now();
        sources.save(source);
        return read.adminSource(source.id);
    }

    /** Sync thủ công một nguồn. Không nhận URL từ client. */
    public NewsIngestionService.Outcome sync(String id) {
        if (!NewsReleaseCapability.liveIngestionPermitted()) return ingestion.ingest(id);
        NewsSource source = sources.findById(id).orElseThrow(() -> ApiInputs.missing());
        if (!source.ingestible()) {
            throw ApiInputs.bad("Nguồn chưa được duyệt quyền hoặc đang tắt");
        }
        return ingestion.ingest(id);
    }

    /** Ẩn hoặc hiện một bài. */
    @Transactional
    public NewsDtos.AdminArticle setVisibility(String articleId,
                                               NewsArticle.PublicationStatus status) {
        NewsArticle article = articles.findById(articleId)
            .orElseThrow(() -> ApiInputs.missing());
        article.publicationStatus = status;
        article.updatedAt = Instant.now();
        articles.save(article);
        return read.adminArticles(0, 1).getContent().stream()
            .filter(a -> a.id().equals(articleId))
            .findFirst()
            .orElseGet(() -> adminArticle(article));
    }

    /** Đặt hoặc bỏ cờ nổi bật. */
    @Transactional
    public NewsDtos.AdminArticle setFeatured(String articleId, boolean featured) {
        NewsArticle article = articles.findById(articleId)
            .orElseThrow(() -> ApiInputs.missing());
        article.featured = featured;
        article.updatedAt = Instant.now();
        articles.save(article);
        return adminArticle(article);
    }

    private NewsDtos.AdminArticle adminArticle(NewsArticle article) {
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
}
