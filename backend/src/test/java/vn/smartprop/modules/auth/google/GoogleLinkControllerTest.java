package vn.smartprop.modules.auth.google;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.same;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.junit.jupiter.api.Test;
import org.springframework.security.oauth2.jwt.Jwt;
import vn.smartprop.common.ApiException;
import vn.smartprop.common.RequestLimits;
import vn.smartprop.modules.auth.RefreshController;
import vn.smartprop.modules.auth.RefreshService;

class GoogleLinkControllerTest {
    @Test void wrongPasswordDoesNotCreateOAuthFlow() {
        GoogleLinkService service = mock(GoogleLinkService.class);
        GoogleLinkFlowStore flows = mock(GoogleLinkFlowStore.class);
        GoogleSettings settings = mock(GoogleSettings.class);
        RefreshController cookies = mock(RefreshController.class);
        RefreshService refresh = mock(RefreshService.class);
        RequestLimits limits = mock(RequestLimits.class);
        GoogleLinkController controller = new GoogleLinkController(service, flows, settings, cookies, refresh, limits);
        Jwt jwt = Jwt.withTokenValue("test-only").header("alg", "HS256").subject("42").claim("jti", "test-session").build();
        HttpServletRequest request = mock(HttpServletRequest.class);
        HttpServletResponse response = mock(HttpServletResponse.class);
        ApiException wrongPassword = new ApiException(400, "WRONG_PASSWORD", "Mật khẩu hiện tại không chính xác");

        when(settings.configured()).thenReturn(true);
        when(refresh.enabled()).thenReturn(true);
        when(service.begin(jwt, "wrong")).thenThrow(wrongPassword);

        ApiException error = assertThrows(ApiException.class,
            () -> controller.start(jwt, new GoogleLinkController.StartRequest("wrong"), request, response));

        assertEquals(400, error.status);
        assertEquals("WRONG_PASSWORD", error.code);
        verify(service).begin(jwt, "wrong");
        verify(flows, never()).begin(anyLong(), anyString(), same(response));
    }
}
