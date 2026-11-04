package vn.smartprop.modules.favorite;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.http.HttpStatus;
import vn.smartprop.common.PageResponse;
import vn.smartprop.modules.property.PropertyDtos;
@RestController @RequestMapping("/api/v1/users/me/saved-properties")
public class FavoriteController {
    private final FavoriteService service;
    public FavoriteController(FavoriteService service) {this.service=service;}
    @GetMapping public PageResponse<PropertyDtos.View> list(@AuthenticationPrincipal Jwt jwt,@RequestParam(defaultValue="0") int page,@RequestParam(defaultValue="20") int size,@RequestParam(required=false) String keyword,@RequestParam(required=false) vn.smartprop.modules.property.Property.Type propertyType,@RequestParam(required=false) String sort) {Long actor=Long.valueOf(jwt.getSubject());return keyword==null&&propertyType==null&&sort==null?service.list(actor,page,size):service.list(actor,page,size,keyword,propertyType,sort);}
    @PutMapping("/{id}") @ResponseStatus(HttpStatus.NO_CONTENT) public void put(@AuthenticationPrincipal Jwt jwt,@PathVariable String id) {service.put(Long.valueOf(jwt.getSubject()),id);}
    @DeleteMapping("/{id}") @ResponseStatus(HttpStatus.NO_CONTENT) public void remove(@AuthenticationPrincipal Jwt jwt,@PathVariable String id) {service.remove(Long.valueOf(jwt.getSubject()),id);}
}