package vn.smartprop.modules.prediction;

import java.util.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.*;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import static org.junit.jupiter.api.Assertions.*;

@EnabledIfEnvironmentVariable(named="SMARTPROP_HISTORY_TEST_URL",matches="jdbc:mysql://127\\.0\\.0\\.1:13[0-9]{3}/smartprop_history_[a-z0-9]+.*")
@SpringBootTest(webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT)
class ValuationHistoryLiveTest {
    @Autowired TestRestTemplate http;
    @DynamicPropertySource static void localOnly(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url",()->System.getenv("SMARTPROP_HISTORY_TEST_URL"));
        registry.add("spring.datasource.username",()->"root");registry.add("spring.datasource.password",()->"");
        registry.add("app.jwt-secret",()->"synthetic-test-only-key-1234567890-no-production-use");
        registry.add("app.valuation.enabled",()->"true");
        registry.add("app.valuation.base-url",()->System.getenv("SMARTPROP_HISTORY_AI_URL"));
        registry.add("app.storage-root",()->"../.scratch/history-live-storage");
        registry.add("logging.level.root",()->"WARN");
    }
    String token() {
        String email="history-"+UUID.randomUUID()+"@example.test", password="SyntheticFixture123!";
        assertEquals(201,http.postForEntity("/api/v1/auth/register",Map.of("email",email,"password",password,"fullName","Synthetic history user","role","BUYER"),Map.class).getStatusCode().value());
        var response=http.postForEntity("/api/v1/auth/login",Map.of("email",email,"password",password),Map.class);
        assertEquals(200,response.getStatusCode().value());return (String)response.getBody().get("accessToken");
    }
    HttpHeaders headers(String token) {var headers=new HttpHeaders();headers.setBearerAuth(token);headers.setContentType(MediaType.APPLICATION_JSON);return headers;}
    @Test void realJwtDatabaseAndV6ModelCompleteTheHistoryFlow() {
        String owner=token(),other=token(),path="/api/v1/users/me/valuation-history";
        HttpHeaders headers=headers(owner);headers.set("Idempotency-Key",UUID.randomUUID().toString());
        var body=Map.of("category","Nhà ở","area_sqm",80,"location_feature","new_unit:hoa xuan","rooms",3,"floors",2,"access_type","alley");
        var saved=http.exchange(path,HttpMethod.POST,new HttpEntity<>(body,headers),Map.class);
        assertEquals(201,saved.getStatusCode().value(),()->String.valueOf(saved.getBody()));
        String id=(String)saved.getBody().get("id");
        Map<?,?> prediction=(Map<?,?>)saved.getBody().get("prediction");
        assertEquals("v6",prediction.get("model_version"));
        assertTrue(((Number)prediction.get("predicted_asking_price_vnd")).longValue()>0);
        var retry=http.exchange(path,HttpMethod.POST,new HttpEntity<>(body,headers),Map.class);
        assertEquals(id,retry.getBody().get("id"));
        var page=http.exchange(path,HttpMethod.GET,new HttpEntity<>(headers(owner)),Map.class);
        assertEquals(1,((Number)page.getBody().get("totalElements")).intValue());
        assertEquals(404,http.exchange(path+"/"+id,HttpMethod.GET,new HttpEntity<>(headers(other)),Map.class).getStatusCode().value());
        assertEquals(404,http.exchange(path+"/"+id,HttpMethod.DELETE,new HttpEntity<>(headers(other)),Map.class).getStatusCode().value());
        assertEquals(204,http.exchange(path+"/"+id,HttpMethod.DELETE,new HttpEntity<>(headers(owner)),Void.class).getStatusCode().value());
        assertEquals(404,http.exchange(path+"/"+id,HttpMethod.GET,new HttpEntity<>(headers(owner)),Map.class).getStatusCode().value());
    }
}
