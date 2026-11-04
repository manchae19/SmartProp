package vn.smartprop.modules.media;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.*;
import java.net.*;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.time.*;
import java.util.*;
import java.util.concurrent.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import vn.smartprop.common.ApiException;
import vn.smartprop.common.RequestLimits;

@Component
public class CloudinaryAdminClient {
    private static final int MAX_BYTES=2*1024*1024,MAX_PAGES=100,MAX_ASSETS=5000;
    private final ObjectMapper json;
    private final RequestLimits limits;
    private final HttpClient http;
    private final String cloud,key,secret;
    public record Asset(String cloudName,String assetId,String publicId,String secureUrl,String assetFolder,
                        String format,long bytes,int width,int height,Instant createdAt) {}
    public record Rejected(String assetId,String reason) {}
    public record Preview(String assetFolder,int pages,int resourceCount,List<Asset> assets,List<Rejected> rejected) {}

    @org.springframework.beans.factory.annotation.Autowired
    public CloudinaryAdminClient(ObjectMapper json,RequestLimits limits,
        @Value("${app.cloudinary.cloud-name:}") String cloud,
        @Value("${app.cloudinary.api-key:}") String key,
        @Value("${app.cloudinary.api-secret:}") String secret){
        this(json,limits,cloud,key,secret,HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3))
            .followRedirects(HttpClient.Redirect.NEVER).build());
    }
    CloudinaryAdminClient(ObjectMapper json,RequestLimits limits,String cloud,String key,String secret,HttpClient http){
        this.json=json;this.limits=limits;this.cloud=cloud;this.key=key;this.secret=secret;this.http=http;
    }
    public boolean configured(){return cloud!=null&&cloud.matches("[A-Za-z0-9_-]{1,63}")&&key!=null&&!key.isBlank()&&!key.contains(":")&&secret!=null&&!secret.isBlank();}
    public Preview listForListing(String code){
        if(!configured())throw error(503,"CLOUDINARY_NOT_CONFIGURED","Chưa cấu hình Cloudinary ở Backend.");
        if(code==null||code.length()>32||!code.matches("SP(?:00[1-9]|0[1-9][0-9]|[1-9][0-9]{2,})"))
            throw error(400,"INVALID_LISTING_CODE","Mã tin không hợp lệ.");
        String folder="SmartProp/dev/properties/"+code,cursor=null;
        var seenCursors=new HashSet<String>();
        var assets=new LinkedHashMap<String,Asset>();
        var rejected=new ArrayList<Rejected>();
        long deadline=System.nanoTime()+TimeUnit.SECONDS.toNanos(45);
        int pages=0,total=0;
        do {
            if(++pages>MAX_PAGES)throw error(502,"CLOUDINARY_PAGE_LIMIT","Số trang Cloudinary vượt giới hạn; chưa đồng bộ dữ liệu.");
            limits.check("cloudinary:admin:"+cloud,100,3600);
            String fields="asset_id,public_id,secure_url,asset_folder,resource_type,type,format,bytes,width,height,created_at,access_mode,access_control";
            String endpoint="https://api.cloudinary.com/v1_1/"+cloud+"/resources/by_asset_folder?asset_folder="+encode(folder)
                +"&max_results=100&direction=asc&fields="+encode(fields)+(cursor==null?"":"&next_cursor="+encode(cursor));
            JsonNode body=page(endpoint,deadline);
            if(!body.path("resources").isArray())throw error(502,"CLOUDINARY_INVALID_RESPONSE","Dữ liệu Cloudinary không hợp lệ.");
            for(JsonNode item:body.path("resources")){
                if(++total>MAX_ASSETS)throw error(502,"CLOUDINARY_ASSET_LIMIT","Quá nhiều tài nguyên; chưa đồng bộ dữ liệu.");
                String id=item.path("asset_id").asText("");
                String reason=rejectReason(item,folder);
                if(reason!=null){rejected.add(new Rejected(id,reason));continue;}
                Instant created;
                try{created=Instant.parse(item.path("created_at").asText());}
                catch(Exception e){rejected.add(new Rejected(id,"INVALID_CREATED_AT"));continue;}
                Asset asset=new Asset(cloud,id,item.path("public_id").asText(),item.path("secure_url").asText(),
                    folder,item.path("format").asText(),item.path("bytes").asLong(),item.path("width").asInt(),item.path("height").asInt(),created);
                Asset previous=assets.putIfAbsent(id,asset);
                if(previous!=null&&!previous.equals(asset))throw error(409,"CLOUDINARY_CHANGED_DURING_SCAN","Ảnh thay đổi trong lúc lấy danh sách; hãy thử lại.");
            }
            var next=body.get("next_cursor");
            if(next!=null&&!next.isNull()&&!next.isTextual())throw error(502,"CLOUDINARY_INVALID_CURSOR","Con trỏ phân trang không hợp lệ.");
            cursor=next==null||next.isNull()||next.asText().isBlank()?null:next.asText();
            if(cursor!=null&&(cursor.length()>4096||!seenCursors.add(cursor)))throw error(502,"CLOUDINARY_CURSOR_LOOP","Cloudinary trả con trỏ phân trang lặp hoặc không hợp lệ.");
        }while(cursor!=null);
        return new Preview(folder,pages,total,assets.values().stream().sorted(Comparator.comparing(Asset::createdAt)
            .thenComparing(Asset::publicId).thenComparing(Asset::assetId)).toList(),List.copyOf(rejected));
    }
    private String rejectReason(JsonNode item,String folder){
        if(!folder.equals(item.path("asset_folder").asText()))return "WRONG_ASSET_FOLDER";
        if(!"image".equals(item.path("resource_type").asText())||!"upload".equals(item.path("type").asText()))return "NOT_PUBLIC_UPLOADED_IMAGE";
        if("authenticated".equals(item.path("access_mode").asText())||item.path("access_control").size()>0)return "RESTRICTED_DELIVERY";
        String id=item.path("asset_id").asText(""),publicId=item.path("public_id").asText("");
        if(id.isBlank()||id.length()>128||publicId.isBlank()||publicId.length()>1024)return "INVALID_ASSET_IDENTITY";
        if(!Set.of("jpg","jpeg","png","webp").contains(item.path("format").asText()))return "UNSUPPORTED_IMAGE_FORMAT";
        if(!item.path("bytes").isIntegralNumber()||item.path("bytes").asLong()<1||item.path("bytes").asLong()>LocalFileStore.MAX_BYTES)return "INVALID_IMAGE_SIZE";
        int width=item.path("width").asInt(),height=item.path("height").asInt();
        if(!item.path("width").isIntegralNumber()||!item.path("height").isIntegralNumber()||width<1||height<1||width>12000||height>12000||(long)width*height>40000000)return "INVALID_IMAGE_DIMENSIONS";
        try{
            String value=item.path("secure_url").asText();if(value.length()>2048)return "INVALID_DELIVERY_URL";
            URI url=URI.create(value);
            if(!"https".equals(url.getScheme())||!"res.cloudinary.com".equalsIgnoreCase(url.getHost())
                ||url.getUserInfo()!=null||url.getPort()!=-1||url.getFragment()!=null
                ||!url.getPath().startsWith("/"+cloud+"/image/upload/"))return "INVALID_DELIVERY_URL";
        }catch(Exception e){return "INVALID_DELIVERY_URL";}
        return null;
    }
    private JsonNode page(String endpoint,long overallDeadline){
        long deadline=Math.min(overallDeadline,System.nanoTime()+TimeUnit.SECONDS.toNanos(8));
        long remaining=deadline-System.nanoTime();if(remaining<=0)throw timeout();
        CompletableFuture<HttpResponse<InputStream>> pending=null;
        try{
            String auth=Base64.getEncoder().encodeToString((key+":"+secret).getBytes(StandardCharsets.UTF_8));
            var request=HttpRequest.newBuilder(URI.create(endpoint)).timeout(Duration.ofNanos(remaining))
                .header("Authorization","Basic "+auth).header("Accept","application/json").GET().build();
            pending=http.sendAsync(request,HttpResponse.BodyHandlers.ofInputStream());
            var response=pending.get(remaining,TimeUnit.NANOSECONDS);
            try(var input=response.body()){
                if(response.statusCode()==401||response.statusCode()==403)throw error(503,"CLOUDINARY_AUTH_FAILED","Cloudinary từ chối credentials hoặc quyền Admin API.");
                if(response.statusCode()==429||response.statusCode()==420)throw error(503,"CLOUDINARY_RATE_LIMITED","Cloudinary đang giới hạn truy cập. Hãy thử lại sau.");
                if(response.statusCode()!=200)throw error(502,"CLOUDINARY_PROVIDER_ERROR","Không lấy được danh sách Cloudinary.");
                var read=CompletableFuture.supplyAsync(()->{try{return input.readNBytes(MAX_BYTES+1);}catch(IOException e){throw new CompletionException(e);}});
                byte[] bytes;
                try{bytes=read.get(Math.max(1,deadline-System.nanoTime()),TimeUnit.NANOSECONDS);}finally{read.cancel(true);}
                if(bytes.length>MAX_BYTES)throw error(502,"CLOUDINARY_RESPONSE_TOO_LARGE","Phản hồi Cloudinary vượt giới hạn.");
                var body=json.readTree(bytes);if(body==null||!body.isObject())throw error(502,"CLOUDINARY_INVALID_RESPONSE","Dữ liệu Cloudinary không hợp lệ.");return body;
            }
        }catch(ApiException e){throw e;}
        catch(InterruptedException e){Thread.currentThread().interrupt();throw error(503,"CLOUDINARY_INTERRUPTED","Yêu cầu Cloudinary đã bị gián đoạn.");}
        catch(TimeoutException e){throw timeout();}
        catch(Exception e){if(e.getCause() instanceof HttpTimeoutException)throw timeout();throw error(502,"CLOUDINARY_PROVIDER_ERROR","Không kết nối hoặc không đọc được Cloudinary.");}
        finally{if(pending!=null&&!pending.isDone())pending.cancel(true);}
    }
    private static String encode(String value){return URLEncoder.encode(value,StandardCharsets.UTF_8);}
    private static ApiException timeout(){return error(504,"CLOUDINARY_TIMEOUT","Cloudinary phản hồi quá thời gian; chưa đồng bộ dữ liệu.");}
    private static ApiException error(int status,String code,String message){return new ApiException(status,code,message);}
}
