package vn.smartprop.modules.auth.google;
import java.util.Map;
import jakarta.servlet.http.*;
import org.springframework.web.bind.annotation.*;
import vn.smartprop.modules.auth.*;
import vn.smartprop.common.*;
@RestController @RequestMapping("/api/v1/auth")
public class GoogleController {
    private final GoogleSettings settings;private final GoogleFlowStore flow;private final GoogleAccountService accounts;private final RefreshService refresh;private final RefreshController cookies;private final RequestLimits limits;
    public GoogleController(GoogleSettings settings,GoogleFlowStore flow,GoogleAccountService accounts,RefreshService refresh,RefreshController cookies,RequestLimits limits){this.settings=settings;this.flow=flow;this.accounts=accounts;this.refresh=refresh;this.cookies=cookies;this.limits=limits;}
    private boolean available(){return settings.configured()&&refresh.enabled();}
    @GetMapping("/google/config") public Map<String,Object> config(HttpServletResponse response){response.setHeader("Cache-Control","no-store");return Map.of("available",available(),"authorizationPath","/auth/oauth2/authorize/google","reason",available()?"READY":"CONFIGURATION_REQUIRED");}
    @GetMapping("/oauth2/authorize/google") public void unavailable(){throw new ApiException(503,"FEATURE_DISABLED","Đăng nhập Google chưa được cấu hình. Vui lòng sử dụng email.");}
    @PostMapping("/oauth2/complete") public AuthDtos.Token complete(HttpServletRequest request,HttpServletResponse response){if(!available())throw new ApiException(503,"FEATURE_DISABLED","Đăng nhập Google chưa được cấu hình.");cookies.origin(request);limits.check("google:complete:"+request.getRemoteAddr(),10,60);var result=accounts.login(flow.consume(request,response),request.getHeader("User-Agent"));cookies.set(response,result.refresh(),result.cookieSeconds());response.setHeader("Cache-Control","no-store");return result.access();}
}
