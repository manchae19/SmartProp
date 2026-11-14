package vn.smartprop.modules.prediction;

import com.fasterxml.jackson.databind.*;
import java.math.BigDecimal;
import java.util.*;
import org.junit.jupiter.api.*;
import org.mockito.ArgumentCaptor;
import vn.smartprop.modules.auth.AccountAccess;
import vn.smartprop.modules.property.Property;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class ValuationServiceTest {
    final ObjectMapper json = new ObjectMapper();
    final AccountAccess access = mock(AccountAccess.class);
    final ValuationClient client = mock(ValuationClient.class);
    final ValuationService service = new ValuationService(access, client);

    @BeforeEach
    void options() throws Exception {
        when(client.exchange(eq("/model/options"), nullable(Object.class))).thenReturn(json.readTree("""
            {"model_version":"v6","model_run":"b4b1339d3f35857e","categories":[
              {"category":"Nhà ở","locations":["Hải Châu"]},
              {"category":"Đất nền","locations":["Hải Châu"]},
              {"category":"Căn hộ chung cư","locations":["Hải Châu"]}]}
            """));
        when(client.exchange(eq("/predict"), any())).thenReturn(json.readTree("""
            {"model_version":"v6","model_run":"b4b1339d3f35857e","configuration":"all","category":"Nhà ở",
             "predicted_asking_price_vnd":3000000000,"predicted_asking_price_million":3000,
             "currency":"VND","price_basis":"Giá rao tham khảo",
             "features_used":{"area_sqm":80,"location_feature":"Hải Châu","ward_source":null,"rooms":3,
               "floors":null,"access_type":null,"house_subtype":null},
             "missing_features":[],"warnings":[]}
            """));
    }

    @Test
    void optionalRealMeasurementsAreForwardedWithoutDefaults() throws Exception {
        var request = new ValuationRequest(Property.Type.HOUSE, Property.Transaction.SALE,
            new BigDecimal("80"), "Hải Châu", "Hải Châu 1", 3, "", "",
            new BigDecimal("7.5"), new BigDecimal("4.5"), "Nguyễn Văn Linh", "Dự án A", 2,
            "Đông Nam", "Tây Bắc");
        var preview = service.preview(42L, request);
        assertTrue(preview.available());
        ArgumentCaptor<Object> captor = ArgumentCaptor.forClass(Object.class);
        verify(client).exchange(eq("/predict"), captor.capture());
        JsonNode input = json.valueToTree(captor.getValue());
        assertEquals(7.5, input.path("road_width_m").asDouble());
        assertEquals(4.5, input.path("frontage_width_m").asDouble());
        assertEquals("Nguyễn Văn Linh", input.path("street_name").asText());
        assertEquals("Dự án A", input.path("project_name").asText());
        assertEquals(2, input.path("bathrooms").asInt());
        assertEquals("Đông Nam", input.path("house_direction").asText());
        assertEquals("Tây Bắc", input.path("balcony_direction").asText());
    }

    @Test
    void absentRealMeasurementsAreNotSynthesized() throws Exception {
        var request = new ValuationRequest(Property.Type.HOUSE, Property.Transaction.SALE,
            new BigDecimal("80"), "Hải Châu", null, null, "", "", null, null, null, null, null, null, null);
        service.preview(42L, request);
        ArgumentCaptor<Object> captor = ArgumentCaptor.forClass(Object.class);
        verify(client).exchange(eq("/predict"), captor.capture());
        JsonNode input = json.valueToTree(captor.getValue());
        for (String field : List.of("road_width_m", "frontage_width_m", "street_name", "project_name",
                                    "bathrooms", "house_direction", "balcony_direction")) {
            assertFalse(input.has(field), field);
        }
    }
}
