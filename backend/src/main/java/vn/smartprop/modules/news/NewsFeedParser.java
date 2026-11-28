package vn.smartprop.modules.news;

import java.io.ByteArrayInputStream;
import java.io.StringReader;
import java.time.Instant;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;
import org.xml.sax.InputSource;

/**
 * Parser RSS 2.0 / Atom an toàn.
 *
 * <p>Bảo vệ XXE: tắt DOCTYPE, tắt external entities, tắt external DTD, tắt XInclude,
 * đặt {@code FEATURE_SECURE_PROCESSING}. Parser không bao giờ tạo outbound request.
 *
 * <p>Một item lỗi không làm hỏng cả feed: item thiếu title hoặc link bị bỏ qua và
 * đếm vào {@code rejected}.
 */
public final class NewsFeedParser {
    private NewsFeedParser() {}

    /** Một item đã parse, chưa chuẩn hoá URL. */
    public record Item(String externalId, String link, String title, String summary,
                       Instant publishedAt) {}

    public record Result(List<Item> items, int rejected, String format) {}

    public static Result parse(byte[] xml) throws Exception {
        Document document = newBuilder().parse(new ByteArrayInputStream(xml));
        document.getDocumentElement().normalize();

        Element root = document.getDocumentElement();
        String rootName = localName(root);

        if ("rss".equalsIgnoreCase(rootName)) {
            return parseRss(root);
        }
        if ("feed".equalsIgnoreCase(rootName)) {
            return parseAtom(root);
        }
        throw new IllegalArgumentException("Định dạng feed không hỗ trợ: " + rootName);
    }

    private static DocumentBuilder newBuilder() throws Exception {
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        // XXE: chặn DOCTYPE và mọi entity bên ngoài.
        factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
        factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
        factory.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
        factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
        factory.setXIncludeAware(false);
        factory.setExpandEntityReferences(false);
        factory.setNamespaceAware(true);
        DocumentBuilder builder = factory.newDocumentBuilder();
        // Không cho parser tự phân giải entity ngoài.
        builder.setEntityResolver((publicId, systemId) -> new InputSource(new StringReader("")));
        return builder;
    }

    private static Result parseRss(Element root) {
        List<Item> items = new ArrayList<>();
        int rejected = 0;
        NodeList nodes = root.getElementsByTagName("item");
        for (int i = 0; i < nodes.getLength(); i++) {
            Element item = (Element) nodes.item(i);
            String title = text(item, "title");
            String link = text(item, "link");
            if (isBlank(title) || isBlank(link)) { rejected++; continue; }
            items.add(new Item(
                firstNonBlank(text(item, "guid"), link),
                link,
                title,
                firstNonBlank(text(item, "description"), text(item, "encoded")),
                parseDate(firstNonBlank(text(item, "pubDate"), text(item, "date")))
            ));
        }
        return new Result(items, rejected, "RSS");
    }

    private static Result parseAtom(Element root) {
        List<Item> items = new ArrayList<>();
        int rejected = 0;
        NodeList nodes = root.getElementsByTagNameNS("*", "entry");
        for (int i = 0; i < nodes.getLength(); i++) {
            Element entry = (Element) nodes.item(i);
            String title = text(entry, "title");
            String link = atomLink(entry);
            if (isBlank(title) || isBlank(link)) { rejected++; continue; }
            items.add(new Item(
                firstNonBlank(text(entry, "id"), link),
                link,
                title,
                firstNonBlank(text(entry, "summary"), text(entry, "content")),
                parseDate(firstNonBlank(text(entry, "published"), text(entry, "updated")))
            ));
        }
        return new Result(items, rejected, "Atom");
    }

    /** Atom có nhiều {@code <link>}; ưu tiên {@code rel="alternate"} hoặc không có rel. */
    private static String atomLink(Element entry) {
        NodeList links = entry.getElementsByTagNameNS("*", "link");
        String fallback = null;
        for (int i = 0; i < links.getLength(); i++) {
            Element link = (Element) links.item(i);
            String href = link.getAttribute("href");
            if (isBlank(href)) continue;
            String rel = link.getAttribute("rel");
            if (isBlank(rel) || "alternate".equalsIgnoreCase(rel)) return href;
            if (fallback == null) fallback = href;
        }
        return fallback;
    }

    /** Lấy text của con trực tiếp đầu tiên khớp tên cục bộ (bỏ qua namespace). */
    private static String text(Element parent, String localName) {
        NodeList children = parent.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            Node node = children.item(i);
            if (node.getNodeType() != Node.ELEMENT_NODE) continue;
            if (localName.equals(localName(node))) {
                String value = node.getTextContent();
                return value == null ? null : value.strip();
            }
        }
        return null;
    }

    private static String localName(Node node) {
        String name = node.getLocalName();
        return name != null ? name : node.getNodeName();
    }

    private static final DateTimeFormatter RFC_1123 =
        DateTimeFormatter.RFC_1123_DATE_TIME;

    /**
     * RSS dùng RFC 822/1123 với offset dạng {@code +0700} (không có dấu hai chấm).
     * {@link DateTimeFormatter#RFC_1123_DATE_TIME} chỉ nhận {@code +07:00}, nên phải
     * thử thêm pattern RFC 822 trước khi bỏ cuộc.
     */
    private static final DateTimeFormatter RFC_822 =
        DateTimeFormatter.ofPattern("EEE, dd MMM yyyy HH:mm:ss Z", Locale.ENGLISH);

    /** Một số feed bỏ tên thứ trong ngày. */
    private static final DateTimeFormatter RFC_822_NO_DAY =
        DateTimeFormatter.ofPattern("dd MMM yyyy HH:mm:ss Z", Locale.ENGLISH);

    /** Parse ngày RSS (RFC 822/1123) hoặc Atom (ISO-8601). Trả null nếu không đọc được. */
    static Instant parseDate(String raw) {
        if (isBlank(raw)) return null;
        String value = raw.strip();

        for (DateTimeFormatter formatter : new DateTimeFormatter[]{
                RFC_822, RFC_822_NO_DAY, RFC_1123}) {
            try {
                return ZonedDateTime.parse(value, formatter).toInstant();
            } catch (DateTimeParseException ignored) {
                // thử formatter tiếp theo
            }
        }
        try {
            return Instant.parse(value);
        } catch (DateTimeParseException ignored) {
            // thử offset date-time
        }
        try {
            return ZonedDateTime.parse(value, DateTimeFormatter.ISO_OFFSET_DATE_TIME).toInstant();
        } catch (DateTimeParseException ignored) {
            return null;
        }
    }

    private static boolean isBlank(String value) { return value == null || value.isBlank(); }

    private static String firstNonBlank(String first, String second) {
        return isBlank(first) ? second : first;
    }
}
