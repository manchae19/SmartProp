package vn.smartprop.modules.media;
import org.springframework.web.bind.annotation.*;
import vn.smartprop.common.RequestLimits;
import vn.smartprop.modules.property.PropertyService;

@RestController
@RequestMapping("/api/v1/admin/properties")
public class CloudinaryPreviewController {
    private final PropertyService properties;
    private final CloudinaryAdminClient cloudinary;
    private final RequestLimits limits;
    private final CloudinarySyncService sync;
    public CloudinaryPreviewController(PropertyService properties,CloudinaryAdminClient cloudinary,RequestLimits limits,CloudinarySyncService sync){
        this.properties=properties;this.cloudinary=cloudinary;this.limits=limits;this.sync=sync;
    }
    public record Sync(@jakarta.validation.constraints.NotNull @jakarta.validation.constraints.Positive Integer expectedVersion) {}
    @PostMapping("/{id}/cloudinary-sync")
    public CloudinarySyncService.Result synchronize(@PathVariable String id,@org.springframework.security.core.annotation.AuthenticationPrincipal org.springframework.security.oauth2.jwt.Jwt jwt,@jakarta.validation.Valid @RequestBody Sync input){
        limits.check("cloudinary:sync:"+jwt.getSubject(),5,60);
        return sync.synchronize(id,Long.parseLong(jwt.getSubject()),input.expectedVersion());
    }
    @GetMapping("/{id}/cloudinary-preview")
    public CloudinaryAdminClient.Preview preview(@PathVariable String id){
        limits.check("cloudinary:preview",10,60);
        var property=properties.existing(id);
        return cloudinary.listForListing(property.getListingCode());
    }
}
