package vn.smartprop.comparable;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;

import vn.smartprop.common.ApiException;
import vn.smartprop.common.ApiInputs;
import vn.smartprop.common.RequestLimits;
import vn.smartprop.modules.auth.AccountAccess;

/**
 * Comparable-properties lookup.
 *
 * <ul>
 *   <li>Default mode ({@code includeResearch=false/null}): accessible to active {@code BROKER}
 *       and {@code ADMIN} accounts; serves only public {@code SMARTPROP} and
 *       {@code EXTERNAL_LISTING} comparables without touching {@code tinix_dataset_records}.</li>
 *   <li>Explicit research mode ({@code includeResearch=true}): strictly requires an active,
 *       non-deleted {@code ADMIN} account and {@code app.comparable.research-enabled=true};
 *       otherwise fails closed with {@code 403 Forbidden}.</li>
 * </ul>
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
    public ComparableDtos.Response comparables(
            @AuthenticationPrincipal Jwt jwt,
            @RequestParam(required = false) Boolean includeResearch,
            @RequestBody(required = false) ComparableDtos.Request body,
            HttpServletRequest request,
            HttpServletResponse response) {
        response.setHeader("Cache-Control", "private, no-store");
        Long id = parseUserId(jwt);
        boolean wantsResearch = Boolean.TRUE.equals(includeResearch)
            || (body != null && Boolean.TRUE.equals(body.includeResearch()));

        if (wantsResearch) {
            access.admin(id);
            if (!service.isResearchEnabled()) {
                throw ApiInputs.forbidden();
            }
        } else {
            access.publisher(id);
        }

        limits.check("comparables:user:" + id, 20, 60);
        limits.check("comparables:ip:" + request.getRemoteAddr(), 40, 60);

        ComparableDtos.Request effective = body == null
            ? new ComparableDtos.Request(null, null, null, null, null, null, null, null, null, wantsResearch)
            : new ComparableDtos.Request(
                body.propertyId(), body.propertyType(), body.district(), body.ward(),
                body.areaSqm(), body.priceVnd(), body.bedrooms(), body.floors(), body.limit(),
                wantsResearch ? Boolean.TRUE : Boolean.FALSE);
        return wantsResearch ? service.rankResearch(effective) : service.rank(effective);
    }

    private static Long parseUserId(Jwt jwt) {
        if (jwt == null) {
            throw new ApiException(401, "UNAUTHENTICATED", "Vui lòng đăng nhập");
        }
        try {
            return Long.valueOf(jwt.getSubject());
        } catch (NumberFormatException | NullPointerException ex) {
            throw new ApiException(401, "UNAUTHENTICATED", "Phiên không hợp lệ");
        }
    }
}
