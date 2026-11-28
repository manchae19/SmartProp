package vn.smartprop.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.math.BigDecimal;
import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import vn.smartprop.advisor.AdvisorController;
import vn.smartprop.advisor.AdvisorDtos;
import vn.smartprop.advisor.AdvisorOrchestrationService;
import vn.smartprop.common.Errors;
import vn.smartprop.common.RequestLimits;
import vn.smartprop.comparable.ComparableController;
import vn.smartprop.comparable.ComparableDtos;
import vn.smartprop.comparable.ComparableRankingService;
import vn.smartprop.market.MarketAnalyticsController;
import vn.smartprop.market.MarketAnalyticsService;
import vn.smartprop.market.MarketDtos;
import vn.smartprop.modules.amenity.AmenityCatalogService;
import vn.smartprop.modules.amenity.AmenityDtos;
import vn.smartprop.modules.amenity.ResearchAmenityController;
import vn.smartprop.modules.auth.AccountAccess;
import vn.smartprop.modules.auth.AuthSession;
import vn.smartprop.modules.auth.SessionPolicy;
import vn.smartprop.modules.auth.SessionRepository;
import vn.smartprop.modules.recommendation.HybridRecommendationService;
import vn.smartprop.modules.recommendation.RecommendationController;
import vn.smartprop.modules.recommendation.RecommendationDtos;
import vn.smartprop.modules.user.User;
import vn.smartprop.modules.user.UserRepository;

/**
 * Real Spring Security FilterChain + NimbusJwtEncoder/Decoder + SessionActivityFilter
 * integration test across all 5 research-capable controllers (0 MySQL connections).
 */
@WebMvcTest(controllers = {
    AdvisorController.class,
    MarketAnalyticsController.class,
    ComparableController.class,
    RecommendationController.class,
    ResearchAmenityController.class
})
@Import({
    SecurityConfig.class,
    Errors.class,
    AccountAccess.class,
    SessionPolicy.class,
    ResearchAccessHttpSecurityTest.SecurityTestBeans.class
})
@TestPropertySource(properties = {
    "app.jwt-secret=phase0-test-secret-with-at-least-32-utf8-bytes!!",
    "app.cors-origins=http://localhost:5173",
    "app.refresh.enabled=false",
    "app.recommendation.demo-key=test-demo-key-secret"
})
class ResearchAccessHttpSecurityTest {

    @TestConfiguration
    static class SecurityTestBeans {
        @Bean Clock clock() { return Clock.systemUTC(); }
        @Bean LoginThrottle loginThrottle(ObjectMapper mapper) { return new LoginThrottle(mapper); }
        @Bean RequestLimits requestLimits() { return new RequestLimits(); }
    }

    @Autowired MockMvc mvc;
    @Autowired JwtEncoder jwtEncoder;

    @MockitoBean UserRepository users;
    @MockitoBean SessionRepository sessions;
    @MockitoBean AdvisorOrchestrationService advisorService;
    @MockitoBean MarketAnalyticsService marketService;
    @MockitoBean ComparableRankingService comparableService;
    @MockitoBean HybridRecommendationService recommendationService;
    @MockitoBean AmenityCatalogService amenityCatalog;

    private String buyerToken;
    private String brokerToken;
    private String adminToken;
    private String suspendedAdminToken;
    private String deletedAdminToken;
    private String revokedAdminToken;

    @BeforeEach
    void setUp() {
        buyerToken = registerSessionAndMintToken(101L, User.Role.BUYER, User.Status.ACTIVE, null, false, 1);
        brokerToken = registerSessionAndMintToken(102L, User.Role.BROKER, User.Status.ACTIVE, null, false, 1);
        adminToken = registerSessionAndMintToken(103L, User.Role.ADMIN, User.Status.ACTIVE, null, false, 1);
        suspendedAdminToken = registerSessionAndMintToken(104L, User.Role.ADMIN, User.Status.LOCKED, null, false, 1);
        deletedAdminToken = registerSessionAndMintToken(105L, User.Role.ADMIN, User.Status.ACTIVE, Instant.now(), false, 1);
        revokedAdminToken = registerSessionAndMintToken(106L, User.Role.ADMIN, User.Status.ACTIVE, null, true, 1);
    }

