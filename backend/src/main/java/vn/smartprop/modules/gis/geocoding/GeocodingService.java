package vn.smartprop.modules.gis.geocoding;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Clock;
import java.util.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import vn.smartprop.common.*;
import vn.smartprop.config.*;
import static vn.smartprop.modules.gis.geocoding.GeocodingDtos.*;

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
    private final GeocodingScopes scopes;
    @org.springframework.beans.factory.annotation.Autowired
    public GeocodingService(GeocodingProviderClient client, RequestLimits limits,
        @Value("${app.geocoding.enabled:false}") boolean enabled,
        @Value("${app.geocoding.provider:GEOAPIFY}") Provider provider,
        @Value("${app.geocoding.geoapify-key:}") String geoapifyKey,
        @Value("${app.geocoding.google-key:}") String googleKey,GeocodingScopes scopes) {
        this(client,limits,enabled,provider,provider==Provider.GOOGLE?googleKey:geoapifyKey,Clock.systemUTC(),scopes);
    }
    GeocodingService(GeocodingProviderClient client,RequestLimits limits,boolean enabled,Provider provider,String key,Clock clock) {
        this(client,limits,enabled,provider,key,clock,new GeocodingScopes(new com.fasterxml.jackson.databind.ObjectMapper()));
    }
    GeocodingService(GeocodingProviderClient client,RequestLimits limits,boolean enabled,Provider provider,String key,Clock clock,GeocodingScopes scopes) {
        this.client=client;this.limits=limits;this.enabled=enabled;this.provider=provider;this.key=key;this.clock=clock;this.scopes=scopes;
    }
    public Availability configuration() {
        String reason=!enabled?"DISABLED":key==null||key.isBlank()?"MISSING_PROVIDER_KEY":"READY";
        return new Availability(reason.equals("READY"),provider,reason,provider==Provider.GOOGLE?"GOOGLE":"OSM",provider==Provider.GEOAPIFY);
    }
    public Result search(Long user,String ip,Search request) {
        if(!request.shareAddress()) throw new ApiException(400,"GEOCODING_CONSENT_REQUIRED","Cần đồng ý gửi địa chỉ tới dịch vụ tìm vị trí.");
        String query=normalize(request);
        limits.check("geo:user:"+user,10,60);
        limits.check("geo:ip:"+ip,30,60);
        if(!enabled||key==null||key.isBlank()) throw new ApiException(503,"GEOCODING_NOT_CONFIGURED","Tìm vị trí tự động chưa được cấu hình. Bạn vẫn có thể đặt ghim thủ công.");
        var scope=scopes.resolve(request);
        if(!scope.available())return new Result(scope.status(),provider,List.of());
        if(provider!=Provider.GEOAPIFY)return new Result("SCOPE_UNAVAILABLE",provider,List.of());
        String cacheKey=user+":"+hash(scope.id()+"\n"+scope.street()+"\n"+query);
        long now=clock.millis();
        synchronized(cache) {
            cache.values().removeIf(entry->entry.expires<=now);
            var existing=cache.get(cacheKey);
            if(existing!=null) return existing.value;
        }
        // Single-instance hard limits include all publishers. Cache hits do not consume paid calls.
        limits.check("geo:egress",1,1);
        limits.check("geo:daily",250,86400);
        var received=client.search(provider,key,query,scope);
        var candidates=scopes.filter(received,scope);
        // One bounded alternate query, only after a successful provider response with no accepted candidates.
        String reduced=scopes.reducedQuery(request);
        if(candidates.isEmpty()&&!reduced.isBlank()&&!reduced.equalsIgnoreCase(query)){
            try{Thread.sleep(1050);}catch(InterruptedException e){Thread.currentThread().interrupt();throw new ApiException(503,"GEOCODING_INTERRUPTED","Tìm vị trí đã bị gián đoạn.");}
            limits.check("geo:egress",1,1);
            limits.check("geo:daily",250,86400);
            var retry=client.search(provider,key,reduced,scope); // Same polygon and street validation; never broaden geography.
            candidates=scopes.filter(retry,scope).stream().map(c->{var x=c.context();return c.reviewed(new Context(x.countryCode(),x.localities(),x.districts(),x.wards(),x.resultType(),x.precision(),x.localityMatched(),
                "Tìm bằng số nhà/tên đường rút gọn; giữ nguyên phạm vi quận. "+x.warning(),x.street()));}).toList();
            if(!retry.isEmpty())received=retry;
        }
        var result=new Result(candidates.isEmpty()?(received.isEmpty()?"ZERO_RESULTS":"NO_MATCHING_LOCALITY"):"OK",provider,candidates);
        if(provider==Provider.GEOAPIFY) synchronized(cache) {
            if(cache.size()>=256) cache.remove(cache.keySet().iterator().next());
            cache.put(cacheKey,new Entry(now+(candidates.isEmpty()?60_000:600_000),result));
        }
        return result;
    }
    static String normalize(Search request) {
        return GeocodingAddress.normalize(request);
    }
    private static String hash(String value) {
        try {return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));}
        catch(NoSuchAlgorithmException e) {throw new IllegalStateException("SHA-256 unavailable");}
    }
}
