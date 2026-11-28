import java.nio.file.Path;
import java.sql.DriverManager;
import org.flywaydb.core.Flyway;

class Wp04Migrate {
    public static void main(String[] args) throws Exception {
        var url = System.getenv("DB_URL");
        var user = System.getenv("DB_USER");
        var password = System.getenv("DB_PASSWORD");
        if (url == null || !url.startsWith("jdbc:mysql://127.0.0.1:54041/wp04_final_fixture?") || !"wp04_fixture".equals(user)) {
            throw new IllegalStateException("Isolation check failed");
        }
        try (var connection = DriverManager.getConnection(url, user, password);
             var stmt = connection.createStatement();
             var result = stmt.executeQuery("SELECT @@server_uuid,@@datadir,@@port,DATABASE(),CURRENT_USER(),(SELECT marker FROM wp04_isolation_marker)")) {
            if (!result.next() || !result.getString(1).equals(System.getenv("WP04_SQL_UUID"))
                 || !Path.of(result.getString(2)).toRealPath().equals(Path.of(System.getenv("WP04_SQL_DATADIR")).toRealPath())
                 || result.getInt(3)!=54041 || !"wp04_final_fixture".equals(result.getString(4))
                 || !"wp04_fixture@127.0.0.1".equals(result.getString(5))
                 || !result.getString(6).equals(System.getenv("WP04_SQL_MARKER"))) {
                throw new IllegalStateException("Disposable MySQL identity check failed");
            }
        }
        var flyway = Flyway.configure().dataSource(url,user,password)
            .locations("filesystem:database/migrations","filesystem:database/research-migrations/poi")
            .target("23").baselineOnMigrate(true).baselineVersion("0").cleanDisabled(true).createSchemas(false).load();
        var result = flyway.migrate();
        if (!result.success || !"23".equals(flyway.info().current().getVersion().getVersion())) {
            throw new IllegalStateException("Standard V23 migration result differs from fixture contract");
        }
        try (var c=DriverManager.getConnection(url,user,password); var stmt=c.createStatement();
             var done=stmt.executeQuery("SELECT COUNT(*) FROM flyway_schema_history WHERE success=1 AND type='SQL'")) {
            if(!done.next() || done.getInt(1)!=23) throw new IllegalStateException("Expected 23 successful SQL versions");
        }
        System.out.println("Verified 23 unchanged SQL migrations at V23.");
    }
}
