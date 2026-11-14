ALTER TABLE property_images
  MODIFY COLUMN storage_key VARCHAR(512) NULL,
  ADD COLUMN storage_provider VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'LOCAL',
  ADD COLUMN cloudinary_cloud_name VARCHAR(63) CHARACTER SET ascii COLLATE ascii_bin NULL,
  ADD COLUMN cloudinary_asset_id VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin NULL,
  ADD COLUMN cloudinary_public_id VARCHAR(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL,
  ADD COLUMN cloudinary_secure_url VARCHAR(2048) CHARACTER SET ascii COLLATE ascii_bin NULL,
  ADD COLUMN cloudinary_asset_folder VARCHAR(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL,
  ADD CONSTRAINT uq_property_cloudinary_asset UNIQUE (property_id, cloudinary_cloud_name, cloudinary_asset_id),
  ADD CONSTRAINT ck_property_image_storage CHECK (
    (storage_provider='LOCAL' AND storage_key IS NOT NULL
      AND cloudinary_cloud_name IS NULL AND cloudinary_asset_id IS NULL
      AND cloudinary_public_id IS NULL AND cloudinary_secure_url IS NULL AND cloudinary_asset_folder IS NULL)
    OR
    (storage_provider='CLOUDINARY' AND storage_key IS NULL
      AND cloudinary_cloud_name IS NOT NULL AND cloudinary_cloud_name<>''
      AND cloudinary_asset_id IS NOT NULL AND cloudinary_asset_id<>''
      AND cloudinary_public_id IS NOT NULL AND cloudinary_public_id<>''
      AND cloudinary_secure_url IS NOT NULL AND cloudinary_secure_url<>''
      AND cloudinary_asset_folder IS NOT NULL AND cloudinary_asset_folder<>'')
  );
