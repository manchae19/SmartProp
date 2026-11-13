package vn.smartprop.modules.amenity;

import java.time.*;
import java.util.*;
import org.springframework.stereotype.Service;
import vn.smartprop.modules.gis.geocoding.GeocodingScopes;
import vn.smartprop.modules.gis.poi.GeoapifyPlacesClient;
import static vn.smartprop.modules.amenity.AmenityMapService.*;

/** Live provider points, filtered against the existing historical district polygon. No centroid pins. */
@Service
public class GeoapifyDistrictPlaces {
    private static final Map<String,List<String>> CATEGORIES=Map.of(
        "SCHOOL",List.of("education.school","childcare.kindergarten"),"HOSPITAL",List.of("healthcare.hospital"),
        "PHARMACY",List.of("healthcare.pharmacy"),"MARKET",List.of("commercial.marketplace"),
        "SUPERMARKET",List.of("commercial.supermarket"),"PARK",List.of("leisure.park"),
        "MALL",List.of("commercial.shopping_mall"),"BEACH",List.of("natural.beach"),"PUBLIC_TRANSPORT",List.of("public_transport"));
    private record Entry(Instant until,MapEvidence value){}
    private final Map<String,Entry> cache=new LinkedHashMap<>();
    private final GeocodingScopes scopes;private final AmenityMapBoundaryCatalog boundaries;private final GeoapifyPlacesClient provider;
    public GeoapifyDistrictPlaces(GeocodingScopes scopes,AmenityMapBoundaryCatalog boundaries,GeoapifyPlacesClient provider){this.scopes=scopes;this.boundaries=boundaries;this.provider=provider;}
    public synchronized MapEvidence find(String district,String category){
        String key=district+":"+category;var hit=cache.get(key);if(hit!=null&&hit.until().isAfter(Instant.now()))return hit.value();
        var shape=scopes.districtGeometry(district);
        if(shape.isEmpty())return empty(district,category,"Chưa có polygon đủ điều kiện cho địa bàn này; không mở rộng sang địa bàn khác.");
        var geometry=shape.get();var box=geometry.getEnvelopeInternal();
        var categories=category.equals("ALL")?CATEGORIES.values().stream().flatMap(List::stream).distinct().toList():CATEGORIES.get(category);
        com.fasterxml.jackson.databind.JsonNode body;
        try{body=provider.searchBounds(box.getMinX(),box.getMinY(),box.getMaxX(),box.getMaxY(),categories);}
        catch(vn.smartprop.common.ApiException unavailable){return empty(district,category,"Nguồn tọa độ tiện ích chưa sẵn sàng. Bản đồ chỉ hiển thị ranh giới; không tạo ghim thay thế.");}
        var found=new LinkedHashMap<String,MapPoi>();
        for(var feature:body.path("features")){
            var data=feature.path("properties");var coords=feature.path("geometry").path("coordinates");
            if(!"Point".equals(feature.path("geometry").path("type").asText())||coords.size()<2||!coords.get(0).isNumber()||!coords.get(1).isNumber())continue;
            double lon=coords.get(0).asDouble(),lat=coords.get(1).asDouble();
            if(!Double.isFinite(lat)||!Double.isFinite(lon)||!geometry.covers(geometry.getFactory().createPoint(new org.locationtech.jts.geom.Coordinate(lon,lat))))continue;
            String name=data.path("name").asText("").strip(),id=data.path("place_id").asText("");
            if(name.isBlank()||name.length()>500||id.isBlank()||id.length()>4096)continue;
            var raw=new ArrayList<String>();data.path("categories").forEach(c->raw.add(c.asText()));
            String group=CATEGORIES.entrySet().stream().filter(e->category.equals("ALL")||e.getKey().equals(category))
                .filter(e->raw.stream().anyMatch(c->e.getValue().stream().anyMatch(prefix->c.equals(prefix)||c.startsWith(prefix+"."))))
                .map(Map.Entry::getKey).sorted().findFirst().orElse(null);
            if(group==null)continue;
            found.putIfAbsent(id,new MapPoi("geoapify:"+id,name,group,district,lat,lon,"GEOAPIFY_POINT","PROVIDER_REPORTED","geoapify","https://www.geoapify.com/","Powered by Geoapify · © OpenStreetMap contributors","Geoapify / upstream source terms",Instant.now().toString()));
        }
        var items=found.values().stream().limit(80).toList();
        var result=new MapEvidence("POI_MAP_V1","PUBLIC",district,category,items,found.size(),found.size()>80||body.path("features").size()>=200,boundaries.find(district),List.of("Tọa độ do Geoapify cung cấp, đã lọc theo polygon quận lịch sử; chưa xác minh thực địa.","Không phải khoảng cách từ căn nhà. Nguồn dự phòng không thay thế dữ liệu POI đã thẩm định."));
        if(cache.size()>=64)cache.remove(cache.keySet().iterator().next());cache.put(key,new Entry(Instant.now().plusSeconds(900),result));return result;
    }
    private MapEvidence empty(String district,String category,String note){return new MapEvidence("POI_MAP_V1","PUBLIC",district,category,List.of(),0,false,boundaries.find(district),List.of(note));}
}
