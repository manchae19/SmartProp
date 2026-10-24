package vn.smartprop.project;
import java.time.Instant;
import java.util.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import vn.smartprop.common.*;
@Repository
public class ProjectManagementRepository {
    private final JdbcTemplate jdbc;
    private final boolean enabled;public boolean enabled(){return enabled;}
    public record State(String id,int version,Instant deletedAt) {}
    public ProjectManagementRepository(JdbcTemplate jdbc,@Value("${app.projects-management.enabled:false}") boolean enabled){this.jdbc=jdbc;this.enabled=enabled;}
    public void requireEnabled(){if(!enabled)throw new ApiException(503,"FEATURE_DISABLED","Projects management is disabled");}
    public State state(String id,boolean lock){requireEnabled();return jdbc.query("SELECT id,content_version,deleted_at FROM projects WHERE id=?"+(lock?" FOR UPDATE":""),(r,n)->new State(r.getString(1),r.getInt(2),r.getTimestamp(3)==null?null:r.getTimestamp(3).toInstant()),id).stream().findFirst().orElseThrow(ApiInputs::missing);}
    public void publicVisible(String id){if(enabled && state(id,false).deletedAt()!=null)throw ApiInputs.missing();}
    public void linkable(String id,String previous){if(enabled && !Objects.equals(id,previous) && state(id,true).deletedAt()!=null)throw ApiInputs.bad("Project is archived");}
    public List<State> page(boolean archived,int page,int size){requireEnabled();ApiInputs.newest(page,size);return jdbc.query("SELECT id,content_version,deleted_at FROM projects WHERE deleted_at IS "+(archived?"NOT ":"")+"NULL ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?",(r,n)->new State(r.getString(1),r.getInt(2),r.getTimestamp(3)==null?null:r.getTimestamp(3).toInstant()),size,(long)page*size);}
    public long count(boolean archived){requireEnabled();return jdbc.queryForObject("SELECT COUNT(*) FROM projects WHERE deleted_at IS "+(archived?"NOT ":"")+"NULL",Long.class);}
    public void reserve(String id,int expected,boolean archive){requireEnabled();if(expected<1 || expected==Integer.MAX_VALUE)throw ApiInputs.bad("Invalid expectedVersion");if(jdbc.update("UPDATE projects SET content_version=content_version+1"+(archive?",deleted_at=UTC_TIMESTAMP(6)":"")+",updated_at=UTC_TIMESTAMP(6) WHERE id=? AND deleted_at IS NULL AND content_version=?",id,expected)!=1)throw ApiInputs.conflict("Project changed or archived");}
}
