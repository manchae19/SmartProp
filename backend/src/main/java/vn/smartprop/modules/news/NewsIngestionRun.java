package vn.smartprop.modules.news;

import jakarta.persistence.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import java.time.Instant;

/** Lịch sử một lần đồng bộ nguồn tin. Persistence mapping only. */
@Entity @Table(name = "news_ingestion_runs")
public class NewsIngestionRun {
    public enum Status { RUNNING, SUCCESS, PARTIAL_SUCCESS, FAILED, NOT_MODIFIED, SKIPPED }

    @Id @JdbcTypeCode(SqlTypes.CHAR) @Column(name = "id", length = 36, nullable = false) public String id;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name = "source_id", length = 36, nullable = false) public String sourceId;

    @Column(name = "started_at", nullable = false) public Instant startedAt;
    @Column(name = "finished_at") public Instant finishedAt;

    @Enumerated(EnumType.STRING) @JdbcTypeCode(SqlTypes.VARCHAR)
    @Column(name = "status", length = 20, nullable = false) public Status status;

    @Column(name = "http_status") public Short httpStatus;
    @Column(name = "items_received", nullable = false) public int itemsReceived;
    @Column(name = "items_inserted", nullable = false) public int itemsInserted;
    @Column(name = "items_updated", nullable = false) public int itemsUpdated;
    @Column(name = "items_duplicate", nullable = false) public int itemsDuplicate;
    @Column(name = "items_rejected", nullable = false) public int itemsRejected;

    @Column(name = "error_code", length = 60) public String errorCode;
    @Column(name = "error_message", length = 500) public String errorMessage;
    @Column(name = "duration_ms") public Integer durationMs;
}
