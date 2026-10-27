package vn.smartprop.project;
import java.util.*;
import com.fasterxml.jackson.databind.*;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import org.locationtech.jts.geom.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.smartprop.auth.AccountAccess;
import vn.smartprop.audit.BusinessAuditWriter;
import vn.smartprop.common.*;
@Service
@Transactional(readOnly=true)
public class ProjectService {
    private final ProjectRepository projects;private final ProjectManagementRepository lifecycle;private final AccountAccess access;private final BusinessAuditWriter audit;
    public record Managed(ProjectController.View project,int contentVersion,java.time.Instant deletedAt,java.time.Instant createdAt,java.time.Instant updatedAt) {}
    public ProjectService(ProjectRepository projects,ProjectManagementRepository lifecycle,AccountAccess access,BusinessAuditWriter audit){this.projects=projects;this.lifecycle=lifecycle;this.access=access;this.audit=audit;}
    private Project existing(String id){return projects.findById(ApiInputs.uuid(id)).orElseThrow(ApiInputs::missing);}
    private Managed view(Project p,ProjectManagementRepository.State s){return new Managed(ProjectController.view(p),s.version(),s.deletedAt(),p.createdAt,p.updatedAt);}
    private org.springframework.data.domain.Page<Project> selected(boolean archived,int page,int size){var states=lifecycle.page(archived,page,size);var byId=new HashMap<String,Project>();projects.findAllById(states.stream().map(ProjectManagementRepository.State::id).toList()).forEach(p->byId.put(p.id,p));return new org.springframework.data.domain.PageImpl<>(states.stream().map(s->byId.get(s.id())).filter(Objects::nonNull).toList(),ApiInputs.newest(page,size),lifecycle.count(archived));}
    public PageResponse<ProjectController.View> list(int page,int size){return PageResponse.of((lifecycle.enabled()?selected(false,page,size):projects.findAll(ApiInputs.newest(page,size))).map(ProjectController::view));}
    public ProjectController.View detail(String id){id=ApiInputs.uuid(id);lifecycle.publicVisible(id);return ProjectController.view(existing(id));}
    public PageResponse<Managed> adminList(Long actor,boolean archived,int page,int size){access.admin(actor);return PageResponse.of(selected(archived,page,size).map(p->view(p,lifecycle.state(p.id,false))));}
    public Managed adminDetail(Long actor,String id){access.admin(actor);lifecycle.requireEnabled();var p=existing(id);return view(p,lifecycle.state(p.id,false));}
    @Transactional public Managed create(Long actor,JsonNode body){access.admin(actor);lifecycle.requireEnabled();Project p=new Project();p.id=UUID.randomUUID().toString();p.amenities=JsonNodeFactory.instance.arrayNode();fill(p,body,true);projects.saveAndFlush(p);audit.record(actor,"PROJECT",p.id,"PROJECT_CREATED","ACTIVE",1);return view(p,lifecycle.state(p.id,false));}
    @Transactional public Managed patch(Long actor,String id,int expected,JsonNode body){access.admin(actor);lifecycle.requireEnabled();id=ApiInputs.uuid(id);var s=lifecycle.state(id,true);if(s.deletedAt()!=null)throw ApiInputs.conflict("Project is archived");lifecycle.reserve(id,expected,false);Project p=existing(id);fill(p,body,false);projects.saveAndFlush(p);audit.record(actor,"PROJECT",id,"PROJECT_UPDATED","ACTIVE",expected+1);return view(p,lifecycle.state(id,false));}
    @Transactional public void archive(Long actor,String id,int expected){access.admin(actor);id=ApiInputs.uuid(id);lifecycle.state(id,true);lifecycle.reserve(id,expected,true);audit.record(actor,"PROJECT",id,"PROJECT_ARCHIVED","ARCHIVED",expected+1);}
    private String text(JsonNode b,String key,int max,boolean required){JsonNode n=b.get(key);if(n==null || n.isNull()){if(required)throw ApiInputs.bad(key+" is required");return null;}if(!n.isTextual())throw ApiInputs.bad(key+" must be text");String s=n.asText().strip();if(s.length()>max || required&&s.isBlank())throw ApiInputs.bad("Invalid "+key);return s.isEmpty()?null:s;}
    private void fill(Project p,JsonNode b,boolean create){
        Set<String> fields=Set.of("name","developer","handoverYear","scale","address","latitude","longitude","amenities");if(b==null||!b.isObject())throw ApiInputs.bad("Expected object");b.fieldNames().forEachRemaining(k->{if(!fields.contains(k))throw ApiInputs.bad("Unknown project field");});
        if(create||b.has("name"))p.name=text(b,"name",255,true);if(b.has("developer"))p.developer=text(b,"developer",255,false);if(b.has("scale"))p.scale=text(b,"scale",4000,false);if(b.has("address"))p.address=text(b,"address",4000,false);
        if(b.has("handoverYear")){var n=b.get("handoverYear");if(n.isNull())p.handoverYear=null;else {if(!n.isIntegralNumber()||!n.canConvertToInt()||n.intValue()<1900||n.intValue()>2200)throw ApiInputs.bad("Invalid handoverYear");p.handoverYear=(short)n.intValue();}}
        if(b.has("latitude")||b.has("longitude")){if(!b.has("latitude")||!b.has("longitude"))throw ApiInputs.bad("Both coordinates required");var lat=b.get("latitude");var lon=b.get("longitude");if(lat.isNull()&&lon.isNull())p.location=null;else{if(!lat.isNumber()||!lon.isNumber()||!Double.isFinite(lat.doubleValue())||!Double.isFinite(lon.doubleValue())||lat.doubleValue()< -90||lat.doubleValue()>90||lon.doubleValue()<= -180||lon.doubleValue()>180)throw ApiInputs.bad("Invalid coordinates");p.location=new GeometryFactory(new PrecisionModel(),4326).createPoint(new Coordinate(lon.doubleValue(),lat.doubleValue()));}}
        if(b.has("amenities")){var a=b.get("amenities");if(!a.isArray()||a.size()>100)throw ApiInputs.bad("Invalid amenities");var values=new LinkedHashSet<String>();for(var n:a){if(!n.isTextual()||n.asText().isBlank()||n.asText().strip().length()>150)throw ApiInputs.bad("Invalid amenity");values.add(n.asText().strip());}var result=JsonNodeFactory.instance.arrayNode();values.forEach(result::add);p.amenities=result;}
    }
}
