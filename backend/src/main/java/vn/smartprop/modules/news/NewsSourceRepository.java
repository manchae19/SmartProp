package vn.smartprop.modules.news;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.transaction.annotation.Transactional;

public interface NewsSourceRepository extends JpaRepository<NewsSource, String> {
    Optional<NewsSource> findBySourceCode(String sourceCode);
    Optional<NewsSource> findByFeedUrl(String feedUrl);

    /** Nguồn đủ điều kiện thu thập: đã duyệt quyền VÀ đang bật. */
    @Query("""
        select s from NewsSource s
        where s.enabled = true and s.rightsReviewStatus = vn.smartprop.modules.news.NewsSource$RightsStatus.APPROVED
        """)
    List<NewsSource> findIngestible();

    /**
     * Nguồn đã đến hạn đồng bộ: bật, đã duyệt quyền, {@code nextFetchAt} đã qua
     * (hoặc null), và không có lease còn hiệu lực.
     */
    @Query("""
        select s from NewsSource s
        where s.enabled = true
          and s.rightsReviewStatus = vn.smartprop.modules.news.NewsSource$RightsStatus.APPROVED
          and (s.nextFetchAt is null or s.nextFetchAt <= :now)
          and (s.syncLeaseToken is null or s.syncLeaseUntil is null or s.syncLeaseUntil <= :now)
        """)
    List<NewsSource> findDue(@Param("now") Instant now);

    /**
     * Claim lease nguyên tử. Chỉ thành công khi nguồn đang bật, đã duyệt quyền,
     * không có lease còn hiệu lực, và đã đến hạn.
     *
     * <p>Đây là compare-and-set ở tầng DB: hai job chạy đồng thời chỉ một job nhận
     * {@code rows == 1}. Không dựa vào đọc-rồi-ghi ở Java.
     *
     * @return 1 nếu claim thành công, 0 nếu job khác đã giữ lease hoặc nguồn không đủ điều kiện
     */
    @Modifying
    @Transactional
    @Query(value = """
        UPDATE news_sources
        SET sync_lease_token = :token,
            sync_lease_until = :until,
            last_attempt_at = :now,
            updated_at = :now
        WHERE id = :id
          AND enabled = 1
          AND rights_review_status = 'APPROVED'
          AND (next_fetch_at IS NULL OR next_fetch_at <= :now)
          AND (sync_lease_token IS NULL OR sync_lease_until IS NULL OR sync_lease_until <= :now)
        """, nativeQuery = true)
    int claimLease(@Param("id") String id, @Param("token") String token,
                   @Param("until") Instant until, @Param("now") Instant now);

    /**
     * Gia hạn lease khi job còn sống. Chỉ job đang giữ token mới gia hạn được.
     *
     * @return 1 nếu còn giữ lease, 0 nếu đã mất
     */
    @Modifying
    @Transactional
    @Query(value = """
        UPDATE news_sources
        SET sync_lease_until = :until
        WHERE id = :id AND sync_lease_token = :token
        """, nativeQuery = true)
    int renewLease(@Param("id") String id, @Param("token") String token,
                   @Param("until") Instant until);

    /**
     * Giải phóng lease. Chỉ job đang giữ token mới giải phóng được — job cũ không
     * xoá lease của job mới.
     *
     * @return 1 nếu giải phóng thành công, 0 nếu không còn giữ lease
     */
    @Modifying
    @Transactional
    @Query(value = """
        UPDATE news_sources
        SET sync_lease_token = NULL, sync_lease_until = NULL
        WHERE id = :id AND sync_lease_token = :token
        """, nativeQuery = true)
    int releaseLease(@Param("id") String id, @Param("token") String token);

    Page<NewsSource> findAllByOrderByNameAsc(Pageable pageable);

    /** Đếm theo trạng thái quyền — dùng cho stats, không load toàn bảng. */
    @Query("select count(s) from NewsSource s where s.rightsReviewStatus = :status")
    long countByRightsStatus(@Param("status") NewsSource.RightsStatus status);

    @Query("select count(s) from NewsSource s where s.enabled = true")
    long countEnabled();

    @Query("select max(s.lastSuccessAt) from NewsSource s")
    Instant lastSuccessAcrossSources();
}
