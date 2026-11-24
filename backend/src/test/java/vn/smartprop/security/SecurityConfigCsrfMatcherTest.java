package vn.smartprop.security;

import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;

class SecurityConfigCsrfMatcherTest {
    @Test void protectsLinkStartAndCompletionPostsButNotReadOnlyStatusOrOauthGet() {
        assertTrue(matches("POST", "/api/v1/auth/google/link/start"));
        assertTrue(matches("POST", "/api/v1/auth/google/link/complete"));
        assertFalse(matches("GET", "/api/v1/auth/google/link/status"));
        assertFalse(matches("GET", "/api/v1/auth/oauth2/link/authorize/google"));
        assertFalse(matches("GET", "/api/v1/auth/oauth2/callback/google"));
    }

    private boolean matches(String method, String path) {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setMethod(method);
        request.setServletPath(path);
        return SecurityConfig.requiresCsrf(request);
    }
}
