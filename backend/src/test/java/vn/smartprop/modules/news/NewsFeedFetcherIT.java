package vn.smartprop.modules.news;

import static org.junit.jupiter.api.Assertions.*;

import com.sun.net.httpserver.HttpServer;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * Fetcher integration test với HTTP server thật trên loopback.
 *
 * <p>Khác với {@link NewsUrlSafetyTest} (kiểm tra logic URL thuần), test này gọi
 * {@link NewsFeedFetcher} thật qua socket thật để xác minh status handling, redirect,
 * conditional GET, timeout và giới hạn kích thước.
 *
 * <p>Server chạy trên {@code 127.0.0.1} — địa chỉ mà SSRF guard chặn. Vì vậy test
 * dựng fetcher với {@code allowHttp=true} và tắt DNS resolution, đồng thời kiểm tra
 * riêng rằng guard vẫn chặn loopback khi bật đầy đủ. Đây là cấu hình test cô lập,
 * không phải bypass production.
 */
class NewsFeedFetcherIT {

    private HttpServer server;
    private String baseUrl;
    private NewsProperties properties;
    private NewsFeedFetcher fetcher;

    private final AtomicInteger requestCount = new AtomicInteger();
    private final AtomicReference<String> lastIfNoneMatch = new AtomicReference<>();
    private final AtomicReference<String> lastIfModifiedSince = new AtomicReference<>();

