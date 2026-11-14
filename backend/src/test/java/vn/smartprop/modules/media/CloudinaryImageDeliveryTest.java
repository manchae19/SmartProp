package vn.smartprop.modules.media;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import java.awt.image.BufferedImage;
import java.io.*;
import java.net.http.*;
import java.util.concurrent.*;
import javax.imageio.ImageIO;
import org.junit.jupiter.api.Test;
import vn.smartprop.common.ApiException;
class CloudinaryImageDeliveryTest {
    static byte[] png()throws Exception{var output=new ByteArrayOutputStream();ImageIO.write(new BufferedImage(4,3,BufferedImage.TYPE_INT_RGB),"png",output);return output.toByteArray();}
    @Test void onlyFixedHttpsCloudinaryTenantIsAccepted(){for(String url:new String[]{"http://res.cloudinary.com/cloud/image/upload/a.jpg","https://evil.invalid/a.jpg","https://res.cloudinary.com/other/image/upload/a.jpg","https://res.cloudinary.com/cloud/raw/upload/a.bin","https://res.cloudinary.com/cloud/image/upload/a.jpg?token=x"})assertThrows(ApiException.class,()->CloudinaryImageDelivery.deliveryUri("cloud",url));}
    @Test void imageSignatureDecodeAndSizeAreValidated()throws Exception{var file=CloudinaryImageDelivery.validate(png());assertEquals("image/png",file.mime());assertEquals(4,file.width());assertEquals(3,file.height());assertEquals(64,file.sha256().length());assertThrows(ApiException.class,()->CloudinaryImageDelivery.validate(new byte[]{(byte)255,(byte)216,(byte)255,0}));assertThrows(ApiException.class,()->CloudinaryImageDelivery.validate(new byte[(int)LocalFileStore.MAX_BYTES+1]));}
    @Test void deliveryRequestHasNoApiCredentialsOrSmartPropJwt()throws Exception{
        byte[] bytes=png();var http=mock(HttpClient.class);var response=mock(HttpResponse.class);
        when(response.statusCode()).thenReturn(200);when(response.body()).thenReturn(new ByteArrayInputStream(bytes));
        when(http.sendAsync(any(HttpRequest.class),any(HttpResponse.BodyHandler.class))).thenAnswer(inv->{HttpRequest r=inv.getArgument(0);assertTrue(r.headers().firstValue("Authorization").isEmpty());assertTrue(r.headers().firstValue("Cookie").isEmpty());return CompletableFuture.completedFuture(response);});
        assertArrayEquals(bytes,new CloudinaryImageDelivery(http).fetch("cloud","https://res.cloudinary.com/cloud/image/upload/v1/a.png").bytes());
    }
    @Test void redirectsAreErrorsAndNeverFollowed()throws Exception{
        var http=mock(HttpClient.class);var response=mock(HttpResponse.class);when(response.statusCode()).thenReturn(302);when(response.body()).thenReturn(new ByteArrayInputStream(new byte[0]));
        when(http.sendAsync(any(HttpRequest.class),any(HttpResponse.BodyHandler.class))).thenReturn(CompletableFuture.completedFuture(response));
        assertEquals(502,assertThrows(ApiException.class,()->new CloudinaryImageDelivery(http).fetch("cloud","https://res.cloudinary.com/cloud/image/upload/v1/a.png")).status);
        verify(http,times(1)).sendAsync(any(HttpRequest.class),any(HttpResponse.BodyHandler.class));
    }
    @Test void timeoutDoesNotReturnPlaceholderBytes()throws Exception{
        var http=mock(HttpClient.class);when(http.sendAsync(any(HttpRequest.class),any(HttpResponse.BodyHandler.class))).thenReturn(CompletableFuture.failedFuture(new HttpTimeoutException("mock")));
        assertEquals(504,assertThrows(ApiException.class,()->new CloudinaryImageDelivery(http).fetch("cloud","https://res.cloudinary.com/cloud/image/upload/v1/a.png")).status);
    }
}
