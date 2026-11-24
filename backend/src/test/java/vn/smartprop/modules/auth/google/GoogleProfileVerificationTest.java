package vn.smartprop.modules.auth.google;

import static org.junit.jupiter.api.Assertions.*;
import java.time.Instant;
import java.util.Date;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.security.oauth2.core.OAuth2AuthenticationException;
import org.springframework.security.oauth2.core.oidc.OidcIdToken;

class GoogleProfileVerificationTest {
    private static final Instant NOW = Instant.parse("2026-11-24T00:00:00Z");

    @Test void acceptsVerifiedTokenForConfiguredAudience() {
        assertEquals("google-sub", GoogleProfile.verified(token("client", true, NOW.plusSeconds(60)), "client", NOW).subject());
    }

    @Test void rejectsWrongAudienceExpiredOrUnverifiedIdentity() {
        assertThrows(OAuth2AuthenticationException.class, () -> GoogleProfile.verified(token("other", true, NOW.plusSeconds(60)), "client", NOW));
        assertThrows(OAuth2AuthenticationException.class, () -> GoogleProfile.verified(token("client", true, NOW.minusSeconds(1)), "client", NOW));
        assertThrows(OAuth2AuthenticationException.class, () -> GoogleProfile.verified(token("client", false, NOW.plusSeconds(60)), "client", NOW));
    }

    private OidcIdToken token(String audience, boolean verified, Instant expires) {
        Instant issued = NOW.minusSeconds(10);
        Map<String, Object> claims = Map.of("iss", "https://accounts.google.com", "sub", "google-sub",
            "aud", List.of(audience), "iat", Date.from(issued), "exp", Date.from(expires),
            "email", "Person@Example.test", "email_verified", verified, "name", "Person");
        return new OidcIdToken("opaque-test-token", issued, expires, claims);
    }
}