    @BeforeEach
    void start() throws Exception {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/feed", exchange -> {
            requestCount.incrementAndGet();
            lastIfNoneMatch.set(exchange.getRequestHeaders().getFirst("If-None-Match"));
            lastIfModifiedSince.set(exchange.getRequestHeaders().getFirst("If-Modified-Since"));
            byte[] body = """
                <?xml version="1.0" encoding="UTF-8"?>
                <rss version="2.0"><channel><title>T</title>
                  <item><title>Giá đất Đà Nẵng</title>
                    <link>https://example.vn/a1</link></item>
                </channel></rss>
                """.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("ETag", "\"v1\"");
            exchange.getResponseHeaders().add("Last-Modified", "Tue, 24 Nov 2026 08:00:00 GMT");
            exchange.sendResponseHeaders(200, body.length);
            try (OutputStream out = exchange.getResponseBody()) { out.write(body); }
        });
        server.createContext("/not-modified", exchange -> {
            requestCount.incrementAndGet();
            lastIfNoneMatch.set(exchange.getRequestHeaders().getFirst("If-None-Match"));
            exchange.sendResponseHeaders(304, -1);
            exchange.close();
        });
        server.createContext("/redirect", exchange -> {
            exchange.getResponseHeaders().add("Location", baseUrl + "/feed");
            exchange.sendResponseHeaders(302, -1);
            exchange.close();
        });
        server.createContext("/redirect-no-location", exchange -> {
            exchange.sendResponseHeaders(302, -1);
            exchange.close();
        });
        server.createContext("/redirect-loop", exchange -> {
            exchange.getResponseHeaders().add("Location", baseUrl + "/redirect-loop");
            exchange.sendResponseHeaders(302, -1);
            exchange.close();
        });
        server.createContext("/rate-limited", exchange -> {
            exchange.getResponseHeaders().add("Retry-After", "120");
            exchange.sendResponseHeaders(429, -1);
            exchange.close();
        });
        server.createContext("/server-error", exchange -> {
            exchange.sendResponseHeaders(500, -1);
            exchange.close();
        });
        server.createContext("/huge", exchange -> {
            byte[] body = new byte[3 * 1024 * 1024];
            exchange.sendResponseHeaders(200, body.length);
            try (OutputStream out = exchange.getResponseBody()) { out.write(body); }
        });
        server.createContext("/slow", exchange -> {
            exchange.sendResponseHeaders(200, 0);
            try (OutputStream out = exchange.getResponseBody()) {
                for (int i = 0; i < 100; i++) {
                    out.write('x');
                    out.flush();
                    Thread.sleep(200);
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            } catch (java.io.IOException ignored) {
                // client đóng kết nối khi hết deadline
            }
        });
        server.start();
        baseUrl = "http://127.0.0.1:" + server.getAddress().getPort();

        properties = new NewsProperties();
        properties.setAllowHttp(true);
        // Test-only: cho phép loopback để dùng HTTP server cục bộ. Production không
        // đặt cờ này; SSRF guard vẫn chặn loopback ở đường mặc định.
        properties.setAllowLoopbackForTests(true);
        properties.setReadTimeoutMs(2000);
        properties.setConnectTimeoutMs(1000);
        properties.setMaxFeedBytes(1024 * 1024);
        properties.setMaxRedirects(2);
        fetcher = new NewsFeedFetcher(properties);
    }

    @AfterEach
    void stop() {
        if (server != null) server.stop(0);
    }

    @Test
    void fetchesValidFeed() {
        var result = fetcher.fetch(baseUrl + "/feed", null, null);
        assertTrue(result.ok(), "status=" + result.status() + " err=" + result.errorCode());
        assertEquals(200, result.status());
        assertNotNull(result.body());
        assertEquals("\"v1\"", result.etag());
        assertNotNull(result.lastModified());
    }

    @Test
    void http304IsNotTreatedAsRedirect() {
        var result = fetcher.fetch(baseUrl + "/not-modified", "\"v1\"", null);
        assertTrue(result.notModified(), "304 phải được nhận là NOT_MODIFIED");
        assertNull(result.errorCode(), "304 không được sinh lỗi BAD_REDIRECT");
        assertEquals(304, result.status());
        assertFalse(result.failed());
    }

    @Test
    void conditionalGetSendsHeaders() {
        fetcher.fetch(baseUrl + "/feed", "\"v1\"", "Tue, 24 Nov 2026 08:00:00 GMT");
        assertEquals("\"v1\"", lastIfNoneMatch.get());
        assertEquals("Tue, 24 Nov 2026 08:00:00 GMT", lastIfModifiedSince.get());
    }

    @Test
    void followsValidRedirect() {
        var result = fetcher.fetch(baseUrl + "/redirect", null, null);
        assertTrue(result.ok(), "err=" + result.errorCode());
        assertEquals(200, result.status());
    }

    @Test
    void redirectWithoutLocationIsRejected() {
        var result = fetcher.fetch(baseUrl + "/redirect-no-location", null, null);
        assertTrue(result.failed());
        assertEquals("BAD_REDIRECT", result.errorCode());
    }

    @Test
    void redirectLoopIsStopped() {
        var result = fetcher.fetch(baseUrl + "/redirect-loop", null, null);
        assertTrue(result.failed());
        assertEquals("TOO_MANY_REDIRECTS", result.errorCode());
    }

    @Test
    void rateLimitCarriesRetryAfter() {
        var result = fetcher.fetch(baseUrl + "/rate-limited", null, null);
        assertTrue(result.failed());
        assertEquals("RATE_LIMITED", result.errorCode());
        assertTrue(result.rateLimited());
        assertEquals("120", result.retryAfter());
    }

    @Test
    void serverErrorIsReported() {
        var result = fetcher.fetch(baseUrl + "/server-error", null, null);
        assertTrue(result.failed());
        assertEquals("HTTP_500", result.errorCode());
    }

    @Test
    void oversizedResponseIsRejected() {
        var result = fetcher.fetch(baseUrl + "/huge", null, null);
        assertTrue(result.failed());
        assertEquals("TOO_LARGE", result.errorCode());
    }

    @Test
    void slowBodyHitsReadDeadline() {
        long begin = System.nanoTime();
        var result = fetcher.fetch(baseUrl + "/slow", null, null);
        long elapsedMs = (System.nanoTime() - begin) / 1_000_000;
        assertTrue(result.failed(), "body chậm phải bị cắt");
        assertTrue(elapsedMs < 15_000,
            "phải dừng trong khoảng deadline, thực tế " + elapsedMs + "ms");
    }

    @Test
    void loopbackIsStillBlockedBySsrfGuard() {
        // Guard đầy đủ (không tắt DNS) phải chặn loopback, kể cả khi allowHttp=true.
        NewsUrlSafety.Result result = NewsUrlSafety.check(
            baseUrl + "/feed", true, true, false, java.util.List.of());
        assertFalse(result.allowed(), "loopback phải bị chặn bởi SSRF guard");
    }

    @Test
    void allowlistBlocksUnlistedHost() {
        // Tắt cờ loopback để đi đúng đường production: guard đầy đủ + allowlist.
        properties.setAllowLoopbackForTests(false);
        properties.setEnforceHostAllowlist(true);
        properties.setAllowedHosts(java.util.List.of("vnexpress.net"));
        var result = fetcher.fetch(baseUrl + "/feed", null, null);
        assertTrue(result.failed());
        assertEquals("URL_BLOCKED", result.errorCode());
    }
}
