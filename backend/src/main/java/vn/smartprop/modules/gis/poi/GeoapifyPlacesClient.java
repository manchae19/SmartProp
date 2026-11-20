package vn.smartprop.modules.gis.poi;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.*;
import java.net.*;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;
import java.util.concurrent.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import vn.smartprop.common.ApiException;
import vn.smartprop.common.RequestLimits;

/** Fixed provider destination. Never log a request URI containing the server key. */
@Component
public class GeoapifyPlacesClient {
    static final int LIMIT=200, MAX_BYTES=1048576;
    private final ObjectMapper json;
    private final RequestLimits limits;
    private final String key;
    private final boolean enabled;
    private final HttpClient client;
    @org.springframework.beans.factory.annotation.Autowired
    public GeoapifyPlacesClient(ObjectMapper json,RequestLimits limits,
        @Value("${app.geocoding.geoapify-key:}") String key,
        @Value("${app.places.enabled:${app.geocoding.enabled:false}}") boolean enabled){
        this(json,limits,key,enabled,HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3)).followRedirects(HttpClient.Redirect.NEVER).build());
    }
    GeoapifyPlacesClient(ObjectMapper json,RequestLimits limits,String key,boolean enabled,HttpClient client){
        this.json=json;this.limits=limits;this.key=key;this.enabled=enabled;this.client=client;
    }
    /** True when a provider key and the places flag are both present. */
    public boolean configured(){return enabled&&key!=null&&!key.isBlank();}
    public JsonNode search(double latitude,double longitude,int radius,List<String> categories){
        String filter="circle:"+longitude+","+latitude+","+radius;
        String url="https://api.geoapify.com/v2/places?categories="+encode(String.join(",",categories))
            +"&filter="+encode(filter)+"&bias="+encode("proximity:"+longitude+","+latitude)
            +"&limit="+LIMIT+"&lang=vi&apiKey="+encode(key);
        return request(url);
    }
    /** Rectangle search bounded to a verified district polygon's envelope. */
    public JsonNode searchBounds(double west,double south,double east,double north,List<String> categories){
        if(!Double.isFinite(west)||!Double.isFinite(south)||!Double.isFinite(east)||!Double.isFinite(north)
            ||west>=east||south>=north||east-west>3||north-south>3)
            throw new ApiException(400,"VALIDATION_ERROR","Phạm vi tiện ích không hợp lệ.");
        String filter="rect:"+west+","+south+","+east+","+north;
        return request("https://api.geoapify.com/v2/places?categories="+encode(String.join(",",categories))
            +"&filter="+encode(filter)+"&limit="+LIMIT+"&lang=vi&apiKey="+encode(key));
    }
    /** Walking or driving route between two validated points. */
    public JsonNode route(double fromLat,double fromLon,double toLat,double toLon,String mode){
        return route(fromLat,fromLon,toLat,toLon,mode,System.nanoTime()+TimeUnit.SECONDS.toNanos(8));
    }
    /**
     * Same route, bounded by the caller's deadline instead of a fixed eight seconds.
     *
     * The caller may already have spent part of its window waiting for a lock, so the
     * request and the body read must both fit in what is left. A call that cannot finish
     * in time is reported as a timeout, never as a missing route.
     */
    public JsonNode route(double fromLat,double fromLon,double toLat,double toLon,String mode,long deadline){
        if(!NearbyService.valid(fromLat,fromLon)||!NearbyService.valid(toLat,toLon)
            ||!java.util.Set.of("walk","drive").contains(mode))
            throw new ApiException(400,"VALIDATION_ERROR","Điểm hoặc phương tiện không hợp lệ.");
        String waypoints=fromLat+","+fromLon+"|"+toLat+","+toLon;
        return request("https://api.geoapify.com/v1/routing?waypoints="+encode(waypoints)
            +"&mode="+encode(mode)+"&units=metric&format=geojson&apiKey="+encode(key),deadline);
    }
    private JsonNode request(String url){return request(url,System.nanoTime()+TimeUnit.SECONDS.toNanos(8));}
    private JsonNode request(String url,long deadline){
        if(!enabled||key==null||key.isBlank())throw new ApiException(503,"NEARBY_NOT_CONFIGURED","Nguồn tiện ích chưa được cấu hình.");
        // Share the existing application's outbound request budget with geocoding.
        limits.check("geo:egress",1,1,"geo:egress");limits.check("geo:daily",250,86400,"geo:daily");
        CompletableFuture<HttpResponse<InputStream>> pending=null;
        try{
            long remaining=Math.max(1,deadline-System.nanoTime());
            var request=HttpRequest.newBuilder(URI.create(url)).timeout(Duration.ofNanos(remaining))
                .header("Accept","application/json").header("User-Agent","SmartProp/1.0 nearby-places").GET().build();
            pending=client.sendAsync(request,HttpResponse.BodyHandlers.ofInputStream());
            var response=pending.get(remaining,TimeUnit.NANOSECONDS);
            try(var input=response.body()){
                int code=response.statusCode();
                if(code==429)throw new ApiException(503,"NEARBY_QUOTA_EXCEEDED","Nguồn tiện ích đang giới hạn truy cập. Vui lòng thử lại sau.");
                if(code==401||code==403)throw new ApiException(503,"NEARBY_PROVIDER_AUTH","Cấu hình truy cập nguồn tiện ích chưa hợp lệ.");
                if(code!=200)throw new ApiException(502,"NEARBY_PROVIDER_ERROR","Nguồn tiện ích chưa phản hồi hợp lệ.");
                // Bound body reading as well as response headers; close/cancel on deadline.
                var read=CompletableFuture.supplyAsync(()->{try{return input.readNBytes(MAX_BYTES+1);}catch(IOException e){throw new CompletionException(e);}});
                byte[] bytes;
                try{bytes=read.get(Math.max(1,deadline-System.nanoTime()),TimeUnit.NANOSECONDS);}finally{read.cancel(true);}
                if(bytes.length>MAX_BYTES)throw new ApiException(502,"NEARBY_PROVIDER_ERROR","Dữ liệu tiện ích vượt giới hạn.");
                var body=json.readTree(bytes);
                if(body==null||!body.path("features").isArray())throw new ApiException(502,"NEARBY_PROVIDER_ERROR","Dữ liệu tiện ích không hợp lệ.");
                return body;
            }
        }catch(ApiException e){throw e;}
        catch(InterruptedException e){Thread.currentThread().interrupt();throw new ApiException(503,"NEARBY_INTERRUPTED","Yêu cầu tiện ích đã bị gián đoạn.");}
        catch(TimeoutException|HttpTimeoutException e){throw new ApiException(504,"NEARBY_TIMEOUT","Tìm tiện ích quá thời gian. Vui lòng thử lại.");}
        catch(Exception e){if(e.getCause() instanceof HttpTimeoutException)throw new ApiException(504,"NEARBY_TIMEOUT","Tìm tiện ích quá thời gian. Vui lòng thử lại.");throw new ApiException(502,"NEARBY_PROVIDER_ERROR","Không kết nối được nguồn tiện ích.");}
        finally{if(pending!=null&&!pending.isDone())pending.cancel(true);}
    }
    private static String encode(String text){return URLEncoder.encode(text,StandardCharsets.UTF_8);}
}
