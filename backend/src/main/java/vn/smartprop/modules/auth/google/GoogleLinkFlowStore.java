package vn.smartprop.modules.auth.google;

import java.time.Clock;
import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.ResponseCookie;
import org.springframework.security.oauth2.core.endpoint.OAuth2AuthorizationRequest;
import org.springframework.stereotype.Component;
import vn.smartprop.common.ApiException;
import vn.smartprop.modules.auth.SecretTokens;

/** Isolated, short-lived OAuth state for an authenticated Google account-linking flow. */
@Component
public class GoogleLinkFlowStore {
    private static final String FLOW_COOKIE = "SMARTPROP_GOOGLE_LINK";
    private static final String TICKET_COOKIE = "SMARTPROP_GOOGLE_LINK_TICKET";
    private static final String FLOW_ATTRIBUTE = "smartprop_flow";
    private static final int TTL_SECONDS = 300;

    public record Binding(long userId, String sessionId) {}
    public record Ticket(GoogleProfile profile, long userId, String sessionId) {}
    private static final class Pending {
        final Binding binding;
        final Instant expires;
        OAuth2AuthorizationRequest request;
        Pending(Binding binding, Instant expires) { this.binding = binding; this.expires = expires; }
    }
    private record Handoff(Ticket ticket, Instant expires) {}

    private final Clock clock;
    private final boolean secure;
    private final Map<String, Pending> pending = new HashMap<>();
    private final Map<String, String> stateHandles = new HashMap<>();
    private final Map<String, Handoff> handoffs = new HashMap<>();

    public GoogleLinkFlowStore(Clock clock, GoogleSettings settings) {
        this.clock = clock;
        this.secure = settings.secure;
    }

    private void prune() {
        Instant now = clock.instant();
        pending.entrySet().removeIf(entry -> !entry.getValue().expires.isAfter(now));
        stateHandles.entrySet().removeIf(entry -> !pending.containsKey(entry.getValue()));
        handoffs.entrySet().removeIf(entry -> !entry.getValue().expires.isAfter(now));
    }

    private String cookie(HttpServletRequest request, String name) {
        if (request.getCookies() != null) for (var cookie : request.getCookies())
            if (cookie.getName().equals(name) && cookie.getValue().matches("[A-Za-z0-9_-]{43}")) return cookie.getValue();
        return null;
    }

    private void setCookie(HttpServletResponse response, String name, String value, int seconds, String sameSite) {
        response.addHeader("Set-Cookie", ResponseCookie.from(name, value).httpOnly(true).secure(secure)
            .sameSite(sameSite).path("/api/v1/auth").maxAge(seconds).build().toString());
        response.setHeader("Cache-Control", "no-store");
        response.setHeader("Referrer-Policy", "no-referrer");
    }

    public synchronized void begin(long userId, String sessionId, HttpServletResponse response) {
        prune();
        if (pending.size() >= 1000) throw new ApiException(429, "RATE_LIMITED", "Vui lòng thử lại sau.");
        String raw = SecretTokens.random();
        pending.put(SecretTokens.hash(raw), new Pending(new Binding(userId, sessionId), clock.instant().plusSeconds(TTL_SECONDS)));
        setCookie(response, FLOW_COOKIE, raw, TTL_SECONDS, "Lax");
    }

    public synchronized boolean isLinkRequest(OAuth2AuthorizationRequest request) {
        return request != null && "link".equals(request.getAttribute(FLOW_ATTRIBUTE));
    }

    public synchronized boolean hasFlowCookie(HttpServletRequest request) {
        return cookie(request, FLOW_COOKIE) != null;
    }

    public synchronized boolean hasPendingStart(HttpServletRequest request) {
        prune();
        String raw = cookie(request, FLOW_COOKIE);
        Pending value = raw == null ? null : pending.get(SecretTokens.hash(raw));
        return value != null && value.request == null;
    }

