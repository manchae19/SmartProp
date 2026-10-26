package vn.smartprop.notification;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;
import vn.smartprop.common.PageResponse;
@RestController
@RequestMapping("/api/v1/users/me/notifications")
public class NotificationController {
    private final NotificationService service;
    public NotificationController(NotificationService service){this.service=service;}
    private Long actor(Jwt jwt,HttpServletResponse response){response.setHeader("Cache-Control","private, no-store");return Long.valueOf(jwt.getSubject());}
    @GetMapping public PageResponse<NotificationDtos.Item> inbox(@AuthenticationPrincipal Jwt jwt,HttpServletResponse response,
        @RequestParam(defaultValue="false") boolean unread,@RequestParam(defaultValue="0") int page,@RequestParam(defaultValue="20") int size) {
        return service.inbox(actor(jwt,response),unread,page,size);
    }
    @GetMapping("/unread-count") public NotificationDtos.UnreadCount unreadCount(@AuthenticationPrincipal Jwt jwt,HttpServletResponse response){return service.unreadCount(actor(jwt,response));}
    @PatchMapping("/{id}/read") public NotificationDtos.Item read(@AuthenticationPrincipal Jwt jwt,HttpServletResponse response,@PathVariable String id){return service.read(actor(jwt,response),id);}
    @PostMapping("/read-all") public NotificationDtos.ReadAll readAll(@AuthenticationPrincipal Jwt jwt,HttpServletResponse response){return service.readAll(actor(jwt,response));}
}
