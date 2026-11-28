package vn.smartprop.modules.news;

import static org.junit.jupiter.api.Assertions.*;

import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * HTTP status handling, host allowlist và category grouping.
 *
 * <p>Kiểm tra logic thuần (không mạng). Fetcher integration test dùng HTTP server
 * thật nằm ở {@link NewsFeedFetcherIT}.
 */
class NewsFetchPolicyTest {

    // ---------- Host allowlist ----------

    @Test
    void allowlistMatchesExactHost() {
        assertTrue(NewsUrlSafety.hostAllowed("vnexpress.net", List.of("vnexpress.net")));
    }

    @Test
    void allowlistMatchesSubdomain() {
        assertTrue(NewsUrlSafety.hostAllowed("rss.vnexpress.net", List.of("vnexpress.net")));
    }

    @Test
    void allowlistRejectsLookalikeHost() {
        // "evil-vnexpress.net" KHÔNG được khớp với "vnexpress.net".
        assertFalse(NewsUrlSafety.hostAllowed("evil-vnexpress.net", List.of("vnexpress.net")));
        assertFalse(NewsUrlSafety.hostAllowed("vnexpress.net.evil.com", List.of("vnexpress.net")));
    }

    @Test
    void allowlistRejectsEmptyList() {
        assertFalse(NewsUrlSafety.hostAllowed("vnexpress.net", List.of()));
        assertFalse(NewsUrlSafety.hostAllowed("vnexpress.net", null));
    }

    @Test
    void allowlistHandlesLeadingDotAndCase() {
        assertTrue(NewsUrlSafety.hostAllowed("vnexpress.net", List.of(".VnExpress.NET")));
    }

    @Test
    void checkWithAllowlistRejectsHostOutsideList() {
        NewsUrlSafety.Result result = NewsUrlSafety.check(
            "https://evil.example.com/feed", false, false, true, List.of("vnexpress.net"));
        assertFalse(result.allowed());
        assertTrue(result.reason().contains("allowlist"));
    }

    @Test
    void checkWithAllowlistAcceptsListedHost() {
        NewsUrlSafety.Result result = NewsUrlSafety.check(
            "https://vnexpress.net/rss/x.rss", false, false, true, List.of("vnexpress.net"));
        assertTrue(result.allowed(), result.reason());
    }

    @Test
    void checkWithoutEnforcementIgnoresAllowlist() {
        NewsUrlSafety.Result result = NewsUrlSafety.check(
            "https://other.example.com/feed", false, false, false, List.of("vnexpress.net"));
        assertTrue(result.allowed(), result.reason());
    }

    @Test
    void allowlistStillRejectsPrivateIp() {
        // Allowlist không được vô hiệu hoá kiểm tra IP.
        NewsUrlSafety.Result result = NewsUrlSafety.check(
            "https://127.0.0.1/feed", false, false, true, List.of("127.0.0.1"));
        assertFalse(result.allowed());
    }

    // ---------- Retry-After parsing ----------

    @Test
    void parsesRetryAfterSeconds() {
        var parsed = NewsFeedFetcher.parseRetryAfter("120");
        assertNotNull(parsed);
        assertTrue(parsed.isAfter(java.time.Instant.now()));
    }

    @Test
    void parsesRetryAfterHttpDate() {
        var parsed = NewsFeedFetcher.parseRetryAfter("Tue, 24 Nov 2026 20:00:00 GMT");
        assertNotNull(parsed);
    }

    @Test
    void rejectsMalformedRetryAfter() {
        assertNull(NewsFeedFetcher.parseRetryAfter("not-a-date"));
        assertNull(NewsFeedFetcher.parseRetryAfter(""));
        assertNull(NewsFeedFetcher.parseRetryAfter(null));
    }

    // ---------- Category grouping ----------

    @Test
    void planningGroupIncludesInfrastructure() {
        List<NewsSource.Category> group = NewsClassifier.parseCategoryGroup("Quy hoạch & hạ tầng");
        assertNotNull(group);
        assertTrue(group.contains(NewsSource.Category.PLANNING));
        assertTrue(group.contains(NewsSource.Category.INFRASTRUCTURE),
            "hạ tầng phải nằm trong nhóm quy hoạch, nếu không sẽ mất bài");
    }

    @Test
    void marketGroupIncludesResidentialAndCommercial() {
        List<NewsSource.Category> group = NewsClassifier.parseCategoryGroup("Thị trường BĐS");
        assertNotNull(group);
        assertTrue(group.contains(NewsSource.Category.MARKET));
        assertTrue(group.contains(NewsSource.Category.RESIDENTIAL));
        assertTrue(group.contains(NewsSource.Category.COMMERCIAL));
    }

