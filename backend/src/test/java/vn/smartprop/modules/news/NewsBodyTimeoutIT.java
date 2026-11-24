package vn.smartprop.modules.news;

import static org.junit.jupiter.api.Assertions.*;

import com.sun.net.httpserver.HttpServer;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * Body timeout thật: server gửi header rồi im lặng hoàn toàn.
 *
 * <p>Đây là ca mà kiểm tra {@code System.nanoTime()} giữa các lần {@code read()} không
 * bao giờ chạy tới — {@code read()} block vô thời hạn. Test chứng minh fetcher vẫn
 * kết thúc trong thời gian giới hạn.
 */
class NewsBodyTimeoutIT {

    private HttpServer server;
    private String baseUrl;
    private NewsProperties properties;
    private NewsFeedFetcher fetcher;
    private final AtomicInteger requests = new AtomicInteger();

    @BeforeEach
    void start() throws Exception {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);

        // Header 200 + Content-Length lớn, rồi không gửi byte nào và giữ socket mở.
        server.createContext("/silent", exchange -> {
            requests.incrementAndGet();
            exchange.sendResponseHeaders(200, 1_000_000);
            // Không ghi gì, không đóng — mô phỏng nguồn treo.
            try {
                Thread.sleep(60_000);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        });

        // Gửi một phần rồi dừng hẳn.
        server.createContext("/partial", exchange -> {
            requests.incrementAndGet();
            exchange.sendResponseHeaders(200, 1_000_000);
            try (OutputStream out = exchange.getResponseBody()) {
                out.write("<rss>".getBytes(StandardCharsets.UTF_8));
                out.flush();
                Thread.sleep(60_000);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            } catch (java.io.IOException ignored) {
                // client đóng khi hết deadline
            }
        });

        // Slow drip: mỗi 300ms một byte.
        server.createContext("/drip", exchange -> {
            requests.incrementAndGet();
            exchange.sendResponseHeaders(200, 0);
            try (OutputStream out = exchange.getResponseBody()) {
                for (int i = 0; i < 200; i++) {
                    out.write('x');
                    out.flush();
                    Thread.sleep(300);
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            } catch (java.io.IOException ignored) {
                // client đóng
            }
        });

        // Feed hợp lệ để chứng minh fetcher vẫn dùng được sau timeout.
        server.createContext("/ok", exchange -> {
            requests.incrementAndGet();
            byte[] body = """
                <?xml version="1.0" encoding="UTF-8"?>
                <rss version="2.0"><channel><title>T</title>
                  <item><title>Giá đất</title><link>https://example.vn/a</link></item>
                </channel></rss>
                """.getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200, body.length);
            try (OutputStream out = exchange.getResponseBody()) { out.write(body); }
        });

        server.setExecutor(java.util.concurrent.Executors.newCachedThreadPool(r -> {
            Thread t = new Thread(r, "news-fixture");
            t.setDaemon(true);
            return t;
        }));
        server.start();
        baseUrl = "http://127.0.0.1:" + server.getAddress().getPort();

        properties = new NewsProperties();
        properties.setAllowHttp(true);

        properties.setReadTimeoutMs(1500);
        properties.setConnectTimeoutMs(1000);
        properties.setMaxFeedBytes(1024 * 1024);
        // Test-only transport: cho phép loopback để chạy HTTP fixture. Nằm trong
        // src/test, không tồn tại trong artifact production.
        fetcher = new TestNewsFeedFetcher(properties);
    }

    @AfterEach
    void stop() {
        if (server != null) server.stop(0);
    }

    @Test
    void silentBodyIsCutByDeadline() {
        long begin = System.nanoTime();
        var result = fetcher.fetch(baseUrl + "/silent", null, null);
        long elapsedMs = (System.nanoTime() - begin) / 1_000_000;

        assertTrue(result.failed(), "body im lặng phải bị cắt");
        assertTrue(elapsedMs < 10_000,
            "phải kết thúc trong khoảng deadline, thực tế " + elapsedMs + "ms");
    }

    @Test
    void partialBodyIsCutByDeadline() {
        long begin = System.nanoTime();
        var result = fetcher.fetch(baseUrl + "/partial", null, null);
        long elapsedMs = (System.nanoTime() - begin) / 1_000_000;

        assertTrue(result.failed(), "body gửi một phần rồi dừng phải bị cắt");
        assertTrue(elapsedMs < 10_000, "thực tế " + elapsedMs + "ms");
    }

    @Test
    void slowDripIsCutByDeadline() {
        long begin = System.nanoTime();
        var result = fetcher.fetch(baseUrl + "/drip", null, null);
        long elapsedMs = (System.nanoTime() - begin) / 1_000_000;

        assertTrue(result.failed(), "slow drip phải bị cắt");
        assertTrue(elapsedMs < 10_000, "thực tế " + elapsedMs + "ms");
    }

    @Test
    void fetcherStillWorksAfterTimeout() {
        // Gây timeout trước.
        fetcher.fetch(baseUrl + "/silent", null, null);
        // Request tiếp theo phải thành công — worker và connection được giải phóng.
        var result = fetcher.fetch(baseUrl + "/ok", null, null);
        assertTrue(result.ok(), "err=" + result.errorCode());
        assertNotNull(result.body());
    }

    @Test
    void deadlineDoesNotLeakThreads() throws Exception {
        int before = Thread.activeCount();
        for (int i = 0; i < 3; i++) {
            fetcher.fetch(baseUrl + "/silent", null, null);
        }
        // Cho thread daemon kịp kết thúc.
        Thread.sleep(500);
        int after = Thread.activeCount();
        assertTrue(after - before < 10,
            "không được rò rỉ thread: trước " + before + ", sau " + after);
    }
}
