package vn.smartprop.geocoding;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import org.springframework.http.CacheControl;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;
import vn.smartprop.auth.AccountAccess;
import org.slf4j.MDC;
import java.util.Locale;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/geocoding")
public class GeocodingController {
    private final GeocodingService service;
    private final AccountAccess access;
    public GeocodingController(GeocodingService service,AccountAccess access) { this.service=service;this.access=access; }
    @GetMapping("/config")
    public ResponseEntity<GeocodingDtos.Availability> configuration(@AuthenticationPrincipal Jwt jwt) {
        access.publisher(Long.valueOf(jwt.getSubject()));
        return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(service.configuration());
    }
    @PostMapping("/search")
    public ResponseEntity<GeocodingDtos.Result> search(@AuthenticationPrincipal Jwt jwt,
        @Valid @RequestBody GeocodingDtos.Search request,HttpServletRequest http,HttpServletResponse response) {
        Long actor=Long.valueOf(jwt.getSubject());
        access.publisher(actor);
        // Forwarded/X-Forwarded-For headers do not define the rate-limit identity.
        String id=UUID.randomUUID().toString();long started=System.nanoTime();
        response.setHeader("X-Geocoding-Request-Id",id);
        try(var ignored=MDC.putCloseable("geocodingRequestId",id)) {
            return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(service.search(actor,http.getRemoteAddr(),request));
        } finally {
            response.setHeader("Server-Timing",String.format(Locale.ROOT,"geocoding;dur=%.1f",(System.nanoTime()-started)/1_000_000.0));
        }
    }
}
