-- Development-only metadata. Accounts are BCrypt-hashed by DevDatabaseSeed first.
-- Run in one connection/transaction. No model predictions or real personal data are seeded.
SET time_zone = '+00:00';
SET @buyer_id=(SELECT id FROM users WHERE email='buyer@smartprop.example.test');
SET @broker_id=(SELECT id FROM users WHERE email='broker@smartprop.example.test');
INSERT INTO projects(id,name,developer,address,location,amenities)
 SELECT '10000000-0000-4000-8000-000000000001','Development Project','Synthetic developer','Demo address, Da Nang',ST_GeomFromText('POINT(108.2200 16.0600)',4326,'axis-order=long-lat'),JSON_ARRAY('PARKING')
 WHERE NOT EXISTS(SELECT 1 FROM projects WHERE id='10000000-0000-4000-8000-000000000001');
INSERT INTO properties(id,owner_id,project_id,title,description,property_type,transaction_type,price,currency,price_unit,area_sqm,bedrooms,bathrooms,address,district,location,declared_amenities,status)
 SELECT '20000000-0000-4000-8000-000000000001',@broker_id,'10000000-0000-4000-8000-000000000001','Synthetic apartment for development','Development fixture; not a real listing','APARTMENT','SALE',3200000000,'VND','TOTAL',68,2,2,'Demo address','Hai Chau',ST_GeomFromText('POINT(108.2200 16.0600)',4326,'axis-order=long-lat'),JSON_ARRAY('SOFA','TV'),'DRAFT'
 WHERE NOT EXISTS(SELECT 1 FROM properties WHERE id='20000000-0000-4000-8000-000000000001');
INSERT INTO property_images(id,property_id,uploaded_by,storage_key,original_filename,mime_type,byte_size,width_px,height_px,sort_order,is_cover)
 SELECT '30000000-0000-4000-8000-000000000001','20000000-0000-4000-8000-000000000001',@broker_id,'dev-fixtures/sample-property.svg','sample-property.svg','image/svg+xml',@fixture_bytes,640,360,0,TRUE
 WHERE NOT EXISTS(SELECT 1 FROM property_images WHERE id='30000000-0000-4000-8000-000000000001');
INSERT INTO points_of_interest(id,name,category,location,source_name,external_id,observed_at)
 SELECT '40000000-0000-4000-8000-000000000001','Synthetic park','PARK',ST_GeomFromText('POINT(108.2210 16.0600)',4326,'axis-order=long-lat'),'development-fixture','park-1',UTC_TIMESTAMP(6)
 WHERE NOT EXISTS(SELECT 1 FROM points_of_interest WHERE id='40000000-0000-4000-8000-000000000001');
INSERT INTO saved_properties(user_id,property_id)
 SELECT @buyer_id,'20000000-0000-4000-8000-000000000001'
 WHERE NOT EXISTS(SELECT 1 FROM saved_properties WHERE user_id=@buyer_id AND property_id='20000000-0000-4000-8000-000000000001');
INSERT INTO reports(id,reporter_id,property_id,reason_code,description,contact_email)
 SELECT '50000000-0000-4000-8000-000000000001',@buyer_id,'20000000-0000-4000-8000-000000000001','OTHER','Synthetic report for moderation development','buyer@smartprop.example.test'
 WHERE NOT EXISTS(SELECT 1 FROM reports WHERE id='50000000-0000-4000-8000-000000000001');
