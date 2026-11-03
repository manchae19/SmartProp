package vn.smartprop.amenity;

import org.springframework.http.CacheControl;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import static vn.smartprop.amenity.AmenityDtos.*;

@RestController
@RequestMapping("/api/v1/amenities")
public class AmenityController {
    private final AmenityCatalogService catalog;

    public AmenityController(AmenityCatalogService catalog) {
        this.catalog = catalog;
    }

    @GetMapping("/summary")
    public ResponseEntity<CatalogSummary> getSummary() {
        return ResponseEntity.ok()
            .cacheControl(CacheControl.noStore())
            .body(catalog.getSummary());
    }

    @GetMapping("/areas")
    public ResponseEntity<List<AreaSummary>> listAreas(
        @RequestParam(required = false) String level,
        @RequestParam(required = false) String district
    ) {
        return ResponseEntity.ok()
            .cacheControl(CacheControl.noStore())
            .body(catalog.listAreas(level, district));
    }

    @GetMapping("/lookup")
    public ResponseEntity<AmenityProfile> lookup(
        @RequestParam(required = false) String district,
        @RequestParam(required = false) String ward,
        @RequestParam(required = false) String street
    ) {
        return catalog.lookup(district, ward, street)
            .map(p -> ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(p))
            .orElseGet(() -> ResponseEntity.notFound().build());
    }

    @GetMapping("/{areaId}")
    public ResponseEntity<AmenityProfile> getById(@PathVariable String areaId) {
        return catalog.getById(areaId)
            .map(p -> ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(p))
            .orElseGet(() -> ResponseEntity.notFound().build());
    }
}
