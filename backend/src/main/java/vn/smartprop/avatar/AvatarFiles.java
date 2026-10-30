package vn.smartprop.avatar;

import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.*;
import java.nio.file.*;
import java.security.*;
import java.util.*;
import javax.imageio.ImageIO;
import javax.imageio.stream.MemoryCacheImageInputStream;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.*;
import org.springframework.web.multipart.MultipartFile;
import vn.smartprop.common.*;
import vn.smartprop.media.LocalFileStore;

/** Avatars have their own directory; property/report storage cleanup never scans it. */
@Component
public class AvatarFiles {
    public static final int MAX_BYTES=5*1024*1024;
    private final Path root;
    private final LocalFileStore files;
    public AvatarFiles(@Value("${app.storage-root:./var/uploads}") String storage){root=Path.of(storage).toAbsolutePath().normalize().resolve("avatars");files=new LocalFileStore(root.toString());}
    private void safeRoot(){for(Path p=root;p!=null;p=p.getParent())if(Files.isSymbolicLink(p))throw new ApiException(503,"STORAGE_UNAVAILABLE","Không thể truy cập ảnh đại diện.");}
    public LocalFileStore.Validated validate(MultipartFile input){
        if(input==null||input.isEmpty())throw ApiInputs.bad("Vui lòng chọn ảnh đại diện.");
        if(input.getSize()>MAX_BYTES)throw new ApiException(413,"PAYLOAD_TOO_LARGE","Ảnh đại diện tối đa 5 MB.");
        try(var in=input.getInputStream()){
            byte[] bytes=in.readNBytes(MAX_BYTES+1);if(bytes.length>MAX_BYTES)throw new ApiException(413,"PAYLOAD_TOO_LARGE","Ảnh đại diện tối đa 5 MB.");
            boolean png=bytes.length>=8&&Arrays.equals(Arrays.copyOf(bytes,8),new byte[]{(byte)137,80,78,71,13,10,26,10});
            boolean jpeg=bytes.length>=3&&bytes[0]==(byte)255&&bytes[1]==(byte)216&&bytes[2]==(byte)255;
            boolean webp=bytes.length>=12&&new String(bytes,0,4,java.nio.charset.StandardCharsets.US_ASCII).equals("RIFF")&&new String(bytes,8,4,java.nio.charset.StandardCharsets.US_ASCII).equals("WEBP");
            String mime=png?"image/png":jpeg?"image/jpeg":webp?"image/webp":null;
            if(mime==null||input.getContentType()!=null&&!mime.equalsIgnoreCase(input.getContentType()))throw ApiInputs.bad("Chỉ nhận ảnh JPEG, PNG hoặc WebP hợp lệ.");
            BufferedImage source;
            try(var stream=new MemoryCacheImageInputStream(new ByteArrayInputStream(bytes))){
                var readers=ImageIO.getImageReaders(stream);if(!readers.hasNext())throw ApiInputs.bad("Không đọc được định dạng ảnh.");
                var reader=readers.next();try{reader.setInput(stream,true,true);int w=reader.getWidth(0),h=reader.getHeight(0);
                    if(w<64||h<64||w>4096||h>4096||(long)w*h>16000000)throw ApiInputs.bad("Chọn ảnh từ 64 đến 4096 pixel mỗi chiều, tối đa 16 triệu pixel.");
                    source=reader.read(0);if(source==null)throw ApiInputs.bad("Ảnh bị hỏng hoặc không giải mã được.");
                }finally{reader.dispose();}
            }
            int size=Math.min(512,Math.min(source.getWidth(),source.getHeight())),crop=Math.min(source.getWidth(),source.getHeight()),x=(source.getWidth()-crop)/2,y=(source.getHeight()-crop)/2;
            var clean=new BufferedImage(size,size,BufferedImage.TYPE_INT_ARGB);Graphics2D g=clean.createGraphics();
            try{g.setRenderingHint(RenderingHints.KEY_INTERPOLATION,RenderingHints.VALUE_INTERPOLATION_BICUBIC);g.drawImage(source,0,0,size,size,x,y,x+crop,y+crop,null);}finally{g.dispose();source.flush();}
            var output=new ByteArrayOutputStream();if(!ImageIO.write(clean,"png",output))throw ApiInputs.bad("Không xử lý được ảnh.");clean.flush();
            byte[] result=output.toByteArray();String sha=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(result));
            // Re-encoding strips metadata, executable trailers and original filenames.
            return new LocalFileStore.Validated(result,"image/png","avatar.png",size,size,sha);
        }catch(IOException|IllegalArgumentException e){throw ApiInputs.bad("Ảnh bị hỏng hoặc không đọc được.");}catch(NoSuchAlgorithmException e){throw new IllegalStateException(e);}
    }
    public LocalFileStore.Stored store(LocalFileStore.Validated image){safeRoot();return files.store(image);}
    public byte[] read(String key){safeRoot();return files.read(key);}
    public void removeAfterCommit(String key){
        if(key==null||!key.matches("[a-f0-9]{32}\\.bin"))return;
        Runnable remove=()->{safeRoot();try{Files.deleteIfExists(root.resolve(key));}catch(IOException e){org.slf4j.LoggerFactory.getLogger(AvatarFiles.class).warn("Deferred avatar cleanup required");}};
        if(TransactionSynchronizationManager.isSynchronizationActive())TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization(){@Override public void afterCommit(){remove.run();}});else remove.run();
    }
}
