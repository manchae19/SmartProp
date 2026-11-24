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
                .target("27").createSchemas(false).baselineOnMigrate(false).cleanDisabled(true)
                // Only the explicit read-only Advisor can acknowledge known pending V17/V18.
                // Checksum/missing/failed validation errors are never ignored.
                .ignoreMigrationPatterns(local?new String[]{"*:pending"}:new String[]{})
                .validateMigrationNaming(true).load();
            if(local)for(var pending:flyway.info().pending()){
                String version=pending.getVersion().getVersion();
                if(!Set.of("17","18","19","20","21","22","23","24","25","26","27").contains(version)
                    ||complete&&!Set.of("19","20","21","22","23","24","25","26","27").contains(version)
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

        // Strict lineage. Every applied version must be known, successful, unique and
        // strictly ascending. V13/V14 are the baseline; V17/V18 are the local-only pair
        // the project has always allowed to be pending. V19-V27 are applied progressively
        // by the migration CLI, so a database may legitimately stop at any of them - but
        // whatever IS applied must be valid. V26 (coordinate provenance, PR #38) and V27
        // (news, PR #41) are independent branches: V27 may be present without V26, and
        // once both merge Flyway applies V26 before V27 and the ascending check enforces
        // the order. Unknown version, failed row, duplicate, out-of-order, or a missing
        // required version is rejected without repair.
        // V13/V14 are the baseline and always required. V17/V18 are the local-only pair
        // the project has always allowed to be pending (see the require-complete flag).
        // V19-V27 are applied progressively by the migration CLI. Whatever IS applied
        // must be known, successful, unique and ascending; V26 (coordinate provenance)
        // and V27 (news) are independent branches, so V27 may appear without V26.
        var required=List.of("13","14");
        var optional=List.of("17","18","19","20","21","22","23","24","25","26","27");
        var allowed=new java.util.ArrayList<String>(required);
        allowed.addAll(optional);

        java.util.Set<String> seen=new java.util.HashSet<>();
        String previous=null;
        for(int i=0;i<history.size();i++){
            var row=history.get(i);Object success=row.get("success");
            String version=String.valueOf(row.get("version"));
            if(!allowed.contains(version)
                ||!(Boolean.TRUE.equals(success)||Integer.valueOf(1).equals(success))
                ||i>0&&!"SQL".equals(row.get("type"))
                ||!seen.add(version)
                ||previous!=null&&compareVersion(previous,version)>=0)
                throw new IllegalStateException("Unexpected/failed Local migration history; stop without repair.");
            previous=version;
        }

        // Every required version must actually be present.
        for(String version:required){
            if(!seen.contains(version))
                throw new IllegalStateException(
                    "Missing required Local migration V"+version+"; stop without repair.");
        }

        // require-complete: kiểm tra V17/V18 TRỰC TIẾP, không dùng history.size() —
        // bốn dòng history có thể là 13,14,19,20 và vẫn thiếu V17/V18.
        if(complete){
            for(String version:List.of("17","18")){
                if(!seen.contains(version))
                    throw new IllegalStateException("Local V"+version+" pending. Review and approve the dedicated completion script before enabling full Backend.");
            }
        }
    }

    /** So sánh version dạng số; trả về âm nếu {@code a} nhỏ hơn {@code b}. */
    private static int compareVersion(String a,String b){
        try{return Integer.compare(Integer.parseInt(a),Integer.parseInt(b));}
        catch(NumberFormatException e){return a.compareTo(b);}
    }
}
