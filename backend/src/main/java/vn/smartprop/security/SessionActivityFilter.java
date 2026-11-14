package vn.smartprop.security;
import vn.smartprop.modules.auth.SessionPolicy;
import vn.smartprop.modules.auth.SessionRepository;

import jakarta.servlet.*;
import jakarta.servlet.http.*;
import java.io.IOException;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.web.filter.OncePerRequestFilter;
import com.fasterxml.jackson.databind.ObjectMapper;

/** Background polling carries no activity pulse and cannot keep an administrator signed in. */
public class SessionActivityFilter extends OncePerRequestFilter {
    private final SessionRepository sessions;private final SessionPolicy policy;private final ObjectMapper mapper;
    public SessionActivityFilter(SessionRepository sessions,SessionPolicy policy,ObjectMapper mapper){this.sessions=sessions;this.policy=policy;this.mapper=mapper;}
    @Override protected void doFilterInternal(HttpServletRequest request,HttpServletResponse response,FilterChain chain)throws ServletException,IOException {
        var authentication=SecurityContextHolder.getContext().getAuthentication();
        if("true".equals(request.getHeader("X-Session-Activity"))&&authentication instanceof JwtAuthenticationToken jwt&&jwt.getAuthorities().stream().anyMatch(a->a.getAuthority().equals("ROLE_ADMIN"))){
            var now=policy.now();if(sessions.touchActivity(jwt.getToken().getId(),now,now.minusSeconds(1800))!=1){SecurityConfig.error(response,mapper,401,"UNAUTHENTICATED","Phiên quản trị đã hết hạn");return;}
        }
        chain.doFilter(request,response);
    }
}
