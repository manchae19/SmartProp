package vn.smartprop.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Clock;
import java.time.Instant;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicLong;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import vn.smartprop.common.ApiException;
import vn.smartprop.common.Errors;
import vn.smartprop.common.RequestLimits;
import vn.smartprop.modules.auth.AccountAccess;
import vn.smartprop.modules.auth.AuthSession;
import vn.smartprop.modules.auth.RefreshController;
import vn.smartprop.modules.auth.RefreshService;
import vn.smartprop.modules.auth.SessionPolicy;
import vn.smartprop.modules.auth.SessionRepository;
import vn.smartprop.modules.auth.google.GoogleFlowStore;
import vn.smartprop.modules.auth.google.GoogleLinkController;
import vn.smartprop.modules.auth.google.GoogleLinkFlowStore;
import vn.smartprop.modules.auth.google.GoogleLinkService;
import vn.smartprop.modules.auth.google.GoogleOAuthConfigurer;
import vn.smartprop.modules.auth.google.GoogleSettings;
import vn.smartprop.modules.user.User;
import vn.smartprop.modules.user.UserRepository;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(controllers = GoogleLinkController.class)
@Import({SecurityConfig.class, Errors.class, AccountAccess.class, SessionPolicy.class,
    RefreshController.class, GoogleOAuthConfigurer.class, GoogleFlowStore.class, GoogleSettings.class,
    GoogleLinkHttpSecurityTest.Beans.class})
@TestPropertySource(properties = {
    "app.jwt-secret=pr40-fixture-key-with-at-least-32-utf8-bytes",
    "app.cors-origins=http://127.0.0.1:5173",
    "app.refresh.enabled=true",
    "app.google.enabled=true",
    "app.google.client-id=pr40-fixture.apps.googleusercontent.com",
    "app.google.client-secret=fixture-only",
    "app.refresh.secure-cookie=false"
})
class GoogleLinkHttpSecurityTest {
    private static final String ORIGIN = "http://127.0.0.1:5173";
    private static final String LINK = "/api/v1/auth/google/link";
    private static final String BODY = "{\"currentPassword\":\"wrong-fixture\"}";
    @Autowired MockMvc mvc;
    @Autowired JwtEncoder encoder;
    @Autowired ObjectMapper json;
    @MockitoBean UserRepository users;
    @MockitoBean SessionRepository sessions;
    @MockitoBean GoogleLinkService service;
    @MockitoBean GoogleLinkFlowStore flows;
    @MockitoBean RefreshService refresh;
    private static final AtomicLong TEST_USER_IDS = new AtomicLong(40L);
    private String bearer;
    private User actor;
    @Autowired CounterClock counterClock;

    static final class CounterClock extends Clock {
        private Instant instant = Instant.now();
        void advanceSeconds(long seconds) { instant = instant.plusSeconds(seconds); }
        @Override public java.time.ZoneId getZone() { return java.time.ZoneOffset.UTC; }
        @Override public Clock withZone(java.time.ZoneId zone) { return Clock.fixed(instant, zone); }
        @Override public Instant instant() { return instant; }
    }

    @TestConfiguration
    static class Beans {
        @Bean @org.springframework.context.annotation.Primary Clock clock() { return Clock.systemUTC(); }
        @Bean LoginThrottle loginThrottle(ObjectMapper mapper) { return new LoginThrottle(mapper); }
        @Bean CounterClock counterClock() { return new CounterClock(); }
        @Bean RequestLimits requestLimits(CounterClock clock) { return new RequestLimits(clock); }
    }

    @BeforeEach void fixtureSession() {
        User user = new User();
        user.id = TEST_USER_IDS.incrementAndGet();
        user.role = User.Role.BUYER;
        user.status = User.Status.ACTIVE;
        user.tokenVersion = 1;
        when(users.findById(user.id)).thenReturn(Optional.of(user));
        actor = user;
        bearer = issueToken(user);
        when(refresh.enabled()).thenReturn(true);
    }

    private String issueToken(User user) {
        AuthSession session = new AuthSession();
        session.id = java.util.UUID.randomUUID().toString();
        session.userId = user.id;
        session.createdAt = session.lastUsedAt = Instant.now().minusSeconds(20);
        session.expiresAt = Instant.now().plusSeconds(1800);
        when(sessions.findById(session.id)).thenReturn(Optional.of(session));
        var claims = JwtClaimsSet.builder().issuer("smartprop").subject(user.id.toString()).id(session.id)
            .claim("ver", 1).issuedAt(Instant.now().minusSeconds(5)).expiresAt(Instant.now().plusSeconds(600)).build();
        return "Bearer " + encoder.encode(JwtEncoderParameters.from(JwsHeader.with(MacAlgorithm.HS256).build(), claims)).getTokenValue();
    }

    private org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder protectedPost(String path) throws Exception {
        var response = mvc.perform(get("/api/v1/auth/csrf").header("Origin", ORIGIN))
            .andExpect(status().isOk()).andReturn().getResponse();
        var token = json.readTree(response.getContentAsString());
        return post(path).cookie(response.getCookie("XSRF-TOKEN"))
            .header(token.get("headerName").asText(), token.get("token").asText());
    }

