package vn.smartprop.modules.media;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import java.util.*;
import org.junit.jupiter.api.*;
import vn.smartprop.common.*;
import vn.smartprop.config.*;
import vn.smartprop.modules.auth.AccountAccess;
import vn.smartprop.modules.property.*;
import vn.smartprop.modules.user.User;
class CloudinaryMediaAccessTest {
    final PropertyService properties=mock(PropertyService.class);
    final PropertyRepository repository=mock(PropertyRepository.class);
    final PropertyImageRepository images=mock(PropertyImageRepository.class);
    final LocalFileStore local=mock(LocalFileStore.class);
    final AccountAccess access=mock(AccountAccess.class);
    final CloudinaryImageDelivery remote=mock(CloudinaryImageDelivery.class);
    PropertyMediaService service;Property property;PropertyImage image;
    final String id="00000000-0000-4000-8000-000000000001",imageId="00000000-0000-4000-8000-000000000002";
    @BeforeEach void setup(){
        service=new PropertyMediaService(properties,repository,images,local,access,remote);
        property=new Property();property.id=id;property.ownerId=2L;property.status=Property.Status.PUBLISHED;when(properties.existing(id)).thenReturn(property);
        image=new PropertyImage();image.id=imageId;image.propertyId=id;image.storageProvider="CLOUDINARY";image.cloudinaryCloudName="cloud";image.cloudinarySecureUrl="https://res.cloudinary.com/cloud/image/upload/v1/a.png";image.sha256="hash";image.mimeType="image/png";
        when(images.findByIdAndPropertyIdAndDeletedAtIsNull(imageId,id)).thenReturn(Optional.of(image));
        when(remote.fetch(anyString(),anyString())).thenReturn(new CloudinaryImageDelivery.Image(new byte[]{1,2}, "image/png",1,1,"hash"));
    }
    @Test void publishedImageUsesCloudinaryOnlyAfterPublicationCheck(){
        var response=service.download(null,id,imageId);assertEquals(200,response.getStatusCode().value());assertArrayEquals(new byte[]{1,2},response.getBody());verifyNoInteractions(local);
    }
    @Test void draftImageIsNotExposedToGuests(){
        property.status=Property.Status.DRAFT;assertEquals(404,assertThrows(ApiException.class,()->service.download(null,id,imageId)).status);verifyNoInteractions(images,remote,local);
    }
    @Test void unrelatedBuyerCannotFetchPrivateCloudImage(){
        property.status=Property.Status.DRAFT;var user=new User();user.id=3L;user.role=User.Role.BUYER;when(access.active(3L)).thenReturn(user);
        assertEquals(404,assertThrows(ApiException.class,()->service.download(3L,id,imageId)).status);verifyNoInteractions(remote,images);
    }
    @Test void changedBytesAreNotServedAsVerifiedImage(){
        when(remote.fetch(anyString(),anyString())).thenReturn(new CloudinaryImageDelivery.Image(new byte[]{3},"image/png",1,1,"changed"));
        assertEquals(502,assertThrows(ApiException.class,()->service.download(null,id,imageId)).status);
    }
    @Test void localImagePathRemainsSupported(){
        image.storageProvider="LOCAL";image.storageKey="a".repeat(32)+".bin";when(local.read(image.storageKey)).thenReturn(new byte[]{7});
        assertArrayEquals(new byte[]{7},service.download(null,id,imageId).getBody());verifyNoInteractions(remote);
    }
}
