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
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;

/**
 * Transaction fencing và bảo vệ quyết định của admin.
 *
 * <p>Kiểm chứng: job cũ không ghi đè job mới, không ghi đè admin visibility/featured,
 * không ghi đè source rights, và fencing phát hiện thay đổi đồng thời.
 */
@SpringBootTest
@EnabledIfEnvironmentVariable(named = "DB_URL", matches = ".+")
class NewsFencingIT {

    @Autowired NewsIngestionPersistenceService persistence;
    @Autowired NewsSourceRepository sources;
    @Autowired NewsArticleRepository articles;
    @Autowired JdbcTemplate jdbc;

    private final List<String> createdSources = new java.util.ArrayList<>();

    @BeforeEach
    void guardIsolatedDatabase() {
        vn.smartprop.testing.Pr41DatabaseTestSafety.require(jdbc);
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

    private String source(String code) {
        String id = UUID.randomUUID().toString();
        jdbc.update("""
            INSERT INTO news_sources (id, source_code, name, publisher, website_url, feed_url,
              default_category, default_region, rights_review_status, rights_reference,
              enabled, fetch_interval_minutes, source_revision, allow_summary)
            VALUES (?, ?, ?, 'NXB', 'https://example.vn', ?, 'MARKET', 'DA_NANG',
              'APPROVED', 'IT-REF', 1, 30, 1, 1)
            """, id, code, "Nguồn " + code, "https://example.vn/" + code + ".rss");
        createdSources.add(id);
        return id;
    }

    private String article(String sourceId, String title) {
        String id = UUID.randomUUID().toString();
        jdbc.update("""
            INSERT INTO news_articles (id, source_id, canonical_url, canonical_url_hash, title,
              summary, category, region, published_at, fetched_at, first_seen_at, last_seen_at,
              publication_status, featured)
            VALUES (?, ?, ?, ?, ?, 'Tóm tắt cũ', 'MARKET', 'DA_NANG', UTC_TIMESTAMP(6),
              UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 'VISIBLE', 0)
            """, id, sourceId, "https://example.vn/" + id,
            NewsText.sha256("https://example.vn/" + id), title);
        return id;
    }

    private NewsFeedParser.Result feedWith(String title, String link) {
        return new NewsFeedParser.Result(
            List.of(new NewsFeedParser.Item(link, link, title, "Tóm tắt mới", Instant.now())),
            0, "RSS");
    }

    private String claim(String sourceId) {
        Instant now = Instant.now();
        String token = UUID.randomUUID().toString();
        int rows = sources.claimLease(sourceId, token, now.plusSeconds(300), now);
        assertThat(rows).as("claim lease phải thành công").isEqualTo(1);
        return token;
    }

    // ---------- Fencing ----------

    @Test
    void staleWorkerCannotPersistAfterLeaseLost() {
        String id = source("it-fence-1");
        String oldToken = claim(id);
        // Job khác chiếm lease.
        jdbc.update("UPDATE news_sources SET sync_lease_token = ? WHERE id = ?",
            UUID.randomUUID().toString(), id);

        var result = persistence.persist(id, oldToken, 1,
            feedWith("Giá đất mới", "https://example.vn/new-1"), Instant.now());

        assertThat(result.leaseLost()).as("phải phát hiện mất lease").isTrue();
        assertThat(result.inserted()).isZero();
        Long count = jdbc.queryForObject(
            "SELECT COUNT(*) FROM news_articles WHERE source_id = ?", Long.class, id);
        assertThat(count).as("không được ghi article khi mất lease").isZero();
    }

    @Test
    void staleWorkerCannotPersistAfterRevisionChange() {
        String id = source("it-fence-2");
        String token = claim(id);
        // Admin sửa nguồn → revision tăng.
        jdbc.update("UPDATE news_sources SET source_revision = 2 WHERE id = ?", id);

        var result = persistence.persist(id, token, 1,
            feedWith("Giá đất mới", "https://example.vn/new-2"), Instant.now());

        assertThat(result.sourceChanged()).as("phải phát hiện revision đổi").isTrue();
        assertThat(result.inserted()).isZero();
    }

    @Test
    void expiredLeaseBlocksPersist() {
        String id = source("it-fence-3");
        String token = claim(id);
        // Lease hết hạn.
        jdbc.update("UPDATE news_sources SET sync_lease_until = ? WHERE id = ?",
            java.sql.Timestamp.from(Instant.now().minusSeconds(60)), id);

        var result = persistence.persist(id, token, 1,
            feedWith("Giá đất mới", "https://example.vn/new-3"), Instant.now());

        assertThat(result.leaseLost()).as("lease hết hạn phải bị phát hiện").isTrue();
        assertThat(result.inserted()).isZero();
    }

    @Test
    void revokedRightsBlocksPersist() {
        String id = source("it-fence-4");
        String token = claim(id);
        // Admin thu hồi quyền trong lúc fetch.
        jdbc.update("""
            UPDATE news_sources SET rights_review_status='REJECTED', enabled=0 WHERE id=?
            """, id);

        var result = persistence.persist(id, token, 1,
            feedWith("Giá đất mới", "https://example.vn/new-4"), Instant.now());

        assertThat(result.sourceChanged()).as("phải phát hiện quyền bị thu hồi").isTrue();
        assertThat(result.inserted()).isZero();
    }

    @Test
    void disabledSourceBlocksPersist() {
        String id = source("it-fence-5");
        String token = claim(id);
        jdbc.update("UPDATE news_sources SET enabled = 0 WHERE id = ?", id);

        var result = persistence.persist(id, token, 1,
            feedWith("Giá đất mới", "https://example.vn/new-5"), Instant.now());

        assertThat(result.sourceChanged()).isTrue();
        assertThat(result.inserted()).isZero();
    }

    @Test
    void staleWorkerCannotMarkSuccess() {
        String id = source("it-fence-6");
        String oldToken = claim(id);
        jdbc.update("UPDATE news_sources SET sync_lease_token = ? WHERE id = ?",
            UUID.randomUUID().toString(), id);

        boolean ok = persistence.markSuccess(id, oldToken, 1, "\"etag\"", "date",
            Instant.now().plusSeconds(600), Instant.now());

        assertThat(ok).as("job cũ không được markSuccess").isFalse();
        String etag = jdbc.queryForObject(
            "SELECT http_etag FROM news_sources WHERE id = ?", String.class, id);
        assertThat(etag).as("không được ghi ETag của job cũ").isNull();
    }

    @Test
    void staleWorkerCannotMarkFailure() {
        String id = source("it-fence-7");
        String oldToken = claim(id);
        jdbc.update("UPDATE news_sources SET sync_lease_token = ? WHERE id = ?",
            UUID.randomUUID().toString(), id);

        boolean ok = persistence.markFailure(id, oldToken, 1, "HTTP_500", "lỗi",
            Instant.now().plusSeconds(600), Instant.now());

        assertThat(ok).as("job cũ không được markFailure").isFalse();
        String error = jdbc.queryForObject(
            "SELECT last_error FROM news_sources WHERE id = ?", String.class, id);
        assertThat(error).as("không được ghi lỗi của job cũ").isNull();
    }

    @Test
    void markSuccessRejectsChangedRevision() {
        String id = source("it-fence-8");
        String token = claim(id);
        jdbc.update("UPDATE news_sources SET source_revision = 5 WHERE id = ?", id);

        boolean ok = persistence.markSuccess(id, token, 1, "\"e\"", "d",
            Instant.now().plusSeconds(600), Instant.now());
        assertThat(ok).as("revision đổi thì không markSuccess").isFalse();
    }

    // ---------- Admin decision integrity ----------

    @Test
    void ingestionDoesNotOverwriteAdminHidden() {
        String id = source("it-admin-1");
        String articleId = article(id, "Giá đất sẽ bị admin ẩn");
        jdbc.update("UPDATE news_articles SET publication_status='HIDDEN' WHERE id=?", articleId);

        String token = claim(id);
        persistence.persist(id, token, 1,
            feedWith("Giá đất sẽ bị admin ẩn", "https://example.vn/" + articleId), Instant.now());

        String status = jdbc.queryForObject(
            "SELECT publication_status FROM news_articles WHERE id = ?", String.class, articleId);
        assertThat(status).as("ingestion không được đổi HIDDEN thành VISIBLE")
            .isEqualTo("HIDDEN");
    }

    @Test
    void ingestionDoesNotOverwriteAdminFeatured() {
        String id = source("it-admin-2");
        String articleId = article(id, "Giá đất được admin ghim");
        jdbc.update("UPDATE news_articles SET featured = 1 WHERE id = ?", articleId);

        String token = claim(id);
        persistence.persist(id, token, 1,
            feedWith("Giá đất được admin ghim", "https://example.vn/" + articleId), Instant.now());

        Boolean featured = jdbc.queryForObject(
            "SELECT featured FROM news_articles WHERE id = ?", Boolean.class, articleId);
        assertThat(featured).as("ingestion không được bỏ cờ featured").isTrue();
    }

    @Test
    void ingestionUpdatesOnlyAllowedColumns() throws Exception {
        String id = source("it-admin-3");
        String articleId = article(id, "Giá đất kiểm tra cột");
        java.sql.Timestamp before = jdbc.queryForObject(
            "SELECT last_seen_at FROM news_articles WHERE id = ?",
            java.sql.Timestamp.class, articleId);

        String token = claim(id);
        Thread.sleep(20);
        persistence.persist(id, token, 1,
            feedWith("Giá đất kiểm tra cột", "https://example.vn/" + articleId), Instant.now());

        java.sql.Timestamp after = jdbc.queryForObject(
            "SELECT last_seen_at FROM news_articles WHERE id = ?",
            java.sql.Timestamp.class, articleId);
        assertThat(after).as("lastSeenAt phải được cập nhật").isAfter(before);

        // Các cột admin không bị đụng.
        String status = jdbc.queryForObject(
            "SELECT publication_status FROM news_articles WHERE id = ?", String.class, articleId);
        assertThat(status).isEqualTo("VISIBLE");
    }

    @Test
    void ingestionDoesNotOverwriteSourceRights() {
        String id = source("it-admin-4");
        String token = claim(id);
        // Admin đổi publisher + thu hồi quyền trong lúc fetch.
        jdbc.update("""
            UPDATE news_sources SET publisher='NXB Khác',
              rights_review_status='PENDING_REVIEW', enabled=0, source_revision=2
            WHERE id=?
            """, id);

        persistence.persist(id, token, 1,
            feedWith("Giá đất mới", "https://example.vn/new-admin-4"), Instant.now());

        String publisher = jdbc.queryForObject(
            "SELECT publisher FROM news_sources WHERE id = ?", String.class, id);
        assertThat(publisher).as("ingestion không được ghi đè publisher").isEqualTo("NXB Khác");

        String rights = jdbc.queryForObject(
            "SELECT rights_review_status FROM news_sources WHERE id = ?", String.class, id);
        assertThat(rights).as("ingestion không được phục hồi APPROVED")
            .isEqualTo("PENDING_REVIEW");
    }

    // ---------- Duplicate identity ----------

    @Test
    void sameGuidDifferentUrlIsRecognisedAsSameArticle() {
        String id = source("it-dup-1");
        String token = claim(id);
        String guid = "guid-stable-1";

        // Lần 1: URL A, GUID X.
        persistence.persist(id, token, 1, new NewsFeedParser.Result(
            List.of(new NewsFeedParser.Item(guid, "https://example.vn/a",
                "Giá đất Đà Nẵng", "Tóm tắt", Instant.now())), 0, "RSS"), Instant.now());

        // Lần 2: URL B, GUID X (cùng bài, URL đổi).
        var result = persistence.persist(id, token, 1, new NewsFeedParser.Result(
            List.of(new NewsFeedParser.Item(guid, "https://example.vn/b",
                "Giá đất Đà Nẵng", "Tóm tắt", Instant.now())), 0, "RSS"), Instant.now());

        Long count = jdbc.queryForObject(
            "SELECT COUNT(*) FROM news_articles WHERE source_id = ?", Long.class, id);
        assertThat(count).as("cùng GUID phải nhận ra là cùng bài, không tạo bản ghi mới")
            .isEqualTo(1);
        assertThat(result.inserted()).isZero();
    }

    @Test
    void sameUrlDifferentGuidIsRecognisedAsSameArticle() {
        String id = source("it-dup-2");
        String token = claim(id);

        persistence.persist(id, token, 1, new NewsFeedParser.Result(
            List.of(new NewsFeedParser.Item("guid-a", "https://example.vn/same",
                "Giá đất Đà Nẵng", "Tóm tắt", Instant.now())), 0, "RSS"), Instant.now());

        var result = persistence.persist(id, token, 1, new NewsFeedParser.Result(
            List.of(new NewsFeedParser.Item("guid-b", "https://example.vn/same",
                "Giá đất Đà Nẵng", "Tóm tắt", Instant.now())), 0, "RSS"), Instant.now());

        Long count = jdbc.queryForObject(
            "SELECT COUNT(*) FROM news_articles WHERE source_id = ?", Long.class, id);
        assertThat(count).as("cùng URL phải nhận ra là cùng bài").isEqualTo(1);
        assertThat(result.inserted()).isZero();
    }

    @Test
    void conflictingIdentitiesAreRejectedNotMerged() {
        String id = source("it-dup-3");
        String token = claim(id);

        // Bài A: URL A + GUID A.
        persistence.persist(id, token, 1, new NewsFeedParser.Result(
            List.of(new NewsFeedParser.Item("guid-a", "https://example.vn/a",
                "Giá đất khu A", "Tóm tắt", Instant.now())), 0, "RSS"), Instant.now());
        // Bài B: URL B + GUID B.
        persistence.persist(id, token, 1, new NewsFeedParser.Result(
            List.of(new NewsFeedParser.Item("guid-b", "https://example.vn/b",
                "Giá đất khu B", "Tóm tắt", Instant.now())), 0, "RSS"), Instant.now());

        // Item xung đột: URL A nhưng GUID B.
        var result = persistence.persist(id, token, 1, new NewsFeedParser.Result(
            List.of(new NewsFeedParser.Item("guid-b", "https://example.vn/a",
                "Giá đất xung đột", "Tóm tắt", Instant.now())), 0, "RSS"), Instant.now());

        assertThat(result.rejected()).as("identity xung đột phải bị từ chối, không hợp nhất")
            .isEqualTo(1);
        Long count = jdbc.queryForObject(
            "SELECT COUNT(*) FROM news_articles WHERE source_id = ?", Long.class, id);
        assertThat(count).as("không được tạo bản ghi thứ ba").isEqualTo(2);
    }

    // ---------- Concurrent fencing ----------

    @Test
    void concurrentPersistAllowsOnlyLeaseHolder() throws Exception {
        String id = source("it-fence-conc");
        String tokenA = claim(id);
        int threads = 4;
        CountDownLatch barrier = new CountDownLatch(1);
        ExecutorService pool = Executors.newFixedThreadPool(threads);
        java.util.concurrent.atomic.AtomicInteger inserted =
            new java.util.concurrent.atomic.AtomicInteger();

        List<Future<?>> futures = new java.util.ArrayList<>();
        for (int i = 0; i < threads; i++) {
            final int index = i;
            futures.add(pool.submit(() -> {
                try {
                    barrier.await();
                    var r = persistence.persist(id, tokenA, 1, new NewsFeedParser.Result(
                        List.of(new NewsFeedParser.Item("g" + index,
                            "https://example.vn/conc-" + index,
                            "Giá đất " + index, "Tóm tắt", Instant.now())), 0, "RSS"),
                        Instant.now());
                    inserted.addAndGet(r.inserted());
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }));
        }
        barrier.countDown();
        for (Future<?> f : futures) f.get(60, TimeUnit.SECONDS);
        pool.shutdown();

        Long count = jdbc.queryForObject(
            "SELECT COUNT(*) FROM news_articles WHERE source_id = ?", Long.class, id);
        assertThat(count).as("không được tạo bản ghi trùng khi persist đồng thời")
            .isEqualTo((long) inserted.get());
    }

    @Test void expiredLeaseCannotMarkSuccessOrFailure() {
        String id=source("it-expired-finish");String token=claim(id);
        jdbc.update("UPDATE news_sources SET sync_lease_until=DATE_SUB(UTC_TIMESTAMP(6),INTERVAL 1 SECOND) WHERE id=?",id);
        Instant now=Instant.now();
        assertThat(persistence.markSuccess(id,token,1,null,null,now.plusSeconds(60),now)).isFalse();
        assertThat(persistence.markFailure(id,token,1,"SYNTHETIC","fixture",now.plusSeconds(60),now)).isFalse();
    }
    @Test void sourceRevisionChangeFencesFailureMetadata() {
        String id=source("it-revision-failure");String token=claim(id);
        jdbc.update("UPDATE news_sources SET source_revision=2 WHERE id=?",id);
        Instant now=Instant.now();
        assertThat(persistence.markFailure(id,token,1,"SYNTHETIC","fixture",now.plusSeconds(60),now)).isFalse();
        assertThat(jdbc.queryForObject("SELECT last_error FROM news_sources WHERE id=?",String.class,id)).isNull();
    }

    @Test void staleCallerTimestampCannotResurrectExpiredLease() {
        String id=source("it-stale-clock");String token=claim(id);
        jdbc.update("UPDATE news_sources SET sync_lease_until=DATE_SUB(UTC_TIMESTAMP(6),INTERVAL 1 SECOND) WHERE id=?",id);
        Instant staleTime=Instant.now().minusSeconds(3600);
        assertThat(persistence.persist(id,token,1,feedWith("Giá đất synthetic", "https://example.vn/stale-clock"),staleTime).leaseLost()).isTrue();
        assertThat(persistence.markSuccess(id,token,1,null,null,Instant.now().plusSeconds(60),staleTime)).isFalse();
        assertThat(persistence.markFailure(id,token,1,"SYNTHETIC","fixture",Instant.now().plusSeconds(60),staleTime)).isFalse();
    }
}
