package vn.smartprop.modules.news;

import jakarta.persistence.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import java.time.Instant;

/**
 * Nguồn tin RSS/Atom. Persistence mapping only.
 *
 * <p>Quyền sử dụng ({@code rightsReviewStatus}) tách khỏi trạng thái bật/tắt
 * ({@code enabled}). Chỉ nguồn {@code APPROVED} + {@code enabled} mới được thu thập.
 * Nguồn mới mặc định {@code PENDING_REVIEW} + {@code enabled=false}.
 */
@Entity @Table(name = "news_sources")
public class NewsSource {
    public enum RightsStatus { PENDING_REVIEW, APPROVED, REJECTED }
    public enum Category { MARKET, PLANNING, LEGAL, INFRASTRUCTURE, PROJECTS, RESIDENTIAL, COMMERCIAL, OTHER }
    public enum Region { DA_NANG, CENTRAL, VIETNAM, UNKNOWN }

    @Id @JdbcTypeCode(SqlTypes.CHAR) @Column(name = "id", length = 36, nullable = false) public String id;
    @Column(name = "source_code", length = 40, nullable = false) public String sourceCode;
    @Column(name = "name", length = 200, nullable = false) public String name;
    @Column(name = "publisher", length = 200, nullable = false) public String publisher;
    @Column(name = "website_url", length = 500, nullable = false) public String websiteUrl;
    @Column(name = "feed_url", length = 500, nullable = false) public String feedUrl;

    @Enumerated(EnumType.STRING) @JdbcTypeCode(SqlTypes.VARCHAR)
    @Column(name = "default_category", length = 40, nullable = false) public Category defaultCategory;
    @Enumerated(EnumType.STRING) @JdbcTypeCode(SqlTypes.VARCHAR)
    @Column(name = "default_region", length = 40, nullable = false) public Region defaultRegion;

    @Enumerated(EnumType.STRING) @JdbcTypeCode(SqlTypes.VARCHAR)
    @Column(name = "rights_review_status", length = 20, nullable = false) public RightsStatus rightsReviewStatus;
    @Column(name = "rights_reference", length = 500) public String rightsReference;
    @Column(name = "rights_checked_at") public Instant rightsCheckedAt;
    @Column(name = "usage_restrictions", length = 1000) public String usageRestrictions;

    /** Quyền theo từng loại nội dung. Mặc định: summary có, ảnh không. */
    @Column(name = "allow_summary", nullable = false) public boolean allowSummary;
    @Column(name = "allow_images", nullable = false) public boolean allowImages;

    @Column(name = "enabled", nullable = false) public boolean enabled;
    @Column(name = "fetch_interval_minutes", nullable = false) public short fetchIntervalMinutes;

    /** Lease chống hai job fetch cùng nguồn. Token do job đang giữ. */
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name = "sync_lease_token", length = 36) public String syncLeaseToken;
    @Column(name = "sync_lease_until") public Instant syncLeaseUntil;

    /** Thời điểm được phép fetch tiếp — thực thi Retry-After và backoff. */
    @Column(name = "next_fetch_at") public Instant nextFetchAt;

    /** Tăng mỗi lần admin sửa nguồn; job đang chạy phát hiện thay đổi. */
    @Column(name = "source_revision", nullable = false) public int sourceRevision;
    @Column(name = "consecutive_failures", nullable = false) public short consecutiveFailures;

    @Column(name = "last_attempt_at") public Instant lastAttemptAt;
    @Column(name = "last_success_at") public Instant lastSuccessAt;
    @Column(name = "last_error", length = 500) public String lastError;

    @Column(name = "http_etag", length = 200) public String httpEtag;
    @Column(name = "http_last_modified", length = 100) public String httpLastModified;

    @Column(name = "created_at", nullable = false) public Instant createdAt;
    @Column(name = "updated_at", nullable = false) public Instant updatedAt;

    /** Nguồn chỉ được thu thập khi đã duyệt quyền VÀ được bật. */
    public boolean ingestible() {
        return enabled && rightsReviewStatus == RightsStatus.APPROVED;
    }

    /** Lease còn hiệu lực tại thời điểm {@code now}. */
    public boolean leaseActive(Instant now) {
        return syncLeaseToken != null && syncLeaseUntil != null && syncLeaseUntil.isAfter(now);
    }

    /** Đã đến hạn fetch tại thời điểm {@code now}. */
    public boolean due(Instant now) {
        return nextFetchAt == null || !nextFetchAt.isAfter(now);
    }
}
