package vn.smartprop.modules.property;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import java.time.Instant;
import java.util.*;
import org.locationtech.jts.geom.*;
import org.springframework.data.domain.Page;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.smartprop.modules.auth.AccountAccess;
import vn.smartprop.common.*;
import vn.smartprop.config.*;
import vn.smartprop.modules.media.*;
import vn.smartprop.modules.project.ProjectRepository;
@Service
public class PropertyService {
    private final PropertyRepository properties;
    private final PropertyImageRepository images;
    private final ProjectRepository projects;
    private final AccountAccess access;
    @org.springframework.beans.factory.annotation.Autowired(required=false) private vn.smartprop.modules.project.ProjectManagementRepository projectLifecycle;
    public PropertyService(PropertyRepository properties,PropertyImageRepository images,ProjectRepository projects,AccountAccess access) {
        this.properties=properties;this.images=images;this.projects=projects;this.access=access;
    }
    public static boolean visible(Property p,Instant now) { return p.deletedAt==null && p.status==Property.Status.PUBLISHED && (p.expiresAt==null || p.expiresAt.isAfter(now)); }
    public Property existing(String id) { return properties.findByIdAndDeletedAtIsNull(ApiInputs.uuid(id)).orElseThrow(ApiInputs::missing); }
    public Property owned(Long actor,String id) {
        access.active(actor);Property p=existing(id);if(!Objects.equals(p.ownerId,actor)) throw ApiInputs.forbidden();return p;
    }
    public Property publicProperty(String id) { Property p=existing(id);if(!visible(p,Instant.now())) throw ApiInputs.missing();return p; }
    /** Call before changing a managed property; the conditional update holds the DB row lock until commit. */
    public void reserve(Property p,Integer version) {
        if(version==null || version<1) throw ApiInputs.bad("expectedVersion bắt buộc và phải lớn hơn 0");
        if(!Objects.equals(p.contentVersion,version) || version==Integer.MAX_VALUE || properties.reserveVersion(p.id,version)!=1)
            throw ApiInputs.conflict("Tin đã thay đổi; hãy tải lại trước khi lưu");
        p.contentVersion=version+1;
    }
    private void fill(Property p,PropertyDtos.Write r) {
        if(r.title()!=null) p.title=r.title().strip();if(r.description()!=null) p.description=r.description();
        if(r.propertyType()!=null) p.propertyType=r.propertyType();if(r.transactionType()!=null) p.transactionType=r.transactionType();
        if(r.price()!=null) p.price=r.price();if(r.currency()!=null) p.currency=r.currency();if(r.priceUnit()!=null) p.priceUnit=r.priceUnit();
        if(r.areaSqm()!=null) p.areaSqm=r.areaSqm();if(r.bedrooms()!=null) p.bedrooms=r.bedrooms();if(r.bathrooms()!=null) p.bathrooms=r.bathrooms();
        if(r.floor()!=null) p.floor=r.floor();if(r.block()!=null) p.block=r.block();if(r.direction()!=null) p.direction=r.direction();
        if(r.address()!=null) p.address=r.address();if(r.city()!=null) p.city=r.city().strip();if(r.district()!=null) p.district=r.district();if(r.ward()!=null) p.ward=r.ward();
        if(r.projectId()!=null) {
            String previous=p.projectId;
            p.projectId=r.projectId().isBlank()?null:ApiInputs.uuid(r.projectId());
            if(p.projectId!=null && projectLifecycle!=null)projectLifecycle.linkable(p.projectId,previous);
            if(p.projectId!=null && !projects.existsById(p.projectId)) throw ApiInputs.bad("projectId không tồn tại");
        }
        if(r.contactName()!=null) p.contactName=r.contactName();if(r.contactPhone()!=null) p.contactPhone=r.contactPhone();if(r.contactEmail()!=null) p.contactEmail=r.contactEmail();
        if(r.declaredAmenities()!=null) { var array=JsonNodeFactory.instance.arrayNode();r.declaredAmenities().stream().map(String::strip).distinct().forEach(array::add);p.declaredAmenities=array; }
        Double lat=r.latitude()!=null?r.latitude():p.location==null?null:p.location.getY();
        Double lon=r.longitude()!=null?r.longitude():p.location==null?null:p.location.getX();
        if(lat==null || lon==null || !Double.isFinite(lat) || !Double.isFinite(lon) || lat < -90 || lat>90 || lon<=-180 || lon>180)
            throw ApiInputs.bad("Tọa độ bắt buộc: latitude [-90,90], longitude (-180,180]");
        p.location=new GeometryFactory(new PrecisionModel(),4326).createPoint(new Coordinate(lon,lat));
        if(p.title==null || p.title.isBlank() || p.propertyType==null || p.transactionType==null || p.price==null || p.areaSqm==null || p.priceUnit==null)
            throw ApiInputs.bad("Thiếu title/propertyType/transactionType/price/priceUnit/areaSqm");
        if(p.price.signum()<0 || p.areaSqm.signum()<=0 || (p.transactionType==Property.Transaction.SALE && p.priceUnit!=Property.PriceUnit.TOTAL))
            throw ApiInputs.bad("Giá/diện tích không hợp lệ; tin bán phải dùng priceUnit TOTAL");
    }
    @Transactional public PropertyDtos.Managed create(Long actor,PropertyDtos.Write r) {
        access.publisherForUpdate(actor);Property p=new Property();p.id=UUID.randomUUID().toString();p.ownerId=actor;
        p.status=Property.Status.DRAFT;p.contentVersion=1;p.currency="VND";p.city="Da Nang";p.declaredAmenities=JsonNodeFactory.instance.arrayNode();
        fill(p,r);properties.saveAndFlush(p);return managed(p,List.of());
    }
    @Transactional public PropertyDtos.Managed patch(Long actor,String id,int version,PropertyDtos.Write r) {
        access.publisherForUpdate(actor);Property p=owned(actor,id);if(p.status==Property.Status.HIDDEN) throw ApiInputs.conflict("Tin bị ẩn cần quản trị viên xử lý");
        reserve(p,version);fill(p,r);p.status=Property.Status.DRAFT;p.publishedAt=null;p.expiresAt=null;p.closedAt=null;
        properties.saveAndFlush(p);return managed(p,images.findByPropertyIdAndDeletedAtIsNullOrderBySortOrderAscIdAsc(p.id));
    }
    @Transactional public PropertyDtos.Managed transition(Long actor,String id,int version,String action) {
        if(!Set.of("submit","close","delete").contains(action))throw ApiInputs.bad("Hành động không hợp lệ");
        Property p=owned(actor,id);
        if(action.equals("submit")) {
            access.publisherForUpdate(actor);
            if(p.status!=Property.Status.DRAFT && p.status!=Property.Status.REJECTED) throw ApiInputs.conflict("Chỉ gửi duyệt tin DRAFT/REJECTED");
            if(images.countByPropertyIdAndDeletedAtIsNull(p.id)<1) throw ApiInputs.bad("Cần ít nhất một ảnh trước khi gửi duyệt");
        }
        reserve(p,version);
        if(action.equals("submit")) {p.status=Property.Status.PENDING;p.publishedAt=null;p.expiresAt=null;p.closedAt=null;}
        else {p.status=Property.Status.CLOSED;p.closedAt=Instant.now();if(action.equals("delete"))p.deletedAt=Instant.now();}
        properties.saveAndFlush(p);return managed(p,images.findByPropertyIdAndDeletedAtIsNullOrderBySortOrderAscIdAsc(p.id));
    }
    @Transactional(readOnly=true) public PropertyDtos.Managed ownDetail(Long actor,String id) {Property p=owned(actor,id);return managed(p,images.findByPropertyIdAndDeletedAtIsNullOrderBySortOrderAscIdAsc(p.id));}
    @Transactional(readOnly=true) public PageResponse<PropertyDtos.Managed> mine(Long actor,int page,int size) {
        access.active(actor);Page<Property> result=properties.findByOwnerIdAndDeletedAtIsNull(actor,ApiInputs.newest(page,size));
        Map<String,List<PropertyImage>> grouped=imageMap(result.getContent());return PageResponse.of(result.map(p->managed(p,grouped.getOrDefault(p.id,List.of()))));
    }
    @Transactional(readOnly=true)
    public PageResponse<PropertyDtos.Managed> mine(Long actor,int page,int size,String keyword,Property.Status status,Property.Type type,String sort) {
        access.active(actor);
        String term=vn.smartprop.modules.collection.CollectionFilters.keyword(keyword);
        var order=vn.smartprop.modules.collection.CollectionFilters.sort(sort,true);
        Instant now=Instant.now();
        org.springframework.data.jpa.domain.Specification<Property> filter=(root,query,cb)->{
            List<jakarta.persistence.criteria.Predicate> terms=new ArrayList<>();
            terms.add(cb.equal(root.get("ownerId"),actor));terms.add(cb.isNull(root.get("deletedAt")));
            terms.add(vn.smartprop.modules.collection.CollectionFilters.text(cb,term,root.get("title"),root.get("address"),root.get("district")));
            if(type!=null)terms.add(cb.equal(root.get("propertyType"),type));
            if(status==Property.Status.EXPIRED) terms.add(cb.or(cb.equal(root.get("status"),status),cb.and(cb.equal(root.get("status"),Property.Status.PUBLISHED),cb.lessThanOrEqualTo(root.get("expiresAt"),now))));
            else if(status!=null){terms.add(cb.equal(root.get("status"),status));if(status==Property.Status.PUBLISHED)terms.add(cb.or(cb.isNull(root.get("expiresAt")),cb.greaterThan(root.get("expiresAt"),now)));}
            return cb.and(terms.toArray(jakarta.persistence.criteria.Predicate[]::new));
        };
        var result=properties.findAll(filter,ApiInputs.page(page,size,order));
        var grouped=imageMap(result.getContent());
        return PageResponse.of(result.map(item->managed(item,grouped.getOrDefault(item.id,List.of()))));
    }
    public Map<String,List<PropertyImage>> imageMap(List<Property> page) {
        if(page.isEmpty()) return Map.of();Map<String,List<PropertyImage>> result=new HashMap<>();
        for(var image:images.findByPropertyIdInAndDeletedAtIsNullOrderBySortOrderAscIdAsc(page.stream().map(p->p.id).toList())) result.computeIfAbsent(image.propertyId,k->new ArrayList<>()).add(image);
        return result;
    }
    public static PropertyDtos.View view(Property p,List<PropertyImage> images) {
        List<String> amenities=new ArrayList<>();if(p.declaredAmenities!=null)p.declaredAmenities.forEach(n->amenities.add(n.asText()));
        return new PropertyDtos.View(p.id,p.projectId,p.title,p.description,p.propertyType,p.transactionType,p.price,p.currency,p.priceUnit,p.areaSqm,p.bedrooms,p.bathrooms,
            p.floor,p.block,p.direction,p.address,p.city,p.district,p.ward,p.location.getY(),p.location.getX(),List.copyOf(amenities),p.status,p.contentVersion,p.publishedAt,p.expiresAt,p.createdAt,p.updatedAt,
            images.stream().map(i->new PropertyDtos.Image(i.id,"/api/v1/properties/"+p.id+"/images/"+i.id+"/content",i.sortOrder,i.isCover)).toList(),p.getListingCode());
    }
    public static PropertyDtos.Managed managed(Property p,List<PropertyImage> images) {return new PropertyDtos.Managed(view(p,images),p.ownerId,p.contactName,p.contactPhone,p.contactEmail);}
}