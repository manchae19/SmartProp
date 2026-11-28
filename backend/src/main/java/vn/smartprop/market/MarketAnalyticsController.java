package vn.smartprop.market;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import vn.smartprop.common.ApiException;
import vn.smartprop.common.ApiInputs;
import vn.smartprop.common.RequestLimits;
import vn.smartprop.modules.auth.AccountAccess;

/**
 * Step 21.5B — Read-only Market Analytics endpoint.
 *
 * <ul>
 *   <li>Public requests ({@code includeResearch=false} and non-research {@code source}): accessible
 *       without login under {@code /api/v1/properties/*}; serves only public {@code SMARTPROP} and
 *       {@code EXTERNAL_LISTING} aggregates.</li>
 *   <li>Research requests ({@code includeResearch=true} or {@code source=TINIX_RESEARCH}): strictly
 *       require an authenticated active {@code ADMIN} account verified in MySQL and
 *       {@code app.market.research-enabled=true}; otherwise fail closed with {@code 403 Forbidden}.</li>
 * </ul>
 */
@RestController
@RequestMapping("/api/v1/properties")
public class MarketAnalyticsController {

    private final MarketAnalyticsService service;
    private final RequestLimits limits;
    private final AccountAccess access;

    public MarketAnalyticsController(
            MarketAnalyticsService service,
            RequestLimits limits,
            AccountAccess access) {
        this.service = service;
        this.limits = limits;
        this.access = access;
    }

    @GetMapping("/market-analytics")
    public MarketDtos.Response analytics(
            @RequestParam(required = false) String district,
            @RequestParam(required = false) String ward,
            @RequestParam(required = false) String propertyType,
            @RequestParam(required = false) String source,
            @RequestParam(required = false) Boolean includeResearch,
            HttpServletRequest request,
            HttpServletResponse response,
            Authentication authentication) {
        limits.check("market-analytics:" + request.getRemoteAddr(), 60, 60);

        if (MarketAnalyticsService.requestsResearch(source, includeResearch)) {
            response.setHeader("Cache-Control", "private, no-store");
            if (!(authentication instanceof JwtAuthenticationToken jwtAuth) || !jwtAuth.isAuthenticated()) {
                throw ApiInputs.forbidden();
            }
            Long userId = parseUserId(jwtAuth);
            limits.check("market-analytics:user:" + userId, 30, 60);
            access.admin(userId);
            if (!service.isResearchEnabled()) {
                throw ApiInputs.forbidden();
            }
            return service.analyticsResearch(district, ward, propertyType, source, includeResearch);
        }

        response.setHeader("Cache-Control", "no-store");
        return service.analytics(district, ward, propertyType, source, false);
    }

    private static Long parseUserId(JwtAuthenticationToken jwtAuth) {
        try {
            return Long.valueOf(jwtAuth.getToken().getSubject());
        } catch (NumberFormatException | NullPointerException ex) {
            throw new ApiException(401, "UNAUTHENTICATED", "Phiên không hợp lệ");
        }
    }
}
