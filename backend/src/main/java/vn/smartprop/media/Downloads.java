package vn.smartprop.media;
import org.springframework.http.*;
public final class Downloads {
    private Downloads() {}
    public static ResponseEntity<byte[]> response(byte[] bytes,String mime,String id) {
        String extension=switch(mime){case "image/png"->".png";case "image/jpeg"->".jpg";case "application/pdf"->".pdf";default->".bin";};
        return ResponseEntity.ok().contentType(MediaType.parseMediaType(mime)).contentLength(bytes.length)
            .header(HttpHeaders.CONTENT_DISPOSITION,ContentDisposition.attachment().filename(id+extension).build().toString())
            .header("X-Content-Type-Options","nosniff").header(HttpHeaders.CACHE_CONTROL,"private, no-store").body(bytes);
    }
}