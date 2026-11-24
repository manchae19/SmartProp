package vn.smartprop.modules.news;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

/**
 * Thu thập feed cho một nguồn.
 *
 * <p>Nguyên tắc:
 * <ul>
 *   <li>Chỉ nguồn {@code APPROVED} + {@code enabled} mới được thu thập.</li>
 *   <li>Không giữ transaction trong lúc chờ network — fetch xong mới mở transaction
 *       ghi.</li>
 *   <li>Idempotent: chạy lại cùng feed không tạo bản ghi trùng. Dựa vào unique
 *       constraint ở DB, không chỉ kiểm tra exists trước INSERT.</li>
 *   <li>Một item lỗi không làm hỏng cả feed.</li>
 *   <li>Không ghi đè quyết định admin về {@code publicationStatus} hay {@code featured}.</li>
 * </ul>
 */
@Service
public class NewsIngestionService {
    private static final Logger log = LoggerFactory.getLogger(NewsIngestionService.class);

    private final NewsSourceRepository sources;
    private final NewsArticleRepository articles;
    private final NewsIngestionRunRepository runs;
    private final NewsFeedFetcher fetcher;
    private final NewsProperties properties;

    public NewsIngestionService(NewsSourceRepository sources, NewsArticleRepository articles,
                                NewsIngestionRunRepository runs, NewsFeedFetcher fetcher,
                                NewsProperties properties) {
        this.sources = sources;
        this.articles = articles;
        this.runs = runs;
        this.fetcher = fetcher;
        this.properties = properties;
    }

    /** Kết quả một lần thu thập. */
    public record Outcome(String runId, NewsIngestionRun.Status status,
                          int received, int inserted, int updated, int duplicate, int rejected,
                          String errorCode, String errorMessage) {}

    /**
     * Thu thập một nguồn.
     *
     * <p>Không có {@code @Transactional} ở đây: network fetch không được giữ
     * transaction. Phần ghi dữ liệu nằm trong {@link #persist}.
     */
    public Outcome ingest(String sourceId) {
        NewsSource source = sources.findById(sourceId).orElse(null);
        if (source == null) {
            return new Outcome(null, NewsIngestionRun.Status.SKIPPED, 0, 0, 0, 0, 0,
                "SOURCE_NOT_FOUND", "Không tìm thấy nguồn");
        }
        if (!source.ingestible()) {
            return new Outcome(null, NewsIngestionRun.Status.SKIPPED, 0, 0, 0, 0, 0,
                "SOURCE_NOT_INGESTIBLE",
                "Nguồn chưa được duyệt quyền hoặc đang tắt");
        }

        Instant startedAt = Instant.now();
        String runId = UUID.randomUUID().toString();
        runs.save(run(runId, sourceId, startedAt, NewsIngestionRun.Status.RUNNING));

        long begin = System.nanoTime();
        NewsFeedFetcher.FetchResult fetched =
            fetcher.fetch(source.feedUrl, source.httpEtag, source.httpLastModified);

        if (fetched.failed()) {
            return finish(runId, source, startedAt, begin, NewsIngestionRun.Status.FAILED,
                fetched.status() == 0 ? null : (short) fetched.status(),
                0, 0, 0, 0, 0, fetched.errorCode(), fetched.errorMessage());
        }

        if (fetched.notModified()) {
            return finish(runId, source, startedAt, begin, NewsIngestionRun.Status.NOT_MODIFIED,
                (short) 304, 0, 0, 0, 0, 0, null, null);
        }

        NewsFeedParser.Result parsed;
        try {
            parsed = NewsFeedParser.parse(fetched.body());
        } catch (Exception e) {
            return finish(runId, source, startedAt, begin, NewsIngestionRun.Status.FAILED,
                (short) fetched.status(), 0, 0, 0, 0, 0,
                "PARSE_ERROR", safeMessage(e));
        }

        return persist(runId, source, startedAt, begin, fetched, parsed);
    }

