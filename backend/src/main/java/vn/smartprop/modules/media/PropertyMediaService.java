package vn.smartprop.modules.media;
import java.time.Instant;
import java.util.*;
import jakarta.validation.constraints.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.http.ResponseEntity;
import org.springframework.web.multipart.MultipartFile;
import vn.smartprop.common.*;
import vn.smartprop.modules.auth.AccountAccess;
import vn.smartprop.modules.property.*;
import vn.smartprop.modules.user.User;
@Service
public class PropertyMediaService {
    public record Patch(@NotNull @Positive Integer expectedVersion,@Min(0) @Max(1000000) Integer sortOrder,Boolean cover) {}
    public record Order(@NotNull @Positive Integer expectedVersion,@NotNull @Size(min=1,max=30) List<@NotBlank String> imageIds) {}
    private final PropertyService properties;private final PropertyRepository repository;private final PropertyImageRepository images;private final LocalFileStore files;private final AccountAccess access;private final CloudinaryImageDelivery cloudinary;
    public PropertyMediaService(PropertyService properties,PropertyRepository repository,PropertyImageRepository images,LocalFileStore files,AccountAccess access,CloudinaryImageDelivery cloudinary) {this.properties=properties;this.repository=repository;this.images=images;this.files=files;this.access=access;this.cloudinary=cloudinary;}
    private Property editable(Long actor,String id) {access.publisherForUpdate(actor);Property p=properties.owned(actor,id);if(p.status==Property.Status.HIDDEN)throw ApiInputs.conflict("Tin bị ẩn không thể sửa ảnh");return p;}
    private void draft(Property p) {p.status=Property.Status.DRAFT;p.publishedAt=null;p.expiresAt=null;p.closedAt=null;}
    private PropertyDtos.Managed result(Property p) {repository.saveAndFlush(p);return PropertyService.managed(p,images.findByPropertyIdAndDeletedAtIsNullOrderBySortOrderAscIdAsc(p.id));}
    @Transactional public PropertyDtos.Managed upload(Long actor,String propertyId,int version,MultipartFile input) {
        Property p=editable(actor,propertyId);var validated=files.validate(input,false);properties.reserve(p,version);
        var current=images.findByPropertyIdAndDeletedAtIsNullOrderBySortOrderAscIdAsc(p.id);if(current.size()>=30)throw ApiInputs.bad("Tối đa30 ảnh/tin");
        int max=current.stream().mapToInt(i->i.sortOrder).max().orElse(-1);if(max==Integer.MAX_VALUE)throw ApiInputs.conflict("Thứ tự ảnh vượt giới hạn");
        var stored=files.store(validated);PropertyImage image=new PropertyImage();image.id=UUID.randomUUID().toString();image.propertyId=p.id;image.uploadedBy=actor;
        image.storageKey=stored.key();image.originalFilename=validated.originalFilename();image.mimeType=validated.mimeType();image.byteSize=(long)validated.bytes().length;image.sha256=validated.sha256();
        image.widthPx=validated.width();image.heightPx=validated.height();image.sortOrder=max+1;image.isCover=current.isEmpty();images.saveAndFlush(image);draft(p);return result(p);
    }
    @Transactional public PropertyDtos.Managed patch(Long actor,String propertyId,String imageId,Patch patch) {
        Property p=editable(actor,propertyId);properties.reserve(p,patch.expectedVersion());var current=images.findByPropertyIdAndDeletedAtIsNullOrderBySortOrderAscIdAsc(p.id);
        PropertyImage image=current.stream().filter(i->i.id.equals(ApiInputs.uuid(imageId))).findFirst().orElseThrow(ApiInputs::missing);
        if(patch.sortOrder()!=null && current.stream().anyMatch(i->!i.id.equals(image.id)&&Objects.equals(i.sortOrder,patch.sortOrder())))throw ApiInputs.conflict("sortOrder đã được dùng; dùng API /images/order để sắp xếp cả danh sách");
        if(patch.sortOrder()!=null)image.sortOrder=patch.sortOrder();
        if(patch.cover()!=null) {
            PropertyImage chosen=patch.cover()?image:current.stream().filter(i->!i.id.equals(image.id)).findFirst().orElseThrow(()->ApiInputs.bad("Ảnh duy nhất phải là ảnh bìa"));
            for(var i:current)i.isCover=false;images.flush();chosen.isCover=true;
        }
        images.flush();draft(p);return result(p);
    }
    @Transactional public PropertyDtos.Managed order(Long actor,String propertyId,Order order) {
        Property p=editable(actor,propertyId);properties.reserve(p,order.expectedVersion());var current=images.findByPropertyIdAndDeletedAtIsNullOrderBySortOrderAscIdAsc(p.id);
        var ids=order.imageIds().stream().map(ApiInputs::uuid).toList();Map<String,PropertyImage> byId=new HashMap<>();current.forEach(i->byId.put(i.id,i));
        if(ids.size()!=current.size()||new HashSet<>(ids).size()!=ids.size()||!byId.keySet().equals(new HashSet<>(ids)))throw ApiInputs.bad("imageIds phải là hoán vị đầy đủ các ảnh hiện có");
        int max=current.stream().mapToInt(i->i.sortOrder).max().orElse(0);if(max>Integer.MAX_VALUE-current.size()-1)throw ApiInputs.conflict("Thứ tự ảnh vượt giới hạn");
        for(int i=0;i<current.size();i++)current.get(i).sortOrder=max+1+i;images.flush();
        for(int i=0;i<ids.size();i++)byId.get(ids.get(i)).sortOrder=i;images.flush();draft(p);return result(p);
    }
    @Transactional public PropertyDtos.Managed remove(Long actor,String propertyId,String imageId,int version) {
        Property p=editable(actor,propertyId);properties.reserve(p,version);var current=images.findByPropertyIdAndDeletedAtIsNullOrderBySortOrderAscIdAsc(p.id);
        PropertyImage image=current.stream().filter(i->i.id.equals(ApiInputs.uuid(imageId))).findFirst().orElseThrow(ApiInputs::missing);
        boolean wasCover=image.isCover;image.deletedAt=Instant.now();image.isCover=false;images.flush();
        if(wasCover)current.stream().filter(i->i.deletedAt==null).findFirst().ifPresent(i->i.isCover=true);
        images.flush();draft(p);return result(p);
    }
    @Transactional(readOnly=true) public ResponseEntity<byte[]> download(Long actor,String propertyId,String imageId) {
        Property p=properties.existing(propertyId);
        if(!PropertyService.visible(p,Instant.now())) {if(actor==null)throw ApiInputs.missing();User u=access.active(actor);if(!Objects.equals(actor,p.ownerId)&&u.role!=User.Role.ADMIN)throw ApiInputs.missing();}
        PropertyImage image=images.findByIdAndPropertyIdAndDeletedAtIsNull(ApiInputs.uuid(imageId),p.id).orElseThrow(ApiInputs::missing);
        if("CLOUDINARY".equals(image.storageProvider)){var remote=cloudinary.fetch(image.cloudinaryCloudName,image.cloudinarySecureUrl);if(!Objects.equals(image.sha256,remote.sha256()))throw new ApiException(502,"CLOUDINARY_IMAGE_CHANGED","Ảnh nguồn đã thay đổi; cần đồng bộ lại.");return Downloads.response(remote.bytes(),remote.mime(),image.id);}
        return Downloads.response(files.read(image.storageKey),image.mimeType,image.id);
    }
}