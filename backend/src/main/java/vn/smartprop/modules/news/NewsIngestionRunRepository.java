package vn.smartprop.modules.news;

import java.util.List;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface NewsIngestionRunRepository extends JpaRepository<NewsIngestionRun, String> {
    List<NewsIngestionRun> findTop20BySourceIdOrderByStartedAtDesc(String sourceId);
    Page<NewsIngestionRun> findAllByOrderByStartedAtDesc(Pageable pageable);
    boolean existsBySourceIdAndStatus(String sourceId, NewsIngestionRun.Status status);
}
