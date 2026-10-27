package vn.smartprop.valuation;
import jakarta.servlet.http.*;
import jakarta.validation.Valid;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;
import vn.smartprop.common.RequestLimits;
import vn.smartprop.auth.AccountAccess;
@RestController
@RequestMapping("/api/v1/properties")
public class ValuationController {
    private final ValuationService service;private final RequestLimits limits;private final AccountAccess access;
    public ValuationController(ValuationService service,RequestLimits limits,AccountAccess access){this.service=service;this.limits=limits;this.access=access;}
    private Long actor(Jwt jwt,HttpServletRequest request,HttpServletResponse response,String operation,int maximum){
        response.setHeader("Cache-Control","private, no-store");Long id=Long.valueOf(jwt.getSubject());access.publisher(id);
        limits.check("valuation:"+operation+":user:"+id,maximum,60);
        limits.check("valuation:"+operation+":ip:"+request.getRemoteAddr(),maximum*3,60);return id;
    }
    @GetMapping("/valuation-options") public ValuationService.Options options(@AuthenticationPrincipal Jwt jwt,HttpServletRequest request,HttpServletResponse response){return service.options(actor(jwt,request,response,"options",30));}
    @PostMapping("/valuation-preview") public ValuationService.Preview preview(@AuthenticationPrincipal Jwt jwt,@Valid @RequestBody ValuationRequest body,HttpServletRequest request,HttpServletResponse response){return service.preview(actor(jwt,request,response,"preview",10),body);}
}