    private String registerSessionAndMintToken(
            Long userId, User.Role role, User.Status status, Instant deletedAt, boolean revoked, int ver) {
        User u = new User();
        u.id = userId;
        u.role = role;
        u.status = status;
        u.deletedAt = deletedAt;
        u.tokenVersion = ver;
        when(users.findById(userId)).thenReturn(Optional.of(u));

        String sid = UUID.randomUUID().toString();
        AuthSession s = new AuthSession();
        s.id = sid;
        s.userId = userId;
        s.createdAt = Instant.now().minusSeconds(60);
        s.lastUsedAt = Instant.now().minusSeconds(10);
        s.expiresAt = Instant.now().plusSeconds(3600);
        s.revoked = revoked;
        when(sessions.findById(sid)).thenReturn(Optional.of(s));

        JwsHeader header = JwsHeader.with(MacAlgorithm.HS256).build();
        JwtClaimsSet claims = JwtClaimsSet.builder()
            .issuer("smartprop")
            .id(sid)
            .subject(String.valueOf(userId))
            .claim("ver", ver)
            .issuedAt(Instant.now().minusSeconds(5))
            .expiresAt(Instant.now().plusSeconds(900))
            .build();
        return jwtEncoder.encode(JwtEncoderParameters.from(header, claims)).getTokenValue();
    }

    private static final String ADVISOR_SAFE_BODY = """
        {"budgetVnd":4000000000,"purpose":"LIVING","propertyType":"HOUSE","includeResearch":false}
        """;
    private static final String ADVISOR_RESEARCH_BODY = """
        {"budgetVnd":4000000000,"purpose":"LIVING","propertyType":"HOUSE","includeResearch":true}
        """;
    private static final String COMPARABLE_BODY = """
        {"propertyType":"HOUSE","district":"Hải Châu","areaSqm":80,"priceVnd":5000000000}
        """;

    @Test
    @DisplayName("Invalid, forged, revoked, suspended, and soft-deleted JWTs are rejected (401) across all research & protected routes")
    void invalidSuspendedDeletedAndRevokedTokensRejectedByRealSecurityChain() throws Exception {
        for (String badToken : List.of("forged.jwt.token", suspendedAdminToken, deletedAdminToken, revokedAdminToken)) {
            mvc.perform(post("/api/v1/properties/comparables")
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + badToken)
                    .contentType(MediaType.APPLICATION_JSON).content(COMPARABLE_BODY))
                .andExpect(status().isUnauthorized());

            mvc.perform(post("/api/v1/advisor/consult")
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + badToken)
                    .contentType(MediaType.APPLICATION_JSON).content(ADVISOR_RESEARCH_BODY))
                .andExpect(status().isUnauthorized());

