package vn.smartprop.auth;
import org.springframework.data.jpa.repository.*;
import org.springframework.data.repository.query.Param;
public interface SessionRepository extends JpaRepository<AuthSession,String> {
    @Lock(jakarta.persistence.LockModeType.PESSIMISTIC_WRITE) @Query("select s from AuthSession s where s.id=:id") java.util.Optional<AuthSession> lockById(@Param("id") String id);
    @org.springframework.transaction.annotation.Transactional
    @Modifying @Query("update AuthSession s set s.lastUsedAt=:now where s.id=:id and s.revoked=false and s.expiresAt>:now and (s.lastUsedAt>:cutoff or s.lastUsedAt is null and s.createdAt>:cutoff)")
    int touchActivity(@Param("id") String id,@Param("now") java.time.Instant now,@Param("cutoff") java.time.Instant cutoff);
    @Modifying @Query("update AuthSession s set s.revoked=true where s.userId=:id")
    void revokeAll(@Param("id") Long id);
}
