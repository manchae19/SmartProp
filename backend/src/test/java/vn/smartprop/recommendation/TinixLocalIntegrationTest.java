package vn.smartprop.recommendation;

import com.fasterxml.jackson.databind.*;
import java.nio.file.*;
import java.math.BigDecimal;
import java.util.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.*;
import vn.smartprop.auth.*;
import vn.smartprop.user.*;
import static org.junit.jupiter.api.Assertions.*;
import static vn.smartprop.recommendation.RecommendationDtos.*;

/** Actual Local database, real HTTP server. No seeds, login, session renewal or DML. */
@EnabledIfEnvironmentVariable(named="SMARTPROP_TINIX_LOCAL_TEST",matches="true")
@SpringBootTest(webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT,properties={
 "spring.profiles.active=hybrid-local-existing-v13","app.local-lineage.require-complete=true",
 "server.address=127.0.0.1","app.server.transport=NIO2","spring.jpa.hibernate.ddl-auto=validate",
 "spring.flyway.enabled=false","spring.sql.init.mode=never","spring.datasource.hikari.read-only=true",
 "spring.datasource.hikari.connection-init-sql=SET SESSION TRANSACTION READ ONLY",
 "app.recommendation.allow-unverified-external=false","app.recommendation.tinix-enabled=true",
 "app.broker-applications.enabled=false","app.profile.avatar-enabled=false","app.google.enabled=false",
 "app.seed.enabled=false","app.database-seed.enabled=false","app.import.external-listings=",
 "app.email.enabled=false","app.email.worker-enabled=false","debug=false"})
