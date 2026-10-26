package vn.smartprop.geocoding;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.http.CacheControl;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;
import vn.smartprop.auth.AccountAccess;

@RestController
@RequestMapping("/api/v1/geocoding")
public class GeocodingController {
    private final GeocodingService service;
    private final AccountAccess access;
    public GeocodingController(GeocodingService service,AccountAccess access) { this.service=service;this.access=access; }
    @PostMapping("/search")
    public ResponseEntity<GeocodingDtos.Result> search(@AuthenticationPrincipal Jwt jwt,
        @Valid @RequestBody GeocodingDtos.Search request,HttpServletRequest http) {
        Long actor=Long.valueOf(jwt.getSubject());
        access.publisher(actor);
        // Forwarded/X-Forwarded-For headers do not define the rate-limit identity.
        return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(service.search(actor,http.getRemoteAddr(),request));
    }
}
