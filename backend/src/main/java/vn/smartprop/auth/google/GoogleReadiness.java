package vn.smartprop.auth.google;
import org.springframework.boot.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
@Component
public class GoogleReadiness implements ApplicationRunner {
    private final GoogleSettings settings;private final JdbcTemplate jdbc;private final boolean refresh;
    public GoogleReadiness(GoogleSettings settings,JdbcTemplate jdbc,@Value("${app.refresh.enabled:false}") boolean refresh){this.settings=settings;this.jdbc=jdbc;this.refresh=refresh;}
    public void run(ApplicationArguments args){if(settings.configured()&&refresh&&!Integer.valueOf(1).equals(jdbc.queryForObject("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='user_external_identities'",Integer.class)))throw new IllegalStateException("Google login requires the approved V15 rollout.");}
}
