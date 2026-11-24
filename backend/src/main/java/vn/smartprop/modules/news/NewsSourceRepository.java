package vn.smartprop.modules.news;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface NewsSourceRepository extends JpaRepository<NewsSource, String> {
    Optional<NewsSource> findBySourceCode(String sourceCode);
    Optional<NewsSource> findByFeedUrl(String feedUrl);

    /** Nguồn đủ điều kiện thu thập: đã duyệt quyền VÀ đang bật. */
    @Query("""
        select s from NewsSource s
        where s.enabled = true and s.rightsReviewStatus = vn.smartprop.modules.news.NewsSource$RightsStatus.APPROVED
        """)
    List<NewsSource> findIngestible();

    /** Nguồn đã đến hạn đồng bộ theo {@code fetchIntervalMinutes}. */
    @Query("""
        select s from NewsSource s
        where s.enabled = true
          and s.rightsReviewStatus = vn.smartprop.modules.news.NewsSource$RightsStatus.APPROVED
          and (s.lastAttemptAt is null
               or s.lastAttemptAt < :cutoff)
        """)
    List<NewsSource> findDue(@Param("cutoff") Instant cutoff);

    Page<NewsSource> findAllByOrderByNameAsc(Pageable pageable);
}
