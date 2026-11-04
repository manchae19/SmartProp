package vn.smartprop.modules.gis.poi;
import java.util.List;
import org.springframework.web.bind.annotation.*;
@RestController
public class PoiController {
    private final PoiService service;
    private final NearbyService explorer;
    private final vn.smartprop.common.RequestLimits limits;
    public PoiController(PoiService service,NearbyService explorer,vn.smartprop.common.RequestLimits limits) {this.service=service;this.explorer=explorer;this.limits=limits;}
    @GetMapping("/api/v1/properties/{id}/nearby") public NearbyDtos.Result explore(@PathVariable String id,@RequestParam(defaultValue="1000") int radius,@RequestParam(defaultValue="education,health,shopping,park") String categories,jakarta.servlet.http.HttpServletRequest request) {limits.check("nearby:ip:"+request.getRemoteAddr(),30,60);return explorer.nearby(id,radius,categories); }
    @GetMapping("/api/v1/properties/{id}/points-of-interest") public List<PoiService.View> nearby(@PathVariable String id,@RequestParam(defaultValue="1000") double radiusMeters,@RequestParam(defaultValue="20") int limit,@RequestParam(required=false) String category) {return service.nearby(id,radiusMeters,limit,category);}
}