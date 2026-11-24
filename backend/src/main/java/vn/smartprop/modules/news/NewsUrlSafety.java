package vn.smartprop.modules.news;

import java.net.Inet4Address;
import java.net.Inet6Address;
import java.net.InetAddress;
import java.net.URI;
import java.net.URISyntaxException;
import java.net.UnknownHostException;
import java.util.Locale;
import java.util.Set;

/**
 * Kiểm tra URL trước khi fetch — chống SSRF.
 *
 * <p>Chỉ cho phép {@code https} (và {@code http} chỉ khi bật rõ ràng). Chặn:
 * <ul>
 *   <li>URL chứa credentials ({@code user:pass@host})</li>
 *   <li>localhost, loopback, private, link-local, multicast, unspecified</li>
 *   <li>cloud metadata endpoints (169.254.169.254, metadata.google.internal, …)</li>
 *   <li>IPv6 loopback/ULA/link-local</li>
 *   <li>hostname không phân giải được</li>
 * </ul>
 *
 * <p><b>Giới hạn đã biết:</b> kiểm tra DNS ở đây và kết nối thực tế là hai thời điểm
 * khác nhau, nên DNS rebinding vẫn có thể xảy ra. Lớp phòng thủ thứ hai là allowlist
 * host của nguồn tin (feed URL do admin cấu hình, không do người dùng nhập) và
 * {@code NewsFeedFetcher} chỉ fetch đúng URL đã lưu trong {@code news_sources}.
 * Không có endpoint nào cho phép truyền URL tùy ý.
 */
public final class NewsUrlSafety {
    private NewsUrlSafety() {}

    /** Host bị chặn tuyệt đối, kể cả khi phân giải ra IP công khai. */
    private static final Set<String> BLOCKED_HOSTS = Set.of(
        "localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback",
        "metadata.google.internal", "metadata.goog",
        "instance-data", "instance-data.ec2.internal"
    );

    /** Tiền tố hostname nội bộ phổ biến. */
    private static final Set<String> BLOCKED_SUFFIXES = Set.of(
        ".local", ".internal", ".localhost", ".home.arpa", ".lan"
    );

    public record Result(boolean allowed, String reason) {
        static Result ok() { return new Result(true, null); }
        static Result deny(String reason) { return new Result(false, reason); }
    }

    /**
     * Kiểm tra URL có được phép fetch không.
     *
     * @param rawUrl       URL cần kiểm tra
     * @param allowHttp    cho phép {@code http} (mặc định chỉ {@code https})
     * @param resolveDns   phân giải DNS để kiểm tra IP thực (tắt trong unit test)
     */
    public static Result check(String rawUrl, boolean allowHttp, boolean resolveDns) {
        if (rawUrl == null || rawUrl.isBlank()) return Result.deny("URL rỗng");
        if (rawUrl.length() > 2000) return Result.deny("URL quá dài");

        URI uri;
        try {
            uri = new URI(rawUrl.strip());
        } catch (URISyntaxException e) {
            return Result.deny("URL không hợp lệ");
        }

        String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase(Locale.ROOT);
        if (!scheme.equals("https") && !(allowHttp && scheme.equals("http"))) {
            return Result.deny("Chỉ cho phép https" + (allowHttp ? " hoặc http" : ""));
        }
        if (uri.getUserInfo() != null) return Result.deny("URL chứa credentials");
        if (uri.getHost() == null || uri.getHost().isBlank()) return Result.deny("URL thiếu host");

        String host = uri.getHost().toLowerCase(Locale.ROOT);
        // Bỏ dấu chấm cuối (FQDN tuyệt đối) để không lách danh sách chặn.
        if (host.endsWith(".")) host = host.substring(0, host.length() - 1);

        if (BLOCKED_HOSTS.contains(host)) return Result.deny("Host bị chặn: " + host);
        for (String suffix : BLOCKED_SUFFIXES) {
            if (host.endsWith(suffix)) return Result.deny("Host nội bộ bị chặn: " + host);
        }

        // Nếu host đã là literal IP, kiểm tra trực tiếp.
        if (isIpLiteral(host)) {
            return checkAddress(host);
        }

        if (!resolveDns) return Result.ok();

        InetAddress[] addresses;
        try {
            addresses = InetAddress.getAllByName(host);
        } catch (UnknownHostException e) {
            return Result.deny("Không phân giải được host: " + host);
        }
        if (addresses.length == 0) return Result.deny("Host không có bản ghi địa chỉ");

        for (InetAddress address : addresses) {
            Result result = checkAddress(address);
            if (!result.allowed()) return result;
        }
        return Result.ok();
    }

