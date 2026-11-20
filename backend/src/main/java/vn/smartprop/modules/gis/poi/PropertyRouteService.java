package vn.smartprop.modules.gis.poi;
import com.fasterxml.jackson.databind.JsonNode;
import java.time.*;
import java.util.*;
import org.springframework.stereotype.Service;
import vn.smartprop.common.ApiException;
import static vn.smartprop.modules.gis.poi.NearbyDtos.*;

/**
 * Routes from a public listing to either a POI returned by its nearby lookup or a
 * destination the user confirmed (their workplace). The origin always comes from the
 * listing's own verified location, never from the browser.
 */
@Service
public class PropertyRouteService {
    public record Route(String propertyId,String poiId,int radiusMeters,String mode,Location origin,Place destination,
        double distanceMeters,double durationSeconds,JsonNode geometry,String provider,Instant fetchedAt,List<Attribution> attribution){}
    /** Route to a caller-confirmed point. {@code label} is echoed back, never stored. */
    public record Commute(String propertyId,String destinationLabel,double destinationLatitude,double destinationLongitude,
        String mode,Location origin,double distanceMeters,double durationSeconds,JsonNode geometry,String provider,
        Instant fetchedAt,List<Attribution> attribution){}
    /** One commute estimate in a ranked batch; null values mean the vendor had no route. */
    public record CommuteCell(String propertyId,Double distanceMeters,Double durationSeconds,String status){}
    public record CommuteMatrix(String mode,String provider,String destinationLabel,List<CommuteCell> cells,Instant fetchedAt){}
    private record Entry(Instant until,Route route){}
    private record CommuteEntry(Instant until,Commute commute){}
    private record MatrixEntry(Instant until,CommuteMatrix matrix){}
    private final NearbyService nearby;private final GeoapifyPlacesClient provider;
    private final CommuteRoutingService routing;
    private final Map<String,Entry> cache=new LinkedHashMap<>();
    private final Map<String,CommuteEntry> commuteCache=new LinkedHashMap<>();
    private final Map<String,MatrixEntry> matrixCache=new LinkedHashMap<>();
    private final java.util.concurrent.locks.ReentrantLock matrixLock=new java.util.concurrent.locks.ReentrantLock();
    public PropertyRouteService(NearbyService nearby,GeoapifyPlacesClient provider,CommuteRoutingService routing){
        this.nearby=nearby;this.provider=provider;this.routing=routing;
    }
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
        var geometry=provider.route(origin.latitude(),origin.longitude(),destination.latitude(),destination.longitude(),mode);
        var measured=measure(geometry,origin.latitude(),origin.longitude(),destination.latitude(),destination.longitude());
        var route=new Route(id,poiId,radius,mode,origin,destination,measured.distance,measured.seconds,measured.geometry,"GEOAPIFY",now,NearbyService.CREDITS);
        if(cache.size()>=256)cache.remove(cache.keySet().iterator().next());cache.put(key,new Entry(now.plusSeconds(900),route));return route;
    }
    /**
     * Travel time from the listing to a point the user confirmed, using whichever
     * routing vendor is configured. The destination must be a finite coordinate inside
     * Vietnam's bounding box; anything else is rejected rather than silently snapped.
     */
    public synchronized Commute commute(String id,double latitude,double longitude,String label,String mode){
        if(!Set.of("walk","drive").contains(mode))throw NearbyService.bad("Phương tiện không hợp lệ.");
        if(!NearbyService.valid(latitude,longitude))throw NearbyService.bad("Điểm đến không hợp lệ.");
        if(latitude<8.0||latitude>23.5||longitude<102.0||longitude>110.0)
            throw new ApiException(422,"COMMUTE_DESTINATION_OUT_OF_AREA","Điểm đến nằm ngoài khu vực SmartProp hỗ trợ.");
        String safeLabel=label==null?"":label.strip();
        if(safeLabel.length()>200)throw NearbyService.bad("Tên điểm đến quá dài.");
        var origin=nearby.advisorOrigin(id);
        if(origin==null)
            throw new ApiException(422,"ROUTE_LOCATION_UNAVAILABLE","Chưa có ghim phù hợp để tính thời gian đi làm.");
        String vendor=routing.provider();
        String key=id+":"+origin.latitude()+":"+origin.longitude()+":"+origin.accuracy()+":"+latitude+":"+longitude+":"+mode+":"+vendor;
        Instant now=Instant.now();commuteCache.values().removeIf(e->!e.until().isAfter(now));var hit=commuteCache.get(key);if(hit!=null)return hit.commute();
        var measured=routing.directions(origin.latitude(),origin.longitude(),latitude,longitude,mode);
        var commute=new Commute(id,safeLabel,latitude,longitude,mode,origin,measured.distanceMeters(),
            measured.durationSeconds(),measured.geometry(),measured.provider(),now,NearbyService.CREDITS);
        if(commuteCache.size()>=256)commuteCache.remove(commuteCache.keySet().iterator().next());
        commuteCache.put(key,new CommuteEntry(now.plusSeconds(900),commute));return commute;
    }
    /**
     * One call for every candidate distance to the same destination. This is what a
     * ranked list needs; a per-listing loop would spend the vendor budget N times.
     */
    public CommuteMatrix commuteMatrix(List<String> propertyIds,double latitude,double longitude,String label,String mode){
        // The budget starts when the request arrives, before the lock is even attempted:
        // time spent queueing behind a concurrent batch is time the caller also waits.
        long deadline=System.nanoTime()+java.util.concurrent.TimeUnit.SECONDS.toNanos(
            CommuteRoutingService.GEOAPIFY_MATRIX_BUDGET_SECONDS);
        // A plain synchronized block cannot be abandoned, so the lock is taken with the
        // remaining budget as its timeout. If it cannot be acquired in time the caller is
        // told the batch was not measured instead of waiting past its own window.
        boolean locked;
        try{
            locked=matrixLock.tryLock(Math.max(1,deadline-System.nanoTime()),java.util.concurrent.TimeUnit.NANOSECONDS);
        }catch(InterruptedException interrupted){
            Thread.currentThread().interrupt();
            throw new ApiException(503,"ROUTE_INTERRUPTED","Yêu cầu tính tuyến đã bị gián đoạn.");
        }
        if(!locked)return unmeasuredMatrix(propertyIds,label,mode);
        try{
            return commuteMatrixLocked(propertyIds,latitude,longitude,label,mode,deadline);
        }finally{matrixLock.unlock();}
    }

    /** Every listing reported as not measured, because the batch never got to run. */
    private CommuteMatrix unmeasuredMatrix(List<String> propertyIds,String label,String mode){
        List<CommuteCell> cells=new ArrayList<>();
        for(String propertyId:propertyIds)cells.add(new CommuteCell(propertyId,null,null,"NOT_MEASURED"));
        return new CommuteMatrix(mode,routing.provider(),label==null?"":label.strip(),List.copyOf(cells),Instant.now());
    }

    private CommuteMatrix commuteMatrixLocked(List<String> propertyIds,double latitude,double longitude,
                                              String label,String mode,long deadline){
        if(propertyIds==null||propertyIds.isEmpty())
            throw NearbyService.bad("Cần ít nhất một tin để tính tuyến.");
        if(propertyIds.size()>6)
            throw new ApiException(400,"COMMUTE_MATRIX_TOO_LARGE","Tối đa 6 tin cho một lần xếp hạng.");
        if(!Set.of("walk","drive").contains(mode))throw NearbyService.bad("Phương tiện không hợp lệ.");
        if(!NearbyService.valid(latitude,longitude))throw NearbyService.bad("Điểm đến không hợp lệ.");
        if(latitude<8.0||latitude>23.5||longitude<102.0||longitude>110.0)
            throw new ApiException(422,"COMMUTE_DESTINATION_OUT_OF_AREA","Điểm đến nằm ngoài khu vực SmartProp hỗ trợ.");
        String safeLabel=label==null?"":label.strip();
        if(safeLabel.length()>200)throw NearbyService.bad("Tên điểm đến quá dài.");
        String vendor=routing.provider();
        String key=String.join(",",propertyIds)+":"+latitude+":"+longitude+":"+mode+":"+vendor;
        Instant now=Instant.now();matrixCache.values().removeIf(e->!e.until().isAfter(now));var hit=matrixCache.get(key);if(hit!=null)return hit.matrix();
        List<CommuteRoutingService.Origin> origins=new ArrayList<>();
        for(String propertyId:propertyIds){
            var result=originFor(propertyId);
            if(result==null){
                origins.add(new CommuteRoutingService.Origin(propertyId,Double.NaN,Double.NaN));
                continue;
            }
            origins.add(new CommuteRoutingService.Origin(propertyId,result.latitude(),result.longitude()));
        }
        // A listing without a verified pin cannot be routed; mark it instead of guessing.
        List<CommuteCell> cells=new ArrayList<>();
        List<CommuteRoutingService.Origin> routable=new ArrayList<>();
        for(var origin:origins){
            if(Double.isFinite(origin.latitude())&&Double.isFinite(origin.longitude())) routable.add(origin);
            else cells.add(new CommuteCell(origin.propertyId(),null,null,"LOCATION_UNVERIFIED"));
        }
        if(!routable.isEmpty()){
            for(var cell:routing.matrix(routable,latitude,longitude,mode,deadline))
                cells.add(new CommuteCell(cell.propertyId(),cell.distanceMeters(),cell.durationSeconds(),
                    !cell.measured()?"NOT_MEASURED":cell.durationSeconds()==null?"NO_ROUTE":"OK"));
        }
        // Restore the caller's order so index i always means the i-th requested listing.
        Map<String,CommuteCell> byId=new LinkedHashMap<>();
        for(var cell:cells) byId.putIfAbsent(cell.propertyId(),cell);
        List<CommuteCell> ordered=new ArrayList<>();
        for(String propertyId:propertyIds)
            ordered.add(byId.getOrDefault(propertyId,new CommuteCell(propertyId,null,null,"NO_ROUTE")));
        var matrix=new CommuteMatrix(mode,vendor,safeLabel,List.copyOf(ordered),now);
        // A batch that ran out of time left some listings unmeasured. Caching that would
        // pin the gap for fifteen minutes, so only a complete batch is cached; the next
        // call retries the listings that were never reached.
        boolean complete=ordered.stream().noneMatch(cell->"NOT_MEASURED".equals(cell.status()));
        if(complete){
            if(matrixCache.size()>=128)matrixCache.remove(matrixCache.keySet().iterator().next());
            matrixCache.put(key,new MatrixEntry(now.plusSeconds(900),matrix));
        }
        return matrix;
    }
    /** Verified origin for a listing, or null when it is not public or has no usable pin. */
    private Location originFor(String propertyId){
        try{
            return nearby.advisorOrigin(propertyId);
        }catch(RuntimeException notPublic){
            // A draft or deleted listing is simply not routable; it must not abort the batch.
            return null;
        }
    }
    private record Measured(double distance,double seconds,JsonNode geometry){}
    /** Shared validation: the returned line must start and end near the requested points. */
    private static Measured measure(JsonNode body,double fromLat,double fromLon,double toLat,double toLon){
        JsonNode feature=body.path("features").path(0);
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
        if(first==null||NearbyService.distance(fromLat,fromLon,first.get(1).asDouble(),first.get(0).asDouble())>1000
            ||NearbyService.distance(toLat,toLon,last.get(1).asDouble(),last.get(0).asDouble())>1000)throw unavailable();
        return new Measured(distance,seconds,geometry.deepCopy());
    }
    private static ApiException unavailable(){return new ApiException(502,"ROUTE_UNAVAILABLE","Chưa tìm được tuyến đường phù hợp. Không thay bằng đường thẳng.");}
}
