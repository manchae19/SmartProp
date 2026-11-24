package vn.smartprop.modules.news;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;

/**
 * Concurrency, lease, sorting và rights enforcement trên MySQL thật.
 *
 * <p>Chỉ chạy khi {@code DB_URL} trỏ tới DB cô lập. Test này ghi dữ liệu và dọn dẹp
 * sau mỗi ca — không được chạy trên database nhóm.
 */
@SpringBootTest
@EnabledIfEnvironmentVariable(named = "DB_URL", matches = ".+")
class NewsConcurrencyIT {

    @Autowired NewsSourceRepository sources;
    @Autowired NewsArticleRepository articles;
    @Autowired NewsIngestionService ingestion;
    @Autowired NewsService read;
    @Autowired JdbcTemplate jdbc;

    private final List<String> createdSources = new java.util.ArrayList<>();

    @BeforeEach
    void guardIsolatedDatabase() {
        // Fail closed: từ chối chạy nếu không phải DB cô lập.
        Integer port = jdbc.queryForObject("SELECT @@port", Integer.class);
        String schema = jdbc.queryForObject("SELECT DATABASE()", String.class);
        assertThat(port).as("test ghi dữ liệu chỉ được chạy trên MySQL cô lập (3307)")
            .isEqualTo(3307);
        assertThat(schema).isEqualTo("smartprop");
    }

    @AfterEach
    void cleanUp() {
        for (String id : createdSources) {
            jdbc.update("DELETE FROM news_ingestion_runs WHERE source_id = ?", id);
            jdbc.update("DELETE FROM news_articles WHERE source_id = ?", id);
            jdbc.update("DELETE FROM news_sources WHERE id = ?", id);
        }
        createdSources.clear();
    }

    private String source(String code, String rights, boolean enabled) {
        String id = UUID.randomUUID().toString();
        jdbc.update("""
            INSERT INTO news_sources (id, source_code, name, publisher, website_url, feed_url,
              default_category, default_region, rights_review_status, rights_reference,
              enabled, fetch_interval_minutes, source_revision)
            VALUES (?, ?, ?, 'NXB', 'https://example.vn', ?, 'MARKET', 'DA_NANG',
              ?, 'IT-REF', ?, 30, 1)
            """, id, code, "Nguồn " + code, "https://example.vn/" + code + ".rss",
            rights, enabled);
        createdSources.add(id);
        return id;
    }

    private String article(String sourceId, String title, Instant publishedAt, String status) {
        String id = UUID.randomUUID().toString();
        jdbc.update("""
            INSERT INTO news_articles (id, source_id, canonical_url, canonical_url_hash, title,
              category, region, published_at, fetched_at, first_seen_at, last_seen_at,
              publication_status)
            VALUES (?, ?, ?, ?, ?, 'MARKET', 'DA_NANG', ?, UTC_TIMESTAMP(6),
              UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), ?)
            """, id, sourceId, "https://example.vn/" + id,
            NewsText.sha256("https://example.vn/" + id), title,
            publishedAt == null ? null : java.sql.Timestamp.from(publishedAt), status);
        return id;
    }

    // ---------- Lease ----------

    @Test
    void onlyOneJobCanClaimLease() {
        String id = source("it-lease", "APPROVED", true);
        Instant now = Instant.now();
        String tokenA = UUID.randomUUID().toString();
        String tokenB = UUID.randomUUID().toString();

        int first = sources.claimLease(id, tokenA, now.plusSeconds(300), now);
        int second = sources.claimLease(id, tokenB, now.plusSeconds(300), now);

        assertThat(first).as("job đầu claim được").isEqualTo(1);
        assertThat(second).as("job thứ hai bị từ chối").isZero();
    }

    @Test
    void expiredLeaseCanBeReclaimed() {
        String id = source("it-lease-exp", "APPROVED", true);
        Instant past = Instant.now().minusSeconds(600);
        String oldToken = UUID.randomUUID().toString();
        sources.claimLease(id, oldToken, past, past);

        String newToken = UUID.randomUUID().toString();
        int claimed = sources.claimLease(id, newToken, Instant.now().plusSeconds(300),
            Instant.now());
        assertThat(claimed).as("lease hết hạn phải claim lại được").isEqualTo(1);
    }

    @Test
    void oldJobCannotReleaseNewLease() {
        String id = source("it-lease-rel", "APPROVED", true);
        Instant now = Instant.now();
        String oldToken = UUID.randomUUID().toString();
        sources.claimLease(id, oldToken, now.minusSeconds(1), now.minusSeconds(600));

        String newToken = UUID.randomUUID().toString();
        sources.claimLease(id, newToken, now.plusSeconds(300), now);

        int released = sources.releaseLease(id, oldToken);
        assertThat(released).as("job cũ không giải phóng được lease của job mới").isZero();

        String current = jdbc.queryForObject(
            "SELECT sync_lease_token FROM news_sources WHERE id = ?", String.class, id);
        assertThat(current).isEqualTo(newToken);
    }

