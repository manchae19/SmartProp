package vn.smartprop.modules.messaging;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import jakarta.servlet.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.http.HttpStatus;
import vn.smartprop.common.*;
import vn.smartprop.config.*;
@RestController @RequestMapping("/api/v1")
public class MessagingController {
    public record Create(@NotBlank String propertyId) {}
    public record Send(@NotBlank String clientMessageId,@NotBlank @Size(max=4000) String body){@Override public String toString(){return "Message[redacted]";}}
    public record Read(@Min(0) long cursor) {}
    private final MessagingService service;private final RequestLimits limits;
    public MessagingController(MessagingService service,RequestLimits limits){this.service=service;this.limits=limits;}
    private Long actor(Jwt j,HttpServletResponse res){res.setHeader("Cache-Control","private, no-store");return Long.valueOf(j.getSubject());}
    private void rate(Long actor,HttpServletRequest req){limits.check("chat-user:"+actor,30,60);limits.check("chat-ip:"+req.getRemoteAddr(),120,60);}
    @PostMapping("/conversations") @ResponseStatus(HttpStatus.CREATED) public MessagingService.Conversation create(@AuthenticationPrincipal Jwt j,HttpServletRequest req,HttpServletResponse res,@Valid @RequestBody Create r){Long a=actor(j,res);rate(a,req);return service.create(a,r.propertyId());}
    @GetMapping("/users/me/conversations") public PageResponse<MessagingService.Conversation> list(@AuthenticationPrincipal Jwt j,HttpServletResponse res,@RequestParam(defaultValue="0") int page,@RequestParam(defaultValue="20") int size){return service.list(actor(j,res),page,size);}
    @GetMapping("/conversations/{id}/messages") public MessagingService.Slice messages(@AuthenticationPrincipal Jwt j,HttpServletResponse res,@PathVariable String id,@RequestParam(defaultValue="0") long after,@RequestParam(defaultValue="50") int limit){return service.messages(actor(j,res),id,after,limit);}
    @PostMapping("/conversations/{id}/messages") @ResponseStatus(HttpStatus.CREATED) public MessagingService.Message send(@AuthenticationPrincipal Jwt j,HttpServletRequest req,HttpServletResponse res,@PathVariable String id,@Valid @RequestBody Send r){Long a=actor(j,res);rate(a,req);return service.send(a,id,r.clientMessageId(),r.body());}
    @PatchMapping("/conversations/{id}/read") @ResponseStatus(HttpStatus.NO_CONTENT) public void read(@AuthenticationPrincipal Jwt j,HttpServletResponse res,@PathVariable String id,@Valid @RequestBody Read r){service.read(actor(j,res),id,r.cursor());}
}
