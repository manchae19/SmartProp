package vn.smartprop.modules.auth;

import java.time.*;
import org.springframework.stereotype.Component;
import vn.smartprop.modules.user.User;

/** Existing expires_at is an absolute bound, never extended by rotation. */
@Component
public class SessionPolicy {
    private final Clock clock;
    public SessionPolicy(Clock clock){this.clock=clock;}
    public Instant now(){return clock.instant();}
    public Duration lifetime(User.Role role,boolean remember){return role==User.Role.ADMIN?Duration.ofHours(8):Duration.ofDays(remember?30:7);}
    public Instant absoluteExpiry(AuthSession session,User user){
        Instant max=session.createdAt.plus(user.role==User.Role.ADMIN?Duration.ofHours(8):Duration.ofDays(30));
        return session.expiresAt.isBefore(max)?session.expiresAt:max;
    }
    public boolean valid(AuthSession session,User user){
        Instant now=now();if(session.revoked||!absoluteExpiry(session,user).isAfter(now))return false;
        Instant activity=session.lastUsedAt==null?session.createdAt:session.lastUsedAt;
        return user.role!=User.Role.ADMIN||activity.plus(Duration.ofMinutes(30)).isAfter(now);
    }
    public long remaining(AuthSession session,User user){return Math.max(0,Duration.between(now(),absoluteExpiry(session,user)).getSeconds());}
}
