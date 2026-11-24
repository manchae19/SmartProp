package vn.smartprop.modules.news;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;

/**
 * Read-only release gate — live ingestion bị khóa bằng hằng số biên dịch.
 *
 * <p>Kiểm chứng: không cấu hình nào mở được, không outbound request, không lease,
 * không run, không article. Public read vẫn hoạt động.
 */
@SpringBootTest
@EnabledIfEnvironmentVariable(named = "DB_URL", matches = ".+")
class NewsReleaseLockIT {

    @Autowired NewsIngestionService ingestion;
    @Autowired NewsSourceRepository sources;
    @Autowired NewsService read;
    @Autowired JdbcTemplate jdbc;

    private final List<String> createdSources = new java.util.ArrayList<>();

    @BeforeEach
    void guardIsolatedDatabase() {
        Integer port = jdbc.queryForObject("SELECT @@port", Integer.class);
        assertThat(port).as("test ghi dữ liệu chỉ chạy trên MySQL cô lập (3307)")
            .isEqualTo(3307);
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

    private String approvedEnabledSource(String code) {
        String id = UUID.randomUUID().toString();
        jdbc.update("""
            INSERT INTO news_sources (id, source_code, name, publisher, website_url, feed_url,
              default_category, default_region, rights_review_status, rights_reference,
              enabled, fetch_interval_minutes, source_revision)
            VALUES (?, ?, ?, 'NXB', 'https://example.vn', ?, 'MARKET', 'DA_NANG',
              'APPROVED', 'IT-REF', 1, 30, 1)
            """, id, code, "Nguồn " + code, "https://example.vn/" + code + ".rss");
        createdSources.add(id);
        return id;
    }

    // ---------- Release capability ----------

    @Test
    void releaseCapabilityIsHardLocked() {
        assertThat(NewsReleaseCapability.liveIngestionPermitted())
            .as("V1 là read-only release — live ingestion phải bị khóa")
            .isFalse();
    }

    @Test
    void lockCodeAndReasonAreDefined() {
        assertThat(NewsReleaseCapability.LOCK_CODE).isEqualTo("LIVE_INGESTION_LOCKED");
        assertThat(NewsReleaseCapability.LOCK_REASON).isNotBlank();
    }

    // ---------- Ingestion blocked regardless of configuration ----------

    @Test
    void ingestBlockedEvenWhenIngestionEnabledAndAllowlistConfigured() {
        // Bật mọi thứ có thể bật qua cấu hình.
        NewsProperties props = new NewsProperties();
        props.setIngestionEnabled(true);
        props.setEnforceHostAllowlist(true);
        props.setAllowedHosts(List.of("example.vn"));
        props.setAllowHttp(true);

        NewsFeedFetcher fetcher = new NewsFeedFetcher(props);
        NewsIngestionPersistenceService persistence =
            new NewsIngestionPersistenceService(sources, null);
        NewsIngestionService service = new NewsIngestionService(
            sources, null, fetcher, persistence, props);

        String id = approvedEnabledSource("it-lock-1");
        NewsIngestionService.Outcome outcome = service.ingest(id);

        assertThat(outcome.status()).isEqualTo(NewsIngestionRun.Status.SKIPPED);
        assertThat(outcome.errorCode()).isEqualTo("LIVE_INGESTION_LOCKED");
    }

    @Test
    void ingestBlockedEvenWhenAllowlistEnforcementDisabled() {
        NewsProperties props = new NewsProperties();
        props.setIngestionEnabled(true);
        props.setEnforceHostAllowlist(false);
        props.setAllowHttp(true);

        NewsFeedFetcher fetcher = new NewsFeedFetcher(props);
        NewsIngestionPersistenceService persistence =
            new NewsIngestionPersistenceService(sources, null);
        NewsIngestionService service = new NewsIngestionService(
            sources, null, fetcher, persistence, props);

        String id = approvedEnabledSource("it-lock-2");
        var outcome = service.ingest(id);

        assertThat(outcome.errorCode()).isEqualTo("LIVE_INGESTION_LOCKED");
    }

    @Test
    void approvedEnabledSourceStillBlocked() {
        String id = approvedEnabledSource("it-lock-3");
        var outcome = ingestion.ingest(id);

        assertThat(outcome.errorCode()).isEqualTo("LIVE_INGESTION_LOCKED");
    }

    @Test
    void schedulerBlocked() {
        approvedEnabledSource("it-lock-4");
        var outcomes = ingestion.ingestDue();

        assertThat(outcomes).isNotEmpty();
        assertThat(outcomes).allSatisfy(outcome ->
            assertThat(outcome.errorCode()).isEqualTo("LIVE_INGESTION_LOCKED"));
    }

    @Test
    void productionFetcherBlocked() {
        NewsProperties props = new NewsProperties();
        props.setIngestionEnabled(true);
        props.setAllowHttp(true);
        var fetcher = new NewsFeedFetcher(props);

        var result = fetcher.fetch("https://example.vn/feed.rss", null, null);

        assertThat(result.failed()).isTrue();
        assertThat(result.errorCode()).isEqualTo("LIVE_INGESTION_LOCKED");
        assertThat(result.body()).as("không được có body").isNull();
    }

    // ---------- No side effects ----------

    @Test
    void noLeaseCreated() {
        String id = approvedEnabledSource("it-lock-5");
        ingestion.ingest(id);

        String token = jdbc.queryForObject(
            "SELECT sync_lease_token FROM news_sources WHERE id = ?", String.class, id);
        assertThat(token).isNull();
    }

    @Test
    void noRunCreated() {
        String id = approvedEnabledSource("it-lock-6");
        ingestion.ingest(id);

        Long runs = jdbc.queryForObject(
            "SELECT COUNT(*) FROM news_ingestion_runs WHERE source_id = ?", Long.class, id);
        assertThat(runs).isZero();
    }

    @Test
    void noArticleWritten() {
        String id = approvedEnabledSource("it-lock-7");
        ingestion.ingest(id);

        Long articles = jdbc.queryForObject(
            "SELECT COUNT(*) FROM news_articles WHERE source_id = ?", Long.class, id);
        assertThat(articles).isZero();
    }

    @Test
    void lastAttemptNotTouched() {
        String id = approvedEnabledSource("it-lock-8");
        ingestion.ingest(id);

        java.sql.Timestamp lastAttempt = jdbc.queryForObject(
            "SELECT last_attempt_at FROM news_sources WHERE id = ?",
            java.sql.Timestamp.class, id);
        assertThat(lastAttempt).isNull();
    }

    // ---------- Public read still works ----------

    @Test
    void publicReadApiStillWorks() {
        var page = read.list(null, null, "newest", 0, 10);
        assertThat(page).isNotNull();
        assertThat(page.items()).isNotNull();
        assertThat(page.sources()).isNotNull();
    }

    @Test
    void featuredStillWorks() {
        var featured = read.featured();
        assertThat(featured).isNotNull();
        assertThat(featured.items()).isNotNull();
    }

    @Test
    void sourcesStillWorks() {
        var sourcesDto = read.sources();
        assertThat(sourcesDto).isNotNull();
        assertThat(sourcesDto.sources()).isNotNull();
    }
}