    private static Result checkAddress(String literal) {
        try {
            return checkAddress(InetAddress.getByName(literal));
        } catch (UnknownHostException e) {
            return Result.deny("Địa chỉ IP không hợp lệ");
        }
    }

    /** Chặn mọi dải địa chỉ không phải IP công khai. */
    static Result checkAddress(InetAddress address) {
        if (address.isLoopbackAddress()) return Result.deny("Loopback bị chặn");
        if (address.isAnyLocalAddress()) return Result.deny("Địa chỉ unspecified bị chặn");
        if (address.isLinkLocalAddress()) return Result.deny("Link-local bị chặn");
        if (address.isSiteLocalAddress()) return Result.deny("Private IP bị chặn");
        if (address.isMulticastAddress()) return Result.deny("Multicast bị chặn");

        byte[] raw = address.getAddress();

        if (address instanceof Inet4Address) {
            int b0 = raw[0] & 0xff;
            int b1 = raw[1] & 0xff;
            // 0.0.0.0/8
            if (b0 == 0) return Result.deny("Dải 0.0.0.0/8 bị chặn");
            // 100.64.0.0/10 — carrier-grade NAT
            if (b0 == 100 && b1 >= 64 && b1 <= 127) return Result.deny("CGNAT bị chặn");
            // 169.254.0.0/16 — link-local, gồm cloud metadata
            if (b0 == 169 && b1 == 254) return Result.deny("Link-local/metadata bị chặn");
            // 192.0.0.0/24, 192.0.2.0/24, 198.18.0.0/15, 198.51.100.0/24, 203.0.113.0/24
            if (b0 == 192 && b1 == 0) return Result.deny("Dải reserved bị chặn");
            if (b0 == 198 && (b1 == 18 || b1 == 19)) return Result.deny("Dải benchmark bị chặn");
            if (b0 == 198 && b1 == 51) return Result.deny("Dải documentation bị chặn");
            if (b0 == 203 && b1 == 0) return Result.deny("Dải documentation bị chặn");
            // 240.0.0.0/4 — reserved
            if (b0 >= 240) return Result.deny("Dải reserved bị chặn");
        } else if (address instanceof Inet6Address) {
            // fc00::/7 — unique local
            if ((raw[0] & 0xfe) == 0xfc) return Result.deny("IPv6 ULA bị chặn");
            // fe80::/10 — link-local (đã bắt ở trên, giữ để rõ ràng)
            if ((raw[0] & 0xff) == 0xfe && (raw[1] & 0xc0) == 0x80) {
                return Result.deny("IPv6 link-local bị chặn");
            }
            // IPv4-mapped ::ffff:a.b.c.d — kiểm tra phần IPv4 nhúng
            boolean mapped = true;
            for (int i = 0; i < 10; i++) if (raw[i] != 0) { mapped = false; break; }
            if (mapped && (raw[10] & 0xff) == 0xff && (raw[11] & 0xff) == 0xff) {
                try {
                    byte[] v4 = {raw[12], raw[13], raw[14], raw[15]};
                    return checkAddress(InetAddress.getByAddress(v4));
                } catch (UnknownHostException e) {
                    return Result.deny("IPv4-mapped không hợp lệ");
                }
            }
        }
        return Result.ok();
    }

    private static boolean isIpLiteral(String host) {
        // IPv4 thuần số và chấm.
        if (host.matches("^\\d{1,3}(\\.\\d{1,3}){3}$")) return true;
        // IPv6 trong ngoặc vuông đã bị URI bỏ ngoặc; nhận diện bằng dấu hai chấm.
        return host.contains(":");
    }
}
