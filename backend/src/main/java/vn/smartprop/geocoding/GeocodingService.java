package vn.smartprop.geocoding;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.text.Normalizer;
import java.time.Clock;
import java.util.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import vn.smartprop.common.*;
import static vn.smartprop.geocoding.GeocodingDtos.*;

@Service
public class GeocodingService {
    private record Entry(long expires, Result value) {}
    private final Map<String,Entry> cache=new LinkedHashMap<>();
    private final GeocodingProviderClient client;
    private final RequestLimits limits;
    private final boolean enabled;
    private final Provider provider;
    private final String key;
    private final Clock clock;
    @org.springframework.beans.factory.annotation.Autowired
    public GeocodingService(GeocodingProviderClient client, RequestLimits limits,
        @Value("${app.geocoding.enabled:false}") boolean enabled,
        @Value("${app.geocoding.provider:GEOAPIFY}") Provider provider,
        @Value("${app.geocoding.geoapify-key:}") String geoapifyKey,
        @Value("${app.geocoding.google-key:}") String googleKey) {
        this(client,limits,enabled,provider,provider==Provider.GOOGLE?googleKey:geoapifyKey,Clock.systemUTC());
    }
    GeocodingService(GeocodingProviderClient client,RequestLimits limits,boolean enabled,Provider provider,String key,Clock clock) {
        this.client=client;this.limits=limits;this.enabled=enabled;this.provider=provider;this.key=key;this.clock=clock;
    }
    public Result search(Long user,String ip,Search request) {
        if(!request.shareAddress()) throw new ApiException(400,"GEOCODING_CONSENT_REQUIRED","Cần đồng ý gửi địa chỉ tới dịch vụ tìm vị trí.");
        limits.check("geo:user:"+user,10,60);
        limits.check("geo:ip:"+ip,30,60);
        if(!enabled||key==null||key.isBlank()) throw new ApiException(503,"GEOCODING_NOT_CONFIGURED","Tìm vị trí tự động chưa được cấu hình. Bạn vẫn có thể đặt ghim thủ công.");
        String query=normalize(request);
        String cacheKey=user+":"+hash(query);
        long now=clock.millis();
        synchronized(cache) {
            cache.values().removeIf(entry->entry.expires<=now);
            var existing=cache.get(cacheKey);
            if(existing!=null) return existing.value;
        }
        // Single-instance hard limits include all publishers. Cache hits do not consume paid calls.
        limits.check("geo:egress",1,1);
        limits.check("geo:daily",250,86400);
        var candidates=client.search(provider,key,query);
        var result=new Result(candidates.isEmpty()?"ZERO_RESULTS":"OK",provider,candidates);
        if(provider==Provider.GEOAPIFY) synchronized(cache) {
            if(cache.size()>=256) cache.remove(cache.keySet().iterator().next());
            cache.put(cacheKey,new Entry(now+(candidates.isEmpty()?60_000:600_000),result));
        }
        return result;
    }
    static String normalize(Search request) {
        var parts=new LinkedHashSet<String>();
        for(String value:new String[]{request.address(),request.ward(),request.district(),request.city(),"Việt Nam"}) {
            if(value==null) continue;
            for(String part:Normalizer.normalize(value,Normalizer.Form.NFC).split(",")) {
                String text=part.strip().replaceAll("\\s+"," ");
                if(text.chars().anyMatch(Character::isISOControl)) throw ApiInputs.bad("Địa chỉ tìm kiếm chứa ký tự không hợp lệ.");
                if(!text.isBlank()&&parts.stream().noneMatch(p->p.equalsIgnoreCase(text))) parts.add(text);
            }
        }
        String query=String.join(", ",parts);
        if(request.address()==null||request.address().isBlank()||request.city()==null||request.city().isBlank()||query.length()>600)
            throw ApiInputs.bad("Nhập địa chỉ và thành phố; chuỗi tìm kiếm tối đa 600 ký tự.");
        return query;
    }
    private static String hash(String value) {
        try {return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));}
        catch(NoSuchAlgorithmException e) {throw new IllegalStateException("SHA-256 unavailable");}
    }
}
