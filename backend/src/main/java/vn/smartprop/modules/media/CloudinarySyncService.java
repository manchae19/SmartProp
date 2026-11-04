package vn.smartprop.modules.media;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.Semaphore;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import vn.smartprop.common.*;
import vn.smartprop.config.*;

@Service
public class CloudinarySyncService {
    private final JdbcTemplate db;
    private final TransactionTemplate tx;
    private final CloudinaryAdminClient cloud;
    private final CloudinaryImageDelivery delivery;
    private final Semaphore syncing=new Semaphore(1);
    public record Result(String propertyId,String listingCode,int created,int updated,int unchanged,int skippedDeleted,
        int duplicateContent,int contentVersion,List<Image> images) {}
    public record Image(String id,String assetId,int sortOrder,boolean cover) {}
    private record Property(String id,String code,int version,String status,Instant deletedAt) {}
    private record Existing(String id,String provider,String cloud,String assetId,String publicId,String url,
        String folder,String sha,long size,int width,int height,int sort,boolean cover,boolean deleted) {}
    private record Prepared(CloudinaryAdminClient.Asset asset,CloudinaryImageDelivery.Image image) {}
    public CloudinarySyncService(JdbcTemplate db,PlatformTransactionManager manager,CloudinaryAdminClient cloud,CloudinaryImageDelivery delivery){
        this.db=db;this.tx=new TransactionTemplate(manager);this.cloud=cloud;this.delivery=delivery;
    }
    private void administrator(long actor){
        Integer count=db.queryForObject("SELECT COUNT(*) FROM users WHERE id=? AND role='ADMIN' AND status='ACTIVE' AND deleted_at IS NULL",Integer.class,actor);
        if(count==null||count!=1)throw ApiInputs.forbidden();
    }
    private Property property(String id,boolean lock){
        var rows=db.query("SELECT id,listing_code,content_version,status,deleted_at FROM properties WHERE id=?"+(lock?" FOR UPDATE":""),
            (r,n)->new Property(r.getString(1),r.getString(2),r.getInt(3),r.getString(4),r.getTimestamp(5)==null?null:r.getTimestamp(5).toInstant()),id);
        if(rows.isEmpty()||rows.getFirst().deletedAt()!=null)throw ApiInputs.missing();return rows.getFirst();
    }
    private List<Existing> existing(String id){
        return db.query("SELECT id,storage_provider,cloudinary_cloud_name,cloudinary_asset_id,cloudinary_public_id,cloudinary_secure_url,cloudinary_asset_folder,sha256,byte_size,width_px,height_px,sort_order,is_cover,deleted_at FROM property_images WHERE property_id=? ORDER BY sort_order,id",
            (r,n)->new Existing(r.getString(1),r.getString(2),r.getString(3),r.getString(4),r.getString(5),r.getString(6),r.getString(7),r.getString(8),r.getLong(9),r.getInt(10),r.getInt(11),r.getInt(12),r.getBoolean(13),r.getTimestamp(14)!=null),id);
    }
    private static boolean matches(Existing e,CloudinaryAdminClient.Asset a){
        return e!=null&&Objects.equals(e.cloud(),a.cloudName())&&Objects.equals(e.assetId(),a.assetId())
            &&Objects.equals(e.publicId(),a.publicId())&&Objects.equals(e.url(),a.secureUrl())&&Objects.equals(e.folder(),a.assetFolder())
            &&e.size()==a.bytes()&&e.width()==a.width()&&e.height()==a.height()&&e.sha()!=null;
    }
    public Result synchronize(String propertyId,long actor,int expectedVersion){
        String id=ApiInputs.uuid(propertyId);administrator(actor);
        if(expectedVersion<1||expectedVersion==Integer.MAX_VALUE)throw ApiInputs.bad("expectedVersion không hợp lệ.");
        if(!syncing.tryAcquire())throw new ApiException(409,"CLOUDINARY_SYNC_BUSY","Đang đồng bộ ảnh; hãy thử lại.");
        try {
            var p=property(id,false);if(p.version()!=expectedVersion)throw ApiInputs.conflict("Tin đã thay đổi; hãy tải lại.");
            Integer columns=db.queryForObject("SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='property_images' AND column_name='cloudinary_asset_id'",Integer.class);
            if(columns==null||columns!=1)throw new ApiException(503,"CLOUDINARY_SCHEMA_NOT_READY","Cần rollout V17 trước khi đồng bộ.");
            var preview=cloud.listForListing(p.code());
            if(!preview.rejected().isEmpty())throw new ApiException(422,"CLOUDINARY_REVIEW_REQUIRED","Có "+preview.rejected().size()+" tài nguyên không hợp lệ; chưa ghi dữ liệu.");
            if(preview.assets().isEmpty())throw new ApiException(404,"CLOUDINARY_FOLDER_EMPTY","Không có ảnh hợp lệ trong thư mục tin.");
            if(preview.assets().size()>30)throw ApiInputs.bad("Thư mục có hơn 30 ảnh; cần chọn lại trước khi đồng bộ.");
            var old=existing(id);var prepared=new ArrayList<Prepared>();long total=0;
            for(var a:preview.assets()){
                total+=a.bytes();if(total>60L*1024*1024)throw ApiInputs.bad("Tổng ảnh vượt giới hạn 60 MB/lần.");
                Existing same=old.stream().filter(e->Objects.equals(e.cloud(),a.cloudName())&&Objects.equals(e.assetId(),a.assetId())).findFirst().orElse(null);
                if(same!=null&&(same.deleted()||matches(same,a))){prepared.add(new Prepared(a,null));continue;}
                var file=delivery.fetch(a.cloudName(),a.secureUrl());
                if(file.bytes().length!=a.bytes()||file.width()!=a.width()||file.height()!=a.height())throw new ApiException(409,"CLOUDINARY_ASSET_CHANGED","Ảnh thay đổi trong lúc tải; chưa ghi dữ liệu.");
                prepared.add(new Prepared(a,file));
            }
            return tx.execute(status->apply(id,actor,expectedVersion,p.code(),prepared));
        }finally{syncing.release();}
    }
    private Result apply(String id,long actor,int expected,String code,List<Prepared> prepared){
        administrator(actor);var p=property(id,true);
        if(p.version()!=expected||!p.code().equals(code))throw ApiInputs.conflict("Tin đã thay đổi; chưa ghi ảnh.");
        var rows=new ArrayList<>(existing(id));int created=0,updated=0,unchanged=0,skipped=0,duplicates=0;
        int next=rows.stream().filter(e->!e.deleted()).mapToInt(Existing::sort).max().orElse(-1)+1;
        for(var item:prepared){
            var a=item.asset();var file=item.image();
            Existing match=rows.stream().filter(e->Objects.equals(e.cloud(),a.cloudName())&&Objects.equals(e.assetId(),a.assetId())).findFirst().orElse(null);
            if(match!=null&&match.deleted()){skipped++;continue;}
            if(matches(match,a)){unchanged++;continue;}
            if(file==null)throw ApiInputs.conflict("Metadata ảnh thay đổi; hãy đồng bộ lại.");
            if(match==null){
                var locals=rows.stream().filter(e->!e.deleted()&&e.provider().equals("LOCAL")&&file.sha256().equals(e.sha())).toList();
                if(locals.size()>1)throw new ApiException(409,"CLOUDINARY_AMBIGUOUS_LOCAL","Có nhiều ảnh local cùng nội dung; cần đối chiếu thủ công.");
                if(!locals.isEmpty())match=locals.getFirst();
                else if(rows.stream().anyMatch(e->!e.deleted()&&file.sha256().equals(e.sha()))){duplicates++;continue;}
            }
            String imageId=match==null?UUID.randomUUID().toString():match.id();int order=match==null?next++:match.sort();boolean cover=match!=null&&match.cover();
            if(order>1000000)throw ApiInputs.conflict("Thứ tự ảnh vượt giới hạn.");
            if(match==null){
                if(rows.stream().filter(e->!e.deleted()).count()>=30)throw ApiInputs.bad("Tin vượt giới hạn 30 ảnh.");
                db.update("INSERT INTO property_images(id,property_id,uploaded_by,storage_provider,storage_key,mime_type,byte_size,sha256,width_px,height_px,sort_order,is_cover,cloudinary_cloud_name,cloudinary_asset_id,cloudinary_public_id,cloudinary_secure_url,cloudinary_asset_folder) VALUES (?,?,?,'CLOUDINARY',NULL,?,?,?,?,?,?,FALSE,?,?,?,?,?)",
                    imageId,id,actor,file.mime(),(long)file.bytes().length,file.sha256(),file.width(),file.height(),order,a.cloudName(),a.assetId(),a.publicId(),a.secureUrl(),a.assetFolder());
                created++;
            } else {
                db.update("UPDATE property_images SET storage_provider='CLOUDINARY',storage_key=NULL,mime_type=?,byte_size=?,sha256=?,width_px=?,height_px=?,cloudinary_cloud_name=?,cloudinary_asset_id=?,cloudinary_public_id=?,cloudinary_secure_url=?,cloudinary_asset_folder=?,updated_at=UTC_TIMESTAMP(6) WHERE id=? AND property_id=?",
                    file.mime(),(long)file.bytes().length,file.sha256(),file.width(),file.height(),a.cloudName(),a.assetId(),a.publicId(),a.secureUrl(),a.assetFolder(),imageId,id);
                updated++;rows.remove(match);
            }
            rows.add(new Existing(imageId,"CLOUDINARY",a.cloudName(),a.assetId(),a.publicId(),a.secureUrl(),a.assetFolder(),file.sha256(),file.bytes().length,file.width(),file.height(),order,cover,false));
        }
        int coverRepaired=0;
        if(rows.stream().anyMatch(e->!e.deleted())&&rows.stream().noneMatch(e->!e.deleted()&&e.cover())){
            var first=rows.stream().filter(e->!e.deleted()).min(Comparator.comparingInt(Existing::sort).thenComparing(Existing::id)).orElseThrow();
            db.update("UPDATE property_images SET is_cover=TRUE,updated_at=UTC_TIMESTAMP(6) WHERE id=?",first.id());coverRepaired=1;
        }
        int version=expected;
        if(created+updated+coverRepaired>0){
            if(db.update("UPDATE properties SET content_version=content_version+1,updated_at=UTC_TIMESTAMP(6) WHERE id=? AND content_version=?",id,expected)!=1)throw ApiInputs.conflict("Tin đã thay đổi.");
            version++;
        }
        var images=existing(id).stream().filter(e->!e.deleted()).map(e->new Image(e.id(),e.assetId(),e.sort(),e.cover())).toList();
        return new Result(id,code,created,updated,unchanged,skipped,duplicates,version,images);
    }
}
