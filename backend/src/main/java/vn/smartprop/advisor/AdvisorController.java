package vn.smartprop.advisor;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.http.CacheControl;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import vn.smartprop.advisor.AdvisorDtos.AdvisorRequest;
import vn.smartprop.advisor.AdvisorDtos.AdvisorResponse;
import vn.smartprop.modules.auth.AccountAccess;
import vn.smartprop.common.ApiInputs;
import vn.smartprop.common.RequestLimits;

/**
 * REST endpoint for Step 21.3 — Unified AI Advisor Consultation.
 *
 * <ul>
 *   <li>Public SAFE mode ({@code includeResearch=false}): accessible without login; returns only
 *       verified active listings in {@code recommendedProperties}, rate-limited per IP/user.</li>
 *   <li>Internal Research mode ({@code includeResearch=true}): strictly requires an authenticated
 *       active {@code ADMIN} account verified against the database and
 *       {@code app.recommendation.tinix-enabled=true}.</li>
 * </ul>
 */
@RestController
@RequestMapping("/api/v1/advisor")
public class AdvisorController {
    private final AdvisorOrchestrationService service;
    private final AccountAccess access;
    private final RequestLimits limits;

    public AdvisorController(
            AdvisorOrchestrationService service,
            AccountAccess access,
            RequestLimits limits) {
        this.service = service;
        this.access = access;
        this.limits = limits;
    }

    @PostMapping("/consult")
    public ResponseEntity<AdvisorResponse> consult(
            @Valid @RequestBody AdvisorRequest request,
            HttpServletRequest httpRequest,
            Authentication authentication) {

        limits.check("advisor:ip:" + httpRequest.getRemoteAddr(), 30, 60);

        if (authentication instanceof JwtAuthenticationToken jwtAuth && jwtAuth.isAuthenticated()) {
            Long userId = Long.valueOf(jwtAuth.getToken().getSubject());
            limits.check("advisor:user:" + userId, 20, 60);
            if (Boolean.TRUE.equals(request.includeResearch())) {
                if (!service.isResearchEnabled()) {
                    throw ApiInputs.forbidden();
                }
                access.admin(userId);
            }
        } else if (Boolean.TRUE.equals(request.includeResearch())) {
            throw ApiInputs.forbidden();
        }

        AdvisorResponse response = service.consult(request);
        return ResponseEntity.ok()
            .cacheControl(CacheControl.noStore())
            .body(response);
    }
}
