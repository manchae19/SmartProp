package vn.smartprop.auth;
import org.springframework.data.jpa.repository.*;
import org.springframework.data.repository.query.Param;
public interface SessionRepository extends JpaRepository<AuthSession,String> {
    @Lock(jakarta.persistence.LockModeType.PESSIMISTIC_WRITE) @Query("select s from AuthSession s where s.id=:id") java.util.Optional<AuthSession> lockById(@Param("id") String id);
    @Modifying @Query("update AuthSession s set s.revoked=true where s.userId=:id")
    void revokeAll(@Param("id") Long id);
}
