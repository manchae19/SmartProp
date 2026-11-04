package vn.smartprop.modules.recommendation;

import com.fasterxml.jackson.databind.JsonNode;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import java.util.*;
import vn.smartprop.modules.auth.*;
import vn.smartprop.modules.user.*;
import vn.smartprop.modules.broker.BrokerApplicationService;
import vn.smartprop.modules.avatar.AvatarService;
import static org.junit.jupiter.api.Assertions.*;

/** Opt-in actual MySQL/HTTP test. Never seeds, imports or migrates a database. */
@EnabledIfEnvironmentVariable(named="SMARTPROP_HYBRID_LOCAL_TEST",matches="true")
@SpringBootTest(webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT,properties={
 "spring.profiles.active=hybrid-local-existing-v13","app.local-lineage.require-complete=true",
 "app.broker-applications.enabled=true","app.profile.avatar-enabled=true","app.google.enabled=false",
 "server.address=127.0.0.1","app.server.transport=NIO2","spring.jpa.hibernate.ddl-auto=validate",
 "spring.flyway.enabled=false","spring.sql.init.mode=never","spring.datasource.hikari.read-only=true",
 "spring.datasource.hikari.connection-init-sql=SET SESSION TRANSACTION READ ONLY",
 "app.recommendation.allow-unverified-external=true","app.seed.enabled=false","app.database-seed.enabled=false",
 "app.import.external-listings=","app.email.enabled=false","app.email.worker-enabled=false","debug=false"})
