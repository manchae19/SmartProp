package vn.smartprop.comparable;

import java.net.URI;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.Locale;
import java.util.Set;
import java.util.stream.Collectors;

/** Only observed listing identities can exclude or combine rows. */
final class ComparableIdentity {
    private ComparableIdentity() {}

    record Key(String namespace, String source, String value) {}

    static Set<Key> keys(String candidateId, String source, String sourceListingId, String group, String url) {
        Set<Key> keys = new LinkedHashSet<>();
        add(keys, "id", "", candidateId);
        if (text(source) != null) {
            String namespace = source.strip().toUpperCase(Locale.ROOT);
            add(keys, "source-listing", namespace, sourceListingId);
            add(keys, "duplicate-group", namespace, group);
        }
        add(keys, "url", "", canonicalUrl(url));
        return keys;
    }

    static Set<Key> subject(String propertyId, ComparableDtos.SubjectIdentity identity) {
        Set<Key> keys = new LinkedHashSet<>(keys(
            propertyId == null ? null : "property:" + propertyId,
            externalNamespace(identity.externalSource()), identity.sourceListingId(), null, identity.canonicalUrl()));
        if (identity.externalId() != null) add(keys, "id", "", "external:" + identity.externalId());
        if (text(identity.tinixId()) != null) add(keys, "id", "", "tinix:" + identity.tinixId());
        return keys;
    }

    static String externalNamespace(String source) {
        String value = text(source);
        return value == null ? null : "external:" + value;
    }

    static String text(String value) {
        return value == null || value.isBlank() ? null : value.strip();
    }

    static String canonicalUrl(String value) {
        if (text(value) == null || value.length() > 2048) return null;
        try {
            URI uri = URI.create(value.strip()).normalize();
            String scheme = uri.getScheme();
            String host = uri.getHost();
            if (scheme == null || host == null || uri.getRawUserInfo() != null) return null;
            scheme = scheme.toLowerCase(Locale.ROOT);
            if (!Set.of("http", "https").contains(scheme)) return null;
            int port = uri.getPort();
            if (port == ("https".equals(scheme) ? 443 : 80)) port = -1;
            String path = uri.getRawPath();
            if (path.isEmpty()) path = "/";
            String query = uri.getRawQuery();
            if (query != null) {
                query = Arrays.stream(query.split("&", -1)).filter(ComparableIdentity::identifyingParameter)
                    .collect(Collectors.joining("&"));
            }
            return scheme + "://" + host.toLowerCase(Locale.ROOT) + (port == -1 ? "" : ":" + port)
                + path + (query == null || query.isEmpty() ? "" : "?" + query);
        } catch (IllegalArgumentException ex) {
            return null;
        }
    }

    private static boolean identifyingParameter(String parameter) {
        String key = parameter.split("=", 2)[0].toLowerCase(Locale.ROOT);
        return !key.startsWith("utm_") && !Set.of("fbclid", "gclid").contains(key);
    }

    private static void add(Set<Key> keys, String namespace, String source, String raw) {
        String value = text(raw);
        if (value != null) keys.add(new Key(namespace, source, value));
    }
}
