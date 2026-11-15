package vn.smartprop.modules.gis.poi;
import com.fasterxml.jackson.databind.JsonNode;
import java.time.*;
import java.util.*;
import org.springframework.stereotype.Service;
import vn.smartprop.common.ApiException;
import static vn.smartprop.modules.gis.poi.NearbyDtos.*;

/** Routes only between the current public listing and a POI returned by its nearby lookup. */
@Service
public class PropertyRouteService {
    public record Route(String propertyId,String poiId,int radiusMeters,String mode,Location origin,Place destination,
        double distanceMeters,double durationSeconds,JsonNode geometry,String provider,Instant fetchedAt,List<Attribution> attribution){}
    private record Entry(Instant until,Route route){}
    private final NearbyService nearby;private final GeoapifyPlacesClient provider;
    private final Map<String,Entry> cache=new LinkedHashMap<>();
    public PropertyRouteService(NearbyService nearby,GeoapifyPlacesClient provider){this.nearby=nearby;this.provider=provider;}
    public synchronized Route route(String id,String poiId,int radius,String categories,String mode){
        if(poiId==null||poiId.length()>4100||!Set.of("walk","drive").contains(mode))throw NearbyService.bad("Điểm đến hoặc phương tiện không hợp lệ.");
        var result=nearby.forAdvisor(id,radius,categories,true);
        if(result.location()==null||!Set.of("EXACT_PROPERTY","BUILDING_ONLY","USER_PROVIDED").contains(result.location().accuracy()))
            throw new ApiException(422,"ROUTE_LOCATION_UNAVAILABLE","Chưa có ghim phù hợp để tìm đường đi.");
        var destination=result.items().stream().filter(p->p.id().equals(poiId)).findFirst()
            .orElseThrow(()->new ApiException(404,"ROUTE_POI_NOT_FOUND","Tiện ích không còn trong danh sách của căn nhà và bán kính này."));
        var origin=result.location();
        String key=id+":"+origin.latitude()+":"+origin.longitude()+":"+origin.accuracy()+":"+poiId+":"+destination.latitude()+":"+destination.longitude()+":"+radius+":"+mode;
        Instant now=Instant.now();cache.values().removeIf(e->!e.until().isAfter(now));var hit=cache.get(key);if(hit!=null)return hit.route();
        JsonNode feature=provider.route(origin.latitude(),origin.longitude(),destination.latitude(),destination.longitude(),mode).path("features").path(0);
        var properties=feature.path("properties");var geometry=feature.path("geometry");
        if(!properties.path("distance").isNumber()||!properties.path("time").isNumber())throw unavailable();
        double distance=properties.path("distance").asDouble(),seconds=properties.path("time").asDouble();
        if(!Double.isFinite(distance)||!Double.isFinite(seconds)||distance<0||distance>200000||seconds<0||seconds>172800)throw unavailable();
        if(!properties.path("distance_units").asText("meters").equals("meters")||!properties.path("time_units").asText("seconds").equals("seconds"))throw unavailable();
        List<JsonNode> lines=new ArrayList<>();
        if(geometry.path("type").asText().equals("MultiLineString"))geometry.path("coordinates").forEach(lines::add);
        else if(geometry.path("type").asText().equals("LineString"))lines.add(geometry.path("coordinates"));else throw unavailable();
        int count=0;JsonNode first=null,last=null;
        for(var line:lines){if(!line.isArray()||line.size()<2)throw unavailable();for(var point:line){
            if(++count>20000||!point.isArray()||point.size()!=2||!point.get(0).isNumber()||!point.get(1).isNumber()||!NearbyService.valid(point.get(1).asDouble(),point.get(0).asDouble()))throw unavailable();
            if(first==null)first=point;last=point;
        }}
        if(first==null||NearbyService.distance(origin.latitude(),origin.longitude(),first.get(1).asDouble(),first.get(0).asDouble())>1000
            ||NearbyService.distance(destination.latitude(),destination.longitude(),last.get(1).asDouble(),last.get(0).asDouble())>1000)throw unavailable();
        var route=new Route(id,poiId,radius,mode,origin,destination,distance,seconds,geometry.deepCopy(),"GEOAPIFY",now,NearbyService.CREDITS);
        if(cache.size()>=256)cache.remove(cache.keySet().iterator().next());cache.put(key,new Entry(now.plusSeconds(900),route));return route;
    }
    private static ApiException unavailable(){return new ApiException(502,"ROUTE_UNAVAILABLE","Chưa tìm được tuyến đường phù hợp. Không thay bằng đường thẳng.");}
}
