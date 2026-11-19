package vn.smartprop.modules.property;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;
import vn.smartprop.common.PageResponse;
import vn.smartprop.modules.media.PropertyImageScanService;
import vn.smartprop.modules.media.PropertyImageAnalysisService;
@RestController @RequestMapping("/api/v1")
public class PropertyController {
    private final PropertyService service;
    @Autowired(required=false) private PropertyImageScanService scanService;
    @Autowired(required=false) private PropertyImageAnalysisService analysisService;
    public PropertyController(PropertyService service) {this.service=service;}
    private Long actor(Jwt jwt) {return Long.valueOf(jwt.getSubject());}
    @PostMapping("/properties") @ResponseStatus(HttpStatus.CREATED)
    public PropertyDtos.Managed create(@AuthenticationPrincipal Jwt jwt,@Valid @RequestBody PropertyDtos.Write r) {return service.create(actor(jwt),r);}
    @PatchMapping("/properties/{id}") public PropertyDtos.Managed patch(@AuthenticationPrincipal Jwt jwt,@PathVariable String id,@RequestParam int expectedVersion,@Valid @RequestBody PropertyDtos.Write r) {return service.patch(actor(jwt),id,expectedVersion,r);}
    @PostMapping("/properties/{id}/submit") public PropertyDtos.Managed submit(@AuthenticationPrincipal Jwt jwt,@PathVariable String id,@Valid @RequestBody PropertyDtos.Version r) {
        PropertyDtos.Managed result=service.transition(actor(jwt),id,r.expectedVersion(),"submit");
        if(scanService!=null)try{scanService.schedule(result.property().id());}catch(RuntimeException ignored){}
        if(analysisService!=null)try{analysisService.schedule(result.property().id());}catch(RuntimeException ignored){}
        return result;
    }
    @PostMapping("/properties/{id}/close") public PropertyDtos.Managed close(@AuthenticationPrincipal Jwt jwt,@PathVariable String id,@Valid @RequestBody PropertyDtos.Version r) {return service.transition(actor(jwt),id,r.expectedVersion(),"close");}
    @DeleteMapping("/properties/{id}") @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@AuthenticationPrincipal Jwt jwt,@PathVariable String id,@RequestParam int expectedVersion) {service.transition(actor(jwt),id,expectedVersion,"delete");}
    @GetMapping("/users/me/properties") public PageResponse<PropertyDtos.Managed> mine(@AuthenticationPrincipal Jwt jwt,@RequestParam(defaultValue="0") int page,@RequestParam(defaultValue="20") int size,@RequestParam(required=false) String keyword,@RequestParam(required=false) Property.Status status,@RequestParam(required=false) Property.Type propertyType,@RequestParam(required=false) String sort) {return keyword==null&&status==null&&propertyType==null&&sort==null?service.mine(actor(jwt),page,size):service.mine(actor(jwt),page,size,keyword,status,propertyType,sort);}
    @GetMapping("/users/me/properties/{id}") public PropertyDtos.Managed ownDetail(@AuthenticationPrincipal Jwt jwt,@PathVariable String id) {return service.ownDetail(actor(jwt),id);}
}
