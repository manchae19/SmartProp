package vn.smartprop.modules.property;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import vn.smartprop.gis.DanangAdminNormalizer;
import vn.smartprop.gis.DanangSpatialValidator;
import vn.smartprop.gis.GisDtos;

/**
 * Coordinate Provenance V1 — điều phối ghi nhận nguồn gốc tọa độ.
 *
 * <p>Chạy trong transaction của caller ({@code MANDATORY}) để property và audit luôn
 * nhất quán: nếu audit lỗi, property rollback theo.
 *
 * <p>Nguyên tắc:
 * <ul>
 *   <li>Không suy {@code accuracy} từ {@code VERIFIED_EXACT} hay số chữ số thập phân.</li>
 *   <li>Không cho client tự khai {@code coordinateSource} đã xác minh — nguồn do
 *       backend xác định theo ngữ cảnh luồng gọi.</li>
 *   <li>Đổi tọa độ hoặc địa chỉ đều làm fingerprint đổi → audit cũ bị supersede.</li>
 * </ul>
 */
@Service
public class PropertyCoordinateAuditService {
    private final PropertyCoordinateAuditRepository repository;
    private final DanangSpatialValidator validator;
    private final DanangAdminNormalizer normalizer;

    public PropertyCoordinateAuditService(PropertyCoordinateAuditRepository repository,
                                          DanangSpatialValidator validator,
                                          DanangAdminNormalizer normalizer) {
        this.repository = repository;
        this.validator = validator;
        this.normalizer = normalizer;
    }

    /** Read-only compatibility for existing pins without an audit. Never grants precision. */
    public PropertyCoordinateAudit.Status legacyReference(Property property) {
        if (property.location == null) return PropertyCoordinateAudit.Status.absent();
        var v = validate(property);
        return PropertyCoordinateAudit.derive("UNKNOWN", "UNKNOWN", null, "UNVERIFIED",
            null, null, v.status().name(), "Existing listing pin; provenance and precision unverified", 0, null);
    }

    /** Standard V1..V23 lineage has no V26 audit table; dependent features fail closed. */
    public boolean available() { return repository.schemaAvailable(); }

    /** Trạng thái tọa độ hiện hành, hoặc {@code absent()} nếu tin chưa có audit. */
    @Transactional(readOnly = true)
    public PropertyCoordinateAudit.Status status(String propertyId) {
        requireAvailable();
        return repository.current(propertyId).orElseGet(PropertyCoordinateAudit.Status::absent);
    }

    @Transactional(readOnly = true)
    public java.util.Map<String, PropertyCoordinateAudit.Status> statuses(List<String> propertyIds) {
        if (!available()) {
            var absent = new java.util.LinkedHashMap<String, PropertyCoordinateAudit.Status>();
            for (String id : propertyIds) absent.put(id, PropertyCoordinateAudit.Status.absent());
            return java.util.Map.copyOf(absent);
        }
        var found = repository.currentForProperties(propertyIds);
        var result = new java.util.LinkedHashMap<String, PropertyCoordinateAudit.Status>();
        for (String id : propertyIds) result.put(id, found.getOrDefault(id, PropertyCoordinateAudit.Status.absent()));
        return java.util.Map.copyOf(result);
    }

    @Transactional(readOnly = true)
    public List<PropertyCoordinateAuditRepository.HistoryRow> history(String propertyId) {
        requireAvailable();
        return repository.history(propertyId);
    }

    @Transactional(readOnly = true)
    public List<PropertyCoordinateAuditRepository.PendingRow> pending(int limit) {
        requireAvailable();
        return pending(limit, null, null);
    }

    /** Hàng đợi xác minh có lọc theo trạng thái và từ khoá. */
    @Transactional(readOnly = true)
    public List<PropertyCoordinateAuditRepository.PendingRow> pending(int limit,
                                                                     String verificationStatus,
                                                                     String query) {
        requireAvailable();
        return repository.pending(Math.min(Math.max(limit, 1), 200),
            verificationStatus, query);
    }

    @Transactional(readOnly = true)
    public PendingPage pendingPage(int limit, int offset, String verificationStatus, String query) {
        requireAvailable();
        int safeLimit = Math.min(Math.max(limit, 1), 200);
        int safeOffset = Math.max(offset, 0);
        return new PendingPage(repository.pending(safeLimit, verificationStatus, query, safeOffset),
            repository.pendingCount(verificationStatus, query), safeOffset, safeLimit);
    }