class TinixLocalIntegrationTest {
    static final String KEY=UUID.randomUUID().toString()+UUID.randomUUID();
    static final Path OUT=Path.of("../.scratch/tinix-integration/step19-1");
    static final long[] BUDGETS={850000000L,1750000000L,2350000000L,3780000000L,5650000000L,12400000000L};
    @DynamicPropertySource static void props(DynamicPropertyRegistry r){
        r.add("spring.datasource.url",()->"jdbc:mysql://127.0.0.1:3306/smartprop?connectionTimeZone=UTC");
        r.add("spring.datasource.username",()->Objects.requireNonNull(System.getenv("DB_USER")));
        r.add("spring.datasource.password",()->Objects.requireNonNull(System.getenv("DB_PASSWORD")));
        r.add("app.jwt-secret",()->UUID.randomUUID().toString()+UUID.randomUUID());
        r.add("app.recommendation.demo-key",()->KEY);
    }
    @Autowired JdbcTemplate jdbc;@Autowired HybridRecommendationService service;@Autowired TestRestTemplate http;
    @Autowired ObjectMapper mapper;@Autowired SessionRepository sessions;@Autowired UserRepository users;
    @Autowired SessionPolicy policy;@Autowired TokenService tokens;
    @org.springframework.boot.test.web.server.LocalServerPort int port;
    Request request(long b,Purpose p){return new Request(BigDecimal.valueOf(b),p,PropertyType.ALL,null,null,null,10);}
    List<Map<String,Object>> checksum(){
        var result=new ArrayList<>(jdbc.queryForList("CHECKSUM TABLE external_listings,external_duplicate_groups,properties,property_images,auth_sessions,flyway_schema_history EXTENDED"));
        result.addAll(jdbc.queryForList("SELECT COUNT(*) AS rows_count,BIT_XOR(CRC32(CONCAT_WS('|',internal_id,quality_status,is_protected_holdout,is_duplicate_representative,transaction_type,price_vnd))) AS metadata_fingerprint FROM tinix_dataset_records FORCE INDEX (ix_tinix_hybrid)"));
        return result;
    }
    void check(Response r,long budget){
        assertTrue(r.topProperties().size()<=10);assertTrue(r.topAreas().size()<=5);Set<String> groups=new HashSet<>();
        for(var p:r.topProperties()){
            assertTrue(p.priceVnd().compareTo(BigDecimal.valueOf(budget))<=0);assertTrue(p.score()>=0&&p.score()<=100);assertFalse(p.explanations().isEmpty());
            if(p.source().kind().equals("TINIX_AI")){
                assertTrue(groups.add(p.duplicateGroup()));assertNull(p.source().detailUrl());assertEquals("UNVERIFIED",p.verificationStatus());
                assertEquals(1,jdbc.queryForObject("SELECT COUNT(*) FROM tinix_dataset_records WHERE internal_id=? AND quality_status='HYBRID_ELIGIBLE_RESEARCH' AND transaction_type='SALE' AND is_protected_holdout=0 AND is_duplicate_representative=1 AND JSON_LENGTH(quality_issues)=0",Integer.class,p.source().recordKey()));
                assertEquals(0,jdbc.queryForObject("SELECT COUNT(*) FROM tinix_dataset_records WHERE duplicate_group=? AND is_protected_holdout=1",Integer.class,p.duplicateGroup()));
            }
        }
    }
    @Test void actualResearchServiceAndSafeHttpAcrossSixBudgets() throws Exception {
        var before=checksum();assertEquals("smartprop",jdbc.queryForObject("SELECT DATABASE()",String.class));assertEquals(3306,jdbc.queryForObject("SELECT @@port",Integer.class));
        assertEquals(3204,jdbc.queryForObject("SELECT COUNT(*) FROM external_listings",Integer.class));assertEquals(983,jdbc.queryForObject("SELECT COUNT(*) FROM external_listings WHERE is_protected_holdout=1",Integer.class));
        var reports=new ArrayList<Object>();
        for(long b:BUDGETS){
            var research=service.recommendResearch(request(b,Purpose.LIVING));check(research,b);assertEquals("INTERNAL_DEMO",research.mode());
            assertTrue(research.topProperties().stream().anyMatch(p->p.source().kind().equals("TINIX_AI")));
            Files.writeString(OUT.resolve("research-service-"+b+".json"),mapper.writerWithDefaultPrettyPrinter().writeValueAsString(research));
            var safe=http.postForEntity("/api/v1/recommendations",request(b,Purpose.LIVING),Response.class);assertEquals(HttpStatus.OK,safe.getStatusCode());check(safe.getBody(),b);
            assertTrue(safe.getBody().topProperties().stream().noneMatch(p->p.source().kind().equals("TINIX_AI")));
            reports.add(Map.of("budgetVnd",b,"researchProperties",research.topProperties().size(),"researchAreas",research.topAreas().size(),"eligibleCandidates",research.eligibleCandidateCount(),"safeHttp",safe.getStatusCode().value(),"safeProperties",safe.getBody().topProperties().size()));
        }
        for(var purpose:Purpose.values())check(service.recommendResearch(request(5650000000L,purpose)),5650000000L);
        Files.writeString(OUT.resolve("live-service-and-safe-http.json"),mapper.writerWithDefaultPrettyPrinter().writeValueAsString(reports));assertEquals(before,checksum());
    }
    @Test void actualHttpRejectsMissingInvalidAuthenticationAndInvalidBudget(){
        assertEquals(HttpStatus.UNAUTHORIZED,http.postForEntity("/api/v1/recommendations/research",request(2350000000L,Purpose.LIVING),JsonNode.class).getStatusCode());
        var headers=new HttpHeaders();headers.setBearerAuth("invalid-token");headers.set("X-SmartProp-Demo-Key",KEY);
        assertEquals(HttpStatus.UNAUTHORIZED,http.postForEntity("/api/v1/recommendations/research",new HttpEntity<>(request(2350000000L,Purpose.LIVING),headers),JsonNode.class).getStatusCode());
        assertEquals(HttpStatus.BAD_REQUEST,http.postForEntity("/api/v1/recommendations",request(0,Purpose.LIVING),JsonNode.class).getStatusCode());
    }
    @Test void actualAdminHttpOnlyIfExistingValidAdminSession() throws Exception {
        AuthSession selected=null;User admin=null;
        for(var s:sessions.findAll()){
            var u=users.findById(s.userId).orElse(null);
            if(u!=null&&u.role==User.Role.ADMIN&&u.status==User.Status.ACTIVE&&u.deletedAt==null&&policy.valid(s,u)){selected=s;admin=u;break;}
        }
        Assumptions.assumeTrue(selected!=null,"No existing valid ADMIN session: positive live demo NOT accepted; do not create or extend sessions");
        var before=checksum();var h=new HttpHeaders();String token=tokens.issueFresh(selected,admin.tokenVersion);h.setBearerAuth(token);
        assertEquals(HttpStatus.FORBIDDEN,http.postForEntity("/api/v1/recommendations/research",new HttpEntity<>(request(2350000000L,Purpose.LIVING),h),JsonNode.class).getStatusCode());
        h.set("X-SmartProp-Demo-Key","wrong");assertEquals(HttpStatus.FORBIDDEN,http.postForEntity("/api/v1/recommendations/research",new HttpEntity<>(request(2350000000L,Purpose.LIVING),h),JsonNode.class).getStatusCode());
        h.set("X-SmartProp-Demo-Key",KEY);var results=new ArrayList<Object>();
        for(long b:BUDGETS){var result=http.postForEntity("/api/v1/recommendations/research",new HttpEntity<>(request(b,Purpose.LIVING),h),Response.class);assertEquals(HttpStatus.OK,result.getStatusCode());check(result.getBody(),b);results.add(result.getBody());}
        Files.writeString(OUT.resolve("live-admin-http.json"),mapper.writerWithDefaultPrettyPrinter().writeValueAsString(results));assertEquals(before,checksum());
        var process=new ProcessBuilder("node","e2e/tinix.live.mjs",OUT.toAbsolutePath().normalize().toString());
        process.directory(Path.of("../frontend/vue.ui").toFile());
        process.environment().put("SMARTPROP_DEV_API_TARGET","http://127.0.0.1:"+port);
        process.environment().put("SMARTPROP_E2E_ADMIN_TOKEN",token);process.environment().put("SMARTPROP_INTERNAL_DEMO_KEY",KEY);
        process.redirectErrorStream(true);process.redirectOutput(OUT.resolve("frontend-admin-live.log").toFile());
        var child=process.start();boolean finished=child.waitFor(180,java.util.concurrent.TimeUnit.SECONDS);
        if(!finished)child.destroyForcibly();assertTrue(finished,"Owned ADMIN browser acceptance timed out");assertEquals(0,child.exitValue());assertEquals(before,checksum());
    }
}
