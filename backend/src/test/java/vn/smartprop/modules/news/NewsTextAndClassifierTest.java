package vn.smartprop.modules.news;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

/** Chuẩn hoá text/URL và phân loại bài viết. */
class NewsTextAndClassifierTest {

    // ---------- Text ----------

    @Test
    void stripsHtmlTagsAndEntities() {
        String cleaned = NewsText.clean(
            "<p>Giá <b>đất</b> tăng&nbsp;mạnh &amp; nguồn cung hạn chế</p>", 500);
        assertEquals("Giá đất tăng mạnh & nguồn cung hạn chế", cleaned);
    }

    @Test
    void removesScriptContent() {
        String cleaned = NewsText.clean(
            "Tiêu đề<script>alert('xss')</script> an toàn", 500);
        assertFalse(cleaned.contains("alert"));
        assertFalse(cleaned.contains("<"));
        assertTrue(cleaned.contains("Tiêu đề"));
    }

    @Test
    void truncatesToMaxLength() {
        String cleaned = NewsText.clean("a".repeat(100), 20);
        assertEquals(20, cleaned.length());
    }

    @Test
    void returnsNullForEmptyAfterCleaning() {
        assertNull(NewsText.clean("<p></p>", 500));
        assertNull(NewsText.clean("   ", 500));
        assertNull(NewsText.clean(null, 500));
    }

    @Test
    void keepsVietnameseDiacritics() {
        String cleaned = NewsText.clean("Đà Nẵng quy hoạch", 500);
        assertEquals("Đà Nẵng quy hoạch", cleaned);
    }

    @Test
    void foldForMatchRemovesDiacritics() {
        assertEquals("da nang quy hoach", NewsText.foldForMatch("Đà Nẵng quy hoạch"));
    }

    // ---------- Canonical URL ----------

    @Test
    void removesTrackingParameters() {
        String canonical = NewsText.canonicalUrl(
            "https://example.vn/bai-viet?utm_source=fb&utm_medium=social&id=42");
        assertEquals("https://example.vn/bai-viet?id=42", canonical);
    }

    @Test
    void removesFragmentAndTrailingSlash() {
        assertEquals("https://example.vn/bai-viet",
            NewsText.canonicalUrl("https://example.vn/bai-viet/#comments"));
    }

    @Test
    void normalizesWwwAndHostCase() {
        assertEquals("https://example.vn/x",
            NewsText.canonicalUrl("https://WWW.Example.VN/x"));
    }

    @Test
    void keepsIdentifyingQueryParameters() {
        String canonical = NewsText.canonicalUrl("https://example.vn/x?p=12345");
        assertEquals("https://example.vn/x?p=12345", canonical);
    }

    @Test
    void rejectsInvalidOrNonHttpUrl() {
        assertNull(NewsText.canonicalUrl("not a url"));
        assertNull(NewsText.canonicalUrl("ftp://example.vn/x"));
        assertNull(NewsText.canonicalUrl(null));
        assertNull(NewsText.canonicalUrl(""));
    }

    @Test
    void sameUrlDifferentTrackingYieldsSameHash() {
        String a = NewsText.canonicalUrl("https://example.vn/x?utm_source=a");
        String b = NewsText.canonicalUrl("https://example.vn/x?utm_source=b");
        assertEquals(NewsText.sha256(a), NewsText.sha256(b));
    }

    // ---------- Classifier ----------

    @Test
    void classifiesPlanningArticle() {
        var result = NewsClassifier.classify(
            "Điều chỉnh quy hoạch phân khu Hòa Vang",
            "Đồ án quy hoạch đô thị vừa được phê duyệt.",
            NewsSource.Category.MARKET, NewsSource.Region.UNKNOWN);
        assertTrue(result.relevant());
        assertEquals(NewsSource.Category.PLANNING, result.category());
    }

    @Test
    void classifiesLegalArticle() {
        var result = NewsClassifier.classify(
            "Luật Đất đai mới và giấy chứng nhận quyền sử dụng đất",
            "Nghị định hướng dẫn thủ tục pháp lý.",
            NewsSource.Category.MARKET, NewsSource.Region.UNKNOWN);
        assertTrue(result.relevant());
        assertEquals(NewsSource.Category.LEGAL, result.category());
    }

