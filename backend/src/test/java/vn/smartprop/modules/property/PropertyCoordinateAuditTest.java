package vn.smartprop.modules.property;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Coordinate Provenance V1 — quy tắc suy ba cờ eligibility.
 *
 * <p>Điểm quan trọng: {@code VERIFIED_EXACT} chỉ là hợp lệ cấp quận. Nó KHÔNG đủ để
 * bật {@code distanceAnalysisEligible} hay {@code parcelAnalysisEligible}.
 */
class PropertyCoordinateAuditTest {

    @Test
    void verifiedExactAloneDoesNotEnableDistanceAnalysis() {
        // Có geographic validity nhưng không có provenance và accuracy.
        var status = PropertyCoordinateAudit.derive(
            "UNKNOWN", "UNKNOWN", null, "UNVERIFIED", null, null,
            "VERIFIED_EXACT", "Tọa độ nằm trong ranh giới quận", 1, null);

        assertTrue(status.referenceMapEligible(), "marker tham khảo được phép");
        assertFalse(status.distanceAnalysisEligible(),
            "VERIFIED_EXACT một mình không đủ để đo khoảng cách");
        assertFalse(status.parcelAnalysisEligible());
    }

    @Test
    void distanceAnalysisNeedsProvenanceAndAccuracy() {
        var withBoth = PropertyCoordinateAudit.derive(
            "USER_PINNED", "STREET", 15.0, "UNVERIFIED", null, null,
            "VERIFIED_EXACT", null, 1, null);
        assertTrue(withBoth.distanceAnalysisEligible());

        var noAccuracy = PropertyCoordinateAudit.derive(
            "USER_PINNED", "UNKNOWN", null, "UNVERIFIED", null, null,
            "VERIFIED_EXACT", null, 1, null);
        assertFalse(noAccuracy.distanceAnalysisEligible(),
            "thiếu accuracy thì không đo khoảng cách");

        var noProvenance = PropertyCoordinateAudit.derive(
            "UNKNOWN", "STREET", 15.0, "UNVERIFIED", null, null,
            "VERIFIED_EXACT", null, 1, null);
        assertFalse(noProvenance.distanceAnalysisEligible(),
            "thiếu provenance thì không đo khoảng cách");
    }

    @Test
    void accuracyMetersPolicyRequiresUnknownNullAndKnownPositiveFinite() {
        for (Double invalid : new Double[] { null, 0.0, -1.0, Double.NaN, Double.POSITIVE_INFINITY }) {
            var status = PropertyCoordinateAudit.derive(
                "USER_PINNED", "STREET", invalid, "UNVERIFIED", null, null,
                "VERIFIED_EXACT", null, 1, null);
            assertFalse(status.distanceAnalysisEligible(), "invalid meters=" + invalid);
        }
        var unknownWithMeters = PropertyCoordinateAudit.derive(
            "USER_PINNED", "UNKNOWN", 1.0, "UNVERIFIED", null, null,
            "VERIFIED_EXACT", null, 1, null);
        assertFalse(unknownWithMeters.distanceAnalysisEligible());
    }

    @Test
    void streetNullIsAcceptedAsMetadataButNeverEnablesDistance() {
        var status = PropertyCoordinateAudit.derive(
            "USER_PINNED", "STREET", null, "UNVERIFIED", null, null,
            "VERIFIED_EXACT", null, 1, null);
        assertTrue(status.referenceMapEligible());
        assertFalse(status.distanceAnalysisEligible());
        assertFalse(status.parcelAnalysisEligible());
    }

    @Test
    void unknownNullAndStreetPositiveFiniteFollowAccuracyEligibilityPolicy() {
        var unknown = PropertyCoordinateAudit.derive(
            "USER_PINNED", "UNKNOWN", null, "UNVERIFIED", null, null,
            "VERIFIED_EXACT", null, 1, null);
        assertFalse(unknown.distanceAnalysisEligible());

        var street = PropertyCoordinateAudit.derive(
            "USER_PINNED", "STREET", 0.01, "PENDING_REVIEW", null, null,
            "VERIFIED_EXACT", null, 1, null);
        assertTrue(street.referenceMapEligible());
        assertTrue(street.distanceAnalysisEligible());
    }

    @Test
    void unverifiedAndPendingCanMapButRequireKnownPositiveAccuracyForDistance() {
        for (String verification : java.util.List.of("UNVERIFIED", "PENDING_REVIEW")) {
            var status = PropertyCoordinateAudit.derive(
                "USER_PINNED", "STREET", 0.5, verification, null, null,
                "VERIFIED_EXACT", null, 1, null);
            assertTrue(status.referenceMapEligible(), verification);
            assertTrue(status.distanceAnalysisEligible(), verification);
        }
    }

    @Test
    void parcelAnalysisNeedsParcelAccuracyAndVerification() {
        var verified = PropertyCoordinateAudit.derive(
            "USER_PINNED", "PARCEL", 3.0, "VERIFIED",
            "FIELD_SURVEY", java.time.Instant.now(), "VERIFIED_EXACT", null, 1, null);
        assertTrue(verified.parcelAnalysisEligible());

        var parcelUnverified = PropertyCoordinateAudit.derive(
            "USER_PINNED", "PARCEL", 3.0, "UNVERIFIED", null, null,
            "VERIFIED_EXACT", null, 1, null);
        assertFalse(parcelUnverified.parcelAnalysisEligible(),
            "PARCEL chưa xác minh không đủ điều kiện phân tích cấp thửa");

        var verifiedStreet = PropertyCoordinateAudit.derive(
            "USER_PINNED", "STREET", 15.0, "VERIFIED",
            "ADMIN_REVIEW", java.time.Instant.now(), "VERIFIED_EXACT", null, 1, null);
        assertFalse(verifiedStreet.parcelAnalysisEligible(),
            "xác minh cấp đường không phải cấp thửa");
    }

