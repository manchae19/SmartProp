package vn.smartprop.modules.moderation;

import java.time.Instant;
import java.util.List;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.transaction.annotation.Transactional;
import jakarta.servlet.http.HttpServletResponse;
import vn.smartprop.modules.property.PropertyService;

@RestController @RequestMapping("/api/v1/users/me/properties")
public class OwnModerationController {
    public record Feedback(String action,String reason,String previousStatus,String newStatus,Instant createdAt) {}
    private final PropertyService properties;private final JdbcTemplate jdbc;
    public OwnModerationController(PropertyService properties,JdbcTemplate jdbc) {this.properties=properties;this.jdbc=jdbc;}
    @GetMapping("/{id}/moderation") @Transactional(readOnly=true)
    public List<Feedback> feedback(@AuthenticationPrincipal Jwt jwt,@PathVariable String id,HttpServletResponse response) {
        response.setHeader("Cache-Control","private, no-store");var p=properties.owned(Long.valueOf(jwt.getSubject()),id);
        return jdbc.query("SELECT action,reason,previous_status,new_status,created_at FROM moderation_actions WHERE property_id=? ORDER BY created_at DESC,id DESC LIMIT 10",
            (r,n)->new Feedback(r.getString("action"),r.getString("reason"),r.getString("previous_status"),r.getString("new_status"),r.getTimestamp("created_at").toInstant()),p.id);
    }
}
