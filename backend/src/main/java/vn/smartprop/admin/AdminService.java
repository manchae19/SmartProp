package vn.smartprop.admin;
import java.time.Instant;
import java.util.*;
import jakarta.validation.constraints.*;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.data.jpa.domain.Specification;
import vn.smartprop.common.*;
import vn.smartprop.auth.*;
import vn.smartprop.user.*;
import vn.smartprop.property.*;
import vn.smartprop.report.*;
import vn.smartprop.audit.*;
@Service
public class AdminService {
    public record StatusPatch(@NotNull User.Status status,@NotBlank @Size(max=4000) String reason) {}
    public record UserView(Long id,String email,String fullName,User.Role role,User.Status status,Instant lockedAt,String lockReason,Instant createdAt,Instant updatedAt) {}
    public record AuditView(String id,Long actorId,AuditLog.ActorType actorType,String action,String entityType,String entityId,Long entityNumericId,JsonNode oldValues,JsonNode newValues,Instant createdAt) {}
    private final UserRepository users;private final PropertyRepository properties;private final ReportRepository reports;private final AuditLogRepository audits;
    private final SessionRepository sessions;private final AccountAccess access;private final DomainEvents events;
    public AdminService(UserRepository users,PropertyRepository properties,ReportRepository reports,AuditLogRepository audits,SessionRepository sessions,AccountAccess access,DomainEvents events) {
        this.users=users;this.properties=properties;this.reports=reports;this.audits=audits;this.sessions=sessions;this.access=access;this.events=events;
    }
    private UserView view(User u) {return new UserView(u.id,u.email,u.fullName,u.role,u.status,u.lockedAt,u.lockReason,u.createdAt,u.updatedAt);}
    @Transactional(readOnly=true) public PageResponse<UserView> users(Long actor,User.Status status,User.Role role,String keyword,int page,int size) {
        access.admin(actor);if(keyword!=null&&keyword.length()>100)throw ApiInputs.bad("keyword tối đa100 ký tự");
        Specification<User> filter=(r,q,cb)->{
            var predicates=new ArrayList<jakarta.persistence.criteria.Predicate>();predicates.add(cb.isNull(r.get("deletedAt")));
            if(status!=null)predicates.add(cb.equal(r.get("status"),status));if(role!=null)predicates.add(cb.equal(r.get("role"),role));
            if(keyword!=null&&!keyword.isBlank()){String term=ApiInputs.like(keyword.strip().toLowerCase(Locale.ROOT));predicates.add(cb.or(cb.like(cb.lower(r.get("email")),term,'\\'),cb.like(cb.lower(r.get("fullName")),term,'\\')));}
            return cb.and(predicates.toArray(jakarta.persistence.criteria.Predicate[]::new));
        };
        return PageResponse.of(users.findAll(filter,ApiInputs.newest(page,size)).map(this::view));
    }
    @Transactional public UserView status(Long actor,Long id,StatusPatch input) {
        if(id==null||id<1)throw ApiInputs.bad("ID người dùng không hợp lệ");
        // Deterministic row locks serialize the last-admin invariant and revalidate the caller after waiting.
        List<User> administrators=users.lockAdministrators(User.Role.ADMIN);
        User caller=administrators.stream().filter(u->Objects.equals(u.id,actor)&&u.deletedAt==null&&u.status==User.Status.ACTIVE).findFirst().orElseThrow(ApiInputs::forbidden);
        User target=administrators.stream().filter(u->Objects.equals(u.id,id)).findFirst().orElseGet(()->users.lockById(id).orElseThrow(ApiInputs::missing));
        if(target.deletedAt!=null)throw ApiInputs.missing();
        if(input.status()==User.Status.LOCKED&&Objects.equals(caller.id,target.id))throw ApiInputs.conflict("Không thể tự khóa tài khoản quản trị");
        if(target.status==input.status())return view(target);
        if(input.status()==User.Status.LOCKED&&target.role==User.Role.ADMIN&&administrators.stream().filter(u->u.deletedAt==null&&u.status==User.Status.ACTIVE).count()<=1)throw ApiInputs.conflict("Không thể khóa quản trị viên hoạt động cuối cùng");
        String before=target.status.name();target.tokenVersion=Math.incrementExact(target.tokenVersion);target.status=input.status();
        target.lockedAt=target.status==User.Status.LOCKED?Instant.now():null;target.lockReason=target.status==User.Status.LOCKED?input.reason().strip():null;
        users.saveAndFlush(target);sessions.revokeAll(target.id);
        events.moderation(actor,null,target.id,null,"USER_"+target.status.name(),input.reason().strip(),before,target.status.name(),target.id);return view(target);
    }
    private Specification<User> userStatus(User.Status status) {return (r,q,cb)->status==null?cb.isNull(r.get("deletedAt")):cb.and(cb.isNull(r.get("deletedAt")),cb.equal(r.get("status"),status));}
    private Specification<Property> propertyStatus(Property.Status status) {return (r,q,cb)->status==null?cb.isNull(r.get("deletedAt")):cb.and(cb.isNull(r.get("deletedAt")),cb.equal(r.get("status"),status));}
    @Transactional(readOnly=true) public Map<String,Long> dashboard(Long actor) {
        access.admin(actor);var none=new PropertySearch.Filters(null,null,null,null,null,null,null,null,null,null,null,null);
        return Map.of("users",users.count(userStatus(null)),"activeUsers",users.count(userStatus(User.Status.ACTIVE)),"lockedUsers",users.count(userStatus(User.Status.LOCKED)),
            "properties",properties.count(propertyStatus(null)),"pendingProperties",properties.count(propertyStatus(Property.Status.PENDING)),"publishedProperties",properties.count(PropertySearch.specification(none,Instant.now())),
            "openReports",reports.countByStatus(Report.Status.OPEN),"processingReports",reports.countByStatus(Report.Status.PROCESSING),"resolvedReports",reports.countByStatus(Report.Status.RESOLVED),"rejectedReports",reports.countByStatus(Report.Status.REJECTED));
    }
    private JsonNode safeValues(JsonNode input) {
        var out=JsonNodeFactory.instance.objectNode();Set<String> states=Set.of("ACTIVE","LOCKED","DRAFT","PENDING","PUBLISHED","REJECTED","HIDDEN","EXPIRED","CLOSED","OPEN","PROCESSING","RESOLVED","ARCHIVED","VERIFIED");
        if(input!=null&&input.path("status").isTextual()&&states.contains(input.path("status").asText()))out.put("status",input.path("status").asText());return out;
    }
    @Transactional(readOnly=true) public PageResponse<AuditView> audit(Long actor,String entityType,Long actorId,String action,int page,int size) {
        access.admin(actor);Set<String> types=Set.of("USER","PROPERTY","REPORT","PROJECT","LEGAL_DOCUMENT");if(entityType!=null&&!types.contains(entityType))throw ApiInputs.bad("entityType phải là USER/PROPERTY/REPORT");
        if(action!=null&&action.length()>100||actorId!=null&&actorId<1)throw ApiInputs.bad("Bộ lọc audit không hợp lệ");
        Specification<AuditLog> filter=(r,q,cb)->{
            var predicates=new ArrayList<jakarta.persistence.criteria.Predicate>();predicates.add(entityType==null?r.get("entityType").in(types):cb.equal(r.get("entityType"),entityType));
            if(actorId!=null)predicates.add(cb.equal(r.get("actorId"),actorId));if(action!=null)predicates.add(cb.equal(r.get("action"),action));return cb.and(predicates.toArray(jakarta.persistence.criteria.Predicate[]::new));
        };
        return PageResponse.of(audits.findAll(filter,ApiInputs.newest(page,size)).map(a->new AuditView(a.id,a.actorId,a.actorType,a.action,a.entityType,a.entityId,a.entityNumericId,safeValues(a.oldValues),safeValues(a.newValues),a.createdAt)));
    }
}