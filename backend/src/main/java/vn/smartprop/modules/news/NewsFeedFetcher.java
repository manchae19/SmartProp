package vn.smartprop.modules.news;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.Instant;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Optional;
import org.springframework.stereotype.Component;

/**
 * Tải feed qua HTTP với giới hạn an toàn.
 *
 * <p>Chỉ fetch URL đã lưu trong {@code news_sources} — không có endpoint nào cho phép
 * truyền URL tùy ý. Mỗi lần fetch đều kiểm tra lại {@link NewsUrlSafety}, kể cả
 * redirect (client không tự theo redirect; ta theo thủ công và kiểm tra từng bước).
 *
 * <p>Giới hạn: connect timeout, read timeout, kích thước tối đa, số redirect tối đa.
 * Hỗ trợ conditional GET qua ETag / If-Modified-Since.
 */
@Component
public class NewsFeedFetcher {
    private final NewsProperties properties;
    private final HttpClient client;

    public NewsFeedFetcher(NewsProperties properties) {
        this.properties = properties;
        this.client = HttpClient.newBuilder()
            .connectTimeout(Duration.ofMillis(properties.getConnectTimeoutMs()))
            .followRedirects(HttpClient.Redirect.NEVER)
            .build();
    }

    /**
     * Cờ test-only. Chỉ true khi cấu hình bật rõ ràng — mặc định false, và không có
     * profile production nào đặt giá trị này.
     */
    boolean isLoopbackAllowedForTests() {
        return properties.isAllowLoopbackForTests();
    }

    /** Kết quả một lần fetch. */
    public record FetchResult(int status, byte[] body, String etag, String lastModified,
                              String finalUrl, String errorCode, String errorMessage,
                              String retryAfter) {
        /** Constructor tiện dụng cho các trường hợp không có Retry-After. */
        public FetchResult(int status, byte[] body, String etag, String lastModified,
                           String finalUrl, String errorCode, String errorMessage) {
            this(status, body, etag, lastModified, finalUrl, errorCode, errorMessage, null);
        }
        public boolean notModified() { return status == 304; }
        public boolean ok() { return status >= 200 && status < 300; }
        public boolean failed() { return errorCode != null; }
        public boolean rateLimited() { return status == 429; }
    }

    /**
     * Executor cho việc đọc body. Có giới hạn để một nguồn xấu không tạo thread vô hạn.
     * Thread là daemon và bị hủy khi hết deadline.
     */
    private static final java.util.concurrent.ExecutorService BODY_READER =
        java.util.concurrent.Executors.newCachedThreadPool(runnable -> {
            Thread thread = new Thread(runnable, "news-body-reader");
            thread.setDaemon(true);
            return thread;
        });

    /** Chỉ những status này mới được theo như redirect. */
    private static final java.util.Set<Integer> REDIRECT_STATUSES =
        java.util.Set.of(301, 302, 303, 307, 308);

    /**
     * Tải feed.
     *
     * @param feedUrl      URL đã lưu trong nguồn
     * @param etag         ETag lần trước, có thể null
     * @param lastModified Last-Modified lần trước, có thể null
     */
    public FetchResult fetch(String feedUrl, String etag, String lastModified) {
        String currentUrl = feedUrl;
        int redirects = 0;

        while (true) {
            NewsUrlSafety.Result safety = isLoopbackAllowedForTests()
                ? NewsUrlSafety.checkAllowingLoopback(currentUrl, properties.isAllowHttp())
                : NewsUrlSafety.check(currentUrl, properties.isAllowHttp(), true,
                    properties.isEnforceHostAllowlist(), properties.getAllowedHosts());
            if (!safety.allowed()) {
                return new FetchResult(0, null, null, null, currentUrl,
                    "URL_BLOCKED", safety.reason());
            }

            HttpRequest.Builder builder;
            try {
                builder = HttpRequest.newBuilder(URI.create(currentUrl))
                    .timeout(Duration.ofMillis(properties.getReadTimeoutMs()))
                    .header("User-Agent", properties.getUserAgent())
                    .header("Accept", "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9")
                    .GET();
            } catch (IllegalArgumentException e) {
                return new FetchResult(0, null, null, null, currentUrl,
                    "INVALID_URL", "URL không hợp lệ");
            }
            if (etag != null && !etag.isBlank()) builder.header("If-None-Match", etag);
            if (lastModified != null && !lastModified.isBlank()) {
                builder.header("If-Modified-Since", lastModified);
            }

            HttpResponse<InputStream> response;
            try {
                response = client.send(builder.build(), HttpResponse.BodyHandlers.ofInputStream());
            } catch (java.net.http.HttpTimeoutException e) {
                return new FetchResult(0, null, null, null, currentUrl,
                    "TIMEOUT", "Hết thời gian chờ");
            } catch (IOException e) {
                return new FetchResult(0, null, null, null, currentUrl,
                    "NETWORK_ERROR", safeMessage(e));
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return new FetchResult(0, null, null, null, currentUrl,
                    "INTERRUPTED", "Bị ngắt");
            }

            int status = response.statusCode();

            // 304 KHÔNG phải redirect. Phải kiểm tra trước khối 3xx, nếu không
            // conditional GET sẽ bị coi là "redirect thiếu Location" và báo lỗi.
            if (status == 304) {
                closeQuietly(response.body());
                // Giữ ETag/Last-Modified đã gửi đi: nguồn xác nhận chúng vẫn đúng.
                return new FetchResult(304, null, etag, lastModified, currentUrl, null, null);
            }

            // Chỉ 301/302/303/307/308 là redirect thật. 300/305/306 và các 3xx khác
            // không được theo tự động.
            if (REDIRECT_STATUSES.contains(status)) {
                Optional<String> location = response.headers().firstValue("location");
                closeQuietly(response.body());
                if (location.isEmpty() || location.get().isBlank()) {
                    return new FetchResult(status, null, null, null, currentUrl,
                        "BAD_REDIRECT", "Redirect thiếu Location");
                }
                if (++redirects > properties.getMaxRedirects()) {
                    return new FetchResult(status, null, null, null, currentUrl,
                        "TOO_MANY_REDIRECTS", "Vượt quá số redirect cho phép");
                }
                try {
                    currentUrl = URI.create(currentUrl).resolve(location.get().strip()).toString();
                } catch (IllegalArgumentException e) {
                    return new FetchResult(status, null, null, null, currentUrl,
                        "BAD_REDIRECT", "Location không hợp lệ");
                }
                continue;
            }

            if (status == 429) {
                closeQuietly(response.body());
                String retryAfter = response.headers().firstValue("retry-after").orElse(null);
                return new FetchResult(429, null, null, null, currentUrl,
                    "RATE_LIMITED", "Nguồn yêu cầu giảm tần suất" +
                        (retryAfter == null ? "" : " (Retry-After: " + retryAfter + ")"),
                    retryAfter);
            }

            if (status < 200 || status >= 300) {
                closeQuietly(response.body());
                return new FetchResult(status, null, null, null, currentUrl,
                    "HTTP_" + status, "Nguồn trả HTTP " + status);
            }

            byte[] body;
            try {
                body = readLimited(response.body(), properties.getMaxFeedBytes());
            } catch (IOException e) {
                return new FetchResult(status, null, null, null, currentUrl,
                    "READ_ERROR", safeMessage(e));
            }
            if (body == null) {
                return new FetchResult(status, null, null, null, currentUrl,
                    "TOO_LARGE", "Feed vượt quá " + properties.getMaxFeedBytes() + " byte");
            }

            return new FetchResult(status, body,
                response.headers().firstValue("etag").orElse(null),
                response.headers().firstValue("last-modified").orElse(null),
                currentUrl, null, null);
        }
    }

