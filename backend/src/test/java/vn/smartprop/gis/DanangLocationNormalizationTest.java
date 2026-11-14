package vn.smartprop.gis;

import static org.junit.jupiter.api.Assertions.*;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.Optional;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import vn.smartprop.modules.amenity.AmenityCatalogService;
import vn.smartprop.modules.amenity.AmenityDtos.AmenityProfile;
import vn.smartprop.gis.GisDtos.AdminNormalizationResult;
import vn.smartprop.gis.GisDtos.AdminNormalizationStatus;
import vn.smartprop.gis.GisDtos.CoordinateStatus;
import vn.smartprop.gis.GisDtos.CoordinateValidationResult;

class DanangLocationNormalizationTest {

    private static DanangAdminNormalizer normalizer;
    private static DanangSpatialValidator validator;
    private static AmenityCatalogService catalogService;

    @BeforeAll
    static void setUp() {
        ObjectMapper mapper = new ObjectMapper();
        normalizer = new DanangAdminNormalizer();
        validator = new DanangSpatialValidator(mapper);
        catalogService = new AmenityCatalogService(mapper);
    }

    @ParameterizedTest
    @CsvSource({
        "'Quận Hải Châu', 'Phường Thạch Thang', 'TP. Đà Nẵng', 'Hải Châu', 'Thạch Thang', 'Thạch Thang'",
        "'Q. Thanh Khê', 'P. Thạc Gián', 'Đà Nẵng', 'Thanh Khê', 'Thạc Gián', 'Thạc Gián'",
        "'quan son tra', 'phuong phuoc my', 'thanh pho da nang', 'Sơn Trà', 'Phước Mỹ', 'Phước Mỹ'",
        "'Ngũ Hành Sơn', 'Mỹ An', '', 'Ngũ Hành Sơn', 'Mỹ An', 'Mỹ An'",
        "'Liên Chiểu', 'Hòa Minh', 'Da Nang', 'Liên Chiểu', 'Hòa Minh', 'Hòa Minh'",
        "'Cẩm Lệ', 'Khuê Trung', 'Đà Nẵng', 'Cẩm Lệ', 'Khuê Trung', 'Khuê Trung'",
        "'Huyện Hoà Vang', 'Xã Hoà Liên', 'Đà Nẵng', 'Hòa Vang', 'Hòa Liên', 'Hòa Liên'"
    })
    @DisplayName("Canonical 7 Da Nang districts, accents/orthography, and administrative prefixes")
    void resolvesCanonicalDistrictsAndWards(
            String rawDistrict,
            String rawWard,
            String rawCity,
            String expectedDistrict,
            String expectedDisplayWard,
            String expectedCatalogWard) {
        AdminNormalizationResult res = normalizer.normalize(rawDistrict, rawWard, rawCity);
        assertEquals(AdminNormalizationStatus.RESOLVED_CANONICAL, res.status());
        assertEquals(expectedDistrict, res.canonicalDistrict());
        assertEquals(expectedDisplayWard, res.displayWard());
        assertEquals(expectedCatalogWard, res.catalogWard());
        assertTrue(res.isResolvedDanangCore());

        Optional<AmenityProfile> profile = catalogService.lookup(res.canonicalDistrict(), res.catalogWard(), null);
        assertTrue(profile.isPresent());
        assertEquals("WARD", profile.get().areaLevel());
    }

    @ParameterizedTest
    @CsvSource({
        "'Hải Châu', 'Hải Châu 1', 'Hải Châu I'",
        "'Hải Châu', 'Phường Hải Châu 01', 'Hải Châu I'",
        "'Quận Hải Châu', 'Hải Châu 2', 'Hải Châu II'",
        "'Hải Châu', 'P. Hải Châu 02', 'Hải Châu II'"
    })
    @DisplayName("Roman vs Arabic numeral ward normalization (Hải Châu 1/2 -> Hải Châu I/II)")
    void normalizesRomanNumeralWardsAndMatchesWardCatalog(String rawDistrict, String rawWard, String expectedRoman) {
        AdminNormalizationResult res = normalizer.normalize(rawDistrict, rawWard, "Đà Nẵng");
        assertEquals(AdminNormalizationStatus.RESOLVED_ROMAN_VARIANT, res.status());
        assertEquals("Hải Châu", res.canonicalDistrict());
        assertEquals(expectedRoman, res.displayWard());
        assertEquals(expectedRoman, res.catalogWard());
        assertNotNull(res.provenanceNote());

        Optional<AmenityProfile> profile = catalogService.lookup(res.canonicalDistrict(), res.catalogWard(), null);
        assertTrue(profile.isPresent());
        assertEquals("WARD", profile.get().areaLevel());
    }

