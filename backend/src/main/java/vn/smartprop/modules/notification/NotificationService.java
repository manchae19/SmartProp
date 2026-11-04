package vn.smartprop.modules.notification;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.smartprop.modules.auth.AccountAccess;
import vn.smartprop.common.*;
@Service
public class NotificationService {
    private final NotificationRepository notifications;
    private final AccountAccess access;
    public NotificationService(NotificationRepository notifications,AccountAccess access) {this.notifications=notifications;this.access=access;}
    @Transactional(readOnly=true)
    public PageResponse<NotificationDtos.Item> inbox(Long actor,boolean unread,int page,int size) {
        access.active(actor);var pageable=ApiInputs.newest(page,size);
        var result=unread?notifications.findByUserIdAndReadAtIsNull(actor,pageable):notifications.findByUserId(actor,pageable);
        return PageResponse.of(result.map(NotificationDtos::view));
    }
    @Transactional(readOnly=true)
    public NotificationDtos.UnreadCount unreadCount(Long actor) {
        access.active(actor);return new NotificationDtos.UnreadCount(notifications.countByUserIdAndReadAtIsNull(actor));
    }
    @Transactional
    public NotificationDtos.Item read(Long actor,String id) {
        access.active(actor);String validId=ApiInputs.uuid(id);
        // Conditional update preserves the first readAt even under concurrent/retried requests.
        notifications.markRead(actor,validId,now());
        return NotificationDtos.view(notifications.findByIdAndUserId(validId,actor).orElseThrow(ApiInputs::missing));
    }
    @Transactional
    public NotificationDtos.ReadAll readAll(Long actor) {
        access.active(actor);Instant cutoff=now();
        return new NotificationDtos.ReadAll(notifications.markAllRead(actor,cutoff),cutoff);
    }
    private static Instant now() {return Instant.now().truncatedTo(ChronoUnit.MICROS);}
}
