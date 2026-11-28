package vn.smartprop.modules.auth.google;

import static org.junit.jupiter.api.Assertions.*;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;
import jakarta.servlet.http.Cookie;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.oauth2.client.registration.InMemoryClientRegistrationRepository;
import org.springframework.security.oauth2.core.endpoint.OAuth2AuthorizationRequest;

class GoogleLinkFlowStoreTest {
    private MutableClock clock;
    private GoogleLinkFlowStore store;

    @BeforeEach void setUp() {
        clock = new MutableClock(Instant.parse("2026-11-24T00:00:00Z"));
        GoogleSettings settings = new GoogleSettings(false, "", "", "http://127.0.0.1:5173/api/v1/auth/oauth2/callback/google",
            "http://127.0.0.1:5173", false, "http://127.0.0.1:5173");
        store = new GoogleLinkFlowStore(clock, settings);
    }

    @Test void bindsStateToUserAndSessionAndConsumesHandoffOnce() {
        MockHttpServletResponse startResponse = new MockHttpServletResponse();
        store.begin(77L, "session-uuid", startResponse);
        String flowCookie = cookieValue(startResponse.getHeader("Set-Cookie"));
        assertTrue(startResponse.getHeader("Set-Cookie").contains("HttpOnly"));
        assertTrue(startResponse.getHeader("Set-Cookie").contains("SameSite=Lax"));

        String state = "oauth-state-once";
        OAuth2AuthorizationRequest authorization = authorization(state);
        MockHttpServletRequest authorizeRequest = request(flowCookie, null);
        store.save(authorization, authorizeRequest, new MockHttpServletResponse());
        assertSame(authorization, store.load(request(flowCookie, state)));

        var callback = request(flowCookie, state);
        assertSame(authorization, store.remove(callback, new MockHttpServletResponse()));
        MockHttpServletResponse ticketResponse = new MockHttpServletResponse();
        store.handoff(new GoogleProfile("google-subject", "person@example.test", "Person"), callback, ticketResponse);
        String ticketHeader = lastCookie(ticketResponse);
        String ticketCookie = cookieValue(ticketHeader);
        assertTrue(ticketHeader.contains("SameSite=Lax"));
        assertEquals(77L, store.consumeTicket(requestWithTicket(ticketCookie), new MockHttpServletResponse()).userId());
        assertThrows(RuntimeException.class, () -> store.consumeTicket(requestWithTicket(ticketCookie), new MockHttpServletResponse()));
    }

    @Test void rejectsStateMismatchAndExpiredFlow() {
        MockHttpServletResponse response = new MockHttpServletResponse();
        store.begin(9L, "jti", response);
        String raw = cookieValue(response.getHeader("Set-Cookie"));
        store.save(authorization("expected"), request(raw, null), new MockHttpServletResponse());
        assertNull(store.load(request(raw, "wrong")));
        clock.advanceSeconds(301);
        assertNull(store.load(request(raw, "expected")));
    }

    @Test void staleLinkCookieDoesNotRouteAnUnrelatedLoginCallbackIntoTheLinkFlow() {
        GoogleSettings settings = new GoogleSettings(false, "", "", "http://127.0.0.1:5173/api/v1/auth/oauth2/callback/google",
            "http://127.0.0.1:5173", false, "http://127.0.0.1:5173");
        GoogleLinkFlowStore linkStore = new GoogleLinkFlowStore(clock, settings);
        GoogleFlowStore router = new GoogleFlowStore(clock, settings, linkStore);
        MockHttpServletResponse response = new MockHttpServletResponse();
        linkStore.begin(12L, "bound-session", response);
        String linkCookie = cookieValue(response.getHeader("Set-Cookie"));
        OAuth2AuthorizationRequest linkRequest = authorization("link-state");
        router.saveAuthorizationRequest(linkRequest, request(linkCookie, null), new MockHttpServletResponse());

        OAuth2AuthorizationRequest loginRequest = OAuth2AuthorizationRequest.authorizationCode()
            .authorizationUri("https://accounts.google.com/o/oauth2/v2/auth").clientId("client-id")
            .redirectUri("http://127.0.0.1/callback").state("login-state")
            .authorizationRequestUri("https://accounts.google.com/o/oauth2/v2/auth?state=login-state").build();
        MockHttpServletRequest loginStart = new MockHttpServletRequest();
        MockHttpServletResponse loginSaved = new MockHttpServletResponse();
        router.saveAuthorizationRequest(loginRequest, loginStart, loginSaved);
        String loginCookie = cookieValue(loginSaved.getHeader("Set-Cookie"));

        MockHttpServletRequest callback = new MockHttpServletRequest();
        callback.setCookies(new Cookie("SMARTPROP_GOOGLE_LINK", linkCookie), new Cookie("SMARTPROP_GOOGLE_FLOW", loginCookie));
        callback.setParameter("state", "login-state");
        assertSame(loginRequest, router.loadAuthorizationRequest(callback));
        assertSame(loginRequest, router.removeAuthorizationRequest(callback, new MockHttpServletResponse()));
        assertFalse(router.isLinkCallbackFlow(callback));
    }

