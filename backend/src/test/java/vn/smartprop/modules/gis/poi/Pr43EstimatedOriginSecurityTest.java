package vn.smartprop.modules.gis.poi;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.locationtech.jts.geom.Coordinate;
import org.locationtech.jts.geom.GeometryFactory;
import org.locationtech.jts.geom.PrecisionModel;
import vn.smartprop.common.ApiException;
import vn.smartprop.gis.DanangAdminNormalizer;
import vn.smartprop.gis.DanangSpatialValidator;
import vn.smartprop.gis.GisDtos;
import vn.smartprop.modules.property.Property;
import vn.smartprop.modules.property.PropertyCoordinateAudit;
import vn.smartprop.modules.property.PropertyCoordinateAuditRepository;
import vn.smartprop.modules.property.PropertyCoordinateAuditService;
import vn.smartprop.modules.property.PropertyDtos;
import vn.smartprop.modules.property.PropertyService;

class Pr43EstimatedOriginSecurityTest {
    private final PropertyService properties = mock(PropertyService.class);
    private final PointOfInterestRepository poiRepo = mock(PointOfInterestRepository.class);
    private final GeoapifyPlacesClient geoapify = mock(GeoapifyPlacesClient.class);
    private final PropertyCoordinateAuditService coordinateAudit = mock(PropertyCoordinateAuditService.class);
    private final ObjectMapper json = new ObjectMapper();
    private NearbyService service;
    private Property property;

    @BeforeEach
    void setup() {
        service = new NearbyService(properties, poiRepo, geoapify, new PropertyLocationEvidence(json, ""), coordinateAudit);
        property = new Property();
        property.id = "legacy-prop-1";
        property.contentVersion = 1;
        property.district = "Cẩm Lệ";
        property.ward = "Hòa Xuân";
        property.location = new GeometryFactory(new PrecisionModel(), 4326).createPoint(new Coordinate(108.215, 16.005));
        when(properties.publicProperty(property.id)).thenReturn(property);
        when(poiRepo.nearby(anyString(), isNull(), anyDouble(), anyInt())).thenReturn(List.of());
    }

    @Test
    void legacyReferenceNeverGrantsDistanceOrParcelEligibilityAndBlocksOutsideDanang() {
        var repo = mock(PropertyCoordinateAuditRepository.class);
        var validator = mock(DanangSpatialValidator.class);
        var normalizer = mock(DanangAdminNormalizer.class);
        var auditSvc = new PropertyCoordinateAuditService(repo, validator, normalizer);

        when(normalizer.normalize(any(), any(), any()))
            .thenReturn(new GisDtos.AdminNormalizationResult(
                GisDtos.AdminNormalizationStatus.RESOLVED_CANONICAL,
                "Cẩm Lệ", "Hòa Xuân", "Hòa Xuân", "Hòa Xuân, Cẩm Lệ", List.of("Cẩm Lệ"), "ok"));
        when(validator.validate(anyDouble(), anyDouble(), any(), anyBoolean()))
            .thenReturn(new GisDtos.CoordinateValidationResult(
                GisDtos.CoordinateStatus.VERIFIED_EXACT, true, 16.005, 108.215, "Cẩm Lệ", 0.0, "Inside Da Nang"));
        var inside = auditSvc.legacyReference(property);
        assertEquals("UNVERIFIED", inside.verificationStatus());
        assertEquals("UNKNOWN", inside.coordinateSource());
        assertEquals("UNKNOWN", inside.accuracyLevel());
        assertTrue(inside.referenceMapEligible());
        assertFalse(inside.distanceAnalysisEligible(), "Legacy pin must NEVER widen verified distance eligibility");
        assertFalse(inside.parcelAnalysisEligible());

        when(validator.validate(anyDouble(), anyDouble(), any(), anyBoolean()))
            .thenReturn(new GisDtos.CoordinateValidationResult(
                GisDtos.CoordinateStatus.OUTSIDE_DANANG_BOUNDS, false, null, null, null, null, "Outside Da Nang"));
        var outside = auditSvc.legacyReference(property);
        assertFalse(outside.referenceMapEligible(), "Out-of-bounds legacy pin must be blocked from reference map");
        assertFalse(outside.distanceAnalysisEligible());
    }

    @Test
    void allowEstimatedOriginAllowsReferenceEligibleLegacyPinWithoutPromotingAdvisorOrigin() throws Exception {
        when(coordinateAudit.available()).thenReturn(true);
        when(coordinateAudit.status(property.id)).thenReturn(PropertyCoordinateAudit.Status.absent());
        var legacyCoord = PropertyDtos.Coordinate.of(
            PropertyCoordinateAudit.derive("UNKNOWN", "UNKNOWN", null, "UNVERIFIED",
                null, null, null, "VERIFIED_EXACT", "Legacy pin", 0, null));
        when(properties.coordinate(property.id)).thenReturn(legacyCoord);
        when(geoapify.search(anyDouble(), anyDouble(), anyInt(), anyList()))
            .thenReturn(json.readTree("{\"features\":[]}"));

        // Default allowEstimatedOrigin=false stays LOCATION_UNVERIFIED:
        var strict = service.nearby(property.id, 1000, "education", false);
        assertEquals("LOCATION_UNVERIFIED", strict.status());
        verifyNoInteractions(geoapify);

        // Explicit allowEstimatedOrigin=true serves straight-line nearby POIs:
        var estimated = service.nearby(property.id, 1000, "education", true);
        assertEquals("EMPTY", estimated.status());
        assertEquals("UNKNOWN", estimated.location().accuracy());

        // advisorOrigin (commute matrix / verified commute) still returns null:
        assertNull(service.advisorOrigin(property.id));
    }

    @Test
    void rejectedCoordinateRemainsBlockedEvenWhenAllowEstimatedOriginIsTrue() {
        when(coordinateAudit.available()).thenReturn(true);
        var rejectedStatus = new PropertyCoordinateAudit.Status(
            "USER_PINNED", "STREET", 15.0, "REJECTED", "ADMIN_REVIEW", Instant.now(),
            "VERIFIED_EXACT", "Rejected pin", false, false, false, 2, Instant.now());
        when(coordinateAudit.status(property.id)).thenReturn(rejectedStatus);
        when(properties.coordinate(property.id)).thenReturn(PropertyDtos.Coordinate.of(rejectedStatus));

        var nearby = service.nearby(property.id, 1000, "education", true);
        assertEquals("LOCATION_UNVERIFIED", nearby.status());
        var advisor = service.forAdvisor(property.id, 1000, "education", true);
        assertEquals("LOCATION_UNVERIFIED", advisor.status());
        verifyNoInteractions(geoapify, poiRepo);
    }

    @Test
    void privateOrUnpublishedPropertyFailsBeforeEstimatedCoordinateCheck() {
        when(properties.publicProperty("draft-prop")).thenThrow(new ApiException(404, "NOT_FOUND", "Not found"));
        assertEquals(404, assertThrows(ApiException.class,
            () -> service.nearby("draft-prop", 1000, "education", true)).status);
        verifyNoInteractions(coordinateAudit, geoapify, poiRepo);
    }

    @Test
    void legacyGroupMapsAllPersistedPoiCategories() {
        assertEquals("health", NearbyService.legacyGroup("PHARMACY"));
        assertEquals("shopping", NearbyService.legacyGroup("MARKET"));
        assertEquals("shopping", NearbyService.legacyGroup("MALL"));
        assertEquals("tourism", NearbyService.legacyGroup("BEACH"));
        assertEquals("transport", NearbyService.legacyGroup("PUBLIC_TRANSPORT"));
    }
}
