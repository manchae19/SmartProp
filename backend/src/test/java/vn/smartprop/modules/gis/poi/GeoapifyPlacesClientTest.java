package vn.smartprop.modules.gis.poi;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.*;
import java.net.http.*;
import java.util.*;
import java.util.concurrent.*;
import org.junit.jupiter.api.Test;
import vn.smartprop.common.*;
import vn.smartprop.config.*;
class GeoapifyPlacesClientTest {
 @Test void missingKeyFailsWithoutNetwork(){var client=new GeoapifyPlacesClient(new ObjectMapper(),new RequestLimits(),"",true);assertEquals(503,assertThrows(ApiException.class,()->client.search(16,108,1000,List.of("education"))).status);}
 @Test void disabledFailsWithoutNetwork(){var client=new GeoapifyPlacesClient(new ObjectMapper(),new RequestLimits(),"test-key",false);assertEquals("NEARBY_NOT_CONFIGURED",assertThrows(ApiException.class,()->client.search(16,108,1000,List.of("education"))).code);}
 @Test void providerQueryUsesFixedHostCircleLonLatAndNeverRedirects()throws Exception{
  var http=mock(HttpClient.class);var response=mock(HttpResponse.class);when(response.statusCode()).thenReturn(200);when(response.body()).thenReturn(new ByteArrayInputStream("{\"features\":[]}".getBytes()));
  when(http.sendAsync(any(HttpRequest.class),any(HttpResponse.BodyHandler.class))).thenAnswer(inv->{HttpRequest request=inv.getArgument(0);assertEquals("api.geoapify.com",request.uri().getHost());assertTrue(request.uri().getQuery().contains("circle:108.0,16.0,1000"));return CompletableFuture.completedFuture(response);});
  var client=new GeoapifyPlacesClient(new ObjectMapper(),new RequestLimits(),"test-only",true,http);assertTrue(client.search(16,108,1000,List.of("education")).path("features").isArray());
 }
 @Test void quotaAndAuthAndErrorsHaveDifferentCodes()throws Exception{for(int status:new int[]{429,401,500}){
  var http=mock(HttpClient.class);var response=mock(HttpResponse.class);when(response.statusCode()).thenReturn(status);when(response.body()).thenReturn(new ByteArrayInputStream(new byte[0]));when(http.sendAsync(any(HttpRequest.class),any(HttpResponse.BodyHandler.class))).thenReturn(CompletableFuture.completedFuture(response));
  var client=new GeoapifyPlacesClient(new ObjectMapper(),new RequestLimits(),"test",true,http);var error=assertThrows(ApiException.class,()->client.search(16,108,1000,List.of("park")));assertEquals(status==429?"NEARBY_QUOTA_EXCEEDED":status==401?"NEARBY_PROVIDER_AUTH":"NEARBY_PROVIDER_ERROR",error.code);
 }}
 @Test void wrappedHttpTimeoutIsReportedAsTimeout()throws Exception{var http=mock(HttpClient.class);when(http.sendAsync(any(HttpRequest.class),any(HttpResponse.BodyHandler.class))).thenReturn(CompletableFuture.failedFuture(new HttpTimeoutException("test timeout")));var client=new GeoapifyPlacesClient(new ObjectMapper(),new RequestLimits(),"test",true,http);assertEquals(504,assertThrows(ApiException.class,()->client.search(16,108,1000,List.of("park"))).status);}
}
