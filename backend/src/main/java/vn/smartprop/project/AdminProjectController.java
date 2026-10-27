package vn.smartprop.project;
import com.fasterxml.jackson.databind.JsonNode;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.http.HttpStatus;
import vn.smartprop.common.PageResponse;
@RestController @RequestMapping("/api/v1/admin/projects")
public class AdminProjectController {
    private final ProjectService service;public AdminProjectController(ProjectService service){this.service=service;}
    private Long actor(Jwt j){return Long.valueOf(j.getSubject());}
    @GetMapping public PageResponse<ProjectService.Managed> list(@AuthenticationPrincipal Jwt j,@RequestParam(defaultValue="false") boolean archived,@RequestParam(defaultValue="0") int page,@RequestParam(defaultValue="20") int size){return service.adminList(actor(j),archived,page,size);}
    @GetMapping("/{id}") public ProjectService.Managed detail(@AuthenticationPrincipal Jwt j,@PathVariable String id){return service.adminDetail(actor(j),id);}
    @PostMapping @ResponseStatus(HttpStatus.CREATED) public ProjectService.Managed create(@AuthenticationPrincipal Jwt j,@RequestBody JsonNode body){return service.create(actor(j),body);}
    @PatchMapping("/{id}") public ProjectService.Managed patch(@AuthenticationPrincipal Jwt j,@PathVariable String id,@RequestParam int expectedVersion,@RequestBody JsonNode body){return service.patch(actor(j),id,expectedVersion,body);}
    @DeleteMapping("/{id}") @ResponseStatus(HttpStatus.NO_CONTENT) public void archive(@AuthenticationPrincipal Jwt j,@PathVariable String id,@RequestParam int expectedVersion){service.archive(actor(j),id,expectedVersion);}
}
