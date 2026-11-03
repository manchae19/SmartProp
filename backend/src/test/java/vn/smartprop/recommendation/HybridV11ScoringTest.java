package vn.smartprop.recommendation;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import vn.smartprop.amenity.AmenityCatalogService;
import vn.smartprop.amenity.AmenityDtos.AmenityProfile;
import vn.smartprop.recommendation.PropertyLocationResolver.Resolution;

import java.math.BigDecimal;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static vn.smartprop.recommendation.RecommendationDtos.*;

class HybridV11ScoringTest {
    private final AmenityCatalogService catalog = new AmenityCatalogService(new ObjectMapper());
    private final PropertyLocationResolver resolver = new PropertyLocationResolver(catalog);
    private final PropertyScoringV11Service scorer = new PropertyScoringV11Service(resolver,
        0.38, 0.17, 0.20, 0.25, 0.45, 0.25, 0.20, 0.10, 0.40, 0.20, 0.25, 0.15);
    private final AmenityEvidenceService evidence = new AmenityEvidenceService();

    static Candidate candidate(String id, PropertyType type, String price, String area, String district, String ward) {
        return new Candidate(id, id, type, new BigDecimal(price), new BigDecimal(area), district, ward,
            new Source("EXTERNAL", "fixture", id, "https://example.invalid/" + id),
            "VALID", "UNVERIFIED", null, false, false, List.of(), false);
    }

    static Request request(long budget, Purpose purpose) {
        return new Request(BigDecimal.valueOf(budget), purpose, PropertyType.ALL, null, null, null, 10);
    }

    @Test void weightsPerPurposeSumToOneAndStayConfigurable() {
        for (var p : Purpose.values()) {
            var w = scorer.weights().asMap(p);
            assertEquals(1.0, w.values().stream().mapToDouble(Double::doubleValue).sum(), 1e-9);
        }
        assertEquals(0.25, scorer.weights().asMap(Purpose.LIVING).get("amenityFit"), 1e-9);
        assertEquals(0.10, scorer.weights().asMap(Purpose.INVESTMENT).get("amenityFit"), 1e-9);
    }

    @Test void invalidWeightsFailFastInsteadOfSilentlyMiscalculating() {
        assertThrows(IllegalStateException.class, () -> new PropertyScoringV11Service(resolver,
            0.5, 0.5, 0.5, 0.5, 0.45, 0.25, 0.20, 0.10, 0.40, 0.20, 0.25, 0.15));
        assertThrows(IllegalStateException.class, () -> new PropertyScoringV11Service(resolver,
            -0.1, 0.17, 0.20, 0.25, 0.45, 0.25, 0.20, 0.10, 0.40, 0.20, 0.25, 0.15));
    }

    @Test void livingPrefersLiveableTypesOverRawLandWithoutDeletingLand() {
        assertTrue(PropertyScoringV11Service.typeFit(PropertyType.HOUSE, Purpose.LIVING)
            > PropertyScoringV11Service.typeFit(PropertyType.LAND, Purpose.LIVING));
        assertTrue(PropertyScoringV11Service.typeFit(PropertyType.APARTMENT, Purpose.LIVING)
            > PropertyScoringV11Service.typeFit(PropertyType.LAND, Purpose.LIVING));
        assertTrue(PropertyScoringV11Service.typeFit(PropertyType.LAND, Purpose.LIVING) > 0,
            "LAND must stay eligible, only ranked lower");
        assertEquals(100.0, PropertyScoringV11Service.typeFit(PropertyType.APARTMENT, Purpose.RENTAL), 1e-9);
        assertEquals(95.0, PropertyScoringV11Service.typeFit(PropertyType.LAND, Purpose.INVESTMENT), 1e-9);
    }

