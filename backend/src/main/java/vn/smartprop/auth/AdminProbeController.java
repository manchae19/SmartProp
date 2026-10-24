package vn.smartprop.auth;
import java.util.Map;
import org.springframework.web.bind.annotation.*;
/** Authorization probe only; administration business features belong to later milestones. */
@RestController
class AdminProbeController {
    @GetMapping("/api/v1/admin/access") Map<String,String> access() { return Map.of("role","ADMIN"); }
}