    @Test
    void legalGroupIsSingleCategory() {
        List<NewsSource.Category> group = NewsClassifier.parseCategoryGroup("Chính sách & pháp lý");
        assertEquals(List.of(NewsSource.Category.LEGAL), group);
    }

    @Test
    void projectsGroupIsSingleCategory() {
        assertEquals(List.of(NewsSource.Category.PROJECTS),
            NewsClassifier.parseCategoryGroup("Dự án"));
    }

    @Test
    void daNangIsRegionNotCategory() {
        assertNull(NewsClassifier.parseCategoryGroup("Tin tức Đà Nẵng"),
            "Đà Nẵng là bộ lọc khu vực, không phải chuyên mục");
    }

    @Test
    void allMeansNoCategoryFilter() {
        assertNull(NewsClassifier.parseCategoryGroup("Tất cả"));
        assertNull(NewsClassifier.parseCategoryGroup(null));
        assertNull(NewsClassifier.parseCategoryGroup(""));
    }

    // ---------- Source status semantics ----------

    @Test
    void neverSyncedSourceIsNeverSynced() {
        NewsSource source = new NewsSource();
        source.lastSuccessAt = null;
        assertEquals("NEVER_SYNCED", NewsService.sourceStatus(source));
    }

    @Test
    void freshSourceIsAvailable() {
        NewsSource source = new NewsSource();
        source.lastSuccessAt = java.time.Instant.now().minusSeconds(60);
        source.lastAttemptAt = source.lastSuccessAt;
        assertEquals("AVAILABLE", NewsService.sourceStatus(source));
    }

    @Test
    void oldSourceIsStale() {
        NewsSource source = new NewsSource();
        source.lastSuccessAt = java.time.Instant.now().minusSeconds(4 * 60 * 60);
        source.lastAttemptAt = source.lastSuccessAt;
        assertEquals("STALE", NewsService.sourceStatus(source));
    }

    @Test
    void failedAttemptAfterSuccessIsFailed() {
        NewsSource source = new NewsSource();
        source.lastSuccessAt = java.time.Instant.now().minusSeconds(60);
        source.lastAttemptAt = java.time.Instant.now();
        source.lastError = "HTTP_500: lỗi";
        assertEquals("FAILED", NewsService.sourceStatus(source));
    }

    // ---------- Lease semantics ----------

    @Test
    void leaseActiveOnlyBeforeExpiry() {
        NewsSource source = new NewsSource();
        source.syncLeaseToken = "token";
        source.syncLeaseUntil = java.time.Instant.now().plusSeconds(60);
        assertTrue(source.leaseActive(java.time.Instant.now()));

        source.syncLeaseUntil = java.time.Instant.now().minusSeconds(1);
        assertFalse(source.leaseActive(java.time.Instant.now()));
    }

    @Test
    void noTokenMeansNoLease() {
        NewsSource source = new NewsSource();
        source.syncLeaseUntil = java.time.Instant.now().plusSeconds(60);
        assertFalse(source.leaseActive(java.time.Instant.now()));
    }

    @Test
    void dueWhenNextFetchIsNull() {
        NewsSource source = new NewsSource();
        assertTrue(source.due(java.time.Instant.now()));
    }

    @Test
    void notDueDuringCooldown() {
        NewsSource source = new NewsSource();
        source.nextFetchAt = java.time.Instant.now().plusSeconds(600);
        assertFalse(source.due(java.time.Instant.now()));
    }

    // ---------- Duplicate classification ----------

    @Test
    void onlyDuplicateEntryIsTreatedAsDuplicate() {
        var duplicate = new org.springframework.dao.DataIntegrityViolationException(
            "could not execute statement",
            new java.sql.SQLIntegrityConstraintViolationException(
                "Duplicate entry 'x' for key 'uq_news_articles_source_url'"));
        assertTrue(NewsIngestionPersistenceService.isDuplicateKey(duplicate));

        var foreignKey = new org.springframework.dao.DataIntegrityViolationException(
            "could not execute statement",
            new java.sql.SQLIntegrityConstraintViolationException(
                "Cannot add or update a child row: a foreign key constraint fails"));
        assertFalse(NewsIngestionPersistenceService.isDuplicateKey(foreignKey),
            "FK violation không phải duplicate");

        var truncation = new org.springframework.dao.DataIntegrityViolationException(
            "could not execute statement",
            new java.sql.SQLException("Data truncation: Data too long for column 'title'"));
        assertFalse(NewsIngestionPersistenceService.isDuplicateKey(truncation),
            "truncation không phải duplicate");
    }
}
