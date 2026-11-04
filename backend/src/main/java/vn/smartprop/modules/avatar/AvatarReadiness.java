package vn.smartprop.modules.avatar;
import org.springframework.boot.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.jdbc.core.JdbcTemplate;
@Component
public class AvatarReadiness implements ApplicationRunner {
    private final JdbcTemplate jdbc;private final boolean enabled;
    public AvatarReadiness(JdbcTemplate jdbc,@Value("${app.profile.avatar-enabled:false}") boolean enabled){this.jdbc=jdbc;this.enabled=enabled;}
    public void run(ApplicationArguments args){if(enabled&&!Integer.valueOf(1).equals(jdbc.queryForObject("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='user_avatars'",Integer.class)))throw new IllegalStateException("Avatar requires the approved V15 rollout.");}
}
