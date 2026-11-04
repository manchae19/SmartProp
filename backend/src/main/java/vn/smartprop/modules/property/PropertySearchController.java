package vn.smartprop.modules.property;
import java.math.BigDecimal;
import org.springframework.web.bind.annotation.*;
import vn.smartprop.common.*;
import vn.smartprop.config.*;
@RestController @RequestMapping("/api/v1/properties")
public class PropertySearchController {
    private final PropertySearch service;
    public PropertySearchController(PropertySearch service) {this.service=service;}
    @GetMapping({"","/map"}) public PageResponse<PropertyDtos.View> search(
        @RequestParam(required=false) String keyword,@RequestParam(required=false) Property.Type propertyType,@RequestParam(required=false) Property.Transaction transactionType,
        @RequestParam(required=false) String city,@RequestParam(required=false) String district,@RequestParam(required=false) String ward,
        @RequestParam(required=false) BigDecimal minPrice,@RequestParam(required=false) BigDecimal maxPrice,
        @RequestParam(required=false) BigDecimal minArea,@RequestParam(required=false) BigDecimal maxArea,
        @RequestParam(required=false) Short bedrooms,@RequestParam(required=false) String bbox,
        @RequestParam(defaultValue="0") int page,@RequestParam(defaultValue="20") int size,@RequestParam(defaultValue="newest") String sort) {
        return service.search(new PropertySearch.Filters(keyword,propertyType,transactionType,city,district,ward,minPrice,maxPrice,minArea,maxArea,bedrooms,bbox),page,size,sort);
    }
    @GetMapping("/{id}") public PropertyDtos.View detail(@PathVariable String id) {return service.detail(id);}
}