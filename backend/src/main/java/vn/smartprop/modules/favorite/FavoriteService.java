package vn.smartprop.modules.favorite;
import java.time.Instant;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.data.domain.Sort;
import vn.smartprop.common.*;
import vn.smartprop.config.*;
import vn.smartprop.modules.property.*;
import vn.smartprop.modules.user.*;
import vn.smartprop.modules.auth.AccountAccess;
@Service
public class FavoriteService {
    private final SavedPropertyRepository saved;private final PropertyRepository properties;private final PropertyService service;private final UserRepository users;private final AccountAccess access;
    public FavoriteService(SavedPropertyRepository saved,PropertyRepository properties,PropertyService service,UserRepository users,AccountAccess access) {this.saved=saved;this.properties=properties;this.service=service;this.users=users;this.access=access;}
    @Transactional public void put(Long actor,String id) {
        users.lockById(actor).orElseThrow(ApiInputs::missing);access.active(actor);var p=service.publicProperty(id);
        var key=new SavedPropertyId(actor,p.id);if(!saved.existsById(key)){var record=new SavedProperty();record.id=key;saved.saveAndFlush(record);}
    }
    @Transactional public void remove(Long actor,String id) {
        users.lockById(actor).orElseThrow(ApiInputs::missing);access.active(actor);var key=new SavedPropertyId(actor,ApiInputs.uuid(id));
        saved.findById(key).ifPresent(saved::delete);
    }
    @Transactional(readOnly=true) public PageResponse<PropertyDtos.View> list(Long actor,int page,int size) {
        access.active(actor);var result=properties.findVisibleSaved(actor,Instant.now(),Property.Status.PUBLISHED,ApiInputs.page(page,size,Sort.unsorted()));
        var grouped=service.imageMap(result.getContent());return PageResponse.of(result.map(p->PropertyService.view(p,grouped.getOrDefault(p.id,java.util.List.of()))));
    }

    @Transactional(readOnly=true)
    public PageResponse<PropertyDtos.View> list(Long actor,int page,int size,String keyword,Property.Type type,String sort) {
        access.active(actor);String term=vn.smartprop.modules.collection.CollectionFilters.keyword(keyword);
        String order=sort==null||sort.isBlank()?"newest":sort;
        if(!java.util.Set.of("newest","oldest","priceAsc","priceDesc","areaDesc").contains(order))throw ApiInputs.bad("sort không được hỗ trợ");
        Instant now=Instant.now();
        org.springframework.data.jpa.domain.Specification<Property> filter=(root,query,cb)->{
            var record=query.from(SavedProperty.class);
            java.util.List<jakarta.persistence.criteria.Predicate> terms=new java.util.ArrayList<>();
            terms.add(cb.equal(record.get("id").get("userId"),actor));terms.add(cb.equal(record.get("id").get("propertyId"),root.get("id")));
            terms.add(cb.equal(root.get("status"),Property.Status.PUBLISHED));terms.add(cb.isNull(root.get("deletedAt")));
            terms.add(cb.or(cb.isNull(root.get("expiresAt")),cb.greaterThan(root.get("expiresAt"),now)));
            terms.add(vn.smartprop.modules.collection.CollectionFilters.text(cb,term,root.get("title"),root.get("address"),root.get("district")));
            if(type!=null)terms.add(cb.equal(root.get("propertyType"),type));
            if(query.getResultType()!=Long.class && query.getResultType()!=long.class){
                var field=order.equals("newest")||order.equals("oldest")?record.get("savedAt"):root.get(order.equals("areaDesc")?"areaSqm":"price");
                query.orderBy(order.equals("oldest")||order.equals("priceAsc")?cb.asc(field):cb.desc(field),cb.desc(root.get("id")));
            }
            return cb.and(terms.toArray(jakarta.persistence.criteria.Predicate[]::new));
        };
        var result=properties.findAll(filter,ApiInputs.page(page,size,Sort.unsorted()));
        var grouped=service.imageMap(result.getContent());return PageResponse.of(result.map(item->PropertyService.view(item,grouped.getOrDefault(item.id,java.util.List.of()))));
    }
}