    @Test void scoresStayBoundedAndNeverNaNForEveryPurposeAndType() {
        for (var purpose : Purpose.values()) {
            for (var type : List.of(PropertyType.HOUSE, PropertyType.APARTMENT, PropertyType.LAND, PropertyType.VILLA)) {
                for (var budget : List.of(750_000_000L, 2_000_000_000L, 5_000_000_000L)) {
                    var s = scorer.score(candidate("x", type, "1600000000", "80", "Hải Châu", null),
                        request(budget, purpose));
                    assertTrue(Double.isFinite(s.score()));
                    assertTrue(s.score() >= 0 && s.score() <= 100, "score out of range: " + s.score());
                }
            }
        }
    }

    @Test void budgetHardLimitIsRespectedAndScoreFallsAtTheCeiling() {
        var exact = candidate("at", PropertyType.HOUSE, "2000000000", "80", "Hải Châu", null);
        var under = candidate("under", PropertyType.HOUSE, "1600000000", "80", "Hải Châu", null);
        var over = candidate("over", PropertyType.HOUSE, "2000000001", "80", "Hải Châu", null);
        var service = service(List.of(exact, under, over), true);
        var result = service.recommend(request(2_000_000_000L, Purpose.LIVING));
        assertTrue(result.topProperties().stream().noneMatch(p -> p.id().equals("over")));
        assertEquals(2, result.eligibleCandidateCount());
        assertTrue(scorer.score(under, request(2_000_000_000L, Purpose.LIVING)).score()
            > scorer.score(exact, request(2_000_000_000L, Purpose.LIVING)).score(),
            "leaving a margin under the ceiling should rank above spending the whole budget");
    }

    @Test void wardLevelAmenityIsStrongerEvidenceThanDistrictFallback() {
        var wardCandidate = candidate("w", PropertyType.HOUSE, "1600000000", "80", "Ngũ Hành Sơn", "Mỹ An");
        var districtOnly = candidate("d", PropertyType.HOUSE, "1600000000", "80", "Ngũ Hành Sơn", "Ward Not In Catalog");
        var ward = resolver.resolve("Ngũ Hành Sơn", "Mỹ An");
        var district = resolver.resolve("Ngũ Hành Sơn", "Ward Not In Catalog");
        assertEquals(PropertyLocationResolver.BASIS_DIRECT_WARD, ward.evidenceBasis());
        assertEquals(PropertyLocationResolver.BASIS_DISTRICT, district.evidenceBasis());
        assertNotNull(district.profile());
        assertTrue(district.confidence() <= 0.80 + 1e-9, "district evidence must be capped below ward-level trust");
        var wardScored = scorer.score(wardCandidate, request(2_000_000_000L, Purpose.LIVING), ward);
        var districtScored = scorer.score(districtOnly, request(2_000_000_000L, Purpose.LIVING), district);
        assertTrue(wardScored.appliedWeights().get("amenityFit") > districtScored.appliedWeights().get("amenityFit"));
    }

    @Test void wardLookupNeverBorrowsAProfileFromAnotherDistrict() {
        var resolution = resolver.resolve("Hải Châu", "Mỹ An");
        assertEquals(PropertyLocationResolver.BASIS_DISTRICT, resolution.evidenceBasis(),
            "a same-named ward in another district must not be used");
        assertEquals("Hải Châu", resolution.profile().parentDistrict());
    }

    @Test void unknownLocationGetsNoInventedAmenityScoreAndKeepsFullRange() {
        var c = candidate("u", PropertyType.HOUSE, "1600000000", "80", null, null);
        var unknown = resolver.resolve(null, null);
        assertFalse(unknown.available());
        var scored = scorer.score(c, request(2_000_000_000L, Purpose.LIVING), unknown);
        assertNull(scored.amenityFit());
        assertFalse(scored.parts().containsKey("amenityFit"));
        var payload = evidence.unavailable(unknown);
        assertNull(payload.areaAmenityScore());
        assertNull(payload.amenityFit());
        assertEquals(0.0, payload.confidence());
        assertEquals("UNKNOWN", payload.coverage());
        assertTrue(payload.dataLimitations().stream().anyMatch(l -> l.contains("khoảng cách")));
    }

