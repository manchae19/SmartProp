package vn.smartprop.recommendation;

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
import vn.smartprop.common.ApiInputs;
import static vn.smartprop.recommendation.RecommendationDtos.*;

@RestController
@RequestMapping("/api/v1/recommendations")
public class RecommendationController {
    private final HybridRecommendationService service;
    private final String demoKey;
    public RecommendationController(HybridRecommendationService service,@Value("${app.recommendation.demo-key:}") String demoKey) {
        this.service=service;this.demoKey=demoKey;
    }
    @PostMapping
    public ResponseEntity<Response> recommend(@Valid @RequestBody Request request,HttpServletRequest http,Authentication authentication) {
        if(service.internalDemo()) {
            String provided=http.getHeader("X-SmartProp-Demo-Key");
            // The shared demo key is a second factor, never a replacement for a
            // live account/session. Authorities come from the existing JWT chain.
            if(!(authentication instanceof JwtAuthenticationToken)||!authentication.isAuthenticated()
                ||authentication.getAuthorities().stream().noneMatch(a->"ROLE_ADMIN".equals(a.getAuthority()))
                ||!Set.of("127.0.0.1","::1","0:0:0:0:0:0:0:1").contains(http.getRemoteAddr())||demoKey.isBlank()||provided==null
                ||!MessageDigest.isEqual(demoKey.getBytes(StandardCharsets.UTF_8),provided.getBytes(StandardCharsets.UTF_8)))throw ApiInputs.forbidden();
        }
        return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(service.recommend(request));
    }
    @PostMapping("/research")
    public ResponseEntity<Response> research(@Valid @RequestBody Request request,HttpServletRequest http,Authentication authentication) {
        if(!service.tinixEnabled())throw ApiInputs.forbidden();
        String provided=http.getHeader("X-SmartProp-Demo-Key");
        if(!(authentication instanceof JwtAuthenticationToken)||!authentication.isAuthenticated()
            ||authentication.getAuthorities().stream().noneMatch(a->"ROLE_ADMIN".equals(a.getAuthority()))
            ||!Set.of("127.0.0.1","::1","0:0:0:0:0:0:0:1").contains(http.getRemoteAddr())||demoKey.isBlank()||provided==null
            ||!MessageDigest.isEqual(demoKey.getBytes(StandardCharsets.UTF_8),provided.getBytes(StandardCharsets.UTF_8)))throw ApiInputs.forbidden();
        return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(service.recommendResearch(request));
    }
    @GetMapping("/research/config")
    public ResponseEntity<java.util.Map<String,Boolean>> researchConfig(HttpServletRequest http,Authentication authentication) {
        if(!(authentication instanceof JwtAuthenticationToken)||!authentication.isAuthenticated()
            ||authentication.getAuthorities().stream().noneMatch(a->"ROLE_ADMIN".equals(a.getAuthority()))
            ||!Set.of("127.0.0.1","::1","0:0:0:0:0:0:0:1").contains(http.getRemoteAddr()))throw ApiInputs.forbidden();
        return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(java.util.Map.of("enabled",service.tinixEnabled()&&!demoKey.isBlank()));
    }
}
