package vn.smartprop.modules.auth.google;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.util.Map;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import vn.smartprop.common.ApiException;
import vn.smartprop.common.RequestLimits;
import vn.smartprop.modules.auth.RefreshController;
import vn.smartprop.modules.auth.RefreshService;

@RestController
@RequestMapping("/api/v1/auth/google/link")
public class GoogleLinkController {
    public record StartRequest(@NotBlank @Size(max = 72) String currentPassword) {
        @Override public String toString() { return "GoogleLinkStartRequest[redacted]"; }
    }

    private final GoogleLinkService service;
    private final GoogleLinkFlowStore flows;
    private final GoogleSettings settings;
    private final RefreshController cookies;
    private final RefreshService refresh;
    private final RequestLimits limits;

    public GoogleLinkController(GoogleLinkService service, GoogleLinkFlowStore flows, GoogleSettings settings,
                                RefreshController cookies, RefreshService refresh, RequestLimits limits) {
        this.service = service;
        this.flows = flows;
        this.settings = settings;
        this.cookies = cookies;
        this.refresh = refresh;
        this.limits = limits;
    }

    @GetMapping("/status")
    public Map<String, Boolean> status(@AuthenticationPrincipal Jwt jwt, HttpServletResponse response) {
        response.setHeader("Cache-Control", "no-store");
        return Map.of("linked", service.status(jwt).linked(), "available", settings.configured() && refresh.enabled());
    }

    @PostMapping("/start")
    public Map<String, String> start(@AuthenticationPrincipal Jwt jwt, @Valid @RequestBody StartRequest body,
                                     HttpServletRequest request, HttpServletResponse response) {
        if (!settings.configured() || !refresh.enabled()) throw new ApiException(503, "FEATURE_DISABLED", "Google Sign-In chưa được cấu hình đầy đủ trên máy chủ.");
        cookies.origin(request);
        limits.check("google:link:start:" + jwt.getId(), 5, 300);
        limits.check("google:link:password:" + jwt.getSubject(), 5, 300);
        var binding = service.begin(jwt, body.currentPassword());
        flows.begin(binding.userId(), binding.sessionId(), response);
        return Map.of("authorizationPath", "/auth/oauth2/link/authorize/google");
    }

    @PostMapping("/complete")
    public Map<String, Boolean> complete(@AuthenticationPrincipal Jwt jwt, HttpServletRequest request, HttpServletResponse response) {
        cookies.origin(request);
        if (!settings.configured() || !refresh.enabled())
            throw new ApiException(503, "FEATURE_DISABLED", "Liên kết Google chưa được bật.");
        limits.check("google:link:complete:" + jwt.getId(), 5, 300);
        var ticket = flows.consumeTicket(request, response);
        service.complete(ticket, jwt);
        response.setHeader("Cache-Control", "no-store");
        return Map.of("linked", true);
    }
}
