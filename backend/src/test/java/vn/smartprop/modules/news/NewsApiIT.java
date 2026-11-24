package vn.smartprop.modules.news;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.RequestPostProcessor;
import vn.smartprop.modules.user.User;
import vn.smartprop.modules.user.UserRepository;

/**
 * HTTP contract test cho News — Spring Security thật, controller thật, MySQL thật.
 *
 * <p>Chạy trên DB cô lập. Bỏ qua khi thiếu {@code DB_URL}.
 *
 * <p>Kiểm chứng: contract khớp Frontend PR #37, phân quyền, không lộ metadata nội bộ,
 * nguồn chưa duyệt không hiển thị, bài HIDDEN không lộ.
 */
@SpringBootTest
@AutoConfigureMockMvc
@EnabledIfEnvironmentVariable(named = "DB_URL", matches = ".+")
class NewsApiIT {

    @Autowired MockMvc mvc;
    @Autowired UserRepository users;
    @Autowired JdbcTemplate jdbc;

    private Long adminId;
    private Long brokerId;
    private final List<String> createdSources = new java.util.ArrayList<>();
    private final List<String> createdArticles = new java.util.ArrayList<>();

    @BeforeEach
    void setUp() {
        List<User> staff = users.findAll().stream()
            .filter(u -> u.deletedAt == null && u.status == User.Status.ACTIVE)
            .toList();
        adminId = staff.stream().filter(u -> u.role == User.Role.ADMIN)
            .map(u -> u.id).findFirst()
            .orElseThrow(() -> new IllegalStateException("cần ADMIN"));
        brokerId = staff.stream()
            .filter(u -> u.role == User.Role.BROKER || u.role == User.Role.ADMIN)
            .map(u -> u.id).findFirst()
            .orElseThrow(() -> new IllegalStateException("cần BROKER"));
    }

    @AfterEach
    void cleanUp() {
        for (String id : createdArticles) {
            jdbc.update("DELETE FROM news_articles WHERE id = ?", id);
        }
        for (String id : createdSources) {
            jdbc.update("DELETE FROM news_ingestion_runs WHERE source_id = ?", id);
            jdbc.update("DELETE FROM news_articles WHERE source_id = ?", id);
            jdbc.update("DELETE FROM news_sources WHERE id = ?", id);
        }
        createdArticles.clear();
        createdSources.clear();
    }

    private RequestPostProcessor asAdmin() {
        return jwt().jwt(j -> j.subject(String.valueOf(adminId)))
            .authorities(new SimpleGrantedAuthority("ROLE_ADMIN"));
    }

    private RequestPostProcessor asBroker() {
        return jwt().jwt(j -> j.subject(String.valueOf(brokerId)))
            .authorities(new SimpleGrantedAuthority("ROLE_BROKER"));
    }

    /** Tạo nguồn APPROVED + enabled trực tiếp trong DB (bỏ qua API để test đọc). */
    private String approvedSource(String code) {
        String id = UUID.randomUUID().toString();
        jdbc.update("""
            INSERT INTO news_sources (id, source_code, name, publisher, website_url, feed_url,
              default_category, default_region, rights_review_status, rights_reference,
              enabled, fetch_interval_minutes, last_success_at)
            VALUES (?, ?, ?, 'NXB Test', 'https://example.vn', ?, 'MARKET', 'DA_NANG',
              'APPROVED', 'IT-REF', 1, 30, UTC_TIMESTAMP(6))
            """, id, code, "Nguồn " + code, "https://example.vn/" + code + ".rss");
        createdSources.add(id);
        return id;
    }

    private String article(String sourceId, String title, String category, String region,
                           String status, boolean featured, Instant publishedAt) {
        String id = UUID.randomUUID().toString();
        jdbc.update("""
            INSERT INTO news_articles (id, source_id, canonical_url, canonical_url_hash, title,
              summary, category, region, published_at, fetched_at, first_seen_at, last_seen_at,
              publication_status, featured)
            VALUES (?, ?, ?, ?, ?, 'Tóm tắt thử', ?, ?, ?, UTC_TIMESTAMP(6),
              UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), ?, ?)
            """, id, sourceId, "https://example.vn/" + id,
            NewsText.sha256("https://example.vn/" + id), title, category, region,
            publishedAt == null ? null : java.sql.Timestamp.from(publishedAt),
            status, featured);
        createdArticles.add(id);
        return id;
    }

