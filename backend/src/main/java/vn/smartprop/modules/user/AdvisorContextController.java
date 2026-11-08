package vn.smartprop.modules.user;

import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;

@RestController
@RequestMapping("/api/v1/users/me/advisor-context")
public class AdvisorContextController {
    private final AdvisorPreferencesService service;
    public AdvisorContextController(AdvisorPreferencesService service) { this.service=service; }
    @GetMapping public org.springframework.http.ResponseEntity<AdvisorPreferencesService.Context> get(@AuthenticationPrincipal Jwt jwt) {
        return org.springframework.http.ResponseEntity.ok().cacheControl(org.springframework.http.CacheControl.noStore()).body(service.context(Long.valueOf(jwt.getSubject())));
    }
}
