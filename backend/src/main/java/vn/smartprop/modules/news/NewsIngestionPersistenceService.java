package vn.smartprop.modules.news;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

/**
 * Ghi kết quả ingestion trong transaction riêng, có fencing.
 *
 * <p>Tách khỏi {@link NewsIngestionService} để lời gọi đi qua Spring AOP proxy —
 * {@code @Transactional} trên method gọi nội bộ trong cùng bean không có hiệu lực.
 *
 * <p><b>Fencing:</b> mỗi lần ghi đều khoá dòng nguồn bằng {@code SELECT ... FOR UPDATE}
 * rồi kiểm tra lease token, lease expiry, {@code sourceRevision} và eligibility trên
 * trạng thái mới nhất. Đây là linearization point: hoặc job ghi xong trước khi admin
 * thu hồi quyền, hoặc admin thu hồi trước và job thấy trạng thái mới rồi bỏ kết quả.
 * Không có cửa sổ nào để job cũ ghi đè quyết định của admin.
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
     * @param leaseToken       token job đang giữ
     * @param expectedRevision revision nguồn tại lúc claim lease
     */
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public Persisted persist(String sourceId, String leaseToken, int expectedRevision,
                             NewsFeedParser.Result parsed, Instant now) {
        // Fencing point: khoá dòng nguồn. Mọi kiểm tra dưới đây đọc trạng thái mới nhất.
        NewsSource source = sources.lockById(sourceId).orElse(null);
        if (source == null) {
            return new Persisted(0, 0, 0, 0, true, false);
        }
        if (!leaseToken.equals(source.syncLeaseToken)) {
            return new Persisted(0, 0, 0, 0, true, false);
        }
        if (source.syncLeaseUntil == null || !source.syncLeaseUntil.isAfter(Instant.now())) {
            return new Persisted(0, 0, 0, 0, true, false);
        }
        if (source.sourceRevision != expectedRevision) {
            return new Persisted(0, 0, 0, 0, false, true);
        }
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
            String summary = NewsRightsPolicy.summary(source) ? NewsText.clean(item.summary(), 2000) : null;
            String hash = NewsText.sha256(canonical);
            String externalId = truncate(item.externalId(), 500);

            NewsClassifier.Classification classification = NewsClassifier.classify(
                title, summary, source.defaultCategory, source.defaultRegion);
            if (!classification.relevant()) { rejected++; continue; }

            // Flush trước khi lookup để thấy bản ghi vừa chèn trong cùng transaction.
            articles.flush();

            // Kiểm tra cả hai identity: canonical URL và external GUID.
            Optional<NewsArticle> byUrl =
                articles.findBySourceIdAndCanonicalUrlHash(source.id, hash);
            Optional<NewsArticle> byGuid = externalId == null
                ? Optional.empty()
                : articles.findBySourceIdAndExternalId(source.id, externalId);

            if (byUrl.isPresent() && byGuid.isPresent()
                    && !byUrl.get().id.equals(byGuid.get().id)) {
                // URL trỏ bài A, GUID trỏ bài B — hai identity xung đột. Không tự hợp
                // nhất vì có thể là hai bài khác nhau. Bỏ item, ghi nhận rejected.
                rejected++;
                continue;
            }

            Optional<NewsArticle> existing = byUrl.isPresent() ? byUrl : byGuid;

            if (existing.isPresent()) {
                NewsArticle article = existing.get();
                // Targeted update: chỉ những cột ingestion được phép sửa.
                // publicationStatus và featured là quyết định của admin — không đụng.
                int rows = articles.touchSeen(article.id, now,
                    article.publishedAt == null ? item.publishedAt() : null,
                    summary != null && !summary.equals(article.summary) ? summary : null);
                if (rows == 1) updated++;
                continue;
            }

            NewsArticle article = new NewsArticle();
            article.id = UUID.randomUUID().toString();
            article.sourceId = source.id;
            article.externalId = externalId;
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
     * <p>Khoá dòng + kiểm tra lease/revision trước khi ghi. Chỉ job đang giữ lease mới
     * cập nhật được — job cũ không ghi đè trạng thái của job mới, và không ghi đè
     * publisher/feedUrl/rights mà admin vừa sửa.
     *
     * @return true nếu ghi thành công
     */
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public boolean markSuccess(String sourceId, String leaseToken, int expectedRevision,
                               String etag, String lastModified, Instant nextFetchAt,
                               Instant now) {
        NewsSource source = sources.lockById(sourceId).orElse(null);
        if (source == null) return false;
        if (!leaseToken.equals(source.syncLeaseToken)) return false;
        if (!source.leaseActive(Instant.now()) || !source.ingestible()) return false;
        if (source.sourceRevision != expectedRevision) return false;

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
     * <p>Khoá dòng + kiểm tra lease trước khi ghi.
     */
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public boolean markFailure(String sourceId, String leaseToken, int expectedRevision, String errorCode,
                               String errorMessage, Instant nextFetchAt, Instant now) {
        NewsSource source = sources.lockById(sourceId).orElse(null);
        if (source == null) return false;
        if (!leaseToken.equals(source.syncLeaseToken)) return false;
        if (!source.leaseActive(Instant.now()) || !source.ingestible()) return false;

        if (source.sourceRevision != expectedRevision) return false;
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
