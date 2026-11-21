package vn.smartprop.modules.gis.geocoding;

import java.time.Clock;
import java.util.List;
import org.junit.jupiter.api.Test;
import vn.smartprop.common.RequestLimits;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * The scope echo tells the client whether a district query actually ran. A branch that
 * returns before reaching the provider must not claim one did.
 */
class GeocodingServiceScopeEchoTest {
    private final GeocodingProviderClient client = mock(GeocodingProviderClient.class);
    private final RequestLimits limits = mock(RequestLimits.class);
    private final GeocodingScopes scopes = new GeocodingScopes(new com.fasterxml.jackson.databind.ObjectMapper());

    private GeocodingService service(GeocodingDtos.Provider provider) {
        return new GeocodingService(client, limits, true, provider, "test-key", Clock.systemUTC(), scopes);
    }

    private static GeocodingDtos.Search search(String district, String ward, Boolean districtOnly) {
        return new GeocodingDtos.Search("123 Nguyễn Văn Linh, Phường Hòa Cường Bắc, Hải Châu, Đà Nẵng",
            "Da Nang", district, ward, true, districtOnly);
    }

    @Test
    void aProviderWithoutDistrictSearchReportsNoScope() {
        // The provider branch returns before any query, so the echo must stay empty.
        var result = service(GeocodingDtos.Provider.GOOGLE).search(42L, "127.0.0.1", search("Hải Châu", "Hòa Cường Bắc", true));
        assertEquals("SCOPE_UNAVAILABLE", result.status());
        assertNull(result.scope(), "chưa truy vấn thì không được báo phạm vi quận");
        assertTrue(result.candidates().isEmpty());
        verifyNoInteractions(client);
    }

    @Test
    void anUnresolvableScopeReportsNoScope() {
        // A ward with no historical polygon resolves to SCOPE_UNAVAILABLE before the query.
        var result = service(GeocodingDtos.Provider.GEOAPIFY).search(42L, "127.0.0.1", search("Hải Châu", "Hòa Cường Bắc", null));
        assertEquals("SCOPE_UNAVAILABLE", result.status());
        assertNull(result.scope(), "chưa truy vấn thì không được báo phạm vi quận");
        verifyNoInteractions(client);
    }

    @Test
    void aDistrictSearchThatRanReportsTheDistrictScope() {
        when(client.search(any(), anyString(), anyString(), any())).thenReturn(List.of());
        var result = service(GeocodingDtos.Provider.GEOAPIFY).search(42L, "127.0.0.1", search("Hải Châu", "Hòa Cường Bắc", true));
        assertEquals("ZERO_RESULTS", result.status());
        assertEquals("DISTRICT", result.scope(), "truy vấn theo quận đã chạy thì phải báo phạm vi quận");
        verify(client).search(any(), anyString(), anyString(), any());
    }

    @Test
    void aNormalSearchReportsTheCityScope() {
        when(client.search(any(), anyString(), anyString(), any())).thenReturn(List.of());
        // No ward in the address, so the normal search resolves to the whole city.
        var request = new GeocodingDtos.Search("123 Nguyễn Văn Linh, Hải Châu, Đà Nẵng",
            "Da Nang", "Hải Châu", null, true, null);
        var result = service(GeocodingDtos.Provider.GEOAPIFY).search(42L, "127.0.0.1", request);
        assertEquals("ZERO_RESULTS", result.status());
        assertEquals("CITY", result.scope());
    }
}
