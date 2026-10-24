package vn.smartprop.legal;
import com.fasterxml.jackson.databind.JsonNode;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.http.*;
import vn.smartprop.common.PageResponse;
@RestController @RequestMapping("/api/v1/properties/{property}/legal-documents")
public class LegalDocumentController {
    private final LegalDocumentService service;public LegalDocumentController(LegalDocumentService service){this.service=service;}
    private Long actor(Jwt j){return Long.valueOf(j.getSubject());}
    @GetMapping public PageResponse<LegalDocumentService.View> list(@AuthenticationPrincipal Jwt j,@PathVariable String property,@RequestParam(defaultValue="0") int page,@RequestParam(defaultValue="20") int size){return service.list(actor(j),property,page,size);}
    @GetMapping("/{id}") public LegalDocumentService.View detail(@AuthenticationPrincipal Jwt j,@PathVariable String property,@PathVariable String id){return service.detail(actor(j),property,id);}
    @PostMapping(consumes="multipart/form-data") @ResponseStatus(HttpStatus.CREATED) public LegalDocumentService.View upload(@AuthenticationPrincipal Jwt j,@PathVariable String property,@RequestPart("metadata") JsonNode metadata,@RequestPart("file") MultipartFile file){return service.upload(actor(j),property,metadata,file);}
    @PatchMapping("/{id}") public LegalDocumentService.View patch(@AuthenticationPrincipal Jwt j,@PathVariable String property,@PathVariable String id,@RequestParam int expectedVersion,@RequestBody JsonNode metadata){return service.patch(actor(j),property,id,expectedVersion,metadata);}
    @DeleteMapping("/{id}") @ResponseStatus(HttpStatus.NO_CONTENT) public void remove(@AuthenticationPrincipal Jwt j,@PathVariable String property,@PathVariable String id,@RequestParam int expectedVersion){service.remove(actor(j),property,id,expectedVersion);}
    @GetMapping("/{id}/content") public ResponseEntity<byte[]> content(@AuthenticationPrincipal Jwt j,@PathVariable String property,@PathVariable String id){return service.content(actor(j),property,id);}
}
