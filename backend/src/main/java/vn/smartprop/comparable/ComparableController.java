package vn.smartprop.comparable;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;

import vn.smartprop.modules.auth.AccountAccess;
import vn.smartprop.common.RequestLimits;

/**
 * Comparable-properties lookup for the valuation screen.
 *
 * Broker-only for the same reason the valuation preview is: the response can
 * carry research rows (TiniX) that are licensed for local demo use, not for an
 * anonymous browser.
 */
@RestController
@RequestMapping("/api/v1/properties")
public class ComparableController {
    private final ComparableRankingService service;
    private final RequestLimits limits;
    private final AccountAccess access;

    public ComparableController(ComparableRankingService service, RequestLimits limits, AccountAccess access) {
        this.service = service;
        this.limits = limits;
        this.access = access;
    }

    @PostMapping("/comparables")
    public ComparableDtos.Response comparables(@AuthenticationPrincipal Jwt jwt,
                                               @RequestBody ComparableDtos.Request body,
                                               HttpServletRequest request,
                                               HttpServletResponse response) {
        response.setHeader("Cache-Control", "private, no-store");
        Long id = Long.valueOf(jwt.getSubject());
        access.publisher(id);
        limits.check("comparables:user:" + id, 20, 60);
        limits.check("comparables:ip:" + request.getRemoteAddr(), 40, 60);
        return service.rank(body == null ? new ComparableDtos.Request(
            null, null, null, null, null, null, null, null, null) : body);
    }
}
