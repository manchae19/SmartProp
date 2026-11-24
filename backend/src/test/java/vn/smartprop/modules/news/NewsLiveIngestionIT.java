package vn.smartprop.modules.news;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;

/**
 * Kiểm tra ingestion với feed RSS thật.
 *
 * <p>Chỉ chạy khi {@code NEWS_LIVE_TEST=1} — không chạy trong CI mặc định vì phụ
 * thuộc mạng ngoài và nguồn bên thứ ba.
 *
 * <p>Nguồn dùng cho test này có {@code rights_reference='IT-TEST-ONLY-NOT-REAL-RIGHTS'}.
 * Đây KHÔNG phải phê duyệt quyền sử dụng thật — chỉ để kiểm chứng kỹ thuật parser,
 * fetcher và deduplication trên DB cô lập.
 */
@SpringBootTest
@EnabledIfEnvironmentVariable(named = "NEWS_LIVE_TEST", matches = "1")
class NewsLiveIngestionIT {

    @Autowired NewsIngestionService ingestion;
    @Autowired NewsSourceRepository sources;
    @Autowired NewsArticleRepository articles;
    @Autowired JdbcTemplate jdbc;

    @Test
    void ingestsRealVnExpressFeedAndIsIdempotent() {
        NewsSource source = sources.findBySourceCode("it-vnexpress").orElse(null);
        assertThat(source).as("cần nguồn it-vnexpress trong DB cô lập").isNotNull();
        assertThat(source.ingestible()).as("nguồn phải APPROVED + enabled").isTrue();

        long before = articles.findBySourceId(source.id).size();

        // Lần 1
        NewsIngestionService.Outcome first = ingestion.ingest(source.id);
        System.out.printf("LIVE lần 1: status=%s received=%d inserted=%d updated=%d "
                + "duplicate=%d rejected=%d%n",
            first.status(), first.received(), first.inserted(), first.updated(),
            first.duplicate(), first.rejected());

        assertThat(first.status())
            .as("lần 1 phải SUCCESS hoặc PARTIAL_SUCCESS")
            .isIn(NewsIngestionRun.Status.SUCCESS, NewsIngestionRun.Status.PARTIAL_SUCCESS);
        assertThat(first.received()).as("phải nhận được item").isGreaterThan(0);

        long afterFirst = articles.findBySourceId(source.id).size();
        assertThat(afterFirst).as("phải chèn được bài").isGreaterThan(before);

        // Lần 2 — idempotent
        NewsIngestionService.Outcome second = ingestion.ingest(source.id);
        System.out.printf("LIVE lần 2: status=%s received=%d inserted=%d updated=%d "
                + "duplicate=%d rejected=%d%n",
            second.status(), second.received(), second.inserted(), second.updated(),
            second.duplicate(), second.rejected());

        long afterSecond = articles.findBySourceId(source.id).size();
        assertThat(afterSecond)
            .as("chạy lại không được tạo bản ghi trùng")
            .isEqualTo(afterFirst);
        assertThat(second.inserted()).as("lần 2 không chèn mới").isZero();

        // Phân bố chuyên mục và khu vực
        var rows = jdbc.queryForList("""
            SELECT category, region, COUNT(*) AS n
            FROM news_articles WHERE source_id = ?
            GROUP BY category, region ORDER BY n DESC
            """, source.id);
        System.out.println("LIVE phân bố:");
        for (var row : rows) {
            System.out.printf("  %s / %s : %s%n",
                row.get("category"), row.get("region"), row.get("n"));
        }

        Long daNang = jdbc.queryForObject("""
            SELECT COUNT(*) FROM news_articles
            WHERE source_id = ? AND region = 'DA_NANG'
            """, Long.class, source.id);
        System.out.printf("LIVE bài Đà Nẵng: %d%n", daNang);

        // Không có bài nào thiếu title hoặc canonical_url
        Long broken = jdbc.queryForObject("""
            SELECT COUNT(*) FROM news_articles
            WHERE source_id = ? AND (title IS NULL OR title = '' OR canonical_url IS NULL)
            """, Long.class, source.id);
        assertThat(broken).as("không có bài thiếu title/url").isZero();

        // publishedAt không bị gán bằng fetchedAt
        Long sameTimestamp = jdbc.queryForObject("""
            SELECT COUNT(*) FROM news_articles
            WHERE source_id = ? AND published_at IS NOT NULL
              AND ABS(TIMESTAMPDIFF(SECOND, published_at, fetched_at)) < 2
            """, Long.class, source.id);
        System.out.printf("LIVE bài có publishedAt ≈ fetchedAt: %d%n", sameTimestamp);
    }
}
