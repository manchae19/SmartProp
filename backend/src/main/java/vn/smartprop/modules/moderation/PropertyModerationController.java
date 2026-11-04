package vn.smartprop.modules.moderation;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import vn.smartprop.modules.property.*;
import vn.smartprop.common.PageResponse;
@RestController @RequestMapping("/api/v1/admin/properties")
public class PropertyModerationController {
    private final PropertyModerationService service;
    public PropertyModerationController(PropertyModerationService service) {this.service=service;}
    @GetMapping public PageResponse<PropertyDtos.Managed> queue(@AuthenticationPrincipal Jwt jwt,@RequestParam(defaultValue="PENDING") Property.Status status,@RequestParam(defaultValue="0") int page,@RequestParam(defaultValue="20") int size) {return service.queue(Long.valueOf(jwt.getSubject()),status,page,size);}
    @GetMapping("/{id}") public PropertyDtos.Managed detail(@AuthenticationPrincipal Jwt jwt,@PathVariable String id) {return service.detail(Long.valueOf(jwt.getSubject()),id);}
    @PostMapping("/{id}/moderation") public PropertyDtos.Managed moderate(@AuthenticationPrincipal Jwt jwt,@PathVariable String id,@Valid @RequestBody PropertyModerationService.Command command) {return service.moderate(Long.valueOf(jwt.getSubject()),id,command);}
}