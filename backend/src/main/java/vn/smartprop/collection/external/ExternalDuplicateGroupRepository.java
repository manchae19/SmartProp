package vn.smartprop.collection.external;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ExternalDuplicateGroupRepository extends JpaRepository<ExternalDuplicateGroup, String> {

    List<ExternalDuplicateGroup> findByDistrict(String district);

    List<ExternalDuplicateGroup> findByCategory(String category);
}
