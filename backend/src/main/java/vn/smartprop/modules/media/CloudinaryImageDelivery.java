package vn.smartprop.modules.media;

import java.io.*;
import java.net.URI;
import java.net.http.*;
import java.security.*;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import javax.imageio.ImageIO;
import org.springframework.stereotype.Component;
import vn.smartprop.common.ApiException;

@Component
public class CloudinaryImageDelivery {
    public record Image(byte[] bytes,String mime,int width,int height,String sha256) {}
    private final HttpClient http;
    private final Semaphore slots=new Semaphore(6);
    public CloudinaryImageDelivery(){this(HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3))
        .followRedirects(HttpClient.Redirect.NEVER).build());}
    CloudinaryImageDelivery(HttpClient http){this.http=http;}
    static URI deliveryUri(String cloud,String url){
        try {
            URI uri=URI.create(url);
            if(cloud==null||!cloud.matches("[A-Za-z0-9_-]{1,63}")||url.length()>2048
                ||!"https".equals(uri.getScheme())||!"res.cloudinary.com".equalsIgnoreCase(uri.getHost())
                ||uri.getUserInfo()!=null||uri.getPort()!=-1||uri.getFragment()!=null||uri.getQuery()!=null
                ||!uri.getPath().startsWith("/"+cloud+"/image/upload/"))throw new IllegalArgumentException();
            return uri;
        }catch(Exception e){throw new ApiException(502,"CLOUDINARY_INVALID_DELIVERY","URL ảnh Cloudinary không hợp lệ.");}
    }
    public Image fetch(String cloud,String url){
        URI uri=deliveryUri(cloud,url);
        if(!slots.tryAcquire())throw new ApiException(503,"CLOUDINARY_IMAGE_BUSY","Đang tải nhiều ảnh, vui lòng thử lại.");
        CompletableFuture<HttpResponse<InputStream>> pending=null;
        try {
            long deadline=System.nanoTime()+TimeUnit.SECONDS.toNanos(10);
            var request=HttpRequest.newBuilder(uri).timeout(Duration.ofSeconds(10)).header("Accept","image/jpeg,image/png,image/webp")
                .header("Accept-Encoding","identity").GET().build();
            pending=http.sendAsync(request,HttpResponse.BodyHandlers.ofInputStream());
            var response=pending.get(10,TimeUnit.SECONDS);
            try(var input=response.body()){
                if(response.statusCode()!=200)throw new ApiException(502,"CLOUDINARY_IMAGE_UNAVAILABLE","Không tải được ảnh từ Cloudinary.");
                var read=CompletableFuture.supplyAsync(()->{try{return input.readNBytes((int)LocalFileStore.MAX_BYTES+1);}catch(IOException e){throw new CompletionException(e);}});
                byte[] bytes;try{bytes=read.get(Math.max(1,deadline-System.nanoTime()),TimeUnit.NANOSECONDS);}finally{read.cancel(true);}
                return validate(bytes);
            }
        }catch(ApiException e){throw e;}
        catch(InterruptedException e){Thread.currentThread().interrupt();throw new ApiException(503,"CLOUDINARY_IMAGE_INTERRUPTED","Tải ảnh đã bị gián đoạn.");}
        catch(Exception e){boolean timed=e instanceof TimeoutException||e.getCause() instanceof HttpTimeoutException;throw new ApiException(timed?504:502,timed?"CLOUDINARY_IMAGE_TIMEOUT":"CLOUDINARY_IMAGE_UNAVAILABLE",timed?"Tải ảnh Cloudinary quá thời gian.":"Không đọc được ảnh Cloudinary.");}
        finally{if(pending!=null&&!pending.isDone())pending.cancel(true);slots.release();}
    }
    static Image validate(byte[] bytes){
        if(bytes.length<3||bytes.length>LocalFileStore.MAX_BYTES)throw new ApiException(422,"INVALID_CLOUDINARY_IMAGE","Ảnh rỗng hoặc vượt giới hạn 10 MB.");
        String mime;
        if(bytes[0]==(byte)255&&bytes[1]==(byte)216&&bytes[2]==(byte)255)mime="image/jpeg";
        else if(bytes.length>=8&&Arrays.equals(Arrays.copyOf(bytes,8),new byte[]{(byte)137,80,78,71,13,10,26,10}))mime="image/png";
        else if(bytes.length>=12&&new String(bytes,0,4,java.nio.charset.StandardCharsets.US_ASCII).equals("RIFF")&&new String(bytes,8,4,java.nio.charset.StandardCharsets.US_ASCII).equals("WEBP"))mime="image/webp";
        else throw new ApiException(422,"INVALID_CLOUDINARY_IMAGE","Chỉ hỗ trợ ảnh JPEG, PNG và WebP hợp lệ.");
        try(var in=ImageIO.createImageInputStream(new ByteArrayInputStream(bytes))){
            var readers=ImageIO.getImageReaders(in);if(!readers.hasNext())throw new IOException();
            var reader=readers.next();
            try{reader.setInput(in,true,true);int w=reader.getWidth(0),h=reader.getHeight(0);
                if(w<1||h<1||w>12000||h>12000||(long)w*h>40000000||reader.read(0)==null)throw new IOException();
                return new Image(bytes,mime,w,h,HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)));
            }finally{reader.dispose();}
        }catch(Exception e){throw new ApiException(422,"INVALID_CLOUDINARY_IMAGE","Ảnh Cloudinary hỏng hoặc vượt giới hạn kích thước.");}
    }
}
