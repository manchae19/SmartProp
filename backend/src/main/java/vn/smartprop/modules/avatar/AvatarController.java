package vn.smartprop.modules.avatar;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.http.*;
import vn.smartprop.common.RequestLimits;
@RestController @RequestMapping("/api/v1/users/me/avatar")
public class AvatarController {
    private final AvatarService service;private final RequestLimits limits;
    public AvatarController(AvatarService service,RequestLimits limits){this.service=service;this.limits=limits;}
    @GetMapping public AvatarService.View get(@AuthenticationPrincipal Jwt jwt){return service.get(Long.valueOf(jwt.getSubject()));}
    @PostMapping(consumes="multipart/form-data") public AvatarService.View upload(@AuthenticationPrincipal Jwt jwt,@RequestPart("file") MultipartFile input){Long actor=Long.valueOf(jwt.getSubject());limits.check("avatar:write:"+actor,10,60);return service.upload(actor,input);}
    @DeleteMapping @ResponseStatus(HttpStatus.NO_CONTENT) public void remove(@AuthenticationPrincipal Jwt jwt){Long actor=Long.valueOf(jwt.getSubject());limits.check("avatar:write:"+actor,10,60);service.remove(actor);}
    @GetMapping("/content") public ResponseEntity<byte[]> content(@AuthenticationPrincipal Jwt jwt){return service.content(Long.valueOf(jwt.getSubject()));}
}
