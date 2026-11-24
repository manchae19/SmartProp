package vn.smartprop.modules.news;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * Cấu hình News.
 *
 * <p>Mặc định an toàn: ingestion TẮT. Không nguồn nào được thu thập cho tới khi
 * admin duyệt quyền và bật nguồn.
 */
@Component
@ConfigurationProperties(prefix = "app.news")
public class NewsProperties {
    /** Bật module News (API đọc). Tắt thì controller không được đăng ký. */
    private boolean enabled = true;

    /** Bật scheduler thu thập. Mặc định TẮT — phải bật rõ ràng. */
    private boolean ingestionEnabled = false;

    /** Cho phép feed http (không phải https). Mặc định tắt. */
    private boolean allowHttp = false;

    private int connectTimeoutMs = 5000;
    private int readTimeoutMs = 15000;
    private int maxFeedBytes = 2 * 1024 * 1024;
    private int maxRedirects = 3;

    /** Số bài tối đa trả về mỗi trang. */
    private int maxPageSize = 50;

    /** Số bài nổi bật tối đa. */
    private int featuredLimit = 6;

    /** User-Agent gửi kèm — nêu rõ danh tính và cách liên hệ. */
    private String userAgent = "SmartPropNewsBot/1.0 (+https://smartprop.vn/bot)";

    /**
     * Host allowlist. Rỗng = cho phép mọi host công khai (chỉ dựa vào kiểm tra IP).
     * Đặt danh sách này ở production để giới hạn nguồn tin được phép fetch.
     *
     * <p>Khớp chính xác hostname hoặc subdomain của mục đó — không dùng substring.
     */
    private java.util.List<String> allowedHosts = new java.util.ArrayList<>();

    /** Bật kiểm tra allowlist. Khi bật và danh sách rỗng, mọi fetch bị từ chối. */
    private boolean enforceHostAllowlist = false;

    /**
     * CHỈ DÙNG CHO TEST. Cho phép fetch loopback để kiểm thử fetcher với HTTP server
     * cục bộ.
     *
     * <p>Không được đặt {@code true} ở production. {@code NewsFeedFetcher} chỉ đọc cờ
     * này khi {@code app.news.enabled} cũng bật và profile không phải production;
     * xem {@link NewsFeedFetcher#isLoopbackAllowedForTests()}.
     */
    private boolean allowLoopbackForTests = false;

    public boolean isEnabled() { return enabled; }
    public void setEnabled(boolean enabled) { this.enabled = enabled; }

    public boolean isIngestionEnabled() { return ingestionEnabled; }
    public void setIngestionEnabled(boolean ingestionEnabled) { this.ingestionEnabled = ingestionEnabled; }

    public boolean isAllowHttp() { return allowHttp; }
    public void setAllowHttp(boolean allowHttp) { this.allowHttp = allowHttp; }

    public int getConnectTimeoutMs() { return connectTimeoutMs; }
    public void setConnectTimeoutMs(int connectTimeoutMs) { this.connectTimeoutMs = connectTimeoutMs; }

    public int getReadTimeoutMs() { return readTimeoutMs; }
    public void setReadTimeoutMs(int readTimeoutMs) { this.readTimeoutMs = readTimeoutMs; }

    public int getMaxFeedBytes() { return maxFeedBytes; }
    public void setMaxFeedBytes(int maxFeedBytes) { this.maxFeedBytes = maxFeedBytes; }

    public int getMaxRedirects() { return maxRedirects; }
    public void setMaxRedirects(int maxRedirects) { this.maxRedirects = maxRedirects; }

    public int getMaxPageSize() { return maxPageSize; }
    public void setMaxPageSize(int maxPageSize) { this.maxPageSize = maxPageSize; }

    public int getFeaturedLimit() { return featuredLimit; }
    public void setFeaturedLimit(int featuredLimit) { this.featuredLimit = featuredLimit; }

    public String getUserAgent() { return userAgent; }
    public void setUserAgent(String userAgent) { this.userAgent = userAgent; }

    public java.util.List<String> getAllowedHosts() { return allowedHosts; }
    public void setAllowedHosts(java.util.List<String> allowedHosts) {
        this.allowedHosts = allowedHosts == null ? new java.util.ArrayList<>() : allowedHosts;
    }

    public boolean isEnforceHostAllowlist() { return enforceHostAllowlist; }
    public void setEnforceHostAllowlist(boolean enforceHostAllowlist) {
        this.enforceHostAllowlist = enforceHostAllowlist;
    }

    public boolean isAllowLoopbackForTests() { return allowLoopbackForTests; }
    public void setAllowLoopbackForTests(boolean allowLoopbackForTests) {
        this.allowLoopbackForTests = allowLoopbackForTests;
    }
}
