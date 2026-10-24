package vn.smartprop.report;
import jakarta.validation.Valid;
import org.springframework.http.*;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import vn.smartprop.common.PageResponse;
@RestController @RequestMapping("/api/v1")
public class ReportController {
    private final ReportService service;
    public ReportController(ReportService service) {this.service=service;}
    private Long actor(Jwt jwt) {return Long.valueOf(jwt.getSubject());}
    @PostMapping("/properties/{id}/reports") @ResponseStatus(HttpStatus.CREATED) public ReportDtos.View create(@AuthenticationPrincipal Jwt jwt,@PathVariable String id,@Valid @RequestBody ReportDtos.Create input) {return service.create(actor(jwt),id,input);}
    @GetMapping("/users/me/reports") public PageResponse<ReportDtos.View> mine(@AuthenticationPrincipal Jwt jwt,@RequestParam(defaultValue="0") int page,@RequestParam(defaultValue="20") int size,@RequestParam(required=false) String keyword,@RequestParam(required=false) Report.Status status,@RequestParam(required=false) String sort) {return keyword==null&&status==null&&sort==null?service.mine(actor(jwt),page,size):service.mine(actor(jwt),page,size,keyword,status,sort);}
    @GetMapping("/reports/{id}") public ReportDtos.View detail(@AuthenticationPrincipal Jwt jwt,@PathVariable String id) {return service.detail(actor(jwt),id);}
    @PostMapping(value="/reports/{id}/attachments",consumes=MediaType.MULTIPART_FORM_DATA_VALUE) @ResponseStatus(HttpStatus.CREATED)
    public ReportDtos.View attach(@AuthenticationPrincipal Jwt jwt,@PathVariable String id,@RequestPart("file") MultipartFile file) {return service.attach(actor(jwt),id,file);}
    @GetMapping("/reports/{id}/attachments/{attachmentId}/content") public ResponseEntity<byte[]> download(@AuthenticationPrincipal Jwt jwt,@PathVariable String id,@PathVariable String attachmentId) {return service.download(actor(jwt),id,attachmentId);}
    @GetMapping("/admin/reports") public PageResponse<ReportDtos.View> queue(@AuthenticationPrincipal Jwt jwt,@RequestParam(required=false) Report.Status status,@RequestParam(defaultValue="0") int page,@RequestParam(defaultValue="20") int size) {return service.queue(actor(jwt),status,page,size);}
    @PatchMapping("/admin/reports/{id}/status") public ReportDtos.View status(@AuthenticationPrincipal Jwt jwt,@PathVariable String id,@Valid @RequestBody ReportDtos.StatusPatch input) {return service.status(actor(jwt),id,input);}
}