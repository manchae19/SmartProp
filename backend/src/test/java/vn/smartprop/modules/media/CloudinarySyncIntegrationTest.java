package vn.smartprop.modules.media;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.awt.image.BufferedImage;
import java.io.*;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;
import javax.imageio.ImageIO;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.*;
import vn.smartprop.common.ApiException;

@EnabledIfEnvironmentVariable(named="SMARTPROP_CLOUDINARY_TEST_URL",matches="jdbc:mysql://127\\.0\\.0\\.1:[0-9]+/smartprop_cloudinary_test_[a-f0-9]+\\?.*")
class CloudinarySyncIntegrationTest {
    static JdbcTemplate db;static DriverManagerDataSource source;static String id;
    CloudinaryAdminClient cloud;CloudinaryImageDelivery delivery;CloudinarySyncService sync;
    List<CloudinaryAdminClient.Asset> assets;
    Map<String,CloudinaryImageDelivery.Image> files;
    @BeforeAll static void schema(){
        String url=System.getenv("SMARTPROP_CLOUDINARY_TEST_URL");if(url==null||url.contains(":3306/"))throw new IllegalStateException("An isolated DB is required");
        source=new DriverManagerDataSource(url,"root","");db=new JdbcTemplate(source);
        Flyway.configure().dataSource(source).locations("filesystem:"+java.nio.file.Path.of("../database/migrations").toAbsolutePath().normalize()).cleanDisabled(true).load().migrate();
        db.update("INSERT INTO users(id,email,password_hash,full_name,role,status,created_at,updated_at) VALUES(1,'admin@example.invalid','not-a-login-credential','Test admin','ADMIN','ACTIVE',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),(2,'buyer@example.invalid','not-a-login-credential','Test buyer','BUYER','ACTIVE',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6))");
        for(int i=0;i<3;i++){id=UUID.randomUUID().toString();db.update("INSERT INTO properties(id,owner_id,title,property_type,transaction_type,price,price_unit,area_sqm,location,status,content_version) VALUES (?,1,'Isolated property','APARTMENT','SALE',2000000000,'TOTAL',60,ST_GeomFromText('POINT(108.23 16.06)',4326,'axis-order=long-lat'),'PUBLISHED',1)",id);}
        assertEquals("SP003",db.queryForObject("SELECT listing_code FROM properties WHERE id=?",String.class,id));
    }
    @BeforeEach void prepare()throws Exception{
        db.update("DELETE FROM property_images WHERE property_id=?",id);db.update("UPDATE properties SET content_version=1 WHERE id=?",id);
        cloud=mock(CloudinaryAdminClient.class);delivery=mock(CloudinaryImageDelivery.class);sync=new CloudinarySyncService(db,new DataSourceTransactionManager(source),cloud,delivery);
        assets=new ArrayList<>();files=new HashMap<>();
        for(int i=0;i<6;i++){
            var bitmap=new BufferedImage(4,3,BufferedImage.TYPE_INT_RGB);bitmap.setRGB(0,0,0xff000000+i*10000);
            var output=new ByteArrayOutputStream();ImageIO.write(bitmap,"png",output);var file=CloudinaryImageDelivery.validate(output.toByteArray());
            String key="asset"+i,url="https://res.cloudinary.com/test-cloud/image/upload/v1/"+key+".png";
            assets.add(new CloudinaryAdminClient.Asset("test-cloud",key,"public/"+key,url,"SmartProp/dev/properties/SP003","png",file.bytes().length,4,3,Instant.parse("2026-11-03T00:00:00Z")));
            files.put(url,file);
        }
        when(cloud.listForListing("SP003")).thenAnswer(inv->new CloudinaryAdminClient.Preview("SmartProp/dev/properties/SP003",2,assets.size(),List.copyOf(assets),List.of()));
        when(delivery.fetch(anyString(),anyString())).thenAnswer(inv->files.get(inv.getArgument(1)));
    }

    @Test void hibernateMappingAndNewLocalUploadsRemainCompatible(){
        var config=new org.hibernate.cfg.Configuration().addAnnotatedClass(PropertyImage.class).addAnnotatedClass(vn.smartprop.modules.property.Property.class);
        config.setProperty("hibernate.connection.url",System.getenv("SMARTPROP_CLOUDINARY_TEST_URL"));
        config.setProperty("hibernate.connection.username","root");config.setProperty("hibernate.connection.password","");
        config.setProperty("hibernate.hbm2ddl.auto","validate");
        try(var factory=config.buildSessionFactory();var session=factory.openSession()){
            var image=new PropertyImage();image.id=UUID.randomUUID().toString();image.propertyId=id;image.uploadedBy=1L;
            image.storageKey="c".repeat(32)+".bin";image.mimeType="image/png";image.byteSize=100L;image.sortOrder=0;image.isCover=true;
            var transaction=session.beginTransaction();session.persist(image);transaction.commit();
            assertEquals("LOCAL",db.queryForObject("SELECT storage_provider FROM property_images WHERE id=?",String.class,image.id));
        }
    }

