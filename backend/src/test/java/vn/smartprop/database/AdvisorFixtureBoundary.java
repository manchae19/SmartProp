package vn.smartprop.database;

import java.nio.file.*;
import java.net.URI;
import java.time.*;
import java.util.*;
import java.security.MessageDigest;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedQueue;

/** Test-only pre-connection boundary. Expected values come from the independent provisioner. */
public final class AdvisorFixtureBoundary {
    public static final Map<String,AdvisorFixtureBoundary> AUTHORIZED=new ConcurrentHashMap<>();
    public static final Queue<String> PHYSICAL_CONNECTIONS=new ConcurrentLinkedQueue<>();
    final Properties expected=new Properties();
    public final String url;
    public AdvisorFixtureBoundary(Path manifest,String authorization) {
        try(var input=Files.newInputStream(manifest)){expected.load(input);}
        catch(Exception e){throw new IllegalStateException("Fixture manifest missing",e);}
        check(authorization!=null&&!authorization.isBlank()&&authorization.equals(value("authorization")),"Explicit fixture authorization required");
        url=value("jdbcUrl");verify(url);
    }
    String value(String key){String v=expected.getProperty(key);check(v!=null&&!v.isBlank(),"Missing "+key);return v;}
    static void check(boolean ok,String reason){if(!ok)throw new IllegalStateException(reason);}
    public void verify(String destination) {
        try {
            check(url.equals(destination),"Effective JDBC destination differs from manifest");
            URI u=URI.create(destination.substring(5));int port=Integer.parseInt(value("port"));
            check(port!=3306&&port!=3307&&port>=1024&&port<=65535,"Protected JDBC port rejected before connection");
            check("mysql".equals(u.getScheme())&&"127.0.0.1".equals(u.getHost())&&u.getPort()==port&&u.getRawUserInfo()==null&&u.getFragment()==null&&("/"+value("schema")).equals(u.getPath()),"Unallocated JDBC destination");
            check(!"smartprop".equalsIgnoreCase(value("schema")),"Protected schema");
            Path config=Path.of(value("configPath"));String content=Files.readString(config);
            check(content.lines().anyMatch(s->s.trim().equals("port="+port)),"Config port differs");
            Path datadir=Path.of(value("datadir")).toRealPath();
            check(content.lines().anyMatch(s->s.startsWith("datadir=")&&Path.of(s.substring(8)).toAbsolutePath().normalize().equals(datadir)),"Config datadir differs");
            check(Files.readString(datadir.resolve("auto.cnf")).contains("server-uuid="+value("serverUuid")),"Initialization UUID differs");
            String hash=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(config)));
            check(hash.equalsIgnoreCase(value("configSha256")),"Config hash differs");
            check(Files.readString(Path.of(value("ownershipFile"))).trim().equals(value("authorization")),"Ownership marker differs");
            ProcessHandle owner=ProcessHandle.of(Long.parseLong(value("pid"))).orElseThrow();check(owner.isAlive(),"Fixture process absent");
            var info=owner.info();check(Path.of(info.command().orElseThrow()).toRealPath().equals(Path.of(value("executable")).toRealPath()),"Executable differs");
            String user=info.user().orElseThrow().replace('\\','/');check(user.equalsIgnoreCase(value("owner"))||user.toLowerCase(Locale.ROOT).endsWith("/"+value("owner").toLowerCase(Locale.ROOT)),"Process owner differs");
            check(Math.abs(Duration.between(Instant.parse(value("startedAt")),info.startInstant().orElseThrow()).toMillis())<2000,"PID reused");
        }catch(IllegalStateException e){throw e;}catch(Exception e){throw new IllegalStateException("Fixture pre-connection validation failed",e);}
    }
}
