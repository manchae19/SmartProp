package vn.smartprop.market;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import vn.smartprop.common.RequestLimits;

/**
 * Step 21.5B — Public, read-only Market Analytics endpoint.
 *
 * <p>Mapped under {@code /api/v1/properties/market-analytics} so it inherits the
 * existing public GET policy for {@code /api/v1/properties/*} (the same policy that
 * already serves {@code /api/v1/properties/market-summary}); no security config change
 * is required. It returns only aggregates — no contact fields, no property ids.
 */
@RestController
@RequestMapping("/api/v1/properties")
public class MarketAnalyticsController {

    private final MarketAnalyticsService service;
    private final RequestLimits limits;

    public MarketAnalyticsController(MarketAnalyticsService service, RequestLimits limits) {
        this.service = service;
        this.limits = limits;
    }

    @GetMapping("/market-analytics")
    public MarketDtos.Response analytics(
            @RequestParam(required = false) String district,
            @RequestParam(required = false) String ward,
            @RequestParam(required = false) String propertyType,
            @RequestParam(required = false) String source,
            @RequestParam(required = false) Boolean includeResearch,
            HttpServletRequest request,
            HttpServletResponse response) {
        response.setHeader("Cache-Control", "no-store");
        limits.check("market-analytics:" + request.getRemoteAddr(), 60, 60);
        return service.analytics(district, ward, propertyType, source, includeResearch);
    }
}