    @Test void firstSyncAndRerunAreIdempotentWithOneCoverAndStableProperty(){
        var before=db.queryForMap("SELECT id,listing_code,title,owner_id,price,area_sqm,status FROM properties WHERE id=?",id);
        var first=sync.synchronize(id,1,1);assertEquals(6,first.created());assertEquals(2,first.contentVersion());
        assertEquals(1,first.images().stream().filter(CloudinarySyncService.Image::cover).count());
        assertEquals(List.of(0,1,2,3,4,5),first.images().stream().map(CloudinarySyncService.Image::sortOrder).toList());
        clearInvocations(delivery);
        var again=sync.synchronize(id,1,2);assertEquals(0,again.created());assertEquals(0,again.updated());assertEquals(6,again.unchanged());assertEquals(2,again.contentVersion());assertEquals(first.images(),again.images());verifyNoInteractions(delivery);
        assertEquals(before,db.queryForMap("SELECT id,listing_code,title,owner_id,price,area_sqm,status FROM properties WHERE id=?",id));
    }
    @Test void localImageIsReusedOnlyWithActualMatchingSha256(){
        assets=new ArrayList<>(assets.subList(0,1));var a=assets.getFirst();var file=files.get(a.secureUrl());String imageId=UUID.randomUUID().toString();
        db.update("INSERT INTO property_images(id,property_id,uploaded_by,storage_key,mime_type,byte_size,sha256,width_px,height_px,sort_order,is_cover) VALUES(?,?,1,?,'image/png',?,?,4,3,0,TRUE)",imageId,id,"a".repeat(32)+".bin",file.bytes().length,file.sha256());
        var result=sync.synchronize(id,1,1);assertEquals(0,result.created());assertEquals(1,result.updated());assertEquals(imageId,result.images().getFirst().id());
        assertEquals("CLOUDINARY",db.queryForObject("SELECT storage_provider FROM property_images WHERE id=?",String.class,imageId));
    }
    @Test void networkFailureLeavesNoPartialImagesAndNoVersionChange(){
        when(delivery.fetch(anyString(),eq(assets.get(1).secureUrl()))).thenThrow(new ApiException(504,"MOCK_TIMEOUT","mock"));
        assertThrows(ApiException.class,()->sync.synchronize(id,1,1));
        assertEquals(0,db.queryForObject("SELECT COUNT(*) FROM property_images WHERE property_id=?",Integer.class,id));
        assertEquals(1,db.queryForObject("SELECT content_version FROM properties WHERE id=?",Integer.class,id));
    }
    @Test void buyerAndStaleVersionCannotSync(){
        assertEquals(403,assertThrows(ApiException.class,()->sync.synchronize(id,2,1)).status);
        assertEquals(409,assertThrows(ApiException.class,()->sync.synchronize(id,1,9)).status);verifyNoInteractions(cloud,delivery);
    }
    @Test void uniqueIndexRejectsDuplicateAssetAndLocalRowsStayCompatible(){
        var result=sync.synchronize(id,1,1);String first=result.images().getFirst().id();
        assertThrows(org.springframework.dao.DataIntegrityViolationException.class,()->db.update("INSERT INTO property_images(id,property_id,uploaded_by,storage_key,storage_provider,mime_type,byte_size,sort_order,is_cover,cloudinary_cloud_name,cloudinary_asset_id,cloudinary_public_id,cloudinary_secure_url,cloudinary_asset_folder) SELECT ?,property_id,uploaded_by,NULL,storage_provider,mime_type,byte_size,100,FALSE,cloudinary_cloud_name,cloudinary_asset_id,cloudinary_public_id,cloudinary_secure_url,cloudinary_asset_folder FROM property_images WHERE id=?",UUID.randomUUID().toString(),first));
        db.update("INSERT INTO property_images(id,property_id,uploaded_by,storage_key,mime_type,byte_size,sort_order,is_cover) VALUES(?,?,1,?,'image/png',100,101,FALSE)",UUID.randomUUID().toString(),id,"b".repeat(32)+".bin");
        assertEquals(1,db.queryForObject("SELECT COUNT(*) FROM property_images WHERE property_id=? AND storage_provider='LOCAL'",Integer.class,id));
    }
    @Test void softDeletedCloudAssetIsNotResurrected(){
        assets=new ArrayList<>(assets.subList(0,1));var first=sync.synchronize(id,1,1);
        db.update("UPDATE property_images SET deleted_at=UTC_TIMESTAMP(6),is_cover=FALSE WHERE id=?",first.images().getFirst().id());
        var result=sync.synchronize(id,1,2);assertEquals(1,result.skippedDeleted());assertEquals(0,result.created());assertTrue(result.images().isEmpty());
    }
    @Test void concurrentSyncsCannotCreateDuplicateAssets()throws Exception{
        assets=new ArrayList<>(assets.subList(0,1));var barrier=new CyclicBarrier(2);
        when(delivery.fetch(anyString(),anyString())).thenAnswer(inv->{barrier.await(10,TimeUnit.SECONDS);return files.get(inv.getArgument(1));});
        var other=new CloudinarySyncService(db,new DataSourceTransactionManager(source),cloud,delivery);
        try(var pool=Executors.newFixedThreadPool(2)){
            Callable<Integer> first=()->{try{return sync.synchronize(id,1,1).created();}catch(ApiException e){assertEquals(409,e.status);return -1;}};
            Callable<Integer> second=()->{try{return other.synchronize(id,1,1).created();}catch(ApiException e){assertEquals(409,e.status);return -1;}};
            var results=pool.invokeAll(List.of(first,second));assertEquals(Set.of(1,-1),Set.of(results.get(0).get(),results.get(1).get()));
        }
        assertEquals(1,db.queryForObject("SELECT COUNT(*) FROM property_images WHERE property_id=?",Integer.class,id));
    }
}
