package vn.smartprop.modules.gis.poi;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.http.*;
import java.util.*;
import org.junit.jupiter.api.*;
import vn.smartprop.common.ApiException;
import vn.smartprop.common.RequestLimits;

/** Vendor selection and response normalisation for the commute router. */
class CommuteRoutingServiceTest {
    final ObjectMapper json=new ObjectMapper();
    final HttpClient client=mock(HttpClient.class);
    final GeoapifyPlacesClient geoapify=mock(GeoapifyPlacesClient.class);

    CommuteRoutingService service(String configured,String orsKey){
        return new CommuteRoutingService(json,configured,orsKey,null,geoapify,client);
    }

    @SuppressWarnings("unchecked")
    void respond(int code,String body,Map<String,String> headers)throws Exception{
        HttpResponse<byte[]> response=mock(HttpResponse.class);
        when(response.statusCode()).thenReturn(code);
        when(response.body()).thenReturn(body.getBytes(java.nio.charset.StandardCharsets.UTF_8));
        HttpHeaders httpHeaders=HttpHeaders.of(headers.entrySet().stream()
            .collect(java.util.stream.Collectors.toMap(Map.Entry::getKey,e->List.of(e.getValue()))),
            (a,b)->true);
        when(response.headers()).thenReturn(httpHeaders);
        when(client.send(any(HttpRequest.class),any(HttpResponse.BodyHandler.class))).thenReturn(response);
    }

    @Test void explicitOrsWithoutAKeyDoesNotSilentlyFallBackToGeoapify(){
        assertEquals(CommuteRoutingService.OPENROUTESERVICE,service("OPENROUTESERVICE","k").provider());
        assertNull(service("OPENROUTESERVICE","").provider());
    }

    @Test void geoapifyIsUsedWhenConfiguredAndAvailable(){
        when(geoapify.configured()).thenReturn(true);
        assertEquals(CommuteRoutingService.GEOAPIFY,service("GEOAPIFY","k").provider());
        when(geoapify.configured()).thenReturn(false);
        assertNull(service("GEOAPIFY","").provider());
    }

    @Test void mapsWalkAndDriveToProviderProfiles(){
        assertEquals("foot-walking",CommuteRoutingService.orsProfile("walk"));
        assertEquals("driving-car",CommuteRoutingService.orsProfile("drive"));
        assertEquals("driving-car",CommuteRoutingService.orsProfile("anything-else"));
    }

    @Test void matrixReturnsOneCellPerOriginInOrder()throws Exception{
        respond(200,"{\"durations\":[[300.0],[600.0]],\"distances\":[[1500.0],[2600.0]]}",Map.of());
        var origins=List.of(new CommuteRoutingService.Origin("a",16.06,108.22),
                            new CommuteRoutingService.Origin("b",16.07,108.23));
        var cells=service("OPENROUTESERVICE","k").matrix(origins,16.08,108.24,"drive");
        assertEquals(2,cells.size());
        assertEquals("a",cells.get(0).propertyId());
        assertEquals(300.0,cells.get(0).durationSeconds(),0.001);
        assertEquals(1500.0,cells.get(0).distanceMeters(),0.001);
        assertEquals("b",cells.get(1).propertyId());
        assertEquals(600.0,cells.get(1).durationSeconds(),0.001);
    }

    @Test void onlyTheEgressBucketIsRetried(){
        // The decision uses the counter that refused, never Retry-After: that header is the
        // time left in the window, so the daily quota also reports 1 second near rollover.
        assertTrue(CommuteRoutingService.isEgressThrottle(new RequestLimits.Exceeded(1,"geo:egress")));
        assertTrue(CommuteRoutingService.isEgressThrottle(new RequestLimits.Exceeded(60,"geo:egress")));
        // Same Retry-After, different counter: not retried.
        assertFalse(CommuteRoutingService.isEgressThrottle(new RequestLimits.Exceeded(1,"geo:daily")));
        assertFalse(CommuteRoutingService.isEgressThrottle(new RequestLimits.Exceeded(1,"commute-matrix:ip:127.0.0.1")));
        // An unattributed 429 is never retried.
        assertFalse(CommuteRoutingService.isEgressThrottle(new RequestLimits.Exceeded(1)));
        assertFalse(CommuteRoutingService.isEgressThrottle(new ApiException(429,"RATE_LIMITED","x")));
        // A provider-side failure is not a throttle at all.
        assertFalse(CommuteRoutingService.isEgressThrottle(new ApiException(502,"ROUTE_UNAVAILABLE","x")));
    }