    @ParameterizedTest
    @CsvSource({
        "'Hải Châu', 'Nam Dương', 'Phước Ninh'",
        "'Thanh Khê', 'Tam Thuận', 'Xuân Hà'",
        "'Thanh Khê', 'Tân Chính', 'Chính Gián'"
    })
    @DisplayName("NQ 1251/NQ-UBTVQH15 (2024) merged historical wards bridge cleanly to successor ward catalog")
    void resolvesNq1251MergedHistoricalWards(String district, String legacyWard, String successorCatalogWard) {
        AdminNormalizationResult res = normalizer.normalize(district, legacyWard, "Đà Nẵng");
        assertEquals(AdminNormalizationStatus.RESOLVED_HISTORICAL_MERGED_WARD, res.status());
        assertEquals(district, res.canonicalDistrict());
        assertEquals(legacyWard, res.displayWard());
        assertEquals(successorCatalogWard, res.catalogWard());
        assertTrue(res.provenanceNote().contains("1251"));

        Optional<AmenityProfile> profile = catalogService.lookup(res.canonicalDistrict(), res.catalogWard(), null);
        assertTrue(profile.isPresent());
        assertEquals("WARD", profile.get().areaLevel());
    }

    @Test
    @DisplayName("NQ 1251/NQ-UBTVQH15 newly formed wards (Phường Hải Châu, Phường An Hải Nam) resolve directly to WARD catalog")
    void resolvesNq1251SuccessorWardsInCatalog() {
        AdminNormalizationResult haiChauWard = normalizer.normalize("Hải Châu", "Phường Hải Châu", "Đà Nẵng");
        assertEquals(AdminNormalizationStatus.RESOLVED_CANONICAL, haiChauWard.status());
        assertEquals("Hải Châu", haiChauWard.canonicalDistrict());
        assertEquals("Hải Châu", haiChauWard.catalogWard());
        assertEquals("WARD", catalogService.lookup("Hải Châu", haiChauWard.catalogWard(), null).orElseThrow().areaLevel());

        AdminNormalizationResult anHaiNam = normalizer.normalize("Sơn Trà", "An Hải Nam", "Đà Nẵng");
        assertEquals(AdminNormalizationStatus.RESOLVED_CANONICAL, anHaiNam.status());
        assertEquals("Sơn Trà", anHaiNam.canonicalDistrict());
        assertEquals("An Hải Nam", anHaiNam.catalogWard());
        assertEquals("WARD", catalogService.lookup("Sơn Trà", anHaiNam.catalogWard(), null).orElseThrow().areaLevel());
    }

    @Test
    @DisplayName("NĐ 24/2005/NĐ-CP split ward Bắc Mỹ An resolves Ngũ Hành Sơn district without guessing Mỹ An vs Khuê Mỹ")
    void handlesHistoricalSplitWardBacMyAnWithoutGuessing() {
        AdminNormalizationResult res = normalizer.normalize("Ngũ Hành Sơn", "Bắc Mỹ An", "Đà Nẵng");
        assertEquals(AdminNormalizationStatus.HISTORICAL_SPLIT_WARD_AMBIGUOUS, res.status());
        assertEquals("Ngũ Hành Sơn", res.canonicalDistrict());
        assertNull(res.catalogWard(), "Must not guess between Mỹ An and Khuê Mỹ");
        assertTrue(res.provenanceNote().contains("24/2005"));

        // Conflicting district + Bắc Mỹ An must fail hierarchy check
        AdminNormalizationResult conflict = normalizer.normalize("Hải Châu", "Bắc Mỹ An", "Đà Nẵng");
        assertEquals(AdminNormalizationStatus.CONFLICTING_ADMIN_HIERARCHY, conflict.status());
        assertNull(conflict.canonicalDistrict());
    }

    @ParameterizedTest
    @CsvSource({
        "'Phường Hòa Cường', 'Hải Châu'",
        "'Phường An Hải', 'Sơn Trà'",
        "'Phường Ngũ Hành Sơn', 'Ngũ Hành Sơn'",
        "'Xã Bà Nà', 'Hòa Vang'",
        "'Xã Hòa Tiến', 'Hòa Vang'"
    })
    @DisplayName("NQ 1659/NQ-UBTVQH15 (2025) single-district new wards map to parent district without fabricating a single old ward")
    void resolvesPost2025SingleDistrictNewWards(String newWard, String expectedParentDistrict) {
        AdminNormalizationResult res = normalizer.normalize("", newWard, "Đà Nẵng");
        assertEquals(AdminNormalizationStatus.RESOLVED_POST_2025_NEW_WARD, res.status());
        assertEquals(expectedParentDistrict, res.canonicalDistrict());
        assertNull(res.catalogWard(), "Multi-ward post-2025 unit must use district profile rather than guessing 1 old ward");
    }

