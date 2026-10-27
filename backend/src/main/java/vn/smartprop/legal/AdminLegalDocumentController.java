package vn.smartprop.legal;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
@RestController @RequestMapping("/api/v1/admin/legal-documents")
public class AdminLegalDocumentController {
    public record Review(@NotBlank String status,@NotBlank @Size(max=4000) String reason,@Positive int expectedVersion) {}
    private final LegalDocumentService service;public AdminLegalDocumentController(LegalDocumentService service){this.service=service;}
    @PostMapping("/{id}/review") public LegalDocumentService.View review(@AuthenticationPrincipal Jwt j,@PathVariable String id,@Valid @RequestBody Review r){return service.review(Long.valueOf(j.getSubject()),id,r.status(),r.reason(),r.expectedVersion());}
}
