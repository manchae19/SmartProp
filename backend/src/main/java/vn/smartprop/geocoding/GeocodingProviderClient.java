package vn.smartprop.geocoding;

import com.fasterxml.jackson.databind.*;
import java.io.*;
import java.net.*;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.*;
import org.springframework.stereotype.Component;
import vn.smartprop.common.ApiException;
import static vn.smartprop.geocoding.GeocodingDtos.*;

/** Fixed HTTPS destinations. No redirects, arbitrary URL, raw payload, or key in API errors/logs. */
@Component
public class GeocodingProviderClient {
    private final ObjectMapper mapper;
    private final HttpClient http;
    @org.springframework.beans.factory.annotation.Autowired
    public GeocodingProviderClient(ObjectMapper mapper) {
        this(mapper, HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(2))
             .followRedirects(HttpClient.Redirect.NEVER).build());
    }
    GeocodingProviderClient(ObjectMapper mapper, HttpClient http) { this.mapper=mapper;this.http=http; }
    public List<Candidate> search(Provider provider, String key, String query) {
        String encoded=URLEncoder.encode(query,StandardCharsets.UTF_8);
        String secret=URLEncoder.encode(key,StandardCharsets.UTF_8);
        String endpoint=provider==Provider.GOOGLE
            ? "https://maps.googleapis.com/maps/api/geocode/json?components=country%3AVN&language=vi&region=vn&address="+encoded+"&key="+secret
            : "https://api.geoapify.com/v1/geocode/search?format=json&limit=5&lang=vi&filter=countrycode%3Avn&text="+encoded+"&apiKey="+secret;
        var request=HttpRequest.newBuilder(URI.create(endpoint)).timeout(Duration.ofSeconds(4))
            .header("Accept","application/json").header("User-Agent","SmartProp/1.0 address-picker").GET().build();
        try {
            var response=http.send(request,HttpResponse.BodyHandlers.ofInputStream());
            try (var input=response.body()) {
                if(response.statusCode()==429) throw failure(429,"GEOCODING_QUOTA","Dịch vụ tìm vị trí đã hết hạn mức. Thử lại sau hoặc chọn ghim thủ công.");
                if(response.statusCode()==401||response.statusCode()==403) throw failure(503,"GEOCODING_UNAVAILABLE","Dịch vụ tìm vị trí chưa được cấu hình hợp lệ.");
                if(response.statusCode()!=200) throw failure(502,"GEOCODING_PROVIDER_ERROR","Dịch vụ tìm vị trí đang gặp lỗi. Bạn vẫn có thể chọn ghim thủ công.");
                byte[] bytes=input.readNBytes(131073);
                if(bytes.length>131072) throw failure(502,"GEOCODING_PROVIDER_ERROR","Phản hồi tìm vị trí không hợp lệ.");
                return parse(provider,mapper.readTree(bytes));
            }
        } catch (HttpTimeoutException e) { throw failure(504,"GEOCODING_TIMEOUT","Tìm vị trí quá thời gian. Thử lại hoặc chọn ghim thủ công.");
        } catch (InterruptedException e) { Thread.currentThread().interrupt();throw failure(503,"GEOCODING_UNAVAILABLE","Tìm vị trí đã bị gián đoạn.");
        } catch (IOException e) { throw failure(502,"GEOCODING_PROVIDER_ERROR","Không nhận được phản hồi hợp lệ từ dịch vụ tìm vị trí."); }
    }
    static ApiException failure(int status,String code,String message) { return new ApiException(status,code,message); }
    List<Candidate> parse(Provider provider, JsonNode root) {
        if(root==null||!root.isObject()) throw failure(502,"GEOCODING_PROVIDER_ERROR","Phản hồi tìm vị trí không hợp lệ.");
        if(provider==Provider.GOOGLE) {
            String status=root.path("status").asText();
            if(status.equals("ZERO_RESULTS")) return List.of();
            if(status.equals("OVER_QUERY_LIMIT")||status.equals("OVER_DAILY_LIMIT")) throw failure(429,"GEOCODING_QUOTA","Dịch vụ tìm vị trí đã hết hạn mức.");
            if(status.equals("REQUEST_DENIED")) throw failure(503,"GEOCODING_UNAVAILABLE","Dịch vụ tìm vị trí chưa được cấu hình hợp lệ.");
            if(!status.equals("OK")) throw failure(502,"GEOCODING_PROVIDER_ERROR","Dịch vụ tìm vị trí không trả về kết quả hợp lệ.");
        }
        JsonNode values=root.path("results");
        if(!values.isArray()) throw failure(502,"GEOCODING_PROVIDER_ERROR","Phản hồi tìm vị trí không hợp lệ.");
        var output=new ArrayList<Candidate>();
        for(var node:values) {
            if(output.size()==5) break;
            boolean google=provider==Provider.GOOGLE;
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
                google?"GOOGLE":"OSM",google?"Google Maps":"Powered by Geoapify · © OpenStreetMap contributors"));
        }
        return List.copyOf(output);
    }
}
