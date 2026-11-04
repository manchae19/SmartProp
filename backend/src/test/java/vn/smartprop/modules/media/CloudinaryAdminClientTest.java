package vn.smartprop.modules.media;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.*;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;
import org.junit.jupiter.api.Test;
import vn.smartprop.common.*;
import vn.smartprop.config.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class CloudinaryAdminClientTest {
    final ObjectMapper json=new ObjectMapper();
    final HttpClient http=mock(HttpClient.class);
    final RequestLimits limits=mock(RequestLimits.class);
    CloudinaryAdminClient client(){return new CloudinaryAdminClient(json,limits,"demo-cloud","test-key","test-secret",http);}
    String asset(String id,String folder,String url){
        return "{\"asset_id\":\""+id+"\",\"public_id\":\"unrelated-public-id/"+id+"\",\"secure_url\":\""+url+"\",\"asset_folder\":\""+folder+"\",\"resource_type\":\"image\",\"type\":\"upload\",\"format\":\"jpg\",\"bytes\":1024,\"width\":800,\"height\":600,\"created_at\":\"2026-11-03T00:00:00Z\"}";
    }
    String good(String id){return asset(id,"SmartProp/dev/properties/SP003","https://res.cloudinary.com/demo-cloud/image/upload/v1/"+id+".jpg");}
    HttpResponse<InputStream> response(int status,String body){
        var response=mock(HttpResponse.class);when(response.statusCode()).thenReturn(status);
        when(response.body()).thenReturn(new ByteArrayInputStream(body.getBytes(StandardCharsets.UTF_8)));return response;
    }
    @Test void missingCredentialsDoesNotCallProvider(){
        var c=new CloudinaryAdminClient(json,limits,"","","",http);assertFalse(c.configured());
        assertEquals("CLOUDINARY_NOT_CONFIGURED",assertThrows(ApiException.class,()->c.listForListing("SP003")).code);
        verifyNoInteractions(http);
    }
    @Test void listingCodeCannotInjectAnArbitraryFolderOrUrl(){
        for(String value:new String[]{"../SP003","SP000","https://evil.invalid","SP003?folder=x"})assertEquals(400,assertThrows(ApiException.class,()->client().listForListing(value)).status);
        verifyNoInteractions(http);
    }
    @Test void paginatesByAssetFolderAndDeduplicatesImmutableAssetId()throws Exception{
        var requests=new ArrayList<HttpRequest>();
        when(http.sendAsync(any(HttpRequest.class),any(HttpResponse.BodyHandler.class))).thenAnswer(inv->{
            HttpRequest request=inv.getArgument(0);requests.add(request);boolean next=request.uri().getQuery().contains("next_cursor=next-2");
            return CompletableFuture.completedFuture(response(200,next?"{\"resources\":["+good("a")+","+good("b")+"]}":"{\"resources\":["+good("a")+"],\"next_cursor\":\"next-2\"}"));
        });
        var result=client().listForListing("SP003");
        assertEquals(2,result.pages());assertEquals(3,result.resourceCount());assertEquals(2,result.assets().size());
        assertEquals("api.cloudinary.com",requests.getFirst().uri().getHost());
        assertEquals("/v1_1/demo-cloud/resources/by_asset_folder",requests.getFirst().uri().getPath());
        assertTrue(requests.getFirst().uri().getQuery().contains("asset_folder=SmartProp/dev/properties/SP003"));
        assertFalse(requests.getFirst().uri().toString().contains("test-secret"));
        assertTrue(requests.getFirst().headers().firstValue("Authorization").orElseThrow().startsWith("Basic "));
        assertEquals("unrelated-public-id/a",result.assets().getFirst().publicId());
    }
    @Test void repeatedCursorStopsInsteadOfLoopingForever()throws Exception{
        when(http.sendAsync(any(HttpRequest.class),any(HttpResponse.BodyHandler.class))).thenAnswer(inv->CompletableFuture.completedFuture(response(200,"{\"resources\":[],\"next_cursor\":\"same\"}")));
        assertEquals("CLOUDINARY_CURSOR_LOOP",assertThrows(ApiException.class,()->client().listForListing("SP003")).code);
        verify(http,times(2)).sendAsync(any(HttpRequest.class),any(HttpResponse.BodyHandler.class));
    }
    @Test void rejectsForeignFolderAndForeignCloudWithoutFollowingDeliveryUrls()throws Exception{
        String body="{\"resources\":["+asset("a","SmartProp/dev/properties/SP004","https://res.cloudinary.com/demo-cloud/image/upload/v1/a.jpg")+","+asset("b","SmartProp/dev/properties/SP003","https://evil.invalid/a.jpg")+","+asset("c","SmartProp/dev/properties/SP003","https://res.cloudinary.com/another-cloud/image/upload/v1/c.jpg")+"]}";
        when(http.sendAsync(any(HttpRequest.class),any(HttpResponse.BodyHandler.class))).thenAnswer(inv->CompletableFuture.completedFuture(response(200,body)));
        var result=client().listForListing("SP003");assertTrue(result.assets().isEmpty());assertEquals(3,result.rejected().size());assertEquals("WRONG_ASSET_FOLDER",result.rejected().getFirst().reason());
        verify(http,times(1)).sendAsync(any(HttpRequest.class),any(HttpResponse.BodyHandler.class));
    }
    @Test void changedAssetIdentityDuringScanIsNotSilentlyImported()throws Exception{
        String a=good("a"),changed=a.replace("v1/a.jpg","v2/a.jpg");
        when(http.sendAsync(any(HttpRequest.class),any(HttpResponse.BodyHandler.class))).thenAnswer(inv->CompletableFuture.completedFuture(response(200,"{\"resources\":["+a+","+changed+"]}")));
        assertEquals("CLOUDINARY_CHANGED_DURING_SCAN",assertThrows(ApiException.class,()->client().listForListing("SP003")).code);
    }
    @Test void authQuotaAndServerErrorsRemainDistinctAndDoNotExposeCredentials()throws Exception{
        for(int status:new int[]{401,403,420,429,500}){
            var transport=mock(HttpClient.class);
            when(transport.sendAsync(any(HttpRequest.class),any(HttpResponse.BodyHandler.class))).thenAnswer(inv->CompletableFuture.completedFuture(response(status,"sensitive provider response")));
            var c=new CloudinaryAdminClient(json,limits,"demo-cloud","test-key","test-secret",transport);
            var e=assertThrows(ApiException.class,()->c.listForListing("SP003"));
            assertEquals(status==401||status==403?"CLOUDINARY_AUTH_FAILED":status==420||status==429?"CLOUDINARY_RATE_LIMITED":"CLOUDINARY_PROVIDER_ERROR",e.code);
            assertFalse(e.getMessage().contains("test-secret"));assertFalse(e.getMessage().contains("sensitive"));
        }
    }
    @Test void timeoutIsBoundedAndNotReportedAsEmptyAlbum()throws Exception{
        when(http.sendAsync(any(HttpRequest.class),any(HttpResponse.BodyHandler.class))).thenReturn(CompletableFuture.failedFuture(new HttpTimeoutException("mock")));
        assertEquals(504,assertThrows(ApiException.class,()->client().listForListing("SP003")).status);
    }
    @Test void malformedAndNullResponsesAreNotTreatedAsEmptyAlbum()throws Exception{
        for(String body:new String[]{"null","{}","{\"resources\":{},\"next_cursor\":\"x\"}"}){
            var transport=mock(HttpClient.class);when(transport.sendAsync(any(HttpRequest.class),any(HttpResponse.BodyHandler.class))).thenAnswer(inv->CompletableFuture.completedFuture(response(200,body)));
            var c=new CloudinaryAdminClient(json,limits,"demo-cloud","test-key","test-secret",transport);
            assertEquals(502,assertThrows(ApiException.class,()->c.listForListing("SP003")).status);
        }
    }
}
