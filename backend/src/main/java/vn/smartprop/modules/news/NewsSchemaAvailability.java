package vn.smartprop.modules.news;

import org.springframework.stereotype.Component;

/** Standard V23 deliberately has no News schema. Never query those tables there. */
@Component
public class NewsSchemaAvailability {
    private final boolean available;
    public NewsSchemaAvailability(vn.smartprop.database.NewsSchemaCapabilities capability) {
        available = capability.newsEnabled();
    }
    public void requireAvailable() {
        if (!available) throw new vn.smartprop.common.ApiException(503, "NEWS_SCHEMA_UNAVAILABLE",
            "News schema is unavailable on Standard V23");
    }
}
