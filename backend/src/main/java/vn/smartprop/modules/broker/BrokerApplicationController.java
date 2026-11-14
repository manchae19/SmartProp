package vn.smartprop.modules.broker;

import jakarta.servlet.http.*;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import vn.smartprop.common.*;
import vn.smartprop.config.*;
import static vn.smartprop.modules.broker.BrokerApplicationDtos.*;

@RestController @RequestMapping("/api/v1")
public class BrokerApplicationController {
    private final BrokerApplicationService service;
    private final RequestLimits limits;
    public BrokerApplicationController(BrokerApplicationService service,RequestLimits limits) {this.service=service;this.limits=limits;}
    private Long actor(Jwt jwt,HttpServletResponse response) { response.setHeader("Cache-Control","private, no-store");return Long.valueOf(jwt.getSubject()); }
    @GetMapping("/users/me/broker-application") public Mine mine(@AuthenticationPrincipal Jwt jwt,HttpServletResponse response) {return service.mine(actor(jwt,response));}
    @PostMapping("/users/me/broker-application") public Mine submit(@AuthenticationPrincipal Jwt jwt,@Valid @RequestBody Submit input,HttpServletRequest request,HttpServletResponse response) {
        Long user=actor(jwt,response);limits.check("broker-application:user:"+user,5,3600);limits.check("broker-application:ip:"+request.getRemoteAddr(),20,3600);
        return service.submit(user,input);
    }
    @GetMapping("/admin/broker-applications") public PageResponse<View> queue(@AuthenticationPrincipal Jwt jwt,@RequestParam(required=false) Status status,@RequestParam(defaultValue="0") int page,@RequestParam(defaultValue="20") int size,HttpServletResponse response) {return service.queue(actor(jwt,response),status,page,size);}
    @GetMapping("/admin/broker-applications/{id}") public View detail(@AuthenticationPrincipal Jwt jwt,@PathVariable String id,HttpServletResponse response) {return service.detail(actor(jwt,response),id);}
    @PostMapping("/admin/broker-applications/{id}/review") public View review(@AuthenticationPrincipal Jwt jwt,@PathVariable String id,@Valid @RequestBody Review input,HttpServletResponse response) {return service.review(actor(jwt,response),id,input);}
}
