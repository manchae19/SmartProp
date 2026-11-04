package vn.smartprop.modules.project;
import java.util.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.transaction.annotation.Transactional;
import vn.smartprop.common.*;
@RestController @RequestMapping("/api/v1/projects") @Transactional(readOnly=true)
public class ProjectController {
    public record View(String id,String name,String developer,Short handoverYear,String scale,String address,Double latitude,Double longitude,List<String> amenities) {}
    private final ProjectService projects;
    public ProjectController(ProjectService projects) {this.projects=projects;}
    public static View view(Project p) {List<String> a=new ArrayList<>();if(p.amenities!=null)p.amenities.forEach(n->a.add(n.asText()));return new View(p.id,p.name,p.developer,p.handoverYear,p.scale,p.address,p.location==null?null:p.location.getY(),p.location==null?null:p.location.getX(),List.copyOf(a));}
    @GetMapping public PageResponse<View> list(@RequestParam(defaultValue="0") int page,@RequestParam(defaultValue="20") int size) {return projects.list(page,size);}
    @GetMapping("/{id}") public View detail(@PathVariable String id) {return projects.detail(id);}
}