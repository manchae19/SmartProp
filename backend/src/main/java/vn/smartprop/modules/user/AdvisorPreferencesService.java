package vn.smartprop.modules.user;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.validation.constraints.*;
import java.util.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.smartprop.common.ApiException;

@Service
public class AdvisorPreferencesService {
    public enum Need { MARKET, SUPERMARKET, MALL, CONVENIENCE_STORE, GYM, SPORTS_FIELD, POOL, PARK,
        RESTAURANT, CAFE, KINDERGARTEN, PRIMARY_SCHOOL, SECONDARY_SCHOOL, PLAYGROUND,
        HOSPITAL, CLINIC, PHARMACY, WORKPLACE, PUBLIC_TRANSPORT }
    public enum Family { MARRIED, SINGLE }
    public record Preferences(Family familyStatus, Boolean hasChildren, @Min(1) @Max(5) Integer childrenCount,
        @Size(max=120) String occupation, @Size(max=180) String workArea,
        @Size(max=19) List<@NotNull Need> selectedNeeds, Need primaryNeed,
        @Size(max=500) String otherNeeds, boolean enabled) {
        public Preferences { selectedNeeds=selectedNeeds==null?List.of():Collections.unmodifiableList(new ArrayList<>(selectedNeeds)); }
        public static Preferences empty() { return new Preferences(null,null,null,"","",List.of(),null,"",false); }
        @Override public String toString() { return "AdvisorPreferences[private]"; }
    }
    public record Context(String subject, boolean enabled, String district, List<Need> selectedNeeds, Need primaryNeed) {}
    private final JdbcTemplate jdbc;
    private final ObjectMapper mapper;
    private final UserRepository users;
    public AdvisorPreferencesService(JdbcTemplate jdbc,ObjectMapper mapper,UserRepository users) {
        this.jdbc=jdbc;this.mapper=mapper;this.users=users;
    }
    public boolean available() {
        return jdbc.queryForObject("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='user_advisor_preferences'",Integer.class)>0;
    }
    @Transactional(readOnly=true)
    public Preferences get(Long id) {
        if(!available()) return Preferences.empty();
        var rows=jdbc.queryForList("SELECT preferences FROM user_advisor_preferences WHERE user_id=?",String.class,id);
        if(rows.isEmpty()) return Preferences.empty();
        try { return mapper.readValue(rows.getFirst(),Preferences.class); }
        catch(Exception e) { throw new ApiException(503,"PROFILE_UNAVAILABLE","Không thể đọc nhu cầu đã lưu."); }
    }
    @Transactional
    public void save(Long id,Preferences p) {
        if(!available()) throw new ApiException(503,"FEATURE_UNAVAILABLE","Nhu cầu cá nhân chưa được triển khai schema. Liên hệ quản trị viên.");
        if(p.selectedNeeds().stream().anyMatch(Objects::isNull) || new HashSet<>(p.selectedNeeds()).size()!=p.selectedNeeds().size()
            || (p.primaryNeed()!=null && !p.selectedNeeds().contains(p.primaryNeed())))
            throw new ApiException(422,"INVALID_PREFERENCES","Ưu tiên nhất phải thuộc các nhu cầu đã chọn, không chọn trùng.");
        var normalized=new Preferences(p.familyStatus(),p.hasChildren(),Boolean.TRUE.equals(p.hasChildren())?p.childrenCount():null,
            trim(p.occupation()),trim(p.workArea()),p.selectedNeeds(),p.primaryNeed(),trim(p.otherNeeds()),p.enabled());
        try {
            String json=mapper.writeValueAsString(normalized);
            jdbc.update("INSERT INTO user_advisor_preferences(user_id,preferences) VALUES (?,?) ON DUPLICATE KEY UPDATE preferences=VALUES(preferences)",id,json);
        } catch(com.fasterxml.jackson.core.JsonProcessingException e) { throw new IllegalStateException("Cannot serialize preferences"); }
    }
    private static String trim(String value) { return value==null?"":value.strip(); }
    @Transactional(readOnly=true)
    public Context context(Long id) {
        var u=users.findById(id).orElseThrow(()->new ApiException(401,"UNAUTHENTICATED","Vui lòng đăng nhập."));
        if(u.deletedAt!=null || u.status!=User.Status.ACTIVE) throw new ApiException(401,"UNAUTHENTICATED","Phiên không hợp lệ.");
        var p=get(id);
        return new Context(id.toString(),p.enabled(),p.enabled()?u.district:null,
            p.enabled()?p.selectedNeeds():List.of(),p.enabled()?p.primaryNeed():null);
    }
}