    @Test void aDailyQuotaStopsTheBatchInsteadOfSleeping()throws Exception{
        when(geoapify.configured()).thenReturn(true);
        when(geoapify.route(anyDouble(),anyDouble(),anyDouble(),anyDouble(),anyString()))
            .thenThrow(new RequestLimits.Exceeded(1,"geo:daily"));
        var origins=List.of(new CommuteRoutingService.Origin("a",16.06,108.22),
                            new CommuteRoutingService.Origin("b",16.07,108.23));
        long start=System.nanoTime();
        var error=assertThrows(ApiException.class,
            ()->service("GEOAPIFY","k").matrix(origins,16.08,108.24,"drive"));
        long millis=(System.nanoTime()-start)/1_000_000;
        assertEquals(429,error.status);
        // No 1.1s sleep per listing: the batch stops on the first refusal.
        assertTrue(millis<1000,"phải dừng ngay, không chờ: "+millis+"ms");
        verify(geoapify,times(1)).route(anyDouble(),anyDouble(),anyDouble(),anyDouble(),anyString());
    }

    @Test void aShortEgressThrottleIsRetriedAndThenSucceeds()throws Exception{
        when(geoapify.configured()).thenReturn(true);
        when(geoapify.route(anyDouble(),anyDouble(),anyDouble(),anyDouble(),anyString()))
            .thenThrow(new RequestLimits.Exceeded(1,"geo:egress"))
            .thenReturn(json.readTree("{\"features\":[{\"properties\":{\"distance\":1500.0,\"time\":300.0},"
                + "\"geometry\":{\"coordinates\":[[108.22,16.06],[108.24,16.08]]}}]}"));
        var origins=List.of(new CommuteRoutingService.Origin("a",16.06,108.22));
        var cells=service("GEOAPIFY","k").matrix(origins,16.08,108.24,"drive");
        assertEquals(1,cells.size());
        assertEquals(300.0,cells.get(0).durationSeconds(),0.001);
        verify(geoapify,times(2)).route(anyDouble(),anyDouble(),anyDouble(),anyDouble(),anyString());
    }
    @Test void matrixKeepsNullForAnUnroutableCell()throws Exception{
        respond(200,"{\"durations\":[[null],[600.0]],\"distances\":[[null],[2600.0]]}",Map.of());
        var origins=List.of(new CommuteRoutingService.Origin("a",16.06,108.22),
                            new CommuteRoutingService.Origin("b",16.07,108.23));
        var cells=service("OPENROUTESERVICE","k").matrix(origins,16.08,108.24,"drive");
        assertNull(cells.get(0).durationSeconds());
        assertNull(cells.get(0).distanceMeters());
        assertEquals(600.0,cells.get(1).durationSeconds(),0.001);
    }

    @Test void directionsNormalisesMetresAndSeconds()throws Exception{
        respond(200,"{\"features\":[{\"properties\":{\"summary\":{\"distance\":4200.5,\"duration\":900.2}},"
            + "\"geometry\":{\"type\":\"LineString\",\"coordinates\":[[108.22,16.06],[108.24,16.08]]}}]}",Map.of());
        var measured=service("OPENROUTESERVICE","k").directions(16.06,108.22,16.08,108.24,"drive");
        assertEquals(4200.5,measured.distanceMeters(),0.001);
        assertEquals(900.2,measured.durationSeconds(),0.001);
        assertEquals(CommuteRoutingService.OPENROUTESERVICE,measured.provider());
        assertEquals("LineString",measured.geometry().path("type").asText());
    }

    @Test void vendorRateLimitIsADistinctError()throws Exception{
        respond(429,"{\"error\":\"rate limit\"}",Map.of("Retry-After","120"));
        var origins=List.of(new CommuteRoutingService.Origin("a",16.06,108.22));
        var error=assertThrows(ApiException.class,
            ()->service("OPENROUTESERVICE","k").matrix(origins,16.08,108.24,"drive"));
        assertEquals(429,error.status);
        assertEquals("ROUTE_PROVIDER_RATE_LIMITED",error.code);
    }

    @Test void vendorAuthFailureNeverEchoesTheKey()throws Exception{
        respond(403,"forbidden",Map.of());
        var origins=List.of(new CommuteRoutingService.Origin("a",16.06,108.22));
        var error=assertThrows(ApiException.class,
            ()->service("OPENROUTESERVICE","secret-key-value").matrix(origins,16.08,108.24,"drive"));
        assertEquals(503,error.status);
        assertEquals("ROUTE_PROVIDER_AUTH",error.code);
        assertFalse(String.valueOf(error.getMessage()).contains("secret-key-value"));
    }

