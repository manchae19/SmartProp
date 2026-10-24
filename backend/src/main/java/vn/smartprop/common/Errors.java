package vn.smartprop.common;
import java.time.Instant;
import java.util.*;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.dao.DataIntegrityViolationException;
@RestControllerAdvice
public class Errors {
    public record Body(String code,String message,Map<String,String> fields,Instant timestamp) {}
    public static Body body(String code,String message) { return new Body(code,message,Map.of(),Instant.now()); }
    @ExceptionHandler(ApiException.class)
    ResponseEntity<Body> api(ApiException e) { var response=ResponseEntity.status(e.status);if(e instanceof RequestLimits.Exceeded limited)response.header("Retry-After",Long.toString(limited.retryAfter));return response.body(body(e.code,e.getMessage())); }
    @ExceptionHandler(MethodArgumentNotValidException.class)
    ResponseEntity<Body> validation(MethodArgumentNotValidException e) {
        Map<String,String> fields=new LinkedHashMap<>();
        e.getBindingResult().getFieldErrors().forEach(f -> fields.putIfAbsent(f.getField(),f.getDefaultMessage()));
        return ResponseEntity.badRequest().body(new Body("VALIDATION_ERROR","Dữ liệu không hợp lệ",fields,Instant.now()));
    }
    @ExceptionHandler(HttpMessageNotReadableException.class)
    ResponseEntity<Body> json() { return ResponseEntity.badRequest().body(body("INVALID_REQUEST","JSON hoặc trường gửi lên không hợp lệ")); }
    @ExceptionHandler(DataIntegrityViolationException.class)
    ResponseEntity<Body> conflict() { return ResponseEntity.status(409).body(body("CONFLICT","Dữ liệu đã tồn tại hoặc xung đột")); }
    @ExceptionHandler(org.springframework.web.HttpRequestMethodNotSupportedException.class)
    ResponseEntity<Body> method(org.springframework.web.HttpRequestMethodNotSupportedException e) {
        HttpHeaders headers=new HttpHeaders();
        if(e.getSupportedHttpMethods()!=null) headers.setAllow(e.getSupportedHttpMethods());
        return new ResponseEntity<>(body("METHOD_NOT_ALLOWED","Phương thức không được hỗ trợ"),headers,HttpStatus.METHOD_NOT_ALLOWED);
    }
    @ExceptionHandler(org.springframework.web.HttpMediaTypeNotSupportedException.class)
    ResponseEntity<Body> media() { return ResponseEntity.status(415).body(body("UNSUPPORTED_MEDIA_TYPE","Kiểu nội dung không được hỗ trợ")); }
    @ExceptionHandler(org.springframework.web.multipart.MaxUploadSizeExceededException.class)
    ResponseEntity<Body> upload() { return ResponseEntity.status(413).body(body("PAYLOAD_TOO_LARGE","Tệp tải lên vượt giới hạn cho phép")); }
    @ExceptionHandler({org.springframework.web.bind.MissingServletRequestParameterException.class,
        org.springframework.web.method.annotation.MethodArgumentTypeMismatchException.class})
    ResponseEntity<Body> parameter() { return ResponseEntity.badRequest().body(body("INVALID_REQUEST","Tham số không hợp lệ")); }
    @ExceptionHandler(org.springframework.web.servlet.resource.NoResourceFoundException.class)
    ResponseEntity<Body> resource() { return ResponseEntity.status(404).body(body("NOT_FOUND","Không tìm thấy tài nguyên")); }
    @ExceptionHandler({org.springframework.web.multipart.support.MissingServletRequestPartException.class,
        org.springframework.web.multipart.MultipartException.class})
    ResponseEntity<Body> multipart() { return ResponseEntity.badRequest().body(body("INVALID_REQUEST","Tệp hoặc multipart request không hợp lệ")); }
    @ExceptionHandler(Exception.class)
    ResponseEntity<Body> unexpected(Exception e) {
        org.slf4j.LoggerFactory.getLogger(Errors.class).error("Unhandled API error type: {}", e.getClass().getName());
        return ResponseEntity.internalServerError().body(body("INTERNAL_ERROR","Không thể xử lý yêu cầu"));
    }
}
