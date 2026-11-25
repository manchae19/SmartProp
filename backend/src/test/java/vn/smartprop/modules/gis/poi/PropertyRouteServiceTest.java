package vn.smartprop.modules.gis.poi;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.*;
import org.junit.jupiter.api.*;
import org.locationtech.jts.geom.*;
import vn.smartprop.common.ApiException;
import vn.smartprop.modules.property.*;

/** Commute routing guards and caching, with the vendor layer mocked. */
class PropertyRouteServiceTest {
    final PropertyService properties=mock(PropertyService.class);
    final PointOfInterestRepository repository=mock(PointOfInterestRepository.class);
    final GeoapifyPlacesClient provider=mock(GeoapifyPlacesClient.class);
    final CommuteRoutingService routing=mock(CommuteRoutingService.class);
    final PropertyCoordinateAuditService coordinateAudit=mock(PropertyCoordinateAuditService.class);
    final ObjectMapper json=new ObjectMapper();
    NearbyService nearby;PropertyRouteService service;Property property;
    @BeforeEach void setup(){
        when(coordinateAudit.available()).thenReturn(true);
        nearby=new NearbyService(properties,repository,provider,new PropertyLocationEvidence(new ObjectMapper(),""),coordinateAudit);
        service=new PropertyRouteService(nearby,provider,routing);
        property=new Property();property.id="test-property";property.contentVersion=1;
        property.location=new GeometryFactory(new PrecisionModel(),4326).createPoint(new Coordinate(108.23,16.06));
        when(properties.publicProperty(property.id)).thenReturn(property);
        when(coordinateAudit.status(property.id)).thenReturn(new PropertyCoordinateAudit.Status("USER_PINNED","STREET",10.0,"UNVERIFIED",null,null,"VERIFIED_EXACT",null,true,true,false,1,java.time.Instant.now()));
        when(repository.nearby(anyString(),isNull(),anyDouble(),anyInt())).thenReturn(List.of());
        try{when(provider.search(anyDouble(),anyDouble(),anyInt(),anyList())).thenReturn(json.readTree("{\"features\":[]}"));}catch(Exception e){throw new IllegalStateException(e);}
        when(routing.provider()).thenReturn(CommuteRoutingService.GEOAPIFY);
    }
    @Test void returnsMeasuredCommuteForAConfirmedPoint()throws Exception{
        when(routing.directions(anyDouble(),anyDouble(),anyDouble(),anyDouble(),eq("drive")))
            .thenReturn(new CommuteRoutingService.Measured(4200,900,json.readTree("{}"),"GEOAPIFY"));
        var result=service.commute(property.id,16.07,108.24,"Công ty","drive");
        assertEquals(4200.0,result.distanceMeters(),0.001);
        assertEquals(900.0,result.durationSeconds(),0.001);
        assertEquals("drive",result.mode());
        assertEquals("GEOAPIFY",result.provider());
        assertEquals("Công ty",result.destinationLabel());
    }
    @Test void anIncompleteBatchIsNotCachedSoTheGapCanBeRetried()throws Exception{
        var located=new Property();located.id="located";located.contentVersion=1;
        located.location=new GeometryFactory(new PrecisionModel(),4326).createPoint(new Coordinate(108.24,16.07));
        when(properties.publicProperty("located")).thenReturn(located);
        when(coordinateAudit.status("located")).thenReturn(new PropertyCoordinateAudit.Status("USER_PINNED","STREET",10.0,"UNVERIFIED",null,null,"VERIFIED_EXACT",null,true,true,false,1,java.time.Instant.now()));
        // First batch: one listing measured, one never reached.
        when(routing.matrix(anyList(),anyDouble(),anyDouble(),eq("drive"),anyLong()))
            .thenReturn(List.of(new CommuteRoutingService.Cell("test-property",4200.0,900.0),
                                new CommuteRoutingService.Cell("located",null,null,false)));
        var first=service.commuteMatrix(List.of("test-property","located"),16.07,108.24,"Cty","drive");
        assertEquals("OK",first.cells().get(0).status());
        assertEquals("NOT_MEASURED",first.cells().get(1).status());

        // Second batch, same ids and destination: it must run again, not replay the gap.
        when(routing.matrix(anyList(),anyDouble(),anyDouble(),eq("drive"),anyLong()))
            .thenReturn(List.of(new CommuteRoutingService.Cell("test-property",4200.0,900.0),
                                new CommuteRoutingService.Cell("located",2600.0,600.0)));
        var second=service.commuteMatrix(List.of("test-property","located"),16.07,108.24,"Cty","drive");
        assertEquals("OK",second.cells().get(1).status());
        assertEquals(600.0,second.cells().get(1).durationSeconds(),0.001);
        verify(routing,times(2)).matrix(anyList(),anyDouble(),anyDouble(),eq("drive"),anyLong());
    }

