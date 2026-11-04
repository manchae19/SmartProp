package vn.smartprop.modules.auth.google;
import java.net.URI;
import java.util.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
@Component
public class GoogleSettings {
    public final boolean enabled,secure;
    public final String clientId,clientSecret,redirectUri,frontendOrigin;
    private final Set<String> origins;
    public GoogleSettings(@Value("${app.google.enabled:false}") boolean enabled,@Value("${app.google.client-id:}") String id,@Value("${app.google.client-secret:}") String secret,@Value("${app.google.redirect-uri:http://127.0.0.1:5173/api/v1/auth/oauth2/callback/google}") String redirect,@Value("${app.google.frontend-origin:http://127.0.0.1:5173}") String frontend,@Value("${app.refresh.secure-cookie:true}") boolean secure,@Value("${app.cors-origins}") String origins){this.enabled=enabled;clientId=id;clientSecret=secret;redirectUri=redirect;frontendOrigin=frontend;this.secure=secure;this.origins=new HashSet<>(Arrays.asList(origins.split(",")));}
    public boolean configured(){
        if(!enabled||clientId.isBlank()||clientSecret.isBlank()||!clientId.endsWith(".apps.googleusercontent.com"))return false;
        try{URI origin=URI.create(frontendOrigin),redirect=URI.create(redirectUri);
            boolean local="http".equals(origin.getScheme())&&Set.of("127.0.0.1","localhost").contains(origin.getHost())&&!secure;
            boolean https="https".equals(origin.getScheme())&&secure;
            return (local||https)&&origin.getUserInfo()==null&&origin.getQuery()==null&&origin.getFragment()==null&&(origin.getPath()==null||origin.getPath().isEmpty())&&origins.stream().map(String::strip).anyMatch(frontendOrigin::equals)&&redirectUri.equals(frontendOrigin+"/api/v1/auth/oauth2/callback/google")&&redirect.getQuery()==null;
        }catch(IllegalArgumentException e){return false;}
    }
    @Override public String toString(){return "GoogleSettings[redacted]";}
}
