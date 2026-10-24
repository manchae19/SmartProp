import java.sql.*;
import java.nio.file.*;
import java.util.*;
/** Read-only reconciliation. Includes soft-deleted metadata; never deletes bytes. */
class StorageAudit {
    public static void main(String[] args) throws Exception {
        if(args.length!=2)throw new IllegalArgumentException("Expected storage root and output TSV");
        Path root=Path.of(args[0]).toAbsolutePath().normalize(),output=Path.of(args[1]).toAbsolutePath().normalize();Set<String> referenced=new TreeSet<>();
        try(Connection c=DriverManager.getConnection(System.getenv("DB_URL"),System.getenv("DB_USER"),System.getenv("DB_PASSWORD"))) {
            c.setReadOnly(true);c.setAutoCommit(false);
            boolean legalExists;try(PreparedStatement check=c.prepareStatement("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='property_legal_documents'")){try(ResultSet rs=check.executeQuery()){rs.next();legalExists=rs.getInt(1)>0;}}
            try(Statement s=c.createStatement();ResultSet rs=s.executeQuery("SELECT storage_key FROM property_images UNION SELECT storage_key FROM report_attachments"+(legalExists?" UNION SELECT storage_key FROM property_legal_documents":""))){while(rs.next())if(rs.getString(1)!=null)referenced.add(rs.getString(1));}
            c.rollback();
        }
        var lines=new ArrayList<String>();lines.add("kind\tkey");long missing=0,orphan=0;
        for(String key:referenced){if(!key.matches("[a-f0-9]{32}\\.bin")){lines.add("LEGACY_OR_INVALID_METADATA\t"+key.replaceAll("[\\t\\r\\n]"," "));continue;}Path p=root.resolve(key);if(!Files.isRegularFile(p,LinkOption.NOFOLLOW_LINKS)){lines.add("MISSING_REFERENCED\t"+key);missing++;}}
        if(Files.isDirectory(root,LinkOption.NOFOLLOW_LINKS)){try(var entries=Files.list(root)){for(Path p:entries.toList())if(Files.isRegularFile(p,LinkOption.NOFOLLOW_LINKS)&&!referenced.contains(p.getFileName().toString())){lines.add("UNREFERENCED_REVIEW_ONLY\t"+p.getFileName().toString().replaceAll("[\\t\\r\\n]"," "));orphan++;}}}
        Files.createDirectories(output.getParent());Files.write(output,lines);System.out.println("Storage audit: references="+referenced.size()+", missing="+missing+", unreferenced="+orphan+"; no files deleted");
    }
}