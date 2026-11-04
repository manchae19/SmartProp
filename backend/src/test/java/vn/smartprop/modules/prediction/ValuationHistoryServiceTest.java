package vn.smartprop.modules.prediction;

import com.fasterxml.jackson.databind.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.*;
import org.junit.jupiter.api.*;
import org.springframework.dao.DataAccessResourceFailureException;
import vn.smartprop.modules.auth.AccountAccess;
import vn.smartprop.common.*;
import vn.smartprop.config.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class ValuationHistoryServiceTest {
    final ObjectMapper json=new ObjectMapper();
    final AccountAccess access=mock(AccountAccess.class);
    final ValuationClient client=mock(ValuationClient.class);
    final ValuationHistoryRepository repository=mock(ValuationHistoryRepository.class);
    final ValuationHistoryService service=new ValuationHistoryService(access,client,repository,json);
    final String key="10000000-0000-4000-8000-000000000001";
    HistoryInput input(){return new HistoryInput("Nhà ở",new BigDecimal("80"),"new_unit:hoa xuan",null,3,new BigDecimal("2"),"alley",null);}
    JsonNode value(String text) throws Exception{return json.readTree(text);}
    JsonNode prediction() throws Exception {
        return value("""
            {"model_version":"v6","model_run":"b4b1339d3f35857e","configuration":"all","category":"Nhà ở",
             "currency":"VND","predicted_asking_price_vnd":3000000000,"predicted_asking_price_million":3000,
             "price_basis":"Giá rao tham khảo",
             "features_used":{"area_sqm":80,"location_feature":"new_unit:hoa xuan","ward_source":null,"rooms":3,"floors":2,"access_type":"alley","house_subtype":null},
             "missing_features":["ward_source","house_subtype"],"warnings":[]}
            """);
    }
    @Test void serverPredictsAndStoresOneSnapshotThenReplaysTheSameKey() throws Exception {
        when(repository.byKey(42L,key)).thenReturn(Optional.empty());
        when(client.exchange(eq("/model/options"),isNull())).thenReturn(value("""
            {"model_version":"v6","model_run":"b4b1339d3f35857e","categories":[{"category":"Nhà ở","locations":["new_unit:hoa xuan"]}]}
            """));
        when(client.exchange(eq("/predict"),any())).thenReturn(prediction());
        doAnswer(invocation->{
            var entry=new ValuationHistoryRepository.Entry(key,Instant.now(),invocation.getArgument(3),invocation.getArgument(4));
            when(repository.byKey(42L,key)).thenReturn(Optional.of(new ValuationHistoryRepository.Stored(entry,invocation.getArgument(2))));
            return null;
        }).when(repository).insert(eq(42L),eq(key),anyString(),any(),any());
        var saved=service.save(42L,input(),key);
        assertEquals(3000000000L,saved.prediction().path("predicted_asking_price_vnd").asLong());
        assertEquals(saved,service.save(42L,input(),key));
        verify(client,times(1)).exchange(eq("/predict"),any());
        verify(repository,times(1)).insert(eq(42L),eq(key),anyString(),any(),any());
        var changed=new HistoryInput("Nhà ở",new BigDecimal("90"),"new_unit:hoa xuan",null,3,new BigDecimal("2"),"alley",null);
        assertEquals(409,assertThrows(ApiException.class,()->service.save(42L,changed,key)).status);
    }
    @Test void crossAccountDetailAndDeleteUseTheAuthenticatedOwner() {
        when(repository.byId(99L,key)).thenReturn(Optional.empty());
        assertEquals(404,assertThrows(ApiException.class,()->service.get(99L,key)).status);
        assertEquals(404,assertThrows(ApiException.class,()->service.delete(99L,key)).status);
        verify(repository).byId(99L,key);verify(repository).delete(99L,key);
    }
    @Test void databaseFailureDoesNotBecomeAnInventedHistoryResult() {
        when(repository.byKey(42L,key)).thenThrow(new DataAccessResourceFailureException("fixture database unavailable"));
        assertEquals(503,assertThrows(ApiException.class,()->service.save(42L,input(),key)).status);
        verifyNoInteractions(client);
    }
    @Test void unknownLocationAndWrongModelCannotBeStored() throws Exception {
        when(repository.byKey(42L,key)).thenReturn(Optional.empty());
        when(client.exchange(eq("/model/options"),isNull())).thenReturn(value("""
            {"model_version":"v6","model_run":"b4b1339d3f35857e","categories":[]}
            """));
        assertEquals(400,assertThrows(ApiException.class,()->service.save(42L,input(),key)).status);
        when(client.exchange(eq("/model/options"),isNull())).thenReturn(value("{\"model_version\":\"v7\"}"));
        assertEquals(503,assertThrows(ApiException.class,()->service.save(42L,input(),key)).status);
        verify(repository,never()).insert(any(),any(),any(),any(),any());
    }
    @Test void categoryMismatchIsRejectedBeforeTheModelIsCalled() {
        var invalid=new HistoryInput("Đất nền",new BigDecimal("80"),"Hải Châu",null,3,null,null,null);
        assertEquals(400,assertThrows(ApiException.class,()->service.save(42L,invalid,key)).status);
        verifyNoInteractions(client);
    }
    @Test void strictJsonDoesNotAcceptAClientPriceOrOwner() throws Exception {
        var strict=json.copy().enable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);
        assertThrows(Exception.class,()->strict.readValue("{\"category\":\"Nhà ở\",\"predicted_asking_price_vnd\":1}",HistoryInput.class));
        assertThrows(Exception.class,()->strict.readValue("{\"user_id\":99}",HistoryInput.class));
    }
}
