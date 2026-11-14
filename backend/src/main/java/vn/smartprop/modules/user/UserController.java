package vn.smartprop.modules.user;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
@RestController @RequestMapping("/api/v1/users/me")
public class UserController {
    private final UserService service;
    public UserController(UserService service) { this.service=service; }
    @GetMapping public UserDtos.Profile me(@AuthenticationPrincipal Jwt jwt) { return service.me(Long.valueOf(jwt.getSubject())); }
    @PatchMapping public UserDtos.Profile update(@AuthenticationPrincipal Jwt jwt,@Valid @RequestBody UserDtos.Patch r) { return service.update(Long.valueOf(jwt.getSubject()),r); }
    @PutMapping("/password") @ResponseStatus(HttpStatus.NO_CONTENT)
    public void password(@AuthenticationPrincipal Jwt jwt,@Valid @RequestBody UserDtos.Password r) { service.password(Long.valueOf(jwt.getSubject()),r); }
}
