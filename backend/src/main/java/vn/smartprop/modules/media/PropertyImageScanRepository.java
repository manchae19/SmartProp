package vn.smartprop.modules.media;

import org.springframework.data.jpa.repository.JpaRepository;
import java.util.*;

public interface PropertyImageScanRepository extends JpaRepository<PropertyImageScan, String> {
    List<PropertyImageScan> findByPropertyIdOrderByCreatedAtAsc(String propertyId);
    Optional<PropertyImageScan> findByPropertyImageId(String propertyImageId);
    List<PropertyImageScan> findByScanStatusInAndClassificationIn(Collection<String> statuses, Collection<String> classifications);
}
