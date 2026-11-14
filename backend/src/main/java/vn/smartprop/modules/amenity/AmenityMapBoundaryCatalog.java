package vn.smartprop.modules.amenity;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Component;
import java.io.IOException;

/** Uses the existing verified historical scope artifact; never constructs centroids. */
@Component
public class AmenityMapBoundaryCatalog {
    public record Boundary(String name, String version, JsonNode geometry, String sourceUrl, String attribution, String license) {}
    private final JsonNode catalog;
    public AmenityMapBoundaryCatalog(ObjectMapper mapper) {
        try(var in=getClass().getResourceAsStream("/geocoding/danang-search-scopes.geojson")) {
            if(in==null) throw new IOException("Scope catalog unavailable");
            catalog=mapper.readTree(in);
        } catch(IOException e) { throw new IllegalStateException("Cannot load existing amenity map boundaries",e); }
    }
    public Boundary find(String district) {
        for(var f:catalog.path("features")) if(AmenityCatalogService.normalize(district).equals(AmenityCatalogService.normalize(f.path("properties").path("name").asText()))) {
            var s=catalog.path("source");
            return new Boundary(district,catalog.path("version").asText(),f.path("geometry").deepCopy(),
                s.path("url").asText(),s.path("attribution").asText(),s.path("license").asText());
        }
        return null;
    }
}
