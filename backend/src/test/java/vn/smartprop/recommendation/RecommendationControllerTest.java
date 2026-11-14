package vn.smartprop.modules.recommendation;
import vn.smartprop.security.SecurityConfig;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import vn.smartprop.modules.auth.*;
import vn.smartprop.common.*;
import vn.smartprop.config.*;
import vn.smartprop.modules.user.UserRepository;
import java.util.List;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import org.springframework.security.core.authority.SimpleGrantedAuthority;

@WebMvcTest(controllers=RecommendationController.class,properties={
 "app.jwt-secret=synthetic-test-secret-never-used-outside-tests-1234",
 "app.recommendation.demo-key=fixture-test-demo-key",
 "spring.jackson.deserialization.fail-on-unknown-properties=true"})
@Import({SecurityConfig.class,ThrottleConfig.class,Errors.class,AuthClockConfig.class})
class RecommendationControllerTest {
    @Test void tinixResearchRequiresFeatureAdminLoopbackAndPrivateServerKey() throws Exception {
        String path=PATH+"/research";
        mvc.perform(post(path).contentType("application/json").content(INPUT)).andExpect(status().isUnauthorized());
        for(String role:List.of("ROLE_BUYER","ROLE_BROKER"))mvc.perform(post(path).with(jwt().authorities(new SimpleGrantedAuthority(role)))
            .contentType("application/json").content(INPUT)).andExpect(status().isForbidden());
        var admin=jwt().authorities(new SimpleGrantedAuthority("ROLE_ADMIN"));
        mvc.perform(post(path).with(admin).contentType("application/json").content(INPUT)).andExpect(status().isForbidden());
        when(service.tinixEnabled()).thenReturn(true);
        mvc.perform(post(path).with(admin).with(r->{r.setRemoteAddr("127.0.0.1");return r;}).contentType("application/json").content(INPUT)).andExpect(status().isForbidden());
        mvc.perform(post(path).with(admin).with(r->{r.setRemoteAddr("127.0.0.1");return r;}).header("X-SmartProp-Demo-Key","wrong")
            .contentType("application/json").content(INPUT)).andExpect(status().isForbidden());
        mvc.perform(post(path).with(admin).with(r->{r.setRemoteAddr("192.0.2.1");return r;}).header("X-SmartProp-Demo-Key","fixture-test-demo-key")
            .contentType("application/json").content(INPUT)).andExpect(status().isForbidden());
        mvc.perform(post(path).with(admin).with(r->{r.setRemoteAddr("127.0.0.1");return r;}).header("X-SmartProp-Demo-Key","fixture-test-demo-key")
            .contentType("application/json").content(INPUT)).andExpect(status().isOk());
        verify(service,times(1)).recommendResearch(any());
    }
    @Test void arbitraryBudgetIsDeserializedWithoutRounding() throws Exception {
        for(String value:List.of("750000000","1250000000","2350000001","3780000000","4650000000","8900000000","15500000000","999999999999999")) {
            mvc.perform(post(PATH).contentType("application/json").content(INPUT.replace("2000000000",value))).andExpect(status().isOk());
            verify(service).recommend(argThat(r->r.budgetVnd().equals(new java.math.BigDecimal(value))));
        }
    }
    @Test void missingNegativeNonNumericAndOverMaximumBudgetsFail() throws Exception {
        for(String value:List.of("null","-1","0","1000000000000000","\"bad\""))
            mvc.perform(post(PATH).contentType("application/json").content(INPUT.replace("2000000000",value))).andExpect(status().isBadRequest());
        verifyNoInteractions(service);
    }
    @Autowired MockMvc mvc;
    @MockitoBean HybridRecommendationService service;
    @MockitoBean RequestLimits limits;
    @MockitoBean SessionRepository sessions;
    @MockitoBean UserRepository users;
    @MockitoBean SessionPolicy sessionPolicy;
    static final String PATH="/api/v1/recommendations";
    static final String INPUT="{\"budgetVnd\":2000000000,\"purpose\":\"LIVING\",\"propertyType\":\"ALL\",\"limit\":10}";
    @Test void newerAccountAndAdminRoutesStayProtected() throws Exception {
        for(String path:List.of("/api/v1/admin/users","/api/v1/users/me/avatar/content","/api/v1/users/me/valuation-history","/api/v1/users/me/broker-application"))
            mvc.perform(get(path)).andExpect(status().isUnauthorized());
        mvc.perform(post("/api/v1/users/me/broker-application").contentType("application/json").content("{}"))
            .andExpect(status().isUnauthorized());
        verifyNoInteractions(service);
    }
    @Test void safeRequestWorksWithoutAccountAndDoesNotCache() throws Exception {
        when(service.recommend(any())).thenReturn(new RecommendationDtos.Response("HEURISTIC_V1","SAFE","ASKING_SALE_VND_TOTAL",null,0,List.of(),List.of(),List.of()));
        mvc.perform(post(PATH).contentType("application/json").content(INPUT)).andExpect(status().isOk())
            .andExpect(header().string("Cache-Control","no-store")).andExpect(jsonPath("$.topProperties").isEmpty());
    }
    @Test void demoWithoutPrivateKeyIsForbidden() throws Exception {
        when(service.internalDemo()).thenReturn(true);
        mvc.perform(post(PATH).contentType("application/json").content(INPUT)).andExpect(status().isForbidden());
        verify(service,never()).recommend(any());
    }
    @Test void demoRequiresLoopbackAndPrivateKey() throws Exception {
        when(service.internalDemo()).thenReturn(true);
        mvc.perform(post(PATH).with(jwt().authorities(new SimpleGrantedAuthority("ROLE_ADMIN"))).with(r->{r.setRemoteAddr("192.0.2.1");return r;})
            .header("X-SmartProp-Demo-Key","fixture-test-demo-key").contentType("application/json").content(INPUT)).andExpect(status().isForbidden());
        mvc.perform(post(PATH).with(jwt().authorities(new SimpleGrantedAuthority("ROLE_ADMIN"))).with(r->{r.setRemoteAddr("127.0.0.1");return r;})
            .header("X-SmartProp-Demo-Key","fixture-test-demo-key").contentType("application/json").content(INPUT)).andExpect(status().isOk());
        verify(service,times(1)).recommend(any());
    }
    @Test void demoKeyAloneAndOrdinaryAccountsNeverUnlockCrawler() throws Exception {
        when(service.internalDemo()).thenReturn(true);
        mvc.perform(post(PATH).with(r->{r.setRemoteAddr("127.0.0.1");return r;})
            .header("X-SmartProp-Demo-Key","fixture-test-demo-key").contentType("application/json").content(INPUT)).andExpect(status().isForbidden());
        for(String role:List.of("ROLE_BUYER","ROLE_BROKER"))
            mvc.perform(post(PATH).with(jwt().authorities(new SimpleGrantedAuthority(role))).with(r->{r.setRemoteAddr("127.0.0.1");return r;})
                .header("X-SmartProp-Demo-Key","fixture-test-demo-key").contentType("application/json").content(INPUT)).andExpect(status().isForbidden());
        mvc.perform(post(PATH).with(jwt().authorities(new SimpleGrantedAuthority("ROLE_ADMIN"))).with(r->{r.setRemoteAddr("127.0.0.1");return r;})
            .header("X-SmartProp-Demo-Key","wrong-key").contentType("application/json").content(INPUT)).andExpect(status().isForbidden());
        verify(service,never()).recommend(any());
    }
    @Test void invalidBudgetLimitEnumOrUnknownFieldIsRejected() throws Exception {
        for(String body:List.of(INPUT.replace("2000000000","0"),INPUT.replace("\"limit\":10","\"limit\":11"),
            INPUT.replace("LIVING","OTHER"),INPUT.replace("\"limit\":10","\"source\":\"crawler\"")))
            mvc.perform(post(PATH).contentType("application/json").content(body)).andExpect(status().isBadRequest());
        verify(service,never()).recommend(any());
    }
}
