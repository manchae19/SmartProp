package vn.smartprop.database;

import java.util.*;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.mock.env.MockEnvironment;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class Pr41IsolatedLineageTest {
    MockEnvironment isolated(){
        var env=new MockEnvironment();env.setActiveProfiles(MigrationProfileEnvironmentGuard.PR41_ISOLATED);
        return env.withProperty("spring.datasource.url",MigrationProfileEnvironmentGuard.PR41_URL)
            .withProperty("spring.flyway.locations","classpath:database/legacy-hybrid-local,classpath:database/research-migrations")
            .withProperty("spring.flyway.enabled","false").withProperty("spring.jpa.hibernate.ddl-auto","validate")
            .withProperty("spring.sql.init.mode","never");
    }
    JdbcTemplate identity(){
        var jdbc=mock(JdbcTemplate.class);
        when(jdbc.queryForObject("SELECT @@port",Integer.class)).thenReturn(3311);
        when(jdbc.queryForObject("SELECT DATABASE()",String.class)).thenReturn("pr41_local");
        when(jdbc.queryForObject("SELECT @@server_uuid",String.class)).thenReturn(MigrationProfileEnvironmentGuard.PR41_SERVER_UUID);
        when(jdbc.queryForObject("SELECT @@datadir",String.class)).thenReturn(MigrationProfileEnvironmentGuard.PR41_DATADIR.replace('/','\\'));
        return jdbc;
    }
    @Test void acceptsOnlyTheApprovedLiteralJdbcUrl(){
        assertDoesNotThrow(()->MigrationProfileEnvironmentGuard.check(isolated()));
        for(String url:List.of(MigrationProfileEnvironmentGuard.LOCAL_URL,MigrationProfileEnvironmentGuard.STAGING_URL,
            "jdbc:mysql://localhost:3311/pr41_local?connectionTimeZone=UTC","jdbc:mysql://127.0.0.1:3311/other?connectionTimeZone=UTC"))
            assertThrows(IllegalStateException.class,()->MigrationProfileEnvironmentGuard.check(isolated().withProperty("spring.datasource.url",url)));
    }
    @Test void rejectsProfileMixingAndReadOnlyPendingOverride(){
        var env=isolated();env.setActiveProfiles(MigrationProfileEnvironmentGuard.PR41_ISOLATED,"dev");
        assertThrows(IllegalStateException.class,()->MigrationProfileEnvironmentGuard.check(env));
        assertThrows(IllegalStateException.class,()->MigrationProfileEnvironmentGuard.check(isolated().withProperty("app.local-lineage.require-complete","false")));
    }
    @Test void exactServerIdentityIsRequired(){assertDoesNotThrow(()->MigrationLineageConfiguration.checkPr41IsolatedIdentity(identity()));}
    @Test void rejectsSharedPorts(){for(int port:new int[]{3306,3307,3312}){var jdbc=identity();when(jdbc.queryForObject("SELECT @@port",Integer.class)).thenReturn(port);assertThrows(IllegalStateException.class,()->MigrationLineageConfiguration.checkPr41IsolatedIdentity(jdbc));}}
    @Test void rejectsWrongUuid(){var jdbc=identity();when(jdbc.queryForObject("SELECT @@server_uuid",String.class)).thenReturn("other-instance");assertThrows(IllegalStateException.class,()->MigrationLineageConfiguration.checkPr41IsolatedIdentity(jdbc));}
    @Test void rejectsWrongDatadirAndSchema(){for(String dir:List.of("D:/mysql-isolated/data/",MigrationProfileEnvironmentGuard.PR41_DATADIR+"other/")){var jdbc=identity();when(jdbc.queryForObject("SELECT @@datadir",String.class)).thenReturn(dir);assertThrows(IllegalStateException.class,()->MigrationLineageConfiguration.checkPr41IsolatedIdentity(jdbc));}var jdbc=identity();when(jdbc.queryForObject("SELECT DATABASE()",String.class)).thenReturn("smartprop");assertThrows(IllegalStateException.class,()->MigrationLineageConfiguration.checkPr41IsolatedIdentity(jdbc));}
    @Test void v28RequiresAllEarlierLocalVersionsAndStrictOrder(){
        var helper=new MigrationLineageConfigurationTest();var valid=helper.through(28);
        assertDoesNotThrow(()->MigrationLineageConfiguration.checkHistory(valid,true,true));
        for(String missing:List.of("20","26","27")){var rows=new ArrayList<>(helper.through(28));rows.removeIf(row->missing.equals(row.get("version")));assertThrows(IllegalStateException.class,()->MigrationLineageConfiguration.checkHistory(rows,true,true));}
        var unordered=new ArrayList<>(helper.through(28));Collections.swap(unordered,unordered.size()-1,unordered.size()-2);assertThrows(IllegalStateException.class,()->MigrationLineageConfiguration.checkHistory(unordered,true,true));
        var duplicate=new ArrayList<>(helper.through(28));duplicate.add(helper.row("28","SQL",28));assertThrows(IllegalStateException.class,()->MigrationLineageConfiguration.checkHistory(duplicate,true,true));
        var failed=new ArrayList<>(helper.through(28));failed.get(failed.size()-1).put("success",false);assertThrows(IllegalStateException.class,()->MigrationLineageConfiguration.checkHistory(failed,true,true));
    }
    @Test void runtimeRefusesPendingNewsMigrations(){for(String version:List.of("26","27","28"))assertThrows(IllegalStateException.class,()->MigrationLineageConfiguration.checkRuntimePendingLocalMigrations(List.of(version),true));assertEquals("28",MigrationLineageConfiguration.target(true));assertEquals("23",MigrationLineageConfiguration.target(false));}
}
