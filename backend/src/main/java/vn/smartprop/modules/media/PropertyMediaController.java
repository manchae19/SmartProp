package vn.smartprop.modules.media;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.http.*;
import org.springframework.web.multipart.MultipartFile;
import vn.smartprop.modules.property.PropertyDtos;
@RestController @RequestMapping("/api/v1/properties/{propertyId}/images")
public class PropertyMediaController {
    private final PropertyMediaService service;
    @Autowired(required=false) private PropertyImageScanService scanService;
    @Autowired(required=false) private PropertyImageAnalysisService analysisService;
    public PropertyMediaController(PropertyMediaService service) {this.service=service;}
    private Long actor(Jwt jwt) {return Long.valueOf(jwt.getSubject());}
    @PostMapping(consumes=MediaType.MULTIPART_FORM_DATA_VALUE) @ResponseStatus(HttpStatus.CREATED)
    public PropertyDtos.Managed upload(@AuthenticationPrincipal Jwt jwt,@PathVariable String propertyId,@RequestParam int expectedVersion,@RequestPart("file") MultipartFile file) {
        PropertyDtos.Managed result=service.upload(actor(jwt),propertyId,expectedVersion,file);
        // Two independent, best-effort side effects. Neither may fail the upload:
        // the image is already committed, and a vision outage must not block posting.
        if(scanService!=null)try{scanService.schedule(propertyId);}catch(RuntimeException ignored){}
        if(analysisService!=null)try{analysisService.schedule(propertyId);}catch(RuntimeException ignored){}
        return result;
    }
    @PatchMapping("/{imageId}") public PropertyDtos.Managed patch(@AuthenticationPrincipal Jwt jwt,@PathVariable String propertyId,@PathVariable String imageId,@Valid @RequestBody PropertyMediaService.Patch patch) {return service.patch(actor(jwt),propertyId,imageId,patch);}
    @PutMapping("/order") public PropertyDtos.Managed order(@AuthenticationPrincipal Jwt jwt,@PathVariable String propertyId,@Valid @RequestBody PropertyMediaService.Order order) {return service.order(actor(jwt),propertyId,order);}
    @DeleteMapping("/{imageId}") public PropertyDtos.Managed remove(@AuthenticationPrincipal Jwt jwt,@PathVariable String propertyId,@PathVariable String imageId,@RequestParam int expectedVersion) {return service.remove(actor(jwt),propertyId,imageId,expectedVersion);}
    @GetMapping("/{imageId}/content") public ResponseEntity<byte[]> content(@AuthenticationPrincipal Jwt jwt,@PathVariable String propertyId,@PathVariable String imageId) {return service.download(jwt==null?null:actor(jwt),propertyId,imageId);}
}