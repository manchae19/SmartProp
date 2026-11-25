package vn.smartprop.modules.gis.poi;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.*;
import org.junit.jupiter.api.*;
import org.locationtech.jts.geom.*;
import vn.smartprop.common.ApiException;
import vn.smartprop.modules.property.*;
class NearbyServiceTest {
 final PropertyService properties=mock(PropertyService.class);
 final PointOfInterestRepository repository=mock(PointOfInterestRepository.class);
 final GeoapifyPlacesClient provider=mock(GeoapifyPlacesClient.class);
 final PropertyCoordinateAuditService coordinateAudit=mock(PropertyCoordinateAuditService.class);
 final ObjectMapper json=new ObjectMapper();
 NearbyService service;Property property;
 @BeforeEach void setup(){service=new NearbyService(properties,repository,provider,new PropertyLocationEvidence(json,""),coordinateAudit);property=new Property();property.id="test-property";property.contentVersion=1;property.location=new GeometryFactory(new PrecisionModel(),4326).createPoint(new Coordinate(108.23,16.06));when(properties.publicProperty(property.id)).thenReturn(property);when(repository.nearby(anyString(),isNull(),anyDouble(),anyInt())).thenReturn(List.of());when(coordinateAudit.status(property.id)).thenReturn(new PropertyCoordinateAudit.Status("USER_PINNED","STREET",10.0,"UNVERIFIED",null,null,"VERIFIED_EXACT",null,true,true,false,1,java.time.Instant.now()));}
 String feature(String id,String name,double lat,double lon,String category){return "{\"type\":\"Feature\",\"geometry\":{\"type\":\"Point\",\"coordinates\":["+lon+","+lat+"]},\"properties\":{\"place_id\":\""+id+"\",\"name\":\""+name+"\",\"categories\":[\""+category+"\"]}}";}
 void upstream(String...features)throws Exception{when(provider.search(anyDouble(),anyDouble(),anyInt(),anyList())).thenReturn(json.readTree("{\"features\":["+String.join(",",features)+"]}"));}
 @Test void filtersOutOfRadiusUnknownCategoryAndDeduplicates()throws Exception{
  String good=feature("a","School",16.061,108.23,"education.school");upstream(good,good,feature("b","Far",16.16,108.23,"education.school"),feature("c","Not a school",16.061,108.23,"healthcare.hospital"));
  var result=service.nearby(property.id,500,"education");assertEquals(1,result.items().size());assertTrue(result.items().getFirst().distanceMeters()>100);assertEquals("UNKNOWN",result.location().accuracy());assertEquals("PARTIAL",result.coverage());assertFalse(result.cacheHit());
 }
 @Test void cacheRechecksPublicationAndDoesNotCallProviderTwice()throws Exception{
  upstream();service.nearby(property.id,1000,"health,education");assertTrue(service.nearby(property.id,1000,"education,health").cacheHit());verify(provider,times(1)).search(anyDouble(),anyDouble(),anyInt(),anyList());verify(properties,times(2)).publicProperty(property.id);
  when(properties.publicProperty(property.id)).thenThrow(new ApiException(404,"NOT_FOUND","Unavailable"));assertEquals(404,assertThrows(ApiException.class,()->service.nearby(property.id,1000,"education,health")).status);
 }
 @Test void versionChangeInvalidatesCache()throws Exception{upstream();service.nearby(property.id,1000,"park");property.contentVersion++;assertFalse(service.nearby(property.id,1000,"park").cacheHit());verify(provider,times(2)).search(anyDouble(),anyDouble(),anyInt(),anyList());}
 @Test void rejectsInvalidRadiusAndCategory(){for(int r:new int[]{0,999,50000})assertEquals(400,assertThrows(ApiException.class,()->service.nearby(property.id,r,"park")).status);assertThrows(ApiException.class,()->service.nearby(property.id,1000,"park,anything"));verifyNoInteractions(properties,provider,repository);}
 @Test void unknownLocationDoesNotInventMarkerOrContactProvider(){property.location=null;var result=service.nearby(property.id,1000,"education");assertNull(result.location());assertEquals("LOCATION_UNAVAILABLE",result.status());verifyNoInteractions(provider,repository);}
 @Test void ineligibleCoordinatesDoNotReachNearbyProviderOrPoiRepository(){when(coordinateAudit.status(property.id)).thenReturn(PropertyCoordinateAudit.Status.absent());var result=service.nearby(property.id,1000,"education");assertEquals("LOCATION_UNVERIFIED",result.status());assertNull(result.location());verifyNoInteractions(provider,repository);}
 @Test void advisorOriginAndNearbyFailClosedWhenDistanceEligibilityIsMissing(){when(coordinateAudit.status(property.id)).thenReturn(PropertyCoordinateAudit.Status.absent());assertNull(service.advisorOrigin(property.id));assertEquals("LOCATION_UNVERIFIED",service.forAdvisor(property.id,1000,"education",true).status());verifyNoInteractions(provider,repository);}
 @Test void providerFailureDoesNotBecomeCachedEmpty(){when(provider.search(anyDouble(),anyDouble(),anyInt(),anyList())).thenThrow(new ApiException(504,"NEARBY_TIMEOUT","timeout"));for(int i=0;i<2;i++)assertThrows(ApiException.class,()->service.nearby(property.id,1000,"education"));verify(provider,times(2)).search(anyDouble(),anyDouble(),anyInt(),anyList());}
 @Test void mergesLocalDataAndRecomputesDistance()throws Exception{upstream();var local=mock(PointOfInterestRepository.Nearby.class);when(local.getId()).thenReturn("local");when(local.getName()).thenReturn("Hospital");when(local.getCategory()).thenReturn("HOSPITAL");when(local.getLatitude()).thenReturn(16.061);when(local.getLongitude()).thenReturn(108.23);when(repository.nearby(anyString(),isNull(),anyDouble(),anyInt())).thenReturn(List.of(local));var r=service.nearby(property.id,1000,"health");assertEquals(1,r.items().size());assertEquals("LOCAL_DATABASE",r.items().getFirst().provider());assertTrue(r.items().getFirst().distanceMeters()<120);}
 @Test void capsResultsAndStatesPartialCoverage()throws Exception{var features=new ArrayList<String>();for(int i=0;i<200;i++)features.add(feature(""+i,"School "+i,16.061,108.23,"education.school"));upstream(features.toArray(String[]::new));var result=service.nearby(property.id,1000,"education");assertEquals(100,result.items().size());assertTrue(result.truncated());}
 @Test void allSupportedGroupsIncludingDiningAreAllowed(){assertEquals(NearbyService.GROUPS.size(),NearbyService.categories(String.join(",",NearbyService.GROUPS.keySet())).size());}
 @Test void haversineHandlesIdenticalAndOppositePoints(){assertEquals(0,NearbyService.distance(16,108,16,108));assertTrue(Double.isFinite(NearbyService.distance(0,0,0,180)));assertFalse(NearbyService.valid(Double.NaN,108));}
}
