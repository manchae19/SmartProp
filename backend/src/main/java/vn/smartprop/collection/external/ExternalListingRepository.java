package vn.smartprop.collection.external;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ExternalListingRepository extends JpaRepository<ExternalListing, Long> {

    Optional<ExternalListing> findByRecordKey(String recordKey);

    boolean existsByRecordKey(String recordKey);

    List<ExternalListing> findByDuplicateGroup(String duplicateGroup);

    long countByQualityStatus(String qualityStatus);

    long countByIsDuplicateTrue();

    long countByIsProtectedHoldoutTrue();
}
