package vn.smartprop.advisor;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import vn.smartprop.advisor.AdvisorDtos.AdvisedProperty;
import vn.smartprop.advisor.AdvisorDtos.AdvisorRequest;
import vn.smartprop.advisor.AdvisorDtos.AdvisorResponse;
import vn.smartprop.advisor.AdvisorDtos.ValuationEvidence;
import vn.smartprop.common.ApiException;
import vn.smartprop.common.RequestLimits;
import vn.smartprop.comparable.ComparableCandidateRepository;
import vn.smartprop.comparable.ComparableCandidateRepository.ExternalRow;
import vn.smartprop.comparable.ComparableCandidateRepository.PropertyRow;
import vn.smartprop.comparable.ComparableCandidateRepository.TinixRow;
import vn.smartprop.comparable.ComparableEligibilityService;
import vn.smartprop.comparable.ComparableRankingService;
import vn.smartprop.modules.auth.AccountAccess;
import vn.smartprop.modules.property.Property;
import vn.smartprop.modules.property.PropertyRepository;
import vn.smartprop.modules.recommendation.HybridRecommendationService;
import vn.smartprop.modules.recommendation.RecommendationDtos;
import vn.smartprop.modules.recommendation.RecommendationDtos.AreaResult;
import vn.smartprop.modules.recommendation.RecommendationDtos.PropertyResult;
import vn.smartprop.modules.recommendation.RecommendationDtos.PropertyType;
import vn.smartprop.modules.recommendation.RecommendationDtos.Purpose;
import vn.smartprop.modules.recommendation.RecommendationDtos.Source;
import vn.smartprop.modules.user.User;
import vn.smartprop.modules.user.UserRepository;

/**
 * Phase 0 — WP02-F01 regression suite: verifies public/research isolation at
 * Controller, Orchestrator, ComparableRankingService, and ComparableCandidateRepository
 * boundaries using pure in-memory fixtures (0 MySQL connections).
 */
class AdvisorResearchAccessHardeningTest {

    private final HybridRecommendationService recService = mock(HybridRecommendationService.class);
    private final ComparableCandidateRepository compRepo = mock(ComparableCandidateRepository.class);
    private final ComparableEligibilityService compEligibility = new ComparableEligibilityService();
    private final PropertyRepository propertyRepo = mock(PropertyRepository.class);
    private final ComparableRankingService publicOnlyComparableService =
        new ComparableRankingService(compRepo, compEligibility, propertyRepo, false);
    private final ComparableRankingService researchEnabledComparableService =
        new ComparableRankingService(compRepo, compEligibility, propertyRepo, true);
    private final AdvisorValuationAdapter valAdapter = mock(AdvisorValuationAdapter.class);
    private final UserRepository userRepo = mock(UserRepository.class);
    private final AccountAccess accountAccess = new AccountAccess(userRepo);
    private final RequestLimits limits = mock(RequestLimits.class);
    private final HttpServletRequest httpReq = mock(HttpServletRequest.class);
    private final ObjectMapper json = new ObjectMapper();

    private static final String REF_UUID = "11111111-1111-4111-8111-111111111111";

