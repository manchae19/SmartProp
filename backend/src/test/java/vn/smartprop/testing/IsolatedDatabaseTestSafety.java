package vn.smartprop.testing;

import java.nio.file.*;
import java.net.URI;
import java.time.*;
import java.util.*;
import java.security.MessageDigest;
import org.springframework.jdbc.core.JdbcTemplate;

/** Test-only boundary: expected identity is provisioned independently, never learned from JDBC. */
public final class IsolatedDatabaseTestSafety {
    private IsolatedDatabaseTestSafety() {}
    public static void require(JdbcTemplate jdbc) {
        String manifest=System.getenv("SMARTPROP_TEST_FIXTURE_MANIFEST");
        check(manifest!=null&&!manifest.isBlank(),"Missing independently provisioned fixture manifest");
        require(jdbc,Path.of(manifest),System.getenv("SMARTPROP_TEST_FIXTURE_AUTHORIZATION"),System.getenv("DB_URL"));
    }
    public static void require(JdbcTemplate jdbc,Path file,String authorization,String destination) {
        try {
            var p=new Properties();try(var stream=Files.newInputStream(file)){p.load(stream);}
            String token=value(p,"authorization");
            check(authorization!=null&&!authorization.isBlank()&&authorization.equals(token),"Explicit fixture authorization required");
            String url=value(p,"jdbcUrl");URI uri=URI.create(url.substring(5));
            int port=Integer.parseInt(value(p,"port"));String schema=value(p,"schema");
            check(port>=1024&&port<=65535&&port!=3306&&port!=3307,"Protected database port");
            check("mysql".equals(uri.getScheme())&&"127.0.0.1".equals(uri.getHost())&&uri.getPort()==port
                &&uri.getRawUserInfo()==null&&uri.getFragment()==null&&("/"+schema).equals(uri.getPath()),"Unexpected JDBC destination");
            check(!schema.equalsIgnoreCase("smartprop")&&schema.matches("[a-zA-Z0-9_]+"),"Protected schema");
            check(url.equals(destination),"DB_URL differs from the authorized fixture");
            UUID.fromString(value(p,"serverUuid"));
            Path datadir=Path.of(value(p,"datadir")).toRealPath();
            check(Files.readString(Path.of(value(p,"ownershipFile"))).trim().equals(token),"Fixture ownership marker mismatch");
            var process=ProcessHandle.of(Long.parseLong(value(p,"pid"))).orElseThrow(()->new IllegalStateException("Fixture process absent"));
            check(process.isAlive(),"Fixture process stopped");var info=process.info();
            check(Path.of(info.command().orElseThrow()).toRealPath().equals(Path.of(value(p,"executable")).toRealPath()),"Fixture executable mismatch");
            String user=info.user().orElseThrow().replace('\\','/');
            check(user.equalsIgnoreCase(value(p,"owner"))||user.toLowerCase(Locale.ROOT).endsWith("/"+value(p,"owner").toLowerCase(Locale.ROOT)),"Fixture owner mismatch");
            check(Math.abs(Duration.between(Instant.parse(value(p,"startedAt")),info.startInstant().orElseThrow()).toMillis())<2000,"Fixture PID was reused");
            String digest=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(Path.of(value(p,"configPath")))));
            check(digest.equalsIgnoreCase(value(p,"configSha256")),"Fixture config changed");
            try(var connection=jdbc.getDataSource().getConnection()){
                check(url.equals(connection.getMetaData().getURL()),"Connected JDBC destination differs");
            }
            check(Integer.valueOf(port).equals(jdbc.queryForObject("SELECT @@port",Integer.class)),"Wrong port");
            check(schema.equals(jdbc.queryForObject("SELECT DATABASE()",String.class)),"Wrong schema");
            check(value(p,"serverUuid").equals(jdbc.queryForObject("SELECT @@server_uuid",String.class)),"Wrong UUID");
            check(datadir.equals(Path.of(jdbc.queryForObject("SELECT @@datadir",String.class)).toRealPath()),"Wrong datadir");
        } catch (IllegalStateException e) {throw e;}
        catch(Exception e){throw new IllegalStateException("Isolated fixture validation failed",e);}
    }
    private static String value(Properties p,String name){String v=p.getProperty(name);check(v!=null&&!v.isBlank(),"Missing fixture "+name);return v;}
    private static void check(boolean ok,String message){if(!ok)throw new IllegalStateException(message);}
}
