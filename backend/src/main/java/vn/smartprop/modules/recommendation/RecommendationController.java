package vn.smartprop.modules.recommendation;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Set;
import vn.smartprop.common.ApiException;
import vn.smartprop.common.ApiInputs;
import vn.smartprop.modules.auth.AccountAccess;
import static vn.smartprop.modules.recommendation.RecommendationDtos.*;

@RestController
@RequestMapping("/api/v1/recommendations")
public class RecommendationController {
    private final HybridRecommendationService service;
    private final String demoKey;
    private final AccountAccess access;

    @org.springframework.beans.factory.annotation.Autowired
    public RecommendationController(
            HybridRecommendationService service,
            @Value("${app.recommendation.demo-key:}") String demoKey,
            AccountAccess access) {
        this.service = service;
        this.demoKey = demoKey;
        this.access = access;
    }

    public RecommendationController(HybridRecommendationService service, String demoKey) {
        this(service, demoKey, null);
    }

    @PostMapping
    public ResponseEntity<Response> recommend(@Valid @RequestBody Request request, HttpServletRequest http, Authentication authentication) {
        if (service.internalDemo()) {
            verifyInternalAdminDemo(http, authentication);
            return ResponseEntity.ok().cacheControl(CacheControl.noStore().cachePrivate()).body(service.recommend(request));
        }
        return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(service.recommendPublic(request));
    }

    @PostMapping("/research")
    public ResponseEntity<Response> research(@Valid @RequestBody Request request, HttpServletRequest http, Authentication authentication) {
        verifyInternalAdminDemo(http, authentication);
        if (!service.tinixEnabled()) throw ApiInputs.forbidden();
        return ResponseEntity.ok().cacheControl(CacheControl.noStore().cachePrivate()).body(service.recommendResearch(request));
    }

    @GetMapping("/research/config")
    public ResponseEntity<java.util.Map<String, Boolean>> researchConfig(HttpServletRequest http, Authentication authentication) {
        verifyActiveAdminOnLoopback(http, authentication);
        return ResponseEntity.ok().cacheControl(CacheControl.noStore().cachePrivate())
            .body(java.util.Map.of("enabled", service.tinixEnabled() && !demoKey.isBlank()));
    }

    private void verifyActiveAdminOnLoopback(HttpServletRequest http, Authentication authentication) {
        if (!(authentication instanceof JwtAuthenticationToken jwtAuth) || !jwtAuth.isAuthenticated()
                || !Set.of("127.0.0.1", "::1", "0:0:0:0:0:0:0:1").contains(http.getRemoteAddr())) {
            throw ApiInputs.forbidden();
        }
        if (access != null) {
            access.admin(parseUserId(jwtAuth));
        }
        if (jwtAuth.getAuthorities().stream().noneMatch(a -> "ROLE_ADMIN".equals(a.getAuthority()))) {
            throw ApiInputs.forbidden();
        }
    }

    private void verifyInternalAdminDemo(HttpServletRequest http, Authentication authentication) {
        verifyActiveAdminOnLoopback(http, authentication);
        String provided = http.getHeader("X-SmartProp-Demo-Key");
        if (demoKey.isBlank() || provided == null
                || !MessageDigest.isEqual(demoKey.getBytes(StandardCharsets.UTF_8), provided.getBytes(StandardCharsets.UTF_8))) {
            throw ApiInputs.forbidden();
        }
    }

    private static Long parseUserId(JwtAuthenticationToken jwtAuth) {
        try {
            return Long.valueOf(jwtAuth.getToken().getSubject());
        } catch (NumberFormatException | NullPointerException ex) {
            throw new ApiException(401, "UNAUTHENTICATED", "Phiên không hợp lệ");
        }
    }
}
