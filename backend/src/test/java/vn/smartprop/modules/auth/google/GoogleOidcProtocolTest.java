package vn.smartprop.modules.auth.google;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.nimbusds.jose.JOSEException;
import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.JWSHeader;
import com.nimbusds.jose.crypto.RSASSASigner;
import com.nimbusds.jose.jwk.RSAKey;
import com.nimbusds.jose.jwk.gen.RSAKeyGenerator;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.SignedJWT;
import java.time.Clock;
import java.time.Instant;
import java.util.Date;
import java.util.List;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.security.oauth2.client.authentication.OAuth2LoginAuthenticationToken;
import org.springframework.security.oauth2.client.endpoint.OAuth2AuthorizationCodeGrantRequestEntityConverter;
import org.springframework.security.oauth2.client.oidc.authentication.OidcAuthorizationCodeAuthenticationProvider;
import org.springframework.security.oauth2.client.oidc.authentication.OidcIdTokenValidator;
import org.springframework.security.oauth2.client.registration.InMemoryClientRegistrationRepository;
import org.springframework.security.oauth2.core.OAuth2AccessToken;
import org.springframework.security.oauth2.core.OAuth2AuthenticationException;
import org.springframework.security.oauth2.core.OAuth2Error;
import org.springframework.security.oauth2.core.endpoint.OAuth2AccessTokenResponse;
import org.springframework.security.oauth2.core.endpoint.OAuth2AuthorizationExchange;
import org.springframework.security.oauth2.core.endpoint.OAuth2AuthorizationRequest;
import org.springframework.security.oauth2.core.endpoint.OAuth2AuthorizationResponse;
import org.springframework.security.oauth2.core.oidc.user.DefaultOidcUser;
import org.springframework.security.oauth2.core.oidc.user.OidcUserAuthority;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import vn.smartprop.common.RequestLimits;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.mock;

class GoogleOidcProtocolTest {
    private static final String ORIGIN = "http://127.0.0.1:5173";
    private static final String ISSUER = "https://accounts.google.com";
    private static final String CLIENT = "pr40-fixture.apps.googleusercontent.com";
    private static final String CALLBACK = ORIGIN + "/api/v1/auth/oauth2/callback/google";
    private static RSAKey trustedKey;
    private static RSAKey differentKey;

    enum Result { VALID, WRONG_ISSUER, WRONG_AUDIENCE, WRONG_NONCE, EXPIRED, WRONG_SIGNATURE, INVALID_VERIFIER, WRONG_STATE }

    @BeforeAll static void keys() throws JOSEException {
        trustedKey = new RSAKeyGenerator(2048).generate();
        differentKey = new RSAKeyGenerator(2048).generate();
    }

    @Test void verifiedSubjectIsAvailableInSignInAndLinkFlows() throws JOSEException {
        assertEquals("fixture-subject", authenticate(false, Result.VALID).getPrincipal().getName());
        assertEquals("fixture-subject", authenticate(true, Result.VALID).getPrincipal().getName());
    }

    @ParameterizedTest
    @EnumSource(value = Result.class, names = "VALID", mode = EnumSource.Mode.EXCLUDE)
    void rejectsInvalidInputBeforeLinkCompletion(Result result) {
        assertThrows(OAuth2AuthenticationException.class, () -> authenticate(true, result));
    }

    private OAuth2LoginAuthenticationToken authenticate(boolean linking, Result result) throws JOSEException {
        var clock = Clock.systemUTC();
        var settings = new GoogleSettings(true, CLIENT, "fixture-only", CALLBACK, ORIGIN, false, ORIGIN);
        var config = new GoogleOAuthConfigurer(settings, mock(GoogleFlowStore.class),
            mock(GoogleLinkFlowStore.class), new RequestLimits(), clock, new ObjectMapper(), null, true);
        var registration = config.registration();
        var resolver = config.resolver(new InMemoryClientRegistrationRepository(registration));
        String path = "/api/v1/auth/oauth2/" + (linking ? "link/" : "") + "authorize/google";
        var servlet = new MockHttpServletRequest("GET", path);
        servlet.setServletPath(path);
        var request = resolver.resolve(servlet);
        assertNotNull(request);
        assertEquals(CALLBACK, request.getRedirectUri());
        String verifier = request.getAttribute("code_verifier");
        assertNotNull(verifier);
        assertEquals("S256", request.getAdditionalParameters().get("code_challenge_method"));
        String nonce = (String) request.getAdditionalParameters().get("nonce");
        assertNotNull(nonce);
        var signedToken = signToken(result, nonce);
        var provider = new OidcAuthorizationCodeAuthenticationProvider(grant -> {
            var form = new OAuth2AuthorizationCodeGrantRequestEntityConverter().convert(grant).getBody();
            assertInstanceOf(org.springframework.util.MultiValueMap.class, form);
            var parameters = (org.springframework.util.MultiValueMap<?, ?>) form;
            assertEquals(List.of(CALLBACK), parameters.get("redirect_uri"));
            if (!List.of(verifier).equals(parameters.get("code_verifier"))) {
                throw new OAuth2AuthenticationException(new OAuth2Error("invalid_grant"));
            }
            return OAuth2AccessTokenResponse.withToken("fixture-access")
                .tokenType(OAuth2AccessToken.TokenType.BEARER).expiresIn(120)
                .additionalParameters(java.util.Map.of("id_token", signedToken)).build();
        }, user -> {
            GoogleProfile.verified(user.getIdToken(), CLIENT, clock.instant());
            return new DefaultOidcUser(List.of(new OidcUserAuthority(user.getIdToken())), user.getIdToken(), "sub");
        });
        var decoder = NimbusJwtDecoder.withPublicKey(trustedKey.toRSAPublicKey()).build();
        decoder.setJwtValidator(new OidcIdTokenValidator(registration));
        provider.setJwtDecoderFactory(ignored -> decoder);
        if (result == Result.INVALID_VERIFIER) {
            request = OAuth2AuthorizationRequest.from(request)
                .attributes(values -> values.put("code_verifier", "incorrect-fixture-verifier")).build();
        }
        var response = OAuth2AuthorizationResponse.success("fixture-authorization-code")
            .state(result == Result.WRONG_STATE ? "unrelated-fixture-state" : request.getState())
            .redirectUri(CALLBACK).build();
        return (OAuth2LoginAuthenticationToken) provider.authenticate(
            new OAuth2LoginAuthenticationToken(registration, new OAuth2AuthorizationExchange(request, response)));
    }

    private String signToken(Result result, String nonce) throws JOSEException {
        var now = Instant.now();
        var claims = new JWTClaimsSet.Builder()
            .issuer(result == Result.WRONG_ISSUER ? "https://other.example.test" : ISSUER)
            .audience(result == Result.WRONG_AUDIENCE ? "other-client" : CLIENT)
            .subject("fixture-subject").claim("email", "owner@example.test").claim("email_verified", true)
            .claim("nonce", result == Result.WRONG_NONCE ? "different-fixture-nonce" : nonce)
            .issueTime(Date.from(now.minusSeconds(result == Result.EXPIRED ? 600 : 1)))
            .expirationTime(Date.from(now.plusSeconds(result == Result.EXPIRED ? -300 : 120))).build();
        var jwt = new SignedJWT(new JWSHeader(JWSAlgorithm.RS256), claims);
        jwt.sign(new RSASSASigner(result == Result.WRONG_SIGNATURE ? differentKey : trustedKey));
        return jwt.serialize();
    }
}
