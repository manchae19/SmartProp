package vn.smartprop.modules.property;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.*;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.data.domain.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.smartprop.common.*;
import vn.smartprop.config.*;
import vn.smartprop.modules.media.PropertyImageRepository;
@Service
public class PropertySearch {
    public record Filters(String keyword,String address,Property.Type propertyType,Property.Transaction transactionType,String city,String district,String ward,
        BigDecimal minPrice,BigDecimal maxPrice,BigDecimal minArea,BigDecimal maxArea,Short bedrooms,String bbox) {}
    public record Bounds(double west,double south,double east,double north) {}
    private final PropertyRepository properties;private final PropertyService service;private final PropertyImageRepository images;
    public PropertySearch(PropertyRepository properties,PropertyService service,PropertyImageRepository images) {this.properties=properties;this.service=service;this.images=images;}
    public static Bounds bounds(String bbox) {
        if(bbox==null || bbox.isBlank()) return null;
        try {
            String[] parts=bbox.split(",",-1);if(parts.length!=4)throw new IllegalArgumentException();
            double w=Double.parseDouble(parts[0]),s=Double.parseDouble(parts[1]),e=Double.parseDouble(parts[2]),n=Double.parseDouble(parts[3]);
            if(!Double.isFinite(w)||!Double.isFinite(s)||!Double.isFinite(e)||!Double.isFinite(n)||w<=-180||e>180||s< -90||n>90||w>=e||s>=n)throw new IllegalArgumentException();
            return new Bounds(w,s,e,n);
        } catch(IllegalArgumentException ex) {throw ApiInputs.bad("bbox phải là west,south,east,north hợp lệ; không đi qua kinh tuyến 180");}
    }
    public static Sort sort(String value) {
        Sort primary=switch(value) {case "newest"->Sort.by(Sort.Order.desc("createdAt"));case "priceAsc"->Sort.by("price");case "priceDesc"->Sort.by(Sort.Order.desc("price"));case "areaAsc"->Sort.by("areaSqm");case "areaDesc"->Sort.by(Sort.Order.desc("areaSqm"));default->throw ApiInputs.bad("sort không được hỗ trợ");};
        return primary.and(Sort.by(Sort.Order.desc("id")));
    }
    public static Specification<Property> specification(Filters f,Instant now) {
        for(String text:Arrays.asList(f.keyword(),f.city(),f.district(),f.ward()))if(text!=null && text.length()>100)throw ApiInputs.bad("Bộ lọc chuỗi tối đa 100 ký tự");
        for(BigDecimal value:Arrays.asList(f.minPrice(),f.maxPrice(),f.minArea(),f.maxArea()))if(value!=null && value.signum()<0)throw ApiInputs.bad("Bộ lọc giá/diện tích phải không âm");
        if((f.minPrice()!=null&&f.maxPrice()!=null&&f.minPrice().compareTo(f.maxPrice())>0)||(f.minArea()!=null&&f.maxArea()!=null&&f.minArea().compareTo(f.maxArea())>0)||f.bedrooms()!=null&&f.bedrooms()<0)throw ApiInputs.bad("Khoảng lọc không hợp lệ");
        Bounds box=bounds(f.bbox());
        return (root,query,cb)->{
            List<jakarta.persistence.criteria.Predicate> predicates=new ArrayList<>();
            predicates.add(cb.equal(root.get("status"),Property.Status.PUBLISHED));predicates.add(cb.isNull(root.get("deletedAt")));
            predicates.add(cb.or(cb.isNull(root.get("expiresAt")),cb.greaterThan(root.get("expiresAt"),now)));
            if(f.keyword()!=null&&!f.keyword().isBlank()) {String term=ApiInputs.like(f.keyword().strip().toLowerCase(Locale.ROOT));predicates.add(cb.or(cb.like(cb.lower(root.get("title")),term,'\\'),cb.like(cb.lower(root.get("description")),term,'\\')));}
            // An address lookup must match the address column itself, not prose that happens to mention the street.
            if(f.address()!=null&&!f.address().isBlank()) {String term=ApiInputs.like(f.address().strip().toLowerCase(Locale.ROOT));predicates.add(cb.like(cb.lower(root.get("address")),term,'\\'));}
            if(f.propertyType()!=null)predicates.add(cb.equal(root.get("propertyType"),f.propertyType()));if(f.transactionType()!=null)predicates.add(cb.equal(root.get("transactionType"),f.transactionType()));
            if(f.city()!=null&&!f.city().isBlank())predicates.add(cb.equal(root.get("city"),f.city()));if(f.district()!=null&&!f.district().isBlank())predicates.add(cb.equal(root.get("district"),f.district()));if(f.ward()!=null&&!f.ward().isBlank())predicates.add(cb.equal(root.get("ward"),f.ward()));
            if(f.minPrice()!=null)predicates.add(cb.greaterThanOrEqualTo(root.get("price"),f.minPrice()));if(f.maxPrice()!=null)predicates.add(cb.lessThanOrEqualTo(root.get("price"),f.maxPrice()));
            if(f.minArea()!=null)predicates.add(cb.greaterThanOrEqualTo(root.get("areaSqm"),f.minArea()));if(f.maxArea()!=null)predicates.add(cb.lessThanOrEqualTo(root.get("areaSqm"),f.maxArea()));if(f.bedrooms()!=null)predicates.add(cb.greaterThanOrEqualTo(root.get("bedrooms"),f.bedrooms()));
            if(box!=null) {predicates.add(cb.between(cb.function("ST_Longitude",Double.class,root.get("location")),box.west(),box.east()));predicates.add(cb.between(cb.function("ST_Latitude",Double.class,root.get("location")),box.south(),box.north()));}
            return cb.and(predicates.toArray(jakarta.persistence.criteria.Predicate[]::new));
        };
    }
    @Transactional(readOnly=true) public PageResponse<PropertyDtos.View> search(Filters filters,int page,int size,String sort) {
        Page<Property> result=properties.findAll(specification(filters,Instant.now()),ApiInputs.page(page,size,sort(sort)));
        var grouped=service.imageMap(result.getContent());return PageResponse.of(result.map(p->PropertyService.view(p,grouped.getOrDefault(p.id,List.of()))));
    }
    @Transactional(readOnly=true) public PropertyDtos.View detail(String id) {Property p=service.publicProperty(id);return PropertyService.view(p,images.findByPropertyIdAndDeletedAtIsNullOrderBySortOrderAscIdAsc(p.id));}
}