    /**
     * Đọc tối đa {@code limit} byte, có deadline tổng THẬT.
     *
     * <p>{@code HttpRequest.timeout} chỉ bao phủ tới khi nhận header. Một nguồn gửi
     * header rồi im lặng khiến {@code in.read()} block vô thời hạn — kiểm tra
     * {@code System.nanoTime()} giữa các lần read không bao giờ chạy tới.
     *
     * <p>Cách sửa: đọc trong một task riêng, chờ tối đa {@code readTimeoutMs}. Hết hạn
     * thì {@code cancel(true)} + đóng stream, giải phóng worker và connection.
     *
     * @return body, hoặc {@code null} nếu vượt {@code limit} byte
     * @throws IOException khi hết deadline hoặc lỗi đọc
     */
    private byte[] readLimited(InputStream input, int limit) throws IOException {
        java.util.concurrent.Future<byte[]> task =
            BODY_READER.submit(() -> readAll(input, limit));
        try {
            return task.get(properties.getReadTimeoutMs(), java.util.concurrent.TimeUnit.MILLISECONDS);
        } catch (java.util.concurrent.TimeoutException e) {
            task.cancel(true);
            closeQuietly(input);
            throw new IOException("Hết thời gian đọc body");
        } catch (java.util.concurrent.ExecutionException e) {
            closeQuietly(input);
            Throwable cause = e.getCause();
            if (cause instanceof IOException io) throw io;
            throw new IOException("Lỗi đọc body: " + safeMessage(
                cause instanceof Exception ex ? ex : new IOException(String.valueOf(cause))));
        } catch (InterruptedException e) {
            task.cancel(true);
            closeQuietly(input);
            Thread.currentThread().interrupt();
            throw new IOException("Bị ngắt khi đọc body");
        }
    }

    /** Đọc toàn bộ stream tới {@code limit}. Chạy trong task riêng để hủy được. */
    private static byte[] readAll(InputStream input, int limit) throws IOException {
        try (InputStream in = input) {
            ByteArrayOutputStream out = new ByteArrayOutputStream(Math.min(limit, 64 * 1024));
            byte[] buffer = new byte[8192];
            int total = 0;
            int read;
            while ((read = in.read(buffer)) != -1) {
                total += read;
                if (total > limit) return null;
                out.write(buffer, 0, read);
            }
            return out.toByteArray();
        }
    }

    private static void closeQuietly(InputStream stream) {
        try { stream.close(); } catch (IOException ignored) { /* không quan trọng */ }
    }

    /** Thông điệp lỗi đã làm sạch — không lộ đường dẫn nội bộ hay stack trace. */
    private static String safeMessage(Exception e) {
        String message = e.getMessage();
        if (message == null) return e.getClass().getSimpleName();
        return message.length() > 200 ? message.substring(0, 200) : message;
    }

    /** Parse header {@code Retry-After} (giây hoặc HTTP-date) thành Instant. */
    public static Instant parseRetryAfter(String value) {
        if (value == null || value.isBlank()) return null;
        try {
            return Instant.now().plusSeconds(Long.parseLong(value.strip()));
        } catch (NumberFormatException ignored) {
            // thử HTTP-date
        }
        try {
            return ZonedDateTime.parse(value.strip(), DateTimeFormatter.RFC_1123_DATE_TIME).toInstant();
        } catch (Exception ignored) {
            return null;
        }
    }
}