    @ParameterizedTest
    @CsvSource({
        "'Phường An Khê', 'Thanh Khê', 'Cẩm Lệ'",
        "'Phường Hòa Xuân', 'Cẩm Lệ', 'Hòa Vang'",
        "'Phường Hòa Khánh', 'Liên Chiểu', 'Hòa Vang'",
        "'Phường Liên Chiểu', 'Liên Chiểu', 'Hòa Vang'",
        "'Phường Hải Vân', 'Liên Chiểu', 'Hòa Vang'"
    })
    @DisplayName("NQ 1659/NQ-UBTVQH15 cross-district merged wards refuse to guess when district is omitted, but resolve when historical district is provided")
    void refusesToGuessCrossDistrictWardsWithoutContext(String bareWard, String candA, String candB) {
        AdminNormalizationResult bare = normalizer.normalize("", bareWard, "Đà Nẵng");
        assertEquals(AdminNormalizationStatus.AMBIGUOUS_CROSS_DISTRICT_WARD, bare.status());
        assertNull(bare.canonicalDistrict(), "Must never guess a single historical district for cross-district NQ 1659 ward");
        assertNull(bare.catalogWard());
        assertTrue(bare.candidateDistricts().contains(candA));
        assertTrue(bare.candidateDistricts().contains(candB));

        // When historical district is explicitly supplied, resolves cleanly
        AdminNormalizationResult withDist = normalizer.normalize(candA, bareWard, "Đà Nẵng");
        assertEquals(candA, withDist.canonicalDistrict());
        assertTrue(
            withDist.status() == AdminNormalizationStatus.RESOLVED_CANONICAL
                || withDist.status() == AdminNormalizationStatus.RESOLVED_POST_2025_NEW_WARD
        );
    }

    @Test
    @DisplayName("Conflicting district-ward hierarchy, former Quảng Nam, Hoàng Sa, outside provinces, and street-only incomplete inputs")
    void rejectsConflictsOutOfScopeAndIncompleteAddresses() {
        // Conflicting district + ward
        AdminNormalizationResult conflict = normalizer.normalize("Hải Châu", "Phước Mỹ", "Đà Nẵng");
        assertEquals(AdminNormalizationStatus.CONFLICTING_ADMIN_HIERARCHY, conflict.status());
        assertNull(conflict.canonicalDistrict());

        // Former Quảng Nam post-07/2025 localities
        AdminNormalizationResult hoiAn = normalizer.normalize("Hội An", "Cẩm Châu", "Đà Nẵng");
        assertEquals(AdminNormalizationStatus.EXTENDED_QUANG_NAM_JURISDICTION, hoiAn.status());
        assertNull(hoiAn.canonicalDistrict());

        AdminNormalizationResult dienBan = normalizer.normalize("Điện Bàn", "Điện Ngọc", "");
        assertEquals(AdminNormalizationStatus.EXTENDED_QUANG_NAM_JURISDICTION, dienBan.status());

        // Hoàng Sa island district
        AdminNormalizationResult hoangSa = normalizer.normalize("Huyện đảo Hoàng Sa", "", "Đà Nẵng");
        assertEquals(AdminNormalizationStatus.EXCLUDED_ISLAND_DISTRICT, hoangSa.status());
        assertNull(hoangSa.canonicalDistrict());

        // Outside Da Nang traps
        AdminNormalizationResult haiPhong = normalizer.normalizeAddress(
            "15 Đường Đà Nẵng, Quận Ngô Quyền, Hải Phòng", "", "", "");
        assertEquals(AdminNormalizationStatus.OUTSIDE_DANANG, haiPhong.status());

        AdminNormalizationResult satDaNang = normalizer.normalizeAddress(
            "KĐT sát Đà Nẵng, Điện Ngọc, Điện Bàn, Quảng Nam", "", "", "");
        assertEquals(AdminNormalizationStatus.OUTSIDE_DANANG, satDaNang.status());

        // Street-only incomplete address -> must NOT guess district/ward
        AdminNormalizationResult streetOnly = normalizer.normalizeAddress(
            "123 Nguyễn Văn Linh", "", "", "Đà Nẵng");
        assertEquals(AdminNormalizationStatus.INCOMPLETE_LOCATION, streetOnly.status());
        assertNull(streetOnly.canonicalDistrict());
        assertNull(streetOnly.catalogWard());

        // Full comma-separated Da Nang address -> extracts ward & district cleanly
        AdminNormalizationResult fullAddr = normalizer.normalizeAddress(
            "123 Nguyễn Văn Linh, Phường Nam Dương, Quận Hải Châu, Đà Nẵng", "", "", "");
        assertEquals(AdminNormalizationStatus.RESOLVED_HISTORICAL_MERGED_WARD, fullAddr.status());
        assertEquals("Hải Châu", fullAddr.canonicalDistrict());
        assertEquals("Phước Ninh", fullAddr.catalogWard());
    }

