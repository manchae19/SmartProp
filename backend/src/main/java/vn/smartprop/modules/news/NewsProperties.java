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
}
