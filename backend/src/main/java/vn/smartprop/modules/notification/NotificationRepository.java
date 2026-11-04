package vn.smartprop.modules.notification;
import java.time.Instant;
import java.util.Optional;
import org.springframework.data.domain.*;
import org.springframework.data.jpa.repository.*;
import org.springframework.data.repository.query.Param;
public interface NotificationRepository extends JpaRepository<Notification,String> {
    Page<Notification> findByUserId(Long userId,Pageable pageable);
    Page<Notification> findByUserIdAndReadAtIsNull(Long userId,Pageable pageable);
    long countByUserIdAndReadAtIsNull(Long userId);
    // Current locking read avoids a stale pre-update snapshot under MySQL REPEATABLE READ.
    @Lock(jakarta.persistence.LockModeType.PESSIMISTIC_READ)
    Optional<Notification> findByIdAndUserId(String id,Long userId);
    @Modifying(clearAutomatically=true,flushAutomatically=true)
    @Query("update Notification n set n.readAt=:at where n.id=:id and n.userId=:user and n.readAt is null")
    int markRead(@Param("user") Long user,@Param("id") String id,@Param("at") Instant at);
    @Modifying(clearAutomatically=true,flushAutomatically=true)
    @Query("update Notification n set n.readAt=:cutoff where n.userId=:user and n.readAt is null and n.createdAt<=:cutoff")
    int markAllRead(@Param("user") Long user,@Param("cutoff") Instant cutoff);
}
