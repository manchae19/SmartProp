package vn.smartprop.auth.google;
import java.time.*;
import java.util.*;
import jakarta.servlet.http.*;
import org.springframework.http.ResponseCookie;
import org.springframework.security.oauth2.client.web.AuthorizationRequestRepository;
import org.springframework.security.oauth2.core.endpoint.OAuth2AuthorizationRequest;
import org.springframework.stereotype.Component;
import vn.smartprop.auth.SecretTokens;
import vn.smartprop.common.*;

/** Short-lived server state; the browser sees only opaque HttpOnly handles. */
@Component
public class GoogleFlowStore implements AuthorizationRequestRepository<OAuth2AuthorizationRequest> {
    private static final String FLOW="SMARTPROP_GOOGLE_FLOW",TICKET="SMARTPROP_GOOGLE_TICKET";
    private record Pending(OAuth2AuthorizationRequest request,Instant expires){}
    private record Ticket(GoogleProfile profile,Instant expires){}
    private final Map<String,Pending> pending=new HashMap<>();private final Map<String,Ticket> tickets=new HashMap<>();
    private final Clock clock;private final GoogleSettings settings;
    public GoogleFlowStore(Clock clock,GoogleSettings settings){this.clock=clock;this.settings=settings;}
    private void prune(){Instant now=clock.instant();pending.values().removeIf(p->!p.expires.isAfter(now));tickets.values().removeIf(p->!p.expires.isAfter(now));}
    private String cookie(HttpServletRequest request,String name){if(request.getCookies()!=null)for(var cookie:request.getCookies())if(cookie.getName().equals(name)&&cookie.getValue().matches("[A-Za-z0-9_-]{43}"))return cookie.getValue();return null;}
    private void set(HttpServletResponse response,String name,String value,int seconds){response.addHeader("Set-Cookie",ResponseCookie.from(name,value).httpOnly(true).secure(settings.secure).sameSite(name.equals(TICKET)?"Strict":"Lax").path("/api/v1/auth/oauth2").maxAge(seconds).build().toString());response.setHeader("Cache-Control","no-store");response.setHeader("Referrer-Policy","no-referrer");}
    @Override public synchronized OAuth2AuthorizationRequest loadAuthorizationRequest(HttpServletRequest request){prune();String raw=cookie(request,FLOW);var value=raw==null?null:pending.get(SecretTokens.hash(raw));if(value==null||!SecretTokens.equal(value.request.getState(),request.getParameter("state")))return null;return value.request;}
    @Override public synchronized void saveAuthorizationRequest(OAuth2AuthorizationRequest value,HttpServletRequest request,HttpServletResponse response){
        prune();String old=cookie(request,FLOW);if(old!=null)pending.remove(SecretTokens.hash(old));
        if(value==null){set(response,FLOW,"",0);return;}if(pending.size()>=1000)throw new ApiException(429,"RATE_LIMITED","Vui lòng thử lại sau.");
        String raw=SecretTokens.random();pending.put(SecretTokens.hash(raw),new Pending(value,clock.instant().plusSeconds(300)));set(response,FLOW,raw,300);
    }
    @Override public synchronized OAuth2AuthorizationRequest removeAuthorizationRequest(HttpServletRequest request,HttpServletResponse response){var result=loadAuthorizationRequest(request);String raw=cookie(request,FLOW);if(raw!=null)pending.remove(SecretTokens.hash(raw));set(response,FLOW,"",0);return result;}
    public synchronized void handoff(GoogleProfile profile,HttpServletResponse response){prune();if(tickets.size()>=1000)throw new ApiException(429,"RATE_LIMITED","Vui lòng thử lại sau.");String raw=SecretTokens.random();tickets.put(SecretTokens.hash(raw),new Ticket(profile,clock.instant().plusSeconds(60)));set(response,TICKET,raw,60);}
    public synchronized GoogleProfile consume(HttpServletRequest request,HttpServletResponse response){prune();String raw=cookie(request,TICKET);var ticket=raw==null?null:tickets.remove(SecretTokens.hash(raw));set(response,TICKET,"",0);if(ticket==null)throw new ApiException(401,"GOOGLE_LOGIN_EXPIRED","Lượt đăng nhập Google đã hết hạn. Vui lòng bắt đầu lại.");return ticket.profile;}
}