    @Test
    void classifiesMarketArticle() {
        var result = NewsClassifier.classify(
            "Giá nhà và nguồn cung bất động sản quý IV",
            "Thanh khoản thị trường bất động sản cải thiện.",
            NewsSource.Category.PLANNING, NewsSource.Region.UNKNOWN);
        assertTrue(result.relevant());
        assertEquals(NewsSource.Category.MARKET, result.category());
    }

    @Test
    void classifiesInfrastructureArticle() {
        var result = NewsClassifier.classify(
            "Cao tốc và tuyến đường ven biển mới",
            "Hạ tầng giao thông khu vực được nâng cấp.",
            NewsSource.Category.MARKET, NewsSource.Region.UNKNOWN);
        assertTrue(result.relevant());
        assertEquals(NewsSource.Category.INFRASTRUCTURE, result.category());
    }

    @Test
    void classifiesProjectsArticle() {
        var result = NewsClassifier.classify(
            "Khởi công dự án nhà ở tại khu đô thị mới",
            "Chủ đầu tư dự án bất động sản công bố tiến độ.",
            NewsSource.Category.MARKET, NewsSource.Region.UNKNOWN);
        assertTrue(result.relevant());
        assertEquals(NewsSource.Category.PROJECTS, result.category());
    }

    @Test
    void rejectsIrrelevantArticle() {
        var result = NewsClassifier.classify(
            "Đội tuyển bóng đá thắng trận",
            "Huấn luyện viên hài lòng với màn trình diễn.",
            NewsSource.Category.MARKET, NewsSource.Region.UNKNOWN);
        assertFalse(result.relevant(), "tin thể thao không được vào SmartProp");
    }

    @Test
    void detectsDaNangRegion() {
        var result = NewsClassifier.classify(
            "Bất động sản Đà Nẵng hút nhà đầu tư",
            "Giao dịch tại quận Hải Châu tăng.",
            NewsSource.Category.MARKET, NewsSource.Region.UNKNOWN);
        assertEquals(NewsSource.Region.DA_NANG, result.region());
        assertNotNull(result.locationTags());
    }

    @Test
    void detectsCentralRegion() {
        var result = NewsClassifier.classify(
            "Bất động sản Quảng Nam khởi sắc",
            "Thị trường nhà đất Hội An phục hồi.",
            NewsSource.Category.MARKET, NewsSource.Region.UNKNOWN);
        assertEquals(NewsSource.Region.CENTRAL, result.region());
    }

    @Test
    void fallsBackToSourceRegionWhenUnknown() {
        var result = NewsClassifier.classify(
            "Giá đất tăng trên cả nước",
            "Thị trường bất động sản ghi nhận biến động.",
            NewsSource.Category.MARKET, NewsSource.Region.VIETNAM);
        assertEquals(NewsSource.Region.VIETNAM, result.region());
    }

    @Test
    void doesNotClassifyOnGenericWordAlone() {
        // "cầu" và "đường" xuất hiện nhưng không phải hạ tầng giao thông.
        var result = NewsClassifier.classify(
            "Cầu thủ chạy trên đường pitch", "Trận đấu tối qua rất hấp dẫn.",
            NewsSource.Category.MARKET, NewsSource.Region.UNKNOWN);
        assertFalse(result.relevant(), "từ đơn chung chung không đủ để phân loại");
    }

    @Test
    void parsesVietnameseCategoryLabels() {
        assertEquals(NewsSource.Category.MARKET,
            NewsClassifier.parseCategory("Thị trường BĐS"));
        assertEquals(NewsSource.Category.PLANNING,
            NewsClassifier.parseCategory("Quy hoạch & hạ tầng"));
        assertEquals(NewsSource.Category.LEGAL,
            NewsClassifier.parseCategory("Chính sách & pháp lý"));
        assertEquals(NewsSource.Category.PROJECTS,
            NewsClassifier.parseCategory("Dự án"));
        assertNull(NewsClassifier.parseCategory("Tất cả"));
        assertNull(NewsClassifier.parseCategory(null));
    }

    @Test
    void categoryLabelsMatchFrontendContract() {
        assertEquals("Thị trường BĐS", NewsClassifier.categoryLabel(NewsSource.Category.MARKET));
        assertEquals("Quy hoạch & hạ tầng", NewsClassifier.categoryLabel(NewsSource.Category.PLANNING));
        assertEquals("Chính sách & pháp lý", NewsClassifier.categoryLabel(NewsSource.Category.LEGAL));
        assertEquals("Dự án", NewsClassifier.categoryLabel(NewsSource.Category.PROJECTS));
    }
}
