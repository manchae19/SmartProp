package vn.smartprop.modules.user;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.validation.Validation;
import java.util.*;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import vn.smartprop.common.ApiException;

class AdvisorPreferencesTest {
    JdbcTemplate jdbc=mock(JdbcTemplate.class);
    UserRepository users=mock(UserRepository.class);
    ObjectMapper mapper=new ObjectMapper();
    AdvisorPreferencesService service=new AdvisorPreferencesService(jdbc,mapper,users);
    AdvisorPreferencesService.Preferences prefs(Boolean children,Integer count,List<AdvisorPreferencesService.Need> needs,AdvisorPreferencesService.Need primary,boolean enabled) {
        return new AdvisorPreferencesService.Preferences(null,children,count,"Engineer","Cẩm Lệ",needs,primary,"",enabled);
    }
    void schema() {when(jdbc.queryForObject(anyString(),eq(Integer.class))).thenReturn(1);}
    @Test void optionalDefaultsAndMissingSchema() {
        when(jdbc.queryForObject(anyString(),eq(Integer.class))).thenReturn(0);
        assertFalse(service.get(1L).enabled());
        assertTrue(service.get(1L).selectedNeeds().isEmpty());
        assertThrows(ApiException.class,()->service.save(1L,AdvisorPreferencesService.Preferences.empty()));
    }
    @Test void saveClearsChildrenAndStoresManyNeedsWithoutLoggingBiography() {
        schema();
        var p=prefs(false,3,List.of(AdvisorPreferencesService.Need.PRIMARY_SCHOOL,AdvisorPreferencesService.Need.SUPERMARKET,AdvisorPreferencesService.Need.GYM),AdvisorPreferencesService.Need.PRIMARY_SCHOOL,true);
        service.save(7L,p);
        var json=org.mockito.ArgumentCaptor.forClass(String.class);
        verify(jdbc).update(contains("INSERT INTO user_advisor_preferences"),eq(7L),json.capture());
        assertTrue(json.getValue().contains("\"childrenCount\":null"));
        assertTrue(json.getValue().contains("GYM"));
        assertFalse(p.toString().contains("Engineer"));
    }
    @Test void rejectsUnselectedPrimaryAndDuplicates() {
        schema();
        assertThrows(ApiException.class,()->service.save(1L,prefs(true,1,List.of(AdvisorPreferencesService.Need.PARK),AdvisorPreferencesService.Need.PRIMARY_SCHOOL,true)));
        assertThrows(ApiException.class,()->service.save(1L,prefs(true,1,List.of(AdvisorPreferencesService.Need.PARK,AdvisorPreferencesService.Need.PARK),null,true)));
    }
    @Test void beanValidationRejectsInvalidCountAndLongText() {
        try(var factory=Validation.buildDefaultValidatorFactory()) {
            assertFalse(factory.getValidator().validate(prefs(true,6,List.of(),null,false)).isEmpty());
            assertTrue(factory.getValidator().validate(AdvisorPreferencesService.Preferences.empty()).isEmpty());
        }
    }
    @Test void contextIsConsentGatedAndDoesNotExposeOccupation() throws Exception {
        schema();var u=new User();u.id=1L;u.status=User.Status.ACTIVE;u.district="Cẩm Lệ";
        when(users.findById(1L)).thenReturn(Optional.of(u));
        var p=prefs(true,2,List.of(AdvisorPreferencesService.Need.SUPERMARKET),AdvisorPreferencesService.Need.SUPERMARKET,false);
        when(jdbc.queryForList(anyString(),eq(String.class),eq(1L))).thenReturn(List.of(mapper.writeValueAsString(p)));
        var c=service.context(1L);
        assertFalse(c.enabled());assertNull(c.district());assertTrue(c.selectedNeeds().isEmpty());
        assertNull(c.familyStatus());assertNull(c.hasChildren());assertNull(c.childrenCount());assertNull(c.ageGroup());
        String wire=mapper.writeValueAsString(c);
        assertFalse(wire.contains("occupation"));assertFalse(wire.contains("Engineer"));
        var enabled=new AdvisorPreferencesService.Preferences(AdvisorPreferencesService.Family.MARRIED,true,2,"Engineer","Cẩm Lệ",
            List.of(AdvisorPreferencesService.Need.SUPERMARKET),AdvisorPreferencesService.Need.SUPERMARKET,"",true,
            AdvisorPreferencesService.AgeGroup.AGE_35_44);
        when(jdbc.queryForList(anyString(),eq(String.class),eq(1L))).thenReturn(List.of(mapper.writeValueAsString(enabled)));
        var c2=service.context(1L);
        assertTrue(c2.enabled());assertEquals(AdvisorPreferencesService.Family.MARRIED,c2.familyStatus());
        assertTrue(c2.hasChildren());assertEquals(2,c2.childrenCount());assertEquals(AdvisorPreferencesService.AgeGroup.AGE_35_44,c2.ageGroup());
        assertFalse(mapper.writeValueAsString(c2).contains("occupation"));
        u.status=User.Status.LOCKED;
        assertThrows(ApiException.class,()->service.context(1L));
    }
}
