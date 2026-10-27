package vn.smartprop.common;
import java.time.*;
import java.util.*;
import org.springframework.stereotype.Component;
@Component
public class RequestLimits {
    public static final class Exceeded extends ApiException { public final long retryAfter;public Exceeded(long retryAfter){super(429,"RATE_LIMITED","Please retry later");this.retryAfter=retryAfter;} }
    private record Window(long until,int count) {}
    private final Map<String,Window> values=new HashMap<>();
    public synchronized void check(String key,int maximum,int seconds){long now=System.currentTimeMillis();if(values.size()>=10000)values.values().removeIf(v->v.until<=now);var value=values.get(key);if(value!=null&&value.until<=now){values.remove(key);value=null;}if(value==null&&values.size()>=10000||value!=null&&value.count>=maximum)throw new Exceeded(value==null?seconds:Math.max(1,(value.until-now+999)/1000));values.put(key,new Window(value==null?now+seconds*1000L:value.until,value==null?1:value.count+1));}
}
