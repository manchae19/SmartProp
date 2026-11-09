package vn.smartprop.database;

import java.util.*;
import org.junit.jupiter.api.Test;
import org.springframework.mock.env.MockEnvironment;
import static org.junit.jupiter.api.Assertions.*;

class MigrationLineageConfigurationTest {
    MockEnvironment local(){
        var e=new MockEnvironment();e.setActiveProfiles(MigrationProfileEnvironmentGuard.LOCAL);
        return e.withProperty("spring.datasource.url",MigrationProfileEnvironmentGuard.LOCAL_URL)
            .withProperty("spring.flyway.locations","classpath:database/legacy-hybrid-local,classpath:database/research-migrations")
            .withProperty("spring.flyway.enabled","false").withProperty("spring.jpa.hibernate.ddl-auto","validate")
            .withProperty("spring.sql.init.mode","never");
    }
    MockEnvironment staging(){
        var e=local().withProperty("spring.datasource.url",MigrationProfileEnvironmentGuard.STAGING_URL);
        e.setActiveProfiles(MigrationProfileEnvironmentGuard.STAGING);
        return e;
    }
    Map<String,Object> row(String version,String type,Integer checksum){
        var r=new HashMap<String,Object>();r.put("version",version);r.put("type",type);r.put("checksum",checksum);r.put("success",true);return r;
    }
    List<Map<String,Object>> before(){return List.of(row("13","BASELINE",null),row("14","SQL",-1382804267));}
    @Test void explicitLocalProfileHasNoAutoMigration(){assertDoesNotThrow(()->MigrationProfileEnvironmentGuard.check(local()));}
    @Test void mutuallyExclusiveProfiles(){var e=local();e.setActiveProfiles(MigrationProfileEnvironmentGuard.LOCAL,MigrationProfileEnvironmentGuard.STANDARD);assertThrows(IllegalStateException.class,()->MigrationProfileEnvironmentGuard.check(e));}
    @Test void rejectsAutoMigrate(){assertThrows(IllegalStateException.class,()->MigrationProfileEnvironmentGuard.check(local().withProperty("spring.flyway.enabled","true")));}
    @Test void rejectsWrongLocation(){assertThrows(IllegalStateException.class,()->MigrationProfileEnvironmentGuard.check(local().withProperty("spring.flyway.locations","classpath:database/migrations")));}
    @Test void rejectsWrongDatabase(){assertThrows(IllegalStateException.class,()->MigrationProfileEnvironmentGuard.check(local().withProperty("spring.datasource.url","jdbc:mysql://127.0.0.1:13306/smartprop")));}
    @Test void rejectsHibernateOrSqlInitDdl(){assertThrows(IllegalStateException.class,()->MigrationProfileEnvironmentGuard.check(local().withProperty("spring.jpa.hibernate.ddl-auto","update")));assertThrows(IllegalStateException.class,()->MigrationProfileEnvironmentGuard.check(local().withProperty("spring.sql.init.mode","always")));}
    @Test void pendingSchemaCannotEnableFullBackend(){assertThrows(IllegalStateException.class,()->MigrationLineageConfiguration.checkHistory(before(),true,true));}
    @Test void pendingSchemaAllowedForStrictlyReadOnlyAdvisor(){var e=local().withProperty("app.local-lineage.require-complete","false").withProperty("spring.datasource.hikari.read-only","true").withProperty("spring.datasource.hikari.connection-init-sql","SET SESSION TRANSACTION READ ONLY");assertDoesNotThrow(()->MigrationProfileEnvironmentGuard.check(e));assertDoesNotThrow(()->MigrationLineageConfiguration.checkHistory(before(),true,false));assertThrows(IllegalStateException.class,()->MigrationProfileEnvironmentGuard.check(e.withProperty("app.profile.avatar-enabled","true")));}
    @Test void rejectsWritablePendingSchemaOverride(){assertThrows(IllegalStateException.class,()->MigrationProfileEnvironmentGuard.check(local().withProperty("app.local-lineage.require-complete","false")));}
    @Test void standardProfileRefusesCrawlerHistory(){assertThrows(IllegalStateException.class,()->MigrationLineageConfiguration.checkHistory(before(),false,true));}
    @Test void rejectsWrongCrawlerChecksum(){assertThrows(IllegalStateException.class,()->MigrationLineageConfiguration.checkHistory(List.of(row("13","BASELINE",null),row("14","SQL",679419338)),true,false));}
    @Test void acceptsCompletedHistoryForValidation(){var r=new ArrayList<>(before());r.add(row("17","SQL",12));r.add(row("18","SQL",34));assertDoesNotThrow(()->MigrationLineageConfiguration.checkHistory(r,true,true));}
    @Test void rejectsUnexpectedOrFailedHistory(){var r=new ArrayList<>(before());r.add(row("15","SQL",12));assertThrows(IllegalStateException.class,()->MigrationLineageConfiguration.checkHistory(r,true,false));var fail=new ArrayList<>(before());fail.get(1).put("success",false);assertThrows(IllegalStateException.class,()->MigrationLineageConfiguration.checkHistory(fail,true,false));}

