package vn.smartprop.audit;
import org.springframework.data.jpa.repository.*;
public interface AuditLogRepository extends JpaRepository<AuditLog,String>,JpaSpecificationExecutor<AuditLog> {}