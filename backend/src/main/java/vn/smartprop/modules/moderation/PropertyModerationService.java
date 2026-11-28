package vn.smartprop.modules.moderation;
import java.time.Instant;
import java.util.*;
import jakarta.validation.constraints.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.data.jpa.domain.Specification;
import vn.smartprop.common.*;
import vn.smartprop.config.*;
import vn.smartprop.modules.auth.AccountAccess;
import vn.smartprop.modules.property.*;
import vn.smartprop.modules.media.PropertyImageRepository;
import vn.smartprop.modules.audit.DomainEvents;
@Service
public class PropertyModerationService {
    public enum Action { APPROVE, REJECT, HIDE, RESTORE }
    public record Command(@NotNull Action action,@NotNull @Positive Integer expectedVersion,@NotBlank @Size(max=4000) String reason) {}
    private final PropertyService service;private final PropertyRepository properties;private final PropertyImageRepository images;private final AccountAccess access;private final DomainEvents events;
    public PropertyModerationService(PropertyService service,PropertyRepository properties,PropertyImageRepository images,AccountAccess access,DomainEvents events) {this.service=service;this.properties=properties;this.images=images;this.access=access;this.events=events;}
    public static Property.Status target(Property.Status current,Action action) {
        return switch(action) {
            case APPROVE -> {if(current!=Property.Status.PENDING)throw ApiInputs.conflict("Chỉ duyệt tin PENDING");yield Property.Status.PUBLISHED;}
            case REJECT -> {if(current!=Property.Status.PENDING)throw ApiInputs.conflict("Chỉ từ chối tin PENDING");yield Property.Status.REJECTED;}
            case HIDE -> {if(current!=Property.Status.PUBLISHED)throw ApiInputs.conflict("Chỉ ẩn tin PUBLISHED");yield Property.Status.HIDDEN;}
            case RESTORE -> {if(current!=Property.Status.HIDDEN)throw ApiInputs.conflict("Chỉ khôi phục tin HIDDEN về hàng đợi duyệt");yield Property.Status.PENDING;}
        };
    }
    @Transactional public PropertyDtos.Managed moderate(Long actor,String id,Command command) {
        access.admin(actor);Property p=service.existing(id);Property.Status after=target(p.status,command.action());String before=p.status.name();
        if(after==Property.Status.PUBLISHED)access.publisherForUpdate(p.ownerId);
        service.reserve(p,command.expectedVersion());if(after==Property.Status.PUBLISHED && images.countByPropertyIdAndDeletedAtIsNull(p.id)<1)throw ApiInputs.bad("Tin phải có ảnh trước khi được duyệt");
        p.status=after;if(after==Property.Status.PUBLISHED){p.publishedAt=Instant.now();p.expiresAt=null;p.closedAt=null;}else if(after==Property.Status.PENDING)p.publishedAt=null;
        properties.saveAndFlush(p);events.moderation(actor,p.id,null,null,"PROPERTY_"+command.action().name(),command.reason().strip(),before,after.name(),p.ownerId);
        return PropertyService.managed(p,images.findByPropertyIdAndDeletedAtIsNullOrderBySortOrderAscIdAsc(p.id),service.coordinate(p.id));
    }
    @Transactional(readOnly=true) public PageResponse<PropertyDtos.Managed> queue(Long actor,Property.Status status,int page,int size) {
        access.admin(actor);Specification<Property> filter=(p,q,cb)->cb.and(cb.isNull(p.get("deletedAt")),cb.equal(p.get("status"),status));
        var result=properties.findAll(filter,ApiInputs.newest(page,size));var grouped=service.imageMap(result.getContent());return PageResponse.of(result.map(p->PropertyService.managed(p,grouped.getOrDefault(p.id,List.of()))));
    }
    @Transactional(readOnly=true) public PropertyDtos.Managed detail(Long actor,String id) {access.admin(actor);Property p=service.existing(id);return PropertyService.managed(p,images.findByPropertyIdAndDeletedAtIsNullOrderBySortOrderAscIdAsc(p.id),service.coordinate(p.id));}
}