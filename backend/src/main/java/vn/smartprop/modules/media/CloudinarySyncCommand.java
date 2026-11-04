package vn.smartprop.modules.media;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.*;
import java.net.URI;
import java.util.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import vn.smartprop.common.*;

public final class CloudinarySyncCommand {
    public static void main(String[] args){
        try{
            Map<String,String> options=new HashMap<>();boolean apply=false;
            for(String arg:args){if(arg.equals("--apply"))apply=true;else if(arg.startsWith("--")&&arg.contains("=")){int i=arg.indexOf('=');options.put(arg.substring(2,i),arg.substring(i+1));}else throw new IllegalArgumentException();}
            String code=options.get("listing-code"),url=System.getenv("DB_URL");
            URI address=URI.create(url.replaceFirst("^jdbc:",""));
            String schema=address.getPath().substring(1);
            if(!Set.of("127.0.0.1","localhost").contains(address.getHost())||!(schema.equals("smartprop")||schema.matches("smartprop_cloudinary_test_[a-f0-9]+")))throw new IllegalArgumentException();
            var source=new DriverManagerDataSource(url,System.getenv("DB_USER"),System.getenv("DB_PASSWORD"));
            var db=new JdbcTemplate(source);var ids=db.queryForList("SELECT id FROM properties WHERE listing_code=? AND deleted_at IS NULL",String.class,code);
            if(ids.size()!=1)throw ApiInputs.missing();
            var mapper=new ObjectMapper().findAndRegisterModules();
            var client=new CloudinaryAdminClient(mapper,new RequestLimits(),System.getenv("CLOUDINARY_CLOUD_NAME"),System.getenv("CLOUDINARY_API_KEY"),System.getenv("CLOUDINARY_API_SECRET"));
            Object result;
            if(apply){
                if(!options.containsKey("operator-id")||!options.containsKey("expected-version"))throw ApiInputs.bad("Cần operator-id và expected-version khi đồng bộ.");
                var sync=new CloudinarySyncService(db,new DataSourceTransactionManager(source),client,new CloudinaryImageDelivery());
                result=sync.synchronize(ids.getFirst(),Long.parseLong(options.get("operator-id")),Integer.parseInt(options.get("expected-version")));
            }else{
                var preview=client.listForListing(code);result=preview;
                System.out.println("READ_ONLY_PREVIEW pages="+preview.pages()+" resources="+preview.resourceCount()+" images="+preview.assets().size()+" rejected="+preview.rejected().size());
            }
            if(options.containsKey("output")){
                Path output=Path.of(options.get("output")).toAbsolutePath().normalize();Files.createDirectories(output.getParent());mapper.writerWithDefaultPrettyPrinter().writeValue(output.toFile(),result);
                System.out.println("Result saved to "+output);
            }else System.out.println(mapper.writerWithDefaultPrettyPrinter().writeValueAsString(result));
        }catch(ApiException e){System.err.println(e.code+": "+e.getMessage());System.exit(1);}
        catch(Exception e){System.err.println("CLOUDINARY_COMMAND_FAILED type="+e.getClass().getSimpleName());for(var frame:java.util.Arrays.stream(e.getStackTrace()).limit(8).toList())System.err.println("  at "+frame);Throwable cause=e;while(cause.getCause()!=null)cause=cause.getCause();if(cause instanceof java.sql.SQLException sql)System.err.println("SQL state="+sql.getSQLState()+" code="+sql.getErrorCode());System.exit(1);}
    }
}