    // Staging is the same lineage on a fixed literal URL; nothing else may reach it.
    @Test void stagingProfileAcceptsOnlyTheFixedStagingUrl(){assertDoesNotThrow(()->MigrationProfileEnvironmentGuard.check(staging()));}
    @Test void stagingRejectsTheProductionUrl(){assertThrows(IllegalStateException.class,()->MigrationProfileEnvironmentGuard.check(staging().withProperty("spring.datasource.url",MigrationProfileEnvironmentGuard.LOCAL_URL)));}
    @Test void productionProfileRejectsTheStagingUrl(){assertThrows(IllegalStateException.class,()->MigrationProfileEnvironmentGuard.check(local().withProperty("spring.datasource.url",MigrationProfileEnvironmentGuard.STAGING_URL)));}
    @Test void stagingRejectsAnyOtherHostPortOrSchema(){
        for(String url:new String[]{
            "jdbc:mysql://127.0.0.1:3307/otherdb?connectionTimeZone=UTC",
            "jdbc:mysql://127.0.0.1:3308/smartprop?connectionTimeZone=UTC",
            "jdbc:mysql://localhost:3307/smartprop?connectionTimeZone=UTC",
            "jdbc:mysql://127.0.0.1:3306/smartprop",
            "jdbc:mysql://10.0.0.5:3307/smartprop?connectionTimeZone=UTC"})
            assertThrows(IllegalStateException.class,()->MigrationProfileEnvironmentGuard.check(staging().withProperty("spring.datasource.url",url)),url);
    }
    @Test void stagingAndLocalProfilesCannotCombine(){var e=staging();e.setActiveProfiles(MigrationProfileEnvironmentGuard.LOCAL,MigrationProfileEnvironmentGuard.STAGING);assertThrows(IllegalStateException.class,()->MigrationProfileEnvironmentGuard.check(e));}
    @Test void stagingCannotUsePendingSchemaReadOnlyMode(){assertThrows(IllegalStateException.class,()->MigrationProfileEnvironmentGuard.check(staging().withProperty("app.local-lineage.require-complete","false")));}
    @Test void stagingKeepsAutoDdlAndMigrateForbidden(){
        assertThrows(IllegalStateException.class,()->MigrationProfileEnvironmentGuard.check(staging().withProperty("spring.jpa.hibernate.ddl-auto","update")));
        assertThrows(IllegalStateException.class,()->MigrationProfileEnvironmentGuard.check(staging().withProperty("spring.jpa.hibernate.ddl-auto","none")));
        assertThrows(IllegalStateException.class,()->MigrationProfileEnvironmentGuard.check(staging().withProperty("spring.flyway.enabled","true")));
        assertThrows(IllegalStateException.class,()->MigrationProfileEnvironmentGuard.check(staging().withProperty("spring.sql.init.mode","always")));
    }
    @Test void stagingDatadirMustBeTheIsolatedOne(){
        assertTrue("F:\\SmartProp-backups\\mysql-isolated\\data\\".replace('\\','/').endsWith(MigrationProfileEnvironmentGuard.STAGING_DATADIR_SUFFIX));
        assertFalse("F:\\MySQL\\Data\\Data\\".replace('\\','/').endsWith(MigrationProfileEnvironmentGuard.STAGING_DATADIR_SUFFIX));
    }
}