            mvc.perform(get("/api/v1/properties/market-analytics?includeResearch=true")
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + badToken))
                .andExpect(status().isUnauthorized());

            mvc.perform(post("/api/v1/recommendations/research")
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + badToken)
                    .header("X-SmartProp-Demo-Key", "test-demo-key-secret")
                    .contentType(MediaType.APPLICATION_JSON)
                    .content("{\"budgetVnd\":3000000000,\"purpose\":\"LIVING\",\"propertyType\":\"HOUSE\"}"))
                .andExpect(status().isUnauthorized());
        }

        verify(comparableService, never()).rank(any());
        verify(comparableService, never()).rankResearch(any());
        verify(marketService, never()).analyticsResearch(any(), any(), any(), any(), any());
        verify(advisorService, never()).consult(any());
    }

    @Test
    void brokerCanSendExplicitComparablePurposeWithAdditiveFields() throws Exception {
        when(comparableService.rank(any())).thenReturn(new ComparableDtos.Response(
            new ComparableDtos.Reference(null, "HOUSE", "Hải Châu", null, new BigDecimal("80"), null, null, null),
            0, "NONE", List.of(), List.of(), Map.of("SMARTPROP", 0, "EXTERNAL_LISTING", 0)));
        mvc.perform(post("/api/v1/properties/comparables")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + brokerToken)
                .contentType(MediaType.APPLICATION_JSON).content("""
                    {"propertyType":"HOUSE","district":"Hải Châu","areaSqm":80,
                     "purpose":"BUYER_BUDGET_SEARCH","buyerBudgetVnd":3000000000,
                     "subjectIdentity":{"externalId":42}}
                    """))
            .andExpect(status().isOk())
            .andExpect(header().string("Cache-Control", "private, no-store"))
            .andExpect(jsonPath("$.comparables").isArray())
            .andExpect(jsonPath("$.reference.propertyType").value("HOUSE"))
            .andExpect(jsonPath("$.eligibleCountsBySource.TINIX_RESEARCH").doesNotExist());
        var captured = org.mockito.ArgumentCaptor.forClass(ComparableDtos.Request.class);
        verify(comparableService).rank(captured.capture());
        var request = captured.getValue();
        assertThat(request.purpose()).isEqualTo(ComparableDtos.Purpose.BUYER_BUDGET_SEARCH);
        assertThat(request.buyerBudgetVnd()).isEqualByComparingTo("3000000000");
        assertThat(request.subjectIdentity().externalId()).isEqualTo(42L);
        verify(comparableService, never()).rankResearch(any());
    }

    @Test
    @DisplayName("Anonymous, BUYER, and BROKER actors are blocked from every research endpoint while BROKER retains public Comparable")
    void roleIsolationThroughRealSecurityChain() throws Exception {
        ComparableDtos.Response publicCompRes = new ComparableDtos.Response(
            new ComparableDtos.Reference(null, "HOUSE", "Hải Châu", null, new BigDecimal("80"), new BigDecimal("5000000000"), null, null),
            0, "NONE", List.of(), List.of(), Map.of("SMARTPROP", 2, "EXTERNAL_LISTING", 5)
        );
        when(comparableService.rank(any())).thenReturn(publicCompRes);
        when(comparableService.isResearchEnabled()).thenReturn(true);
        when(marketService.isResearchEnabled()).thenReturn(true);
        when(advisorService.isResearchEnabled()).thenReturn(true);

        // Anonymous: Comparable -> 401; Market/Advisor research -> 403; Recommendation/Amenity research -> 401
        mvc.perform(post("/api/v1/properties/comparables")
                .contentType(MediaType.APPLICATION_JSON).content(COMPARABLE_BODY))
            .andExpect(status().isUnauthorized());
        mvc.perform(get("/api/v1/properties/market-analytics?includeResearch=true"))
            .andExpect(status().isForbidden());
        mvc.perform(get("/api/v1/properties/market-analytics?source=TINIX_RESEARCH"))
            .andExpect(status().isForbidden());
        mvc.perform(post("/api/v1/advisor/consult")
                .contentType(MediaType.APPLICATION_JSON).content(ADVISOR_RESEARCH_BODY))
            .andExpect(status().isForbidden());
        mvc.perform(get("/api/v1/amenities/research/hai-chau"))
            .andExpect(status().isUnauthorized());

        // BUYER: Comparable -> 403; Market/Advisor/Recommendation/Amenity research -> 403
        mvc.perform(post("/api/v1/properties/comparables")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + buyerToken)
                .contentType(MediaType.APPLICATION_JSON).content(COMPARABLE_BODY))
            .andExpect(status().isForbidden());
        mvc.perform(get("/api/v1/properties/market-analytics?includeResearch=true")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + buyerToken))
            .andExpect(status().isForbidden());
        mvc.perform(post("/api/v1/advisor/consult")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + buyerToken)
                .contentType(MediaType.APPLICATION_JSON).content(ADVISOR_RESEARCH_BODY))
            .andExpect(status().isForbidden());
        mvc.perform(get("/api/v1/amenities/research/hai-chau")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + buyerToken))
            .andExpect(status().isForbidden());

        // BROKER: Public Comparable -> 200 OK; Comparable/Market/Advisor/Recommendation/Amenity research -> 403
        mvc.perform(post("/api/v1/properties/comparables")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + brokerToken)
                .contentType(MediaType.APPLICATION_JSON).content(COMPARABLE_BODY))
            .andExpect(status().isOk())
            .andExpect(header().string("Cache-Control", "private, no-store"));

        mvc.perform(post("/api/v1/properties/comparables?includeResearch=true")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + brokerToken)
                .contentType(MediaType.APPLICATION_JSON).content(COMPARABLE_BODY))
            .andExpect(status().isForbidden());
        mvc.perform(get("/api/v1/properties/market-analytics?includeResearch=true")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + brokerToken))
            .andExpect(status().isForbidden());
        mvc.perform(post("/api/v1/advisor/consult")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + brokerToken)
                .contentType(MediaType.APPLICATION_JSON).content(ADVISOR_RESEARCH_BODY))
            .andExpect(status().isForbidden());
        mvc.perform(post("/api/v1/recommendations/research")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + brokerToken)
                .header("X-SmartProp-Demo-Key", "test-demo-key-secret")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"budgetVnd\":3000000000,\"purpose\":\"LIVING\",\"propertyType\":\"HOUSE\"}"))
            .andExpect(status().isForbidden());

        verify(comparableService, never()).rankResearch(any());
        verify(marketService, never()).analyticsResearch(any(), any(), any(), any(), any());
    }

    @Test
    @DisplayName("Active ADMIN requires explicit research request + server enablement and receives Cache-Control: private, no-store")
    void activeAdminExplicitResearchAndCacheHeadersVerified() throws Exception {
        ComparableDtos.Response publicCompRes = new ComparableDtos.Response(
            new ComparableDtos.Reference(null, "HOUSE", "Hải Châu", null, new BigDecimal("80"), new BigDecimal("5000000000"), null, null),
            0, "NONE", List.of(), List.of(), Map.of("SMARTPROP", 2, "EXTERNAL_LISTING", 5)
        );
        when(comparableService.rank(any())).thenReturn(publicCompRes);
        when(comparableService.rankResearch(any())).thenReturn(publicCompRes);

        // 1. Default ADMIN Comparable call -> public rank(), NOT rankResearch()
        mvc.perform(post("/api/v1/properties/comparables")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + adminToken)
                .contentType(MediaType.APPLICATION_JSON).content(COMPARABLE_BODY))
            .andExpect(status().isOk())
            .andExpect(header().string("Cache-Control", "private, no-store"));
        verify(comparableService, never()).rankResearch(any());

        // 2. ADMIN explicit research when disabled -> 403
        when(comparableService.isResearchEnabled()).thenReturn(false);
        mvc.perform(post("/api/v1/properties/comparables?includeResearch=true")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + adminToken)
                .contentType(MediaType.APPLICATION_JSON).content(COMPARABLE_BODY))
            .andExpect(status().isForbidden());

        // 3. ADMIN explicit research when enabled -> 200 + Cache-Control: private, no-store across all endpoints
        when(comparableService.isResearchEnabled()).thenReturn(true);
        mvc.perform(post("/api/v1/properties/comparables?includeResearch=true")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + adminToken)
                .contentType(MediaType.APPLICATION_JSON).content(COMPARABLE_BODY))
            .andExpect(status().isOk())
            .andExpect(header().string("Cache-Control", "private, no-store"));

        AdvisorDtos.AdvisorResponse safeAdv = new AdvisorDtos.AdvisorResponse(
            "ADVISOR_ORCHESTRATOR_V1", "SAFE", "HEURISTIC_V1", "ASKING_SALE_VND_TOTAL", "disc",
            null, new AdvisorDtos.ServiceStatus("AVAILABLE", "AVAILABLE", "AVAILABLE", "SKIPPED", false),
            0, Map.of(), List.of(), List.of(), List.of(), List.of()
        );
        when(advisorService.isResearchEnabled()).thenReturn(true);
        when(advisorService.consult(any())).thenReturn(safeAdv);

        // Advisor SAFE -> no-store; Advisor Research -> private, no-store
        mvc.perform(post("/api/v1/advisor/consult")
                .contentType(MediaType.APPLICATION_JSON).content(ADVISOR_SAFE_BODY))
            .andExpect(status().isOk())
            .andExpect(header().string("Cache-Control", "no-store"));

        String advResearchCache = mvc.perform(post("/api/v1/advisor/consult")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + adminToken)
                .contentType(MediaType.APPLICATION_JSON).content(ADVISOR_RESEARCH_BODY))
            .andExpect(status().isOk())
            .andReturn().getResponse().getHeader("Cache-Control");
        assertThat(advResearchCache).contains("private").contains("no-store");

        // Market Research -> private, no-store
        MarketDtos.Response marketRes = new MarketDtos.Response(
            new MarketDtos.Meta("2026-11-27T00:00:00Z", new MarketDtos.Filters(null, null, null, "ALL", true),
                0, 30, "ASKING_SALE_VND_TOTAL", "disc", true, "CC BY-NC 4.0", "INSUFFICIENT_DATA", List.of()),
            new MarketDtos.Stat("ALL", "All", 0, null, null, null, null, null, null, "INSUFFICIENT_DATA", List.of()),
            List.of(), List.of(), List.of(), List.of(), List.of(), List.of(), List.of()
        );
        when(marketService.isResearchEnabled()).thenReturn(true);
        when(marketService.analyticsResearch(any(), any(), any(), any(), eq(true))).thenReturn(marketRes);
        mvc.perform(get("/api/v1/properties/market-analytics?includeResearch=true")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + adminToken))
            .andExpect(status().isOk())
            .andExpect(header().string("Cache-Control", "private, no-store"));

        // Recommendation Research (loopback + demo key + active ADMIN) -> 200 + private, no-store
        when(recommendationService.tinixEnabled()).thenReturn(true);
        when(recommendationService.recommendResearch(any())).thenReturn(new RecommendationDtos.Response(
            "HEURISTIC_V1", "INTERNAL_DEMO", "ASKING_SALE_VND_TOTAL", null, 0, List.of(), List.of(), List.of(), null
        ));
        String recCache = mvc.perform(post("/api/v1/recommendations/research")
                .with(r -> { r.setRemoteAddr("127.0.0.1"); return r; })
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + adminToken)
                .header("X-SmartProp-Demo-Key", "test-demo-key-secret")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"budgetVnd\":3000000000,\"purpose\":\"LIVING\",\"propertyType\":\"HOUSE\"}"))
            .andExpect(status().isOk())
            .andReturn().getResponse().getHeader("Cache-Control");
        assertThat(recCache).contains("private").contains("no-store");

        // Amenity Research (loopback + demo key + active ADMIN) -> 200 + private, no-store
        AmenityDtos.AmenityProfile profile = new AmenityDtos.AmenityProfile(
            "hai-chau", "DISTRICT", "Hải Châu", null, 80.0,
            new AmenityDtos.CategoryScores(80.0, 80.0, 80.0, 80.0, 80.0),
            0.9, 0.85, 120,
            new AmenityDtos.PoiCounts(18, 2, 2, 2, 2, 2, 2, 2, 4),
            8.4, 2.1, "COMPLETE", "NONE", List.of(), "Đầy đủ tiện ích", List.of("OSM"), List.of()
        );
        when(amenityCatalog.getById("hai-chau")).thenReturn(Optional.of(profile));
        String amenityCache = mvc.perform(get("/api/v1/amenities/research/hai-chau")
                .with(r -> { r.setRemoteAddr("127.0.0.1"); return r; })
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + adminToken)
                .header("X-SmartProp-Demo-Key", "test-demo-key-secret"))
            .andExpect(status().isOk())
            .andReturn().getResponse().getHeader("Cache-Control");
        assertThat(amenityCache).contains("private").contains("no-store");
    }

    @Test
    @DisplayName("Advisor research-config capability endpoint enforces active ADMIN and leaks zero keys or research data")
    void advisorResearchConfigCapabilityEndpointSecurity() throws Exception {
        // Anonymous & invalid/revoked/locked/deleted tokens -> 401
        mvc.perform(get("/api/v1/admin/advisor/research-config"))
            .andExpect(status().isUnauthorized());
        for (String badToken : List.of("forged.jwt.token", suspendedAdminToken, deletedAdminToken, revokedAdminToken)) {
            mvc.perform(get("/api/v1/admin/advisor/research-config")
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + badToken))
                .andExpect(status().isUnauthorized());
        }

        // BUYER & BROKER -> 403
        mvc.perform(get("/api/v1/admin/advisor/research-config")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + buyerToken))
            .andExpect(status().isForbidden());
        mvc.perform(get("/api/v1/admin/advisor/research-config")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + brokerToken))
            .andExpect(status().isForbidden());

        // Active ADMIN when disabled -> 200 {"enabled":false} + private, no-store
        when(advisorService.isResearchEnabled()).thenReturn(false);
        var disabledRes = mvc.perform(get("/api/v1/admin/advisor/research-config")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + adminToken))
            .andExpect(status().isOk())
            .andReturn().getResponse();
        assertThat(disabledRes.getHeader("Cache-Control")).contains("private").contains("no-store");
        assertThat(disabledRes.getContentAsString()).isEqualTo("{\"enabled\":false}");

        // Active ADMIN when enabled -> 200 {"enabled":true} + private, no-store (no demoKey or research data)
        when(advisorService.isResearchEnabled()).thenReturn(true);
        var enabledRes = mvc.perform(get("/api/v1/admin/advisor/research-config")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + adminToken))
            .andExpect(status().isOk())
            .andReturn().getResponse();
        assertThat(enabledRes.getHeader("Cache-Control")).contains("private").contains("no-store");
        assertThat(enabledRes.getContentAsString()).isEqualTo("{\"enabled\":true}");
    }

    @Test
    @DisplayName("Loopback-only routes reject non-loopback ADMIN, forged X-Forwarded-For, bad demo key, and disabled research")
    void loopbackOnlyRoutesEnforceDefenseInDepthGuards() throws Exception {
        when(recommendationService.tinixEnabled()).thenReturn(true);

        // Non-loopback ADMIN even WITH valid JWT, demo key, and forged X-Forwarded-For: 127.0.0.1 -> 403
        for (String path : List.of("/api/v1/recommendations/research/config", "/api/v1/amenities/research/hai-chau", "/api/v1/amenities/research/areas")) {
            mvc.perform(get(path)
                    .with(r -> { r.setRemoteAddr("203.0.113.42"); return r; })
                    .header("X-Forwarded-For", "127.0.0.1")
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + adminToken)
                    .header("X-SmartProp-Demo-Key", "test-demo-key-secret"))
                .andExpect(status().isForbidden());
        }
        mvc.perform(post("/api/v1/recommendations/research")
                .with(r -> { r.setRemoteAddr("203.0.113.42"); return r; })
                .header("X-Forwarded-For", "127.0.0.1")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + adminToken)
                .header("X-SmartProp-Demo-Key", "test-demo-key-secret")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"budgetVnd\":3000000000,\"purpose\":\"LIVING\",\"propertyType\":\"HOUSE\"}"))
            .andExpect(status().isForbidden());

        // Loopback ADMIN with missing or wrong demo key -> 403
        mvc.perform(post("/api/v1/recommendations/research")
                .with(r -> { r.setRemoteAddr("127.0.0.1"); return r; })
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + adminToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"budgetVnd\":3000000000,\"purpose\":\"LIVING\",\"propertyType\":\"HOUSE\"}"))
            .andExpect(status().isForbidden());
        mvc.perform(post("/api/v1/recommendations/research")
                .with(r -> { r.setRemoteAddr("127.0.0.1"); return r; })
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + adminToken)
                .header("X-SmartProp-Demo-Key", "wrong-demo-key")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"budgetVnd\":3000000000,\"purpose\":\"LIVING\",\"propertyType\":\"HOUSE\"}"))
            .andExpect(status().isForbidden());
        mvc.perform(get("/api/v1/amenities/research/hai-chau")
                .with(r -> { r.setRemoteAddr("127.0.0.1"); return r; })
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + adminToken)
                .header("X-SmartProp-Demo-Key", "wrong-demo-key"))
            .andExpect(status().isForbidden());

        // Loopback ADMIN with valid demo key when research flag is disabled -> 403
        when(recommendationService.tinixEnabled()).thenReturn(false);
        mvc.perform(post("/api/v1/recommendations/research")
                .with(r -> { r.setRemoteAddr("127.0.0.1"); return r; })
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + adminToken)
                .header("X-SmartProp-Demo-Key", "test-demo-key-secret")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"budgetVnd\":3000000000,\"purpose\":\"LIVING\",\"propertyType\":\"HOUSE\"}"))
            .andExpect(status().isForbidden());
    }
}
