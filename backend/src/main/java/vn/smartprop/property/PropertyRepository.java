package vn.smartprop.property;
import org.springframework.data.jpa.repository.*;
import org.springframework.data.repository.query.Param;
import org.springframework.data.domain.*;
import java.time.Instant;
import java.util.*;
public interface PropertyRepository extends JpaRepository<Property,String>,JpaSpecificationExecutor<Property> {
    @Lock(jakarta.persistence.LockModeType.PESSIMISTIC_WRITE) @Query("select p from Property p where p.id=:id") Optional<Property> lockById(@Param("id") String id);
    Optional<Property> findByIdAndDeletedAtIsNull(String id);
    Page<Property> findByOwnerIdAndDeletedAtIsNull(Long ownerId,Pageable page);
    @Modifying(flushAutomatically=true)
    @Query("update Property p set p.contentVersion=p.contentVersion+1 where p.id=:id and p.contentVersion=:version and p.deletedAt is null")
    int reserveVersion(@Param("id") String id,@Param("version") Integer version);
    @Query("select p from Property p,SavedProperty s where s.id.userId=:userId and s.id.propertyId=p.id and p.status=:status and p.deletedAt is null and (p.expiresAt is null or p.expiresAt>:now) order by s.savedAt desc,p.id desc")
    Page<Property> findVisibleSaved(@Param("userId") Long userId,@Param("now") Instant now,@Param("status") Property.Status status,Pageable page);
}