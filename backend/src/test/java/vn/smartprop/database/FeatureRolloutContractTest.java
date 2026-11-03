package vn.smartprop.database;

import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.mock.web.MockMultipartFile;
import vn.smartprop.avatar.*;
import vn.smartprop.auth.google.*;
import vn.smartprop.broker.*;
import vn.smartprop.common.ApiException;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/** Existing feature policy regression; no database fixtures or writes. */
class FeatureRolloutContractTest {
    GoogleSettings google(String redirect,boolean secure){return new GoogleSettings(true,"test.apps.googleusercontent.com","unit-secret",redirect,"http://127.0.0.1:5173",secure,"http://127.0.0.1:5173");}
    @Test void googleLocalNeedsMatchingCallbackAndCookiePolicy(){
        assertTrue(google("http://127.0.0.1:5173/api/v1/auth/oauth2/callback/google",false).configured());
        assertFalse(google("http://attacker.invalid/callback",false).configured());
        assertFalse(google("http://127.0.0.1:5173/api/v1/auth/oauth2/callback/google",true).configured());
    }
    @Test void googleIdentityTableRequiredOnlyWhenConfiguredAndRefreshEnabled(){
        var jdbc=mock(JdbcTemplate.class);when(jdbc.queryForObject(anyString(),eq(Integer.class))).thenReturn(0);
        var settings=google("http://127.0.0.1:5173/api/v1/auth/oauth2/callback/google",false);
        assertThrows(IllegalStateException.class,()->new GoogleReadiness(settings,jdbc,true).run(null));
        assertDoesNotThrow(()->new GoogleReadiness(settings,jdbc,false).run(null));
        when(jdbc.queryForObject(anyString(),eq(Integer.class))).thenReturn(1);
        assertDoesNotThrow(()->new GoogleReadiness(settings,jdbc,true).run(null));
    }
    @Test void avatarCannotEnableWithMissingTable(){
        var jdbc=mock(JdbcTemplate.class);when(jdbc.queryForObject(anyString(),eq(Integer.class))).thenReturn(0);
        assertThrows(IllegalStateException.class,()->new AvatarReadiness(jdbc,true).run(null));
        assertDoesNotThrow(()->new AvatarReadiness(jdbc,false).run(null));
        when(jdbc.queryForObject(anyString(),eq(Integer.class))).thenReturn(1);
        assertDoesNotThrow(()->new AvatarReadiness(jdbc,true).run(null));
    }
    @Test void avatarRejectsDisguisedUploadBeforeStorage(){
        var files=new AvatarFiles("./var/test-unused-storage");
        assertThrows(ApiException.class,()->files.validate(new MockMultipartFile("avatar","x.png","image/png","not-an-image".getBytes())));
    }
    @Test void brokerApprovalTransitionsRemainRestricted(){
        assertEquals(BrokerApplicationDtos.Status.APPROVED,BrokerApplicationService.next(BrokerApplicationDtos.Status.PENDING,BrokerApplicationDtos.Action.APPROVE));
        assertEquals(BrokerApplicationDtos.Status.SUSPENDED,BrokerApplicationService.next(BrokerApplicationDtos.Status.APPROVED,BrokerApplicationDtos.Action.SUSPEND));
        assertThrows(ApiException.class,()->BrokerApplicationService.next(BrokerApplicationDtos.Status.REJECTED,BrokerApplicationDtos.Action.APPROVE));
        assertThrows(ApiException.class,()->BrokerApplicationService.next(BrokerApplicationDtos.Status.PENDING,BrokerApplicationDtos.Action.SUSPEND));
    }
}