    // ---------- Public API ----------

    @Test
    void anonymousCanListNews() throws Exception {
        String source = approvedSource("it-list");
        article(source, "Giá đất Đà Nẵng tăng", "MARKET", "DA_NANG", "VISIBLE", false,
            Instant.now());

        mvc.perform(get("/api/v1/news"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.items").isArray())
            .andExpect(jsonPath("$.page").value(0))
            .andExpect(jsonPath("$.size").isNumber())
            .andExpect(jsonPath("$.totalElements").isNumber())
            .andExpect(jsonPath("$.totalPages").isNumber())
            .andExpect(jsonPath("$.sources").isArray());
    }

    @Test
    void articleCarriesFrontendContractFields() throws Exception {
        String source = approvedSource("it-fields");
        article(source, "Quy hoạch Hòa Vang", "PLANNING", "DA_NANG", "VISIBLE", false,
            Instant.now());

        String body = mvc.perform(get("/api/v1/news").param("q", "Hòa Vang"))
            .andExpect(status().isOk())
            .andReturn().getResponse().getContentAsString();

        // Các field Frontend PR #37 đọc trực tiếp.
        assertThat(body).contains("\"title\"");
        assertThat(body).contains("\"summary\"");
        assertThat(body).contains("\"category\"");
        assertThat(body).contains("\"articleUrl\"");
        assertThat(body).contains("\"sourceName\"");
        assertThat(body).contains("\"sourceUrl\"");
        assertThat(body).contains("\"publishedAt\"");
        assertThat(body).contains("\"fetchedAt\"");
        assertThat(body).contains("\"locationTags\"");
        // Nhãn tiếng Việt đúng contract.
        assertThat(body).contains("Quy hoạch & hạ tầng");
    }

    @Test
    void hiddenArticleIsNotPublic() throws Exception {
        String source = approvedSource("it-hidden");
        article(source, "Bài bị ẩn về đất nền", "MARKET", "DA_NANG", "HIDDEN", false,
            Instant.now());

        String body = mvc.perform(get("/api/v1/news").param("q", "bị ẩn"))
            .andExpect(status().isOk())
            .andReturn().getResponse().getContentAsString();
        assertThat(body).doesNotContain("Bài bị ẩn");
    }

    @Test
    void articleFromUnapprovedSourceIsNotPublic() throws Exception {
        String id = UUID.randomUUID().toString();
        jdbc.update("""
            INSERT INTO news_sources (id, source_code, name, publisher, website_url, feed_url,
              rights_review_status, enabled)
            VALUES (?, 'it-pending', 'Nguồn chờ duyệt', 'NXB', 'https://p.vn',
              'https://p.vn/rss', 'PENDING_REVIEW', 1)
            """, id);
        createdSources.add(id);
        article(id, "Bài từ nguồn chưa duyệt quyền", "MARKET", "DA_NANG", "VISIBLE", false,
            Instant.now());

        String body = mvc.perform(get("/api/v1/news").param("q", "chưa duyệt"))
            .andExpect(status().isOk())
            .andReturn().getResponse().getContentAsString();
        assertThat(body).doesNotContain("chưa duyệt quyền");
    }

    @Test
    void disabledSourceIsNotPublic() throws Exception {
        String id = UUID.randomUUID().toString();
        jdbc.update("""
            INSERT INTO news_sources (id, source_code, name, publisher, website_url, feed_url,
              rights_review_status, enabled)
            VALUES (?, 'it-disabled', 'Nguồn tắt', 'NXB', 'https://d.vn',
              'https://d.vn/rss', 'APPROVED', 0)
            """, id);
        createdSources.add(id);
        article(id, "Bài từ nguồn đang tắt", "MARKET", "DA_NANG", "VISIBLE", false,
            Instant.now());

        String body = mvc.perform(get("/api/v1/news").param("q", "đang tắt"))
            .andExpect(status().isOk())
            .andReturn().getResponse().getContentAsString();
        assertThat(body).doesNotContain("đang tắt");
    }

    @Test
    void featuredEndpointWorks() throws Exception {
        String source = approvedSource("it-featured");
        article(source, "Tin nổi bật Đà Nẵng", "MARKET", "DA_NANG", "VISIBLE", true,
            Instant.now());

        mvc.perform(get("/api/v1/news/featured"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.items").isArray());
    }

    @Test
    void sourcesEndpointReturnsPublicMetadataOnly() throws Exception {
        approvedSource("it-sources");

        String body = mvc.perform(get("/api/v1/news/sources"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.sources").isArray())
            .andReturn().getResponse().getContentAsString();

        assertThat(body).contains("\"name\"");
        assertThat(body).contains("\"count\"");
        assertThat(body).contains("\"lastSuccessAt\"");
        assertThat(body).contains("\"status\"");
        // Không lộ metadata nội bộ.
        assertThat(body).doesNotContain("rightsReference");
        assertThat(body).doesNotContain("lastError");
        assertThat(body).doesNotContain("httpEtag");
    }

    @Test
    void categoryFilterWorks() throws Exception {
        String source = approvedSource("it-cat");
        article(source, "Quy hoạch phân khu mới", "PLANNING", "DA_NANG", "VISIBLE", false,
            Instant.now());

        String planning = mvc.perform(get("/api/v1/news")
                .param("category", "Quy hoạch & hạ tầng"))
            .andExpect(status().isOk())
            .andReturn().getResponse().getContentAsString();
        assertThat(planning).contains("Quy hoạch phân khu mới");

        String legal = mvc.perform(get("/api/v1/news")
                .param("category", "Chính sách & pháp lý"))
            .andExpect(status().isOk())
            .andReturn().getResponse().getContentAsString();
        assertThat(legal).doesNotContain("Quy hoạch phân khu mới");
    }

    @Test
    void oversizedPageSizeIsClamped() throws Exception {
        mvc.perform(get("/api/v1/news").param("size", "9999"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.size").value(org.hamcrest.Matchers.lessThanOrEqualTo(50)));
    }

    @Test
    void emptyDatasetReturnsEmptyPageNotError() throws Exception {
        mvc.perform(get("/api/v1/news").param("q", "không có bài nào khớp xyz123"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.items").isEmpty())
            .andExpect(jsonPath("$.totalElements").value(0));
    }

    // ---------- Admin security ----------

    @Test
    void anonymousCannotReadAdminSources() throws Exception {
        mvc.perform(get("/api/v1/admin/news/sources"))
            .andExpect(status().isUnauthorized());
    }

    @Test
    void brokerCannotReadAdminSources() throws Exception {
        mvc.perform(get("/api/v1/admin/news/sources").with(asBroker()))
            .andExpect(status().isForbidden());
    }

    @Test
    void adminCanReadAdminSources() throws Exception {
        mvc.perform(get("/api/v1/admin/news/sources").with(asAdmin()))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }

    @Test
    void adminStatsWorks() throws Exception {
        mvc.perform(get("/api/v1/admin/news/stats").with(asAdmin()))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.totalSources").isNumber())
            .andExpect(jsonPath("$.approvedSources").isNumber())
            .andExpect(jsonPath("$.visibleArticles").isNumber());
    }

    @Test
    void brokerCannotSyncSource() throws Exception {
        String source = approvedSource("it-sync-broker");
        mvc.perform(post("/api/v1/admin/news/sources/" + source + "/sync").with(asBroker()))
            .andExpect(status().isForbidden());
    }

    // ---------- Admin source lifecycle ----------

    @Test
    void newSourceIsAlwaysPendingAndDisabled() throws Exception {
        String code = "it-new-" + UUID.randomUUID().toString().substring(0, 8);
        String body = mvc.perform(post("/api/v1/admin/news/sources").with(asAdmin())
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"sourceCode":"%s","name":"Nguồn mới","publisher":"NXB",
                     "websiteUrl":"https://new.vn","feedUrl":"https://new.vn/%s.rss"}
                    """.formatted(code, code)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.rightsReviewStatus").value("PENDING_REVIEW"))
            .andExpect(jsonPath("$.enabled").value(false))
            .andReturn().getResponse().getContentAsString();

        String id = com.jayway.jsonpath.JsonPath.read(body, "$.id");
        createdSources.add(id);
    }

    @Test
    void cannotApproveWithoutRightsReference() throws Exception {
        String source = approvedSource("it-approve");
        // Đặt lại PENDING để test chuyển sang APPROVED không có căn cứ.
        jdbc.update("""
            UPDATE news_sources SET rights_review_status='PENDING_REVIEW',
              rights_reference=NULL, enabled=0 WHERE id=?
            """, source);

        mvc.perform(patch("/api/v1/admin/news/sources/" + source).with(asAdmin())
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"rightsReviewStatus":"APPROVED"}
                    """))
            .andExpect(status().isBadRequest());
    }

    @Test
    void cannotEnableUnapprovedSource() throws Exception {
        String id = UUID.randomUUID().toString();
        jdbc.update("""
            INSERT INTO news_sources (id, source_code, name, publisher, website_url, feed_url,
              rights_review_status, enabled)
            VALUES (?, 'it-enable', 'Chờ duyệt', 'NXB', 'https://e.vn',
              'https://e.vn/rss', 'PENDING_REVIEW', 0)
            """, id);
        createdSources.add(id);

        mvc.perform(patch("/api/v1/admin/news/sources/" + id).with(asAdmin())
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"enabled":true}
                    """))
            .andExpect(status().isBadRequest());
    }

    @Test
    void rejectsPrivateIpFeedUrl() throws Exception {
        String code = "it-ssrf-" + UUID.randomUUID().toString().substring(0, 8);
        mvc.perform(post("/api/v1/admin/news/sources").with(asAdmin())
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"sourceCode":"%s","name":"SSRF","publisher":"X",
                     "websiteUrl":"https://x.vn","feedUrl":"https://127.0.0.1/rss"}
                    """.formatted(code)))
            .andExpect(status().isBadRequest());
    }

    @Test
    void adminCanHideArticle() throws Exception {
        String source = approvedSource("it-hide");
        String articleId = article(source, "Bài sẽ bị ẩn", "MARKET", "DA_NANG", "VISIBLE",
            false, Instant.now());

        mvc.perform(patch("/api/v1/admin/news/articles/" + articleId + "/visibility")
                .with(asAdmin())
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"publicationStatus":"HIDDEN"}
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.publicationStatus").value("HIDDEN"));

        String body = mvc.perform(get("/api/v1/news").param("q", "sẽ bị ẩn"))
            .andReturn().getResponse().getContentAsString();
        assertThat(body).doesNotContain("Bài sẽ bị ẩn");
    }

    @Test
    void adminCanFeatureArticle() throws Exception {
        String source = approvedSource("it-feat");
        String articleId = article(source, "Bài nổi bật", "MARKET", "DA_NANG", "VISIBLE",
            false, Instant.now());

        mvc.perform(patch("/api/v1/admin/news/articles/" + articleId + "/featured")
                .with(asAdmin())
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"featured":true}
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.featured").value(true));
    }

    @Test
    void syncRejectsUnapprovedSource() throws Exception {
        String id = UUID.randomUUID().toString();
        jdbc.update("""
            INSERT INTO news_sources (id, source_code, name, publisher, website_url, feed_url,
              rights_review_status, enabled)
            VALUES (?, 'it-sync-pending', 'Chờ duyệt', 'NXB', 'https://s.vn',
              'https://s.vn/rss', 'PENDING_REVIEW', 1)
            """, id);
        createdSources.add(id);

        mvc.perform(post("/api/v1/admin/news/sources/" + id + "/sync").with(asAdmin()))
            .andExpect(status().isBadRequest());
    }
}
