package vn.smartprop.amenity;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.web.server.ResponseStatusException;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
class AmenityMapServiceTest {
    private AmenityMapService.MapPoi point(String id, String status, String category, String basis, String url, double latitude) {
        return new AmenityMapService.MapPoi(id,"Unit fixture",category,"Hải Châu",latitude,108.22,basis,status,
            "openstreetmap_overpass",url,"© OpenStreetMap contributors","ODbL",null);
    }
    @Test void onlyValidatedSourceCoordinatesWithMatchingObjectBasisAreAccepted() {
        assertTrue(AmenityMapService.eligible(point("a","VALID","HOSPITAL","OSM_NODE","https://www.openstreetmap.org/node/12",16.05)));
        assertTrue(AmenityMapService.eligible(point("a","VALID","SCHOOL","OSM_WAY_CENTER","https://www.openstreetmap.org/way/12",16.05)));
        for(String status:List.of("LEGACY_UNVERIFIED","LEGACY_RECLASSIFIED","NEEDS_REVIEW","REJECTED"))
            assertFalse(AmenityMapService.eligible(point("a",status,"HOSPITAL","OSM_NODE","https://www.openstreetmap.org/node/12",16.05)));
        assertFalse(AmenityMapService.eligible(point("a","VALID","UNKNOWN","OSM_NODE","https://www.openstreetmap.org/node/12",16.05)));
        assertFalse(AmenityMapService.eligible(point("a","VALID","BEACH","AREA_CENTROID","https://www.openstreetmap.org/node/12",16.05)));
        assertFalse(AmenityMapService.eligible(point("a","VALID","BEACH","OSM_NODE","https://www.openstreetmap.org/way/12",16.05)));
        assertFalse(AmenityMapService.eligible(point("a","VALID","BEACH","OSM_NODE","https://evil.invalid/node/12",16.05)));
        assertFalse(AmenityMapService.eligible(point("a","VALID","BEACH","OSM_NODE","https://www.openstreetmap.org/node/12",Double.NaN)));
    }
    @Test void rejectAmbiguousDistrictCategoryBeforeQueryingDatabase() {
        var jdbc=mock(JdbcTemplate.class);
        var service=new AmenityMapService(jdbc,new AmenityCatalogService(new ObjectMapper()),new AmenityMapBoundaryCatalog(new ObjectMapper()));
        assertThrows(ResponseStatusException.class,()->service.find("anywhere","HOSPITAL"));
        assertThrows(ResponseStatusException.class,()->service.find("Hải Châu","RESEARCH"));
        verifyNoInteractions(jdbc);
    }
    @Test @SuppressWarnings("unchecked") void boundedBalancedCategoriesKeepTransitFromDrowningOtherAmenities() {
        var jdbc=mock(JdbcTemplate.class);
        List<AmenityMapService.MapPoi> rows=new ArrayList<>();
        for(int i=0;i<20;i++) rows.add(point("transit"+i,"VALID","PUBLIC_TRANSPORT","OSM_NODE","https://www.openstreetmap.org/node/"+(i+1),16.05));
        rows.add(point("hospital","VALID","HOSPITAL","OSM_WAY_CENTER","https://www.openstreetmap.org/way/22",16.05));
        when(jdbc.query(anyString(),any(RowMapper.class),eq("Hải Châu"),eq("ALL"),eq("ALL"))).thenReturn(rows);
        var result=new AmenityMapService(jdbc,new AmenityCatalogService(new ObjectMapper()),new AmenityMapBoundaryCatalog(new ObjectMapper())).find("Hai Chau","ALL");
        assertEquals(9,result.items().size());assertTrue(result.truncated());assertEquals(21,result.eligibleCount());
        assertEquals("PUBLIC",result.visibility());assertTrue(result.items().stream().anyMatch(p->p.id().equals("hospital")));
    }
    @Test @SuppressWarnings("unchecked") void areaOnlyUsesExistingBoundaryWithoutAnyInventedPoint() {
        var jdbc=mock(JdbcTemplate.class);
        when(jdbc.query(anyString(),any(RowMapper.class),eq("Hải Châu"),eq("BEACH"),eq("BEACH"))).thenReturn(List.of());
        var r=new AmenityMapService(jdbc,new AmenityCatalogService(new ObjectMapper()),new AmenityMapBoundaryCatalog(new ObjectMapper())).find("Hải Châu","BEACH");
        assertTrue(r.items().isEmpty());assertNotNull(r.boundary());
        assertEquals("Hải Châu",r.boundary().name());assertEquals("Polygon",r.boundary().geometry().path("type").asText());
    }
    @Test void publicControllerReturnsBoundedErrorsDirectlyWithoutAuthenticationErrorDispatch() {
        var service=mock(AmenityMapService.class);var controller=new AmenityMapController(service);
        when(service.find("bad","ALL")).thenThrow(new ResponseStatusException(org.springframework.http.HttpStatus.BAD_REQUEST));
        assertEquals(400,controller.get("bad","ALL").getStatusCode().value());
        when(service.find("Hải Châu","ALL")).thenThrow(new org.springframework.dao.DataAccessResourceFailureException("private SQL"));
        var r=controller.get("Hải Châu","ALL");assertEquals(503,r.getStatusCode().value());assertNull(r.getBody());
    }
}
