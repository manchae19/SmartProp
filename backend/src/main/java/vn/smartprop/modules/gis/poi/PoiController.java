package vn.smartprop.modules.gis.poi;
import java.util.List;
import org.springframework.web.bind.annotation.*;
@RestController
public class PoiController {
    private final PropertyRouteService routes;
    private final PoiService service;
    private final NearbyService explorer;
    private final vn.smartprop.common.RequestLimits limits;
    public PoiController(PoiService service,NearbyService explorer,vn.smartprop.common.RequestLimits limits,PropertyRouteService routes) {this.routes=routes;this.service=service;this.explorer=explorer;this.limits=limits;}
    @GetMapping("/api/v1/properties/{id}/nearby") public NearbyDtos.Result explore(@PathVariable String id,@RequestParam(defaultValue="1000") int radius,@RequestParam(defaultValue="education,health,shopping,park") String categories,@RequestParam(defaultValue="false") boolean verifiedOrigin,@RequestParam(defaultValue="false") boolean allowEstimatedOrigin,jakarta.servlet.http.HttpServletRequest request) {limits.check("nearby:ip:"+request.getRemoteAddr(),30,60);return verifiedOrigin?explorer.forAdvisor(id,radius,categories,allowEstimatedOrigin):explorer.nearby(id,radius,categories,allowEstimatedOrigin); }
    @GetMapping("/api/v1/properties/{id}/route") public PropertyRouteService.Route route(@PathVariable String id,@RequestParam String poiId,@RequestParam(defaultValue="1000") int radius,@RequestParam(defaultValue="education,health,shopping,park") String categories,@RequestParam(defaultValue="walk") String mode,jakarta.servlet.http.HttpServletRequest request){limits.check("route:ip:"+request.getRemoteAddr(),15,60);return routes.route(id,poiId,radius,categories,mode);}
    /**
     * Commute time from a public listing to a point the user confirmed. The destination
     * is supplied per request and never stored; only the listing id is looked up server-side.
     */
    @GetMapping("/api/v1/properties/{id}/commute") public PropertyRouteService.Commute commute(@PathVariable String id,@RequestParam double latitude,@RequestParam double longitude,@RequestParam(required=false) String label,@RequestParam(defaultValue="drive") String mode,jakarta.servlet.http.HttpServletRequest request){limits.check("commute:ip:"+request.getRemoteAddr(),15,60);return routes.commute(id,latitude,longitude,label,mode);}
    public record MatrixRequest(List<String> propertyIds,double latitude,double longitude,String label,String mode) {}
    /**
     * Travel time from several listings to the same confirmed destination in one vendor
     * call, so ranking a shortlist does not spend one request per candidate.
     */
    @PostMapping("/api/v1/advisor/commute-matrix") public PropertyRouteService.CommuteMatrix commuteMatrix(@RequestBody MatrixRequest body,jakarta.servlet.http.HttpServletRequest request){limits.check("commute-matrix:ip:"+request.getRemoteAddr(),10,60);return routes.commuteMatrix(body.propertyIds(),body.latitude(),body.longitude(),body.label(),body.mode()==null?"drive":body.mode());}
    @GetMapping("/api/v1/properties/{id}/points-of-interest") public List<PoiService.View> nearby(@PathVariable String id,@RequestParam(defaultValue="1000") double radiusMeters,@RequestParam(defaultValue="20") int limit,@RequestParam(required=false) String category) {return service.nearby(id,radiusMeters,limit,category);}
}
