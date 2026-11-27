package vn.smartprop.modules.news;

import org.junit.jupiter.api.Test;
import org.springframework.mock.env.MockEnvironment;
import static org.junit.jupiter.api.Assertions.*;

class NewsStandardSchemaTest {
    org.hibernate.mapping.Table table(String name) {
        var table=org.mockito.Mockito.mock(org.hibernate.mapping.Table.class);
        org.mockito.Mockito.when(table.getName()).thenReturn(name);return table;
    }
    @Test void standardProfileFailsClosedBeforeNewsQueries() {
        var env=new MockEnvironment();env.setActiveProfiles("standard-migrations");
        var error=assertThrows(vn.smartprop.common.ApiException.class,()->new NewsSchemaAvailability(env).requireAvailable());
        assertEquals(503,error.status);assertEquals("NEWS_SCHEMA_UNAVAILABLE",error.code);
    }
    @Test void standardStillValidatesEveryNonNewsTable() {
        var provider=new vn.smartprop.database.StandardNewsSchemaConfiguration.NewsFilterProvider();
        for(String name:new String[]{"news_sources","news_articles","news_ingestion_runs"})
            assertFalse(provider.getValidateFilter().includeTable(table(name)));
        for(String name:new String[]{"properties","users","external_listings"})
            assertTrue(provider.getValidateFilter().includeTable(table(name)));
    }
}
