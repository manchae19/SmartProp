package vn.smartprop.modules.gis.geocoding;

import com.fasterxml.jackson.databind.*;
import java.io.*;
import java.util.*;
import java.util.stream.*;
import org.locationtech.jts.geom.*;
import org.springframework.stereotype.Component;
import static vn.smartprop.modules.gis.geocoding.GeocodingDtos.*;

/** Versioned historical geometry, not a geocoder centroid, display circle, or administrative-name guess. */
@Component
public final class GeocodingScopes {
    private final GeometryFactory factory=new GeometryFactory(new PrecisionModel(),4326);
    private final List<Region> regions=new ArrayList<>();
    private final Map<String,String> newWardDistricts=new HashMap<>();
    private final Set<String> legacyWards=new HashSet<>();
    private final String version;
    record Region(String id,String name,Geometry geometry,String placeId) {}
    record Scope(String id,String status,List<Region> regions,String street) {
        boolean available(){return status.equals("READY");}
        boolean contains(double latitude,double longitude){
            if(!Double.isFinite(latitude)||!Double.isFinite(longitude))return false;
            return regions.stream().anyMatch(r->r.geometry().contains(r.geometry().getFactory().createPoint(new Coordinate(longitude,latitude))));
        }
        String filter(){
            if(!available()||regions.isEmpty())throw new IllegalStateException("Verified scope required");
            var bounds=new Envelope();regions.forEach(r->bounds.expandToInclude(r.geometry().getEnvelopeInternal()));
            String place=regions.size()==1&&!regions.getFirst().placeId().isBlank()?"|place:"+regions.getFirst().placeId():"";
            return "countrycode:vn"+place+"|rect:"+bounds.getMinX()+","+bounds.getMinY()+","+bounds.getMaxX()+","+bounds.getMaxY();
        }
        boolean accepts(Candidate candidate){
            if(!available()||candidate.context()==null||!"vn".equalsIgnoreCase(candidate.context().countryCode())||!contains(candidate.latitude(),candidate.longitude()))return false;
            if(street.isBlank())return true;
            if(!Set.of("street","building","amenity").contains(candidate.context().resultType()))return false;
            return streetKey(candidate.context().street()).equals(street);
        }
    }
    public GeocodingScopes(ObjectMapper mapper){
        try(var input=GeocodingScopes.class.getResourceAsStream("/geocoding/danang-search-scopes.geojson")){
            if(input==null)throw new IOException("Missing geographic scope catalog");
            var data=mapper.readTree(input);version=data.path("version").asText();
            for(var feature:data.path("features")){
                var p=feature.path("properties");Geometry geometry=geometry(feature.path("geometry"));
                if(geometry.isEmpty()||!geometry.isValid())throw new IOException("Invalid verified scope geometry: "+p.path("id").asText());
                String place=p.path("verifiedPlaceId").asText("");if(!place.isBlank()&&!place.matches("[a-f0-9]{20,2048}"))throw new IOException("Invalid provider place identifier");
                regions.add(new Region(p.path("id").asText(),p.path("name").asText(),geometry,place));
            }
            for(var item:data.path("newWardEquivalences"))newWardDistricts.put(GeocodingAddress.key(item.path("ward").asText()),GeocodingAddress.key(item.path("district").asText()));
            for(var item:data.path("unavailableLegacyWards"))legacyWards.add(GeocodingAddress.key(item.path("ward").asText()));
            if(regions.isEmpty()||version.isBlank())throw new IOException("Empty geographic scope catalog");
        }catch(IOException|IllegalArgumentException e){throw new IllegalStateException("Cannot load verified geographic scopes",e);}
    }
    private Geometry geometry(JsonNode value){
        if(value.path("type").asText().equals("Polygon"))return polygon(value.path("coordinates"));
        if(value.path("type").asText().equals("MultiPolygon")){
            var polygons=new ArrayList<Polygon>();for(var p:value.path("coordinates"))polygons.add(polygon(p));return factory.createMultiPolygon(polygons.toArray(Polygon[]::new));
        }
        throw new IllegalArgumentException("Only Polygon/MultiPolygon scopes allowed");
    }
    private Polygon polygon(JsonNode rings){
        if(!rings.isArray()||rings.isEmpty())throw new IllegalArgumentException("Missing polygon rings");
        LinearRing outer=ring(rings.get(0));var holes=new LinearRing[rings.size()-1];for(int i=1;i<rings.size();i++)holes[i-1]=ring(rings.get(i));return factory.createPolygon(outer,holes);
    }
    private LinearRing ring(JsonNode value){
        var coords=new Coordinate[value.size()];for(int i=0;i<value.size();i++){double x=value.get(i).path(0).asDouble(Double.NaN),y=value.get(i).path(1).asDouble(Double.NaN);if(!Double.isFinite(x)||!Double.isFinite(y)||x<=-180||x>180||y<-90||y>90)throw new IllegalArgumentException("Invalid boundary coordinate");coords[i]=new Coordinate(x,y);}return factory.createLinearRing(coords);
    }
    private Optional<Region> district(String name){String key=GeocodingAddress.key(name);return regions.stream().filter(r->GeocodingAddress.key(r.name()).equals(key)).findFirst();}
    private Scope empty(String status){return new Scope(version+":"+status,status,List.of(),"");}
    private boolean adminPart(String value){
        String key=GeocodingAddress.key(value);
        return Set.of("da nang","viet nam","vietnam","vn").contains(key)||district(value).isPresent()||legacyWards.contains(key)||newWardDistricts.containsKey(key)
            || value.strip().matches("(?iu)^(?:phường|p\\.?|xã|quận|q\\.?|huyện|thành phố|tp\\.?)\\s+.*");
    }
    static String streetKey(String value){
        if(value==null)return "";
        return GeocodingAddress.key(value).replaceFirst("^(?:so\\s+)?[0-9]+[a-z]?(?:[/.-][0-9a-z]+)*\\s*","")
            .replaceFirst("^(?:duong|d|street|road)\\s+","").replaceAll("[^a-z0-9 ]"," ").replaceAll("\\s+"," ").strip();
    }
    Scope resolve(Search request){
        if(!GeocodingAddress.key(request.city()).equals("da nang"))return empty("NO_MATCHING_LOCALITY");
        String selectedDistrict=GeocodingAddress.key(request.district()),selectedWard=GeocodingAddress.key(request.ward());
        var explicitDistricts=new LinkedHashSet<String>();var explicitWards=new LinkedHashSet<String>();
        String street="";
        for(String raw:request.address().split(",")){
            String part=raw.strip(),key=GeocodingAddress.key(part);if(part.isBlank())continue;
            if(part.matches("(?iu)^(?:quận|q\\.?|huyện)\\s+.*"))explicitDistricts.add(key);
            else if(part.matches("(?iu)^(?:phường|p\\.?|xã)\\s+.*"))explicitWards.add(key);
            else if(legacyWards.contains(key))explicitWards.add(key);
            else if(district(part).isPresent())explicitDistricts.add(key);
            else if(!adminPart(part)&&street.isBlank())street=streetKey(part);
        }
        if(explicitDistricts.size()>1||explicitWards.size()>1)return empty("NO_MATCHING_LOCALITY");
        // User-selected filters cannot be replaced or widened by free text.
        if(!selectedDistrict.isBlank()&&!explicitDistricts.isEmpty()&&!explicitDistricts.contains(selectedDistrict))return empty("NO_MATCHING_LOCALITY");
        if(!selectedWard.isBlank()&&!explicitWards.isEmpty()&&!explicitWards.contains(selectedWard))return empty("NO_MATCHING_LOCALITY");
        if(selectedDistrict.isBlank()&&!explicitDistricts.isEmpty())selectedDistrict=explicitDistricts.iterator().next();
        if(selectedWard.isBlank()&&!explicitWards.isEmpty())selectedWard=explicitWards.iterator().next();
        if(!selectedWard.isBlank()){
            String equivalent=newWardDistricts.get(selectedWard);
            // No historical ward polygon exists in the bundled source. Do not use a new larger ward instead.
            if(equivalent==null)return empty("SCOPE_UNAVAILABLE");
            if(!selectedDistrict.isBlank()&&!selectedDistrict.equals(equivalent))return empty("NO_MATCHING_LOCALITY");
            selectedDistrict=equivalent;
        }
        if(!selectedDistrict.isBlank()){
            var region=district(selectedDistrict);if(region.isEmpty())return empty("SCOPE_UNAVAILABLE");
            return new Scope(version+":"+region.get().id()+":"+selectedWard,"READY",List.of(region.get()),street);
        }
        return new Scope(version+":supported-danang","READY",List.copyOf(regions),street);
    }
    List<Candidate> filter(List<Candidate> candidates,Scope scope){
        var seen=new HashSet<String>();
        return candidates.stream().filter(scope::accepts)
            .sorted(Comparator.comparingDouble((Candidate c)->c.confidence()==null?0:c.confidence()).reversed())
            .filter(c->seen.add(c.formattedAddress().toLowerCase(Locale.ROOT)+":"+c.latitude()+":"+c.longitude()))
            .limit(5).map(c->{var x=c.context();return c.reviewed(new Context(x.countryCode(),x.localities(),x.districts(),x.wards(),x.resultType(),x.precision(),true,x.warning(),x.street()));}).toList();
    }
}
