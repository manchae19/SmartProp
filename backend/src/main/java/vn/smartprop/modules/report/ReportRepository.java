package vn.smartprop.modules.report;
import java.util.Optional;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.*;
import org.springframework.data.repository.query.Param;
import org.springframework.data.domain.*;
public interface ReportRepository extends JpaRepository<Report,String>,JpaSpecificationExecutor<Report> {
    Page<Report> findByReporterId(Long reporterId,Pageable pageable);
    @Lock(LockModeType.PESSIMISTIC_WRITE) @Query("select r from Report r where r.id=:id") Optional<Report> lockById(@Param("id") String id);
    long countByStatus(Report.Status status);
}