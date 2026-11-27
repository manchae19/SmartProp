package vn.smartprop.advisor;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
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
import org.mockito.ArgumentCaptor;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import vn.smartprop.advisor.AdvisorDtos.AdvisedProperty;
import vn.smartprop.advisor.AdvisorDtos.AdvisorRequest;
import vn.smartprop.advisor.AdvisorDtos.AdvisorResponse;
import vn.smartprop.common.ApiException;
import vn.smartprop.common.RequestLimits;
import vn.smartprop.comparable.ComparableEligibilityService;
import vn.smartprop.comparable.ComparableRankingService;
import vn.smartprop.modules.amenity.AmenityCatalogService;
import vn.smartprop.modules.auth.AccountAccess;
import vn.smartprop.modules.recommendation.AmenityEvidenceService;
import vn.smartprop.modules.recommendation.AreaScoringService;
import vn.smartprop.modules.recommendation.AreaScoringV11Service;
import vn.smartprop.modules.recommendation.HybridRecommendationService;
import vn.smartprop.modules.recommendation.PropertyLocationResolver;
import vn.smartprop.modules.recommendation.PropertyScoringService;
import vn.smartprop.modules.recommendation.PropertyScoringV11Service;
import vn.smartprop.modules.recommendation.RecommendationCandidateRepository;
import vn.smartprop.modules.recommendation.RecommendationController;
import vn.smartprop.modules.recommendation.RecommendationDtos;
import vn.smartprop.modules.recommendation.RecommendationDtos.AmenityPriority;
import vn.smartprop.modules.recommendation.RecommendationDtos.PropertyType;
import vn.smartprop.modules.recommendation.RecommendationDtos.Purpose;
import vn.smartprop.modules.recommendation.RecommendationDtos.Source;
import vn.smartprop.modules.recommendation.TinixCandidateRepository;
import vn.smartprop.modules.user.User;
import vn.smartprop.modules.user.UserRepository;

/**
 * PR #46 Finding 1 — Comprehensive regression matrix (Cases A through K) verifying
 * that Advisor SAFE mode and Public Recommendation strictly enforce public candidate
 * eligibility BEFORE retrieval caps, ranking, top-K slicing, area aggregation,
 * candidate counts, warnings, and nested evidence regardless of internal demo config.
 */
class AdvisorSafeCandidatePolicyTest {

    private final ComparableRankingService compService = mock(ComparableRankingService.class);
    private final ComparableEligibilityService compEligibility = new ComparableEligibilityService();
    private final AdvisorValuationAdapter valAdapter = mock(AdvisorValuationAdapter.class);
    private final UserRepository userRepo = mock(UserRepository.class);
    private final AccountAccess accountAccess = new AccountAccess(userRepo);
    private final RequestLimits limits = mock(RequestLimits.class);
    private final HttpServletRequest httpReq = mock(HttpServletRequest.class);
    private final ObjectMapper mapper = new ObjectMapper();

    @BeforeEach
    void setUp() {
        when(httpReq.getRemoteAddr()).thenReturn("127.0.0.1");
        when(userRepo.findById(10L)).thenReturn(Optional.of(activeUser(10L, User.Role.BUYER)));
        when(userRepo.findById(20L)).thenReturn(Optional.of(activeUser(20L, User.Role.BROKER)));
        when(userRepo.findById(30L)).thenReturn(Optional.of(activeUser(30L, User.Role.ADMIN)));
        when(valAdapter.probeSupportedLocations()).thenReturn(Map.of("Nhà ở", Set.of("Hải Châu", "Sơn Trà")));
    }

