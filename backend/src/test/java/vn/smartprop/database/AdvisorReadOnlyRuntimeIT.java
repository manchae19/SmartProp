package vn.smartprop.database;

import java.nio.file.*;
import java.net.*;
import java.net.http.*;
import java.sql.*;
import java.time.*;
import java.util.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.web.servlet.context.ServletWebServerApplicationContext;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import static org.junit.jupiter.api.Assertions.*;

@EnabledIfEnvironmentVariable(named="PR41_ADVISOR_RUNTIME_TEST",matches="true")
class AdvisorReadOnlyRuntimeIT {
    final ObjectMapper json=new ObjectMapper();
    final Path manifests=Path.of(System.getenv("SMARTPROP_ADVISOR_FIXTURE_DIRECTORY"));
    final Path evidence=Path.of(System.getenv("SMARTPROP_ADVISOR_EVIDENCE"));
    AdvisorFixtureBoundary fixture(String schema) {
        var f=new AdvisorFixtureBoundary(manifests.resolve(schema+".properties"),System.getenv("SMARTPROP_TEST_FIXTURE_AUTHORIZATION"));
        AdvisorFixtureBoundary.AUTHORIZED.put(f.url,f);return f;
    }
    JdbcTemplate inspection(AdvisorFixtureBoundary f) {
        var ds=new DriverManagerDataSource(f.url,System.getenv("DB_USER"),System.getenv("DB_PASSWORD"));
        ds.setDriverClassName(AdvisorGuardedDriver.class.getName());return new JdbcTemplate(ds);
    }
    void seedSyntheticSessions(JdbcTemplate jdbc) {
        jdbc.execute("CREATE TABLE IF NOT EXISTS pr41_write_probe(id INT PRIMARY KEY)");
        for(String role:List.of("ADMIN","BUYER","BROKER")) {
            String email="advisor-p1-"+role.toLowerCase()+"@example.invalid";
            jdbc.update("INSERT INTO users(email,password_hash,full_name,role,status,created_at,updated_at,notification_preferences) "
                +"SELECT ?, 'synthetic-unusable', ?, ?, 'ACTIVE', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), JSON_OBJECT() "
                +"WHERE NOT EXISTS(SELECT 1 FROM users WHERE email=?)",email,"SYNTHETIC ADVISOR P1 "+role,role,email);
            jdbc.update("INSERT INTO auth_sessions(id,user_id,created_at,expires_at,revoked,last_used_at) "
                +"SELECT UUID(),u.id,UTC_TIMESTAMP(6),DATE_ADD(UTC_TIMESTAMP(6),INTERVAL 8 HOUR),0,UTC_TIMESTAMP(6) "
                +"FROM users u WHERE u.email=? AND NOT EXISTS(SELECT 1 FROM auth_sessions s WHERE s.user_id=u.id AND s.revoked=0)",email);
        }
    }
    List<String> arguments(AdvisorFixtureBoundary f,boolean complete,String nativeProfile) {
        return new ArrayList<>(List.of("--spring.config.location=classpath:application.yml",
            "--spring.config.import=classpath:application-"+nativeProfile+".yml",
            "--spring.profiles.active=pr41-advisor-fixture-simulation",
            "--spring.datasource.url="+f.url,"--spring.datasource.driver-class-name="+AdvisorGuardedDriver.class.getName(),
            "--smartprop.test.fixture-manifest="+manifests.resolve(f.value("schema")+".properties"),
            "--smartprop.test.native-profile="+nativeProfile,
            "--server.address=127.0.0.1","--server.port=0","--spring.main.banner-mode=off",
            "--spring.flyway.enabled=false","--spring.sql.init.mode=never","--spring.jpa.hibernate.ddl-auto=validate",
            "--app.local-lineage.require-complete="+complete,
            "--spring.datasource.hikari.read-only="+!complete,
            "--spring.datasource.hikari.connection-init-sql="+(!complete?"SET SESSION TRANSACTION READ ONLY":"SELECT 1"),
            "--app.broker-applications.enabled="+complete,"--app.profile.avatar-enabled="+complete,
            "--app.google.enabled=false","--app.seed.enabled=false","--app.database-seed.enabled=false",
            "--app.news.ingestion-enabled=false",
            "--app.advisor.valuation-enabled=false","--app.recommendation.tinix-enabled=false",
            "--app.recommendation.allow-unverified-external=false","--app.email.enabled=false","--app.email.worker-enabled=false"));
    }
    ConfigurableApplicationContext start(List<String> args) {
        return new SpringApplicationBuilder(vn.smartprop.SmartPropApplication.class,AdvisorFixtureRuntimeConfiguration.class).run(args.toArray(String[]::new));
    }
    Map<String,Object> snapshot(JdbcTemplate jdbc) {
        var history=jdbc.queryForList("SELECT * FROM flyway_schema_history ORDER BY installed_rank");
        var names=jdbc.queryForList("SELECT table_name FROM information_schema.tables WHERE table_schema=DATABASE() AND table_type='BASE TABLE' ORDER BY table_name",String.class);
        var checksum=jdbc.queryForList("CHECKSUM TABLE "+String.join(",",names.stream().map(n->"`"+n+"`").toList())+" EXTENDED");
        return Map.of("history",history,"tables",checksum);
    }
    void save(String name,Map<String,Object> result)throws Exception {Files.createDirectories(evidence);Files.writeString(evidence.resolve(name+".json"),json.writerWithDefaultPrettyPrinter().writeValueAsString(result));}
    HttpResponse<String> call(ConfigurableApplicationContext context,String path,String token,String body)throws Exception {
        int port=((ServletWebServerApplicationContext)context).getWebServer().getPort();
        var builder=HttpRequest.newBuilder(URI.create("http://127.0.0.1:"+port+path)).timeout(Duration.ofSeconds(20));
        if(token!=null)builder.header("Authorization","Bearer "+token);
        if(body==null)builder.GET();else builder.header("Content-Type","application/json").POST(HttpRequest.BodyPublishers.ofString(body));
        return HttpClient.newHttpClient().send(builder.build(),HttpResponse.BodyHandlers.ofString());
    }
    String token(ConfigurableApplicationContext context,JdbcTemplate jdbc,String role) {
        var row=jdbc.queryForMap("SELECT s.id,s.user_id,s.created_at,s.expires_at FROM auth_sessions s JOIN users u ON u.id=s.user_id WHERE u.email=? AND s.revoked=0 ORDER BY s.created_at DESC LIMIT 1","advisor-p1-"+role.toLowerCase()+"@example.invalid");
        var session=new vn.smartprop.modules.auth.AuthSession();session.id=(String)row.get("id");session.userId=((Number)row.get("user_id")).longValue();
        session.createdAt=instant(row.get("created_at"));session.expiresAt=instant(row.get("expires_at"));
        return context.getBean(vn.smartprop.modules.auth.TokenService.class).issue(session);
    }
    java.time.Instant instant(Object value) {
        if(value instanceof java.sql.Timestamp timestamp)return timestamp.toInstant();
        if(value instanceof java.time.LocalDateTime local)return local.toInstant(java.time.ZoneOffset.UTC);
        throw new IllegalStateException("Unexpected fixture timestamp type: "+value.getClass().getName());
    }
    void api(ConfigurableApplicationContext context,boolean news)throws Exception {
        var jdbc=context.getBean(JdbcTemplate.class);
        var advisor=call(context,"/api/v1/advisor/consult",null,"{\"budgetVnd\":4000000000,\"purpose\":\"LIVING\",\"propertyType\":\"HOUSE\",\"includeResearch\":false,\"includeValuation\":false,\"includeComparables\":false}");
        assertEquals(200,advisor.statusCode(),advisor.body());assertEquals("SAFE",json.readTree(advisor.body()).path("mode").asText());
        for(String path:List.of("/api/v1/news","/api/v1/news/featured","/api/v1/news/sources")) {
            var response=call(context,path,null,null);assertEquals(news?200:503,response.statusCode(),response.body());
            if(!news)assertTrue(response.body().contains("NEWS_SCHEMA_UNAVAILABLE"));
        }
        assertEquals(401,call(context,"/api/v1/admin/news/sources",null,null).statusCode());
        for(String role:List.of("BUYER","BROKER"))assertEquals(403,call(context,"/api/v1/admin/news/sources",token(context,jdbc,role),null).statusCode());
        assertEquals(news?200:503,call(context,"/api/v1/admin/news/sources",token(context,jdbc,"ADMIN"),null).statusCode());
    }
    @ParameterizedTest @ValueSource(ints={21,26,27})
    void advisorReadOnlyRetainsHttp200AndNews503(int version)throws Exception {
        var f=fixture("pr41_advisor_v"+version);var admin=inspection(f);seedSyntheticSessions(admin);var before=snapshot(admin);
        try(var context=start(arguments(f,false,MigrationProfileEnvironmentGuard.LOCAL))) {
            assertTrue(context.getBean(jakarta.persistence.EntityManagerFactory.class).isOpen());
            var capability=context.getBean(NewsSchemaCapabilities.class);assertFalse(capability.newsEnabled());assertEquals(version>=27,capability.validateNewsTables());
            var runtime=context.getBean(JdbcTemplate.class);assertEquals(1,runtime.queryForObject("SELECT @@session.transaction_read_only",Integer.class));
            assertThrows(org.springframework.dao.DataAccessException.class,()->runtime.update("INSERT INTO pr41_write_probe(id) VALUES(41)"));
            assertEquals(0,admin.queryForObject("SELECT COUNT(*) FROM pr41_write_probe",Integer.class));api(context,false);
        } finally {var after=snapshot(admin);save("advisor-v"+version,Map.of("version",version,"actualProfile","pr41-advisor-fixture-simulation","simulatedNativePolicy",MigrationProfileEnvironmentGuard.LOCAL,"before",before,"after",after,"unchanged",before.equals(after)));assertEquals(before,after);}
    }
    void refused(String name,AdvisorFixtureBoundary f,List<String> args,String message)throws Exception {
        var admin=inspection(f);var before=snapshot(admin);int physical=AdvisorFixtureBoundary.PHYSICAL_CONNECTIONS.size();
        var error=assertThrows(Exception.class,()->{try(var context=start(args)){fail("Invalid runtime started");}});
        StringBuilder reasons=new StringBuilder();for(Throwable e=error;e!=null;e=e.getCause())reasons.append(e.getMessage()).append('\n');
        assertTrue(reasons.toString().contains(message),reasons.toString());
        int startupConnections=AdvisorFixtureBoundary.PHYSICAL_CONNECTIONS.size()-physical;
        var after=snapshot(admin);assertEquals(before,after);
        save(name,Map.of("startup","REFUSED","reason",message,"before",before,"after",after,"historyAndDataUnchanged",true,"connectionsDuringStartup",startupConnections));
    }
    @ParameterizedTest @ValueSource(ints={26,27})
    void fullLocalAndStagingRejectPendingNews(int version)throws Exception {
        var f=fixture("pr41_advisor_v"+version);
        for(String profile:List.of(MigrationProfileEnvironmentGuard.LOCAL,MigrationProfileEnvironmentGuard.STAGING))refused("full-"+profile+"-v"+version,f,arguments(f,true,profile),"migration is pending");
    }
    @Test void completedLocalAndStagingValidateV28()throws Exception {
        var f=fixture("pr41_local");var admin=inspection(f);seedSyntheticSessions(admin);var before=snapshot(admin);
        for(String profile:List.of(MigrationProfileEnvironmentGuard.LOCAL,MigrationProfileEnvironmentGuard.STAGING))
            try(var context=start(arguments(f,true,profile))){assertTrue(context.getBean(NewsSchemaCapabilities.class).newsEnabled());assertTrue(context.getBean(NewsSchemaCapabilities.class).validateNewsTables());api(context,true);}
        var after=snapshot(admin);assertEquals(before,after);save("full-v28",Map.of("profile","isolated Local/Staging policy simulations","before",before,"after",after,"unchanged",true));
    }
    @Test void invalidHistoryIsRefused()throws Exception {var f=fixture("pr41_advisor_gap21");refused("invalid-history",f,arguments(f,false,MigrationProfileEnvironmentGuard.LOCAL),"Unexpected/failed Local migration history");}
    @Test void checksumMismatchIsRefused()throws Exception {
        var f=fixture("pr41_local");var args=arguments(f,true,MigrationProfileEnvironmentGuard.LOCAL);
        args.add("--smartprop.test.validation-locations="+System.getenv("SMARTPROP_ADVISOR_NEGATIVE_LOCATIONS"));
        refused("invalid-checksum",f,args,"checksum mismatch");
    }
    @Test void existingV27NewsTablesAndColumnsRemainValidated()throws Exception {
        var f=fixture("pr41_advisor_v27");var admin=inspection(f);
        admin.execute("RENAME TABLE news_articles TO pr41_held_news_articles");
        try{refused("v27-missing-table",f,arguments(f,false,MigrationProfileEnvironmentGuard.LOCAL),"News tables do not match");}
        finally{admin.execute("RENAME TABLE pr41_held_news_articles TO news_articles");}
        admin.execute("ALTER TABLE news_articles RENAME COLUMN title TO pr41_held_title");
        try{refused("v27-missing-column",f,arguments(f,false,MigrationProfileEnvironmentGuard.LOCAL),"missing column [title]");}
        finally{admin.execute("ALTER TABLE news_articles RENAME COLUMN pr41_held_title TO title");}
    }
    @Test void absentLineageRejectsNewsViewInsteadOfFilteringItAsMissing()throws Exception {
        var f=fixture("pr41_advisor_v21");var admin=inspection(f);
        admin.execute("CREATE VIEW news_articles AS SELECT id FROM properties");
        try{refused("v21-news-view",f,arguments(f,false,MigrationProfileEnvironmentGuard.LOCAL),"News tables do not match");}
        finally{admin.execute("DROP VIEW news_articles");}
    }
    @Test void appliedV28RightsConstraintMustRemainEnforced()throws Exception {
        var f=fixture("pr41_local");var admin=inspection(f);
        admin.execute("ALTER TABLE news_sources ALTER CHECK ck_news_sources_approved_reference NOT ENFORCED");
        try{refused("v28-disabled-check",f,arguments(f,true,MigrationProfileEnvironmentGuard.LOCAL),"Required V28 rights constraint is missing");}
        finally{admin.execute("ALTER TABLE news_sources ALTER CHECK ck_news_sources_approved_reference ENFORCED");}
    }
    @Test void invalidReadOnlyGuardsFailBeforeConnection()throws Exception {
        var f=fixture("pr41_advisor_v21");
        for(String bad:List.of("--spring.datasource.hikari.read-only=false","--spring.datasource.hikari.connection-init-sql=SET SESSION TRANSACTION READ WRITE","--app.broker-applications.enabled=true","--app.profile.avatar-enabled=true","--app.google.enabled=true")){
            var args=arguments(f,false,MigrationProfileEnvironmentGuard.LOCAL);String key=bad.substring(0,bad.indexOf('='));args.removeIf(a->a.startsWith(key+"="));args.add(bad);
            int physical=AdvisorFixtureBoundary.PHYSICAL_CONNECTIONS.size();
            var e=assertThrows(Exception.class,()->{try(var context=start(args)){fail("Invalid read-only policy started");}});
            assertEquals(physical,AdvisorFixtureBoundary.PHYSICAL_CONNECTIONS.size(),e.toString());
        }
        int physical=AdvisorFixtureBoundary.PHYSICAL_CONNECTIONS.size();assertThrows(Exception.class,()->start(arguments(f,false,MigrationProfileEnvironmentGuard.STAGING)));
        assertEquals(physical,AdvisorFixtureBoundary.PHYSICAL_CONNECTIONS.size());save("read-only-guards",Map.of("invalidPolicies",6,"connections",0));
    }
    @Test void protectedOrFallbackDestinationsAreBlockedBeforeConnection()throws Exception {
        var f=fixture("pr41_advisor_v21");int physical=AdvisorFixtureBoundary.PHYSICAL_CONNECTIONS.size();
        for(int port:List.of(3306,3307)){
            var args=arguments(f,false,MigrationProfileEnvironmentGuard.LOCAL);args.removeIf(a->a.startsWith("--spring.datasource.url="));args.add("--spring.datasource.url=jdbc:mysql://127.0.0.1:"+port+"/smartprop?connectionTimeZone=UTC");
            assertThrows(Exception.class,()->start(args));
            assertThrows(SQLException.class,()->new AdvisorGuardedDriver().connect("jdbc:mysql://127.0.0.1:"+port+"/smartprop?connectionTimeZone=UTC",new Properties()));
        }
        var noOverride=arguments(f,false,MigrationProfileEnvironmentGuard.LOCAL);noOverride.removeIf(a->a.startsWith("--spring.datasource.url="));assertThrows(Exception.class,()->start(noOverride));
        var alternative=arguments(f,false,MigrationProfileEnvironmentGuard.LOCAL);alternative.add("--spring.datasource.hikari.jdbc-url=jdbc:mysql://127.0.0.1:3306/smartprop");assertThrows(Exception.class,()->start(alternative));
        assertEquals(physical,AdvisorFixtureBoundary.PHYSICAL_CONNECTIONS.size());save("protected-before-connection",Map.of("protectedPorts",List.of(3306,3307),"fallbackAndHikariOverride","REFUSED","physicalConnections",0));
    }
    @AfterAll static void connectionEvidence()throws Exception {
        Path dir=Path.of(System.getenv("SMARTPROP_ADVISOR_EVIDENCE"));Files.createDirectories(dir);
        Files.write(dir.resolve("physical-jdbc-destinations.txt"),AdvisorFixtureBoundary.PHYSICAL_CONNECTIONS);
        assertTrue(AdvisorFixtureBoundary.PHYSICAL_CONNECTIONS.stream().allMatch(url->url.startsWith("jdbc:mysql://127.0.0.1:3311/")));
    }
}
