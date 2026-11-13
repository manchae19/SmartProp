package vn.smartprop.modules.gis.poi;
import com.fasterxml.jackson.databind.JsonNode;
import java.time.*;
import java.util.*;
import java.util.concurrent.*;
import org.springframework.stereotype.Service;
import vn.smartprop.common.ApiException;
import vn.smartprop.modules.property.Property;
import vn.smartprop.modules.property.PropertyService;
import static vn.smartprop.modules.gis.poi.NearbyDtos.*;

@Service
public class NearbyService {
    static final Map<String,List<String>> GROUPS=Map.of(
        "education",List.of("education","childcare"),
        "health",List.of("healthcare"),
        "shopping",List.of("commercial.supermarket","commercial.shopping_mall","commercial.marketplace"),
        "park",List.of("leisure.park"),
        "bank",List.of("service.financial.bank"),
        "dining",List.of("catering.restaurant","catering.cafe"),
        "tourism",List.of("tourism","accommodation.hotel"),
        "entertainment",List.of("entertainment"),
        "transport",List.of("public_transport"));
    static final List<Attribution> CREDITS=List.of(
        new Attribution("© OpenStreetMap contributors","https://www.openstreetmap.org/copyright"),
        new Attribution("Powered by Geoapify","https://www.geoapify.com/"));
    private record Entry(Instant until,Result result){}
    private final Map<String,Entry> cache=new LinkedHashMap<>();
    private final ConcurrentHashMap<String,CompletableFuture<Result>> flights=new ConcurrentHashMap<>();
    private final Semaphore slots=new Semaphore(8);
    private final PropertyLocationEvidence locationEvidence;
    private final PropertyService properties;
    private final PointOfInterestRepository pois;
    private final GeoapifyPlacesClient provider;
    public NearbyService(PropertyService properties,PointOfInterestRepository pois,GeoapifyPlacesClient provider,PropertyLocationEvidence locationEvidence){
        this.locationEvidence=locationEvidence;this.properties=properties;this.pois=pois;this.provider=provider;
    }
    public static List<String> categories(String raw){
        if(raw==null||raw.isBlank())throw bad("Chọn ít nhất một nhóm tiện ích.");
        var selected=new TreeSet<String>();
        for(String value:raw.split(",",-1)){String key=value.strip().toLowerCase(Locale.ROOT);if(!GROUPS.containsKey(key))throw bad("Nhóm tiện ích không hợp lệ.");selected.add(key);}
        if(selected.size()>GROUPS.size())throw bad("Quá nhiều nhóm tiện ích.");
        return List.copyOf(selected);
    }
    public Result forAdvisor(String id,int radius,String input){return forAdvisor(id,radius,input,false);}
    public Result forAdvisor(String id,int radius,String input,boolean allowEstimatedOrigin){
        if(!Set.of(500,1000,2000,5000).contains(radius))throw bad("Bán kính không hợp lệ.");
        var selected=categories(input);
        var property=properties.publicProperty(id);
        if(property.location==null||!valid(property.location.getY(),property.location.getX()))
            return new Result(id,null,radius,selected,"STRAIGHT_LINE",List.of(),Instant.now(),false,false,"UNKNOWN","LOCATION_UNAVAILABLE",CREDITS);
        var evidence=locationEvidence.resolve(property);
        String accuracy=allowEstimatedOrigin&&"UNKNOWN".equals(evidence.accuracy())?"USER_PROVIDED":evidence.accuracy();
        var location=new Location(property.location.getY(),property.location.getX(),accuracy,evidence.source(),evidence.reference(),evidence.verifiedAt());
        if(!Set.of("EXACT_PROPERTY","BUILDING_ONLY","USER_PROVIDED").contains(accuracy))
            return new Result(id,location,radius,selected,"STRAIGHT_LINE",List.of(),Instant.now(),false,false,"UNKNOWN","LOCATION_UNVERIFIED",CREDITS);
        var result=nearby(id,radius,input);
        return new Result(id,location,radius,selected,result.distanceType(),result.items().stream().filter(p->"GEOAPIFY".equals(p.provider())).toList(),result.fetchedAt(),result.cacheHit(),result.truncated(),result.coverage(),result.status(),result.attribution());
    }
    public Result nearby(String id,int radius,String input){
        if(!Set.of(500,1000,2000,5000).contains(radius))throw bad("Bán kính hỗ trợ: 500, 1000, 2000 hoặc 5000 mét.");
        var selected=categories(input);
        Property property=properties.publicProperty(id); // Always recheck visibility, including cache hits.
        if(property.location==null||!valid(property.location.getY(),property.location.getX()))
            return new Result(property.id,null,radius,selected,"STRAIGHT_LINE",List.of(),Instant.now(),false,false,"UNKNOWN","LOCATION_UNAVAILABLE",CREDITS);
        double lat=property.location.getY(),lon=property.location.getX();
        String key=property.id+":"+property.contentVersion+":"+lat+":"+lon+":"+radius+":"+String.join(",",selected);
        Instant now=Instant.now();
        synchronized(cache){cache.values().removeIf(e->!e.until.isAfter(now));var hit=cache.get(key);if(hit!=null)return hit.result.cached();}
        var future=new CompletableFuture<Result>();var existing=flights.putIfAbsent(key,future);
        if(existing!=null){try{return existing.get(12,TimeUnit.SECONDS).cached();}
            catch(Exception e){if(e instanceof InterruptedException)Thread.currentThread().interrupt();if(e instanceof ExecutionException&&e.getCause() instanceof ApiException api)throw api;throw new ApiException(504,"NEARBY_TIMEOUT","Đang tải tiện ích, vui lòng thử lại.");}}
        boolean acquired=slots.tryAcquire();
        try{
            if(!acquired)throw new ApiException(503,"NEARBY_BUSY","Hệ thống tiện ích đang bận.");
            var upstream=selected.stream().flatMap(c->GROUPS.get(c).stream()).distinct().sorted().toList();
            JsonNode body=provider.search(lat,lon,radius,upstream);
            var found=new LinkedHashMap<String,Place>();
            for(var feature:body.path("features")){
                if(found.size()>=GeoapifyPlacesClient.LIMIT)break;
                var data=feature.path("properties");var coords=feature.path("geometry").path("coordinates");
                if(!"Point".equals(feature.path("geometry").path("type").asText())||!coords.isArray()||coords.size()<2||!coords.get(0).isNumber()||!coords.get(1).isNumber())continue;
                double x=coords.get(0).asDouble(),y=coords.get(1).asDouble();if(!valid(y,x))continue;
                String name=data.path("name").asText("").strip(),placeId=data.path("place_id").asText("").strip();
                if(name.isBlank()||placeId.isBlank()||name.length()>500||placeId.length()>4096)continue;
                var raw=new ArrayList<String>();data.path("categories").forEach(c->raw.add(c.asText()));
                var groups=selected.stream().filter(g->raw.stream().anyMatch(c->GROUPS.get(g).stream().anyMatch(prefix->c.equals(prefix)||c.startsWith(prefix+".")))).toList();
                if(groups.isEmpty())continue;
                double distance=distance(lat,lon,y,x);if(distance>radius)continue;
                var place=new Place("geoapify:"+placeId,name,groups,groups.get(0),y,x,distance,
                    nullable(data.path("formatted").asText("")),"GEOAPIFY",placeId,null);
                found.putIfAbsent(place.id(),place);
            }
            String point=String.format(Locale.ROOT,"POINT(%.10f %.10f)",lon,lat);
            for(var local:pois.nearby(point,null,radius,100)){
                String group=legacyGroup(local.getCategory());
                if(local.getName()==null||local.getName().isBlank()||!selected.contains(group)||local.getLatitude()==null||local.getLongitude()==null||!valid(local.getLatitude(),local.getLongitude()))continue;
                double d=distance(lat,lon,local.getLatitude(),local.getLongitude());if(d>radius)continue;
                // Prefer a provider result over a duplicate persisted provider identity.
                boolean duplicate=local.getExternalId()!=null&&found.values().stream().anyMatch(v->Objects.equals(v.sourcePlaceId(),local.getExternalId()));
                if(!duplicate)found.putIfAbsent("local:"+local.getId(),new Place("local:"+local.getId(),local.getName(),List.of(group),group,
                    local.getLatitude(),local.getLongitude(),d,null,Optional.ofNullable(local.getSourceName()).orElse("LOCAL_DATABASE"),local.getExternalId(),null));
            }
            var ordered=found.values().stream().sorted(Comparator.comparingDouble(Place::distanceMeters).thenComparing(Place::id)).toList();
            boolean truncated=body.path("features").size()>=GeoapifyPlacesClient.LIMIT||ordered.size()>100;
            var result=new Result(property.id,new Location(lat,lon,"UNKNOWN"),radius,selected,"STRAIGHT_LINE",
                List.copyOf(ordered.subList(0,Math.min(100,ordered.size()))),Instant.now(),false,truncated,"PARTIAL",ordered.isEmpty()?"EMPTY":"OK",CREDITS);
            synchronized(cache){if(cache.size()>=512)cache.remove(cache.keySet().iterator().next());cache.put(key,new Entry(Instant.now().plusSeconds(ordered.isEmpty()?120:900),result));}
            future.complete(result);return result;
        }catch(RuntimeException e){future.completeExceptionally(e);throw e;}
        finally{flights.remove(key,future);if(acquired)slots.release();}
    }
    static boolean valid(double lat,double lon){return Double.isFinite(lat)&&Double.isFinite(lon)&&lat>=-90&&lat<=90&&lon>-180&&lon<=180;}
    static double distance(double lat1,double lon1,double lat2,double lon2){
        double x=Math.toRadians(lat2-lat1),y=Math.toRadians(lon2-lon1);
        double a=Math.sin(x/2)*Math.sin(x/2)+Math.cos(Math.toRadians(lat1))*Math.cos(Math.toRadians(lat2))*Math.sin(y/2)*Math.sin(y/2);
        return 6371008.8*2*Math.atan2(Math.sqrt(Math.min(1,a)),Math.sqrt(Math.max(0,1-a)));
    }
    static String legacyGroup(String category){return switch(category==null?"":category.toUpperCase(Locale.ROOT)){case "SCHOOL"->"education";case "HOSPITAL"->"health";case "SUPERMARKET"->"shopping";case "PARK"->"park";case "BANK"->"bank";default->"";};}
    static String nullable(String value){return value.isBlank()?null:value;}
    static ApiException bad(String message){return new ApiException(400,"VALIDATION_ERROR",message);}
}
