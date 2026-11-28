package vn.smartprop.modules.news;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface NewsArticleRepository extends JpaRepository<NewsArticle, String> {

    Optional<NewsArticle> findBySourceIdAndCanonicalUrlHash(String sourceId, String canonicalUrlHash);

    Optional<NewsArticle> findBySourceIdAndExternalId(String sourceId, String externalId);

    /**
     * Bài công khai: nguồn đã duyệt quyền, đang bật, bài VISIBLE.
     *
     * <p>Sắp xếp theo {@code publishedAt} giảm dần, NULL xuống cuối — bài không rõ
     * ngày đăng không được đẩy lên đầu như thể mới nhất.
     */
    @Query("""
        select a from NewsArticle a
        join NewsSource s on s.id = a.sourceId
        where a.publicationStatus = vn.smartprop.modules.news.NewsArticle$PublicationStatus.VISIBLE
          and s.enabled = true
          and s.rightsReviewStatus = vn.smartprop.modules.news.NewsSource$RightsStatus.APPROVED
          and s.rightsReference is not null and length(cast(function('regexp_replace', s.rightsReference, '[[:space:]]', '') as String)) > 0
          and (:category is null or a.category = :category)
          and (:categories is null or a.category in :categories)
          and (:region is null or a.region = :region)
          and (:keyword is null
               or lower(a.title) like :keyword escape '\\'
               or (s.allowSummary = true
                   and lower(a.summary) like :keyword escape '\\'))
        order by a.publishedAt desc nulls last, a.firstSeenAt desc, a.id desc
        """)
    Page<NewsArticle> findPublic(@Param("category") NewsSource.Category category,
                                 @Param("categories") java.util.List<NewsSource.Category> categories,
                                 @Param("region") NewsSource.Region region,
                                 @Param("keyword") String keyword,
                                 Pageable pageable);

    /**
     * Bài công khai sắp xếp cũ nhất trước — thực hiện tại DB, trước pagination.
     *
     * <p>Bài không rõ ngày đăng ({@code publishedAt IS NULL}) luôn xuống cuối ở cả
     * hai chiều sắp xếp: chúng không thể so sánh thời gian nên không được trộn vào
     * thứ tự thời gian. Tie-breaker {@code firstSeenAt} giữ thứ tự ổn định giữa trang.
     */
    @Query("""
        select a from NewsArticle a
        join NewsSource s on s.id = a.sourceId
        where a.publicationStatus = vn.smartprop.modules.news.NewsArticle$PublicationStatus.VISIBLE
          and s.enabled = true
          and s.rightsReviewStatus = vn.smartprop.modules.news.NewsSource$RightsStatus.APPROVED
          and s.rightsReference is not null and length(cast(function('regexp_replace', s.rightsReference, '[[:space:]]', '') as String)) > 0
          and (:category is null or a.category = :category)
          and (:categories is null or a.category in :categories)
          and (:region is null or a.region = :region)
          and (:keyword is null
               or lower(a.title) like :keyword escape '\\'
               or (s.allowSummary = true
                   and lower(a.summary) like :keyword escape '\\'))
        order by a.publishedAt asc nulls last, a.firstSeenAt asc, a.id asc
        """)
    Page<NewsArticle> findPublicOldest(@Param("category") NewsSource.Category category,
                                       @Param("categories") java.util.List<NewsSource.Category> categories,
                                       @Param("region") NewsSource.Region region,
                                       @Param("keyword") String keyword,
                                       Pageable pageable);

    /** Bài nổi bật: ưu tiên featured, sau đó Đà Nẵng, sau đó mới nhất. */
    @Query("""
        select a from NewsArticle a
        join NewsSource s on s.id = a.sourceId
        where a.publicationStatus = vn.smartprop.modules.news.NewsArticle$PublicationStatus.VISIBLE
          and s.enabled = true
          and s.rightsReviewStatus = vn.smartprop.modules.news.NewsSource$RightsStatus.APPROVED
          and s.rightsReference is not null and length(cast(function('regexp_replace', s.rightsReference, '[[:space:]]', '') as String)) > 0
        order by a.featured desc,
                 case when a.region = vn.smartprop.modules.news.NewsSource$Region.DA_NANG then 0 else 1 end,
                 a.publishedAt desc nulls last,
                 a.firstSeenAt desc, a.id desc
        """)
    Page<NewsArticle> findFeatured(Pageable pageable);

    /** Thời điểm bài công khai mới nhất được thấy — dùng cho {@code lastUpdatedAt}. */
    @Query("""
        select max(a.lastSeenAt) from NewsArticle a
        join NewsSource s on s.id = a.sourceId
        where a.publicationStatus = vn.smartprop.modules.news.NewsArticle$PublicationStatus.VISIBLE
          and s.enabled = true
          and s.rightsReviewStatus = vn.smartprop.modules.news.NewsSource$RightsStatus.APPROVED
          and s.rightsReference is not null and length(cast(function('regexp_replace', s.rightsReference, '[[:space:]]', '') as String)) > 0
        """)
    Instant lastPublicUpdate();

    /** Số bài công khai của một nguồn — cho metadata nguồn tin. */
    @Query("""
        select count(a) from NewsArticle a
        where a.sourceId = :sourceId
          and a.publicationStatus = vn.smartprop.modules.news.NewsArticle$PublicationStatus.VISIBLE
        """)
    long countPublicBySource(@Param("sourceId") String sourceId);

    @org.springframework.data.jpa.repository.Modifying(flushAutomatically = true, clearAutomatically = false)
    @Query("update NewsArticle a set a.publicationStatus = vn.smartprop.modules.news.NewsArticle$PublicationStatus.HIDDEN, a.updatedAt = :now where a.sourceId = :sourceId")
    int hideBySource(@Param("sourceId") String sourceId, @Param("now") Instant now);

    @org.springframework.data.jpa.repository.Modifying(flushAutomatically = true, clearAutomatically = true)
    @Query("update NewsArticle a set a.featured = :featured, a.updatedAt = :now where a.id = :id")
    int updateFeatured(@Param("id") String id, @Param("featured") boolean featured, @Param("now") Instant now);

    @org.springframework.data.jpa.repository.Modifying(flushAutomatically = true, clearAutomatically = true)
    @Query("update NewsArticle a set a.publicationStatus = :status, a.updatedAt = :now where a.id = :id")
    int updateVisibility(@Param("id") String id, @Param("status") NewsArticle.PublicationStatus status, @Param("now") Instant now);

    List<NewsArticle> findBySourceId(String sourceId);

    Page<NewsArticle> findAllByOrderByFirstSeenAtDesc(Pageable pageable);

    /**
     * Cập nhật metadata ingestion được phép sửa — targeted UPDATE.
     *
     * <p>Chỉ đụng {@code last_seen_at}, {@code fetched_at}, {@code updated_at}, và
     * tuỳ chọn {@code published_at} (khi trước đó NULL) và {@code summary} (khi quyền
     * cho phép). KHÔNG đụng {@code publication_status} hay {@code featured} — đó là
     * quyết định của admin, và một entity save toàn phần sẽ ghi đè chúng bằng snapshot
     * cũ.
     *
     * @return số dòng cập nhật
     */
    @org.springframework.data.jpa.repository.Modifying(flushAutomatically = true)
    @org.springframework.transaction.annotation.Transactional
    @Query("""
        update NewsArticle a
        set a.lastSeenAt = :now,
            a.fetchedAt = :now,
            a.updatedAt = :now,
            a.publishedAt = coalesce(a.publishedAt, :publishedAt),
            a.summary = coalesce(:summary, a.summary)
        where a.id = :id
        """)
    int touchSeen(@Param("id") String id, @Param("now") Instant now,
                  @Param("publishedAt") Instant publishedAt,
                  @Param("summary") String summary);

    /** Đếm theo trạng thái hiển thị — aggregate, không load bảng. */
    long countByPublicationStatus(NewsArticle.PublicationStatus status);

    /** Đếm theo khu vực — aggregate, không load bảng. */
    long countByRegion(NewsSource.Region region);
}
