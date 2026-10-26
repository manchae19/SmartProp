package vn.smartprop.auth;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import vn.smartprop.user.UserDtos;
@RestController @RequestMapping("/api/v1/auth")
public class AuthController {
    private final AuthService service;
    @org.springframework.beans.factory.annotation.Autowired(required=false) private RefreshService refresh;
    @org.springframework.beans.factory.annotation.Autowired(required=false) private RefreshController cookies;
    public AuthController(AuthService service) { this.service=service; }
    @PostMapping("/register") @ResponseStatus(HttpStatus.CREATED)
    public UserDtos.Profile register(@Valid @RequestBody AuthDtos.Register r) { return service.register(r); }
    @PostMapping("/login") public AuthDtos.Token login(@Valid @RequestBody AuthDtos.Login r,jakarta.servlet.http.HttpServletRequest req,jakarta.servlet.http.HttpServletResponse res) {
        boolean optIn="true".equalsIgnoreCase(req.getHeader("X-Refresh-Session"));
        if(optIn){if(refresh==null||!refresh.enabled())throw new vn.smartprop.common.ApiException(503,"FEATURE_DISABLED","Refresh disabled");cookies.origin(req);}
        var access=service.login(r);res.setHeader("Cache-Control","no-store");if(optIn){var result=refresh.activate(access,req.getHeader("User-Agent"));cookies.set(res,result.refresh(),7*86400);}return access;
    }
    @PostMapping("/logout") @ResponseStatus(HttpStatus.NO_CONTENT)
    public void logout(@AuthenticationPrincipal Jwt jwt,jakarta.servlet.http.HttpServletRequest req,jakarta.servlet.http.HttpServletResponse res) {
        String cookie=cookies==null||refresh==null||!refresh.enabled()?null:cookies.cookie(req);
        if(cookie!=null){cookies.origin(req);refresh.cookieLogout(cookie);cookies.set(res,"",0);}
        if(jwt!=null)service.logout(jwt.getId());else if(cookie==null)throw new vn.smartprop.common.ApiException(401,"UNAUTHENTICATED","Login required");
    }
}
