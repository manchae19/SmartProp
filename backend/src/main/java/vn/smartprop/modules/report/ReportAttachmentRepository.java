package vn.smartprop.modules.report;
import java.util.*;
import org.springframework.data.jpa.repository.JpaRepository;
public interface ReportAttachmentRepository extends JpaRepository<ReportAttachment,String> {
    List<ReportAttachment> findByReportIdOrderByCreatedAtAscIdAsc(String reportId);
    Optional<ReportAttachment> findByIdAndReportId(String id,String reportId);
    long countByReportId(String reportId);
}