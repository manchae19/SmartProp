package vn.smartprop.modules.user;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
@RestController @RequestMapping("/api/v1/users/me/notification-preferences")
public class PreferencesController {
    private final PreferencesService service;
    public PreferencesController(PreferencesService service) { this.service=service; }
    @GetMapping public PreferencesService.Preferences get(@AuthenticationPrincipal Jwt jwt) { return service.get(Long.valueOf(jwt.getSubject())); }
    @PatchMapping public PreferencesService.Preferences patch(@AuthenticationPrincipal Jwt jwt,@RequestBody PreferencesService.Patch patch) { return service.patch(Long.valueOf(jwt.getSubject()),patch); }
}