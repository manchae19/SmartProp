package vn.smartprop.modules.favorite;
import org.springframework.data.jpa.repository.JpaRepository;
public interface SavedPropertyRepository extends JpaRepository<SavedProperty,SavedPropertyId> {
}
