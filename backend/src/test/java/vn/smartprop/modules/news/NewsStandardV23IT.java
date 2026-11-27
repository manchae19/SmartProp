package vn.smartprop.modules.news;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("standard-migrations")
@EnabledIfEnvironmentVariable(named="PR41_STANDARD_V23_TEST",matches="true")
class NewsStandardV23IT {
    @Autowired MockMvc mvc;
    @Autowired JdbcTemplate jdbc;
    @Autowired vn.smartprop.modules.user.UserRepository users;
    @Autowired org.springframework.core.env.Environment environment;
    @Test void partialNewsSchemaIsRefusedBeforeHibernateValidation() {
        assertEquals(3311,jdbc.queryForObject("SELECT @@port",Integer.class));
        assertEquals("pr41_standard",jdbc.queryForObject("SELECT DATABASE()",String.class));
        assertEquals(0,jdbc.queryForObject("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='news_articles'",Integer.class));
        jdbc.execute("CREATE TABLE news_articles (synthetic_test_id INT PRIMARY KEY)");
        try {
            var error=assertThrows(Exception.class,()->{
                try(var context=new org.springframework.boot.builder.SpringApplicationBuilder(vn.smartprop.SmartPropApplication.class)
                    .profiles(environment.getActiveProfiles()).run("--server.address=127.0.0.1","--server.port=0","--spring.main.banner-mode=off")) {
                    fail("Partial News schema was accepted");
                }
            });
            StringBuilder messages=new StringBuilder();for(Throwable cause=error;cause!=null;cause=cause.getCause())messages.append(cause.getMessage());
            assertTrue(messages.toString().contains("News tables do not match"),messages.toString());
        } finally {jdbc.execute("DROP TABLE news_articles");}
    }
    @Test void noNewsTablesAndControlled503WithRealAuthorization() throws Exception {
        assertEquals(3311,jdbc.queryForObject("SELECT @@port",Integer.class));
        assertEquals("pr41_standard",jdbc.queryForObject("SELECT DATABASE()",String.class));
        assertEquals(0,jdbc.queryForObject("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name IN ('news_sources','news_articles','news_ingestion_runs')",Integer.class));
        for(String path:new String[]{"/api/v1/news","/api/v1/news/featured","/api/v1/news/sources"})
            mvc.perform(get(path)).andExpect(status().isServiceUnavailable());
        mvc.perform(get("/api/v1/admin/news/sources")).andExpect(status().isUnauthorized());
        for(String role:new String[]{"USER","BROKER"})
            mvc.perform(get("/api/v1/admin/news/sources").with(jwt().jwt(j->j.subject("999999")).authorities(new SimpleGrantedAuthority("ROLE_"+role))))
                .andExpect(status().isForbidden());
        var user=new vn.smartprop.modules.user.User();
        user.email="pr41-standard-"+java.util.UUID.randomUUID()+"@example.invalid";
        user.passwordHash="synthetic-not-a-real-password";user.fullName="Synthetic admin";
        user.role=vn.smartprop.modules.user.User.Role.ADMIN;user.status=vn.smartprop.modules.user.User.Status.ACTIVE;
        user.tokenVersion=0;user.notificationPreferences=com.fasterxml.jackson.databind.node.JsonNodeFactory.instance.objectNode();
        user=users.saveAndFlush(user); final String id=user.id.toString();
        try {
            for(String suffix:new String[]{"sources","sources/synthetic","articles","stats","ingestion-runs"})
                mvc.perform(get("/api/v1/admin/news/"+suffix).with(jwt().jwt(j->j.subject(id)).authorities(new SimpleGrantedAuthority("ROLE_ADMIN"))))
                    .andExpect(status().isServiceUnavailable());
        } finally {jdbc.update("DELETE FROM user_roles WHERE user_id=?",user.id);users.deleteById(user.id);}
    }
}