    @BeforeEach
    void setUp() {
        when(httpReq.getRemoteAddr()).thenReturn("127.0.0.1");
        when(userRepo.findById(10L)).thenReturn(Optional.of(activeUser(10L, User.Role.BUYER)));
        when(userRepo.findById(20L)).thenReturn(Optional.of(activeUser(20L, User.Role.BROKER)));
        when(userRepo.findById(30L)).thenReturn(Optional.of(activeUser(30L, User.Role.ADMIN)));

        Property refEntity = new Property();
        refEntity.id = REF_UUID;
        refEntity.status = Property.Status.PUBLISHED;
        refEntity.transactionType = Property.Transaction.SALE;
        refEntity.priceUnit = Property.PriceUnit.TOTAL;
        refEntity.currency = "VND";
        refEntity.propertyType = Property.Type.HOUSE;
        refEntity.district = "Hải Châu";
        refEntity.ward = null;
        refEntity.areaSqm = new BigDecimal("80");
        refEntity.price = new BigDecimal("4700000000");
        refEntity.bedrooms = 3;
        when(propertyRepo.findByIdAndDeletedAtIsNull(REF_UUID)).thenReturn(Optional.of(refEntity));

        when(valAdapter.probeSupportedLocations()).thenReturn(Map.of("Nhà ở", Set.of("Hải Châu")));
        when(valAdapter.evaluate(any(), any(), any(), any(), any(), any(), any(), any())).thenReturn(
            new ValuationEvidence("AVAILABLE", true, null, "v1.3", "tinix_xgboost_v1_3_integrated",
                new BigDecimal("4900000000"), new BigDecimal("-4.1"), "ASKING_SALE_VND_TOTAL",
                Map.of("areaSqm", 80.0), List.of(), null, List.of())
        );

        // Populate research repository with attractive TiniX rows that MUST NOT be queried in SAFE mode
        when(compRepo.tinixCandidates(any(), anyInt())).thenReturn(List.of(
            new TinixRow("tnx-leak-01", "HOUSE", "Hải Châu", "Hòa Cường Bắc",
                new BigDecimal("80"), new BigDecimal("4600000000"),
                new BigDecimal("3"), new BigDecimal("5"), new BigDecimal("3"), new BigDecimal("6"), "grp-1")
        ));
        when(compRepo.eligibleCounts()).thenReturn(Map.of("SMARTPROP", 2, "EXTERNAL_LISTING", 5, "TINIX_RESEARCH", 55816));
        when(compRepo.publicEligibleCounts()).thenReturn(Map.of("SMARTPROP", 2, "EXTERNAL_LISTING", 5));
    }

    private static User activeUser(Long id, User.Role role) {
        User u = new User();
        u.id = id;
        u.role = role;
        u.status = User.Status.ACTIVE;
        u.deletedAt = null;
        u.tokenVersion = 1;
        return u;
    }

    private static JwtAuthenticationToken jwtFor(Long id, User.Role role) {
        Jwt jwt = Jwt.withTokenValue("tok-" + id)
            .header("alg", "HS256")
            .subject(String.valueOf(id))
            .claim("ver", 1)
            .issuedAt(Instant.now())
            .expiresAt(Instant.now().plusSeconds(900))
            .build();
        return new JwtAuthenticationToken(jwt, List.of(new SimpleGrantedAuthority("ROLE_" + role.name())));
    }

    private static PropertyResult publicProperty() {
        return new PropertyResult(
            "prop:" + REF_UUID,
            "Nhà phố Hòa Cường Bắc",
            PropertyType.HOUSE,
            new BigDecimal("4700000000"),
            new BigDecimal("80"),
            "Hải Châu",
            "Hòa Cường Bắc",
            86.0,
            Map.of("budgetFit", 88.0),
            List.of("Phù hợp nhu cầu ở thực"),
            new Source("PROPERTY", "SmartProp", REF_UUID, null),
            "PLATFORM_PUBLISHED",
            "VERIFIED",
            null,
            List.of(),
            null
        );
    }

    private static AdvisorRequest consultReq(Boolean includeResearch) {
        return new AdvisorRequest(
            new BigDecimal("5000000000"), 0, Purpose.LIVING, PropertyType.HOUSE,
            null, "Hải Châu", null, 5, true, true, includeResearch
        );
    }

    private void stubPublicRecommendationWithData() {
        when(recService.recommendPublic(any())).thenReturn(new RecommendationDtos.Response(
            "HEURISTIC_V1_1", "SAFE", "ASKING_SALE_VND_TOTAL",
            new RecommendationDtos.Request(new BigDecimal("5000000000"), Purpose.LIVING, PropertyType.HOUSE, null, "Hải Châu", null, 5),
            1,
            List.of(new AreaResult("Hải Châu", "Hòa Cường Bắc", 1, 86.0, new BigDecimal("4700000000"),
                List.of("SmartProp"), 1, 0, List.of("Trung tâm"), List.of())),
            List.of(publicProperty()),
            List.of("HEURISTIC_V1_1: weighted"),
            Map.of("budgetFit", 0.38)
        ));
    }

