package vn.smartprop.market;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import vn.smartprop.common.ApiException;
import vn.smartprop.common.RequestLimits;
import vn.smartprop.market.MarketAnalyticsRepository.CohortRow;
import vn.smartprop.market.MarketDtos.Response;
import vn.smartprop.modules.auth.AccountAccess;
import vn.smartprop.modules.user.User;
import vn.smartprop.modules.user.UserRepository;

/**
 * Phase 0 — WP03-F01 regression suite: verifies server-side authorization,
 * repository non-invocation on unauthorized requests, public/research cache
 * isolation, and zero research metadata leakage in public responses.
 */
class MarketResearchAccessHardeningTest {

    private final MarketAnalyticsRepository repo = mock(MarketAnalyticsRepository.class);
    private final UserRepository userRepo = mock(UserRepository.class);
    private final AccountAccess access = new AccountAccess(userRepo);
    private final RequestLimits limits = mock(RequestLimits.class);
    private final HttpServletRequest httpReq = mock(HttpServletRequest.class);
    private final HttpServletResponse httpRes = mock(HttpServletResponse.class);
    private final ObjectMapper json = new ObjectMapper();

    @BeforeEach
    void setUp() {
        when(httpReq.getRemoteAddr()).thenReturn("127.0.0.1");
        when(userRepo.findById(10L)).thenReturn(Optional.of(activeUser(10L, User.Role.BUYER)));
        when(userRepo.findById(20L)).thenReturn(Optional.of(activeUser(20L, User.Role.BROKER)));
        when(userRepo.findById(30L)).thenReturn(Optional.of(activeUser(30L, User.Role.ADMIN)));
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

    private static List<CohortRow> publicRows() {
        List<CohortRow> rows = new ArrayList<>();
        for (int i = 0; i < 40; i++) {
            rows.add(new CohortRow("SMARTPROP", "Hải Châu", "Phước Ninh", "HOUSE", 6_000_000_000d, 80.0, null));
        }
        for (int i = 0; i < 35; i++) {
            rows.add(new CohortRow("EXTERNAL_LISTING", "Hải Châu", null, "HOUSE", 5_200_000_000d, 80.0, null));
        }
        return rows;
    }

    private static List<CohortRow> researchRows() {
        List<CohortRow> rows = new ArrayList<>(publicRows());
        for (String m : List.of("2025-06", "2025-07", "2025-08")) {
            for (int i = 0; i < 40; i++) {
                rows.add(new CohortRow("TINIX_RESEARCH", "Hải Châu", "Phước Ninh", "HOUSE", 3_200_000_000d, 80.0, m));
            }
        }
        return rows;
    }

    @Test
    @DisplayName("Anonymous default request returns public SMARTPROP + EXTERNAL_LISTING data with zero research metadata or loadCohort(true)")
    void anonymousDefaultRequestIsCleanAndPublic() throws Exception {
        when(repo.loadCohort(false)).thenReturn(publicRows());
        MarketAnalyticsService service = new MarketAnalyticsService(repo, true);
        MarketAnalyticsController controller = new MarketAnalyticsController(service, limits, access);

        Response res = controller.analytics(null, null, null, null, null, httpReq, httpRes, null);
        assertThat(res.meta().researchIncluded()).isFalse();
        assertThat(res.meta().researchLicense()).isNull();
        assertThat(res.meta().totalSampleCount()).isEqualTo(75L);
        assertThat(res.monthly()).isEmpty();
        assertThat(res.bySource()).extracting(MarketDtos.SourceCount::source)
            .containsExactly("SMARTPROP", "EXTERNAL_LISTING");

        String serialized = json.writeValueAsString(res);
        assertThat(serialized).doesNotContain("TINIX_RESEARCH", "CC BY-NC", "TINIX_RESEARCH_INCLUDED", "SINGLE_SNAPSHOT");

        verify(repo, times(1)).loadCohort(false);
        verify(repo, never()).loadCohort(true);
        verify(httpRes).setHeader("Cache-Control", "no-store");
    }

    @Test
    @DisplayName("Anonymous research attempts (includeResearch=true, source=TINIX_RESEARCH, and combinations) fail closed with 403 and 0 repo calls")
    void anonymousResearchParametersRejectedWithoutTouchingRepository() {
        MarketAnalyticsService service = new MarketAnalyticsService(repo, true);
        MarketAnalyticsController controller = new MarketAnalyticsController(service, limits, access);

        // 1. Anonymous includeResearch=true
        assertThatThrownBy(() -> controller.analytics(null, null, null, null, true, httpReq, httpRes, null))
            .isInstanceOf(ApiException.class)
            .extracting(e -> ((ApiException) e).status).isEqualTo(403);

        // 2. Anonymous source=TINIX_RESEARCH (includeResearch=null)
        assertThatThrownBy(() -> controller.analytics(null, null, null, "TINIX_RESEARCH", null, httpReq, httpRes, null))
            .isInstanceOf(ApiException.class)
            .extracting(e -> ((ApiException) e).status).isEqualTo(403);

        // 3. Combined: source=TINIX_RESEARCH + includeResearch=false
        assertThatThrownBy(() -> controller.analytics(null, null, null, "tinix_research", false, httpReq, httpRes, null))
            .isInstanceOf(ApiException.class)
            .extracting(e -> ((ApiException) e).status).isEqualTo(403);

        // 4. Combined: source=SMARTPROP + includeResearch=true
        assertThatThrownBy(() -> controller.analytics("Hải Châu", null, "HOUSE", "SMARTPROP", true, httpReq, httpRes, null))
            .isInstanceOf(ApiException.class)
            .extracting(e -> ((ApiException) e).status).isEqualTo(403);

        verify(repo, never()).loadCohort(anyBoolean());
    }

    @Test
    @DisplayName("Authenticated BUYER and BROKER users without research permission are rejected (403) without touching repository")
    void nonAdminAuthenticatedUsersRejected() {
        MarketAnalyticsService service = new MarketAnalyticsService(repo, true);
        MarketAnalyticsController controller = new MarketAnalyticsController(service, limits, access);

        for (JwtAuthenticationToken actor : List.of(jwtFor(10L, User.Role.BUYER), jwtFor(20L, User.Role.BROKER))) {
            assertThatThrownBy(() -> controller.analytics(null, null, null, null, true, httpReq, httpRes, actor))
                .isInstanceOf(ApiException.class)
                .extracting(e -> ((ApiException) e).status).isEqualTo(403);
            assertThatThrownBy(() -> controller.analytics(null, null, null, "TINIX_RESEARCH", false, httpReq, httpRes, actor))
                .isInstanceOf(ApiException.class)
                .extracting(e -> ((ApiException) e).status).isEqualTo(403);
        }

        verify(repo, never()).loadCohort(anyBoolean());
    }

    @Test
    @DisplayName("Research disabled fails closed (403) even for authenticated ADMIN without loading research cohort")
    void researchDisabledFailsClosedEvenForAdmin() {
        MarketAnalyticsService disabledService = new MarketAnalyticsService(repo, false);
        MarketAnalyticsController controller = new MarketAnalyticsController(disabledService, limits, access);

        assertThatThrownBy(() -> controller.analytics(null, null, null, null, true, httpReq, httpRes, jwtFor(30L, User.Role.ADMIN)))
            .isInstanceOf(ApiException.class)
            .extracting(e -> ((ApiException) e).status).isEqualTo(403);

        assertThatThrownBy(() -> controller.analytics(null, null, null, "TINIX_RESEARCH", false, httpReq, httpRes, jwtFor(30L, User.Role.ADMIN)))
            .isInstanceOf(ApiException.class)
            .extracting(e -> ((ApiException) e).status).isEqualTo(403);

        verify(repo, never()).loadCohort(anyBoolean());
    }

    @Test
    @DisplayName("Cache isolation: Research -> Public and Public -> Research never cross-contaminate cohorts, medians, or cache keys")
    void bidirectionalCacheIsolationBetweenPublicAndAuthorizedResearch() {
        when(repo.loadCohort(false)).thenReturn(publicRows());     // 75 rows, median ~5.2B-6.0B
        when(repo.loadCohort(true)).thenReturn(researchRows());    // 195 rows (75 public + 120 TiniX @ 3.2B)

        MarketAnalyticsService service = new MarketAnalyticsService(repo, true);
        MarketAnalyticsController controller = new MarketAnalyticsController(service, limits, access);
        JwtAuthenticationToken admin = jwtFor(30L, User.Role.ADMIN);

        // Sequence 1: Authorized Research request FIRST -> then Anonymous Public request for exact same district/type
        Response researchFirst = controller.analytics("Hải Châu", null, "HOUSE", null, true, httpReq, httpRes, admin);
        assertThat(researchFirst.meta().researchIncluded()).isTrue();
        assertThat(researchFirst.meta().researchLicense()).isEqualTo("CC BY-NC 4.0");
        assertThat(researchFirst.meta().totalSampleCount()).isEqualTo(195L);
        assertThat(researchFirst.overall().medianAskingPriceVnd()).isEqualByComparingTo("3200000000");

        Response publicAfterResearch = controller.analytics("Hải Châu", null, "HOUSE", null, false, httpReq, httpRes, null);
        assertThat(publicAfterResearch.meta().researchIncluded()).isFalse();
        assertThat(publicAfterResearch.meta().researchLicense()).isNull();
        assertThat(publicAfterResearch.meta().totalSampleCount()).isEqualTo(75L);
        assertThat(publicAfterResearch.overall().medianAskingPriceVnd()).isEqualByComparingTo("6000000000");
        assertThat(publicAfterResearch.bySource()).extracting(MarketDtos.SourceCount::source)
            .doesNotContain("TINIX_RESEARCH");
        assertThat(publicAfterResearch.monthly()).isEmpty();

        // Sequence 2: Public request FIRST on a fresh service -> then Authorized Research request
        MarketAnalyticsService service2 = new MarketAnalyticsService(repo, true);
        MarketAnalyticsController controller2 = new MarketAnalyticsController(service2, limits, access);

        Response publicFirst = controller2.analytics("Hải Châu", null, "HOUSE", null, null, httpReq, httpRes, null);
        assertThat(publicFirst.meta().totalSampleCount()).isEqualTo(75L);

        Response researchAfterPublic = controller2.analytics("Hải Châu", null, "HOUSE", null, true, httpReq, httpRes, admin);
        assertThat(researchAfterPublic.meta().researchIncluded()).isTrue();
        assertThat(researchAfterPublic.meta().totalSampleCount()).isEqualTo(195L);
        assertThat(researchAfterPublic.monthly()).hasSize(3);

        // Pipe-character delimiter collision test on CacheKey record
        Response pipeA = controller2.analytics("Hải Châu|Phước Ninh", null, "HOUSE", null, false, httpReq, httpRes, null);
        Response pipeB = controller2.analytics("Hải Châu", "Phước Ninh", "HOUSE", null, false, httpReq, httpRes, null);
        assertThat(pipeA.meta().totalSampleCount()).isZero();
        assertThat(pipeB.meta().totalSampleCount()).isEqualTo(40L);
    }

    @Test
    @DisplayName("Empty public cohort returns INSUFFICIENT_DATA without falling back to research data; defensive filter strips stray research rows")
    void emptyPublicCohortAndDefenseInDepthAgainstStrayResearchRows() {
        // Case A: Empty public cohort while research cohort is full
        when(repo.loadCohort(false)).thenReturn(List.of());
        when(repo.loadCohort(true)).thenReturn(researchRows());

        MarketAnalyticsService service = new MarketAnalyticsService(repo, true);
        MarketAnalyticsController controller = new MarketAnalyticsController(service, limits, access);

        Response emptyPublic = controller.analytics(null, null, null, null, false, httpReq, httpRes, null);
        assertThat(emptyPublic.meta().totalSampleCount()).isZero();
        assertThat(emptyPublic.overall().dataStatus()).isEqualTo("INSUFFICIENT_DATA");
        assertThat(emptyPublic.overall().medianAskingPriceVnd()).isNull();
        verify(repo, never()).loadCohort(true);

        // Case B: Defense-in-depth if loadCohort(false) ever returned a stray TINIX_RESEARCH row
        MarketAnalyticsRepository buggyRepo = mock(MarketAnalyticsRepository.class);
        when(buggyRepo.loadCohort(false)).thenReturn(List.of(
            new CohortRow("TINIX_RESEARCH", "Hải Châu", "Phước Ninh", "HOUSE", 3_000_000_000d, 80.0, "2025-08")
        ));
        MarketAnalyticsService guardedService = new MarketAnalyticsService(buggyRepo, false);
        Response sanitized = guardedService.analytics(null, null, null, null, false);
        assertThat(sanitized.meta().totalSampleCount()).isZero();
        assertThat(sanitized.bySource()).extracting(MarketDtos.SourceCount::source)
            .doesNotContain("TINIX_RESEARCH");
    }
}
