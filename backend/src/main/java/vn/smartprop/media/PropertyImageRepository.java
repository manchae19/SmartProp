package vn.smartprop.media;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.*;
public interface PropertyImageRepository extends JpaRepository<PropertyImage,String> {
    List<PropertyImage> findByPropertyIdAndDeletedAtIsNullOrderBySortOrderAscIdAsc(String propertyId);
    List<PropertyImage> findByPropertyIdInAndDeletedAtIsNullOrderBySortOrderAscIdAsc(Collection<String> ids);
    Optional<PropertyImage> findByIdAndPropertyIdAndDeletedAtIsNull(String id,String propertyId);
    long countByPropertyIdAndDeletedAtIsNull(String propertyId);
}