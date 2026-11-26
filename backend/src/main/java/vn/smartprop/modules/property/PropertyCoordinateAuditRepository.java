package vn.smartprop.modules.property;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.HexFormat;
import java.util.List;
import java.util.Optional;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

/**
 * Read/write access for {@code property_coordinate_audit}.
 *
 * <p>Mọi thao tác ghi đều nằm trong transaction của caller. Bản ghi hiện hành là bản
 * có {@code superseded_at IS NULL}; ràng buộc {@code uq_coord_audit_current} bảo đảm
 * mỗi tin chỉ có tối đa một bản như vậy.
 */
@Repository
public class PropertyCoordinateAuditRepository {
    private final JdbcTemplate jdbc;
    private final boolean schemaAvailable;

    public PropertyCoordinateAuditRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
        Integer tables = jdbc.queryForObject("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = DATABASE() AND table_name = 'property_coordinate_audit'
            """, Integer.class);
        this.schemaAvailable = Integer.valueOf(1).equals(tables);
        if (!schemaAvailable) {
            System.getLogger(PropertyCoordinateAuditRepository.class.getName()).log(
                System.Logger.Level.WARNING,
                "Coordinate provenance is disabled: property_coordinate_audit is absent in schema {0}.",
                jdbc.queryForObject("SELECT DATABASE()", String.class));
        }
    }

    public boolean schemaAvailable() { return schemaAvailable; }

    /**
     * Fingerprint của snapshot tọa độ + địa chỉ.
     *
     * <p><b>Không bao gồm {@code validatorScopeVersion}.</b> Phiên bản dữ liệu địa giới
     * là thuộc tính của kết quả validation, không phải của vị trí người dùng đã chọn.
     * Gộp nó vào fingerprint khiến việc cập nhật ranh giới hành chính trông giống như
     * người dùng đã di chuyển điểm — tạo revision giả và làm mất xác minh không cần thiết.
     *
     * <p>Khi validator scope đổi, {@link #record} phát hiện qua cột
     * {@code validator_scope_version} riêng và chỉ cập nhật lại kết quả geographic
     * validation trên bản ghi hiện hành, không tạo revision mới.
     *
     * <p>Đổi bất kỳ thành phần nào dưới đây đều làm fingerprint đổi → audit cũ bị
     * supersede: tọa độ, địa chỉ, quận, phường.
     *
     * <p>Tọa độ được làm tròn 7 chữ số thập phân (≈1 cm) trước khi hash để sai số biểu
     * diễn DOUBLE không làm fingerprint khác nhau cho cùng một điểm.
     */
    public static String fingerprint(double latitude, double longitude,
                                     String address, String district, String ward) {
        String payload = String.format(java.util.Locale.ROOT, "%.7f|%.7f|%s|%s|%s",
            latitude, longitude,
            nullToEmpty(address), nullToEmpty(district), nullToEmpty(ward));
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(payload.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 không khả dụng", e);
        }
    }

    /**
     * Fingerprint dùng cho backfill — cùng công thức với {@link #fingerprint}, nhận
     * tọa độ đã ở dạng chuỗi DECIMAL(10,7) để SQL và Java cho cùng kết quả.
     *
     * <p>Backfill dùng chính hàm này (qua SQL tương đương) nên fingerprint của bản
     * backfill khớp runtime khi tọa độ và địa chỉ không đổi. Nhờ vậy lần đầu người
     * dùng sửa tiêu đề không tạo revision mới.
     */
    public static String fingerprintFromDecimal(String latitude, String longitude,
                                                String address, String district, String ward) {
        String payload = String.format(java.util.Locale.ROOT, "%s|%s|%s|%s|%s",
            latitude, longitude,
            nullToEmpty(address), nullToEmpty(district), nullToEmpty(ward));
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(payload.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 không khả dụng", e);
        }
    }

    private static String nullToEmpty(String value) { return value == null ? "" : value.strip(); }

    /** Bản ghi audit hiện hành của một tin, nếu có. */
    public Optional<PropertyCoordinateAudit.Status> current(String propertyId) {
        List<PropertyCoordinateAudit.Status> rows = jdbc.query("""
            SELECT coordinate_source, accuracy_level, accuracy_meters, verification_status,
                   verification_method, verified_at, geographic_validation_status,
                   geographic_validation_note, revision, created_at
            FROM property_coordinate_audit
            WHERE property_id = ? AND superseded_at IS NULL
            """,
            (rs, i) -> PropertyCoordinateAudit.derive(
                rs.getString("coordinate_source"),
                rs.getString("accuracy_level"),
                rs.getObject("accuracy_meters", java.math.BigDecimal.class) == null ? null
                    : rs.getBigDecimal("accuracy_meters").doubleValue(),
                rs.getString("verification_status"),
                rs.getString("verification_method"),
                rs.getObject("verified_at", java.time.LocalDateTime.class) == null ? null
                    : rs.getTimestamp("verified_at").toInstant(),
                rs.getString("geographic_validation_status"),
                rs.getString("geographic_validation_note"),
                rs.getInt("revision"),
                rs.getTimestamp("created_at") == null ? null
                    : rs.getTimestamp("created_at").toInstant()),
            propertyId);
        return rows.stream().findFirst();
    }

    /** Current eligibility metadata for one public property-search page. */
    public java.util.Map<String, PropertyCoordinateAudit.Status> currentForProperties(List<String> propertyIds) {
        if (propertyIds == null || propertyIds.isEmpty()) return java.util.Map.of();
        String placeholders = String.join(",", java.util.Collections.nCopies(propertyIds.size(), "?"));
        return jdbc.query("""
            SELECT property_id, coordinate_source, accuracy_level, accuracy_meters, verification_status,
                   verification_method, verified_at, geographic_validation_status,
                   geographic_validation_note, revision, created_at
            FROM property_coordinate_audit
            WHERE property_id IN (""" + placeholders + ") AND superseded_at IS NULL",
            rs -> {
                var result = new java.util.LinkedHashMap<String, PropertyCoordinateAudit.Status>();
                while (rs.next()) result.put(rs.getString("property_id"), status(rs));
                return java.util.Map.copyOf(result);
            }, propertyIds.toArray());
    }

    private static PropertyCoordinateAudit.Status status(java.sql.ResultSet rs) throws java.sql.SQLException {
        return PropertyCoordinateAudit.derive(
            rs.getString("coordinate_source"),
            rs.getString("accuracy_level"),
            rs.getBigDecimal("accuracy_meters") == null ? null : rs.getBigDecimal("accuracy_meters").doubleValue(),
            rs.getString("verification_status"),
            rs.getString("verification_method"),
            rs.getTimestamp("verified_at") == null ? null : rs.getTimestamp("verified_at").toInstant(),
            rs.getString("geographic_validation_status"),
            rs.getString("geographic_validation_note"),
            rs.getInt("revision"),
            rs.getTimestamp("created_at") == null ? null : rs.getTimestamp("created_at").toInstant());
    }

    /** Fingerprint của bản ghi hiện hành — dùng để phát hiện tọa độ đã đổi. */
    public Optional<String> currentFingerprint(String propertyId) {
        List<String> rows = jdbc.queryForList("""
            SELECT coordinate_fingerprint FROM property_coordinate_audit
            WHERE property_id = ? AND superseded_at IS NULL
            """, String.class, propertyId);
        return rows.stream().findFirst();
    }

    /** Revision lớn nhất đã dùng cho tin này (kể cả bản đã superseded). */
    public int maxRevision(String propertyId) {
        Integer value = jdbc.queryForObject("""
            SELECT COALESCE(MAX(revision), 0) FROM property_coordinate_audit
            WHERE property_id = ?
            """, Integer.class, propertyId);
        return value == null ? 0 : value;
    }

    /**
     * Kết thúc hiệu lực bản ghi hiện hành. Trả số dòng cập nhật — 0 nghĩa là không có
     * bản hiện hành (đã bị thay thế bởi transaction khác).
     */
    public int supersedeCurrent(String propertyId, PropertyCoordinateAudit.SupersedeReason reason) {
        return jdbc.update("""
            UPDATE property_coordinate_audit
            SET superseded_at = UTC_TIMESTAMP(6), superseded_reason = ?
            WHERE property_id = ? AND superseded_at IS NULL
            """, reason.name(), propertyId);
    }

    /** Ghi một bản ghi audit mới. Caller chịu trách nhiệm supersede bản cũ trước. */
    public void insert(String id, String propertyId, int revision,
                       double latitude, double longitude, String fingerprint,
                       String address, String district, String ward,
                       PropertyCoordinateAudit.Source source, String sourceReference,
                       Long sourceRecordedBy,
                       PropertyCoordinateAudit.Accuracy accuracy, Double accuracyMeters,
                       String accuracyMethod,
                       PropertyCoordinateAudit.Verification verification,
                       PropertyCoordinateAudit.VerificationMethod verificationMethod,
                       Instant verifiedAt, Long verifiedBy, String evidenceReference,
                       String geographicStatus, String geographicNote,
                       String validatorScopeVersion) {
        jdbc.update("""
            INSERT INTO property_coordinate_audit (
              id, property_id, revision, audited_latitude, audited_longitude, srid,
              coordinate_fingerprint, fingerprint_version,
              address_snapshot, district_snapshot, ward_snapshot,
              coordinate_source, source_reference, source_recorded_at, source_recorded_by,
              accuracy_level, accuracy_meters, accuracy_method,
              verification_status, verification_method, verified_at, verified_by,
              evidence_reference,
              geographic_validation_status, geographic_validation_note,
              validator_scope_version, validated_at)
            VALUES (?, ?, ?, ?, ?, 4326, ?, 1, ?, ?, ?, ?, ?, UTC_TIMESTAMP(6), ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, UTC_TIMESTAMP(6))
            """,
            id, propertyId, revision, latitude, longitude, fingerprint,
            address, district, ward,
            source.name(), sourceReference, sourceRecordedBy,
            accuracy.name(), accuracyMeters, accuracyMethod,
            verification.name(),
            verificationMethod == null ? null : verificationMethod.name(),
            verifiedAt == null ? null : java.sql.Timestamp.from(verifiedAt),
            verifiedBy, evidenceReference,
            geographicStatus, geographicNote, validatorScopeVersion);
    }

    /**
     * Ghi quyết định xác minh lên đúng revision admin đã kiểm tra, chỉ khi revision đó
     * chưa có quyết định cuối cùng.
     *
     * <p>Ba điều kiện chống race:
     * <ol>
     *   <li>{@code revision = ?} — admin mở revision 1, người đăng sửa tạo revision 2,
     *       câu UPDATE không khớp dòng nào → 409. Không xác minh nhầm bản mới.</li>
     *   <li>{@code superseded_at IS NULL} — revision đúng nhưng đã bị thay thế cũng
     *       không được xác minh.</li>
     *   <li>{@code verification_status IN ('UNVERIFIED','PENDING_REVIEW')} — hai admin
     *       cùng mở revision 3, admin A xác minh VERIFIED, admin B gửi REJECTED dựa
     *       trên trạng thái cũ. Câu UPDATE của B không khớp vì trạng thái đã là
     *       VERIFIED → 409. Quyết định của A không bị ghi đè âm thầm.</li>
     * </ol>
     *
     * <p>Muốn thu hồi một quyết định đã có, phải dùng luồng riêng có audit trail —
     * không ghi đè trực tiếp qua endpoint này.
     *
     * @return số dòng cập nhật; 0 nghĩa là revision đã đổi, đã bị supersede, hoặc đã có
     *         quyết định xác minh
     */
    public int verifyCurrent(String propertyId, int expectedRevision,
                             PropertyCoordinateAudit.Verification status,
                             PropertyCoordinateAudit.VerificationMethod method,
                             Long verifiedBy, String evidenceReference,
                             PropertyCoordinateAudit.Accuracy accuracy, Double accuracyMeters,
                             String accuracyMethod) {
        return jdbc.update("""
            UPDATE property_coordinate_audit
            SET verification_status = ?, verification_method = ?, verified_at = UTC_TIMESTAMP(6),
                verified_by = ?, evidence_reference = ?,
                accuracy_level = ?, accuracy_meters = ?, accuracy_method = ?
            WHERE property_id = ? AND revision = ? AND superseded_at IS NULL
              AND verification_status IN ('UNVERIFIED','PENDING_REVIEW')
            """,
            status.name(), method == null ? null : method.name(), verifiedBy,
            evidenceReference, accuracy.name(), accuracyMeters, accuracyMethod,
            propertyId, expectedRevision);
    }

    /**
     * Cập nhật lại kết quả geographic validation trên bản ghi hiện hành khi
     * {@code validatorScopeVersion} đổi nhưng tọa độ và địa chỉ không đổi.
     *
     * <p>Không tạo revision mới, không đụng tới verification — người dùng không di
     * chuyển điểm, chỉ dữ liệu ranh giới hành chính được cập nhật.
     *
     * @return số dòng cập nhật
     */
    public int refreshValidation(String propertyId, String geographicStatus,
                                 String geographicNote, String validatorScopeVersion) {
        return jdbc.update("""
            UPDATE property_coordinate_audit
            SET geographic_validation_status = ?, geographic_validation_note = ?,
                validator_scope_version = ?, validated_at = UTC_TIMESTAMP(6)
            WHERE property_id = ? AND superseded_at IS NULL
            """,
            geographicStatus, geographicNote, validatorScopeVersion, propertyId);
    }

    /** Phiên bản validator đã dùng cho bản ghi hiện hành. */
    public Optional<String> currentValidatorScope(String propertyId) {
        List<String> rows = jdbc.queryForList("""
            SELECT validator_scope_version FROM property_coordinate_audit
            WHERE property_id = ? AND superseded_at IS NULL
            """, String.class, propertyId);
        return rows.stream().findFirst();
    }

    /** Lịch sử đầy đủ của một tin, mới nhất trước. */
    public List<HistoryRow> history(String propertyId) {
        return jdbc.query("""
            SELECT revision, coordinate_source, accuracy_level, accuracy_meters,
                   verification_status, verification_method, verified_at, verified_by,
                   geographic_validation_status, created_at, superseded_at, superseded_reason
            FROM property_coordinate_audit
            WHERE property_id = ?
            ORDER BY revision DESC
            """,
            (rs, i) -> new HistoryRow(
                rs.getInt("revision"),
                rs.getString("coordinate_source"),
                rs.getString("accuracy_level"),
                rs.getBigDecimal("accuracy_meters") == null ? null
                    : rs.getBigDecimal("accuracy_meters").doubleValue(),
                rs.getString("verification_status"),
                rs.getString("verification_method"),
                rs.getTimestamp("verified_at") == null ? null
                    : rs.getTimestamp("verified_at").toInstant(),
                rs.getObject("verified_by", Long.class),
                rs.getString("geographic_validation_status"),
                rs.getTimestamp("created_at") == null ? null
                    : rs.getTimestamp("created_at").toInstant(),
                rs.getTimestamp("superseded_at") == null ? null
                    : rs.getTimestamp("superseded_at").toInstant(),
                rs.getString("superseded_reason")),
            propertyId);
    }

    public record HistoryRow(int revision, String coordinateSource, String accuracyLevel,
                             Double accuracyMeters, String verificationStatus,
                             String verificationMethod, Instant verifiedAt, Long verifiedBy,
                             String geographicValidationStatus, Instant createdAt,
                             Instant supersededAt, String supersedeReason) {}

    /** Tin đang chờ xác minh — cho admin review. */
    public List<PendingRow> pending(int limit) {
        return pending(limit, null, null);
    }

    /**
     * Hàng đợi xác minh có lọc.
     *
     * @param verificationStatus lọc theo trạng thái xác minh, {@code null} = mọi trạng thái
     * @param query              tìm theo mã tin, tiêu đề hoặc địa chỉ, {@code null} = không lọc
     */
    public List<PendingRow> pending(int limit, String verificationStatus, String query) {
        return pending(limit, verificationStatus, query, 0);
    }

    public List<PendingRow> pending(int limit, String verificationStatus, String query, int offset) {
        StringBuilder sql = new StringBuilder("""
            SELECT a.property_id, p.listing_code, p.title, p.address, p.district, p.ward,
                   a.revision, a.coordinate_source, a.accuracy_level,
                   a.verification_status, a.geographic_validation_status,
                   a.geographic_validation_note, a.created_at
            FROM property_coordinate_audit a
            JOIN properties p ON p.id = a.property_id
            WHERE a.superseded_at IS NULL
              AND p.deleted_at IS NULL
            """);
        List<Object> args = new java.util.ArrayList<>();
        if (verificationStatus != null && !verificationStatus.isBlank()) {
            sql.append(" AND a.verification_status = ?");
            args.add(verificationStatus);
        } else {
            // Mặc định: chỉ tin chưa có quyết định cuối.
            sql.append(" AND a.verification_status IN ('UNVERIFIED','PENDING_REVIEW')");
        }
        if (query != null && !query.isBlank()) {
            sql.append(" AND (p.listing_code LIKE ? OR p.title LIKE ? OR p.address LIKE ?)");
            String like = "%" + query.strip() + "%";
            args.add(like);
            args.add(like);
            args.add(like);
        }
        // id is the V26 primary key. Keep the existing newest-first order while
        // making equal timestamps deterministic across LIMIT/OFFSET pages.
        sql.append(" ORDER BY a.created_at DESC, a.id DESC LIMIT ? OFFSET ?");
        args.add(limit);
        args.add(offset);

        return jdbc.query(sql.toString(),
            (rs, i) -> new PendingRow(
                rs.getString("property_id"), rs.getString("listing_code"),
                rs.getString("title"), rs.getString("address"),
                rs.getString("district"), rs.getString("ward"),
                rs.getInt("revision"), rs.getString("coordinate_source"),
                rs.getString("accuracy_level"), rs.getString("verification_status"),
                rs.getString("geographic_validation_status"),
                rs.getString("geographic_validation_note"),
                rs.getTimestamp("created_at") == null ? null
                    : rs.getTimestamp("created_at").toInstant()),
            args.toArray());
    }

    public long pendingCount(String verificationStatus, String query) {
        StringBuilder sql = new StringBuilder("""
            SELECT COUNT(*)
            FROM property_coordinate_audit a
            JOIN properties p ON p.id = a.property_id
            WHERE a.superseded_at IS NULL AND p.deleted_at IS NULL
            """);
        List<Object> args = new java.util.ArrayList<>();
        if (verificationStatus != null && !verificationStatus.isBlank()) {
            sql.append(" AND a.verification_status = ?");
            args.add(verificationStatus);
        } else {
            sql.append(" AND a.verification_status IN ('UNVERIFIED','PENDING_REVIEW')");
        }
        if (query != null && !query.isBlank()) {
            sql.append(" AND (p.listing_code LIKE ? OR p.title LIKE ? OR p.address LIKE ?)");
            String like = "%" + query.strip() + "%";
            args.add(like);
            args.add(like);
            args.add(like);
        }
        Long count = jdbc.queryForObject(sql.toString(), Long.class, args.toArray());
        return count == null ? 0 : count;
    }

    /**
     * Thống kê hàng đợi — đếm trên toàn bộ bảng, không suy từ trang đã phân trang.
     *
     * <p>Chỉ tính audit hiện hành của tin chưa xoá.
     */
    public Stats stats() {
        return jdbc.queryForObject("""
            SELECT
              COUNT(*) AS total,
              SUM(a.verification_status = 'UNVERIFIED') AS unverified,
              SUM(a.verification_status = 'PENDING_REVIEW') AS pending_review,
              SUM(a.verification_status = 'VERIFIED') AS verified,
              SUM(a.verification_status = 'REJECTED') AS rejected,
              SUM(a.verification_status = 'STALE') AS stale,
              SUM(a.geographic_validation_status = 'INVALID_DISTRICT_MISMATCH') AS district_mismatch
            FROM property_coordinate_audit a
            JOIN properties p ON p.id = a.property_id
            WHERE a.superseded_at IS NULL AND p.deleted_at IS NULL
            """,
            (rs, i) -> new Stats(
                rs.getLong("total"), rs.getLong("unverified"),
                rs.getLong("pending_review"), rs.getLong("verified"),
                rs.getLong("rejected"), rs.getLong("stale"),
                rs.getLong("district_mismatch")));
    }

    public record Stats(long total, long unverified, long pendingReview, long verified,
                        long rejected, long stale, long districtMismatch) {}

    /**
     * Chi tiết một tin cho admin review — gồm tọa độ, địa chỉ và toàn bộ metadata.
     *
     * <p>Chỉ admin gọi được (kiểm tra ở controller). Không dùng cho public response.
     */
    public Optional<ReviewDetail> reviewDetail(String propertyId) {
        List<ReviewDetail> rows = jdbc.query("""
            SELECT a.property_id, p.listing_code, p.title, p.address, p.city,
                   p.district, p.ward, p.status,
                   ST_Latitude(p.location) AS latitude, ST_Longitude(p.location) AS longitude,
                   a.revision, a.coordinate_source, a.source_reference,
                   a.source_recorded_at, a.source_recorded_by,
                   a.accuracy_level, a.accuracy_meters, a.accuracy_method,
                   a.verification_status, a.verification_method, a.verified_at, a.verified_by,
                   a.evidence_reference,
                   a.geographic_validation_status, a.geographic_validation_note,
                   a.validator_scope_version, a.validated_at, a.created_at
            FROM property_coordinate_audit a
            JOIN properties p ON p.id = a.property_id
            WHERE a.property_id = ? AND a.superseded_at IS NULL
            """,
            (rs, i) -> {
                String coordinateSource = rs.getString("coordinate_source");
                String accuracyLevel = rs.getString("accuracy_level");
                Double accuracyMeters = rs.getBigDecimal("accuracy_meters") == null ? null
                    : rs.getBigDecimal("accuracy_meters").doubleValue();
                String verificationStatus = rs.getString("verification_status");
                String verificationMethod = rs.getString("verification_method");
                Instant verifiedAt = rs.getTimestamp("verified_at") == null ? null
                    : rs.getTimestamp("verified_at").toInstant();
                String geographicStatus = rs.getString("geographic_validation_status");
                String geographicNote = rs.getString("geographic_validation_note");
                int revision = rs.getInt("revision");
                Instant createdAt = rs.getTimestamp("created_at") == null ? null
                    : rs.getTimestamp("created_at").toInstant();
                boolean parcelEligible = PropertyCoordinateAudit.derive(
                    coordinateSource, accuracyLevel, accuracyMeters, verificationStatus,
                    verificationMethod, verifiedAt, geographicStatus, geographicNote,
                    revision, createdAt).parcelAnalysisEligible();

                return new ReviewDetail(
                    rs.getString("property_id"), rs.getString("listing_code"),
                    rs.getString("title"), rs.getString("address"), rs.getString("city"),
                    rs.getString("district"), rs.getString("ward"), rs.getString("status"),
                    rs.getDouble("latitude"), rs.getDouble("longitude"),
                    revision, coordinateSource, rs.getString("source_reference"),
                    rs.getTimestamp("source_recorded_at") == null ? null
                        : rs.getTimestamp("source_recorded_at").toInstant(),
                    rs.getObject("source_recorded_by", Long.class),
                    accuracyLevel, accuracyMeters, rs.getString("accuracy_method"),
                    verificationStatus, verificationMethod, verifiedAt,
                    rs.getObject("verified_by", Long.class), rs.getString("evidence_reference"),
                    geographicStatus, geographicNote, rs.getString("validator_scope_version"),
                    rs.getTimestamp("validated_at") == null ? null
                        : rs.getTimestamp("validated_at").toInstant(),
                    createdAt, parcelEligible);
            },
            propertyId);
        return rows.stream().findFirst();
    }

    public record ReviewDetail(String propertyId, String listingCode, String title,
                               String address, String city, String district, String ward,
                               String propertyStatus, double latitude, double longitude,
                               int revision, String coordinateSource, String sourceReference,
                               Instant sourceRecordedAt, Long sourceRecordedBy,
                               String accuracyLevel, Double accuracyMeters, String accuracyMethod,
                               String verificationStatus, String verificationMethod,
                               Instant verifiedAt, Long verifiedBy, String evidenceReference,
                               String geographicValidationStatus, String geographicValidationNote,
                               String validatorScopeVersion, Instant validatedAt,
                               Instant createdAt, boolean parcelAnalysisEligible) {}

    public record PendingRow(String propertyId, String listingCode, String title,
                             String address, String district, String ward, int revision,
                             String coordinateSource, String accuracyLevel,
                             String verificationStatus, String geographicValidationStatus,
                             String geographicValidationNote, Instant createdAt) {}
}
