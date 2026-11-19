package vn.smartprop.modules.media;

import com.fasterxml.jackson.databind.JsonNode;

import java.math.BigDecimal;
import java.time.Instant;

/**
 * Persisted YOLOv8 object analysis for one property image.
 *
 * <p><b>Deliberately NOT a JPA entity.</b> Hibernate's {@code ddl-auto=validate}
 * checks every mapped entity at startup, regardless of any feature flag. Mapping
 * this table would make the whole backend refuse to start on a database that has
 * not yet applied V22 — which is exactly the state of MySQL 3306 today. The
 * existing {@link ImageScanRecovery} solves the same problem the same way: plain
 * JDBC, tolerant of a schema that may not exist yet.
 *
 * <p>Persistence lives in {@link PropertyImageAnalysisRepository}, which talks to
 * the table through {@code JdbcTemplate} and reports "table absent" instead of
 * throwing.
 *
 * <p>Nothing here is a moderation decision. A detection count never rejects,
 * publishes or flags a listing.
 */
public class PropertyImageAnalysis {
    public String id;
    public String propertyId;
    public String propertyImageId;
    public String analysisStatus;
    public String algorithmVersion;
    public String modelVersion;
    public int detectionCount;
    public JsonNode detections;
    public JsonNode countsByLabel;
    /** Full document-likeness hint (fractions + reason); null when not computed. */
    public JsonNode documentHint;
    public boolean documentLike;
    public Integer imageWidth;
    public Integer imageHeight;
    public String imageFormat;
    public String imageSha256;
    public BigDecimal inferenceMs;
    public String errorCode;
    /** How many times analysis has been attempted; bounds automatic retries. */
    public int attemptCount;
    public Instant analyzedAt;
    public Instant createdAt;
    public Instant updatedAt;
}