    @Test void linkAuthorizationUsesSeparateEndpointMarkerAndPkce() {
        GoogleSettings settings = new GoogleSettings(true, "client.apps.googleusercontent.com", "secret-not-logged",
            "http://127.0.0.1:5173/api/v1/auth/oauth2/callback/google", "http://127.0.0.1:5173", false,
            "http://127.0.0.1:5173");
        GoogleLinkFlowStore linkStore = new GoogleLinkFlowStore(clock, settings);
        GoogleFlowStore flowStore = new GoogleFlowStore(clock, settings, linkStore);
        GoogleOAuthConfigurer configurer = new GoogleOAuthConfigurer(settings, flowStore, linkStore,
            new vn.smartprop.common.RequestLimits(), clock, new ObjectMapper(),
            org.mockito.Mockito.mock(ObjectProvider.class), true);
        var resolver = configurer.resolver(new InMemoryClientRegistrationRepository(configurer.registration()));

        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setServletPath("/api/v1/auth/oauth2/link/authorize/google");
        request.setRequestURI("/api/v1/auth/oauth2/link/authorize/google");
        var authorization = resolver.resolve(request);
        assertNotNull(authorization);
        assertEquals("link", authorization.getAttribute("smartprop_flow"));
        assertTrue(authorization.getAdditionalParameters().containsKey("code_challenge"));
        assertEquals("S256", authorization.getAdditionalParameters().get("code_challenge_method"));
        assertNotNull(authorization.getAttributes().get("nonce"));
        assertNotNull(authorization.getAdditionalParameters().get("nonce"));
    }

    @Test void callbackTicketCannotBeReplayedConcurrently() throws Exception {
        MockHttpServletResponse response = new MockHttpServletResponse();
        store.begin(5L, "session", response);
        String flow = cookieValue(response.getHeader("Set-Cookie"));
        store.save(authorization("state"), request(flow, null), new MockHttpServletResponse());
        var callback = request(flow, "state");
        store.remove(callback, new MockHttpServletResponse());
        MockHttpServletResponse handoff = new MockHttpServletResponse();
        store.handoff(new GoogleProfile("sub", "p@example.test", "P"), callback, handoff);
        String ticket = cookieValue(lastCookie(handoff));

        CountDownLatch ready = new CountDownLatch(2), go = new CountDownLatch(1);
        AtomicInteger accepted = new AtomicInteger();
        Runnable completion = () -> {
            ready.countDown();
            try { go.await(); store.consumeTicket(requestWithTicket(ticket), new MockHttpServletResponse()); accepted.incrementAndGet(); }
            catch (RuntimeException ignored) { }
            catch (InterruptedException interrupted) { Thread.currentThread().interrupt(); }
        };
        Thread first = new Thread(completion), second = new Thread(completion);
        first.start(); second.start(); ready.await(); go.countDown(); first.join(); second.join();
        assertEquals(1, accepted.get());
    }

    @Test void preservesCallbackBindingOnlyInTheRequestThatConsumedIt() {
        var response = new MockHttpServletResponse();
        store.begin(5L, "session", response);
        String flow = cookieValue(response.getHeader("Set-Cookie"));
        var authorization = authorization("expected-state");
        store.save(authorization, request(flow, null), new MockHttpServletResponse());
        assertNull(store.remove(request(flow, null), new MockHttpServletResponse()));
        assertNull(store.remove(request(flow, "different-state"), new MockHttpServletResponse()));
        var callback = request(flow, "expected-state");
        assertSame(authorization, store.remove(callback, new MockHttpServletResponse()));
        var replay = request(flow, "expected-state");
        assertNull(store.remove(replay, new MockHttpServletResponse()));
        var profile = new GoogleProfile("subject", "fixture@example.test", "Fixture");
        assertThrows(vn.smartprop.common.ApiException.class, () -> store.handoff(profile, replay, new MockHttpServletResponse()));
        var handoff = new MockHttpServletResponse();
        store.handoff(profile, callback, handoff);
        clock.advanceSeconds(60);
        var error = assertThrows(vn.smartprop.common.ApiException.class,
            () -> store.consumeTicket(requestWithTicket(cookieValue(lastCookie(handoff))), new MockHttpServletResponse()));
        assertEquals(410, error.status);
    }

    private OAuth2AuthorizationRequest authorization(String state) {
        return OAuth2AuthorizationRequest.authorizationCode().authorizationUri("https://accounts.google.com/o/oauth2/v2/auth")
            .clientId("client-id").redirectUri("http://127.0.0.1/callback").state(state)
            .authorizationRequestUri("https://accounts.google.com/o/oauth2/v2/auth?state=" + state)
            .attributes(attributes -> attributes.put("smartprop_flow", "link")).build();
    }
    private MockHttpServletRequest request(String flow, String state) {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setCookies(new Cookie("SMARTPROP_GOOGLE_LINK", flow));
        if (state != null) request.setParameter("state", state);
        return request;
    }
    private MockHttpServletRequest requestWithTicket(String ticket) {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setCookies(new Cookie("SMARTPROP_GOOGLE_LINK_TICKET", ticket));
        return request;
    }
    private String cookieValue(String header) { return header.substring(header.indexOf('=') + 1, header.indexOf(';')); }
    private String lastCookie(MockHttpServletResponse response) {
        var headers = response.getHeaders("Set-Cookie");
        return headers.get(headers.size() - 1);
    }

    private static final class MutableClock extends Clock {
        private Instant now;
        MutableClock(Instant now) { this.now = now; }
        void advanceSeconds(long seconds) { now = now.plusSeconds(seconds); }
        @Override public ZoneId getZone() { return ZoneId.of("UTC"); }
        @Override public Clock withZone(ZoneId zone) { return this; }
        @Override public Instant instant() { return now; }
    }
}
