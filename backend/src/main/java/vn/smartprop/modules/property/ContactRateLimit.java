package vn.smartprop.modules.property;

import java.time.Clock;
import java.util.HashMap;
import java.util.Map;
import org.springframework.stereotype.Component;
import vn.smartprop.common.ApiException;

/** Single-instance, bounded fixed windows. Forwarded headers are deliberately not used. */
@Component
public class ContactRateLimit {
    private static final int USER_LIMIT=30, IP_LIMIT=120, CAPACITY=10_000;
    private static final long WINDOW_MILLIS=60_000;
    private final Clock clock;
    private final int userLimit, ipLimit, capacity;
    private final Map<Long,Window> users=new HashMap<>();
    private final Map<String,Window> ips=new HashMap<>();
    private long lastCleanup;
    private static final class Window {
        final long until;
        int count;
        Window(long until) { this.until=until; }
    }
    public static final class Exceeded extends ApiException {
        public final long retryAfter;
        Exceeded(long retryAfter) {
            super(429,"RATE_LIMITED","Bạn xem liên hệ quá nhanh; vui lòng thử lại sau.");
            this.retryAfter=retryAfter;
        }
    }
    public ContactRateLimit() { this(Clock.systemUTC(),USER_LIMIT,IP_LIMIT,CAPACITY); }
    ContactRateLimit(Clock clock,int userLimit,int ipLimit,int capacity) {
        this.clock=clock;this.userLimit=userLimit;this.ipLimit=ipLimit;this.capacity=capacity;
    }
    public synchronized void check(Long user,String ip) {
        long now=clock.millis();
        if(now-lastCleanup>=WINDOW_MILLIS || users.size()>=capacity || ips.size()>=capacity) {
            users.values().removeIf(w->w.until<=now);
            ips.values().removeIf(w->w.until<=now);
            lastCleanup=now;
        }
        Window u=users.get(user), i=ips.get(ip);
        if(u!=null && u.until<=now) {users.remove(user);u=null;}
        if(i!=null && i.until<=now) {ips.remove(ip);i=null;}
        long retry=0;
        if(u!=null && u.count>=userLimit) retry=Math.max(retry,u.until-now);
        if(i!=null && i.count>=ipLimit) retry=Math.max(retry,i.until-now);
        if((u==null && users.size()>=capacity) || (i==null && ips.size()>=capacity)) retry=Math.max(retry,WINDOW_MILLIS);
        if(retry>0) throw new Exceeded(Math.max(1,(retry+999)/1000));
        if(u==null) {u=new Window(now+WINDOW_MILLIS);users.put(user,u);}
        if(i==null) {i=new Window(now+WINDOW_MILLIS);ips.put(ip,i);}
        u.count++;i.count++;
    }
}