    @Test void amenitiesJsonNeverLeaksResearchSampleCount() throws Exception {
        var mapper = new ObjectMapper();
        var profile = catalog.getById("ward-my-an-ngu-hanh-son").orElseThrow();
        assertTrue(profile.sampleListingCount() > 0, "catalog does carry the research count internally");
        String json = mapper.writeValueAsString(profile);
        assertFalse(json.contains("sampleListingCount"), "public amenities payload must not expose TiniX sample counts");
        String summaryJson = mapper.writeValueAsString(catalog.listAreas("WARD", null));
        assertFalse(summaryJson.contains("sampleListingCount"));
    }

    @Test void publicEvidenceOmitsCoordinatesAndResearchCounts() {
        var resolution = resolver.resolve("Ngũ Hành Sơn", "Mỹ An");
        var payload = evidence.build(resolution.profile(), resolution, PropertyScoringV11Service.round(resolution.profile().livingScore()));
        assertNotNull(payload);
        assertEquals("WARD", payload.areaLevel());
        assertEquals(PropertyLocationResolver.BASIS_DIRECT_WARD, payload.evidenceBasis());
        assertTrue(payload.poiEvidence().size() <= AmenityEvidenceService.MAX_EVIDENCE_ITEMS);
        assertNotNull(payload.categoryScores().get("education"));
        assertTrue(payload.dataLimitations().stream().anyMatch(l -> l.contains("khoảng cách")));
        assertEquals(5, payload.categoryScores().size());
    }

    @Test void districtEvidenceEmitsSharedAmenityWarningAndCap() {
        var resolution = resolver.resolve("Liên Chiểu", "Ward Not In Catalog");
        var payload = evidence.build(resolution.profile(), resolution, null);
        assertTrue(payload.note().contains("quận/huyện"));
        assertTrue(payload.dataLimitations().stream().anyMatch(l -> l.contains("quận/huyện")));
        assertTrue(payload.confidence() <= 0.80 + 1e-9);
    }

    @Test void featureFlagOffKeepsV1ContractAndFeatureFlagOnAddsEvidence() {
        var values = List.of(candidate("a", PropertyType.HOUSE, "1600000000", "80", "Ngũ Hành Sơn", "Mỹ An"));
        var off = service(values, false).recommend(request(2_000_000_000L, Purpose.LIVING));
        assertEquals("HEURISTIC_V1", off.method());
        assertNull(off.topProperties().getFirst().amenityEvidence());
        assertFalse(off.topProperties().getFirst().scoreBreakdown().containsKey("propertyTypeFit"));

        var on = service(values, true).recommend(request(2_000_000_000L, Purpose.LIVING));
        assertEquals("HEURISTIC_V1_1", on.method());
        var item = on.topProperties().getFirst();
        assertNotNull(item.amenityEvidence());
        assertNotNull(item.amenityEvidence().areaId());
        assertTrue(item.scoreBreakdown().containsKey("propertyTypeFit"));
        assertTrue(item.scoreBreakdown().containsKey("amenityFit"));
        assertNotNull(on.scoringWeights());
        assertNotNull(on.topAreas().getFirst().amenityScore());
    }

