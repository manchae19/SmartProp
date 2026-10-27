package vn.smartprop.admin;
import java.util.Map;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import vn.smartprop.common.PageResponse;
import vn.smartprop.user.User;
@RestController @RequestMapping("/api/v1/admin")
public class AdminController {
    private final AdminService service;
    public AdminController(AdminService service) {this.service=service;}
    private Long actor(Jwt jwt) {return Long.valueOf(jwt.getSubject());}
    @GetMapping("/users") public PageResponse<AdminService.UserView> users(@AuthenticationPrincipal Jwt jwt,@RequestParam(required=false) User.Status status,@RequestParam(required=false) User.Role role,@RequestParam(required=false) String keyword,@RequestParam(defaultValue="0") int page,@RequestParam(defaultValue="20") int size) {return service.users(actor(jwt),status,role,keyword,page,size);}
    @PatchMapping("/users/{id}/status") public AdminService.UserView status(@AuthenticationPrincipal Jwt jwt,@PathVariable Long id,@Valid @RequestBody AdminService.StatusPatch input) {return service.status(actor(jwt),id,input);}
    @GetMapping("/dashboard") public Map<String,Long> dashboard(@AuthenticationPrincipal Jwt jwt) {return service.dashboard(actor(jwt));}
    @GetMapping("/audit-logs") public PageResponse<AdminService.AuditView> audit(@AuthenticationPrincipal Jwt jwt,@RequestParam(required=false) String entityType,@RequestParam(required=false) Long actorId,@RequestParam(required=false) String action,@RequestParam(defaultValue="0") int page,@RequestParam(defaultValue="20") int size) {return service.audit(actor(jwt),entityType,actorId,action,page,size);}
}