    private static User activeUser(Long id, User.Role role) {
        User u = new User();
        u.id = id;
        u.role = role;
        u.status = User.Status.ACTIVE;
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

    private static HybridRecommendationService newV11RecommendationService(
            RecommendationCandidateRepository repo, boolean demoEnabled, TinixCandidateRepository tinix, boolean tinixEnabled) {
        AmenityCatalogService catalog = new AmenityCatalogService(new ObjectMapper());
        AmenityEvidenceService evidence = new AmenityEvidenceService();
        PropertyLocationResolver resolver = new PropertyLocationResolver(catalog);
        PropertyScoringV11Service propV11 = new PropertyScoringV11Service(
            resolver,
            0.38, 0.17, 0.20, 0.25,
            0.45, 0.25, 0.20, 0.10,
            0.40, 0.20, 0.25, 0.15
        );
        AreaScoringV11Service areaV11 = new AreaScoringV11Service(resolver, evidence);

        HybridRecommendationService svc = new HybridRecommendationService(
            repo,
            new PropertyScoringService(),
            new AreaScoringService(),
            demoEnabled,
            staticProvider(propV11),
            staticProvider(areaV11),
            staticProvider(evidence),
            staticProvider(resolver),
            true
        );
        try {
            var m = HybridRecommendationService.class.getDeclaredMethod("configureTinix", TinixCandidateRepository.class, boolean.class);
            m.setAccessible(true);
            m.invoke(svc, tinix, tinixEnabled);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
        return svc;
    }

    private static <T> org.springframework.beans.factory.ObjectProvider<T> staticProvider(T bean) {
        return new org.springframework.beans.factory.ObjectProvider<>() {
            @Override public T getObject(Object... args) { return bean; }
            @Override public T getIfAvailable() { return bean; }
            @Override public T getIfUnique() { return bean; }
            @Override public T getObject() { return bean; }
        };
    }

    @SuppressWarnings("unchecked")
    private static <T> T newCandidate(
            String id, String title, PropertyType type, String price, String area,
            String district, String ward, Source source, String quality, String verification,
            String dupGroup, boolean duplicate, List<String> issues) {
        try {
            Class<?> cls = Class.forName("vn.smartprop.modules.recommendation.RecommendationDtos$Candidate");
            var ctor = cls.getDeclaredConstructors()[0];
            ctor.setAccessible(true);
            return (T) ctor.newInstance(
                id, title, type, new BigDecimal(price), new BigDecimal(area),
                district, ward, source, quality, verification, dupGroup, duplicate, false, issues, false
            );
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    private static AdvisorRequest safeConsult(int limit) {
        return new AdvisorRequest(
            new BigDecimal("5000000000"), 0, Purpose.LIVING, PropertyType.HOUSE,
            null, null, null, limit, false, false, false
        );
    }

    @Test
    @DisplayName("Cases A, B, C, D: Advisor SAFE with demo disabled & demo enabled across Anonymous, BUYER, BROKER, ADMIN only queries public cohort")
    void advisorSafeIgnoresInternalDemoFlagAcrossAllActors() throws Exception {
        RecommendationCandidateRepository repo = mock(RecommendationCandidateRepository.class);
        TinixCandidateRepository tinix = mock(TinixCandidateRepository.class);

        Object publicProp = newCandidate(
            "property:11111111-1111-4111-8111-111111111111", "Nhà phố Hải Châu công khai",
            PropertyType.HOUSE, "4800000000", "75", "Hải Châu", "Hòa Cường Bắc",
            new Source("PROPERTY", "SmartProp", "11111111-1111-4111-8111-111111111111", "/api/v1/properties/11111111-1111-4111-8111-111111111111"),
            "PLATFORM_PUBLISHED", "PLATFORM_PUBLISHED", null, false, List.of()
        );
        Object verifiedExt = newCandidate(
            "external:101", "Nhà phố Sơn Trà đã xác minh",
            PropertyType.HOUSE, "4300000000", "80", "Sơn Trà", null,
            new Source("EXTERNAL", "batdongsan", "ext-101", "https://example.com/101"),
            "VALID", "VERIFIED", "grp-101", false, List.of()
        );
        Object unverifiedDemo = newCandidate(
            "external:901", "Tin demo chưa xác minh",
            PropertyType.HOUSE, "3400000000", "90", "Ngũ Hành Sơn", null,
            new Source("EXTERNAL", "crawler", "ext-901", "https://example.com/901"),
            "VALID", "UNVERIFIED", "grp-901", false, List.of()
        );
        Object needsReviewDemo = newCandidate(
            "external:902", "Tin demo cần duyệt",
            PropertyType.HOUSE, "3500000000", "92", "Liên Chiểu", null,
            new Source("EXTERNAL", "crawler", "ext-902", "https://example.com/902"),
            "NEEDS_REVIEW", "UNVERIFIED", "grp-902", true, List.of("NEAR_DUPLICATE")
        );

        when(repo.find(any(), eq(false))).thenReturn((List) List.of(publicProp, verifiedExt));
        when(repo.find(any(), eq(true))).thenReturn((List) List.of(publicProp, verifiedExt, unverifiedDemo, needsReviewDemo));

        // Case A: demo=false
        HybridRecommendationService recDemoOff = newV11RecommendationService(repo, false, tinix, true);
        AdvisorOrchestrationService advDemoOff = new AdvisorOrchestrationService(recDemoOff, compService, compEligibility, valAdapter, false);
        AdvisorResponse resOff = advDemoOff.consult(safeConsult(5));
        assertThat(resOff.mode()).isEqualTo("SAFE");
        assertThat(resOff.recommendationMethod()).isEqualTo("HEURISTIC_V1_1");
        assertThat(resOff.eligibleCandidateCount()).isEqualTo(2);
        assertThat(resOff.recommendedProperties()).extracting(AdvisedProperty::id)
            .containsExactlyInAnyOrder("property:11111111-1111-4111-8111-111111111111", "external:101");

        // Cases B, C, D: demo=true across Anonymous, BUYER, BROKER, ADMIN
        HybridRecommendationService recDemoOn = newV11RecommendationService(repo, true, tinix, true);
        AdvisorOrchestrationService advDemoOn = new AdvisorOrchestrationService(recDemoOn, compService, compEligibility, valAdapter, true);
        AdvisorController controller = new AdvisorController(advDemoOn, accountAccess, limits);

        List<JwtAuthenticationToken> actors = java.util.Arrays.asList(
            null,
            jwtFor(10L, User.Role.BUYER),
            jwtFor(20L, User.Role.BROKER),
            jwtFor(30L, User.Role.ADMIN)
        );

        for (JwtAuthenticationToken actor : actors) {
            ResponseEntity<AdvisorResponse> entity = controller.consult(safeConsult(5), httpReq, actor);
            assertThat(entity.getStatusCode().value()).isEqualTo(200);
            AdvisorResponse body = entity.getBody();
            assertThat(body).isNotNull();
            assertThat(body.mode()).isEqualTo("SAFE");
            assertThat(body.eligibleCandidateCount()).isEqualTo(2);
            assertThat(body.recommendedProperties()).hasSize(2);
            assertThat(body.recommendedProperties()).allMatch(AdvisedProperty::liveListing);
            assertThat(body.topAreas()).extracting(RecommendationDtos.AreaResult::district)
                .containsExactlyInAnyOrder("Hải Châu", "Sơn Trà");
            assertThat(body.topAreas()).allMatch(a -> a.unverifiedCount() == 0 && a.needsReviewCount() == 0);
            String rawJson = mapper.writeValueAsString(body);
            assertThat(rawJson).doesNotContain("UNVERIFIED", "NEEDS_REVIEW", "INTERNAL_DEMO", "ext-901", "ext-902", "TINIX");
        }

        // Repository was NEVER called with demo=true or tinix.find()!
        verify(repo, never()).find(any(), eq(true));
        verify(repo, times(5)).find(any(), eq(false));
        verify(tinix, never()).find(any());
    }

    @Test
    @DisplayName("Cases E, F, H, I: Pre-ranking eligibility rejects higher-scoring UNVERIFIED & NEEDS_REVIEW before limit, counts, and area aggregation; SQL excludes demo before CAP")
    void preRankingEligibilityAndSqlCapIsolation() {
        // 1. Verify SQL in RecommendationCandidateRepository.findPublic(req) filters VALID + VERIFIED BEFORE LIMIT 10001
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.query(anyString(), any(RowMapper.class), any(), any(), any())).thenReturn(List.of());
        RecommendationCandidateRepository sqlRepo = new RecommendationCandidateRepository(jdbc, mapper);
        sqlRepo.findPublic(new RecommendationDtos.Request(
            new BigDecimal("5000000000"), Purpose.LIVING, PropertyType.HOUSE, null, "Hải Châu", null, 5
        ));
        ArgumentCaptor<String> sqlCaptor = ArgumentCaptor.forClass(String.class);
        verify(jdbc, times(2)).query(sqlCaptor.capture(), any(RowMapper.class), any(), any(), any());
        String externalSql = sqlCaptor.getAllValues().get(1);
        assertThat(externalSql).contains("l.quality_status='VALID' AND l.verification_status='VERIFIED'");
        assertThat(externalSql).doesNotContain("NEEDS_REVIEW", "UNVERIFIED");
        assertThat(externalSql.indexOf("l.verification_status='VERIFIED'"))
            .isLessThan(externalSql.indexOf("LIMIT 10001"));

        // 2. Even if a repository returns mixed candidates where UNVERIFIED and NEEDS_REVIEW outscore public on limit=1:
        RecommendationCandidateRepository mixedRepo = mock(RecommendationCandidateRepository.class);
        TinixCandidateRepository tinix = mock(TinixCandidateRepository.class);

        // Public property near ceiling (lower budgetFit score)
        Object lowerScoringPublic = newCandidate(
            "property:22222222-2222-4222-8222-222222222222", "Nhà phố Hải Châu sát trần",
            PropertyType.HOUSE, "4950000000", "60", "Hải Châu", "Phước Ninh",
            new Source("PROPERTY", "SmartProp", "22222222-2222-4222-8222-222222222222", "/api/v1/properties/22222222-2222-4222-8222-222222222222"),
            "PLATFORM_PUBLISHED", "PLATFORM_PUBLISHED", null, false, List.of()
        );
        // Demo candidates with much better price/area fit that would rank #1 and #2 if filtered post-ranking!
        Object highScoreUnverified = newCandidate(
            "external:701", "Tin UNVERIFIED điểm cao",
            PropertyType.HOUSE, "3200000000", "95", "Hải Châu", null,
            new Source("EXTERNAL", "crawler", "ext-701", "https://example.com/701"),
            "VALID", "UNVERIFIED", "grp-701", false, List.of()
        );
        Object highScoreNeedsReview = newCandidate(
            "external:702", "Tin NEEDS_REVIEW điểm cao",
            PropertyType.HOUSE, "3100000000", "100", "Sơn Trà", null,
            new Source("EXTERNAL", "crawler", "ext-702", "https://example.com/702"),
            "NEEDS_REVIEW", "VERIFIED", "grp-702", true, List.of("NEAR_DUPLICATE")
        );

        when(mixedRepo.find(any(), eq(false))).thenReturn((List) List.of(highScoreUnverified, highScoreNeedsReview, lowerScoringPublic));

        HybridRecommendationService recService = newV11RecommendationService(mixedRepo, true, tinix, true);
        AdvisorOrchestrationService advisor = new AdvisorOrchestrationService(recService, compService, compEligibility, valAdapter, false);

        // Request limit = 1: if filtering happened AFTER top-1 slicing, recommendedProperties would be EMPTY!
        AdvisorResponse res = advisor.consult(safeConsult(1));
        assertThat(res.mode()).isEqualTo("SAFE");
        assertThat(res.eligibleCandidateCount()).isEqualTo(1);
        assertThat(res.recommendedProperties()).hasSize(1);
        assertThat(res.recommendedProperties().get(0).id()).isEqualTo("property:22222222-2222-4222-8222-222222222222");
        assertThat(res.recommendedProperties().get(0).liveListing()).isTrue();

        // Area summary reflects ONLY the 1 public Hải Châu listing (average price = 4.95B, Sơn Trà absent!)
        assertThat(res.topAreas()).hasSize(1);
        assertThat(res.topAreas().get(0).district()).isEqualTo("Hải Châu");
        assertThat(res.topAreas().get(0).candidateCount()).isEqualTo(1);
        assertThat(res.topAreas().get(0).averageAskingPriceVnd()).isEqualByComparingTo("4950000000");
        assertThat(res.topAreas().get(0).unverifiedCount()).isZero();
        assertThat(res.topAreas().get(0).needsReviewCount()).isZero();
    }

    @Test
    @DisplayName("Case G: Empty public cohort never falls back to internal demo or TiniX research candidates")
    void emptyPublicCohortNeverFallsBackToDemoOrTinix() {
        RecommendationCandidateRepository repo = mock(RecommendationCandidateRepository.class);
        TinixCandidateRepository tinix = mock(TinixCandidateRepository.class);

        Object unverifiedDemo = newCandidate(
            "external:801", "Tin demo sẵn có",
            PropertyType.HOUSE, "3200000000", "85", "Hải Châu", null,
            new Source("EXTERNAL", "crawler", "ext-801", "https://example.com/801"),
            "VALID", "UNVERIFIED", "grp-801", false, List.of()
        );
        Object tinixRow = newCandidate(
            "tinix:tnx-01", "Quan sát nghiên cứu",
            PropertyType.HOUSE, "3100000000", "85", "Hải Châu", null,
            new Source("TINIX_AI", "TiniX AI", "tnx-01", null),
            "HYBRID_ELIGIBLE_RESEARCH", "UNVERIFIED", "grp-tnx-01", false, List.of()
        );

        when(repo.find(any(), eq(false))).thenReturn(List.of());
        when(repo.find(any(), eq(true))).thenReturn((List) List.of(unverifiedDemo));
        when(tinix.find(any())).thenReturn((List) List.of(tinixRow));

        HybridRecommendationService recService = newV11RecommendationService(repo, true, tinix, true);
        AdvisorOrchestrationService advisor = new AdvisorOrchestrationService(recService, compService, compEligibility, valAdapter, true);

        AdvisorResponse res = advisor.consult(safeConsult(5));
        assertThat(res.mode()).isEqualTo("SAFE");
        assertThat(res.eligibleCandidateCount()).isZero();
        assertThat(res.recommendedProperties()).isEmpty();
        assertThat(res.topAreas()).isEmpty();
        assertThat(res.warnings()).anyMatch(w -> w.startsWith("NO_ELIGIBLE_CANDIDATES:"));

        verify(repo).find(any(), eq(false));
        verify(repo, never()).find(any(), eq(true));
        verify(tinix, never()).find(any());
    }

    @Test
    @DisplayName("Cases J & K: Explicit internal demo contract and Public Recommendation / PR #45 RAG V1.1 + strict-area contract preserved")
    void internalDemoAndPublicRagRecommendationContractsPreserved() {
        RecommendationCandidateRepository repo = mock(RecommendationCandidateRepository.class);
        TinixCandidateRepository tinix = mock(TinixCandidateRepository.class);

        Object publicProp80 = newCandidate(
            "property:33333333-3333-4333-8333-333333333333", "Nhà phố Hải Châu 80m2",
            PropertyType.HOUSE, "4200000000", "80", "Hải Châu", "Hòa Cường Bắc",
            new Source("PROPERTY", "SmartProp", "33333333-3333-4333-8333-333333333333", "/api/v1/properties/33333333-3333-4333-8333-333333333333"),
            "PLATFORM_PUBLISHED", "PLATFORM_PUBLISHED", null, false, List.of()
        );
        Object publicExt95 = newCandidate(
            "external:202", "Nhà phố Hải Châu 95m2",
            PropertyType.HOUSE, "4500000000", "95", "Hải Châu", null,
            new Source("EXTERNAL", "batdongsan", "ext-202", "https://example.com/202"),
            "VALID", "VERIFIED", "grp-202", false, List.of()
        );
        Object unverifiedDemo = newCandidate(
            "external:905", "Nhà phố demo",
            PropertyType.HOUSE, "3900000000", "90", "Hải Châu", null,
            new Source("EXTERNAL", "crawler", "ext-905", "https://example.com/905"),
            "VALID", "UNVERIFIED", "grp-905", false, List.of()
        );

        when(repo.find(any(), eq(false))).thenReturn((List) List.of(publicProp80, publicExt95));
        when(repo.find(any(), eq(true))).thenReturn((List) List.of(publicProp80, publicExt95, unverifiedDemo));

        // Case K: Public Recommendation (demo=false, V1.1=true) called anonymously by RAG BackendTools
        HybridRecommendationService publicRecService = newV11RecommendationService(repo, false, tinix, false);
        RecommendationController publicController = new RecommendationController(publicRecService, "", accountAccess);

        // Strict minAreaExclusive=true (> 80 excludes 80m2, keeps 95m2!)
        RecommendationDtos.Request ragReq = new RecommendationDtos.Request(
            new BigDecimal("5000000000"), Purpose.LIVING, PropertyType.HOUSE,
            new BigDecimal("80"), new BigDecimal("120"), true, false,
            "Hải Châu", null, 5, List.of(AmenityPriority.SCHOOL)
        );
        ResponseEntity<RecommendationDtos.Response> pubRes = publicController.recommend(ragReq, httpReq, null);
        assertThat(pubRes.getStatusCode().value()).isEqualTo(200);
        assertThat(pubRes.getHeaders().getCacheControl()).isEqualTo("no-store");
        assertThat(pubRes.getBody()).isNotNull();
        assertThat(pubRes.getBody().method()).isEqualTo("HEURISTIC_V1_1");
        assertThat(pubRes.getBody().mode()).isEqualTo("SAFE");
        assertThat(pubRes.getBody().eligibleCandidateCount()).isEqualTo(1);
        assertThat(pubRes.getBody().topProperties()).hasSize(1);
        assertThat(pubRes.getBody().topProperties().get(0).id()).isEqualTo("external:202");
        assertThat(pubRes.getBody().scoringWeights()).containsEntry("budgetFit", 0.38);

        // Case J: Explicit Internal Demo (demo=true) requires loopback + active ADMIN + X-SmartProp-Demo-Key
        HybridRecommendationService demoRecService = newV11RecommendationService(repo, true, tinix, false);
        RecommendationController demoController = new RecommendationController(demoRecService, "secret-demo-key", accountAccess);

        // Anonymous rejected on internal demo
        assertThatThrownBy(() -> demoController.recommend(ragReq, httpReq, null))
            .isInstanceOf(ApiException.class)
            .extracting(e -> ((ApiException) e).status).isEqualTo(403);

        // Authorized loopback ADMIN + demo key succeeds with INTERNAL_DEMO
        when(httpReq.getHeader("X-SmartProp-Demo-Key")).thenReturn("secret-demo-key");
        ResponseEntity<RecommendationDtos.Response> demoRes = demoController.recommend(ragReq, httpReq, jwtFor(30L, User.Role.ADMIN));
        assertThat(demoRes.getStatusCode().value()).isEqualTo(200);
        assertThat(demoRes.getHeaders().getCacheControl()).contains("private").contains("no-store");
        assertThat(demoRes.getBody().mode()).isEqualTo("INTERNAL_DEMO");
        assertThat(demoRes.getBody().eligibleCandidateCount()).isEqualTo(2); // 95m2 + 90m2 demo (80m2 still excluded by >80!)
    }
}