    @Test
    void parcelRequiresPositiveFiniteMetersAndVerificationEvidenceFields() {
        for (Double invalid : new Double[] {null, 0.0, -1.0, Double.NaN, Double.POSITIVE_INFINITY}) {
            var status = PropertyCoordinateAudit.derive(
                "USER_PINNED", "PARCEL", invalid, "VERIFIED",
                "FIELD_SURVEY", java.time.Instant.now(), "VERIFIED_EXACT", null, 1, null);
            assertFalse(status.parcelAnalysisEligible(), "meters=" + invalid);
        }
        var missingMethod = PropertyCoordinateAudit.derive(
            "USER_PINNED", "PARCEL", 1.0, "VERIFIED", null,
            java.time.Instant.now(), "VERIFIED_EXACT", null, 1, null);
        assertFalse(missingMethod.parcelAnalysisEligible());
        var valid = PropertyCoordinateAudit.derive(
            "USER_PINNED", "PARCEL", 1.0, "VERIFIED", "FIELD_SURVEY",
            java.time.Instant.now(), "VERIFIED_EXACT", null, 1, null);
        assertTrue(valid.parcelAnalysisEligible());
    }

    @Test
    void boundaryBufferStillAllowsReferenceMap() {
        var status = PropertyCoordinateAudit.derive(
            "UNKNOWN", "UNKNOWN", null, "UNVERIFIED", null, null,
            "VERIFIED_BOUNDARY_BUFFER", "cách biên 20 m", 1, null);
        assertTrue(status.referenceMapEligible());
        assertFalse(status.distanceAnalysisEligible());
    }

    @Test
    void invalidDistrictMismatchDisablesEverything() {
        var status = PropertyCoordinateAudit.derive(
            "USER_PINNED", "STREET", 15.0, "UNVERIFIED", null, null,
            "INVALID_DISTRICT_MISMATCH", "lệch 2734 m", 1, null);
        assertFalse(status.referenceMapEligible(),
            "tọa độ lệch địa bàn không được hiển thị marker");
        assertFalse(status.distanceAnalysisEligible());
        assertFalse(status.parcelAnalysisEligible());
    }

    @Test
    void rejectedOrStaleCoordinatesAreNotEligibleForSpatialUse() {
        for (String verification : java.util.List.of("REJECTED", "STALE")) {
            var status = PropertyCoordinateAudit.derive(
                "USER_PINNED", "STREET", 15.0, verification, null, null,
                "VERIFIED_EXACT", null, 1, null);
            assertFalse(status.referenceMapEligible(), verification);
            assertFalse(status.distanceAnalysisEligible(), verification);
            assertFalse(status.parcelAnalysisEligible(), verification);
        }
    }

    @Test
    void absentStatusIsSafeDefault() {
        var status = PropertyCoordinateAudit.Status.absent();
        assertEquals("UNKNOWN", status.coordinateSource());
        assertEquals("UNKNOWN", status.accuracyLevel());
        assertEquals("UNVERIFIED", status.verificationStatus());
        assertFalse(status.referenceMapEligible());
        assertFalse(status.distanceAnalysisEligible());
        assertFalse(status.parcelAnalysisEligible());
        assertEquals(0, status.revision());
    }

    @Test
    void fingerprintChangesWhenAddressChanges() {
        String base = PropertyCoordinateAuditRepository.fingerprint(
            16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");
        String samePoint = PropertyCoordinateAuditRepository.fingerprint(
            16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");
        String newAddress = PropertyCoordinateAuditRepository.fingerprint(
            16.0430, 108.1840, "Đường Tôn Đản, Hòa Phát", "Cẩm Lệ", "Hòa Phát");
        String newPoint = PropertyCoordinateAuditRepository.fingerprint(
            16.0500, 108.1900, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");

        assertEquals(base, samePoint, "cùng đầu vào phải cùng fingerprint");
        assertNotEquals(base, newAddress,
            "đổi địa chỉ phải đổi fingerprint — nếu không, xác minh cũ bị dùng lại sai");
        assertNotEquals(base, newPoint, "đổi tọa độ phải đổi fingerprint");
    }

    @Test
    void fingerprintDoesNotDependOnValidatorScope() {
        // Phiên bản dữ liệu địa giới KHÔNG được nằm trong fingerprint: cập nhật ranh
        // giới hành chính không phải là người dùng di chuyển điểm. Nếu gộp vào, mỗi lần
        // cập nhật địa giới sẽ tạo revision giả và làm mất xác minh không cần thiết.
        String a = PropertyCoordinateAuditRepository.fingerprint(
            16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");
        String b = PropertyCoordinateAuditRepository.fingerprint(
            16.0430, 108.1840, "Đường Tôn Đản, Hòa An", "Cẩm Lệ", "Hòa An");
        assertEquals(a, b, "cùng vị trí và địa chỉ phải cùng fingerprint bất kể scope");
    }
    @Test
    void fingerprintIgnoresFloatingPointNoise() {
        // 16.043000000000001 là artifact IEEE-754 của 16.043.
        String clean = PropertyCoordinateAuditRepository.fingerprint(
            16.043, 108.184, "A", "B", "C");
        String noisy = PropertyCoordinateAuditRepository.fingerprint(
            16.043000000000001, 108.18400000000001, "A", "B", "C");
        assertEquals(clean, noisy,
            "nhiễu biểu diễn DOUBLE không được làm đổi fingerprint");
    }
}
