package vn.smartprop.modules.news;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

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
import vn.smartprop.common.ApiException;

/**
 * Source rights lifecycle và thực thi quyền summary.
 *
 * <p>Kiểm chứng: không reapprove cùng request đổi identity, không sai attribution
 * lịch sử, summary bị cấm không xuất hiện trong public API kể cả khi đã lưu.
 */
@SpringBootTest
@EnabledIfEnvironmentVariable(named = "DB_URL", matches = ".+")
class NewsSourceRightsIT {

    @Autowired NewsAdminService admin;
    @Autowired NewsService read;
    @Autowired NewsSourceRepository sources;
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

    private String createSource(String code) {
        var created = admin.create(new NewsDtos.CreateSource(
            code, "Nguồn " + code, "NXB Gốc", "https://example.vn",
            "https://example.vn/" + code + ".rss",
            NewsSource.Category.MARKET, NewsSource.Region.DA_NANG,
            null, null, 30));
        createdSources.add(created.id());
        return created.id();
    }

    /** Duyệt quyền VÀ bật nguồn — hai bước riêng theo đúng policy. */
    private void approveAndEnable(String id, String reference) {
        admin.update(id, new NewsDtos.UpdateSource(
            null, null, null, null, null, null,
            NewsSource.RightsStatus.APPROVED, reference, null,
            null, null, null, null));
        admin.update(id, new NewsDtos.UpdateSource(
            null, null, null, null, null, null, null, null, null,
            null, null, true, null));
    }

    private String article(String sourceId, String title, String summary) {
        String id = UUID.randomUUID().toString();
        jdbc.update("""
            INSERT INTO news_articles (id, source_id, canonical_url, canonical_url_hash, title,
              summary, category, region, published_at, fetched_at, first_seen_at, last_seen_at,
              publication_status, featured)
            VALUES (?, ?, ?, ?, ?, ?, 'MARKET', 'DA_NANG', UTC_TIMESTAMP(6),
              UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 'VISIBLE', 0)
            """, id, sourceId, "https://example.vn/" + id,
            NewsText.sha256("https://example.vn/" + id), title, summary);
        return id;
    }

    // ---------- Defaults ----------

    @Test
    void newSourceDefaultsToPendingDisabledNoSummaryNoImages() {
        String id = createSource("it-rights-new");
        NewsSource source = sources.findById(id).orElseThrow();

        assertThat(source.rightsReviewStatus).isEqualTo(NewsSource.RightsStatus.PENDING_REVIEW);
        assertThat(source.enabled).as("nguồn mới phải tắt").isFalse();
        assertThat(source.allowSummary).as("summary mặc định không cho phép").isFalse();
        assertThat(source.allowImages).as("ảnh mặc định không cho phép").isFalse();
    }

    @Test
    void cannotApproveWithoutReference() {
        String id = createSource("it-rights-noref");
        assertThatThrownBy(() -> admin.update(id, new NewsDtos.UpdateSource(
            null, null, null, null, null, null,
            NewsSource.RightsStatus.APPROVED, null, null, null, null, null, null)))
            .isInstanceOf(ApiException.class);
    }

    // ---------- Identity change resets approval ----------

    @Test
    void changingFeedUrlResetsApprovalAndDisables() {
        String id = createSource("it-rights-feed");
        approveAndEnable(id, "IT-REF-1");
        admin.update(id, new NewsDtos.UpdateSource(
            null, null, null, null, null, null, null, null, null, null, null, true, null));
        assertThat(sources.findById(id).orElseThrow().enabled).isTrue();

        // Đổi feed URL.
        admin.update(id, new NewsDtos.UpdateSource(
            null, null, null, "https://example.vn/changed.rss", null, null,
            null, null, null, null, null, null, null));

        NewsSource after = sources.findById(id).orElseThrow();
        assertThat(after.rightsReviewStatus)
            .as("đổi feed URL phải về PENDING_REVIEW").isEqualTo(NewsSource.RightsStatus.PENDING_REVIEW);
        assertThat(after.enabled).as("đổi feed URL phải tắt nguồn").isFalse();
        assertThat(after.rightsCheckedAt).as("phải xoá rightsCheckedAt cũ").isNull();
    }

    @Test
    void changingPublisherResetsApproval() {
        String id = createSource("it-rights-pub");
        approveAndEnable(id, "IT-REF-2");

        admin.update(id, new NewsDtos.UpdateSource(
            null, "NXB Khác", null, null, null, null, null, null, null, null, null, null, null));

        NewsSource after = sources.findById(id).orElseThrow();
        assertThat(after.rightsReviewStatus).isEqualTo(NewsSource.RightsStatus.PENDING_REVIEW);
        assertThat(after.enabled).isFalse();
    }

    @Test
    void cannotReapproveInSameRequestAsIdentityChange() {
        String id = createSource("it-rights-same");
        approveAndEnable(id, "IT-REF-3");

        // Đổi feedUrl VÀ gửi APPROVED trong cùng request → phải bị từ chối.
        assertThatThrownBy(() -> admin.update(id, new NewsDtos.UpdateSource(
            null, null, null, "https://example.vn/same-req.rss", null, null,
            NewsSource.RightsStatus.APPROVED, "IT-REF-4", null, null, null, null, null)))
            .as("không được approve cùng request đổi identity")
            .isInstanceOf(ApiException.class);

        // Nguồn vẫn ở trạng thái an toàn.
        NewsSource after = sources.findById(id).orElseThrow();
        assertThat(after.rightsReviewStatus).isEqualTo(NewsSource.RightsStatus.APPROVED);
        assertThat(after.feedUrl).as("feed URL không được đổi khi request bị từ chối")
            .isEqualTo("https://example.vn/it-rights-same.rss");
    }