    @Test void requiresAuthenticationAndCsrfForLinking() throws Exception {
        mvc.perform(get(LINK + "/status")).andExpect(status().isUnauthorized());
        mvc.perform(protectedPost(LINK + "/start").contentType(MediaType.APPLICATION_JSON).content(BODY))
            .andExpect(status().isUnauthorized());
        mvc.perform(post(LINK + "/start").header("Origin", ORIGIN).header("Authorization", bearer)
            .contentType(MediaType.APPLICATION_JSON).content(BODY)).andExpect(status().isForbidden());
        mvc.perform(post(LINK + "/complete").header("Origin", ORIGIN).header("Authorization", bearer))
            .andExpect(status().isForbidden());
        verifyNoInteractions(flows);
    }

    @Test void rejectsForeignOriginBeforeReadingTicket() throws Exception {
        mvc.perform(protectedPost(LINK + "/complete").header("Origin", "https://foreign.example")
            .header("Authorization", bearer)).andExpect(status().isForbidden());
        verifyNoInteractions(flows);
    }

    @Test void expiredTicketPreservesValidSession() throws Exception {
        when(flows.consumeTicket(any(), any(), any(), any())).thenThrow(new ApiException(410, "GOOGLE_LINK_EXPIRED", "Expired"));
        when(service.status(any())).thenReturn(new GoogleLinkService.Status(false));
        mvc.perform(protectedPost(LINK + "/complete").header("Origin", ORIGIN).header("Authorization", bearer))
            .andExpect(status().isGone()).andExpect(jsonPath("$.code").value("GOOGLE_LINK_EXPIRED"));
        mvc.perform(get(LINK + "/status").header("Authorization", bearer)).andExpect(status().isOk());
    }

    @Test void wrongPasswordLeavesSessionAndCreatesNoFlow() throws Exception {
        when(service.begin(any(), eq("wrong-fixture"))).thenThrow(new ApiException(400, "WRONG_PASSWORD", "Wrong password"));
        when(service.status(any())).thenReturn(new GoogleLinkService.Status(false));
        mvc.perform(protectedPost(LINK + "/start").header("Origin", ORIGIN).header("Authorization", bearer)
            .contentType(MediaType.APPLICATION_JSON).content(BODY))
            .andExpect(status().isBadRequest()).andExpect(jsonPath("$.code").value("WRONG_PASSWORD"))
            .andExpect(result -> assertTrue(result.getResponse().getHeaders("Set-Cookie").stream()
                .noneMatch(cookie -> cookie.startsWith("SMARTPROP_REFRESH="))))
            .andExpect(header().doesNotExist("Location"));
        mvc.perform(get(LINK + "/status").header("Authorization", bearer))
            .andExpect(status().isOk()).andExpect(jsonPath("$.linked").value(false));
        verifyNoInteractions(flows);
    }

    @Test void limitsPasswordConfirmationAndCompletionIndependently() throws Exception {
        when(service.begin(any(), eq("wrong-fixture")))
            .thenThrow(new ApiException(400, "WRONG_PASSWORD", "Wrong password"));
        when(flows.consumeTicket(any(), any(), any(), any()))
            .thenThrow(new ApiException(410, "GOOGLE_LINK_EXPIRED", "Expired"));
        for (int attempt = 0; attempt < 5; attempt++) {
            mvc.perform(protectedPost(LINK + "/start").header("Origin", ORIGIN).header("Authorization", bearer)
                .contentType(MediaType.APPLICATION_JSON).content(BODY)).andExpect(status().isBadRequest());
            mvc.perform(protectedPost(LINK + "/complete").header("Origin", ORIGIN).header("Authorization", bearer))
                .andExpect(status().isGone());
        }
        mvc.perform(protectedPost(LINK + "/start").header("Origin", ORIGIN).header("Authorization", bearer)
            .contentType(MediaType.APPLICATION_JSON).content(BODY))
            .andExpect(status().isTooManyRequests()).andExpect(header().exists("Retry-After"));
        mvc.perform(protectedPost(LINK + "/complete").header("Origin", ORIGIN).header("Authorization", bearer))
            .andExpect(status().isTooManyRequests()).andExpect(header().string("Retry-After", "300"));
        String secondSession = issueToken(actor);
        mvc.perform(protectedPost(LINK + "/start").header("Origin", ORIGIN).header("Authorization", secondSession)
            .contentType(MediaType.APPLICATION_JSON).content(BODY))
            .andExpect(status().isTooManyRequests()).andExpect(header().string("Retry-After", "300"));
        counterClock.advanceSeconds(300);
        mvc.perform(protectedPost(LINK + "/start").header("Origin", ORIGIN).header("Authorization", secondSession)
            .contentType(MediaType.APPLICATION_JSON).content(BODY)).andExpect(status().isBadRequest());
        mvc.perform(protectedPost(LINK + "/complete").header("Origin", ORIGIN).header("Authorization", bearer))
            .andExpect(status().isGone());
    }

    @Test void limitsAuthorizationAndKeepsCallbackDestinationFixed() throws Exception {
        String callback = "/api/v1/auth/oauth2/callback/google";
        mvc.perform(get(callback + "/extra")).andExpect(status().isUnauthorized());
        mvc.perform(get(callback).param("returnTo", "https://foreign.example"))
            .andExpect(status().is3xxRedirection()).andExpect(header().string("Location", ORIGIN + "/login?reason=google-failed"));
        String authorize = "/api/v1/auth/oauth2/link/authorize/google";
        for (int attempt = 0; attempt < 10; attempt++) {
            mvc.perform(get(authorize)).andExpect(status().isUnauthorized());
        }
        mvc.perform(get(authorize)).andExpect(status().isTooManyRequests()).andExpect(header().string("Retry-After", "60"));
        counterClock.advanceSeconds(60);
        mvc.perform(get(authorize)).andExpect(status().isUnauthorized());
    }

}
