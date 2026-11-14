package vn.smartprop.modules.notification;
import java.time.Instant;
public final class NotificationDtos {
    private NotificationDtos() {}
    public record Item(String id,String kind,String title,String body,String propertyId,String reportId,Instant readAt,Instant createdAt) {}
    public record UnreadCount(long count) {}
    public record ReadAll(int updatedCount,Instant cutoff) {}
    public static Item view(Notification n) {return new Item(n.id,n.kind,n.title,n.body,n.propertyId,n.reportId,n.readAt,n.createdAt);}
}
