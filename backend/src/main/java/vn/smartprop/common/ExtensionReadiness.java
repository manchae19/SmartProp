package vn.smartprop.common;
import org.springframework.stereotype.Component;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
@Component @Order(-100)
public class ExtensionReadiness implements ApplicationRunner {
    @org.springframework.beans.factory.annotation.Autowired(required=false) private vn.smartprop.email.MailOutbox mail;
    private final JdbcTemplate jdbc;private final boolean projects,legal,refresh,email,chat;
    public ExtensionReadiness(JdbcTemplate jdbc,@Value("${app.projects-management.enabled:false}") boolean projects,@Value("${app.legal-documents.enabled:false}") boolean legal,@Value("${app.refresh.enabled:false}") boolean refresh,@Value("${app.email.enabled:false}") boolean email,@Value("${app.messaging.enabled:false}") boolean chat){this.jdbc=jdbc;this.projects=projects;this.legal=legal;this.refresh=refresh;this.email=email;this.chat=chat;}
    private void table(String name){if(!Integer.valueOf(1).equals(jdbc.queryForObject("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name=?",Integer.class,name)))throw new IllegalStateException("Enabled backend extension requires schema table: "+name);}
    private void column(String table,String column){if(!Integer.valueOf(1).equals(jdbc.queryForObject("SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name=? AND column_name=?",Integer.class,table,column)))throw new IllegalStateException("Enabled backend extension requires schema column: "+table+"."+column);}
    public void run(ApplicationArguments args){if(projects){column("projects","deleted_at");column("projects","content_version");}if(legal)table("property_legal_documents");if(refresh){column("auth_sessions","issued_token_version");table("auth_refresh_token_history");}if(email){column("password_reset_tokens","issued_token_version");table("email_verification_tokens");table("mail_outbox");if(mail!=null)mail.ready();}if(chat){table("conversations");table("conversation_participants");table("messages");}}
}
