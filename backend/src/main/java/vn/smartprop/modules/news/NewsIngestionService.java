package vn.smartprop.modules.news;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

/**
 * Thu thập feed cho một nguồn.
 *
 * <p>Luồng:
 * <ol>
 *   <li>Claim lease nguyên tử ở DB — hai job đồng thời chỉ một job thắng.</li>
 *   <li>Tạo ingestion run (RUNNING).</li>
 *   <li>Fetch ngoài transaction — không giữ DB lock trong lúc chờ mạng.</li>
 *   <li>Parse ngoài transaction.</li>
 *   <li>Ghi trong transaction riêng ({@link NewsIngestionPersistenceService}).</li>
 *   <li>Giải phóng lease.</li>
 * </ol>
 *
 * <p>Nếu job mất lease giữa chừng (admin can thiệp, lease hết hạn), kết quả bị bỏ —
 * không ghi đè quyết định của admin hay trạng thái của job mới.
 */
@Service
public class NewsIngestionService {
    private static final Logger log = LoggerFactory.getLogger(NewsIngestionService.class);

    /** Lease sống 5 phút — đủ cho fetch + parse, không giữ nguồn quá lâu nếu crash. */
    private static final Duration LEASE_DURATION = Duration.ofMinutes(5);

    /** Backoff cơ sở khi lỗi tạm thời. */
    private static final Duration BASE_BACKOFF = Duration.ofMinutes(15);
    private static final Duration MAX_BACKOFF = Duration.ofHours(6);

    private final NewsSourceRepository sources;
    private final NewsIngestionRunRepository runs;
    private final NewsFeedFetcher fetcher;
    private final NewsIngestionPersistenceService persistence;
    private final NewsProperties properties;

    public NewsIngestionService(NewsSourceRepository sources, NewsIngestionRunRepository runs,
                                NewsFeedFetcher fetcher,
                                NewsIngestionPersistenceService persistence,
                                NewsProperties properties) {
        this.sources = sources;
        this.runs = runs;
        this.fetcher = fetcher;
        this.persistence = persistence;
        this.properties = properties;
    }

    /** Kết quả một lần thu thập. */
    public record Outcome(String runId, NewsIngestionRun.Status status,
                          int received, int inserted, int updated, int duplicate, int rejected,
                          String errorCode, String errorMessage) {}

