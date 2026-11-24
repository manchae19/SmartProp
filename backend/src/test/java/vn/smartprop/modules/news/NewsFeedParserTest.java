package vn.smartprop.modules.news;

import static org.junit.jupiter.api.Assertions.*;

import java.time.Instant;
import org.junit.jupiter.api.Test;

/** Parser RSS/Atom — bao gồm các ca XXE và dữ liệu lỗi. */
class NewsFeedParserTest {

    private static byte[] bytes(String xml) { return xml.getBytes(java.nio.charset.StandardCharsets.UTF_8); }

    @Test
    void parsesRss20WithVietnameseText() throws Exception {
        String xml = """
            <?xml version="1.0" encoding="UTF-8"?>
            <rss version="2.0"><channel>
              <title>Báo Đà Nẵng</title>
              <item>
                <title>Giá đất Đà Nẵng tăng mạnh quý IV</title>
                <link>https://example.vn/bai-1</link>
                <description>Thị trường bất động sản Đà Nẵng ghi nhận nhiều giao dịch.</description>
                <pubDate>Tue, 24 Nov 2026 08:00:00 +0700</pubDate>
                <guid>example-1</guid>
              </item>
            </channel></rss>
            """;
        NewsFeedParser.Result result = NewsFeedParser.parse(bytes(xml));
        assertEquals("RSS", result.format());
        assertEquals(1, result.items().size());
        NewsFeedParser.Item item = result.items().get(0);
        assertEquals("Giá đất Đà Nẵng tăng mạnh quý IV", item.title());
        assertEquals("https://example.vn/bai-1", item.link());
        assertEquals("example-1", item.externalId());
        assertNotNull(item.publishedAt());
    }

    @Test
    void parsesAtomWithAlternateLink() throws Exception {
        String xml = """
            <?xml version="1.0" encoding="UTF-8"?>
            <feed xmlns="http://www.w3.org/2005/Atom">
              <title>Feed</title>
              <entry>
                <title>Quy hoạch phân khu Hòa Vang</title>
                <link rel="alternate" href="https://example.vn/atom-1"/>
                <id>atom-1</id>
                <summary>Điều chỉnh quy hoạch đô thị.</summary>
                <published>2026-11-24T08:00:00Z</published>
              </entry>
            </feed>
            """;
        NewsFeedParser.Result result = NewsFeedParser.parse(bytes(xml));
        assertEquals("Atom", result.format());
        assertEquals(1, result.items().size());
        assertEquals("https://example.vn/atom-1", result.items().get(0).link());
        assertNotNull(result.items().get(0).publishedAt());
    }

    @Test
    void rejectsItemWithoutTitleOrLink() throws Exception {
        String xml = """
            <?xml version="1.0" encoding="UTF-8"?>
            <rss version="2.0"><channel>
              <item><title>Không có link</title></item>
              <item><link>https://example.vn/no-title</link></item>
              <item><title>Hợp lệ</title><link>https://example.vn/ok</link></item>
            </channel></rss>
            """;
        NewsFeedParser.Result result = NewsFeedParser.parse(bytes(xml));
        assertEquals(1, result.items().size());
        assertEquals(2, result.rejected());
    }

    @Test
    void missingPublishedDateStaysNull() throws Exception {
        String xml = """
            <?xml version="1.0" encoding="UTF-8"?>
            <rss version="2.0"><channel>
              <item><title>Không có ngày</title><link>https://example.vn/x</link></item>
            </channel></rss>
            """;
        NewsFeedParser.Result result = NewsFeedParser.parse(bytes(xml));
        assertNull(result.items().get(0).publishedAt(),
            "không được gán fetchedAt vào publishedAt");
    }

    @Test
    void rejectsDoctypeToBlockXxe() {
        String xml = """
            <?xml version="1.0"?>
            <!DOCTYPE rss [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
            <rss version="2.0"><channel>
              <item><title>&xxe;</title><link>https://example.vn/x</link></item>
            </channel></rss>
            """;
        assertThrows(Exception.class, () -> NewsFeedParser.parse(bytes(xml)),
            "DOCTYPE phải bị chặn để phòng XXE");
    }

    @Test
    void rejectsExternalEntityReference() {
        String xml = """
            <?xml version="1.0"?>
            <!DOCTYPE rss SYSTEM "http://attacker.example/evil.dtd">
            <rss version="2.0"><channel>
              <item><title>X</title><link>https://example.vn/x</link></item>
            </channel></rss>
            """;
        assertThrows(Exception.class, () -> NewsFeedParser.parse(bytes(xml)),
            "external DTD phải bị chặn");
    }

    @Test
    void rejectsMalformedXml() {
        assertThrows(Exception.class,
            () -> NewsFeedParser.parse(bytes("<rss><channel><item>")));
    }

    @Test
    void rejectsUnsupportedRoot() {
        assertThrows(IllegalArgumentException.class,
            () -> NewsFeedParser.parse(bytes("<html><body>x</body></html>")));
    }

    @Test
    void parsesRfc1123AndIsoDates() {
        assertNotNull(NewsFeedParser.parseDate("Tue, 24 Nov 2026 08:00:00 +0700"));
        assertNotNull(NewsFeedParser.parseDate("2026-11-24T08:00:00Z"));
        assertNull(NewsFeedParser.parseDate("không phải ngày"));
        assertNull(NewsFeedParser.parseDate(null));
    }

    @Test
    void emptyFeedYieldsNoItems() throws Exception {
        String xml = """
            <?xml version="1.0" encoding="UTF-8"?>
            <rss version="2.0"><channel><title>Rỗng</title></channel></rss>
            """;
        NewsFeedParser.Result result = NewsFeedParser.parse(bytes(xml));
        assertEquals(0, result.items().size());
        assertEquals(0, result.rejected());
    }
}
