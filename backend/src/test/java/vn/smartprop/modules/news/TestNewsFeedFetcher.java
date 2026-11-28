package vn.smartprop.modules.news;

import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

/**
 * Transport CHỈ DÙNG TRONG TEST — cho phép loopback để chạy HTTP fixture server.
 *
 * <p>Nằm trong {@code src/test}, nên không tồn tại trong artifact production. Không có
 * property, biến môi trường hay profile nào bật được nó ở runtime thật.
 *
 * <p>Khác biệt duy nhất so với {@link NewsFeedFetcher}: bỏ kiểm tra loopback của
 * {@link NewsUrlSafety}. Mọi kiểm tra khác giữ nguyên — private IP, link-local,
 * metadata, redirect, allowlist, size limit, timeout.
 */
class TestNewsFeedFetcher extends NewsFeedFetcher {

    TestNewsFeedFetcher(NewsProperties properties) {
        super(properties);
    }

    /**
     * Bỏ release gate CHỈ trong test để kiểm thử transport. Production luôn trả
     * {@code LIVE_INGESTION_LOCKED} trước khi tới đây.
     */
    @Override
    public FetchResult fetch(String feedUrl, String etag, String lastModified) {
        try {
            var transport = NewsFeedFetcher.class.getDeclaredMethod("fetchTransport", String.class, String.class, String.class);
            transport.setAccessible(true);
            return (FetchResult) transport.invoke(this, feedUrl, etag, lastModified);
        } catch (ReflectiveOperationException exception) {
            throw new AssertionError("Test-only transport invocation failed", exception);
        }
    }

    /**
     * Chỉ nới đúng loopback. Private/link-local/metadata vẫn bị chặn — test không
     * được chứng minh một hành vi mà production không có.
     */
    @Override
    NewsUrlSafety.Result checkDestination(String url) {
        NewsUrlSafety.Result strict = super.checkDestination(url);
        if (strict.allowed()) return strict;
        if (strict.reason() != null && strict.reason().contains("Loopback")) {
            try {
                String host = URI.create(url).getHost();
                if ("127.0.0.1".equals(host) || "localhost".equals(host) || "::1".equals(host)) {
                    return new NewsUrlSafety.Result(true, null);
                }
            } catch (IllegalArgumentException ignored) {
                // rơi xuống deny
            }
        }
        return strict;
    }
}
