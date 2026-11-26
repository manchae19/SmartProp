package vn.smartprop.modules.property;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import vn.smartprop.common.ApiException;

class PropertyCoordinateAuditServiceTest {
    private PropertyCoordinateAuditRepository repository;
    private PropertyCoordinateAuditService service;

    @BeforeEach
    void setUp() {
        repository = mock(PropertyCoordinateAuditRepository.class);
        when(repository.schemaAvailable()).thenReturn(true);
        service = new PropertyCoordinateAuditService(repository, null, null);
    }

    private boolean verify(PropertyCoordinateAudit.Accuracy accuracy, Double meters,
                           PropertyCoordinateAudit.Verification status,
                           PropertyCoordinateAudit.VerificationMethod method,
                           String evidence) {
        return service.verify("property-id", 1, status, method, 7L, evidence,
            accuracy, meters, "TEST_METHOD");
    }

    @Test
    void unknownAllowsOnlyNullMeters() {
        assertFalse(verify(PropertyCoordinateAudit.Accuracy.UNKNOWN, null,
            PropertyCoordinateAudit.Verification.PENDING_REVIEW, null, null));
        assertThrows(ApiException.class, () -> verify(PropertyCoordinateAudit.Accuracy.UNKNOWN, 1.0,
            PropertyCoordinateAudit.Verification.PENDING_REVIEW, null, null));
    }

    @Test
    void streetAllowsNullOrPositiveFiniteMeters() {
        assertFalse(verify(PropertyCoordinateAudit.Accuracy.STREET, null,
            PropertyCoordinateAudit.Verification.PENDING_REVIEW, null, null));
        assertFalse(verify(PropertyCoordinateAudit.Accuracy.STREET, 0.25,
            PropertyCoordinateAudit.Verification.PENDING_REVIEW, null, null));
        for (Double invalid : new Double[] {0.0, -1.0, Double.NaN,
                Double.POSITIVE_INFINITY, Double.NEGATIVE_INFINITY}) {
            assertThrows(ApiException.class, () -> verify(PropertyCoordinateAudit.Accuracy.STREET,
                invalid, PropertyCoordinateAudit.Verification.PENDING_REVIEW, null, null));
        }
    }

    @Test
    void parcelRequiresPositiveFiniteMetersAndVerificationEvidence() {
        for (Double invalid : new Double[] {null, 0.0, -1.0, Double.NaN,
                Double.POSITIVE_INFINITY, Double.NEGATIVE_INFINITY}) {
            assertThrows(ApiException.class, () -> verify(PropertyCoordinateAudit.Accuracy.PARCEL,
                invalid, PropertyCoordinateAudit.Verification.VERIFIED,
                PropertyCoordinateAudit.VerificationMethod.FIELD_SURVEY, "evidence"));
        }
        assertThrows(ApiException.class, () -> verify(PropertyCoordinateAudit.Accuracy.PARCEL, 1.0,
            PropertyCoordinateAudit.Verification.VERIFIED, null, "evidence"));
        assertThrows(ApiException.class, () -> verify(PropertyCoordinateAudit.Accuracy.PARCEL, 1.0,
            PropertyCoordinateAudit.Verification.VERIFIED,
            PropertyCoordinateAudit.VerificationMethod.FIELD_SURVEY, " "));
        assertFalse(verify(PropertyCoordinateAudit.Accuracy.PARCEL, 1.0,
            PropertyCoordinateAudit.Verification.VERIFIED,
            PropertyCoordinateAudit.VerificationMethod.FIELD_SURVEY, "evidence"));
    }

    @Test
    void unavailableAuditSchemaFailsClosedWithoutBreakingPropertyStatusReads() {
        when(repository.schemaAvailable()).thenReturn(false);
        assertEquals("UNKNOWN", service.statuses(java.util.List.of("p1")).get("p1").accuracyLevel());
        assertThrows(ApiException.class, () -> service.status("p1"));
        ApiException error = assertThrows(ApiException.class, () -> service.history("p1"));
        assertEquals(503, error.status);
        assertEquals("COORDINATE_AUDIT_UNAVAILABLE", error.code);
    }

    @Test
    void repositoryDetectsStandardLineageWithoutSuppressingMetadataErrors() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForObject(contains("information_schema.tables"), eq(Integer.class))).thenReturn(0);
        when(jdbc.queryForObject("SELECT DATABASE()", String.class)).thenReturn("smartprop_v23");
        assertFalse(new PropertyCoordinateAuditRepository(jdbc).schemaAvailable());

        JdbcTemplate unavailableMetadata = mock(JdbcTemplate.class);
        when(unavailableMetadata.queryForObject(contains("information_schema.tables"), eq(Integer.class)))
            .thenThrow(new org.springframework.jdbc.BadSqlGrammarException("probe", "query", null));
        assertThrows(org.springframework.jdbc.BadSqlGrammarException.class,
            () -> new PropertyCoordinateAuditRepository(unavailableMetadata));
    }

    @Test
    void pendingPageClampsBoundsAndCountsTheSameFilters() {
        when(repository.pending(200, "UNVERIFIED", "listing", 0)).thenReturn(java.util.List.of());
        when(repository.pendingCount("UNVERIFIED", "listing")).thenReturn(241L);

        var page = service.pendingPage(500, -10, "UNVERIFIED", "listing");

        assertEquals(241L, page.total());
        assertEquals(0, page.offset());
        assertEquals(200, page.limit());
        org.mockito.Mockito.verify(repository).pending(200, "UNVERIFIED", "listing", 0);
        org.mockito.Mockito.verify(repository).pendingCount("UNVERIFIED", "listing");
    }
}