    @Test
    @DisplayName("SAFE mode (Anonymous, BUYER, BROKER, ADMIN) never queries TiniX repository or leaks research metadata while keeping V1.3 active")
    void safeModeIsolatesAllActorsFromResearchRepository() throws Exception {
        stubPublicRecommendationWithData();
        when(recService.tinixEnabled()).thenReturn(true);
        when(compRepo.propertyCandidates(any(), anyInt())).thenReturn(List.of(
            new PropertyRow("hc-200", "HOUSE", "Hải Châu", "Hòa Cường Bắc", new BigDecimal("82"), new BigDecimal("4650000000"), 3)
        ));
        when(compRepo.externalCandidates(any(), anyString(), anyInt())).thenReturn(List.of(
            new ExternalRow(501L, "CHOTOT", "Nhà ở", "Hải Châu", new BigDecimal("79"), new BigDecimal("4550000000"), "VALID", "https://chotot.com/501", "501", null)
        ));

        // Even if allowResearchComparables=true AND comparable researchEnabled=true, SAFE mode MUST still exclude TiniX!
        AdvisorOrchestrationService orchestrator = new AdvisorOrchestrationService(
            recService, researchEnabledComparableService, compEligibility, valAdapter, true);
        AdvisorController controller = new AdvisorController(orchestrator, accountAccess, limits);

        List<JwtAuthenticationToken> actors = java.util.Arrays.asList(
            null, // Anonymous
            jwtFor(10L, User.Role.BUYER), // Authenticated ordinary user
            jwtFor(20L, User.Role.BROKER), // BROKER
            jwtFor(30L, User.Role.ADMIN)   // ADMIN in SAFE mode (includeResearch=false)
        );

        for (JwtAuthenticationToken auth : actors) {
            ResponseEntity<AdvisorResponse> entity = controller.consult(consultReq(false), httpReq, auth);
            assertThat(entity.getStatusCode().value()).isEqualTo(200);
            assertThat(entity.getHeaders().getCacheControl()).isEqualTo("no-store");
            AdvisorResponse body = entity.getBody();
            assertThat(body).isNotNull();
            assertThat(body.mode()).isEqualTo("SAFE");
            assertThat(body.recommendedProperties()).hasSize(1);

            AdvisedProperty prop = body.recommendedProperties().get(0);
            // V1.3 valuation remains active and untouched
            assertThat(prop.valuationEvidence().available()).isTrue();
            assertThat(prop.valuationEvidence().modelVersion()).isEqualTo("v1.3");
            assertThat(prop.valuationEvidence().predictedAskingPriceVnd()).isEqualByComparingTo("4900000000");

            // Only public comparables returned
            assertThat(prop.comparableEvidence().comparables())
                .extracting(AdvisorDtos.ComparableItem::sourceKind)
                .containsExactlyInAnyOrder("SMARTPROP", "EXTERNAL_LISTING");

            String serialized = json.writeValueAsString(body);
            assertThat(serialized).doesNotContain("TINIX_RESEARCH", "TINIX_AI", "tnx-leak-01", "CC BY-NC", "RESEARCH_COMPARABLES_LABEL");
        }

        // Strict repository isolation proof: ZERO TiniX SQL calls across all 4 actors!
        verify(compRepo, never()).tinixCandidates(any(), anyInt());
        verify(compRepo, never()).eligibleCounts();
        verify(recService, never()).recommend(any());
        verify(recService, never()).recommendResearch(any());
    }

