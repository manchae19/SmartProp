package vn.smartprop.property;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;
import vn.smartprop.common.Errors;

@RestController
@RequestMapping("/api/v1/properties")
public class PropertyContactController {
    private final PropertyContactService service;
    public PropertyContactController(PropertyContactService service) {this.service=service;}
    @GetMapping("/{id}/contact")
    public PropertyContactDtos.Contact contact(@AuthenticationPrincipal Jwt jwt,@PathVariable String id,
                                               HttpServletRequest request,HttpServletResponse response) {
        response.setHeader("Cache-Control","private, no-store");
        response.setHeader("Pragma","no-cache");
        return service.contact(Long.valueOf(jwt.getSubject()),id,request.getRemoteAddr());
    }
    @ExceptionHandler(ContactRateLimit.Exceeded.class)
    public ResponseEntity<Errors.Body> limited(ContactRateLimit.Exceeded e) {
        return ResponseEntity.status(429).header("Retry-After",Long.toString(e.retryAfter))
            .header("Cache-Control","private, no-store").body(Errors.body(e.code,e.getMessage()));
    }
}