    public record PendingPage(List<PropertyCoordinateAuditRepository.PendingRow> items,
                              long total, int offset, int limit) {}

    /** Thống kê hàng đợi — đếm toàn bộ, không suy từ trang đã phân trang. */
    @Transactional(readOnly = true)
    public PropertyCoordinateAuditRepository.Stats stats() {
        requireAvailable();
        return repository.stats();
    }

    /** Chi tiết một tin cho admin review. */
    @Transactional(readOnly = true)
    public PropertyCoordinateAuditRepository.ReviewDetail reviewDetail(String propertyId) {
        requireAvailable();
        return repository.reviewDetail(propertyId).orElseThrow(
            () -> vn.smartprop.common.ApiInputs.missing());
    }

    private void requireAvailable() {
        if (!available()) throw new vn.smartprop.common.ApiException(503,
            "COORDINATE_AUDIT_UNAVAILABLE", "Coordinate audit is unavailable for this database lineage.");
    }

    /**
     * Ghi nhận tọa độ sau khi property đã được lưu.
     *
     * <p>Ba nhánh, theo thứ tự:
     * <ol>
     *   <li><b>Không đổi gì</b> — fingerprint khớp và validator scope khớp → không làm
     *       gì. Sửa tiêu đề, giá, mô tả không tạo revision, không mất xác minh.</li>
     *   <li><b>Chỉ validator scope đổi</b> — fingerprint khớp nhưng scope khác → cập
     *       nhật lại geographic validation trên bản ghi hiện hành. Không tạo revision,
     *       không đụng verification: người dùng không di chuyển điểm.</li>
     *   <li><b>Tọa độ hoặc địa chỉ đổi</b> — fingerprint khác → supersede bản cũ, tạo
     *       revision mới với {@code UNVERIFIED}. Không kế thừa xác minh của vị trí cũ.</li>
     * </ol>
     *
     * @param source nguồn tọa độ do backend xác định, không lấy từ request
     */
    @Transactional(propagation = Propagation.MANDATORY)
    public void record(Property property, PropertyCoordinateAudit.Source source,
                       String sourceReference, Long actor) {
        if (!available()) return;
        if (property.location == null) return;

        double latitude = property.location.getY();
        double longitude = property.location.getX();
        String scopeVersion = validator.scopeVersion();
        String fingerprint = PropertyCoordinateAuditRepository.fingerprint(
            latitude, longitude, property.address, property.district, property.ward);

        Optional<String> current = repository.currentFingerprint(property.id);
        if (current.isPresent() && current.get().equals(fingerprint)) {
            // Vị trí không đổi. Kiểm tra riêng phiên bản validator: nếu dữ liệu địa giới
            // đã cập nhật thì đánh giá lại geographic validity, nhưng KHÔNG tạo revision
            // và KHÔNG đụng verification — người dùng không di chuyển điểm.
            Optional<String> currentScope = repository.currentValidatorScope(property.id);
            if (currentScope.isPresent() && !currentScope.get().equals(scopeVersion)) {
                GisDtos.CoordinateValidationResult refreshed = validate(property);
                repository.refreshValidation(property.id, refreshed.status().name(),
                    refreshed.validationNote(), scopeVersion);
            }
            return;
        }

        // Tọa độ hoặc địa chỉ đã đổi — kết thúc hiệu lực bản cũ trước.
        repository.supersedeCurrent(property.id,
            PropertyCoordinateAudit.SupersedeReason.COORDINATE_CHANGED);

        GisDtos.CoordinateValidationResult validation = validate(property);

        repository.insert(
            UUID.randomUUID().toString(), property.id,
            repository.maxRevision(property.id) + 1,
            latitude, longitude, fingerprint,
            property.address, property.district, property.ward,
            source, sourceReference, actor,
            // Accuracy mặc định UNKNOWN: chưa có bằng chứng độ chính xác.
            PropertyCoordinateAudit.Accuracy.UNKNOWN, null, null,
            // Verification mặc định UNVERIFIED: publish không nâng mức xác minh.
            PropertyCoordinateAudit.Verification.UNVERIFIED, null, null, null, null,
            validation.status().name(), validation.validationNote(), scopeVersion);
    }

