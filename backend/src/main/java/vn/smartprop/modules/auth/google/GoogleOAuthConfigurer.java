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
import org.springframework.http.HttpMethod;
import org.springframework.http.client.BufferingClientHttpRequestFactory;
import org.springframework.http.client.ClientHttpResponse;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.http.converter.FormHttpMessageConverter;
import org.springframework.security.oauth2.client.http.OAuth2ErrorResponseErrorHandler;
import org.springframework.security.oauth2.core.http.converter.OAuth2AccessTokenResponseHttpMessageConverter;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.ResponseErrorHandler;
import org.springframework.web.client.RestTemplate;
import java.net.URI;
import vn.smartprop.common.*;
import vn.smartprop.config.*;

/** Protocol validation (signature, issuer, audience, timestamps, nonce) stays in Spring Security OIDC. */
@Component
public class GoogleOAuthConfigurer {
    private static final org.slf4j.Logger LOG=org.slf4j.LoggerFactory.getLogger(GoogleOAuthConfigurer.class);
    private static final java.util.Set<String> SAFE_TOKEN_ERRORS=java.util.Set.of("invalid_client","invalid_grant","invalid_request","redirect_uri_mismatch","unauthorized_client","unsupported_grant_type","invalid_scope","server_error","temporarily_unavailable","access_denied");
    private final GoogleSettings settings;private final GoogleFlowStore store;private final GoogleLinkFlowStore linking;private final RequestLimits limits;private final Clock clock;private final boolean refresh;private final ObjectMapper json;private final ObjectProvider<OAuth2AccessTokenResponseClient<OAuth2AuthorizationCodeGrantRequest>> tokenClients;
    public GoogleOAuthConfigurer(GoogleSettings settings,GoogleFlowStore store,GoogleLinkFlowStore linking,RequestLimits limits,Clock clock,ObjectMapper json,ObjectProvider<OAuth2AccessTokenResponseClient<OAuth2AuthorizationCodeGrantRequest>> tokenClients,@Value("${app.refresh.enabled:false}") boolean refresh){this.settings=settings;this.store=store;this.linking=linking;this.limits=limits;this.clock=clock;this.json=json;this.tokenClients=tokenClients;this.refresh=refresh;}
    public ClientRegistration registration(){return ClientRegistration.withRegistrationId("google").clientName("Google").clientId(settings.clientId).clientSecret(settings.clientSecret).clientAuthenticationMethod(ClientAuthenticationMethod.CLIENT_SECRET_POST).authorizationGrantType(AuthorizationGrantType.AUTHORIZATION_CODE).redirectUri(settings.redirectUri).scope("openid","email","profile").authorizationUri("https://accounts.google.com/o/oauth2/v2/auth").tokenUri("https://oauth2.googleapis.com/token").jwkSetUri("https://www.googleapis.com/oauth2/v3/certs").issuerUri("https://accounts.google.com").userInfoUri("https://openidconnect.googleapis.com/v1/userinfo").userNameAttributeName("sub").build();}
    public OAuth2AuthorizationRequestResolver resolver(ClientRegistrationRepository repository){
        var login=new DefaultOAuth2AuthorizationRequestResolver(repository,"/api/v1/auth/oauth2/authorize");login.setAuthorizationRequestCustomizer(OAuth2AuthorizationRequestCustomizers.withPkce());
        var link=new DefaultOAuth2AuthorizationRequestResolver(repository,"/api/v1/auth/oauth2/link/authorize");var pkce=OAuth2AuthorizationRequestCustomizers.withPkce();link.setAuthorizationRequestCustomizer(builder->{pkce.accept(builder);builder.attributes(attributes->attributes.put("smartprop_flow","link"));});
        return new OAuth2AuthorizationRequestResolver(){
            @Override public OAuth2AuthorizationRequest resolve(HttpServletRequest request){String path=request.getRequestURI();return path.startsWith("/api/v1/auth/oauth2/link/authorize/")?link.resolve(request):login.resolve(request);}
            @Override public OAuth2AuthorizationRequest resolve(HttpServletRequest request,String clientId){String path=request.getRequestURI();return path.startsWith("/api/v1/auth/oauth2/link/authorize/")?link.resolve(request,clientId):login.resolve(request,clientId);}
        };
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
            String path=request.getRequestURI();if(path.equals("/api/v1/auth/oauth2/authorize/google")||path.equals("/api/v1/auth/oauth2/link/authorize/google"))try{boolean isLink=path.contains("/link/");limits.check((isLink?"google:link:authorize:":"google:start:")+request.getRemoteAddr(),10,60);if(!settings.secure&&(!java.util.Set.of("127.0.0.1","localhost").contains(request.getServerName())||!java.util.Set.of("127.0.0.1","::1","0:0:0:0:0:0:0:1").contains(request.getRemoteAddr())))throw ApiInputs.forbidden();if(isLink){String origin=request.getHeader("Origin"),fetchSite=request.getHeader("Sec-Fetch-Site");if(origin!=null&&!settings.frontendOrigin.equals(origin)||"cross-site".equalsIgnoreCase(fetchSite))throw ApiInputs.forbidden();if(!linking.hasPendingStart(request))throw new ApiException(401,"GOOGLE_LINK_REQUIRED","Vui lòng bắt đầu liên kết từ phần Bảo mật của tài khoản SmartProp.");}}catch(ApiException error){response.setStatus(error.status);response.setContentType("application/json");response.setCharacterEncoding("UTF-8");response.setHeader("Cache-Control","no-store");if(error instanceof RequestLimits.Exceeded limit)response.setHeader("Retry-After",String.valueOf(limit.retryAfter));json.writeValue(response.getWriter(),Errors.body(error.code,error.getMessage()));return;}chain.doFilter(request,response);
        }},OAuth2AuthorizationRequestRedirectFilter.class);
        var diagnostics=new TokenExchangeDiagnostics(json);
        var configuredDelegate=tokenClients.getIfAvailable();
        final var delegate=configuredDelegate==null?diagnosticDefaultTokenClient(diagnostics):configuredDelegate;
        OAuth2AccessTokenResponseClient<OAuth2AuthorizationCodeGrantRequest> tokenClient=grant->{diagnostics.begin();try{return delegate.getTokenResponse(grant);}catch(RuntimeException error){diagnostics.logFailure(error);throw error;}finally{diagnostics.clear();}};
        http.requestCache(cache->cache.disable()).oauth2Login(oauth->oauth.clientRegistrationRepository(repository).authorizedClientRepository(clients)
            .authorizationEndpoint(endpoint->endpoint.baseUri("/api/v1/auth/oauth2/authorize").authorizationRequestResolver(resolver(repository)).authorizationRequestRepository(store))
            .redirectionEndpoint(endpoint->endpoint.baseUri("/api/v1/auth/oauth2/callback/*"))
            .tokenEndpoint(endpoint->endpoint.accessTokenResponseClient(tokenClient))
            .userInfoEndpoint(endpoint->endpoint.oidcUserService(request->{var token=request.getIdToken();GoogleProfile.verified(token,settings.clientId,clock.instant());return new DefaultOidcUser(java.util.List.of(new OidcUserAuthority(token)),token,"sub");}))
            .successHandler((request,response,authentication)->{boolean isLink=store.isLinkCallbackFlow(request);try{var user=(OidcUser)authentication.getPrincipal();var profile=GoogleProfile.verified(user.getIdToken(),settings.clientId,clock.instant());if(isLink){linking.handoff(profile,request,response);response.sendRedirect(settings.frontendOrigin+"/auth/google/link/complete");}else{store.handoff(profile,response);response.sendRedirect(settings.frontendOrigin+"/auth/google/complete");}SecurityContextHolder.clearContext();}catch(OAuth2AuthenticationException failure){audit(failure);if(isLink)linking.fail(request,response);SecurityContextHolder.clearContext();response.sendRedirect(settings.frontendOrigin+(isLink?"/auth/google/link/complete?status=failed":"/login?reason=google-failed"));}catch(RuntimeException failure){if(isLink)linking.fail(request,response);SecurityContextHolder.clearContext();response.sendRedirect(settings.frontendOrigin+(isLink?"/auth/google/link/complete?status=failed":"/login?reason=google-failed"));}})
            .failureHandler((request,response,error)->{boolean isLink=store.isLinkCallbackFlow(request);audit(error);if(isLink)linking.fail(request,response);SecurityContextHolder.clearContext();response.setHeader("Cache-Control","no-store");response.setHeader("Referrer-Policy","no-referrer");response.sendRedirect(settings.frontendOrigin+(isLink?"/auth/google/link/complete?status=failed":"/login?reason=google-failed"));}));
    }
    private static OAuth2AccessTokenResponseClient<OAuth2AuthorizationCodeGrantRequest> diagnosticDefaultTokenClient(TokenExchangeDiagnostics diagnostics){
        var client=new DefaultAuthorizationCodeTokenResponseClient();
        var rest=new RestTemplate(java.util.List.of(new FormHttpMessageConverter(),new OAuth2AccessTokenResponseHttpMessageConverter()));
        rest.setRequestFactory(new BufferingClientHttpRequestFactory(new SimpleClientHttpRequestFactory()));
        rest.getInterceptors().add((request,body,execution)->{var response=execution.execute(request,body);diagnostics.captureStatus(response);return response;});
        var oauthErrors=new OAuth2ErrorResponseErrorHandler();
        rest.setErrorHandler(new ResponseErrorHandler(){
            @Override public boolean hasError(ClientHttpResponse response)throws IOException{return oauthErrors.hasError(response);}
            @Override public void handleError(URI url,HttpMethod method,ClientHttpResponse response)throws IOException{diagnostics.captureOAuthError(response);oauthErrors.handleError(url,method,response);}
        });
        client.setRestOperations(rest);
        return client;
    }
    private static String safeOAuthError(String code){if("invalid_token_response".equals(code))return "malformed_response";return code!=null&&SAFE_TOKEN_ERRORS.contains(code)?code:"rejected";}
    private static void audit(org.springframework.security.core.AuthenticationException error){String code=error instanceof OAuth2AuthenticationException oidc?oidc.getError().getErrorCode():"rejected";if(!java.util.Set.of("invalid_nonce","invalid_id_token","invalid_state_parameter","authorization_request_not_found","invalid_token_response","access_denied").contains(code))code="rejected";LOG.warn("Google authentication rejected: {}",code);}

    private static final class TokenExchangeDiagnostics {
        private record Exchange(int[] status,String[] oauthError){}
        private final ObjectMapper mapper;private final ThreadLocal<Exchange> current=new ThreadLocal<>();
        private TokenExchangeDiagnostics(ObjectMapper mapper){this.mapper=mapper;}
        private void begin(){current.set(new Exchange(new int[]{-1},new String[]{null}));}
        private void clear(){current.remove();}
        private void captureStatus(ClientHttpResponse response)throws IOException{var exchange=current.get();if(exchange!=null)exchange.status()[0]=response.getStatusCode().value();}
        private void captureOAuthError(ClientHttpResponse response){var exchange=current.get();if(exchange==null)return;try{var body=mapper.readTree(response.getBody());var error=body==null?null:body.get("error");exchange.oauthError()[0]=error!=null&&error.isTextual()?safeOAuthError(error.textValue()):"malformed_response";}catch(Exception ignored){exchange.oauthError()[0]="malformed_response";}}
        private void logFailure(RuntimeException failure){
            var exchange=current.get();String status="unavailable",code="malformed_response";
            if(exchange!=null){if(exchange.status()[0]>=100&&exchange.status()[0]<=599)status=Integer.toString(exchange.status()[0]);if(exchange.oauthError()[0]!=null)code=exchange.oauthError()[0];}
            if(exchange==null||exchange.oauthError()[0]==null){
                if(failure instanceof ResourceAccessException)code="transport_error";
                else if(failure instanceof OAuth2AuthenticationException oauth)code=safeOAuthError(oauth.getError().getErrorCode());
            }
            LOG.warn("Google token exchange failed: http_status={} oauth_error={}",status,code);
        }
    }
}
