package vn.smartprop.collection;

import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpServletRequest;
import vn.smartprop.common.RequestLimits;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;
import vn.smartprop.property.Property;

/** Uses the existing public-property and authenticated owner route policies. */
@RestController
@RequestMapping("/api/v1")
public class CollectionSummaryController {
    private final CollectionSummaryService service;
    private final RequestLimits limits;
    public CollectionSummaryController(CollectionSummaryService service,RequestLimits limits){this.service=service;this.limits=limits;}
    private Long actor(Jwt jwt,HttpServletResponse response){response.setHeader("Cache-Control","private, no-store");return Long.valueOf(jwt.getSubject());}
    @GetMapping("/properties/market-summary")
    public CollectionSummaryService.Market market(@RequestParam(required=false) String city,@RequestParam(required=false) String district,
        @RequestParam(required=false) Property.Type propertyType,@RequestParam(defaultValue="SALE") Property.Transaction transactionType,
        @RequestParam(defaultValue="TOTAL") Property.PriceUnit priceUnit,HttpServletResponse response,HttpServletRequest request){
        response.setHeader("Cache-Control","no-store");limits.check("market-summary:"+request.getRemoteAddr(),30,60);return service.market(city,district,propertyType,transactionType,priceUnit);
    }
    @GetMapping("/users/me/properties/summary") public CollectionSummaryService.Owned owned(@AuthenticationPrincipal Jwt jwt,HttpServletResponse response){return service.owned(actor(jwt,response));}
    @GetMapping("/users/me/saved-properties/summary") public CollectionSummaryService.Favorites favorites(@AuthenticationPrincipal Jwt jwt,HttpServletResponse response){return service.favorites(actor(jwt,response));}
    @GetMapping("/reports/summary") public CollectionSummaryService.Reports reports(@AuthenticationPrincipal Jwt jwt,HttpServletResponse response){return service.reports(actor(jwt,response));}
}
