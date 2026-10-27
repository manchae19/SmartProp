package vn.smartprop.poi;
import java.util.List;
import org.springframework.web.bind.annotation.*;
@RestController
public class PoiController {
    private final PoiService service;
    public PoiController(PoiService service) {this.service=service;}
    @GetMapping("/api/v1/properties/{id}/points-of-interest") public List<PoiService.View> nearby(@PathVariable String id,@RequestParam(defaultValue="1000") double radiusMeters,@RequestParam(defaultValue="20") int limit,@RequestParam(required=false) String category) {return service.nearby(id,radiusMeters,limit,category);}
}