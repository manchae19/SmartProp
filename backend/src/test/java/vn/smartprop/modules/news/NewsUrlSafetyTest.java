package vn.smartprop.modules.news;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

/** SSRF protection — kiểm tra URL trước khi fetch. */
class NewsUrlSafetyTest {

    @Test
    void allowsPublicHttpsUrl() {
        NewsUrlSafety.Result result =
            NewsUrlSafety.check("https://vnexpress.net/rss/bat-dong-san.rss", false, false);
        assertTrue(result.allowed(), result.reason());
    }

    @Test
    void rejectsHttpWhenNotAllowed() {
        NewsUrlSafety.Result result =
            NewsUrlSafety.check("http://example.com/feed", false, false);
        assertFalse(result.allowed());
        assertTrue(result.reason().contains("https"));
    }

    @Test
    void allowsHttpWhenExplicitlyEnabled() {
        assertTrue(NewsUrlSafety.check("http://example.com/feed", true, false).allowed());
    }

    @Test
    void rejectsNonHttpSchemes() {
        for (String url : new String[]{
            "file:///etc/passwd", "ftp://example.com/x", "gopher://example.com/x",
            "javascript:alert(1)", "data:text/xml,<rss/>"}) {
            assertFalse(NewsUrlSafety.check(url, true, false).allowed(), url);
        }
    }

    @Test
    void rejectsCredentialsInUrl() {
        NewsUrlSafety.Result result =
            NewsUrlSafety.check("https://user:pass@example.com/feed", false, false);
        assertFalse(result.allowed());
        assertTrue(result.reason().contains("credentials"));
    }

    @Test
    void rejectsLocalhostVariants() {
        for (String url : new String[]{
            "https://localhost/feed", "https://LOCALHOST/feed",
            "https://localhost./feed", "https://ip6-localhost/feed"}) {
            assertFalse(NewsUrlSafety.check(url, false, false).allowed(), url);
        }
    }

    @Test
    void rejectsInternalHostSuffixes() {
        for (String url : new String[]{
            "https://printer.local/feed", "https://api.internal/feed",
            "https://box.home.arpa/feed", "https://nas.lan/feed"}) {
            assertFalse(NewsUrlSafety.check(url, false, false).allowed(), url);
        }
    }

    @Test
    void rejectsLoopbackIpv4() {
        for (String url : new String[]{
            "https://127.0.0.1/feed", "https://127.1.2.3/feed", "https://0.0.0.0/feed"}) {
            assertFalse(NewsUrlSafety.check(url, false, false).allowed(), url);
        }
    }

    @Test
    void rejectsPrivateIpv4Ranges() {
        for (String url : new String[]{
            "https://10.0.0.1/feed", "https://172.16.0.1/feed", "https://192.168.1.1/feed",
            "https://100.64.0.1/feed", "https://169.254.169.254/latest/meta-data/",
            "https://192.0.2.1/feed", "https://198.18.0.1/feed", "https://240.0.0.1/feed"}) {
            assertFalse(NewsUrlSafety.check(url, false, false).allowed(), url);
        }
    }

    @Test
    void rejectsCloudMetadataHosts() {
        for (String url : new String[]{
            "https://metadata.google.internal/computeMetadata/v1/",
            "https://169.254.169.254/latest/meta-data/",
            "https://instance-data/latest/"}) {
            assertFalse(NewsUrlSafety.check(url, false, false).allowed(), url);
        }
    }

    @Test
    void rejectsIpv6LoopbackAndUla() {
        for (String url : new String[]{
            "https://[::1]/feed", "https://[fc00::1]/feed", "https://[fd12:3456::1]/feed",
            "https://[fe80::1]/feed"}) {
            assertFalse(NewsUrlSafety.check(url, false, false).allowed(), url);
        }
    }

    @Test
    void rejectsIpv4MappedIpv6Loopback() {
        assertFalse(NewsUrlSafety.check("https://[::ffff:127.0.0.1]/feed", false, false).allowed());
    }

    @Test
    void rejectsEmptyAndOversizedUrl() {
        assertFalse(NewsUrlSafety.check(null, false, false).allowed());
        assertFalse(NewsUrlSafety.check("", false, false).allowed());
        assertFalse(NewsUrlSafety.check("https://example.com/" + "a".repeat(2100), false, false).allowed());
    }

    @Test
    void rejectsUrlWithoutHost() {
        assertFalse(NewsUrlSafety.check("https:///feed", false, false).allowed());
    }

    @Test
    void dnsResolutionRejectsHostResolvingToPrivateIp() {
        // "localhost" đã bị chặn ở danh sách host, nhưng kiểm tra thêm nhánh DNS.
        NewsUrlSafety.Result result = NewsUrlSafety.check("https://localhost/feed", false, true);
        assertFalse(result.allowed());
    }
}
