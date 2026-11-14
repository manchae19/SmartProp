package vn.smartprop.modules.media;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.math.BigDecimal;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.Collection;
import java.util.List;
import java.util.Optional;

/**
 * JDBC persistence for {@link PropertyImageAnalysis}.
 *
 * <p>Plain {@code JdbcTemplate} on purpose: the table only exists after V22 is
 * applied, and a JPA mapping would make Hibernate's startup validation fail on
 * every database that has not migrated yet. Every read reports "table absent"
 * as an empty result instead of throwing, so the backend starts and serves
 * normally on a V21 database with the feature flag off.
 */
@Repository
public class PropertyImageAnalysisRepository {
    private static final Logger log = LoggerFactory.getLogger(PropertyImageAnalysisRepository.class);

    private static final String COLUMNS =
        "id, property_id, property_image_id, analysis_status, algorithm_version, model_version, "
        + "detection_count, detections, counts_by_label, document_hint, document_like, "
        + "image_width, image_height, image_format, image_sha256, inference_ms, error_code, attempt_count, "
        + "analyzed_at, created_at, updated_at";

    private final JdbcTemplate jdbc;
    private final ObjectMapper mapper;
    private volatile Boolean tablePresent;

    public PropertyImageAnalysisRepository(JdbcTemplate jdbc, ObjectMapper mapper) {
        this.jdbc = jdbc;
        this.mapper = mapper;
    }

    /**
     * Whether V22 has been applied.
     *
     * <p>Cached after the first successful probe: the answer only changes when a
     * migration runs, which never happens while the application is up.
     */
    public boolean tablePresent() {
        Boolean cached = tablePresent;
        if (cached != null) return cached;
        try {
            Integer count = jdbc.queryForObject(
                "SELECT COUNT(*) FROM information_schema.tables "
                    + "WHERE table_schema = DATABASE() AND table_name = 'property_image_analysis'",
                Integer.class);
            boolean present = count != null && count > 0;
            tablePresent = present;
            if (!present) {
                log.info("property_image_analysis is absent (V22 not applied); object analysis stays inactive.");
            }
            return present;
        } catch (RuntimeException error) {
            // Never let a metadata probe break startup.
            log.warn("Could not probe property_image_analysis: {}", error.getClass().getSimpleName());
            return false;
        }
    }

    public List<PropertyImageAnalysis> findByPropertyId(String propertyId) {
        if (!tablePresent()) return List.of();
        return jdbc.query(
            "SELECT " + COLUMNS + " FROM property_image_analysis WHERE property_id = ? ORDER BY created_at ASC",
            this::map, propertyId);
    }

    public Optional<PropertyImageAnalysis> findByPropertyImageIdAndModelVersion(String propertyImageId, String modelVersion) {
        if (!tablePresent()) return Optional.empty();
        List<PropertyImageAnalysis> rows = jdbc.query(
            "SELECT " + COLUMNS + " FROM property_image_analysis "
                + "WHERE property_image_id = ? AND model_version = ?",
            this::map, propertyImageId, modelVersion);
        return rows.stream().findFirst();
    }

    public List<PropertyImageAnalysis> findCompletedWithFindings() {
        if (!tablePresent()) return List.of();
        return jdbc.query(
            "SELECT " + COLUMNS + " FROM property_image_analysis "
                + "WHERE analysis_status = 'COMPLETED' AND (detection_count > 0 OR document_like = TRUE)",
            this::map);
    }

    public List<PropertyImageAnalysis> findByPropertyIdInAndStatusIn(Collection<String> propertyIds, Collection<String> statuses) {
        if (!tablePresent() || propertyIds.isEmpty() || statuses.isEmpty()) return List.of();
        String propertyPlaceholders = String.join(",", java.util.Collections.nCopies(propertyIds.size(), "?"));
        String statusPlaceholders = String.join(",", java.util.Collections.nCopies(statuses.size(), "?"));
        Object[] args = java.util.stream.Stream.concat(propertyIds.stream(), statuses.stream()).toArray();
        return jdbc.query(
            "SELECT " + COLUMNS + " FROM property_image_analysis "
                + "WHERE property_id IN (" + propertyPlaceholders + ") "
                + "AND analysis_status IN (" + statusPlaceholders + ")",
            this::map, args);
    }