    @Test void rankingIsDeterministicAndDedupStillAppliesUnderV11() {
        var a = candidate("a", PropertyType.HOUSE, "1600000000", "80", "Hải Châu", null);
        var b = candidate("b", PropertyType.HOUSE, "1600000000", "80", "Hải Châu", null);
        var service = service(List.of(b, a), true);
        for (int i = 0; i < 5; i++) {
            assertEquals(List.of("a", "b"), service.recommend(request(2_000_000_000L, Purpose.LIVING))
                .topProperties().stream().map(PropertyResult::id).toList());
        }
        // Same duplicate group -> exactly one representative survives and votes once in the area.
        var shared = new Candidate("c", "c", PropertyType.HOUSE, new BigDecimal("1600000000"), new BigDecimal("80"),
            "Hải Châu", null, new Source("EXTERNAL", "fixture", "c", "https://example.invalid/c"),
            "VALID", "UNVERIFIED", "grp", true, false, List.of(), false);
        var twin = new Candidate("b2", "b2", PropertyType.HOUSE, new BigDecimal("1700000000"), new BigDecimal("82"),
            "Hải Châu", null, new Source("EXTERNAL", "fixture", "b2", "https://example.invalid/b2"),
            "VALID", "UNVERIFIED", "grp", true, false, List.of(), false);
        var result = service(List.of(shared, twin), true).recommend(request(2_000_000_000L, Purpose.LIVING));
        assertEquals(1, result.eligibleCandidateCount());
        assertEquals(1, result.topAreas().getFirst().candidateCount());
        // Deterministic representative = highest score, so the 1.6B row (exactly the 80% target) wins.
        assertEquals("c", result.topProperties().getFirst().id());
    }

    @Test void limitsAreEnforcedForPropertiesAndAreas() {
        var many = new ArrayList<Candidate>();
        for (int i = 0; i < 30; i++) many.add(candidate("p" + i, PropertyType.HOUSE, "1600000000", "80", "Hải Châu", null));
        var result = service(many, true).recommend(new Request(BigDecimal.valueOf(2_000_000_000L),
            Purpose.LIVING, PropertyType.ALL, null, null, null, 10));
        assertEquals(10, result.topProperties().size());
        assertTrue(result.topAreas().size() <= AreaScoringV11Service.MAX_AREAS);
    }

    @Test void protectedHoldoutAndRejectedRowsStayExcludedUnderV11() {
        var held = new Candidate("held", "held", PropertyType.HOUSE, new BigDecimal("1600000000"), new BigDecimal("80"),
            "Hải Châu", null, new Source("EXTERNAL", "fixture", "held", null), "VALID", "UNVERIFIED", null, false, true, List.of(), false);
        var rejected = new Candidate("rej", "rej", PropertyType.HOUSE, new BigDecimal("1600000000"), new BigDecimal("80"),
            "Hải Châu", null, new Source("EXTERNAL", "fixture", "rej", null), "REJECTED", "UNVERIFIED", null, false, false, List.of(), false);
        var groupHeld = new Candidate("gh", "gh", PropertyType.HOUSE, new BigDecimal("1600000000"), new BigDecimal("80"),
            "Hải Châu", null, new Source("EXTERNAL", "fixture", "gh", null), "VALID", "UNVERIFIED", "g1", true, false, List.of(), true);
        var result = service(List.of(held, rejected, groupHeld), true).recommend(request(2_000_000_000L, Purpose.LIVING));
        assertTrue(result.topProperties().isEmpty());
    }

    @Test void explanationsNeverClaimADistance() {
        var values = List.of(candidate("a", PropertyType.HOUSE, "1600000000", "80", "Ngũ Hành Sơn", "Mỹ An"));
        var result = service(values, true).recommend(request(2_000_000_000L, Purpose.LIVING));
        for (String text : result.topProperties().getFirst().explanations()) {
            assertFalse(text.matches(".*\\d+\\s*m\\b(?!²).*"), "must not claim a metre distance: " + text);
        }
        for (String limitation : result.topProperties().getFirst().amenityEvidence().dataLimitations()) {
            assertFalse(limitation.matches(".*cách\\s+\\d+.*"), "must not claim a distance: " + limitation);
        }
    }

    private HybridRecommendationService service(List<Candidate> candidates, boolean v11) {
        var repo = mock(RecommendationCandidateRepository.class);
        when(repo.find(any(), anyBoolean())).thenReturn(candidates);
        var v11Scorer = v11 ? scorer : null;
        var v11Areas = v11 ? new AreaScoringV11Service(resolver, evidence) : null;
        var v11Evidence = v11 ? evidence : null;
        return new HybridRecommendationService(repo, new PropertyScoringService(), new AreaScoringService(), true,
            v11Scorer, v11Areas, v11Evidence, resolver, v11);
    }
}