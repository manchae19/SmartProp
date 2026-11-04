package vn.smartprop.modules.prediction;
import com.fasterxml.jackson.databind.*;
import java.net.*;
import java.net.http.*;
import java.nio.ByteBuffer;
import java.io.ByteArrayOutputStream;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.Flow;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import vn.smartprop.common.ApiException;
/** Fixed loopback peer; bounded response, whole-exchange deadline, no redirects/credentials. */
@Component
public class ValuationClient {
    private final URI base; private final ObjectMapper json; private final boolean enabled;
    private final HttpClient client=HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(1)).followRedirects(HttpClient.Redirect.NEVER).build();
    public ValuationClient(ObjectMapper json,@Value("${app.valuation.enabled:false}") boolean enabled,
        @Value("${app.valuation.base-url:http://127.0.0.1:8000}") String url){
        this.json=json;this.enabled=enabled;this.base=URI.create(url);
        if(!"http".equals(base.getScheme()) || !"127.0.0.1".equals(base.getHost()) || base.getUserInfo()!=null ||
            base.getQuery()!=null || base.getFragment()!=null || !(base.getPath().isEmpty()||base.getPath().equals("/")) || base.getPort()<1)
            throw new IllegalArgumentException("Valuation peer must be a fixed IPv4 loopback HTTP origin with an explicit port");
    }
    public JsonNode exchange(String path,Object payload){
        if(!enabled)throw unavailable();
        if(!Set.of("/model/options","/predict").contains(path))throw new IllegalArgumentException("Unknown model route");
        CompletableFuture<HttpResponse<byte[]>> pending=null;
        try {
            var request=HttpRequest.newBuilder(base.resolve(path)).timeout(Duration.ofSeconds(5)).header("Accept","application/json");
            if(payload==null)request.GET();else request.header("Content-Type","application/json").POST(HttpRequest.BodyPublishers.ofByteArray(json.writeValueAsBytes(payload)));
            pending=client.sendAsync(request.build(),info->new BoundedBody());
            var response=pending.get(5,TimeUnit.SECONDS);
            if(response.statusCode()!=200)throw unavailable();
            JsonNode body=json.readTree(response.body());
            if(body==null || !body.isObject())throw unavailable();
            return body;
        }catch(InterruptedException e){Thread.currentThread().interrupt();throw unavailable();}
        catch(Exception e){throw unavailable();}
        finally{if(pending!=null&&!pending.isDone())pending.cancel(true);}
    }
    static ApiException unavailable(){return new ApiException(503,"VALUATION_UNAVAILABLE","Giá tham khảo chưa sẵn sàng. Bạn vẫn có thể lưu hoặc gửi tin.");}
    static final class BoundedBody implements HttpResponse.BodySubscriber<byte[]> {
        final CompletableFuture<byte[]> body=new CompletableFuture<>();final ByteArrayOutputStream out=new ByteArrayOutputStream();Flow.Subscription subscription;
        public CompletionStage<byte[]> getBody(){return body;}
        public void onSubscribe(Flow.Subscription s){subscription=s;s.request(1);body.whenComplete((v,e)->{if(e!=null)s.cancel();});}
        public void onNext(List<ByteBuffer> buffers){for(var b:buffers){if(out.size()+b.remaining()>65536){subscription.cancel();body.completeExceptionally(new IllegalStateException("Model response exceeds bound"));return;}byte[] bytes=new byte[b.remaining()];b.get(bytes);out.writeBytes(bytes);}subscription.request(1);}
        public void onError(Throwable e){body.completeExceptionally(e);}
        public void onComplete(){body.complete(out.toByteArray());}
    }
}