    /**
     * Thu thập một nguồn.
     *
     * <p>Không {@code @Transactional}: network fetch không được giữ transaction.
     * Mỗi bước ghi dùng transaction riêng.
     *
     * <p><b>Safety gate:</b> kiểm tra global policy TRƯỚC mọi thứ khác — trước claim
     * lease, trước tạo run, trước DNS lookup, trước HTTP request. Mọi đường vào
     * (scheduler, manual sync, gọi service trực tiếp) đều đi qua đây nên không đường
     * nào bypass được.
     */
    public Outcome ingest(String sourceId) {
        // Gate 0: release capability. Đây là hằng số biên dịch — không cấu hình nào
        // mở được. V1 là read-only release vì DNS rebinding chưa xử lý đầy đủ.
        if (!NewsReleaseCapability.liveIngestionPermitted()) {
            log.info("news.ingest blocked source={} reason={}", sourceId,
                NewsReleaseCapability.LOCK_CODE);
            return new Outcome(null, NewsIngestionRun.Status.SKIPPED, 0, 0, 0, 0, 0,
                NewsReleaseCapability.LOCK_CODE, NewsReleaseCapability.LOCK_REASON);
        }
        // Gate 1: global ingestion policy. Mặc định tắt.
        if (!properties.isIngestionEnabled()) {
            log.info("news.ingest blocked source={} reason=INGESTION_DISABLED", sourceId);
            return new Outcome(null, NewsIngestionRun.Status.SKIPPED, 0, 0, 0, 0, 0,
                "INGESTION_DISABLED",
                "Thu thập tin tức đang bị tắt trên máy chủ này");
        }
        // Gate 2: network fetching policy. Khi bật ingestion nhưng chưa có allowlist
        // được cấu hình, từ chối thay vì fetch tới host bất kỳ.
        if (properties.isEnforceHostAllowlist() && properties.getAllowedHosts().isEmpty()) {
            log.warn("news.ingest blocked source={} reason=ALLOWLIST_EMPTY", sourceId);
            return new Outcome(null, NewsIngestionRun.Status.SKIPPED, 0, 0, 0, 0, 0,
                "ALLOWLIST_EMPTY",
                "Chưa cấu hình host allowlist; từ chối fetch");
        }

        Instant now = Instant.now();
        String leaseToken = UUID.randomUUID().toString();
        Instant leaseUntil = now.plus(LEASE_DURATION);

        // Claim nguyên tử. 0 dòng = job khác đang giữ, hoặc nguồn không đủ điều kiện.
        int claimed = sources.claimLease(sourceId, leaseToken, leaseUntil, now);
        if (claimed == 0) {
            NewsSource existing = sources.findById(sourceId).orElse(null);
            String reason = existing == null ? "SOURCE_NOT_FOUND"
                : !existing.ingestible() ? "SOURCE_NOT_INGESTIBLE"
                : existing.leaseActive(now) ? "LEASE_HELD"
                : "NOT_DUE";
            log.info("news.ingest skipped source={} reason={}", sourceId, reason);
            return new Outcome(null, NewsIngestionRun.Status.SKIPPED, 0, 0, 0, 0, 0,
                reason, "Không claim được nguồn: " + reason);
        }

        NewsSource source = sources.findById(sourceId).orElseThrow();
        int expectedRevision = source.sourceRevision;
        String runId = UUID.randomUUID().toString();
        Instant startedAt = now;
        long begin = System.nanoTime();

        try {
            runs.save(run(runId, sourceId, startedAt, NewsIngestionRun.Status.RUNNING));

            NewsFeedFetcher.FetchResult fetched =
                fetcher.fetch(source.feedUrl, source.httpEtag, source.httpLastModified);

            if (fetched.failed()) {
                return finishFailure(runId, sourceId, leaseToken, startedAt, begin,
                    fetched.status() == 0 ? null : (short) fetched.status(),
                    fetched.errorCode(), fetched.errorMessage(), fetched.retryAfter());
            }

            if (fetched.notModified()) {
                // 304: nguồn liên hệ thành công, nội dung không đổi.
                // Không tạo article, không đụng lastSeenAt của bài cũ.
                Instant nextFetch = now.plusSeconds(source.fetchIntervalMinutes * 60L);
                persistence.markSuccess(sourceId, leaseToken, expectedRevision,
                    fetched.etag(), fetched.lastModified(), nextFetch, now);
                return finishRun(runId, sourceId, leaseToken, startedAt, begin,
                    NewsIngestionRun.Status.NOT_MODIFIED, (short) 304, 0, 0, 0, 0, 0,
                    null, null);
            }

            NewsFeedParser.Result parsed;
            try {
                parsed = NewsFeedParser.parse(fetched.body());
            } catch (Exception e) {
                return finishFailure(runId, sourceId, leaseToken, startedAt, begin,
                    (short) fetched.status(), "PARSE_ERROR", safeMessage(e), null);
            }

            NewsIngestionPersistenceService.Persisted result =
                persistence.persist(sourceId, leaseToken, expectedRevision, parsed, now);

            if (result.leaseLost() || result.sourceChanged()) {
                String code = result.leaseLost() ? "LEASE_LOST" : "SOURCE_CHANGED";
                return finishRun(runId, sourceId, leaseToken, startedAt, begin,
                    NewsIngestionRun.Status.SKIPPED, (short) fetched.status(),
                    parsed.items().size() + parsed.rejected(), 0, 0, 0, parsed.rejected(),
                    code, "Nguồn đã thay đổi trong lúc fetch; bỏ kết quả");
            }

            Instant nextFetch = now.plusSeconds(source.fetchIntervalMinutes * 60L);
            persistence.markSuccess(sourceId, leaseToken, expectedRevision,
                fetched.etag(), fetched.lastModified(), nextFetch, now);

            NewsIngestionRun.Status status = result.rejected() > 0
                && result.inserted() == 0 && result.updated() == 0
                ? NewsIngestionRun.Status.PARTIAL_SUCCESS
                : NewsIngestionRun.Status.SUCCESS;

            return finishRun(runId, sourceId, leaseToken, startedAt, begin, status,
                (short) fetched.status(), parsed.items().size() + parsed.rejected(),
                result.inserted(), result.updated(), result.duplicate(), result.rejected(),
                null, null);

        } catch (RuntimeException e) {
            // Lỗi bất ngờ: ghi FAILED, giải phóng lease, cho phép retry.
            log.error("news.ingest failed source={} run={} error={}",
                sourceId, runId, e.getClass().getSimpleName());
            return finishFailure(runId, sourceId, leaseToken, startedAt, begin, null,
                "INTERNAL_ERROR", safeMessage(e), null);
        } finally {
            // Luôn giải phóng lease — kể cả khi lỗi. Chỉ job giữ token mới giải phóng được.
            sources.releaseLease(sourceId, leaseToken);
        }
    }