    @Test void unconfiguredVendorRefusesInsteadOfGuessing(){
        var origins=List.of(new CommuteRoutingService.Origin("a",16.06,108.22));
        var error=assertThrows(ApiException.class,
            ()->service("OPENROUTESERVICE","").matrix(origins,16.08,108.24,"drive"));
        assertEquals(503,error.status);
        assertEquals("ROUTE_NOT_CONFIGURED",error.code);
    }

    @Test void matrixRejectsAnInvalidOriginCoordinate()throws Exception{
        var origins=List.of(new CommuteRoutingService.Origin("a",Double.NaN,108.22));
        assertThrows(ApiException.class,()->service("OPENROUTESERVICE","k").matrix(origins,16.08,108.24,"drive"));
        verifyNoInteractions(client);
    }

    @Test void geoapifyBatchKeepsGoingWhenOnePairHasNoRoute()throws Exception{
        when(geoapify.configured()).thenReturn(true);
        when(geoapify.route(anyDouble(),anyDouble(),anyDouble(),anyDouble(),anyString()))
            .thenThrow(new ApiException(502,"ROUTE_UNAVAILABLE","x"))
            .thenReturn(json.readTree("{\"features\":[{\"properties\":{\"distance\":1000,\"time\":200},"
                + "\"geometry\":{\"type\":\"LineString\",\"coordinates\":[[108.2,16.0],[108.3,16.1]]}}]}"));
        var origins=List.of(new CommuteRoutingService.Origin("a",16.06,108.22),
                            new CommuteRoutingService.Origin("b",16.07,108.23));
        var cells=service("GEOAPIFY","").matrix(origins,16.08,108.24,"drive");
        assertNull(cells.get(0).durationSeconds());
        assertEquals(200.0,cells.get(1).durationSeconds(),0.001);
    }

    @Test void geoapifyBatchStopsOnOurOwnBudgetError()throws Exception{
        when(geoapify.configured()).thenReturn(true);
        when(geoapify.route(anyDouble(),anyDouble(),anyDouble(),anyDouble(),anyString()))
            .thenThrow(new ApiException(429,"RATE_LIMITED","Please retry later"));
        var origins=List.of(new CommuteRoutingService.Origin("a",16.06,108.22));
        var error=assertThrows(ApiException.class,
            ()->service("GEOAPIFY","").matrix(origins,16.08,108.24,"drive"));
        assertEquals("RATE_LIMITED",error.code);
    }

    @Test void anUnattributed429IsNotRetried()throws Exception{
        when(geoapify.configured()).thenReturn(true);
        when(geoapify.route(anyDouble(),anyDouble(),anyDouble(),anyDouble(),anyString()))
            .thenThrow(new ApiException(429,"RATE_LIMITED","Please retry later"));
        var origins=List.of(new CommuteRoutingService.Origin("a",16.06,108.22));
        long start=System.nanoTime();
        var error=assertThrows(ApiException.class,
            ()->service("GEOAPIFY","").matrix(origins,16.08,108.24,"drive"));
        long millis=(System.nanoTime()-start)/1_000_000;
        assertEquals(429,error.status);
        assertTrue(millis<1000,"không được chờ: "+millis+"ms");
        verify(geoapify,times(1)).route(anyDouble(),anyDouble(),anyDouble(),anyDouble(),anyString());
    }

    @Test void anUnroutableListingStaysNoRouteWhileTheRestKeepTheirResult()throws Exception{
        when(geoapify.configured()).thenReturn(true);
        when(geoapify.route(anyDouble(),anyDouble(),anyDouble(),anyDouble(),anyString()))
            .thenReturn(json.readTree("{\"features\":[{\"properties\":{\"distance\":1500.0,\"time\":300.0},"
                + "\"geometry\":{\"type\":\"LineString\",\"coordinates\":[[108.22,16.06],[108.24,16.08]]}}]}"))
            .thenThrow(new ApiException(502,"ROUTE_UNAVAILABLE","x"))
            .thenReturn(json.readTree("{\"features\":[{\"properties\":{\"distance\":2600.0,\"time\":600.0},"
                + "\"geometry\":{\"type\":\"LineString\",\"coordinates\":[[108.23,16.07],[108.24,16.08]]}}]}"));
        var origins=List.of(new CommuteRoutingService.Origin("a",16.06,108.22),
                            new CommuteRoutingService.Origin("b",16.07,108.23),
                            new CommuteRoutingService.Origin("c",16.05,108.21));
        var cells=service("GEOAPIFY","").matrix(origins,16.08,108.24,"drive");
        assertEquals(3,cells.size());
        assertEquals(300.0,cells.get(0).durationSeconds(),0.001);
        assertNull(cells.get(1).durationSeconds(),"căn không tuyến phải để trống");
        assertNull(cells.get(1).distanceMeters());
        assertEquals(600.0,cells.get(2).durationSeconds(),0.001);
    }
    // ---- hosted endpoint shape -------------------------------------------------

