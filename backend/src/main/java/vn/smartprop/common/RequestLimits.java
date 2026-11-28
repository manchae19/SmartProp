package vn.smartprop.common;
import java.time.*;
import java.util.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
@Component
public class RequestLimits {
    /**
     * A limit was hit. `bucket` names the counter that refused, when the caller declared
     * one, so a caller can tell a one-second egress window from a daily quota. It is never
     * written to a response: the counter key can contain a client address.
     */
    public static final class Exceeded extends ApiException {
        public final long retryAfter;
        public final String bucket;
        public Exceeded(long retryAfter){this(retryAfter,null);}
        public Exceeded(long retryAfter,String bucket){super(429,"RATE_LIMITED","Please retry later");this.retryAfter=retryAfter;this.bucket=bucket;}
    }
    private record Window(long until,int count) {}
    private final Clock clock;
    public RequestLimits() { this(Clock.systemUTC()); }
    @Autowired public RequestLimits(Clock clock) { this.clock = clock; }
    private final Map<String,Window> values=new HashMap<>();
    public synchronized void check(String key,int maximum,int seconds){check(key,maximum,seconds,null);}
    public synchronized void check(String key,int maximum,int seconds,String bucket){long now=clock.millis();if(values.size()>=10000)values.values().removeIf(v->v.until<=now);var value=values.get(key);if(value!=null&&value.until<=now){values.remove(key);value=null;}if(value==null&&values.size()>=10000||value!=null&&value.count>=maximum)throw new Exceeded(value==null?seconds:Math.max(1,(value.until-now+999)/1000),bucket);values.put(key,new Window(value==null?now+seconds*1000L:value.until,value==null?1:value.count+1));}
}
