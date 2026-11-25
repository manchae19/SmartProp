package vn.smartprop.modules.gis.poi;
import java.util.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.smartprop.common.*;
import vn.smartprop.config.*;
import vn.smartprop.modules.property.PropertyService;
import vn.smartprop.modules.property.PropertyCoordinateAuditService;
@Service
public class PoiService {
    public record View(String id,String name,String category,double latitude,double longitude,double distanceMeters) {}
    private final PointOfInterestRepository pois;private final PropertyService properties;private final PropertyCoordinateAuditService coordinateAudit;
    public PoiService(PointOfInterestRepository pois,PropertyService properties,PropertyCoordinateAuditService coordinateAudit) {this.pois=pois;this.properties=properties;this.coordinateAudit=coordinateAudit;}
    @Transactional(readOnly=true) public List<View> nearby(String id,double radius,int limit,String category) {
        if(!Double.isFinite(radius)||radius<1||radius>50000||limit<1||limit>100||category!=null&&category.length()>50)throw ApiInputs.bad("radiusMeters 1–50000; limit 1–100; category tối đa50 ký tự");
        var p=properties.publicProperty(id);
        if(!coordinateAudit.status(id).distanceAnalysisEligible())throw new ApiException(422,"LOCATION_UNVERIFIED","Chưa đủ bằng chứng tọa độ để phân tích khoảng cách.");
        if(p.location==null)throw new ApiException(422,"LOCATION_UNAVAILABLE","Tin chưa có tọa độ hợp lệ.");
        String point=String.format(Locale.ROOT,"POINT(%.10f %.10f)",p.location.getX(),p.location.getY());
        return pois.nearby(point,category,radius,limit).stream().map(n->new View(n.getId(),n.getName(),n.getCategory(),n.getLatitude(),n.getLongitude(),n.getDistanceMeters())).toList();
    }
}
