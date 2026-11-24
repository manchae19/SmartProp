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
 * Global ingestion safety gate — mọi đường vào đều bị chặn khi ingestion tắt.
 *
 * <p>Kiểm chứng: không claim lease, không tạo run, không HTTP request, không ghi
 * article. Public read API vẫn hoạt động.
 */
@SpringBootTest
@EnabledIfEnvironmentVariable(named = "DB_URL", matches = ".+")
class NewsSafetyGateIT {

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

    private String approvedSource(String code) {
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

    @Test
    void ingestionDisabledByDefault() {
        // Mặc định NewsProperties.ingestionEnabled = false.
        assertThat(new NewsProperties().isIngestionEnabled())
            .as("ingestion phải tắt mặc định").isFalse();
    }

    @Test
    void ingestReturnsSkippedWhenGlobalGateClosed() {
        String id = approvedSource("it-gate-1");
        NewsIngestionService.Outcome outcome = ingestion.ingest(id);

        assertThat(outcome.status()).isEqualTo(NewsIngestionRun.Status.SKIPPED);
        assertThat(outcome.errorCode()).isEqualTo("INGESTION_DISABLED");
    }

    @Test
    void noLeaseClaimedWhenGateClosed() {
        String id = approvedSource("it-gate-2");
        ingestion.ingest(id);

        String token = jdbc.queryForObject(
            "SELECT sync_lease_token FROM news_sources WHERE id = ?", String.class, id);
        assertThat(token).as("không được claim lease khi gate đóng").isNull();
    }

    @Test
    void noRunCreatedWhenGateClosed() {
        String id = approvedSource("it-gate-3");
        ingestion.ingest(id);

        Long runs = jdbc.queryForObject(
            "SELECT COUNT(*) FROM news_ingestion_runs WHERE source_id = ?", Long.class, id);
        assertThat(runs).as("không được tạo ingestion run khi gate đóng").isZero();
    }

    @Test
    void noArticleWrittenWhenGateClosed() {
        String id = approvedSource("it-gate-4");
        ingestion.ingest(id);

        Long articles = jdbc.queryForObject(
            "SELECT COUNT(*) FROM news_articles WHERE source_id = ?", Long.class, id);
        assertThat(articles).as("không được ghi article khi gate đóng").isZero();
    }

    @Test
    void lastAttemptNotTouchedWhenGateClosed() {
        String id = approvedSource("it-gate-5");
        ingestion.ingest(id);

        Instant lastAttempt = jdbc.queryForObject(
            "SELECT last_attempt_at FROM news_sources WHERE id = ?", Instant.class, id);
        assertThat(lastAttempt).as("không được đụng lastAttemptAt khi gate đóng").isNull();
    }

    @Test
    void ingestDueSkipsEverySourceWhenGateClosed() {
        approvedSource("it-gate-6");
        var outcomes = ingestion.ingestDue();
        // Mỗi nguồn đến hạn trả một outcome SKIPPED — không fetch, không ghi.
        assertThat(outcomes).isNotEmpty();
        assertThat(outcomes).allSatisfy(outcome -> {
            assertThat(outcome.status()).isEqualTo(NewsIngestionRun.Status.SKIPPED);
            assertThat(outcome.errorCode()).isEqualTo("INGESTION_DISABLED");
        });
    }

    @Test
    void publicReadStillWorksWhenIngestionDisabled() {
        // Gate chỉ chặn ghi/fetch, không chặn đọc.
        var page = read.list(null, null, "newest", 0, 10);
        assertThat(page).isNotNull();
        assertThat(page.items()).isNotNull();
    }

    @Test
    void emptyAllowlistBlocksIngestionEvenWhenEnabled() {
        // Bật ingestion nhưng allowlist rỗng → vẫn từ chối.
        NewsProperties props = new NewsProperties();
        props.setIngestionEnabled(true);
        props.setEnforceHostAllowlist(true);
        props.setAllowedHosts(List.of());

        NewsFeedFetcher fetcher = new NewsFeedFetcher(props);
        NewsIngestionPersistenceService persistence =
            new NewsIngestionPersistenceService(sources, null);
        NewsIngestionService service = new NewsIngestionService(
            sources, null, fetcher, persistence, props);

        String id = approvedSource("it-gate-7");
        NewsIngestionService.Outcome outcome = service.ingest(id);

        assertThat(outcome.status()).isEqualTo(NewsIngestionRun.Status.SKIPPED);
        assertThat(outcome.errorCode()).isEqualTo("ALLOWLIST_EMPTY");
    }
}
