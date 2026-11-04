package vn.smartprop.modules.gis.poi;
import java.util.List;
import org.springframework.data.jpa.repository.*;
import org.springframework.data.repository.query.Param;
public interface PointOfInterestRepository extends JpaRepository<PointOfInterest,String> {
    interface Nearby {String getId();String getName();String getCategory();String getSourceName();String getExternalId();Double getLatitude();Double getLongitude();Double getDistanceMeters();}
    @Query(value="select id,name,category,source_name sourceName,external_id externalId,ST_Latitude(location) latitude,ST_Longitude(location) longitude,ST_Distance_Sphere(location,ST_GeomFromText(:point,4326,'axis-order=long-lat')) distanceMeters from points_of_interest where (:category is null or category=:category) and ST_Distance_Sphere(location,ST_GeomFromText(:point,4326,'axis-order=long-lat'))<=:radius order by distanceMeters,id limit :limit",nativeQuery=true)
    List<Nearby> nearby(@Param("point") String point,@Param("category") String category,@Param("radius") double radius,@Param("limit") int limit);
}