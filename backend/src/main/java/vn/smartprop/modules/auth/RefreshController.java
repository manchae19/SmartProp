package vn.smartprop.modules.auth;
import jakarta.servlet.http.*;
import java.util.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.security.web.csrf.CsrfToken;
import org.springframework.web.bind.annotation.*;
import vn.smartprop.common.*;
import vn.smartprop.config.*;
@RestController @RequestMapping("/api/v1/auth")
public class RefreshController {
    private final RefreshService service;private final RequestLimits limits;private final Set<String> origins;private final boolean secure;
    public RefreshController(RefreshService service,RequestLimits limits,@Value("${app.cors-origins}") String origins,@Value("${app.refresh.secure-cookie:true}") boolean secure){this.service=service;this.limits=limits;this.origins=new HashSet<>();for(String origin:origins.split(",")){String value=origin.trim();if(!value.isEmpty())this.origins.add(value);}this.secure=secure;}
    public void origin(HttpServletRequest request) {
        validateOrigin(request.getHeader("Origin"), request);
    }

    private void validateOrigin(String origin, HttpServletRequest request) {
        if (origin == null || !origins.contains(origin)) throw ApiInputs.forbidden();
        if (!secure && (!origin.matches("http://(localhost|127\\.0\\.0\\.1)(:[0-9]+)?")
                || !Set.of("localhost", "127.0.0.1", "::1").contains(request.getServerName())
                || !Set.of("127.0.0.1", "::1", "0:0:0:0:0:0:0:1").contains(request.getRemoteAddr())))
            throw ApiInputs.forbidden();
    }

    private void bootstrapOrigin(HttpServletRequest request) {
        if (request.getHeader("Origin") != null) {
            origin(request);
            return;
        }
        // Browsers can omit Origin on a same-origin GET. Never extend this to mutation endpoints.
        if (!"GET".equals(request.getMethod()) || !"same-origin".equals(request.getHeader("Sec-Fetch-Site")))
            throw ApiInputs.forbidden();
        String scheme = request.getScheme();
        if (!Set.of("http", "https").contains(scheme)) throw ApiInputs.forbidden();
        String host = request.getServerName();
        if (host.contains(":" ) && !host.startsWith("[")) host = "[" + host + "]";
        int port = request.getServerPort();
        boolean defaultPort = ("https".equals(scheme) && port == 443) || ("http".equals(scheme) && port == 80);
        validateOrigin(scheme + "://" + host + (defaultPort ? "" : ":" + port), request);
    }
    public String cookie(HttpServletRequest req){if(req.getCookies()!=null)for(var c:req.getCookies())if(c.getName().equals("SMARTPROP_REFRESH"))return c.getValue();return null;}
    public void set(HttpServletResponse res,String value,long ttl){res.addHeader("Set-Cookie",ResponseCookie.from("SMARTPROP_REFRESH",value).httpOnly(true).secure(secure).sameSite("Lax").path("/api/v1/auth").maxAge(ttl).build().toString());res.setHeader("Cache-Control","no-store");}
    public void clear(HttpServletResponse res){set(res,"",0);res.addHeader("Set-Cookie",ResponseCookie.from("XSRF-TOKEN","").httpOnly(true).secure(secure).sameSite("Lax").path("/api/v1/auth").maxAge(0).build().toString());}
    @GetMapping("/csrf") public Map<String,String> csrf(HttpServletRequest req,HttpServletResponse res,CsrfToken csrf){if(!service.enabled())throw new ApiException(503,"FEATURE_DISABLED","Refresh disabled");bootstrapOrigin(req);limits.check("csrf:"+req.getRemoteAddr(),60,60);res.setHeader("Cache-Control","no-store");return Map.of("token",csrf.getToken(),"headerName",csrf.getHeaderName());}
    @PostMapping("/refresh") public AuthDtos.Token refresh(HttpServletRequest req,HttpServletResponse res){origin(req);limits.check("refresh-ip:"+req.getRemoteAddr(),60,60);String raw=cookie(req);if(raw!=null)limits.check("refresh-hash:"+SecretTokens.hash(raw),10,60);try{var result=service.rotate(raw,"true".equals(req.getHeader("X-Session-Activity")));set(res,result.refresh(),result.cookieSeconds());return result.access();}catch(ApiException e){if(e.status==401)set(res,"",0);throw e;}}
}
