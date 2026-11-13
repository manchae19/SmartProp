package vn.smartprop.modules.gis.poi;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.*;
import java.net.URI;
import java.time.Instant;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import vn.smartprop.modules.property.Property;

/** Optional operator-reviewed evidence. Never infers precision from an address or project. */
@Component
public class PropertyLocationEvidence {
    private final ObjectMapper json;
    private final String file;
    public record Evidence(String accuracy,String source,String reference,Instant verifiedAt) {}
    public PropertyLocationEvidence(ObjectMapper json,@Value("${app.places.location-evidence-file:}") String file){this.json=json;this.file=file;}
    public Evidence resolve(Property property){
        var unknown=new Evidence("UNKNOWN","PROPERTY_LISTING",null,null);
        if(property.location==null||file==null||file.isBlank())return unknown;
        try{
            Path path=Path.of(file);if(!Files.isRegularFile(path)||Files.size(path)>262144)return unknown;
            var node=json.readTree(Files.readAllBytes(path)).path(property.id);
            String accuracy=node.path("accuracy").asText(),source=node.path("source").asText(),reference=node.path("reference").asText();
            if(!java.util.Set.of("EXACT_PROPERTY","BUILDING_ONLY","APPROXIMATE").contains(accuracy)||source.isBlank()||source.length()>200)return unknown;
            URI uri=URI.create(reference);
            if(!java.util.Set.of("https","http").contains(uri.getScheme())||uri.getHost()==null||uri.getUserInfo()!=null||uri.getQuery()!=null)return unknown;
            if(!node.path("latitude").isNumber()||!node.path("longitude").isNumber())return unknown;
            double lat=node.path("latitude").asDouble(),lon=node.path("longitude").asDouble();
            if(!NearbyService.valid(lat,lon)||Math.abs(lat-property.location.getY())>0.0000001||Math.abs(lon-property.location.getX())>0.0000001)return unknown;
            Instant at=Instant.parse(node.path("verifiedAt").asText());if(at.isAfter(Instant.now()))return unknown;
            return new Evidence(accuracy,source,reference,at);
        }catch(Exception ignored){return unknown;}
    }
}
