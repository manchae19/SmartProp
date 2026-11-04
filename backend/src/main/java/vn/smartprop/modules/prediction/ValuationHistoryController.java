package vn.smartprop.modules.prediction;

import jakarta.servlet.http.*;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;
import vn.smartprop.common.*;
import vn.smartprop.config.*;

@RestController
@RequestMapping("/api/v1/users/me/valuation-history")
public class ValuationHistoryController {
    private final ValuationHistoryService service;
    private final RequestLimits limits;
    public ValuationHistoryController(ValuationHistoryService service,RequestLimits limits) { this.service=service;this.limits=limits; }
    private Long actor(Jwt jwt,HttpServletResponse response) {
        response.setHeader("Cache-Control","private, no-store");return Long.valueOf(jwt.getSubject());
    }
    @PostMapping @ResponseStatus(HttpStatus.CREATED)
    public ValuationHistoryRepository.Entry save(@AuthenticationPrincipal Jwt jwt,HttpServletRequest request,HttpServletResponse response,
            @Valid @RequestBody HistoryInput body,@RequestHeader(value="Idempotency-Key",required=false) String key) {
        Long user=actor(jwt,response);limits.check("history:save:user:"+user,10,60);
        limits.check("history:save:ip:"+request.getRemoteAddr(),30,60);return service.save(user,body,key);
    }
    @GetMapping public PageResponse<ValuationHistoryRepository.Entry> list(@AuthenticationPrincipal Jwt jwt,HttpServletResponse response,
            @RequestParam(defaultValue="0") int page,@RequestParam(defaultValue="20") int size) { return service.list(actor(jwt,response),page,size); }
    @GetMapping("/{id}") public ValuationHistoryRepository.Entry get(@AuthenticationPrincipal Jwt jwt,HttpServletResponse response,@PathVariable String id) { return service.get(actor(jwt,response),id); }
    @DeleteMapping("/{id}") @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@AuthenticationPrincipal Jwt jwt,HttpServletResponse response,@PathVariable String id) { service.delete(actor(jwt,response),id); }
}
