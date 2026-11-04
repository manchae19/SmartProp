package vn.smartprop.modules.audit;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.*;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
@Service
public class BusinessAuditWriter {
    private final AuditLogRepository audits;
    public BusinessAuditWriter(AuditLogRepository audits){this.audits=audits;}
    @Transactional(propagation=Propagation.MANDATORY)
    public void record(Long actor,String type,String id,String action,String status,int version){
        AuditLog log=new AuditLog();log.id=UUID.randomUUID().toString();log.actorId=actor;log.actorType=AuditLog.ActorType.USER;log.entityType=type;log.entityId=id;log.action=action;
        log.newValues=JsonNodeFactory.instance.objectNode().put("status",status).put("contentVersion",version);audits.save(log);
    }
}