    @Test
    void cannotClearReferenceWhileApproved() {
        String id = createSource("it-rights-clear");
        approveAndEnable(id, "IT-REF-5");

        assertThatThrownBy(() -> admin.update(id, new NewsDtos.UpdateSource(
            null, null, null, null, null, null, null, "   ", null, null, null, null, null)))
            .isInstanceOf(ApiException.class);
    }

    @Test
    void cannotEnableUnapprovedSource() {
        String id = createSource("it-rights-enable");
        assertThatThrownBy(() -> admin.update(id, new NewsDtos.UpdateSource(
            null, null, null, null, null, null, null, null, null, null, null, true, null)))
            .isInstanceOf(ApiException.class);
    }

    // ---------- Historical attribution ----------

    @Test
    void existingArticlesKeepOriginalPublisherAfterSourceRename() {
        String id = createSource("it-rights-hist");
        approveAndEnable(id, "IT-REF-6");
        String articleId = article(id, "Giá đất Đà Nẵng tăng", "Tóm tắt gốc");

        // Đổi tên hiển thị (không phải identity) — article vẫn thuộc nguồn cũ.
        admin.update(id, new NewsDtos.UpdateSource(
            "Tên mới", null, null, null, null, null, null, null, null, null, null, null, null));

        String sourceId = jdbc.queryForObject(
            "SELECT source_id FROM news_articles WHERE id = ?", String.class, articleId);
        assertThat(sourceId).as("article phải giữ nguyên source_id").isEqualTo(id);
    }

    // ---------- Summary permission enforcement ----------

    @Test
    void summaryNotReturnedWhenSourceDisallowsIt() {
        String id = createSource("it-rights-sum");
        approveAndEnable(id, "IT-REF-7");
        admin.update(id, new NewsDtos.UpdateSource(
            null, null, null, null, null, null, null, null, null, false, null, true, null));
        article(id, "Giá đất kiểm tra summary", "Tóm tắt bí mật");

        var page = read.list(null, "kiểm tra summary", "newest", 0, 10);
        assertThat(page.items()).isNotEmpty();
        assertThat(page.items().get(0).summary())
            .as("summary phải null khi nguồn không cho phép").isNull();
    }

    @Test
    void summaryReturnedWhenSourceAllowsIt() {
        String id = createSource("it-rights-sum-ok");
        approveAndEnable(id, "IT-REF-8");
        admin.update(id, new NewsDtos.UpdateSource(
            null, null, null, null, null, null, null, null, null, true, null, true, null));
        article(id, "Giá đất cho phép summary", "Tóm tắt công khai");

        var page = read.list(null, "cho phép summary", "newest", 0, 10);
        assertThat(page.items()).isNotEmpty();
        assertThat(page.items().get(0).summary()).isEqualTo("Tóm tắt công khai");
    }

    @Test
    void searchDoesNotMatchForbiddenSummary() {
        String id = createSource("it-rights-search");
        approveAndEnable(id, "IT-REF-9");
        admin.update(id, new NewsDtos.UpdateSource(
            null, null, null, null, null, null, null, null, null, false, null, true, null));
        // Title không chứa "bí mật", chỉ summary chứa.
        article(id, "Giá đất bình thường", "từ khoá bí mật trong summary");

        var page = read.list(null, "bí mật", "newest", 0, 10);
        assertThat(page.items())
            .as("search không được khớp summary bị cấm").isEmpty();
    }

    @Test
    void featuredDoesNotReturnForbiddenSummary() {
        String id = createSource("it-rights-feat");
        approveAndEnable(id, "IT-REF-10");
        admin.update(id, new NewsDtos.UpdateSource(
            null, null, null, null, null, null, null, null, null, false, null, true, null));
        String articleId = article(id, "Giá đất nổi bật", "Tóm tắt bị cấm");
        jdbc.update("UPDATE news_articles SET featured = 1 WHERE id = ?", articleId);

        var featured = read.featured();
        assertThat(featured.items()).isNotEmpty();
        assertThat(featured.items().get(0).summary())
            .as("featured cũng phải tôn trọng quyền summary").isNull();
    }

    // ---------- Revoke ----------

    @Test
    void revokingRightsHidesArticlesFromPublic() {
        String id = createSource("it-rights-revoke");
        approveAndEnable(id, "IT-REF-11");
        article(id, "Giá đất trước thu hồi", "Tóm tắt");

        assertThat(read.list(null, "trước thu hồi", "newest", 0, 10).items()).isNotEmpty();

        admin.update(id, new NewsDtos.UpdateSource(
            null, null, null, null, null, null,
            NewsSource.RightsStatus.REJECTED, null, null, null, null, null, null));

        assertThat(read.list(null, "trước thu hồi", "newest", 0, 10).items())
            .as("thu hồi quyền phải ẩn bài khỏi public").isEmpty();
    }

    @Test
    void disabledSourceHidesArticlesFromPublic() {
        String id = createSource("it-rights-disable");
        approveAndEnable(id, "IT-REF-12");
        admin.update(id, new NewsDtos.UpdateSource(
            null, null, null, null, null, null, null, null, null, null, null, true, null));
        article(id, "Giá đất trước khi tắt", "Tóm tắt");

        assertThat(read.list(null, "trước khi tắt", "newest", 0, 10).items()).isNotEmpty();

        admin.update(id, new NewsDtos.UpdateSource(
            null, null, null, null, null, null, null, null, null, null, null, false, null));

        assertThat(read.list(null, "trước khi tắt", "newest", 0, 10).items())
            .as("tắt nguồn phải ẩn bài khỏi public").isEmpty();
    }
}
