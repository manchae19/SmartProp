package vn.smartprop.audit;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.*;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import vn.smartprop.moderation.*;
import vn.smartprop.notification.*;
@Service
@Transactional(propagation=Propagation.MANDATORY)
public class DomainEvents {
    private final AuditLogRepository audits;private final ModerationActionRepository actions;private final NotificationRepository notifications;
    public DomainEvents(AuditLogRepository audits,ModerationActionRepository actions,NotificationRepository notifications) {this.audits=audits;this.actions=actions;this.notifications=notifications;}
    public void moderation(Long actor,String propertyId,Long userId,String reportId,String action,String reason,String before,String after,Long recipient) {
        ModerationAction m=new ModerationAction();m.id=UUID.randomUUID().toString();m.adminId=actor;m.propertyId=propertyId;m.userId=userId;m.reportId=reportId;
        m.action=action;m.reason=reason;m.previousStatus=before;m.newStatus=after;actions.save(m);
        AuditLog audit=new AuditLog();audit.id=UUID.randomUUID().toString();audit.actorId=actor;audit.actorType=AuditLog.ActorType.USER;audit.action=action;
        audit.entityType=reportId!=null?"REPORT":userId!=null?"USER":"PROPERTY";audit.entityId=reportId!=null?reportId:propertyId;audit.entityNumericId=userId;
        audit.oldValues=JsonNodeFactory.instance.objectNode().put("status",before);audit.newValues=JsonNodeFactory.instance.objectNode().put("status",after);audits.save(audit);
        if(recipient!=null) {Notification n=new Notification();n.id=UUID.randomUUID().toString();n.userId=recipient;n.kind="STATUS_UPDATE";n.title="Cập nhật trạng thái";
            n.body="Trạng thái mới: "+after;n.propertyId=propertyId;n.reportId=reportId;n.dedupeKey="moderation:"+m.id;notifications.save(n);}
    }
}