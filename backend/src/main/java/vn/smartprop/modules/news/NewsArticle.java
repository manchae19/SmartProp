package vn.smartprop.modules.news;

import jakarta.persistence.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import java.time.Instant;

/**
 * Bài viết tin tức đã thu thập. Persistence mapping only.
 *
 * <p>Chỉ lưu metadata + summary ngắn. Không lưu toàn văn, không lưu ảnh báo chí.
 *
 * <p>{@code publishedAt} là ngày publisher đăng và có thể NULL khi feed không cung
 * cấp. Không bao giờ gán {@code fetchedAt} vào {@code publishedAt}.
 */
@Entity @Table(name = "news_articles")
public class NewsArticle {
    public enum PublicationStatus { VISIBLE, HIDDEN }

    @Id @JdbcTypeCode(SqlTypes.CHAR) @Column(name = "id", length = 36, nullable = false) public String id;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name = "source_id", length = 36, nullable = false) public String sourceId;

    @Column(name = "external_id", length = 500) public String externalId;
    @Column(name = "canonical_url", length = 1000, nullable = false) public String canonicalUrl;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name = "canonical_url_hash", length = 64, nullable = false) public String canonicalUrlHash;

    @Column(name = "title", length = 500, nullable = false) public String title;
    @Column(name = "summary", length = 2000) public String summary;

    @Enumerated(EnumType.STRING) @JdbcTypeCode(SqlTypes.VARCHAR)
    @Column(name = "category", length = 40, nullable = false) public NewsSource.Category category;
    @Enumerated(EnumType.STRING) @JdbcTypeCode(SqlTypes.VARCHAR)
    @Column(name = "region", length = 40, nullable = false) public NewsSource.Region region;
    @Column(name = "location_tags", length = 500) public String locationTags;

    @Column(name = "published_at") public Instant publishedAt;
    @Column(name = "fetched_at", nullable = false) public Instant fetchedAt;
    @Column(name = "first_seen_at", nullable = false) public Instant firstSeenAt;
    @Column(name = "last_seen_at", nullable = false) public Instant lastSeenAt;

    @JdbcTypeCode(SqlTypes.CHAR) @Column(name = "content_fingerprint", length = 64) public String contentFingerprint;

    @Enumerated(EnumType.STRING) @JdbcTypeCode(SqlTypes.VARCHAR)
    @Column(name = "publication_status", length = 20, nullable = false) public PublicationStatus publicationStatus;
    @Column(name = "featured", nullable = false) public boolean featured;

    @Column(name = "created_at", nullable = false) public Instant createdAt;
    @Column(name = "updated_at", nullable = false) public Instant updatedAt;
}