    @Test void defaultBaseIsTheHostedGatewayWithASinglePrefix(){
        assertEquals("https://api.heigit.org/openrouteservice",
            CommuteRoutingService.normaliseBase(null));
        assertEquals("https://api.heigit.org/openrouteservice",
            CommuteRoutingService.normaliseBase(""));
        assertEquals("https://api.heigit.org/openrouteservice",
            CommuteRoutingService.normaliseBase("https://api.heigit.org/openrouteservice/"));
        assertEquals("https://api.heigit.org/openrouteservice",
            CommuteRoutingService.normaliseBase("  https://api.heigit.org/openrouteservice//  "));
    }

    @Test void matrixCallsTheDocumentedHeigitPath()throws Exception{
        respond(200,"{\"durations\":[[300.0]],\"distances\":[[1500.0]]}",Map.of());
        var origins=List.of(new CommuteRoutingService.Origin("a",16.06,108.22));
        service("OPENROUTESERVICE","k").matrix(origins,16.08,108.24,"drive");
        var request=capturedRequest();
        assertEquals("https://api.heigit.org/openrouteservice/v2/matrix/driving-car",
            request.uri().toString());
        assertEquals("k",request.headers().firstValue("Authorization").orElse(""));
    }

    @Test void carDirectionsCallsTheGeojsonPathNotTheMatrixPath()throws Exception{
        respond(200,"{\"features\":[{\"properties\":{\"summary\":{\"distance\":4200.0,\"duration\":900.0}},"
            + "\"geometry\":{\"type\":\"LineString\",\"coordinates\":[[108.22,16.06],[108.24,16.08]]}}]}",Map.of());
        service("OPENROUTESERVICE","k").directions(16.06,108.22,16.08,108.24,"drive");
        assertEquals("https://api.heigit.org/openrouteservice/v2/directions/driving-car/geojson",
            capturedRequest().uri().toString());
    }

    @Test void walkingDirectionsUsesTheFootProfile()throws Exception{
        respond(200,"{\"features\":[{\"properties\":{\"summary\":{\"distance\":1200.0,\"duration\":800.0}},"
            + "\"geometry\":{\"type\":\"LineString\",\"coordinates\":[[108.22,16.06],[108.23,16.07]]}}]}",Map.of());
        service("OPENROUTESERVICE","k").directions(16.06,108.22,16.07,108.23,"walk");
        assertEquals("https://api.heigit.org/openrouteservice/v2/directions/foot-walking/geojson",
            capturedRequest().uri().toString());
    }

    @Test void walkingMatrixUsesTheFootProfile()throws Exception{
        respond(200,"{\"durations\":[[600.0]],\"distances\":[[800.0]]}",Map.of());
        var origins=List.of(new CommuteRoutingService.Origin("a",16.06,108.22));
        service("OPENROUTESERVICE","k").matrix(origins,16.07,108.23,"walk");
        assertEquals("https://api.heigit.org/openrouteservice/v2/matrix/foot-walking",
            capturedRequest().uri().toString());
    }

    @Test void aSelfHostedBaseIsUsedVerbatimWithoutTheHostedPrefix()throws Exception{
        respond(200,"{\"durations\":[[300.0]],\"distances\":[[1500.0]]}",Map.of());
        var local=new CommuteRoutingService(json,"OPENROUTESERVICE","k","http://127.0.0.1:18999",
            geoapify,client);
        local.matrix(List.of(new CommuteRoutingService.Origin("a",16.06,108.22)),16.08,108.24,"drive");
        assertEquals("http://127.0.0.1:18999/v2/matrix/driving-car",
            capturedRequest().uri().toString());
    }

    private HttpRequest capturedRequest(){
        var captor=org.mockito.ArgumentCaptor.forClass(HttpRequest.class);
        try{
            verify(client,atLeastOnce()).send(captor.capture(),any(HttpResponse.BodyHandler.class));
        }catch(Exception e){
            throw new IllegalStateException(e);
        }
        return captor.getValue();
    }
}
