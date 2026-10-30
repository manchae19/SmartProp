package vn.smartprop.geocoding;

import com.fasterxml.jackson.databind.*;
import java.io.*;
import java.net.*;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.*;
import java.nio.ByteBuffer;
import java.util.concurrent.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.stereotype.Component;
import vn.smartprop.common.ApiException;
import static vn.smartprop.geocoding.GeocodingDtos.*;

/** Fixed HTTPS destinations. No redirects, arbitrary URL, raw payload, or key in API errors/logs. */
@Component
public class GeocodingProviderClient {
    static final Duration REQUEST_TIMEOUT=Duration.ofSeconds(8);
    static final int MAX_BODY_BYTES=131072;
    private static final Logger log=LoggerFactory.getLogger(GeocodingProviderClient.class);
    private final ObjectMapper mapper;
    private final HttpClient http;
    private final Duration requestTimeout;
    @org.springframework.beans.factory.annotation.Autowired
    public GeocodingProviderClient(ObjectMapper mapper) {
        this(mapper, HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3))
             .followRedirects(HttpClient.Redirect.NEVER).build());
    }
    GeocodingProviderClient(ObjectMapper mapper, HttpClient http) { this(mapper,http,REQUEST_TIMEOUT); }
    GeocodingProviderClient(ObjectMapper mapper,HttpClient http,Duration timeout) {
        if(timeout.isNegative()||timeout.isZero()||timeout.compareTo(REQUEST_TIMEOUT)>0)throw new IllegalArgumentException("Bounded provider timeout required");
        this.mapper=mapper;this.http=http;this.requestTimeout=timeout;
    }
    List<Candidate> search(Provider provider,String key,String query){return fetch(provider,key,query,"countrycode:vn");}
    public List<Candidate> search(Provider provider,String key,String query,GeocodingScopes.Scope scope){
        if(provider!=Provider.GEOAPIFY||scope==null||!scope.available())throw new IllegalArgumentException("Verified Geoapify scope required");
        return fetch(provider,key,query,scope.filter());
    }
    private List<Candidate> fetch(Provider provider, String key, String query,String filter) {
        String encoded=URLEncoder.encode(query,StandardCharsets.UTF_8);
        String secret=URLEncoder.encode(key,StandardCharsets.UTF_8);
        String endpoint=provider==Provider.GOOGLE
            ? "https://maps.googleapis.com/maps/api/geocode/json?components=country%3AVN&language=vi&region=vn&address="+encoded+"&key="+secret
            : "https://api.geoapify.com/v1/geocode/search?format=json&limit=5&lang=vi&bias=countrycode%3Anone&filter="+URLEncoder.encode(filter,StandardCharsets.UTF_8)+"&text="+encoded+"&apiKey="+secret;
        var request=HttpRequest.newBuilder(URI.create(endpoint)).timeout(requestTimeout)
            .header("Accept","application/json").header("User-Agent","SmartProp/1.0 address-picker").GET().build();
        long started=System.nanoTime();int httpStatus=0;String outcome="PROVIDER_ERROR",phase="REQUEST";
        String requestId=Optional.ofNullable(MDC.get("geocodingRequestId")).orElseGet(()->UUID.randomUUID().toString());
        CompletableFuture<HttpResponse<byte[]>> pending=null;
        try {
            pending=http.sendAsync(request,info->new LimitedBodySubscriber());
            var response=pending.get(requestTimeout.toMillis(),TimeUnit.MILLISECONDS);
            httpStatus=response.statusCode();phase="RESPONSE";
                if(response.statusCode()==429) throw failure(429,"GEOCODING_QUOTA","Dịch vụ tìm vị trí đã hết hạn mức. Thử lại sau hoặc chọn ghim thủ công.");
                if(response.statusCode()==401||response.statusCode()==403) throw failure(503,"GEOCODING_AUTH_FAILED","Dịch vụ tìm vị trí chưa được cấu hình hợp lệ. Hãy đặt ghim thủ công hoặc liên hệ quản trị viên.");
                if(response.statusCode()!=200) throw failure(502,"GEOCODING_PROVIDER_ERROR","Dịch vụ tìm vị trí đang gặp lỗi. Bạn vẫn có thể chọn ghim thủ công.");
                byte[] bytes=response.body();
                if(bytes==null||bytes.length>MAX_BODY_BYTES)throw failure(502,"GEOCODING_PROVIDER_ERROR","Phản hồi tìm vị trí không hợp lệ.");
                var result=parse(provider,mapper.readTree(bytes));outcome="OK";return result;
        } catch (TimeoutException e) {
            if(pending!=null)pending.cancel(true);outcome="GEOCODING_TIMEOUT";
            throw failure(504,outcome,"Tìm vị trí quá thời gian. Thử lại hoặc chọn ghim thủ công.");
        } catch (ExecutionException e) {
            Throwable cause=e.getCause();while(cause instanceof CompletionException&&cause.getCause()!=null)cause=cause.getCause();
            if(cause instanceof HttpTimeoutException){phase=cause instanceof HttpConnectTimeoutException?"CONNECT":"REQUEST";outcome="GEOCODING_TIMEOUT";throw failure(504,outcome,"Tìm vị trí quá thời gian. Thử lại hoặc chọn ghim thủ công.");}
            outcome="GEOCODING_PROVIDER_ERROR";throw failure(502,outcome,"Không nhận được phản hồi hợp lệ từ dịch vụ tìm vị trí.");
        } catch (InterruptedException e) {
            if(pending!=null)pending.cancel(true);Thread.currentThread().interrupt();outcome="GEOCODING_UNAVAILABLE";throw failure(503,outcome,"Tìm vị trí đã bị gián đoạn.");
        } catch (ApiException e) {outcome=e.code;throw e;
        } catch (IOException e) {outcome="GEOCODING_PROVIDER_ERROR";throw failure(502,outcome,"Không nhận được phản hồi hợp lệ từ dịch vụ tìm vị trí.");
        } finally {
            // No address, user, URL, response body, key or exception text is logged.
            log.info("geocoding_provider requestId={} provider={} phase={} httpStatus={} outcome={} elapsedMs={}",requestId,provider,phase,httpStatus,outcome,(System.nanoTime()-started)/1_000_000);
        }
    }
    /** Completion waits for the entire bounded body, so the deadline also covers a stalled stream. */
    static final class LimitedBodySubscriber implements HttpResponse.BodySubscriber<byte[]> {
        private final HttpResponse.BodySubscriber<byte[]> delegate=HttpResponse.BodySubscribers.ofByteArray();
        private Flow.Subscription subscription;private long size;private boolean failed;
        public CompletionStage<byte[]> getBody(){return delegate.getBody();}
        public void onSubscribe(Flow.Subscription value){subscription=value;delegate.onSubscribe(value);}
        public void onNext(List<ByteBuffer> buffers){
            if(failed)return;
            for(var buffer:buffers){size+=buffer.remaining();if(size>MAX_BODY_BYTES){failed=true;subscription.cancel();delegate.onError(new IOException("Provider body exceeds limit"));return;}}
            delegate.onNext(buffers);
        }
        public void onError(Throwable error){if(!failed){failed=true;delegate.onError(error);}}
        public void onComplete(){if(!failed)delegate.onComplete();}
    }
    static ApiException failure(int status,String code,String message) { return new ApiException(status,code,message); }
    List<Candidate> parse(Provider provider, JsonNode root) {
        if(root==null||!root.isObject()) throw failure(502,"GEOCODING_PROVIDER_ERROR","Phản hồi tìm vị trí không hợp lệ.");
        if(provider==Provider.GOOGLE) {
            String status=root.path("status").asText();
            if(status.equals("ZERO_RESULTS")) return List.of();
            if(status.equals("OVER_QUERY_LIMIT")||status.equals("OVER_DAILY_LIMIT")) throw failure(429,"GEOCODING_QUOTA","Dịch vụ tìm vị trí đã hết hạn mức.");
            if(status.equals("REQUEST_DENIED")) throw failure(503,"GEOCODING_AUTH_FAILED","Dịch vụ tìm vị trí chưa được cấu hình hợp lệ.");
            if(!status.equals("OK")) throw failure(502,"GEOCODING_PROVIDER_ERROR","Dịch vụ tìm vị trí không trả về kết quả hợp lệ.");
        }
        JsonNode values=root.path("results");
        if(!values.isArray()) throw failure(502,"GEOCODING_PROVIDER_ERROR","Phản hồi tìm vị trí không hợp lệ.");
        var output=new ArrayList<Candidate>();
        for(var node:values) {
            if(output.size()==5) break;
            boolean google=provider==Provider.GOOGLE;
            if(google&&contains(node.path("types"),"real_estate_agency"))continue;
            var geometry=node.path("geometry");
            var lat=google?geometry.path("location").path("lat"):node.path("lat");
            var lon=google?geometry.path("location").path("lng"):node.path("lon");
            if(!lat.isNumber()||!lon.isNumber()) continue;
            double y=lat.asDouble(),x=lon.asDouble();
            String address=node.path(google?"formatted_address":"formatted").asText("");
            if(!Double.isFinite(x)||!Double.isFinite(y)||y < -90||y>90||x<=-180||x>180||address.isBlank()||address.length()>1000) continue;
            Accuracy accuracy=Accuracy.UNKNOWN;
            Level level=Level.UNKNOWN;
            boolean addressMatched=false;
            Double confidence=null;
            if(google) {
                accuracy=switch(geometry.path("location_type").asText()) {
                    case "ROOFTOP" -> Accuracy.EXACT;
                    case "RANGE_INTERPOLATED" -> Accuracy.INTERPOLATED;
                    case "GEOMETRIC_CENTER","APPROXIMATE" -> Accuracy.APPROXIMATE;
                    default -> Accuracy.UNKNOWN;
                };
                boolean house=false;
                for(var type:node.path("types")) if(Set.of("street_address","premise","subpremise").contains(type.asText())) house=true;
                addressMatched=house&&!node.path("partial_match").asBoolean(false);
                // Geocoder precision is not proof of a particular apartment/parcel or public consent.
                level=house?Level.BUILDING_ONLY:Level.APPROXIMATE;
            } else {
                var rank=node.path("rank");
                double n=rank.path("confidence").asDouble(-1);
                if(Double.isFinite(n)&&n>=0&&n<=1) confidence=n;
                boolean building=node.path("result_type").asText().equals("building");
                addressMatched=building&&!node.path("housenumber").asText().isBlank()
                    &&rank.path("match_type").asText().equals("full_match")&&confidence!=null&&confidence>=0.9;
                level=building?Level.BUILDING_ONLY:Level.APPROXIMATE;
                // Geoapify does not supply a ROOFTOP/interpolation geometry guarantee. Do not invent one.
                accuracy=building?Accuracy.UNKNOWN:Accuracy.APPROXIMATE;
            }
            String id=provider.name().toLowerCase(Locale.ROOT)+"-"+output.size();
            output.add(new Candidate(id,address,y,x,provider,accuracy,level,confidence,addressMatched,!google,
                google?"GOOGLE":"OSM",google?"Google Maps":"Powered by Geoapify · © OpenStreetMap contributors",context(provider,node)));
        }
        return List.copyOf(output);
    }
    private static boolean contains(JsonNode values,String target) { for(var value:values)if(value.asText().equals(target))return true;return false; }
    private static List<String> texts(JsonNode node,String... fields) {
        var values=new LinkedHashSet<String>();for(String field:fields){String value=node.path(field).asText("").strip();if(!value.isBlank()&&value.length()<=150)values.add(value);}return List.copyOf(values);
    }
    private static List<String> components(JsonNode node,String... kinds) {
        var accepted=Set.of(kinds);var values=new LinkedHashSet<String>();
        for(var part:node.path("address_components"))for(var type:part.path("types"))if(accepted.contains(type.asText())){
            String value=part.path("long_name").asText("").strip();if(!value.isBlank()&&value.length()<=150)values.add(value);
        }
        return List.copyOf(values);
    }
    private static Context context(Provider provider,JsonNode node) {
        boolean google=provider==Provider.GOOGLE;String country="",kind;
        List<String> localities,districts,wards;
        if(google){
            for(var part:node.path("address_components"))if(contains(part.path("types"),"country"))country=part.path("short_name").asText("").toLowerCase(Locale.ROOT);
            localities=components(node,"locality","administrative_area_level_1");districts=components(node,"administrative_area_level_2","sublocality_level_1");wards=components(node,"administrative_area_level_3","sublocality_level_2");
            kind=contains(node.path("types"),"route")?"street":contains(node.path("types"),"street_address")||contains(node.path("types"),"premise")||contains(node.path("types"),"subpremise")?"building":contains(node.path("types"),"locality")||contains(node.path("types"),"political")?"area":"unknown";
        }else{country=node.path("country_code").asText("").toLowerCase(Locale.ROOT);localities=texts(node,"city","state");districts=texts(node,"district","city_district","county");wards=texts(node,"suburb","quarter");kind=node.path("result_type").asText("unknown");}
        if(!country.matches("[a-z]{2}"))country="";
        Precision precision=kind.equals("street")?Precision.APPROXIMATE_STREET:Set.of("area","suburb","district","postcode","city","county","state","country").contains(kind)?Precision.APPROXIMATE_AREA:Precision.UNKNOWN;
        // A house/building match is not proof of the exact property or parcel. Never manufacture EXACT/PROJECT.
        String street=google?components(node,"route").stream().findFirst().orElse(""):node.path("street").asText("");
        return new Context(country,localities,districts,wards,kind,precision,false,"",street);
    }
}