    public synchronized boolean ownsState(HttpServletRequest request) {
        prune();
        String state = request.getParameter("state");
        String handle = state == null ? null : stateHandles.get(state);
        return handle != null && pending.containsKey(handle);
    }

    public synchronized OAuth2AuthorizationRequest load(HttpServletRequest request) {
        prune();
        String raw = cookie(request, FLOW_COOKIE);
        Pending value = raw == null ? null : pending.get(SecretTokens.hash(raw));
        if (value == null || value.request == null || !SecretTokens.equal(value.request.getState(), request.getParameter("state"))) return null;
        return value.request;
    }

    public synchronized void save(OAuth2AuthorizationRequest request, HttpServletRequest httpRequest, HttpServletResponse response) {
        prune();
        String raw = cookie(httpRequest, FLOW_COOKIE);
        Pending value = raw == null ? null : pending.get(SecretTokens.hash(raw));
        if (request == null || value == null || !isLinkRequest(request)) {
            if (value != null) pending.remove(SecretTokens.hash(raw));
            clearFlow(response);
            return;
        }
        if (value.request != null) stateHandles.remove(value.request.getState());
        value.request = request;
        stateHandles.put(request.getState(), SecretTokens.hash(raw));
        setCookie(response, FLOW_COOKIE, raw, Math.max(1, (int) (value.expires.getEpochSecond() - clock.instant().getEpochSecond())), "Lax");
    }

    public synchronized OAuth2AuthorizationRequest remove(HttpServletRequest request, HttpServletResponse response) {
        OAuth2AuthorizationRequest result = load(request);
        String raw = cookie(request, FLOW_COOKIE);
        if (raw != null) {
            Pending value = pending.get(SecretTokens.hash(raw));
            if (value != null && value.request != null) value.request = null;
        }
        clearFlow(response);
        return result;
    }

    public synchronized void clearFlow(HttpServletResponse response) { setCookie(response, FLOW_COOKIE, "", 0, "Lax"); }

    /** Consume the state-to-session binding exactly once after Spring has validated OAuth state and OIDC. */
    public synchronized void handoff(GoogleProfile profile, HttpServletRequest request, HttpServletResponse response) {
        prune();
        String state = request.getParameter("state");
        String handle = state == null ? null : stateHandles.remove(state);
        Pending binding = handle == null ? null : pending.remove(handle);
        clearFlow(response);
        if (binding == null || !binding.expires.isAfter(clock.instant()))
            throw new ApiException(401, "GOOGLE_LINK_EXPIRED", "Yêu cầu liên kết đã hết hạn. Vui lòng bắt đầu lại.");
        if (handoffs.size() >= 1000) throw new ApiException(429, "RATE_LIMITED", "Vui lòng thử lại sau.");
        String raw = SecretTokens.random();
        handoffs.put(SecretTokens.hash(raw), new Handoff(new Ticket(profile, binding.binding.userId(), binding.binding.sessionId()), clock.instant().plusSeconds(60)));
        setCookie(response, TICKET_COOKIE, raw, 60, "Lax");
    }

    public synchronized Ticket consumeTicket(HttpServletRequest request, HttpServletResponse response) {
        prune();
        String raw = cookie(request, TICKET_COOKIE);
        Handoff handoff = raw == null ? null : handoffs.remove(SecretTokens.hash(raw));
        setCookie(response, TICKET_COOKIE, "", 0, "Lax");
        if (handoff == null || !handoff.expires().isAfter(clock.instant()))
            throw new ApiException(401, "GOOGLE_LINK_EXPIRED", "Yêu cầu liên kết đã hết hạn. Vui lòng bắt đầu lại.");
        return handoff.ticket();
    }

    public synchronized void fail(HttpServletRequest request, HttpServletResponse response) {
        String state = request.getParameter("state");
        String handle = state == null ? null : stateHandles.remove(state);
        if (handle != null) pending.remove(handle);
        String raw = cookie(request, FLOW_COOKIE);
        if (raw != null) pending.remove(SecretTokens.hash(raw));
        clearFlow(response);
    }
}
