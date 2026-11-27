package vn.smartprop.modules.news;

import org.springframework.stereotype.Component;
import org.springframework.core.env.Environment;


import vn.smartprop.database.MigrationProfileEnvironmentGuard;

/** Standard V23 deliberately has no News schema. Never query those tables there. */
@Component
public class NewsSchemaAvailability {
    private final boolean available;
    public NewsSchemaAvailability(Environment environment) {
        available = !java.util.List.of(environment.getActiveProfiles())
            .contains(MigrationProfileEnvironmentGuard.STANDARD);
    }
    public void requireAvailable() {
        if (!available) throw new vn.smartprop.common.ApiException(503, "NEWS_SCHEMA_UNAVAILABLE",
            "News schema is unavailable on Standard V23");
    }
}
