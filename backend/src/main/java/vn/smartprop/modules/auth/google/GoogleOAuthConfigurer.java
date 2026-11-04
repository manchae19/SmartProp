package vn.smartprop.modules.auth.google;

import java.time.Clock;
import java.io.IOException;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.*;
import jakarta.servlet.http.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.client.*;
import org.springframework.security.oauth2.client.oidc.userinfo.OidcUserService;
import org.springframework.security.oauth2.client.registration.*;
import org.springframework.security.oauth2.client.web.*;
import org.springframework.security.oauth2.client.endpoint.*;
import org.springframework.security.oauth2.core.*;
import org.springframework.security.oauth2.core.endpoint.OAuth2AuthorizationRequest;
import org.springframework.security.oauth2.core.oidc.user.OidcUser;
import org.springframework.security.oauth2.core.oidc.user.DefaultOidcUser;
import org.springframework.security.oauth2.core.oidc.user.OidcUserAuthority;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import vn.smartprop.common.*;
import vn.smartprop.config.*;

/** Protocol validation (signature, issuer, audience, timestamps, nonce) stays in Spring Security OIDC. */
@Component
public class GoogleOAuthConfigurer {
    private final GoogleSettings settings;private final GoogleFlowStore store;private final RequestLimits limits;private final Clock clock;private final boolean refresh;private final ObjectMapper json;private final ObjectProvider<OAuth2AccessTokenResponseClient<OAuth2AuthorizationCodeGrantRequest>> tokenClients;
    public GoogleOAuthConfigurer(GoogleSettings settings,GoogleFlowStore store,RequestLimits limits,Clock clock,ObjectMapper json,ObjectProvider<OAuth2AccessTokenResponseClient<OAuth2AuthorizationCodeGrantRequest>> tokenClients,@Value("${app.refresh.enabled:false}") boolean refresh){this.settings=settings;this.store=store;this.limits=limits;this.clock=clock;this.json=json;this.tokenClients=tokenClients;this.refresh=refresh;}
    public ClientRegistration registration(){return ClientRegistration.withRegistrationId("google").clientName("Google").clientId(settings.clientId).clientSecret(settings.clientSecret).clientAuthenticationMethod(ClientAuthenticationMethod.CLIENT_SECRET_POST).authorizationGrantType(AuthorizationGrantType.AUTHORIZATION_CODE).redirectUri(settings.redirectUri).scope("openid","email","profile").authorizationUri("https://accounts.google.com/o/oauth2/v2/auth").tokenUri("https://oauth2.googleapis.com/token").jwkSetUri("https://www.googleapis.com/oauth2/v3/certs").issuerUri("https://accounts.google.com").userInfoUri("https://openidconnect.googleapis.com/v1/userinfo").userNameAttributeName("sub").build();}
    public OAuth2AuthorizationRequestResolver resolver(ClientRegistrationRepository repository){
        var delegate=new DefaultOAuth2AuthorizationRequestResolver(repository,"/api/v1/auth/oauth2/authorize");delegate.setAuthorizationRequestCustomizer(OAuth2AuthorizationRequestCustomizers.withPkce());
        return delegate;
    }
    public void configure(HttpSecurity http)throws Exception{
        if(!settings.configured()||!refresh)return;
        var repository=new InMemoryClientRegistrationRepository(registration());
        var clients=new OAuth2AuthorizedClientRepository(){
            @Override public <T extends OAuth2AuthorizedClient>T loadAuthorizedClient(String id,Authentication principal,HttpServletRequest request){return null;}
            @Override public void saveAuthorizedClient(OAuth2AuthorizedClient client,Authentication principal,HttpServletRequest request,HttpServletResponse response){}
            @Override public void removeAuthorizedClient(String id,Authentication principal,HttpServletRequest request,HttpServletResponse response){}
        };
        http.addFilterBefore(new OncePerRequestFilter(){@Override protected void doFilterInternal(HttpServletRequest request,HttpServletResponse response,FilterChain chain)throws ServletException,IOException{
            if(request.getRequestURI().equals("/api/v1/auth/oauth2/authorize/google"))try{limits.check("google:start:"+request.getRemoteAddr(),10,60);if(!settings.secure&&(!java.util.Set.of("127.0.0.1","localhost").contains(request.getServerName())||!java.util.Set.of("127.0.0.1","::1","0:0:0:0:0:0:0:1").contains(request.getRemoteAddr())))throw ApiInputs.forbidden();}catch(ApiException error){response.setStatus(error.status);response.setContentType("application/json");response.setCharacterEncoding("UTF-8");response.setHeader("Cache-Control","no-store");if(error instanceof RequestLimits.Exceeded limit)response.setHeader("Retry-After",String.valueOf(limit.retryAfter));json.writeValue(response.getWriter(),Errors.body(error.code,error.getMessage()));return;}chain.doFilter(request,response);
        }},OAuth2AuthorizationRequestRedirectFilter.class);
        http.requestCache(cache->cache.disable()).oauth2Login(oauth->oauth.clientRegistrationRepository(repository).authorizedClientRepository(clients)
            .authorizationEndpoint(endpoint->endpoint.baseUri("/api/v1/auth/oauth2/authorize").authorizationRequestResolver(resolver(repository)).authorizationRequestRepository(store))
            .redirectionEndpoint(endpoint->endpoint.baseUri("/api/v1/auth/oauth2/callback/*"))
            .tokenEndpoint(endpoint->{var configured=tokenClients.getIfAvailable();if(configured!=null)endpoint.accessTokenResponseClient(configured);})
            .userInfoEndpoint(endpoint->endpoint.oidcUserService(request->{var token=request.getIdToken();GoogleProfile.verified(token,settings.clientId,clock.instant());return new DefaultOidcUser(java.util.List.of(new OidcUserAuthority(token)),token,"sub");}))
            .successHandler((request,response,authentication)->{try{var user=(OidcUser)authentication.getPrincipal();store.handoff(GoogleProfile.verified(user.getIdToken(),settings.clientId,clock.instant()),response);SecurityContextHolder.clearContext();response.sendRedirect(settings.frontendOrigin+"/auth/google/complete");}catch(OAuth2AuthenticationException failure){audit(failure);SecurityContextHolder.clearContext();response.sendRedirect(settings.frontendOrigin+"/login?reason=google-failed");}})
            .failureHandler((request,response,error)->{audit(error);SecurityContextHolder.clearContext();response.setHeader("Cache-Control","no-store");response.setHeader("Referrer-Policy","no-referrer");response.sendRedirect(settings.frontendOrigin+"/login?reason=google-failed");}));
    }
    private static void audit(org.springframework.security.core.AuthenticationException error){String code=error instanceof OAuth2AuthenticationException oidc?oidc.getError().getErrorCode():"rejected";if(!java.util.Set.of("invalid_nonce","invalid_id_token","invalid_state_parameter","authorization_request_not_found","invalid_token_response","access_denied").contains(code))code="rejected";org.slf4j.LoggerFactory.getLogger(GoogleOAuthConfigurer.class).warn("Google authentication rejected: {}",code);}
}
