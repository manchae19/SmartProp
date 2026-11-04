package vn.smartprop.modules.broker;

import java.util.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.smartprop.modules.auth.*;
import vn.smartprop.modules.audit.*;
import vn.smartprop.common.*;
import vn.smartprop.config.*;
import vn.smartprop.modules.user.*;
import static vn.smartprop.modules.broker.BrokerApplicationDtos.*;

@Service
public class BrokerApplicationService {
    private final BrokerApplicationRepository applications;
    private final UserRepository users;
    private final SessionRepository sessions;
    private final AccountAccess access;
    private final BusinessAuditWriter audit;
    private final DomainEvents events;
    private final boolean enabled;
    public BrokerApplicationService(BrokerApplicationRepository applications,UserRepository users,SessionRepository sessions,
        AccountAccess access,BusinessAuditWriter audit,DomainEvents events,@Value("${app.broker-applications.enabled:false}") boolean enabled) {
        this.applications=applications;this.users=users;this.sessions=sessions;this.access=access;this.audit=audit;this.events=events;this.enabled=enabled;
    }
    private void ready() { if(!enabled)throw new ApiException(503,"FEATURE_DISABLED","Đăng ký quyền đăng tin chưa được bật; cần quản trị viên triển khai V13"); }
    private User activeLocked(Long actor) {
        User u=users.lockById(actor).orElseThrow(ApiInputs::forbidden);
        if(u.deletedAt!=null||u.status!=User.Status.ACTIVE)throw ApiInputs.forbidden();return u;
    }
    @Transactional(readOnly=true) public Mine mine(Long actor) {
        ready();User u=access.active(actor);View application=applications.byUser(actor).orElse(null);
        boolean publisher=u.role==User.Role.BROKER||u.role==User.Role.ADMIN;
        return new Mine(application==null?(publisher?"APPROVED":"NOT_REQUESTED"):application.status().name(),publisher,publisher&&application==null,application);
    }
    @Transactional public Mine submit(Long actor,Submit input) {
        ready();User u=activeLocked(actor);
        if(u.role!=User.Role.BUYER)throw ApiInputs.conflict("Tài khoản đã có quyền đăng tin");
        View previous=applications.byUserForUpdate(actor).orElse(null);
        if(previous==null&&input.expectedVersion()!=null)throw ApiInputs.conflict("Hồ sơ chưa tồn tại; hãy tải lại");
        if(previous!=null) {
            if(previous.status()!=Status.REJECTED&&previous.status()!=Status.NEEDS_INFORMATION)throw ApiInputs.conflict("Đã có yêu cầu hoặc quyền đang bị tạm ngưng; không gửi trùng");
            if(!Objects.equals(input.expectedVersion(),previous.contentVersion())||previous.contentVersion()==Integer.MAX_VALUE)throw ApiInputs.conflict("Hồ sơ đã thay đổi; hãy tải lại");
        }
        View result=applications.submit(actor,input,previous);
        // Audit stores statuses/version only, never application phone, message or tokens.
        audit.record(actor,"BROKER_APPLICATION",result.id(),"BROKER_APPLICATION_SUBMITTED",result.status().name(),result.contentVersion());
        return new Mine(result.status().name(),false,false,result);
    }
    @Transactional(readOnly=true) public PageResponse<View> queue(Long actor,Status status,int page,int size) { ready();access.admin(actor);return applications.queue(status,page,size); }
    @Transactional(readOnly=true) public View detail(Long actor,String id) { ready();access.admin(actor);return applications.byId(ApiInputs.uuid(id)); }
    public static Status next(Status status,Action action) {
        return switch(action) {
            case APPROVE -> {if(status!=Status.PENDING&&status!=Status.SUSPENDED)throw ApiInputs.conflict("Chỉ duyệt hồ sơ PENDING hoặc khôi phục SUSPENDED");yield Status.APPROVED;}
            case REJECT -> {if(status!=Status.PENDING)throw ApiInputs.conflict("Chỉ từ chối hồ sơ PENDING");yield Status.REJECTED;}
            case REQUEST_INFORMATION -> {if(status!=Status.PENDING)throw ApiInputs.conflict("Chỉ yêu cầu bổ sung hồ sơ PENDING");yield Status.NEEDS_INFORMATION;}
            case SUSPEND -> {if(status!=Status.APPROVED)throw ApiInputs.conflict("Chỉ tạm ngưng hồ sơ APPROVED");yield Status.SUSPENDED;}
        };
    }
    @Transactional public View review(Long actor,String id,Review input) {
        ready();String uuid=ApiInputs.uuid(id);
        // Same administrator -> target-user lock order as AdminService.status. Never locks an application before its user.
        var admins=users.lockAdministrators(User.Role.ADMIN);
        if(admins.stream().noneMatch(u->Objects.equals(u.id,actor)&&u.status==User.Status.ACTIVE&&u.deletedAt==null))throw ApiInputs.forbidden();
        View initial=applications.byId(uuid);User target=activeLocked(initial.userId());
        if(target.role==User.Role.ADMIN)throw ApiInputs.conflict("Không thay quyền quản trị bằng hồ sơ đăng tin");
        View current=applications.byUserForUpdate(target.id).orElseThrow(ApiInputs::missing);
        if(!Objects.equals(input.expectedVersion(),current.contentVersion())||current.contentVersion()==Integer.MAX_VALUE)throw ApiInputs.conflict("Hồ sơ đã thay đổi; hãy tải lại");
        Status after=next(current.status(),input.action());
        boolean grant=after==Status.APPROVED,revoke=after==Status.SUSPENDED;
        if(grant||revoke) {
            if(grant&&target.role!=User.Role.BUYER||revoke&&target.role!=User.Role.BROKER)throw ApiInputs.conflict("Quyền tài khoản không còn khớp hồ sơ");
            target.role=grant?User.Role.BROKER:User.Role.BUYER;
            target.tokenVersion=Math.incrementExact(target.tokenVersion);users.saveAndFlush(target);sessions.revokeAll(target.id);
        }
        View result=applications.review(current,actor,input,after);
        audit.record(actor,"BROKER_APPLICATION",uuid,"BROKER_APPLICATION_"+input.action().name(),after.name(),result.contentVersion());
        events.moderation(actor,null,target.id,null,"BROKER_"+input.action().name(),input.reason().strip(),current.status().name(),after.name(),target.id);
        return result;
    }
}
