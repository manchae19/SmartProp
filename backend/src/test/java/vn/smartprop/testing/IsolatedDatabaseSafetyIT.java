package vn.smartprop.testing;

import java.nio.file.*;
import java.util.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@EnabledIfEnvironmentVariable(named="SMARTPROP_TEST_FIXTURE_AUTHORIZATION",matches=".+")
class IsolatedDatabaseSafetyIT {
    Path manifest;Properties expected;JdbcTemplate jdbc;String auth,url;
    @BeforeEach void setup() throws Exception {
        manifest=Path.of(System.getenv("SMARTPROP_TEST_FIXTURE_MANIFEST"));expected=new Properties();
        try(var in=Files.newInputStream(manifest)){expected.load(in);}
        auth=System.getenv("SMARTPROP_TEST_FIXTURE_AUTHORIZATION");url=System.getenv("DB_URL");
        jdbc=new JdbcTemplate(new DriverManagerDataSource(url,System.getenv("DB_USER"),System.getenv("DB_PASSWORD")));
    }
    void reject(String key,String value) throws Exception {
        Properties p=new Properties();p.putAll(expected);p.setProperty(key,value);
        Path changed=Files.createTempFile("isolated-negative-",".properties");
        try{try(var out=Files.newOutputStream(changed)){p.store(out,"negative test; no DB writes");}
            assertThrows(IllegalStateException.class,()->IsolatedDatabaseTestSafety.require(jdbc,changed,auth,url));
        }finally{Files.delete(changed);}
    }
    @Test void independentlyProvisionedFixtureIsAccepted(){IsolatedDatabaseTestSafety.require(jdbc);}
    @Test void wrongUuidRejected() throws Exception {reject("serverUuid","00000000-0000-0000-0000-000000000001");}
    @Test void wrongSchemaRejected() throws Exception {reject("schema","other_fixture");}
    @Test void wrongDatadirRejected() throws Exception {reject("datadir",manifest.getParent().toString());}
    @Test void wrongJdbcRejected() throws Exception {reject("jdbcUrl",url.replace("127.0.0.1","localhost"));}
    @Test void wrongOwnershipRejected() throws Exception {reject("owner","somebody-else");}
    @Test void missingAuthorizationRejectedBeforeJdbc(){
        var untouched=mock(JdbcTemplate.class);
        assertThrows(IllegalStateException.class,()->IsolatedDatabaseTestSafety.require(untouched,manifest,null,url));verifyNoInteractions(untouched);
    }
    @Test void protectedPortsRejectedBeforeJdbc() throws Exception {
        for(int port:new int[]{3306,3307}){
            Properties p=new Properties();p.putAll(expected);p.setProperty("port",Integer.toString(port));
            p.setProperty("jdbcUrl","jdbc:mysql://127.0.0.1:"+port+"/smartprop?connectionTimeZone=UTC");
            Path changed=Files.createTempFile("isolated-protected-",".properties");var untouched=mock(JdbcTemplate.class);
            try{try(var out=Files.newOutputStream(changed)){p.store(out,"protected port negative");}
                assertThrows(IllegalStateException.class,()->IsolatedDatabaseTestSafety.require(untouched,changed,auth,p.getProperty("jdbcUrl")));verifyNoInteractions(untouched);
            }finally{Files.delete(changed);}
        }
    }
}