    @Test void aCompleteBatchIsCached()throws Exception{
        when(routing.matrix(anyList(),anyDouble(),anyDouble(),eq("drive"),anyLong()))
            .thenReturn(List.of(new CommuteRoutingService.Cell("test-property",4200.0,900.0)));
        service.commuteMatrix(List.of("test-property"),16.07,108.24,"Cty","drive");
        service.commuteMatrix(List.of("test-property"),16.07,108.24,"Cty","drive");
        verify(routing,times(1)).matrix(anyList(),anyDouble(),anyDouble(),eq("drive"),anyLong());
    }
    @Test void rejectsDestinationOutsideTheSupportedArea(){
        var error=assertThrows(ApiException.class,()->service.commute(property.id,51.5,-0.12,"London","drive"));
        assertEquals(422,error.status);
        assertEquals("COMMUTE_DESTINATION_OUT_OF_AREA",error.code);
        verifyNoInteractions(routing);
    }
    @Test void rejectsInvalidCoordinatesAndMode(){
        assertThrows(ApiException.class,()->service.commute(property.id,Double.NaN,108.24,"x","drive"));
        assertThrows(ApiException.class,()->service.commute(property.id,16.07,108.24,"x","fly"));
        verifyNoInteractions(routing);
    }
    @Test void rejectsAnOverlongLabel(){
        var error=assertThrows(ApiException.class,()->service.commute(property.id,16.07,108.24,"x".repeat(201),"drive"));
        assertEquals(400,error.status);
        verifyNoInteractions(routing);
    }
    @Test void refusesWhenTheListingHasNoUsableOrigin(){
        property.location=null;
        var error=assertThrows(ApiException.class,()->service.commute(property.id,16.07,108.24,"x","drive"));
        assertEquals(422,error.status);
        assertEquals("ROUTE_LOCATION_UNAVAILABLE",error.code);
        verifyNoInteractions(routing);
    }
    @Test void commuteRefusesAnOriginWithoutCoordinateEligibility(){
        when(coordinateAudit.status(property.id)).thenReturn(PropertyCoordinateAudit.Status.absent());
        var error=assertThrows(ApiException.class,()->service.commute(property.id,16.07,108.24,"x","drive"));
        assertEquals(422,error.status);
        assertEquals("ROUTE_LOCATION_UNAVAILABLE",error.code);
        verifyNoInteractions(routing,provider,repository);
    }
    @Test void cachesRepeatedCommuteLookups()throws Exception{
        when(routing.directions(anyDouble(),anyDouble(),anyDouble(),anyDouble(),eq("drive")))
            .thenReturn(new CommuteRoutingService.Measured(4200,900,json.readTree("{}"),"GEOAPIFY"));
        service.commute(property.id,16.07,108.24,"x","drive");
        service.commute(property.id,16.07,108.24,"x","drive");
        verify(routing,times(1)).directions(anyDouble(),anyDouble(),anyDouble(),anyDouble(),eq("drive"));
    }
    @Test void matrixKeepsTheCallerOrderAndMarksUnverifiedOrigins(){
        Property located=new Property();located.id="located";located.contentVersion=1;
        located.location=new GeometryFactory(new PrecisionModel(),4326).createPoint(new Coordinate(108.24,16.07));
        when(properties.publicProperty("located")).thenReturn(located);
        when(coordinateAudit.status("located")).thenReturn(new PropertyCoordinateAudit.Status("USER_PINNED","STREET",10.0,"UNVERIFIED",null,null,"VERIFIED_EXACT",null,true,true,false,1,java.time.Instant.now()));
        when(routing.matrix(anyList(),anyDouble(),anyDouble(),anyString(),anyLong()))
            .thenReturn(List.of(new CommuteRoutingService.Cell("located",1500.0,300.0)));
        var result=service.commuteMatrix(List.of("missing","located"),16.07,108.24,"Cty","drive");
        assertEquals(2,result.cells().size());
        assertEquals("missing",result.cells().get(0).propertyId());
        assertEquals("LOCATION_UNVERIFIED",result.cells().get(0).status());
        assertEquals("located",result.cells().get(1).propertyId());
        assertEquals("OK",result.cells().get(1).status());
        assertEquals(300.0,result.cells().get(1).durationSeconds(),0.001);
    }
    @Test void matrixRejectsMoreThanSixListings(){
        var ids=new ArrayList<String>();
        for(int i=0;i<7;i++) ids.add("p"+i);
        var error=assertThrows(ApiException.class,()->service.commuteMatrix(ids,16.07,108.24,"x","drive"));
        assertEquals(400,error.status);
        assertEquals("COMMUTE_MATRIX_TOO_LARGE",error.code);
    }
}
