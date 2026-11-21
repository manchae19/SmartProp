package vn.smartprop.modules.prepurchase;

import org.springframework.http.CacheControl;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import vn.smartprop.modules.property.PropertyDtos;
import vn.smartprop.modules.property.PropertySearch;

/**
 * Public pre-purchase checks for one listing: planning documents and flood records.
 *
 * <p>Anonymous access is intentional: this is the same public material the listing page
 * already shows. Private legal documents stay behind their own authenticated route.
 */
@RestController
@RequestMapping("/api/v1/properties")
public class PrePurchaseController {
    private final PropertySearch search;
    private final PrePurchaseService service;

    public PrePurchaseController(PropertySearch search, PrePurchaseService service) {
        this.search = search;
        this.service = service;
    }

    @GetMapping("/{id}/pre-purchase-checks")
    public ResponseEntity<PrePurchaseService.Checks> checks(@PathVariable String id) {
        PropertyDtos.View listing = search.detail(id);
        return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(service.forListing(listing));
    }
}
