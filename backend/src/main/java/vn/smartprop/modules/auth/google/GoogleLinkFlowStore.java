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
    private static final String CONSUMED_FLOW = GoogleLinkFlowStore.class.getName() + ".consumed";
    private static final int TTL_SECONDS = 300;

    public record Binding(long userId, String sessionId) {}
    public record Ticket(GoogleProfile profile, long userId, String sessionId) {}
    private static final class Flow {
        final Binding binding;
        final String handle;
        Instant expires;
        OAuth2AuthorizationRequest request;
        String state;
        String ticketHandle;

        Flow(Binding binding, String handle, Instant expires) {
            this.binding = binding;
            this.handle = handle;
            this.expires = expires;
        }
    }
    private record Handoff(Ticket ticket, Flow flow) {}

    private final Clock clock;
    private final boolean secure;
    private final Map<Binding, Flow> latest = new HashMap<>();
    private final Map<String, Flow> pending = new HashMap<>();
    private final Map<String, String> stateHandles = new HashMap<>();
    private final Map<String, Handoff> handoffs = new HashMap<>();

    public GoogleLinkFlowStore(Clock clock, GoogleSettings settings) {
        this.clock = clock;
        this.secure = settings.secure;
    }

    private void prune() {
        Instant now = clock.instant();
        for (var flow : latest.values().stream().filter(flow -> !flow.expires.isAfter(now)).toList()) {
            discard(flow);
        }
    }

    private void discard(Flow flow) {
        latest.remove(flow.binding, flow);
        pending.remove(flow.handle);
        if (flow.state != null) stateHandles.remove(flow.state, flow.handle);
        if (flow.ticketHandle != null) handoffs.remove(flow.ticketHandle);
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
        Binding binding = new Binding(userId, sessionId);
        Flow previous = latest.get(binding);
        if (previous != null) {
            discard(previous);
            if (previous.ticketHandle != null) setCookie(response, TICKET_COOKIE, "", 0, "Lax");
        }
        if (latest.size() >= 1000) throw new ApiException(429, "RATE_LIMITED", "Vui lòng thử lại sau.");
        String raw = SecretTokens.random();
        var flow = new Flow(binding, SecretTokens.hash(raw), clock.instant().plusSeconds(TTL_SECONDS));
        latest.put(binding, flow);
        pending.put(flow.handle, flow);
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
        Flow value = raw == null ? null : pending.get(SecretTokens.hash(raw));
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
        Flow value = raw == null ? null : pending.get(SecretTokens.hash(raw));
        if (value == null || value.request == null || !SecretTokens.equal(value.request.getState(), request.getParameter("state"))) return null;
        return value.request;
    }

    public synchronized void save(OAuth2AuthorizationRequest request, HttpServletRequest httpRequest, HttpServletResponse response) {
        prune();
        String raw = cookie(httpRequest, FLOW_COOKIE);
        Flow value = raw == null ? null : pending.get(SecretTokens.hash(raw));
        if (request == null || value == null || !isLinkRequest(request))
            throw new ApiException(410, "GOOGLE_LINK_EXPIRED", "Yêu cầu liên kết đã hết hạn. Vui lòng bắt đầu lại.");
        if (value.request != null)
            throw new ApiException(409, "GOOGLE_LINK_ALREADY_STARTED", "Yêu cầu liên kết đã được khởi tạo.");
        value.request = request;
        value.state = request.getState();
        stateHandles.put(value.state, value.handle);
    }

    public synchronized OAuth2AuthorizationRequest remove(HttpServletRequest request, HttpServletResponse response) {
        OAuth2AuthorizationRequest result = load(request);
        if (result == null) return null;
        String handle = SecretTokens.hash(cookie(request, FLOW_COOKIE));
        Flow flow = pending.remove(handle);
        stateHandles.remove(result.getState());
        request.setAttribute(CONSUMED_FLOW, flow);
        return result;
    }

    /** The current flow is checked again after token exchange, which can overlap a new start in another tab. */
    public synchronized void handoff(GoogleProfile profile, HttpServletRequest request, HttpServletResponse response) {
        prune();
        Flow flow = (Flow) request.getAttribute(CONSUMED_FLOW);
        request.removeAttribute(CONSUMED_FLOW);
        if (flow == null || latest.get(flow.binding) != flow)
            throw new ApiException(410, "GOOGLE_LINK_EXPIRED", "Yêu cầu liên kết đã hết hạn. Vui lòng bắt đầu lại.");
        String raw = SecretTokens.random();
        flow.ticketHandle = SecretTokens.hash(raw);
        flow.expires = clock.instant().plusSeconds(60);
        var ticket = new Ticket(profile, flow.binding.userId(), flow.binding.sessionId());
        handoffs.put(flow.ticketHandle, new Handoff(ticket, flow));
        setCookie(response, TICKET_COOKIE, raw, 60, "Lax");
    }

    public synchronized Ticket consumeTicket(HttpServletRequest request, HttpServletResponse response,
                                             String userId, String sessionId) {
        prune();
        String raw = cookie(request, TICKET_COOKIE);
        Handoff handoff = raw == null ? null : handoffs.get(SecretTokens.hash(raw));
        if (handoff == null)
            throw new ApiException(410, "GOOGLE_LINK_EXPIRED", "Yêu cầu liên kết đã hết hạn. Vui lòng bắt đầu lại.");
        var flow = handoff.flow();
        if (!Long.toString(flow.binding.userId()).equals(userId) || !flow.binding.sessionId().equals(sessionId))
            throw new ApiException(409, "GOOGLE_LINK_SESSION_MISMATCH", "Phiên đăng nhập đã thay đổi. Vui lòng bắt đầu liên kết lại.");
        discard(flow);
        setCookie(response, TICKET_COOKIE, "", 0, "Lax");
        String flowCookie = cookie(request, FLOW_COOKIE);
        if (flowCookie != null && flow.handle.equals(SecretTokens.hash(flowCookie)))
            setCookie(response, FLOW_COOKIE, "", 0, "Lax");
        return handoff.ticket();
    }

    public synchronized void fail(HttpServletRequest request, HttpServletResponse response) {
        Flow flow = (Flow) request.getAttribute(CONSUMED_FLOW);
        request.removeAttribute(CONSUMED_FLOW);
        if (flow != null && latest.get(flow.binding) == flow) discard(flow);
    }
}