    @Test
    @DisplayName("SAFE mode does NOT fallback to TiniX research rows when public comparable cohort is completely empty")
    void safeModeNeverFallsBackToResearchWhenPublicCohortEmpty() throws Exception {
        stubPublicRecommendationWithData();
        when(recService.tinixEnabled()).thenReturn(true);
        // Public repositories are completely empty (0 rows), while TiniX has matching rows stubbed in setUp()
        when(compRepo.propertyCandidates(any(), anyInt())).thenReturn(List.of());
        when(compRepo.externalCandidates(any(), anyString(), anyInt())).thenReturn(List.of());

        AdvisorOrchestrationService orchestrator = new AdvisorOrchestrationService(
            recService, researchEnabledComparableService, compEligibility, valAdapter, true);
        AdvisorController controller = new AdvisorController(orchestrator, accountAccess, limits);

        AdvisorResponse res = controller.consult(consultReq(null), httpReq, null).getBody();
        assertThat(res).isNotNull();
        AdvisedProperty prop = res.recommendedProperties().get(0);
        assertThat(prop.comparableEvidence().status()).isEqualTo("EMPTY_NO_MATCHES");
        assertThat(prop.comparableEvidence().candidateCount()).isZero();
        assertThat(prop.comparableEvidence().comparables()).isEmpty();

        // Neither primary pass nor wide [0.1x, 10x] fallback pass touched TiniX!
        verify(compRepo, never()).tinixCandidates(any(), anyInt());
        verify(compRepo, never()).eligibleCounts();
    }

    @Test
    @DisplayName("Unauthorized research mode fails closed (403/401) for Anonymous, BUYER, BROKER, and unknown subject without touching repositories")
    void unauthorizedResearchModeFailsClosed() {
        when(recService.tinixEnabled()).thenReturn(true);
        AdvisorOrchestrationService orchestrator = new AdvisorOrchestrationService(
            recService, researchEnabledComparableService, compEligibility, valAdapter, true);
        AdvisorController controller = new AdvisorController(orchestrator, accountAccess, limits);

        // Anonymous -> 403
        assertThatThrownBy(() -> controller.consult(consultReq(true), httpReq, null))
            .isInstanceOf(ApiException.class)
            .extracting(e -> ((ApiException) e).status)
            .isEqualTo(403);

        // Ordinary user (BUYER) -> 403
        assertThatThrownBy(() -> controller.consult(consultReq(true), httpReq, jwtFor(10L, User.Role.BUYER)))
            .isInstanceOf(ApiException.class)
            .extracting(e -> ((ApiException) e).status)
            .isEqualTo(403);

        // BROKER -> 403
        assertThatThrownBy(() -> controller.consult(consultReq(true), httpReq, jwtFor(20L, User.Role.BROKER)))
            .isInstanceOf(ApiException.class)
            .extracting(e -> ((ApiException) e).status)
            .isEqualTo(403);

        // Missing/deleted user -> 401
        when(userRepo.findById(999L)).thenReturn(Optional.empty());
        assertThatThrownBy(() -> controller.consult(consultReq(true), httpReq, jwtFor(999L, User.Role.ADMIN)))
            .isInstanceOf(ApiException.class)
            .extracting(e -> ((ApiException) e).status)
            .isEqualTo(401);

        verifyNoInteractions(recService, compRepo, valAdapter);
    }

    @Test
    @DisplayName("Research mode fails closed (403) even for ADMIN when research flag is disabled at controller or service layer")
    void researchModeWhenDisabledFailsClosedForAdmin() {
        when(recService.tinixEnabled()).thenReturn(false);
        AdvisorOrchestrationService orchestrator = new AdvisorOrchestrationService(
            recService, researchEnabledComparableService, compEligibility, valAdapter, true);
        AdvisorController controller = new AdvisorController(orchestrator, accountAccess, limits);

        assertThatThrownBy(() -> controller.consult(consultReq(true), httpReq, jwtFor(30L, User.Role.ADMIN)))
            .isInstanceOf(ApiException.class)
            .extracting(e -> ((ApiException) e).status)
            .isEqualTo(403);

        assertThatThrownBy(() -> orchestrator.consult(consultReq(true)))
            .isInstanceOf(ApiException.class)
            .extracting(e -> ((ApiException) e).status)
            .isEqualTo(403);

        verify(recService, never()).recommendResearch(any());
        verifyNoInteractions(compRepo, valAdapter);
    }