    /**
     * Chạy validator với district đã chuẩn hoá như production.
     *
     * <p>Kết quả chỉ phản ánh {@code geographic_validity} — KHÔNG phải độ chính xác
     * cấp thửa.
     */
    private GisDtos.CoordinateValidationResult validate(Property property) {
        GisDtos.AdminNormalizationResult normalized =
            normalizer.normalize(property.district, property.ward, property.city);
        return validator.validate(property.location.getY(), property.location.getX(),
            normalized.canonicalDistrict(), true);
    }

    /**
     * Ghi quyết định xác minh. Đây là transaction boundary của luồng verify —
     * controller không mở transaction, service tự mở.
     *
     * <p>Kiểm tra {@code expectedRevision} để không xác minh nhầm bản mới: admin mở
     * revision 1, người đăng sửa tạo revision 2, admin bấm xác minh → UPDATE không
     * khớp dòng nào → trả false → controller trả 409.
     *
     * @return false nếu revision đã đổi hoặc đã bị supersede
     */
    @Transactional
    public boolean verify(String propertyId, int expectedRevision,
                          PropertyCoordinateAudit.Verification status,
                          PropertyCoordinateAudit.VerificationMethod method,
                          Long verifiedBy, String evidenceReference,
                          PropertyCoordinateAudit.Accuracy accuracy, Double accuracyMeters,
                          String accuracyMethod) {
        requireAvailable();
        if (status == PropertyCoordinateAudit.Verification.VERIFIED
                && (method == null || evidenceReference == null || evidenceReference.isBlank())) {
            throw vn.smartprop.common.ApiInputs.bad(
                "Xác minh cần verificationMethod và evidenceReference");
        }
        if (accuracy == PropertyCoordinateAudit.Accuracy.PARCEL
                && status != PropertyCoordinateAudit.Verification.VERIFIED) {
            throw vn.smartprop.common.ApiInputs.bad(
                "accuracyLevel PARCEL chỉ hợp lệ khi verificationStatus VERIFIED");
        }
        if (accuracy == PropertyCoordinateAudit.Accuracy.UNKNOWN && accuracyMeters != null) {
            throw vn.smartprop.common.ApiInputs.bad(
                "accuracyLevel UNKNOWN phải có accuracyMeters NULL");
        }
        if (accuracy == PropertyCoordinateAudit.Accuracy.STREET && accuracyMeters != null
                && (!Double.isFinite(accuracyMeters) || accuracyMeters <= 0)) {
            throw vn.smartprop.common.ApiInputs.bad(
                "accuracyMeters của STREET phải hữu hạn và dương khi được cung cấp");
        }
        if (accuracy == PropertyCoordinateAudit.Accuracy.PARCEL
                && (accuracyMeters == null || !Double.isFinite(accuracyMeters) || accuracyMeters <= 0)) {
            throw vn.smartprop.common.ApiInputs.bad(
                "accuracyLevel PARCEL cần accuracyMeters hữu hạn và dương");
        }
        if (accuracy != PropertyCoordinateAudit.Accuracy.UNKNOWN
                && accuracy != PropertyCoordinateAudit.Accuracy.STREET
                && accuracy != PropertyCoordinateAudit.Accuracy.PARCEL
                && (accuracyMeters == null || !Double.isFinite(accuracyMeters) || accuracyMeters <= 0)) {
            throw vn.smartprop.common.ApiInputs.bad(
                "accuracyLevel đã biết cần accuracyMeters hữu hạn và dương");
        }
        if (accuracy == PropertyCoordinateAudit.Accuracy.PARCEL
                && (method == null || evidenceReference == null || evidenceReference.isBlank())) {
            throw vn.smartprop.common.ApiInputs.bad(
                "accuracyLevel PARCEL cần phương pháp xác minh và bằng chứng");
        }
        int updated = repository.verifyCurrent(propertyId, expectedRevision, status, method,
            verifiedBy, evidenceReference, accuracy, accuracyMeters, accuracyMethod);
        return updated == 1;
    }

    /**
     * Đánh dấu audit hiện hành là STALE khi địa chỉ đổi nhưng tọa độ giữ nguyên.
     *
     * <p>Fingerprint đã bao gồm địa chỉ nên {@link #record} sẽ tự supersede. Hàm này
     * dùng khi cần đánh dấu rõ lý do mà không tạo revision mới.
     */
    @Transactional(propagation = Propagation.MANDATORY)
    public void markStale(String propertyId) {
        repository.supersedeCurrent(propertyId,
            PropertyCoordinateAudit.SupersedeReason.ADDRESS_CHANGED);
    }
}
