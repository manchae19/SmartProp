package vn.smartprop.security;
import vn.smartprop.modules.auth.AuthSession;
import vn.smartprop.modules.auth.SessionPolicy;
import vn.smartprop.modules.auth.SessionRepository;
import com.nimbusds.jose.jwk.source.ImmutableSecret;
import jakarta.servlet.http.*;
import org.springframework.http.HttpMethod;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.*;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.*;
import org.springframework.core.convert.converter.Converter;
import org.springframework.security.authentication.AbstractAuthenticationToken;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.config.annotation.ObjectPostProcessor;
import org.springframework.security.oauth2.core.*;
import org.springframework.security.oauth2.server.resource.web.DefaultBearerTokenResolver;
import org.springframework.security.web.csrf.CsrfFilter;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.*;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.*;
import vn.smartprop.common.Errors;
import vn.smartprop.modules.user.*;
@Configuration
public class SecurityConfig {
    @Bean PasswordEncoder passwordEncoder() { return new BCryptPasswordEncoder(12); }
    @Bean SecretKeySpec jwtKey(@Value("${app.jwt-secret}") String secret) {
        byte[] bytes=secret.getBytes(StandardCharsets.UTF_8);
        if(bytes.length<32) throw new IllegalStateException("JWT_SECRET must contain at least 32 UTF-8 bytes");
        return new SecretKeySpec(bytes,"HmacSHA256");
    }
    @Bean JwtEncoder jwtEncoder(SecretKeySpec key) { return new NimbusJwtEncoder(new ImmutableSecret<>(key)); }
    @Bean JwtDecoder jwtDecoder(SecretKeySpec key,SessionRepository sessions,UserRepository users,SessionPolicy policy,java.time.Clock clock) {
        NimbusJwtDecoder decoder=NimbusJwtDecoder.withSecretKey(key).macAlgorithm(MacAlgorithm.HS256).build();
        OAuth2TokenValidator<Jwt> liveSession=jwt -> {
            try {
                if(jwt.getId()==null || jwt.getSubject()==null || jwt.getExpiresAt()==null ||
                   !jwt.getExpiresAt().isAfter(clock.instant()))
                    return OAuth2TokenValidatorResult.failure(new OAuth2Error("invalid_token"));
                AuthSession s=sessions.findById(jwt.getId()).orElse(null);
                User u=users.findById(Long.valueOf(jwt.getSubject())).orElse(null);
                if(s!=null && u!=null && s.userId.equals(u.id) && !s.revoked &&
                   policy.valid(s,u) && u.status==User.Status.ACTIVE && u.deletedAt==null && versionMatches(jwt,u.tokenVersion))
                    return OAuth2TokenValidatorResult.success();
            } catch(IllegalArgumentException | NullPointerException ignored) { }
            return OAuth2TokenValidatorResult.failure(new OAuth2Error("invalid_token","Invalid or revoked session",null));
        };
        var timestamp=new JwtTimestampValidator(java.time.Duration.ZERO);timestamp.setClock(clock);
        decoder.setJwtValidator(new DelegatingOAuth2TokenValidator<>(timestamp,new JwtIssuerValidator("smartprop"),liveSession));
        return decoder;
    }
    @Bean SecurityFilterChain security(HttpSecurity http,UserRepository users,ObjectMapper mapper,
                                      LoginThrottle throttle,SessionRepository sessions,SessionPolicy policy,@Value("${app.cors-origins}") String origins,@Value("${app.refresh.enabled:false}") boolean refreshEnabled,@Value("${app.refresh.secure-cookie:true}") boolean secureCookie,org.springframework.beans.factory.ObjectProvider<vn.smartprop.modules.auth.google.GoogleOAuthConfigurer> google) throws Exception {
        Converter<Jwt,AbstractAuthenticationToken> converter=jwt -> {
            User u=users.findById(Long.valueOf(jwt.getSubject())).orElseThrow(() -> new OAuth2AuthenticationException(new OAuth2Error("invalid_token")));
            if(u.status!=User.Status.ACTIVE || u.deletedAt!=null || !versionMatches(jwt,u.tokenVersion))
                throw new OAuth2AuthenticationException(new OAuth2Error("invalid_token"));
            return new JwtAuthenticationToken(jwt,List.of(new SimpleGrantedAuthority("ROLE_"+u.role.name())));
        };
        CorsConfiguration cors=new CorsConfiguration();
        cors.setAllowedOrigins(Arrays.stream(origins.split(",")).map(String::strip).toList());
        cors.setAllowedMethods(List.of("GET","POST","PATCH","PUT","DELETE","OPTIONS"));
        cors.setAllowedHeaders(List.of("Authorization","Content-Type","X-Refresh-Session","X-CSRF-TOKEN","X-Session-Activity","Idempotency-Key"));
        cors.setAllowCredentials(refreshEnabled);
        UrlBasedCorsConfigurationSource source=new UrlBasedCorsConfigurationSource(); source.registerCorsConfiguration("/**",cors);
        var bearerTokens = new DefaultBearerTokenResolver();
        if(refreshEnabled){
            var csrfRepository=new org.springframework.security.web.csrf.CookieCsrfTokenRepository();csrfRepository.setHeaderName("X-CSRF-TOKEN");
            csrfRepository.setCookieCustomizer(c->c.httpOnly(true).secure(secureCookie).sameSite("Lax").path("/api/v1/auth"));
            http.csrf(c -> c.csrfTokenRepository(csrfRepository)
                .csrfTokenRequestHandler(new org.springframework.security.web.csrf.CsrfTokenRequestAttributeHandler())
                .requireCsrfProtectionMatcher(SecurityConfig::requiresCsrf)
                .withObjectPostProcessor(new ObjectPostProcessor<CsrfFilter>() {
                    @Override public <O extends CsrfFilter> O postProcess(O filter) {
                        // Keep Spring's bearer exemption for existing routes. Linking also changes account ownership credentials.
                        filter.setRequireCsrfProtectionMatcher(request -> googleLinkWrite(request)
                            || requiresCsrf(request) && !hasBearerToken(bearerTokens, request));
                        return filter;
                    }
                }));
        }else http.csrf(c->c.disable());
        var googleLogin=google.getIfAvailable();if(googleLogin!=null)googleLogin.configure(http);
        http.cors(c -> c.configurationSource(source))
            .sessionManagement(c -> c.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(c -> c
                .requestMatchers("/api/v1/auth/csrf","/api/v1/auth/refresh","/api/v1/auth/email-verification/confirm","/api/v1/auth/password/forgot","/api/v1/auth/password/reset").permitAll()
                .requestMatchers("/api/v1/auth/google/config","/api/v1/auth/oauth2/authorize/google","/api/v1/auth/oauth2/callback/google","/api/v1/auth/oauth2/complete").permitAll()
                .requestMatchers("/api/v1/auth/oauth2/link/authorize/google").permitAll()
                .requestMatchers("/api/v1/auth/google/link/status","/api/v1/auth/google/link/start","/api/v1/auth/google/link/complete").authenticated()
                .requestMatchers("/api/v1/auth/register","/api/v1/auth/login","/actuator/health","/actuator/health/**").permitAll()
                .requestMatchers("/api/v1/auth/logout").access((authentication,context)->new org.springframework.security.authorization.AuthorizationDecision(refreshEnabled || authentication.get()!=null && authentication.get().isAuthenticated() && !(authentication.get() instanceof org.springframework.security.authentication.AnonymousAuthenticationToken)))
                .requestMatchers("/api/v1/users/me/sessions","/api/v1/users/me/sessions/*","/api/v1/auth/email-verification/request").authenticated()
                .requestMatchers("/api/v1/users/me/advisor-chats", "/api/v1/users/me/advisor-chats/**").authenticated()
                .requestMatchers("/api/v1/users/me/valuation-history","/api/v1/users/me/valuation-history/*").authenticated()
                .requestMatchers("/api/v1/users/me/avatar","/api/v1/users/me/avatar/content").authenticated()
                .requestMatchers("/api/v1/admin/**").hasRole("ADMIN")
                // Coordinate Provenance V1.
                // verify: chỉ admin. history: phải đăng nhập (controller kiểm tra owner/admin).
                // coordinate: công khai cho tin PUBLISHED; controller chặn tin chưa công khai.
                .requestMatchers(HttpMethod.POST,"/api/v1/properties/*/coordinate/verify").hasRole("ADMIN")
                .requestMatchers(HttpMethod.GET,"/api/v1/properties/*/coordinate/history").authenticated()
                .requestMatchers(HttpMethod.GET,"/api/v1/properties/*/coordinate").permitAll()
                .requestMatchers(HttpMethod.GET,"/api/v1/users/me/advisor-context").authenticated()
                .requestMatchers(HttpMethod.GET,"/api/v1/users/me/broker-application","/api/v1/users/me/properties/*/moderation").authenticated()
                .requestMatchers(HttpMethod.POST,"/api/v1/users/me/broker-application").authenticated()
                .requestMatchers("/api/v1/conversations","/api/v1/users/me/conversations","/api/v1/conversations/*/messages","/api/v1/conversations/*/read").authenticated()
                .requestMatchers("/api/v1/properties/*/legal-documents","/api/v1/properties/*/legal-documents/*","/api/v1/properties/*/legal-documents/*/content").authenticated()
                .requestMatchers(HttpMethod.GET,"/api/v1/users/me/notifications","/api/v1/users/me/notifications/unread-count").authenticated()
                .requestMatchers(HttpMethod.PATCH,"/api/v1/users/me/notifications/*/read").authenticated()
                .requestMatchers(HttpMethod.POST,"/api/v1/users/me/notifications/read-all").authenticated()
                .requestMatchers(HttpMethod.GET,"/api/v1/properties/*/contact").authenticated()
                .requestMatchers(HttpMethod.GET,"/api/v1/properties/valuation-options").hasAnyRole("BROKER","ADMIN")
                .requestMatchers(HttpMethod.GET,"/api/v1/properties/*/image-scan").permitAll()
                .requestMatchers(HttpMethod.POST,"/api/v1/properties/*/image-scan/retry").hasAnyRole("BROKER","ADMIN")
                // YOLOv8 object analysis mirrors the duplicate scanner: public read
                // for a public listing (the controller still checks visibility),
                // retry restricted to publishers.
                .requestMatchers(HttpMethod.GET,"/api/v1/properties/*/image-analysis").permitAll()
                .requestMatchers(HttpMethod.POST,"/api/v1/properties/*/image-analysis/retry").hasAnyRole("BROKER","ADMIN")
                .requestMatchers(HttpMethod.POST,"/api/v1/properties/valuation-preview","/api/v1/properties/comparables").hasAnyRole("BROKER","ADMIN")
                .requestMatchers(HttpMethod.GET,"/api/v1/amenities/research/**").hasRole("ADMIN")
                // News: ba endpoint đọc công khai. Không có thao tác ghi công khai.
                .requestMatchers(HttpMethod.GET,"/api/v1/news","/api/v1/news/featured","/api/v1/news/sources").permitAll()
                .requestMatchers(HttpMethod.GET,"/api/v1/properties","/api/v1/properties/map","/api/v1/properties/*","/api/v1/properties/*/points-of-interest","/api/v1/properties/*/nearby","/api/v1/properties/*/route","/api/v1/properties/*/commute","/api/v1/properties/*/images/*/content","/api/v1/properties/*/pre-purchase-checks","/api/v1/projects","/api/v1/projects/*","/api/v1/amenities/**").permitAll()
                .requestMatchers(HttpMethod.POST,"/api/v1/geocoding/search").hasAnyRole("BROKER","ADMIN")
                // Advisor chat is anonymous; this route requires per-call consent and is IP-capped.
                .requestMatchers(HttpMethod.POST,"/api/v1/advisor/geocoding","/api/v1/advisor/commute-matrix").permitAll()
                .requestMatchers(HttpMethod.POST,"/api/v1/recommendations/research").hasRole("ADMIN")
                .requestMatchers(HttpMethod.GET,"/api/v1/recommendations/research/config").hasRole("ADMIN")
                .requestMatchers(HttpMethod.POST,"/api/v1/recommendations","/api/v1/advisor/consult").permitAll()
                .requestMatchers(HttpMethod.GET,"/api/v1/geocoding/config").hasAnyRole("BROKER","ADMIN")
                .requestMatchers(HttpMethod.POST,"/api/v1/properties","/api/v1/properties/*/submit","/api/v1/properties/*/images").hasAnyRole("BROKER","ADMIN")
                .requestMatchers(HttpMethod.PATCH,"/api/v1/properties/*","/api/v1/properties/*/images/*").hasAnyRole("BROKER","ADMIN")
                .requestMatchers(HttpMethod.PUT,"/api/v1/properties/*/images/order").hasAnyRole("BROKER","ADMIN")
                .requestMatchers(HttpMethod.DELETE,"/api/v1/properties/*","/api/v1/properties/*/images/*").authenticated()
                .requestMatchers("/api/v1/users/me/notification-preferences","/api/v1/users/me/properties","/api/v1/users/me/properties/*","/api/v1/users/me/saved-properties","/api/v1/users/me/saved-properties/*","/api/v1/users/me/reports","/api/v1/reports/*","/api/v1/reports/*/attachments","/api/v1/reports/*/attachments/*/content","/api/v1/properties/*/reports","/api/v1/properties/*/close").authenticated()
                .requestMatchers("/api/v1/auth/logout","/api/v1/users/me","/api/v1/users/me/password").authenticated()
                .anyRequest().denyAll())
            .exceptionHandling(c -> c
                .authenticationEntryPoint((req,res,e) -> error(res,mapper,401,"UNAUTHENTICATED","Phiên không hợp lệ hoặc đã hết hạn"))
                .accessDeniedHandler((req,res,e) -> error(res,mapper,403,"FORBIDDEN","Bạn không có quyền truy cập")))
            .oauth2ResourceServer(c -> c.bearerTokenResolver(bearerTokens).jwt(j -> j.jwtAuthenticationConverter(converter))
                .authenticationEntryPoint((req,res,e) -> error(res,mapper,401,"UNAUTHENTICATED","Phiên không hợp lệ hoặc đã hết hạn")))
            .addFilterBefore(throttle,UsernamePasswordAuthenticationFilter.class)
            .addFilterAfter(new SessionActivityFilter(sessions,policy,mapper),org.springframework.security.oauth2.server.resource.web.authentication.BearerTokenAuthenticationFilter.class);
        return http.build();
    }
    private static boolean versionMatches(Jwt jwt,int expected) {
        Object version=jwt.getClaim("ver");
        return (version instanceof Integer || version instanceof Long) && ((Number)version).longValue()==expected;
    }
    static void error(HttpServletResponse response,ObjectMapper mapper,int status,String code,String message) throws java.io.IOException {
        response.setStatus(status); response.setContentType("application/json"); response.setCharacterEncoding("UTF-8");
        mapper.writeValue(response.getWriter(),Errors.body(code,message));
    }
    static boolean requiresCsrf(HttpServletRequest request) {
        if(!"POST".equals(request.getMethod()))return false;
        String path=request.getServletPath();if(path.isEmpty())path=request.getRequestURI();
        if(path.equals("/api/v1/auth/refresh")||path.equals("/api/v1/auth/oauth2/complete")||googleLinkWrite(request))return true;
        if(path.equals("/api/v1/auth/logout")&&request.getCookies()!=null)for(var cookie:request.getCookies())if(cookie.getName().equals("SMARTPROP_REFRESH"))return true;
        return false;
    }
    private static boolean googleLinkWrite(HttpServletRequest request) {
        if (!"POST".equals(request.getMethod())) return false;
        String path = request.getServletPath();
        if (path.isEmpty()) path = request.getRequestURI();
        return path.equals("/api/v1/auth/google/link/start") || path.equals("/api/v1/auth/google/link/complete");
    }

    private static boolean hasBearerToken(DefaultBearerTokenResolver resolver, HttpServletRequest request) {
        try {
            return resolver.resolve(request) != null;
        } catch (OAuth2AuthenticationException malformed) {
            return false;
        }
    }
}
