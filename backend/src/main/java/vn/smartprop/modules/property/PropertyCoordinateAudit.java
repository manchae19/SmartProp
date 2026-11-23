package vn.smartprop.modules.property;

import java.time.Instant;

/**
 * Coordinate Provenance V1 — lịch sử nguồn gốc, độ chính xác và xác minh tọa độ.
 *
 * <p>Tách ba khái niệm độc lập (xem docs/SMARTPROP_COORDINATE_PROVENANCE_AUDIT.md):
 * <ul>
 *   <li>{@code geographicValidationStatus} — điểm có hợp lệ và đúng địa bàn không
 *       (kết quả {@code DanangSpatialValidator}). Chỉ cấp quận, KHÔNG phải cấp thửa.</li>
 *   <li>{@code coordinateSource} — tọa độ đến từ đâu.</li>
 *   <li>{@code accuracyLevel} + {@code verificationStatus} — có đúng thửa đất không.</li>
 * </ul>
 *
 * <p>Mỗi bản ghi gắn với MỘT phiên bản tọa độ qua {@code coordinateFingerprint}.
 * Khi tọa độ hoặc địa chỉ đổi, bản ghi cũ bị superseded và bản mới được tạo —
 * không kế thừa trạng thái xác minh của tọa độ cũ.
 */
public final class PropertyCoordinateAudit {
    private PropertyCoordinateAudit() {}

    /** Tọa độ đến từ đâu. Chỉ ghi giá trị có bằng chứng thực tế. */
    public enum Source {
        /** Người dùng tự chọn điểm trên bản đồ trong form đăng tin. */
        USER_PINNED,
        /** Hệ thống tạo từ geocoding địa chỉ. */
        GEOCODED,
        /** Đi qua luồng import đã xác nhận. */
        IMPORTED,
        /** Vị trí mặc định do quản trị đặt. */
        ADMIN_DEFAULT,
        /** Không đủ bằng chứng — mặc định cho dữ liệu cũ. */
        UNKNOWN
    }

    /**
     * Độ chính xác được CHỨNG MINH, không suy từ số chữ số thập phân.
     *
     * <p>{@code PARCEL} chỉ hợp lệ khi {@code verificationStatus = VERIFIED} —
     * ràng buộc {@code ck_coord_audit_parcel_requires_verification} trong DB.
     */
    public enum Accuracy { UNKNOWN, CITY, DISTRICT, WARD, STREET, BUILDING, PARCEL }

    /** Trạng thái xác minh độc lập. Không tự nâng khi publish. */
    public enum Verification { UNVERIFIED, PENDING_REVIEW, VERIFIED, REJECTED, STALE }

    /** Phương pháp xác minh. Bắt buộc khi {@code VERIFIED}. */
    public enum VerificationMethod {
        FIELD_SURVEY,
        CADASTRAL_RECORD,
        AERIAL_IMAGERY,
        ADMIN_REVIEW
    }

    /** Lý do bản ghi audit hết hiệu lực. */
    public enum SupersedeReason {
        COORDINATE_CHANGED,
        ADDRESS_CHANGED,
        ADMINISTRATIVE_CHANGED,
        MANUAL_REVOKE
    }

    /**
     * Kết quả đọc trạng thái tọa độ cho API và GIS.
     *
     * <p>Ba cờ eligibility được suy từ metadata có bằng chứng, KHÔNG từ một enum đơn lẻ.
     * Mặc định an toàn: thiếu provenance hoặc accuracy thì cờ tương ứng là false.
     */
    public record Status(
        String coordinateSource,
        String accuracyLevel,
        Double accuracyMeters,
        String verificationStatus,
        String verificationMethod,
        Instant verifiedAt,
        String geographicValidationStatus,
        String geographicValidationNote,
        boolean referenceMapEligible,
        boolean distanceAnalysisEligible,
        boolean parcelAnalysisEligible,
        int revision,
        Instant auditedAt
    ) {
        /** Không có audit — dữ liệu cũ chưa từng được ghi nhận nguồn gốc. */
        public static Status absent() {
            return new Status("UNKNOWN", "UNKNOWN", null, "UNVERIFIED", null, null,
                null, null, false, false, false, 0, null);
        }
    }

    /**
     * Suy ba cờ eligibility từ metadata. Đây là nguồn duy nhất của logic này —
     * GIS và API đều dùng chung.
     *
     * <p>Quy tắc:
     * <ul>
     *   <li>{@code referenceMapEligible} — geometry hợp lệ và điểm phù hợp địa bàn
     *       (validator trả {@code VERIFIED_EXACT} hoặc {@code VERIFIED_BOUNDARY_BUFFER}).</li>
     *   <li>{@code distanceAnalysisEligible} — cần provenance xác định VÀ accuracy
     *       được chứng minh. Không đủ nếu chỉ có {@code VERIFIED_EXACT}.</li>
     *   <li>{@code parcelAnalysisEligible} — cần ĐỒNG THỜI: geographic validity,
     *       provenance xác định, {@code accuracyLevel = PARCEL}, và
     *       {@code verificationStatus = VERIFIED}.</li>
     * </ul>
     *
     * <p>Ràng buộc DB ({@code ck_coord_audit_parcel_requires_verification}) chỉ chặn
     * cặp PARCEL+chưa-VERIFIED. Nó KHÔNG kiểm tra geographic validity hay provenance —
     * đó là việc của hàm này. DB CHECK không thay thế kiểm tra nghiệp vụ.
     */
    public static Status derive(String coordinateSource, String accuracyLevel,
                                Double accuracyMeters, String verificationStatus,
                                String verificationMethod, Instant verifiedAt,
                                String geographicStatus, String geographicNote,
                                int revision, Instant auditedAt) {
        boolean geoOk = "VERIFIED_EXACT".equals(geographicStatus)
            || "VERIFIED_BOUNDARY_BUFFER".equals(geographicStatus);
        boolean hasProvenance = coordinateSource != null
            && !"UNKNOWN".equals(coordinateSource);
        boolean hasAccuracy = accuracyLevel != null && !"UNKNOWN".equals(accuracyLevel);
        boolean verified = "VERIFIED".equals(verificationStatus);
        boolean hasEvidence = verificationMethod != null && verifiedAt != null;

        boolean referenceMap = geoOk;
        boolean distance = geoOk && hasProvenance && hasAccuracy;
        // Cấp thửa cần đủ bốn điều kiện — không chỉ PARCEL + VERIFIED.
        boolean parcel = geoOk && hasProvenance && hasAccuracy && verified && hasEvidence
            && "PARCEL".equals(accuracyLevel);

        return new Status(coordinateSource, accuracyLevel, accuracyMeters,
            verificationStatus, verificationMethod, verifiedAt,
            geographicStatus, geographicNote,
            referenceMap, distance, parcel, revision, auditedAt);
    }
}
