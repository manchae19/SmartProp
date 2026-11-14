package vn.smartprop.modules.auth;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.http.HttpStatus;
import vn.smartprop.common.PageResponse;
@RestController @RequestMapping("/api/v1/users/me/sessions")
public class SessionController {
    private final RefreshService service;public SessionController(RefreshService service){this.service=service;}
    @GetMapping public PageResponse<RefreshService.SessionView> list(@AuthenticationPrincipal Jwt j,@RequestParam(defaultValue="0") int page,@RequestParam(defaultValue="20") int size){return service.list(Long.valueOf(j.getSubject()),j.getId(),page,size);}
    @DeleteMapping("/{id}") @ResponseStatus(HttpStatus.NO_CONTENT) public void revoke(@AuthenticationPrincipal Jwt j,@PathVariable String id){service.revoke(Long.valueOf(j.getSubject()),id);}
    @DeleteMapping @ResponseStatus(HttpStatus.NO_CONTENT) public void all(@AuthenticationPrincipal Jwt j){service.revokeAll(Long.valueOf(j.getSubject()));}
}
