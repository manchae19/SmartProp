package vn.smartprop.auth;
import jakarta.servlet.*;
import jakarta.servlet.http.*;
import java.io.IOException;
import java.time.*;
import java.util.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.web.filter.OncePerRequestFilter;
/** Single-instance fixed window limiter. Do not trust client-supplied forwarding headers. */
public class LoginThrottle extends OncePerRequestFilter {
    private record Window(Instant start,int count) {}
    private final Map<String,Window> windows=new HashMap<>();
    private final ObjectMapper mapper;
    public LoginThrottle(ObjectMapper mapper) { this.mapper=mapper; }
    public synchronized boolean allow(String key) {
        Instant now=Instant.now();
        windows.entrySet().removeIf(e -> e.getValue().start.plusSeconds(900).isBefore(now));
        Window w=windows.get(key);
        if(w==null) {
            if(windows.size()>=10000) return false;
            windows.put(key,new Window(now,1)); return true;
        }
        if(w.count>=20) return false;
        windows.put(key,new Window(w.start,w.count+1)); return true;
    }
    @Override protected void doFilterInternal(HttpServletRequest req,HttpServletResponse res,FilterChain chain) throws ServletException,IOException {
        String path=req.getServletPath();
        if(path.isEmpty()) path=req.getRequestURI().substring(req.getContextPath().length());
        if("POST".equals(req.getMethod()) && (path.equals("/api/v1/auth/login") || path.equals("/api/v1/auth/register")) && !allow(req.getRemoteAddr())) {
            res.setHeader("Retry-After","900");
            SecurityConfig.error(res,mapper,429,"RATE_LIMITED","Thử lại sau tối đa 15 phút"); return;
        }
        chain.doFilter(req,res);
    }
}
