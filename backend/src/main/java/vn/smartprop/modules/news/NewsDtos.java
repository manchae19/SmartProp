package vn.smartprop.modules.news;

import java.time.Instant;
import java.util.List;
import jakarta.validation.constraints.*;

/**
 * DTO cho News API.
 *
 * <p>Contract khớp chính xác Frontend PR #37:
 * <ul>
 *   <li>{@code items}, {@code page}, {@code size}, {@code totalElements},
 *       {@code totalPages} — phân trang</li>
 *   <li>{@code lastUpdatedAt}, {@code refreshing}, {@code sources} — metadata snapshot</li>
 *   <li>Article: {@code id}, {@code title}, {@code summary}, {@code category},
 *       {@code articleUrl}, {@code sourceName}, {@code sourceUrl},
 *       {@code publishedAt}, {@code fetchedAt}, {@code locationTags}</li>
 *   <li>Source: {@code id}, {@code name}, {@code feedUrl}, {@code count},
 *       {@code lastSuccessAt}, {@code status}</li>
 * </ul>
 *
 * <p>Không trả {@code verifiedBy}, {@code evidenceReference}, stack trace, IP nội bộ
 * hay cấu hình riêng tư.
 */
public final class NewsDtos {
    private NewsDtos() {}

    /** Một bài viết công khai. */
    public record Article(
        String id,
        String title,
        String summary,
        String category,
        String region,
        String articleUrl,
        String sourceName,
        String sourceUrl,
        Instant publishedAt,
        Instant fetchedAt,
        String locationTags
    ) {}

    /** Metadata một nguồn tin công khai. */
    public record Source(
        String id,
        String name,
        String publisher,
        String websiteUrl,
        String feedUrl,
        long count,
        Instant lastSuccessAt,
        String status
    ) {}

    /** Trang bài viết kèm metadata snapshot. */
    public record Page(
        List<Article> items,
        int page,
        int size,
        long totalElements,
        int totalPages,
        Instant lastUpdatedAt,
        boolean refreshing,
        List<Source> sources
    ) {}

    /** Danh sách nguồn cho {@code /news/sources}. */
    public record Sources(List<Source> sources, Instant lastUpdatedAt) {}

    // ---------- Admin ----------

    public record AdminSource(
        String id,
        String sourceCode,
        String name,
        String publisher,
        String websiteUrl,
        String feedUrl,
        String defaultCategory,
        String defaultRegion,
        String rightsReviewStatus,
        String rightsReference,
        Instant rightsCheckedAt,
        String usageRestrictions,
        boolean allowSummary,
        boolean allowImages,
        boolean enabled,
        int fetchIntervalMinutes,
        Instant lastAttemptAt,
        Instant lastSuccessAt,
        String lastError,
        Instant nextFetchAt,
        int sourceRevision,
        long articleCount
    ) {}

    public record AdminArticle(
        String id,
        String sourceId,
        String sourceName,
        String title,
        String summary,
        String category,
        String region,
        String articleUrl,
        Instant publishedAt,
        Instant fetchedAt,
        Instant firstSeenAt,
        Instant lastSeenAt,
        String publicationStatus,
        boolean featured
    ) {}

    public record AdminRun(
        String id,
        String sourceId,
        String sourceName,
        Instant startedAt,
        Instant finishedAt,
        String status,
        Integer httpStatus,
        int itemsReceived,
        int itemsInserted,
        int itemsUpdated,
        int itemsDuplicate,
        int itemsRejected,
        String errorCode,
        String errorMessage,
        Integer durationMs
    ) {}

    public record Stats(
        long totalSources,
        long enabledSources,
        long approvedSources,
        long pendingReviewSources,
        long totalArticles,
        long visibleArticles,
        long hiddenArticles,
        long daNangArticles,
        Instant lastSuccessAt
    ) {}

    /** Tạo nguồn mới. Luôn tạo ở trạng thái PENDING_REVIEW + disabled. */
    public record CreateSource(
        @NotBlank @Size(max = 40) @Pattern(regexp = "^[a-z0-9][a-z0-9_-]*$") String sourceCode,
        @NotBlank @Size(max = 200) String name,
        @NotBlank @Size(max = 200) String publisher,
        @NotBlank @Size(max = 500) String websiteUrl,
        @NotBlank @Size(max = 500) String feedUrl,
        NewsSource.Category defaultCategory,
        NewsSource.Region defaultRegion,
        @Size(max = 500) String rightsReference,
        @Size(max = 1000) String usageRestrictions,
        @Min(5) @Max(1440) Integer fetchIntervalMinutes
    ) {}

    /**
     * Cập nhật nguồn.
     *
     * <p>{@code rightsReviewStatus} chỉ chuyển sang APPROVED khi có
     * {@code rightsReference} — không duyệt quyền mà không có căn cứ.
     */
    public record UpdateSource(
        @Size(max = 200) String name,
        @Size(max = 200) String publisher,
        @Size(max = 500) String websiteUrl,
        @Size(max = 500) String feedUrl,
        NewsSource.Category defaultCategory,
        NewsSource.Region defaultRegion,
        NewsSource.RightsStatus rightsReviewStatus,
        @Size(max = 500) String rightsReference,
        @Size(max = 1000) String usageRestrictions,
        Boolean allowSummary,
        Boolean allowImages,
        Boolean enabled,
        @Min(5) @Max(1440) Integer fetchIntervalMinutes
    ) {}

    /** Ẩn hoặc hiện một bài. */
    public record VisibilityPatch(@NotNull NewsArticle.PublicationStatus publicationStatus) {}

    /** Đặt hoặc bỏ cờ nổi bật. */
    public record FeaturedPatch(@NotNull Boolean featured) {}
}
