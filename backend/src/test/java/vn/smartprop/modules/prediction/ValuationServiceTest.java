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
    final ValuationService service = new ValuationService(access, client, "v1.3");

    @BeforeEach
    void options() throws Exception {
        when(client.exchange(eq("/model/options"), nullable(Object.class))).thenReturn(json.readTree("""
            {"model_version":"v1.3","model_run":"tinix_xgboost_v1_3_integrated","categories":[
              {"category":"Nhà ở","locations":["Hải Châu"]},
              {"category":"Đất nền","locations":["Hải Châu"]},
              {"category":"Căn hộ chung cư","locations":["Hải Châu"]}]}
            """));
        when(client.exchange(eq("/predict"), any())).thenReturn(json.readTree("""
            {"model_version":"v1.3","predicted_asking_price_vnd":3100000000,
             "predicted_asking_price_billion":3.1,"price_band":"3.0-3.2 ty",
             "calibration_factor":1.02,"calibration_policy":"isotonic","naive_price_vnd":3000000000,
             "features_used":{"area":80,"district":"Hải Châu","bedroom_count":3},
             "missing_features":[],"shap_explanation":null}
            """));
    }

    @Test
    void optionsReportTheVersionTheServiceActuallyServes() throws Exception {
        var options = service.options(42L);
        assertEquals("v1.3", options.modelVersion());
        assertEquals("tinix_xgboost_v1_3_integrated", options.modelRun());
        assertEquals(3, options.categories().size());
    }

    @Test
    void aPreviewReportsV13AndItsPrice() throws Exception {
        var request = new ValuationRequest(Property.Type.HOUSE, Property.Transaction.SALE,
            new BigDecimal("80"), "Hải Châu", null, 3, "", "", null, null, null, null, null, null, null, null, null);
        var preview = service.preview(42L, request);
        assertTrue(preview.available());
        assertEquals("v1.3", preview.modelVersion());
        assertEquals("3100000000", preview.predictedAskingPriceVnd());
        verify(client).exchange(eq("/predict"), any());
    }

    @Test
    void optionalRealMeasurementsAreForwardedWithoutDefaults() throws Exception {
        var request = new ValuationRequest(Property.Type.HOUSE, Property.Transaction.SALE,
            new BigDecimal("80"), "Hải Châu", "Hải Châu 1", 3, "", "",
            new BigDecimal("7.5"), new BigDecimal("4.5"), "Nguyễn Văn Linh", "Dự án A", 2,
            "Đông Nam", "Tây Bắc", null, null);
        service.preview(42L, request);
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
            new BigDecimal("80"), "Hải Châu", null, null, "", "", null, null, null, null, null, null, null, null, null);
        service.preview(42L, request);
        ArgumentCaptor<Object> captor = ArgumentCaptor.forClass(Object.class);
        verify(client).exchange(eq("/predict"), captor.capture());
        JsonNode input = json.valueToTree(captor.getValue());
        for (String field : List.of("road_width_m", "frontage_width_m", "street_name", "project_name",
                                    "bathrooms", "house_direction", "balcony_direction")) {
            assertFalse(input.has(field), field);
        }
    }

    @Test
    void theBathroomCountReachesTheModelInput() throws Exception {
        when(client.exchange(eq("/predict"), any())).thenReturn(json.readTree("""
            {"model_version":"v1.3","predicted_asking_price_vnd":3100000000,
             "features_used":{"area":80,"bathroom_count":2},"missing_features":[]}
            """));
        var request = new ValuationRequest(Property.Type.HOUSE, Property.Transaction.SALE,
            new BigDecimal("80"), "Hải Châu", null, 3, "", "", null, null, null, null, 2, null, null, null, null);
        var preview = service.preview(42L, request);
        assertEquals(2, preview.featuresUsed().get("bathrooms"));
    }

    @Test
    void anUnavailableModelLeavesThePreviewUnavailableInsteadOfFailing() throws Exception {
        when(client.exchange(eq("/predict"), any())).thenThrow(ValuationClient.unavailable());
        var request = new ValuationRequest(Property.Type.HOUSE, Property.Transaction.SALE,
            new BigDecimal("80"), "Hải Châu", null, 3, "", "", null, null, null, null, null, null, null, null, null);
        var preview = service.preview(42L, request);
        assertFalse(preview.available(), "nguoi dung van luu duoc tin");
        assertNotNull(preview.reason());
    }

    @Test
    void aResponseThatIsNotVersionedV13IsRejected() throws Exception {
        when(client.exchange(eq("/predict"), any())).thenReturn(json.readTree("""
            {"model_version":"v6","predicted_asking_price_vnd":3000000000,
             "features_used":{"area":80}}
            """));
        var request = new ValuationRequest(Property.Type.HOUSE, Property.Transaction.SALE,
            new BigDecimal("80"), "Hải Châu", null, 3, "", "", null, null, null, null, null, null, null, null, null);
        assertThrows(vn.smartprop.common.ApiException.class, () -> service.preview(42L, request));
    }

    @Test
    void anAreaMismatchIsRejected() throws Exception {
        when(client.exchange(eq("/predict"), any())).thenReturn(json.readTree("""
            {"model_version":"v1.3","predicted_asking_price_vnd":3100000000,
             "features_used":{"area":99},"missing_features":[]}
            """));
        var request = new ValuationRequest(Property.Type.HOUSE, Property.Transaction.SALE,
            new BigDecimal("80"), "Hải Châu", null, 3, "", "", null, null, null, null, null, null, null, null, null);
        assertThrows(vn.smartprop.common.ApiException.class, () -> service.preview(42L, request));
    }
    @Test
    void floorsAndSubtypeAreForwardedForAHouse() throws Exception {
        var request = new ValuationRequest(Property.Type.HOUSE, Property.Transaction.SALE,
            new BigDecimal("80"), "Hải Châu", null, 3, "", "", null, null, null, null, null, null, null, 3, "house_c4");
        service.preview(42L, request);
        ArgumentCaptor<Object> captor = ArgumentCaptor.forClass(Object.class);
        verify(client).exchange(eq("/predict"), captor.capture());
        JsonNode input = json.valueToTree(captor.getValue());
        assertEquals(3, input.path("floors").asInt());
        assertEquals("house_c4", input.path("house_subtype").asText());
    }

    @Test
    void villaAlwaysKeepsTheVillaSubtypeEvenWhenAnotherIsSent() throws Exception {
        var request = new ValuationRequest(Property.Type.VILLA, Property.Transaction.SALE,
            new BigDecimal("80"), "Hải Châu", null, 4, "", "", null, null, null, null, null, null, null, 2, "house_c4");
        service.preview(42L, request);
        ArgumentCaptor<Object> captor = ArgumentCaptor.forClass(Object.class);
        verify(client).exchange(eq("/predict"), captor.capture());
        assertEquals("villa", json.valueToTree(captor.getValue()).path("house_subtype").asText());
    }

    @Test
    void floorsAndSubtypeAreDroppedForAnApartment() throws Exception {
        var request = new ValuationRequest(Property.Type.APARTMENT, Property.Transaction.SALE,
            new BigDecimal("80"), "Hải Châu", null, 2, "", "", null, null, null, null, null, null, null, 5, "house_c4");
        service.preview(42L, request);
        ArgumentCaptor<Object> captor = ArgumentCaptor.forClass(Object.class);
        verify(client).exchange(eq("/predict"), captor.capture());
        JsonNode input = json.valueToTree(captor.getValue());
        assertFalse(input.has("floors"), "tầng căn hộ không phải tổng số tầng nhà");
        assertFalse(input.has("house_subtype"), "căn hộ không nhận kiểu nhà");
    }

    @Test
    void floorsAreDroppedForLand() throws Exception {
        var request = new ValuationRequest(Property.Type.LAND, Property.Transaction.SALE,
            new BigDecimal("80"), "Hải Châu", null, null, "", "", null, null, null, null, null, null, null, 3, null);
        service.preview(42L, request);
        ArgumentCaptor<Object> captor = ArgumentCaptor.forClass(Object.class);
        verify(client).exchange(eq("/predict"), captor.capture());
        assertFalse(json.valueToTree(captor.getValue()).has("floors"));
    }
}