    /** Ghi kết quả parse vào DB trong một transaction riêng. */
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    protected Outcome persist(String runId, NewsSource source, Instant startedAt, long begin,
                              NewsFeedFetcher.FetchResult fetched, NewsFeedParser.Result parsed) {
        Instant now = Instant.now();
        int inserted = 0, updated = 0, duplicate = 0, rejected = parsed.rejected();

        for (NewsFeedParser.Item item : parsed.items()) {
            String canonical = NewsText.canonicalUrl(item.link());
            if (canonical == null) { rejected++; continue; }

            String title = NewsText.clean(item.title(), 500);
            if (title == null) { rejected++; continue; }

            String summary = NewsText.clean(item.summary(), 2000);
            String hash = NewsText.sha256(canonical);

            NewsClassifier.Classification classification = NewsClassifier.classify(
                title, summary, source.defaultCategory, source.defaultRegion);
            if (!classification.relevant()) { rejected++; continue; }

            Optional<NewsArticle> existing =
                articles.findBySourceIdAndCanonicalUrlHash(source.id, hash);

            if (existing.isPresent()) {
                NewsArticle article = existing.get();
                // Chỉ cập nhật metadata; KHÔNG đụng publicationStatus / featured.
                article.lastSeenAt = now;
                article.fetchedAt = now;
                if (article.publishedAt == null && item.publishedAt() != null) {
                    article.publishedAt = item.publishedAt();
                }
                if (summary != null && (article.summary == null
                        || !summary.equals(article.summary))) {
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
            article.contentFingerprint = NewsText.sha256(title + "|" + (summary == null ? "" : summary));
            article.publicationStatus = NewsArticle.PublicationStatus.VISIBLE;
            article.featured = false;
            article.createdAt = now;
            article.updatedAt = now;

            try {
                articles.saveAndFlush(article);
                inserted++;
            } catch (org.springframework.dao.DataIntegrityViolationException e) {
                // Race: request khác đã chèn cùng bài. Không phải lỗi.
                duplicate++;
            }
        }

        // Cập nhật conditional GET và trạng thái nguồn.
        source.httpEtag = truncate(fetched.etag(), 200);
        source.httpLastModified = truncate(fetched.lastModified(), 100);
        source.lastSuccessAt = now;
        source.lastError = null;
        source.updatedAt = now;
        sources.save(source);

        NewsIngestionRun.Status status = rejected > 0 && inserted == 0 && updated == 0
            ? NewsIngestionRun.Status.PARTIAL_SUCCESS
            : NewsIngestionRun.Status.SUCCESS;

        return finish(runId, source, startedAt, begin, status, (short) fetched.status(),
            parsed.items().size() + parsed.rejected(), inserted, updated, duplicate, rejected,
            null, null);
    }

    /** Ghi kết thúc run và cập nhật trạng thái nguồn khi lỗi. */
    private Outcome finish(String runId, NewsSource source, Instant startedAt, long begin,
                           NewsIngestionRun.Status status, Short httpStatus,
                           int received, int inserted, int updated, int duplicate, int rejected,
                           String errorCode, String errorMessage) {
        Instant finishedAt = Instant.now();
        int durationMs = (int) ((System.nanoTime() - begin) / 1_000_000);

        NewsIngestionRun run = runs.findById(runId).orElse(null);
        if (run != null) {
            run.finishedAt = finishedAt;
            run.status = status;
            run.httpStatus = httpStatus;
            run.itemsReceived = received;
            run.itemsInserted = inserted;
            run.itemsUpdated = updated;
            run.itemsDuplicate = duplicate;
            run.itemsRejected = rejected;
            run.errorCode = truncate(errorCode, 60);
            run.errorMessage = truncate(errorMessage, 500);
            run.durationMs = durationMs;
            runs.save(run);
        }

        // Cập nhật nguồn: luôn ghi lastAttemptAt; lỗi thì ghi lastError.
        NewsSource fresh = sources.findById(source.id).orElse(source);
        fresh.lastAttemptAt = startedAt;
        fresh.updatedAt = finishedAt;
        if (errorCode != null) {
            fresh.lastError = truncate(errorCode + ": " + (errorMessage == null ? "" : errorMessage), 500);
        }
        sources.save(fresh);

        log.info("news.ingest source={} run={} status={} received={} inserted={} updated={} "
                + "duplicate={} rejected={} durationMs={}",
            source.sourceCode, runId, status, received, inserted, updated, duplicate, rejected,
            durationMs);

        return new Outcome(runId, status, received, inserted, updated, duplicate, rejected,
            errorCode, errorMessage);
    }

    private static NewsIngestionRun run(String id, String sourceId, Instant startedAt,
                                        NewsIngestionRun.Status status) {
        NewsIngestionRun run = new NewsIngestionRun();
        run.id = id;
        run.sourceId = sourceId;
        run.startedAt = startedAt;
        run.status = status;
        run.itemsReceived = 0;
        run.itemsInserted = 0;
        run.itemsUpdated = 0;
        run.itemsDuplicate = 0;
        run.itemsRejected = 0;
        return run;
    }

    private static String truncate(String value, int max) {
        if (value == null) return null;
        return value.length() <= max ? value : value.substring(0, max);
    }

    private static String safeMessage(Exception e) {
        String message = e.getMessage();
        if (message == null) return e.getClass().getSimpleName();
        return message.length() > 200 ? message.substring(0, 200) : message;
    }

    /** Thu thập mọi nguồn đã đến hạn. Dùng bởi scheduler. */
    public List<Outcome> ingestDue() {
        Instant now = Instant.now();
        return sources.findIngestible().stream()
            .filter(source -> source.lastAttemptAt == null
                || source.lastAttemptAt.plusSeconds(source.fetchIntervalMinutes * 60L).isBefore(now))
            .map(source -> ingest(source.id))
            .toList();
    }
}
