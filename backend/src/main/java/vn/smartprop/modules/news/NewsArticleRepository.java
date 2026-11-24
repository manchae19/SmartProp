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
          and (:category is null or a.category = :category)
          and (:categories is null or a.category in :categories)
          and (:region is null or a.region = :region)
          and (:keyword is null
               or lower(a.title) like :keyword escape '\\'
               or lower(a.summary) like :keyword escape '\\')
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
          and (:category is null or a.category = :category)
          and (:categories is null or a.category in :categories)
          and (:region is null or a.region = :region)
          and (:keyword is null
               or lower(a.title) like :keyword escape '\\'
               or lower(a.summary) like :keyword escape '\\')
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
        order by a.featured desc,
                 case when a.region = vn.smartprop.modules.news.NewsSource$Region.DA_NANG then 0 else 1 end,
                 a.publishedAt desc nulls last,
                 a.firstSeenAt desc
        """)
    Page<NewsArticle> findFeatured(Pageable pageable);

    /** Thời điểm bài công khai mới nhất được thấy — dùng cho {@code lastUpdatedAt}. */
    @Query("""
        select max(a.lastSeenAt) from NewsArticle a
        join NewsSource s on s.id = a.sourceId
        where a.publicationStatus = vn.smartprop.modules.news.NewsArticle$PublicationStatus.VISIBLE
          and s.enabled = true
          and s.rightsReviewStatus = vn.smartprop.modules.news.NewsSource$RightsStatus.APPROVED
        """)
    Instant lastPublicUpdate();

    /** Số bài công khai của một nguồn — cho metadata nguồn tin. */
    @Query("""
        select count(a) from NewsArticle a
        where a.sourceId = :sourceId
          and a.publicationStatus = vn.smartprop.modules.news.NewsArticle$PublicationStatus.VISIBLE
        """)
    long countPublicBySource(@Param("sourceId") String sourceId);

    List<NewsArticle> findBySourceId(String sourceId);

    Page<NewsArticle> findAllByOrderByFirstSeenAtDesc(Pageable pageable);

    /** Đếm theo trạng thái hiển thị — aggregate, không load bảng. */
    long countByPublicationStatus(NewsArticle.PublicationStatus status);

    /** Đếm theo khu vực — aggregate, không load bảng. */
    long countByRegion(NewsSource.Region region);
}
