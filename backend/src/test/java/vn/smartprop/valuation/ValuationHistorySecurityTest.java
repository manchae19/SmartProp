package vn.smartprop.valuation;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import vn.smartprop.auth.*;
import vn.smartprop.common.*;
import vn.smartprop.user.UserRepository;
import java.util.List;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(controllers=ValuationHistoryController.class,properties={
    "app.jwt-secret=synthetic-test-secret-never-used-outside-tests-1234",
    "app.cors-origins=http://127.0.0.1:5173",
    "spring.jackson.deserialization.fail-on-unknown-properties=true"})
@Import({SecurityConfig.class,ThrottleConfig.class,Errors.class})
class ValuationHistorySecurityTest {
    @Autowired MockMvc mvc;
    @MockitoBean ValuationHistoryService service;
    @MockitoBean RequestLimits limits;
    @MockitoBean SessionRepository sessions;
    @MockitoBean UserRepository users;
    static final String PATH="/api/v1/users/me/valuation-history";
    @Test void anonymousRequestsAreRejected() throws Exception {
        mvc.perform(get(PATH)).andExpect(status().isUnauthorized());
        mvc.perform(post(PATH).contentType("application/json").content("{}")).andExpect(status().isUnauthorized());
        mvc.perform(delete(PATH+"/10000000-0000-4000-8000-000000000001")).andExpect(status().isUnauthorized());
        verifyNoInteractions(service);
    }
    @Test void authenticatedBuyerReadsOnlyItsOwnNamespace() throws Exception {
        when(service.list(42L,0,20)).thenReturn(new PageResponse<>(List.of(),0,20,0,0));
        mvc.perform(get(PATH).with(jwt().jwt(j->j.subject("42")))).andExpect(status().isOk())
            .andExpect(header().string("Cache-Control","private, no-store"));
        verify(service).list(42L,0,20);
    }
    @Test void inputCannotContainAClientPrice() throws Exception {
        mvc.perform(post(PATH).with(jwt().jwt(j->j.subject("42"))).contentType("application/json")
            .content("{\"category\":\"Nhà ở\",\"area_sqm\":80,\"location_feature\":\"Hải Châu\",\"price\":1}"))
            .andExpect(status().isBadRequest());
        verifyNoInteractions(service);
    }
}