    /**
     * Insert or update one row.
     *
     * <p>The natural key is {@code (property_image_id, model_version)}, but a row
     * is created with a {@code "pending"} placeholder before the model answers.
     * Matching on that key alone would miss the row once the real version is
     * known, so the update also matches by id — the row's stable identity.
     */
    public void save(PropertyImageAnalysis row) {
        if (!tablePresent()) return;
        Instant now = Instant.now();
        if (row.createdAt == null) row.createdAt = now;
        row.updatedAt = now;
        int updated = jdbc.update(
            "UPDATE property_image_analysis SET analysis_status=?, algorithm_version=?, model_version=?, "
                + "detection_count=?, detections=?, counts_by_label=?, document_hint=?, document_like=?, "
                + "image_width=?, image_height=?, image_format=?, image_sha256=?, inference_ms=?, "
                + "error_code=?, attempt_count=?, analyzed_at=?, updated_at=? "
                + "WHERE id=?",
            row.analysisStatus, row.algorithmVersion, row.modelVersion,
            row.detectionCount, json(row.detections), json(row.countsByLabel), json(row.documentHint), row.documentLike,
            row.imageWidth, row.imageHeight, row.imageFormat, row.imageSha256, row.inferenceMs,
            row.errorCode, row.attemptCount, timestamp(row.analyzedAt), timestamp(row.updatedAt),
            row.id);
        if (updated > 0) return;
        jdbc.update(
            "INSERT INTO property_image_analysis (" + COLUMNS + ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            row.id, row.propertyId, row.propertyImageId, row.analysisStatus, row.algorithmVersion, row.modelVersion,
            row.detectionCount, json(row.detections), json(row.countsByLabel), json(row.documentHint), row.documentLike,
            row.imageWidth, row.imageHeight, row.imageFormat, row.imageSha256, row.inferenceMs,
            row.errorCode, row.attemptCount, timestamp(row.analyzedAt), timestamp(row.createdAt), timestamp(row.updatedAt));
    }

    public void saveAll(List<PropertyImageAnalysis> rows) {
        if (!tablePresent()) return;
        for (PropertyImageAnalysis row : rows) save(row);
    }

    private String json(JsonNode node) {
        if (node == null) return null;
        try {
            return mapper.writeValueAsString(node);
        } catch (Exception error) {
            return null;
        }
    }

    private static Timestamp timestamp(Instant value) {
        return value == null ? null : Timestamp.from(value);
    }

    private static Instant instant(Timestamp value) {
        return value == null ? null : value.toInstant();
    }

    private PropertyImageAnalysis map(ResultSet rs, int index) throws SQLException {
        PropertyImageAnalysis row = new PropertyImageAnalysis();
        row.id = rs.getString("id");
        row.propertyId = rs.getString("property_id");
        row.propertyImageId = rs.getString("property_image_id");
        row.analysisStatus = rs.getString("analysis_status");
        row.algorithmVersion = rs.getString("algorithm_version");
        row.modelVersion = rs.getString("model_version");
        row.detectionCount = rs.getInt("detection_count");
        row.detections = readJson(rs.getString("detections"));
        row.countsByLabel = readJson(rs.getString("counts_by_label"));
        row.documentHint = readJson(rs.getString("document_hint"));
        row.documentLike = rs.getBoolean("document_like");
        row.imageWidth = (Integer) rs.getObject("image_width");
        row.imageHeight = (Integer) rs.getObject("image_height");
        row.imageFormat = rs.getString("image_format");
        row.imageSha256 = rs.getString("image_sha256");
        BigDecimal inference = rs.getBigDecimal("inference_ms");
        row.inferenceMs = inference;
        row.errorCode = rs.getString("error_code");
        row.attemptCount = rs.getInt("attempt_count");
        row.analyzedAt = instant(rs.getTimestamp("analyzed_at"));
        row.createdAt = instant(rs.getTimestamp("created_at"));
        row.updatedAt = instant(rs.getTimestamp("updated_at"));
        return row;
    }

    private JsonNode readJson(String value) {
        if (value == null || value.isBlank()) return null;
        try {
            return mapper.readTree(value);
        } catch (Exception error) {
            return null;
        }
    }
}
