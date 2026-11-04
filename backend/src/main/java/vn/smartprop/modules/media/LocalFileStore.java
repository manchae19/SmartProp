package vn.smartprop.modules.media;
import java.io.*;
import java.nio.file.*;
import java.nio.channels.Channels;
import java.security.*;
import java.util.*;
import javax.imageio.ImageIO;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.*;
import org.springframework.web.multipart.MultipartFile;
import vn.smartprop.common.*;
@Component
public class LocalFileStore {
    public static final long MAX_BYTES=10L*1024*1024;
    private final Path root;
    public LocalFileStore(@Value("${app.storage-root:./var/uploads}") String root) {this.root=Path.of(root).toAbsolutePath().normalize();}
    public record Validated(byte[] bytes,String mimeType,String originalFilename,Integer width,Integer height,String sha256) {}
    public record Stored(String key,Validated file) {}
    public Validated validate(MultipartFile input,boolean allowPdf) {
        if(input==null || input.isEmpty())throw ApiInputs.bad("Tệp không được rỗng");
        if(input.getSize()>MAX_BYTES)throw new ApiException(413,"PAYLOAD_TOO_LARGE","Tệp tối đa 10MB");
        try(InputStream in=input.getInputStream()) {
            byte[] bytes=in.readNBytes((int)MAX_BYTES+1);if(bytes.length>MAX_BYTES)throw new ApiException(413,"PAYLOAD_TOO_LARGE","Tệp tối đa 10MB");
            String mime;Integer width=null,height=null;
            boolean png=bytes.length>=8 && Arrays.equals(Arrays.copyOf(bytes,8),new byte[]{(byte)137,80,78,71,13,10,26,10});
            boolean jpeg=bytes.length>=3 && bytes[0]==(byte)255 && bytes[1]==(byte)216 && bytes[2]==(byte)255;
            boolean pdf=allowPdf && bytes.length>=12 && new String(bytes,0,5,java.nio.charset.StandardCharsets.US_ASCII).equals("%PDF-") && new String(bytes,Math.max(0,bytes.length-1024),Math.min(1024,bytes.length),java.nio.charset.StandardCharsets.ISO_8859_1).contains("%%EOF");
            if(png || jpeg) {
                mime=png?"image/png":"image/jpeg";
                try(var imageInput=ImageIO.createImageInputStream(new ByteArrayInputStream(bytes))) {
                    var readers=ImageIO.getImageReaders(imageInput);if(!readers.hasNext())throw ApiInputs.bad("Ảnh không hợp lệ");
                    var reader=readers.next();try {reader.setInput(imageInput,true,true);width=reader.getWidth(0);height=reader.getHeight(0);
                        if(width<1||height<1||width>12000||height>12000||(long)width*height>40000000)throw ApiInputs.bad("Ảnh vượt giới hạn kích thước/pixel");
                        if(reader.read(0)==null)throw ApiInputs.bad("Không giải mã được ảnh");
                    } finally {reader.dispose();}
                }
            } else if(pdf) mime="application/pdf";
            else throw ApiInputs.bad(allowPdf?"Chỉ nhận JPEG/PNG/PDF hợp lệ":"Chỉ nhận ảnh JPEG/PNG hợp lệ");
            String name=Optional.ofNullable(input.getOriginalFilename()).orElse("upload").replace('\\','/');
            name=name.substring(name.lastIndexOf('/')+1).replaceAll("[\\p{Cntrl}]","");if(name.length()>255)name=name.substring(name.length()-255);
            String hash=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
            return new Validated(bytes,mime,name,width,height,hash);
        } catch(IOException e) {throw ApiInputs.bad("Tệp không đọc/giải mã được");}
        catch(NoSuchAlgorithmException e) {throw new IllegalStateException("SHA-256 unavailable",e);}
    }
    public Stored store(Validated file) {
        String key=UUID.randomUUID().toString().replace("-","")+".bin";Path target=root.resolve(key);boolean created=false;
        try {
            Files.createDirectories(root);if(Files.isSymbolicLink(root))throw new IOException("Symlink storage root");
            try(var output=Files.newOutputStream(target,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE)) {created=true;output.write(file.bytes());}
            if(TransactionSynchronizationManager.isSynchronizationActive())TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                @Override public void afterCompletion(int status) {if(status!=STATUS_COMMITTED)try{Files.deleteIfExists(target);}catch(IOException e){org.slf4j.LoggerFactory.getLogger(LocalFileStore.class).warn("Rollback file cleanup failed");}}
            });
            return new Stored(key,file);
        } catch(IOException e) {
            if(created)try{Files.deleteIfExists(target);}catch(IOException ignored){org.slf4j.LoggerFactory.getLogger(LocalFileStore.class).warn("Partial file cleanup failed");}
            throw new ApiException(503,"STORAGE_UNAVAILABLE","Không lưu được tệp; vui lòng thử lại");
        }
    }
    public byte[] read(String key) {
        if(key==null || !key.matches("[a-f0-9]{32}\\.bin"))throw ApiInputs.missing();
        Path target=root.resolve(key).normalize();if(!target.startsWith(root)||Files.isSymbolicLink(root)||Files.isSymbolicLink(target))throw ApiInputs.missing();
        try(var channel=Files.newByteChannel(target,Set.of(StandardOpenOption.READ,LinkOption.NOFOLLOW_LINKS));var in=Channels.newInputStream(channel)) {
            byte[] bytes=in.readNBytes((int)MAX_BYTES+1);if(bytes.length>MAX_BYTES)throw ApiInputs.missing();return bytes;
        } catch(IOException e) {throw ApiInputs.missing();}
    }
}