    /** Ghi run thành công và giải phóng lease (lease giải phóng ở finally). */
    private Outcome finishRun(String runId, String sourceId, String leaseToken,
                              Instant startedAt, long begin, NewsIngestionRun.Status status,
                              Short httpStatus, int received, int inserted, int updated,
                              int duplicate, int rejected, String errorCode, String errorMessage) {
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

        log.info("news.ingest source={} run={} status={} received={} inserted={} updated={} "
                + "duplicate={} rejected={} durationMs={}",
            sourceId, runId, status, received, inserted, updated, duplicate, rejected, durationMs);

        return new Outcome(runId, status, received, inserted, updated, duplicate, rejected,
            errorCode, errorMessage);
    }

    /** Ghi run thất bại, tính backoff (tôn trọng Retry-After), giải phóng lease. */
    private Outcome finishFailure(String runId, String sourceId, String leaseToken,
                                  Instant startedAt, long begin, Short httpStatus,
                                  String errorCode, String errorMessage, String retryAfter) {
        Instant now = Instant.now();
        Instant nextFetch = computeNextFetch(sourceId, errorCode, retryAfter, now);
        persistence.markFailure(sourceId, leaseToken, errorCode, errorMessage, nextFetch, now);
        return finishRun(runId, sourceId, leaseToken, startedAt, begin,
            NewsIngestionRun.Status.FAILED, httpStatus, 0, 0, 0, 0, 0, errorCode, errorMessage);
    }

    /**
     * Tính thời điểm fetch tiếp theo.
     *
     * <p>429 → tôn trọng {@code Retry-After} (không bao giờ sớm hơn). Lỗi khác →
     * backoff luỹ thừa theo {@code consecutiveFailures}, có trần.
     */
    Instant computeNextFetch(String sourceId, String errorCode, String retryAfter, Instant now) {
        if ("RATE_LIMITED".equals(errorCode)) {
            Instant parsed = NewsFeedFetcher.parseRetryAfter(retryAfter);
            if (parsed != null && parsed.isAfter(now)) return parsed;
            // Không có Retry-After hợp lệ: chờ tối thiểu 15 phút.
            return now.plus(BASE_BACKOFF);
        }
        NewsSource source = sources.findById(sourceId).orElse(null);
        int failures = source == null ? 1 : Math.max(source.consecutiveFailures, 1);
        long minutes = BASE_BACKOFF.toMinutes() * (1L << Math.min(failures - 1, 5));
        Duration backoff = Duration.ofMinutes(Math.min(minutes, MAX_BACKOFF.toMinutes()));
        return now.plus(backoff);
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
        return sources.findDue(Instant.now()).stream()
            .map(source -> ingest(source.id))
            .toList();
    }
}