    @Test
    @DisplayName("Spatial polygon validator: exact match, boundary buffer, misplaced viewport pin (7e6c0fcf), swapped axes, invalid & null TiniX")
    void validatesSpatialPolygonsAndNeverFabricatesCoordinates() {
        assertEquals("OCHA-2020-geoBoundaries-9469f09", validator.scopeVersion());

        // 1. Exact point inside Hải Châu (Dragon Bridge west bank)
        CoordinateValidationResult exact = validator.validate(16.0611, 108.2215, "Hải Châu", true);
        assertEquals(CoordinateStatus.VERIFIED_EXACT, exact.status());
        assertTrue(exact.usableForPinAndPoi());
        assertEquals(16.0611, exact.verifiedLatitude());
        assertEquals(108.2215, exact.verifiedLongitude());
        assertEquals("Hải Châu", exact.matchedPolygonDistrict());

        // 2. Real anomaly in DB: property 7e6c0fcf-a092-48ec-ae9e-f2be0ee159aa (declared Liên Chiểu, pinned at Hải Châu center 16.0544, 108.2022)
        CoordinateValidationResult mismatch = validator.validate(16.0544, 108.2022, "Liên Chiểu", true);
        assertEquals(CoordinateStatus.INVALID_DISTRICT_MISMATCH, mismatch.status());
        assertFalse(mismatch.usableForPinAndPoi(), "Misplaced viewport pin must NEVER be plotted or used for POI distances");
        assertNull(mismatch.verifiedLatitude());
        assertNull(mismatch.verifiedLongitude());
        assertEquals("Hải Châu", mismatch.matchedPolygonDistrict());
        assertTrue(mismatch.distanceToDeclaredPolygonMeters() > 2000.0);

        // 3. Swapped lat/lon axes (108.22, 16.06)
        CoordinateValidationResult swapped = validator.validate(108.2215, 16.0611, "Hải Châu", true);
        assertEquals(CoordinateStatus.INVALID_SWAPPED_AXES, swapped.status());
        assertFalse(swapped.usableForPinAndPoi());
        assertNull(swapped.verifiedLatitude());

        // 4. Zero (0,0) and NaN
        assertEquals(CoordinateStatus.INVALID_COORDINATES, validator.validate(0.0, 0.0, "Hải Châu", true).status());
        assertEquals(CoordinateStatus.INVALID_COORDINATES, validator.validate(Double.NaN, 108.20, "Hải Châu", true).status());

        // 5. Out of Da Nang bounds (Hội An / Hà Nội)
        CoordinateValidationResult hoiAnPt = validator.validate(15.8794, 108.3350, "Ngũ Hành Sơn", true);
        assertEquals(CoordinateStatus.OUTSIDE_DANANG_BOUNDS, hoiAnPt.status());
        assertFalse(hoiAnPt.usableForPinAndPoi());

        // 6. TiniX / External null coordinates -> NONE_ADMIN_ONLY, zero fabricated coordinates
        CoordinateValidationResult tinix = validator.validate(null, null, "Sơn Trà", false);
        assertEquals(CoordinateStatus.NONE_ADMIN_ONLY, tinix.status());
        assertFalse(tinix.usableForPinAndPoi());
        assertNull(tinix.verifiedLatitude());
        assertNull(tinix.verifiedLongitude());

        // 7. Non-platform record even if someone passed coordinates with allowPublicPin=false -> usableForPinAndPoi=false
        CoordinateValidationResult researchGuard = validator.validate(16.0611, 108.2215, "Hải Châu", false);
        assertFalse(researchGuard.usableForPinAndPoi());
        assertNull(researchGuard.verifiedLatitude());
        assertNull(researchGuard.verifiedLongitude());
    }
}

