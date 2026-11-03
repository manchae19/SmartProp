package vn.smartprop.amenity;

import org.springframework.http.CacheControl;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.dao.DataAccessException;

@RestController
@RequestMapping("/api/v1/amenities/map")
public class AmenityMapController {
    private final AmenityMapService service;
    public AmenityMapController(AmenityMapService service) { this.service = service; }

    @GetMapping
    public ResponseEntity<AmenityMapService.MapEvidence> get(
        @RequestParam String district, @RequestParam(defaultValue="ALL") String category) {
        try {
            return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(service.find(district, category));
        } catch (ResponseStatusException e) {
            return ResponseEntity.status(e.getStatusCode()).cacheControl(CacheControl.noStore()).build();
        } catch (DataAccessException e) {
            // Optional enrichment may not be installed in another environment. Fail closed;
            // never substitute legacy/unverified coordinates or expose SQL diagnostics.
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).cacheControl(CacheControl.noStore()).build();
        }
    }
}
