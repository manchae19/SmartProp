package vn.smartprop.modules.gis.poi;
import java.time.Instant;
import java.util.List;

public final class NearbyDtos {
    private NearbyDtos() {}
    /**
     * Origin of a nearby lookup. {@code source}, {@code reference} and {@code verifiedAt} carry
     * operator-reviewed evidence and stay null for plain listing coordinates.
     */
    public record Location(Double latitude,Double longitude,String accuracy,String source,String reference,Instant verifiedAt) {
        /** Listing coordinates without reviewed evidence. */
        public Location(Double latitude,Double longitude,String accuracy){this(latitude,longitude,accuracy,null,null,null);}
    }
    public record Place(String id,String name,List<String> categoryGroups,String category,
                        double latitude,double longitude,double distanceMeters,String address,
                        String provider,String sourcePlaceId,Instant sourceUpdatedAt) {}
    public record Attribution(String label,String url) {}
    public record Result(String propertyId,Location location,int radiusMeters,List<String> categories,
                         String distanceType,List<Place> items,Instant fetchedAt,boolean cacheHit,
                         boolean truncated,String coverage,String status,List<Attribution> attribution) {
        Result cached(){return new Result(propertyId,location,radiusMeters,categories,distanceType,items,
            fetchedAt,true,truncated,coverage,status,attribution);}
    }
}