class RecommendationMySqlIntegrationTest {
    static final String KEY=UUID.randomUUID().toString()+UUID.randomUUID();
    @DynamicPropertySource static void local(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url",()->"jdbc:mysql://127.0.0.1:3306/smartprop?connectionTimeZone=UTC");
        r.add("spring.datasource.username",()->Objects.requireNonNull(System.getenv("DB_USER")));
        r.add("spring.datasource.password",()->Objects.requireNonNull(System.getenv("DB_PASSWORD")));
        r.add("app.jwt-secret",()->UUID.randomUUID().toString()+UUID.randomUUID());
        r.add("app.recommendation.demo-key",()->KEY);
    }
    @Autowired TestRestTemplate http;
    @Autowired JdbcTemplate jdbc;
    @Autowired SessionRepository sessions;
    @Autowired UserRepository users;
    @Autowired SessionPolicy policy;
    @Autowired TokenService tokens;
    @Autowired BrokerApplicationService brokerService;
    @Autowired AvatarService avatarService;
    List<Map<String,Object>> snapshot() {
        var names=jdbc.queryForList("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='smartprop' ORDER BY TABLE_NAME",String.class);
        assertEquals(49,names.size());
        assertTrue(names.stream().allMatch(n->n.matches("[A-Za-z0-9_]+")));
        return jdbc.queryForList("CHECKSUM TABLE "+String.join(",",names.stream().map(n->"smartprop.`"+n+"`").toList())+" EXTENDED");
    }
    @Test void completedSchemaAndAnonymousRoutesRemainSafe() {
        var before=snapshot();
        assertEquals(List.of("13","14","17","18","19"),jdbc.queryForList("SELECT version FROM flyway_schema_history ORDER BY installed_rank",String.class));
        for(String table:List.of("broker_applications","user_avatars","user_external_identities"))
            assertEquals(0,jdbc.queryForObject("SELECT COUNT(*) FROM "+table,Integer.class));
        for(String path:List.of("/api/v1/users/me/broker-application","/api/v1/users/me/avatar","/api/v1/admin/broker-applications"))
            assertEquals(HttpStatus.UNAUTHORIZED,http.getForEntity(path,JsonNode.class).getStatusCode());
        var google=http.getForEntity("/api/v1/auth/google/config",JsonNode.class);
        assertEquals(HttpStatus.OK,google.getStatusCode());assertFalse(Objects.requireNonNull(google.getBody()).path("available").asBoolean());
        assertEquals(before,snapshot());
    }
    @Test void actualBrokerAndAvatarReadsUseExistingSessionWithoutMutatingBusinessData() {
        var before=snapshot();AuthSession selected=null;User user=null;
        for(var s:sessions.findAll()){
            var u=users.findById(s.userId).orElse(null);
            if(u!=null&&u.status==User.Status.ACTIVE&&u.deletedAt==null&&policy.valid(s,u)){selected=s;user=u;break;}
        }
        Assumptions.assumeTrue(selected!=null,"No existing valid session; do not create users/sessions for this read-only test");
        var headers=new HttpHeaders();headers.setBearerAuth(tokens.issueFresh(selected,user.tokenVersion));
        // No X-Session-Activity pulse: authenticated GETs must not update existing sessions.
        var broker=http.exchange("/api/v1/users/me/broker-application",HttpMethod.GET,new HttpEntity<>(headers),JsonNode.class);
        assertEquals(HttpStatus.OK,broker.getStatusCode());
        assertEquals(user.role==User.Role.BUYER?"NOT_REQUESTED":"APPROVED",Objects.requireNonNull(broker.getBody()).path("status").asText());
        var avatar=http.exchange("/api/v1/users/me/avatar",HttpMethod.GET,new HttpEntity<>(headers),JsonNode.class);
        assertEquals(HttpStatus.OK,avatar.getStatusCode());
        var body=Objects.requireNonNull(avatar.getBody());assertTrue(body.path("enabled").asBoolean());assertFalse(body.path("available").asBoolean());
        assertEquals(HttpStatus.NOT_FOUND,http.exchange("/api/v1/users/me/avatar/content",HttpMethod.GET,new HttpEntity<>(headers),JsonNode.class).getStatusCode());
        assertEquals(before,snapshot());
        System.out.println("SMARTPROP_COMPLETION_API: broker=200, avatar=200(enabled/empty), avatarContent=404, existing-session/read-only, no activity pulse");
    }
    @Test void brokerAndAvatarServicesReadActualCompletedSchemaWithoutCreatingAccounts() {
        var before=snapshot();
        var user=users.findAll().stream().filter(u->u.status==User.Status.ACTIVE&&u.deletedAt==null).findFirst();
        Assumptions.assumeTrue(user.isPresent(),"No active existing user; do not create accounts for this read-only test");
        var u=user.orElseThrow();var broker=brokerService.mine(u.id);var avatar=avatarService.get(u.id);
        assertEquals(u.role==User.Role.BUYER?"NOT_REQUESTED":"APPROVED",broker.status());
        assertTrue(avatar.enabled());assertFalse(avatar.available());assertNull(avatar.url());
        assertEquals(before,snapshot());
        System.out.println("SMARTPROP_COMPLETION_SERVICES: Broker/Avatar read actual new tables using an existing active user; zero writes");
    }
    @Test void actualDemoApiHonorsBudgetQualityHoldoutAndDedupWithoutWrites() {
        assertEquals(3306,jdbc.queryForObject("SELECT @@port",Integer.class));
        assertEquals("smartprop",jdbc.queryForObject("SELECT DATABASE()",String.class));
        assertEquals(3204,jdbc.queryForObject("SELECT COUNT(*) FROM external_listings",Integer.class));
        assertEquals(983,jdbc.queryForObject("SELECT COUNT(*) FROM external_listings WHERE is_protected_holdout=1",Integer.class));
        var before=snapshot();
        AuthSession adminSession=null;User admin=null;
        for(var session:sessions.findAll()) {
            var u=users.findById(session.userId).orElse(null);
            if(u!=null&&u.role==User.Role.ADMIN&&u.status==User.Status.ACTIVE&&u.deletedAt==null&&policy.valid(session,u)) {
                adminSession=session;admin=u;break;
            }
        }
        Assumptions.assumeTrue(adminSession!=null,"No existing valid ADMIN session; do not create/extend sessions for read-only demo acceptance");
        var headers=new HttpHeaders();headers.setContentType(MediaType.APPLICATION_JSON);headers.set("X-SmartProp-Demo-Key",KEY);
        headers.setBearerAuth(tokens.issueFresh(adminSession,admin.tokenVersion));
        var budgets=List.of(2_000_000_000L,5_000_000_000L,3_000_000_000L);
        var purposes=List.of("LIVING","INVESTMENT","RENTAL");var types=List.of("ALL","HOUSE","APARTMENT");
        for(int i=0;i<3;i++) {
            var request=Map.of("budgetVnd",budgets.get(i),"purpose",purposes.get(i),"propertyType",types.get(i),"limit",10);
            var response=http.postForEntity("/api/v1/recommendations",new HttpEntity<>(request,headers),JsonNode.class);
            assertEquals(HttpStatus.OK,response.getStatusCode());var body=Objects.requireNonNull(response.getBody());
            assertEquals("INTERNAL_DEMO",body.path("mode").asText());assertFalse(body.path("topProperties").isEmpty());
            Set<String> groups=new HashSet<>();
            for(var p:body.path("topProperties")) {
                assertTrue(p.path("priceVnd").decimalValue().compareTo(java.math.BigDecimal.valueOf(budgets.get(i)))<=0);
                assertTrue(p.path("score").asDouble()>=0&&p.path("score").asDouble()<=100);
                if(!types.get(i).equals("ALL"))assertEquals(types.get(i),p.path("propertyType").asText());
                assertFalse(p.path("explanations").isEmpty());
                if(p.path("source").path("kind").asText().equals("EXTERNAL")) {
                    String key=p.path("source").path("recordKey").asText();
                    assertEquals(0,jdbc.queryForObject("SELECT COUNT(*) FROM external_listings WHERE record_key=? AND (quality_status='REJECTED' OR is_protected_holdout=1)",Integer.class,key));
                    assertEquals(1,jdbc.queryForObject("SELECT COUNT(*) FROM external_listings WHERE record_key=? AND verification_status=? AND quality_status=?",Integer.class,key,p.path("verificationStatus").asText(),p.path("qualityStatus").asText()));
                    assertFalse(p.path("warnings").isEmpty());
                    if(!p.path("duplicateGroup").isNull()) {
                        String group=p.path("duplicateGroup").asText();assertTrue(groups.add(group));
                        assertEquals(0,jdbc.queryForObject("SELECT COUNT(*) FROM external_listings WHERE duplicate_group=? AND is_protected_holdout=1",Integer.class,group));
                    }
                }
            }
        }
        var valid=Map.of("budgetVnd",2_000_000_000L,"purpose","LIVING","propertyType","ALL");
        assertEquals(HttpStatus.FORBIDDEN,http.postForEntity("/api/v1/recommendations",valid,JsonNode.class).getStatusCode());
        assertEquals(HttpStatus.BAD_REQUEST,http.postForEntity("/api/v1/recommendations",new HttpEntity<>(Map.of("budgetVnd",0,"purpose","LIVING","propertyType","ALL"),headers),JsonNode.class).getStatusCode());
        assertEquals(before,snapshot());
    }
    @Test void actualDemoKeyWithoutAuthenticatedAdminNeverExposesCrawler() {
        var before=snapshot();
        var headers=new HttpHeaders();headers.setContentType(MediaType.APPLICATION_JSON);headers.set("X-SmartProp-Demo-Key",KEY);
        var input=Map.of("budgetVnd",2350000000L,"purpose","LIVING","propertyType","ALL");
        assertEquals(HttpStatus.FORBIDDEN,http.postForEntity("/api/v1/recommendations",new HttpEntity<>(input,headers),JsonNode.class).getStatusCode());
        assertEquals(before,snapshot());
    }
}
