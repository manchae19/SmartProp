package vn.smartprop.modules.media;

import jakarta.persistence.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;
import org.hibernate.type.SqlTypes;
import java.time.*;
import java.math.BigDecimal;
import com.fasterxml.jackson.databind.JsonNode;
import org.locationtech.jts.geom.Point;

/** Persistence mapping only. Foreign-key IDs do not imply cascade operations. */
@Entity @Table(name="property_images")
public class PropertyImage {

    @Id @JdbcTypeCode(SqlTypes.CHAR) @Column(name="id",length=36,nullable=false) public String id;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name="property_id",length=36,nullable=false) public String propertyId;
    @Column(name="uploaded_by",nullable=false) public Long uploadedBy;
    @Column(name="storage_key",length=512) public String storageKey;
    @Column(name="storage_provider",length=16,nullable=false) public String storageProvider="LOCAL";
    @Column(name="cloudinary_cloud_name",length=63) public String cloudinaryCloudName;
    @Column(name="cloudinary_asset_id",length=128) public String cloudinaryAssetId;
    @Column(name="cloudinary_public_id",length=1024) public String cloudinaryPublicId;
    @Column(name="cloudinary_secure_url",length=2048) public String cloudinarySecureUrl;
    @Column(name="cloudinary_asset_folder",length=512) public String cloudinaryAssetFolder;
    @Column(name="original_filename",length=255) public String originalFilename;
    @Column(name="mime_type",length=50,nullable=false) public String mimeType;
    @Column(name="byte_size",nullable=false) public Long byteSize;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name="sha256",length=64) public String sha256;
    @Column(name="width_px") public Integer widthPx;
    @Column(name="height_px") public Integer heightPx;
    @Column(name="sort_order",nullable=false) public Integer sortOrder;
    @Column(name="is_cover",nullable=false) public boolean isCover;
    @Column(name="deleted_at") public Instant deletedAt;
    @CreationTimestamp @Column(name="created_at",nullable=false) public Instant createdAt;
    @UpdateTimestamp @Column(name="updated_at",nullable=false) public Instant updatedAt;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name="active_cover",length=36,insertable=false,updatable=false) public String activeCover;
    @Column(name="active_sort",insertable=false,updatable=false) public Integer activeSort;
}
