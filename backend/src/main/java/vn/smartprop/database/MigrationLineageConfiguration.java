package vn.smartprop.database;

import java.util.*;
import javax.sql.DataSource;
import org.flywaydb.core.Flyway;
import org.springframework.beans.factory.InitializingBean;
import org.springframework.context.annotation.*;
import org.springframework.core.env.Environment;
import org.springframework.jdbc.core.JdbcTemplate;

/** Only SELECT/metadata and Flyway validate. Never calls migrate/baseline/repair. */
@Configuration(proxyBeanMethods=false)
public class MigrationLineageConfiguration {
    @Bean InitializingBean validateSelectedMigrationLineage(DataSource source,Environment env){
        return ()->{
            boolean local=MigrationProfileEnvironmentGuard.isLocal(env);
            boolean standard=List.of(env.getActiveProfiles()).contains(MigrationProfileEnvironmentGuard.STANDARD);
            JdbcTemplate jdbc=new JdbcTemplate(source);
            if(!local&&!standard){
                Integer present=jdbc.queryForObject("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='flyway_schema_history'",Integer.class);
                if(Integer.valueOf(1).equals(present)){
                    var old=jdbc.queryForList("SELECT version,type,checksum,success FROM flyway_schema_history ORDER BY installed_rank");
                    checkHistory(old,false,false);
                }
                return;
            }
            var history=jdbc.queryForList("SELECT version,type,checksum,success FROM flyway_schema_history ORDER BY installed_rank");
            checkHistory(history,local,env.getProperty("app.local-lineage.require-complete",Boolean.class,true));
            if(local)checkLocalIdentity(jdbc,MigrationProfileEnvironmentGuard.staging(env));
            boolean complete=env.getProperty("app.local-lineage.require-complete",Boolean.class,true);
            Flyway flyway=Flyway.configure().dataSource(source)
                .locations("classpath:database/"+(local?"legacy-hybrid-local":"migrations"),"classpath:database/research-migrations"+(local?"":"/poi"))
                .target("25").createSchemas(false).baselineOnMigrate(false).cleanDisabled(true)
                // Only the explicit read-only Advisor can acknowledge known pending V17/V18.
                // Checksum/missing/failed validation errors are never ignored.
                .ignoreMigrationPatterns(local?new String[]{"*:pending"}:new String[]{})
                .validateMigrationNaming(true).load();
            if(local)for(var pending:flyway.info().pending()){
                String version=pending.getVersion().getVersion();
                if(!Set.of("17","18","19","20","21","22","23","24","25").contains(version)
                    ||complete&&!Set.of("19","20","21","22","23","24","25").contains(version)
                    ||"19".equals(version)&&env.getProperty("app.recommendation.tinix-enabled",Boolean.class,false))throw new IllegalStateException("Unexpected pending Local migration; review the location.");
            }
            flyway.validate();
        };
    }
    /** Refuses a live server that is not the expected instance: no implicit 3306 fallback on staging. */
    static void checkLocalIdentity(JdbcTemplate jdbc,boolean staging){
        Integer port=jdbc.queryForObject("SELECT @@port",Integer.class);
        String schema=jdbc.queryForObject("SELECT DATABASE()",String.class);
        if(!Integer.valueOf(staging?3307:3306).equals(port)||!"smartprop".equals(schema))throw new IllegalStateException("Wrong Local database identity.");
        if(staging){
            String datadir=jdbc.queryForObject("SELECT @@datadir",String.class);
            String normalized=datadir==null?"":datadir.replace('\\','/');
            if(!normalized.endsWith(MigrationProfileEnvironmentGuard.STAGING_DATADIR_SUFFIX))throw new IllegalStateException("Staging must use the isolated datadir; refusing "+datadir);
        }
    }
    static void checkHistory(List<Map<String,Object>> history,boolean local,boolean complete){
        boolean legacy=history.stream().anyMatch(r->"14".equals(r.get("version"))&&Objects.equals(r.get("checksum"),-1382804267));
        if(!local){if(legacy)throw new IllegalStateException("Crawler14 history requires explicit hybrid-local-existing-v13 profile.");return;}
        if(history.size()<2||!"13".equals(history.get(0).get("version"))||!"BASELINE".equals(history.get(0).get("type"))||!legacy)throw new IllegalStateException("Expected Local BASELINE13/original crawler14 history.");
        var allowed=List.of("13","14","17","18","19","20","21","22","23","24","25");
        for(int i=0;i<history.size();i++){
            var row=history.get(i);Object success=row.get("success");
            if(i>=allowed.size()||!allowed.get(i).equals(row.get("version"))||!(Boolean.TRUE.equals(success)||Integer.valueOf(1).equals(success))||i>0&&!"SQL".equals(row.get("type")))throw new IllegalStateException("Unexpected/failed Local migration history; stop without repair.");
        }
        if(complete&&history.size()<4)throw new IllegalStateException("Local V17/V18 pending. Review and approve the dedicated completion script before enabling full Backend.");
    }
}
