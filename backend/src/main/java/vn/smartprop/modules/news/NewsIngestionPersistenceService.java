package vn.smartprop.modules.news;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

/**
 * Ghi kết quả ingestion trong transaction riêng.
 *
 * <p>Tách khỏi {@link NewsIngestionService} để lời gọi đi qua Spring AOP proxy —
 * {@code @Transactional} trên method gọi nội bộ trong cùng bean không có hiệu lực.
 *
 * <p>Transaction ở đây chỉ bao quanh phần ghi DB, không bao gồm network fetch.
 */
@Service
public class NewsIngestionPersistenceService {
    private final NewsSourceRepository sources;
    private final NewsArticleRepository articles;

    public NewsIngestionPersistenceService(NewsSourceRepository sources,
                                           NewsArticleRepository articles) {
        this.sources = sources;
        this.articles = articles;
    }

    /** Kết quả ghi. */
    public record Persisted(int inserted, int updated, int duplicate, int rejected,
                            boolean leaseLost, boolean sourceChanged) {}

    /**
     * Ghi các item đã parse vào DB.
     *
     * <p>Trước khi ghi, kiểm tra lại nguồn: lease còn giữ, quyền chưa bị thu hồi,
     * nguồn chưa bị tắt, {@code sourceRevision} chưa đổi. Nếu bất kỳ điều kiện nào
     * sai, không ghi gì và trả cờ tương ứng — không ghi đè quyết định của admin.
     *
     * @param leaseToken token job đang giữ
     * @param expectedRevision revision nguồn tại lúc claim lease
     */
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public Persisted persist(String sourceId, String leaseToken, int expectedRevision,
                             NewsFeedParser.Result parsed, Instant now) {
        NewsSource source = sources.findById(sourceId).orElse(null);
        if (source == null) {
            return new Persisted(0, 0, 0, 0, true, false);
        }
        // Lease đã mất (job khác claim, hoặc admin can thiệp) → không ghi.
        if (!leaseToken.equals(source.syncLeaseToken)) {
            return new Persisted(0, 0, 0, 0, true, false);
        }
        // Admin đã sửa nguồn trong lúc fetch → bỏ kết quả.
        if (source.sourceRevision != expectedRevision) {
            return new Persisted(0, 0, 0, 0, false, true);
        }
        // Quyền bị thu hồi hoặc nguồn bị tắt trong lúc fetch → không ghi.
        if (!source.ingestible()) {
            return new Persisted(0, 0, 0, 0, false, true);
        }

        int inserted = 0, updated = 0, duplicate = 0, rejected = parsed.rejected();

        for (NewsFeedParser.Item item : parsed.items()) {
            String canonical = NewsText.canonicalUrl(item.link());
            if (canonical == null) { rejected++; continue; }

            String title = NewsText.clean(item.title(), 500);
            if (title == null) { rejected++; continue; }

            // Chỉ lưu summary khi nguồn cho phép.
            String summary = source.allowSummary ? NewsText.clean(item.summary(), 2000) : null;
            String hash = NewsText.sha256(canonical);

            NewsClassifier.Classification classification = NewsClassifier.classify(
                title, summary, source.defaultCategory, source.defaultRegion);
            if (!classification.relevant()) { rejected++; continue; }

            Optional<NewsArticle> existing =
                articles.findBySourceIdAndCanonicalUrlHash(source.id, hash);

            if (existing.isPresent()) {
                NewsArticle article = existing.get();
                // Chỉ cập nhật metadata ingestion được phép sửa.
                // KHÔNG đụng publicationStatus / featured — đó là quyết định của admin.
                article.lastSeenAt = now;
                article.fetchedAt = now;
                if (article.publishedAt == null && item.publishedAt() != null) {
                    article.publishedAt = item.publishedAt();
                }
                if (summary != null && !summary.equals(article.summary)) {
                    article.summary = summary;
                }
                article.updatedAt = now;
                articles.save(article);
                updated++;
                continue;
            }

            NewsArticle article = new NewsArticle();
            article.id = UUID.randomUUID().toString();
            article.sourceId = source.id;
            article.externalId = truncate(item.externalId(), 500);
            article.canonicalUrl = truncate(canonical, 1000);
            article.canonicalUrlHash = hash;
            article.title = title;
            article.summary = summary;
            article.category = classification.category();
            article.region = classification.region();
            article.locationTags = truncate(classification.locationTags(), 500);
            article.publishedAt = item.publishedAt();
            article.fetchedAt = now;
            article.firstSeenAt = now;
            article.lastSeenAt = now;
            article.contentFingerprint = NewsText.sha256(
                title + "|" + (summary == null ? "" : summary));
            article.publicationStatus = NewsArticle.PublicationStatus.VISIBLE;
            article.featured = false;
            article.createdAt = now;
            article.updatedAt = now;

            try {
                articles.saveAndFlush(article);
                inserted++;
            } catch (org.springframework.dao.DataIntegrityViolationException e) {
                // Chỉ coi là duplicate khi khoá bị trùng. Lỗi khác (FK, truncation,
                // CHECK) phải ném ra để transaction rollback và run ghi FAILED.
                if (!isDuplicateKey(e)) throw e;
                duplicate++;
            }
        }

        return new Persisted(inserted, updated, duplicate, rejected, false, false);
    }

    /**
     * Cập nhật metadata nguồn sau khi ghi bài thành công.
     *
     * <p>Chỉ job đang giữ lease mới cập nhật được — job cũ không ghi đè trạng thái
     * của job mới.
     */
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public boolean markSuccess(String sourceId, String leaseToken, String etag,
                               String lastModified, Instant nextFetchAt, Instant now) {
        NewsSource source = sources.findById(sourceId).orElse(null);
        if (source == null || !leaseToken.equals(source.syncLeaseToken)) return false;

        source.httpEtag = truncate(etag, 200);
        source.httpLastModified = truncate(lastModified, 100);
        source.lastSuccessAt = now;
        source.lastError = null;
        source.consecutiveFailures = 0;
        source.nextFetchAt = nextFetchAt;
        source.updatedAt = now;
        sources.save(source);
        return true;
    }

    /**
     * Ghi trạng thái thất bại và tính backoff.
     *
     * <p>Không ghi đè nếu job đã mất lease.
     */
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public boolean markFailure(String sourceId, String leaseToken, String errorCode,
                               String errorMessage, Instant nextFetchAt, Instant now) {
        NewsSource source = sources.findById(sourceId).orElse(null);
        if (source == null || !leaseToken.equals(source.syncLeaseToken)) return false;

        source.lastError = truncate(errorCode + ": "
            + (errorMessage == null ? "" : errorMessage), 500);
        source.consecutiveFailures = (short) Math.min(source.consecutiveFailures + 1, 100);
        source.nextFetchAt = nextFetchAt;
        source.updatedAt = now;
        sources.save(source);
        return true;
    }

    /** Chỉ true khi lỗi là trùng khoá duy nhất, không phải FK/CHECK/truncation. */
    static boolean isDuplicateKey(org.springframework.dao.DataIntegrityViolationException e) {
        String message = e.getMostSpecificCause() == null
            ? String.valueOf(e.getMessage())
            : String.valueOf(e.getMostSpecificCause().getMessage());
        return message != null && message.contains("Duplicate entry");
    }

    private static String truncate(String value, int max) {
        if (value == null) return null;
        return value.length() <= max ? value : value.substring(0, max);
    }
}