    @Test
    void unapprovedSourceCannotBeClaimed() {
        String id = source("it-lease-pending", "PENDING_REVIEW", true);
        int claimed = sources.claimLease(id, UUID.randomUUID().toString(),
            Instant.now().plusSeconds(300), Instant.now());
        assertThat(claimed).as("nguồn chưa duyệt quyền không claim được").isZero();
    }

    @Test
    void disabledSourceCannotBeClaimed() {
        String id = source("it-lease-disabled", "APPROVED", false);
        int claimed = sources.claimLease(id, UUID.randomUUID().toString(),
            Instant.now().plusSeconds(300), Instant.now());
        assertThat(claimed).as("nguồn đang tắt không claim được").isZero();
    }

    @Test
    void cooldownBlocksClaim() {
        String id = source("it-cooldown", "APPROVED", true);
        jdbc.update("UPDATE news_sources SET next_fetch_at = ? WHERE id = ?",
            java.sql.Timestamp.from(Instant.now().plusSeconds(600)), id);

        int claimed = sources.claimLease(id, UUID.randomUUID().toString(),
            Instant.now().plusSeconds(300), Instant.now());
        assertThat(claimed).as("đang trong cooldown thì không claim được").isZero();
    }

    // ---------- Concurrent ingestion ----------

    @Test
    void concurrentIngestAllowsOnlyOneWinner() throws Exception {
        String id = source("it-concurrent", "APPROVED", true);
        int threads = 4;
        CountDownLatch barrier = new CountDownLatch(1);
        ExecutorService pool = Executors.newFixedThreadPool(threads);
        AtomicInteger claimed = new AtomicInteger();

        List<Future<?>> futures = new java.util.ArrayList<>();
        for (int i = 0; i < threads; i++) {
            futures.add(pool.submit(() -> {
                try {
                    barrier.await();
                    Instant now = Instant.now();
                    int rows = sources.claimLease(id, UUID.randomUUID().toString(),
                        now.plusSeconds(300), now);
                    if (rows == 1) claimed.incrementAndGet();
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }));
        }
        barrier.countDown();
        for (Future<?> f : futures) f.get(30, TimeUnit.SECONDS);
        pool.shutdown();

        assertThat(claimed.get())
            .as("chỉ một job claim được lease trong %d thread đồng thời", threads)
            .isEqualTo(1);
    }

    @Test
    void twoDifferentSourcesClaimIndependently() throws Exception {
        String a = source("it-indep-a", "APPROVED", true);
        String b = source("it-indep-b", "APPROVED", true);
        CountDownLatch barrier = new CountDownLatch(1);
        ExecutorService pool = Executors.newFixedThreadPool(2);

        Future<Integer> fa = pool.submit(() -> {
            barrier.await();
            Instant now = Instant.now();
            return sources.claimLease(a, UUID.randomUUID().toString(),
                now.plusSeconds(300), now);
        });
        Future<Integer> fb = pool.submit(() -> {
            barrier.await();
            Instant now = Instant.now();
            return sources.claimLease(b, UUID.randomUUID().toString(),
                now.plusSeconds(300), now);
        });
        barrier.countDown();

        assertThat(fa.get(30, TimeUnit.SECONDS)).as("nguồn A claim được").isEqualTo(1);
        assertThat(fb.get(30, TimeUnit.SECONDS)).as("nguồn B claim được").isEqualTo(1);
        pool.shutdown();
    }

    @Test
    void ingestSkipsWhenLeaseHeld() {
        String id = source("it-skip", "APPROVED", true);
        Instant now = Instant.now();
        sources.claimLease(id, UUID.randomUUID().toString(), now.plusSeconds(300), now);

        NewsIngestionService.Outcome outcome = ingestion.ingest(id);
        assertThat(outcome.status()).isEqualTo(NewsIngestionRun.Status.SKIPPED);
        assertThat(outcome.errorCode()).isEqualTo("LEASE_HELD");
    }

    @Test
    void ingestSkipsUnapprovedSource() {
        String id = source("it-skip-pending", "PENDING_REVIEW", true);
        NewsIngestionService.Outcome outcome = ingestion.ingest(id);
        assertThat(outcome.status()).isEqualTo(NewsIngestionRun.Status.SKIPPED);
        assertThat(outcome.errorCode()).isEqualTo("SOURCE_NOT_INGESTIBLE");
    }

    @Test
    void leaseIsReleasedAfterIngest() {
        String id = source("it-release", "APPROVED", true);
        ingestion.ingest(id);
        String token = jdbc.queryForObject(
            "SELECT sync_lease_token FROM news_sources WHERE id = ?", String.class, id);
        assertThat(token).as("lease phải được giải phóng sau khi ingest xong").isNull();
    }

    @Test
    void noRunStaysRunningAfterIngest() {
        String id = source("it-running", "APPROVED", true);
        ingestion.ingest(id);
        Long running = jdbc.queryForObject("""
            SELECT COUNT(*) FROM news_ingestion_runs
            WHERE source_id = ? AND status = 'RUNNING'
            """, Long.class, id);
        assertThat(running).as("không được có run RUNNING vĩnh viễn").isZero();
    }

    // ---------- Sorting ----------

    @Test
    void oldestSortingIsDoneInDatabase() {
        String id = source("it-sort", "APPROVED", true);
        Instant base = Instant.parse("2026-11-01T00:00:00Z");
        for (int i = 0; i < 25; i++) {
            article(id, "Bài " + i, base.plusSeconds(i * 3600L), "VISIBLE");
        }

        var newestPage0 = read.list(null, null, "newest", 0, 10);
        var newestPage1 = read.list(null, null, "newest", 1, 10);
        var oldestPage0 = read.list(null, null, "oldest", 0, 10);
        var oldestPage1 = read.list(null, null, "oldest", 1, 10);

        assertThat(newestPage0.items()).hasSize(10);
        assertThat(oldestPage0.items()).hasSize(10);
        assertThat(newestPage0.totalElements()).isEqualTo(25);

        // Trang 0 và trang 1 không trùng bài.
        var newestIds = new java.util.HashSet<String>();
        newestPage0.items().forEach(a -> newestIds.add(a.id()));
        newestPage1.items().forEach(a -> assertThat(newestIds).doesNotContain(a.id()));

        // Oldest page 0 phải là bài cũ nhất, không phải đảo của newest page 0.
        Instant firstOldest = oldestPage0.items().get(0).publishedAt();
        Instant firstNewest = newestPage0.items().get(0).publishedAt();
        assertThat(firstOldest).as("oldest page 0 bắt đầu từ bài cũ nhất")
            .isBefore(firstNewest);

        // Oldest page 1 tiếp tục tăng dần, không quay lại đầu.
        Instant lastOfPage0 = oldestPage0.items().get(9).publishedAt();
        Instant firstOfPage1 = oldestPage1.items().get(0).publishedAt();
        assertThat(firstOfPage1).as("oldest page 1 nối tiếp page 0")
            .isAfter(lastOfPage0);
    }

    @Test
    void nullPublishedAtSortsLastInBothDirections() {
        String id = source("it-null-date", "APPROVED", true);
        article(id, "Có ngày", Instant.parse("2026-11-01T00:00:00Z"), "VISIBLE");
        article(id, "Không ngày", null, "VISIBLE");

        var newest = read.list(null, null, "newest", 0, 10);
        var oldest = read.list(null, null, "oldest", 0, 10);

        assertThat(newest.items().get(newest.items().size() - 1).publishedAt())
            .as("bài không rõ ngày xuống cuối khi newest").isNull();
        assertThat(oldest.items().get(oldest.items().size() - 1).publishedAt())
            .as("bài không rõ ngày xuống cuối khi oldest").isNull();
    }

    @Test
    void invalidSortIsRejected() {
        org.junit.jupiter.api.Assertions.assertThrows(
            vn.smartprop.common.ApiException.class,
            () -> read.list(null, null, "random_sql", 0, 10));
    }

    // ---------- Rights enforcement ----------

    @Test
    void articleFromRevokedSourceDisappearsFromPublic() {
        String id = source("it-revoke", "APPROVED", true);
        article(id, "Bài trước khi thu hồi", Instant.now(), "VISIBLE");

        var before = read.list(null, "thu hồi", "newest", 0, 10);
        assertThat(before.items()).isNotEmpty();

        jdbc.update("""
            UPDATE news_sources SET rights_review_status='REJECTED', enabled=0 WHERE id=?
            """, id);

        var after = read.list(null, "thu hồi", "newest", 0, 10);
        assertThat(after.items()).as("thu hồi quyền thì bài không còn công khai").isEmpty();
    }

    @Test
    void hiddenArticleIsExcludedFromPublic() {
        String id = source("it-hidden", "APPROVED", true);
        article(id, "Bài bị ẩn", Instant.now(), "HIDDEN");

        var page = read.list(null, "bị ẩn", "newest", 0, 10);
        assertThat(page.items()).isEmpty();
    }

    @Test
    void summaryIsNotStoredWhenSourceDisallowsIt() {
        String id = source("it-no-summary", "APPROVED", true);
        jdbc.update("UPDATE news_sources SET allow_summary = 0 WHERE id = ?", id);

        NewsSource source = sources.findById(id).orElseThrow();
        assertThat(source.allowSummary).isFalse();
        assertThat(source.allowImages).as("ảnh mặc định không được phép").isFalse();
    }

    // ---------- Stats ----------

    @Test
    void statsUsesAggregatesNotFullTableLoad() {
        String id = source("it-stats", "APPROVED", true);
        article(id, "Bài A", Instant.now(), "VISIBLE");
        article(id, "Bài B", Instant.now(), "HIDDEN");

        var stats = read.stats();
        assertThat(stats.totalSources()).isGreaterThan(0);
        assertThat(stats.approvedSources()).isGreaterThan(0);
        assertThat(stats.visibleArticles()).isGreaterThanOrEqualTo(1);
        assertThat(stats.hiddenArticles()).isGreaterThanOrEqualTo(1);
    }
}
