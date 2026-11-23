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

    public PropertyCoordinateAuditRepository(JdbcTemplate jdbc) { this.jdbc = jdbc; }

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
        return jdbc.query("""
            SELECT a.property_id, p.listing_code, p.address, p.district, p.ward,
                   a.revision, a.coordinate_source, a.geographic_validation_status,
                   a.geographic_validation_note, a.created_at
            FROM property_coordinate_audit a
            JOIN properties p ON p.id = a.property_id
            WHERE a.superseded_at IS NULL
              AND a.verification_status IN ('UNVERIFIED','PENDING_REVIEW')
              AND p.deleted_at IS NULL
            ORDER BY a.created_at DESC
            LIMIT ?
            """,
            (rs, i) -> new PendingRow(
                rs.getString("property_id"), rs.getString("listing_code"),
                rs.getString("address"), rs.getString("district"), rs.getString("ward"),
                rs.getInt("revision"), rs.getString("coordinate_source"),
                rs.getString("geographic_validation_status"),
                rs.getString("geographic_validation_note"),
                rs.getTimestamp("created_at") == null ? null
                    : rs.getTimestamp("created_at").toInstant()),
            limit);
    }

    public record PendingRow(String propertyId, String listingCode, String address,
                             String district, String ward, int revision,
                             String coordinateSource, String geographicValidationStatus,
                             String geographicValidationNote, Instant createdAt) {}
}
