package vn.smartprop.modules.auth;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import jakarta.servlet.http.*;
import java.util.Map;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.http.HttpStatus;
import vn.smartprop.common.RequestLimits;
@RestController @RequestMapping("/api/v1/auth")
public class AccountEmailController {
    public record Email(@NotBlank @jakarta.validation.constraints.Email @Size(max=254) String email){@Override public String toString(){return "Email[redacted]";}}
    public record Verify(@NotBlank @Size(max=100) String token){@Override public String toString(){return "Verify[redacted]";}}
    public record Reset(@NotBlank @Size(max=100) String token,@NotBlank @Size(min=8,max=72) String newPassword){@Override public String toString(){return "Reset[redacted]";}}
    private final AccountEmailService service;private final RequestLimits limits;
    public AccountEmailController(AccountEmailService service,RequestLimits limits){this.service=service;this.limits=limits;}
    private void rate(HttpServletRequest req,HttpServletResponse res,boolean issuance){res.setHeader("Cache-Control","no-store");limits.check("mail:"+(issuance?"issue:":"consume:")+req.getRemoteAddr(),issuance?5:20,900);}
    @PostMapping("/password/forgot") @ResponseStatus(HttpStatus.ACCEPTED) public Map<String,String> forgot(@Valid @RequestBody Email body,HttpServletRequest req,HttpServletResponse res){rate(req,res,true);service.forgot(body.email());return Map.of("message","If eligible, an email will be queued.");}
    @PostMapping("/email-verification/request") @ResponseStatus(HttpStatus.ACCEPTED) public Map<String,String> request(@AuthenticationPrincipal Jwt j,HttpServletRequest req,HttpServletResponse res){rate(req,res,true);service.request(Long.valueOf(j.getSubject()));return Map.of("message","If eligible, an email will be queued.");}
    @PostMapping("/email-verification/confirm") @ResponseStatus(HttpStatus.NO_CONTENT) public void confirm(@Valid @RequestBody Verify body,HttpServletRequest req,HttpServletResponse res){rate(req,res,false);service.consume(body.token(),true,null);}
    @PostMapping("/password/reset") @ResponseStatus(HttpStatus.NO_CONTENT) public void reset(@Valid @RequestBody Reset body,HttpServletRequest req,HttpServletResponse res){rate(req,res,false);service.consume(body.token(),false,body.newPassword());}
}