    @Test
    @DisplayName("Authorized ADMIN research mode respects allow-research-comparables gate (off by default, labelled when explicitly enabled)")
    void authorizedAdminResearchModeRespectsComparableGate() {
        when(recService.tinixEnabled()).thenReturn(true);
        when(recService.recommendResearch(any())).thenReturn(new RecommendationDtos.Response(
            "HEURISTIC_V1_1", "INTERNAL_DEMO", "ASKING_SALE_VND_TOTAL",
            new RecommendationDtos.Request(new BigDecimal("5000000000"), Purpose.LIVING, PropertyType.HOUSE, null, "Hải Châu", null, 5),
            1, List.of(), List.of(publicProperty()), List.of(), Map.of()
        ));
        when(compRepo.propertyCandidates(any(), anyInt())).thenReturn(List.of());
        when(compRepo.externalCandidates(any(), anyString(), anyInt())).thenReturn(List.of());

        // Case A: default allowResearchComparables = false -> comparables stay public-only even in INTERNAL_RESEARCH mode
        AdvisorOrchestrationService defaultOrchestrator = new AdvisorOrchestrationService(
            recService, researchEnabledComparableService, compEligibility, valAdapter, false);
        AdvisorController defaultController = new AdvisorController(defaultOrchestrator, accountAccess, limits);

        ResponseEntity<AdvisorResponse> entityDefault = defaultController.consult(consultReq(true), httpReq, jwtFor(30L, User.Role.ADMIN));
        assertThat(entityDefault.getHeaders().getCacheControl()).contains("private").contains("no-store");
        AdvisorResponse resDefault = entityDefault.getBody();
        assertThat(resDefault).isNotNull();
        assertThat(resDefault.mode()).isEqualTo("INTERNAL_RESEARCH");
        assertThat(resDefault.recommendedProperties().get(0).comparableEvidence().comparables()).isEmpty();
        verify(compRepo, never()).tinixCandidates(any(), anyInt());

        // Case B: allowResearchComparables = true while comparable.research-enabled = false -> clean public fallback (no DEGRADED crash!)
        AdvisorOrchestrationService unalignedOrchestrator = new AdvisorOrchestrationService(
            recService, publicOnlyComparableService, compEligibility, valAdapter, true);
        AdvisorController unalignedController = new AdvisorController(unalignedOrchestrator, accountAccess, limits);

        AdvisorResponse resUnaligned = unalignedController.consult(consultReq(true), httpReq, jwtFor(30L, User.Role.ADMIN)).getBody();
        assertThat(resUnaligned).isNotNull();
        assertThat(resUnaligned.serviceStatus().comparableService()).isEqualTo("AVAILABLE");
        assertThat(resUnaligned.recommendedProperties().get(0).comparableEvidence().status()).isEqualTo("EMPTY_NO_MATCHES");
        verify(compRepo, never()).tinixCandidates(any(), anyInt());

        // Case C: both allowResearchComparables = true AND comparable.research-enabled = true -> ADMIN receives labelled TiniX comparable
        AdvisorOrchestrationService explicitOrchestrator = new AdvisorOrchestrationService(
            recService, researchEnabledComparableService, compEligibility, valAdapter, true);
        AdvisorController explicitController = new AdvisorController(explicitOrchestrator, accountAccess, limits);

        AdvisorResponse resExplicit = explicitController.consult(consultReq(true), httpReq, jwtFor(30L, User.Role.ADMIN)).getBody();
        assertThat(resExplicit).isNotNull();
        assertThat(resExplicit.recommendedProperties().get(0).comparableEvidence().comparables()).hasSize(1);
        var comp = resExplicit.recommendedProperties().get(0).comparableEvidence().comparables().get(0);
        assertThat(comp.candidateId()).isEqualTo("tinix:tnx-leak-01");
        assertThat(comp.researchReference()).isTrue();
        assertThat(comp.liveListing()).isFalse();
        assertThat(comp.listingUrl()).isNull();
        assertThat(comp.datasetLicense()).isEqualTo("CC BY-NC 4.0");
        assertThat(resExplicit.warnings()).anyMatch(w -> w.startsWith("RESEARCH_COMPARABLES_LABEL:"));
    }
}
