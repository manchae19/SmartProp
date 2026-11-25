package vn.smartprop.modules.gis.poi;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.util.List;
import org.junit.jupiter.api.Test;
import vn.smartprop.common.ApiException;
import vn.smartprop.modules.property.Property;
import vn.smartprop.modules.property.PropertyCoordinateAudit;
import vn.smartprop.modules.property.PropertyCoordinateAuditService;
import vn.smartprop.modules.property.PropertyService;

class PoiServiceTest {
    @Test void pointsOfInterestRejectsCoordinateWithoutDistanceEligibility() {
        var pois=mock(PointOfInterestRepository.class);
        var properties=mock(PropertyService.class);
        var audit=mock(PropertyCoordinateAuditService.class);
        when(audit.available()).thenReturn(true);
        when(properties.publicProperty("p1")).thenReturn(new Property());
        when(audit.status("p1")).thenReturn(PropertyCoordinateAudit.Status.absent());
        var service=new PoiService(pois,properties,audit);

        var error=assertThrows(ApiException.class,()->service.nearby("p1",1000,20,null));

        assertEquals(422,error.status);
        assertEquals("LOCATION_UNVERIFIED",error.code);
        assertEquals("Chưa đủ bằng chứng tọa độ để phân tích khoảng cách.",error.getMessage());
        verifyNoInteractions(pois);
    }

    @Test void pointsOfInterestWithoutCoordinatesReturnsLocalizedAvailabilityMessage() {
        var pois=mock(PointOfInterestRepository.class);
        var properties=mock(PropertyService.class);
        var audit=mock(PropertyCoordinateAuditService.class);
        when(audit.available()).thenReturn(true);
        var property=new Property();
        property.location=null;
        when(properties.publicProperty("p1")).thenReturn(property);
        when(audit.status("p1")).thenReturn(new PropertyCoordinateAudit.Status(
            "USER_PINNED","STREET",10d,"UNVERIFIED",null,null,
            "VERIFIED_EXACT",null,true,true,false,1,null));
        var service=new PoiService(pois,properties,audit);

        var error=assertThrows(ApiException.class,()->service.nearby("p1",1000,20,null));

        assertEquals(422,error.status);
        assertEquals("LOCATION_UNAVAILABLE",error.code);
        assertEquals("Tin chưa có tọa độ hợp lệ.",error.getMessage());
        verifyNoInteractions(pois);
    }

    @Test void pointsOfInterestFailsClosedWhenCoordinateAuditSchemaIsUnavailable() {
        var pois=mock(PointOfInterestRepository.class);
        var properties=mock(PropertyService.class);
        var audit=mock(PropertyCoordinateAuditService.class);
        when(audit.available()).thenReturn(false);
        var service=new PoiService(pois,properties,audit);

        var error=assertThrows(ApiException.class,()->service.nearby("p1",1000,20,null));

        assertEquals(422,error.status);
        assertEquals("LOCATION_UNVERIFIED",error.code);
        verifyNoInteractions(pois);
    }
}
