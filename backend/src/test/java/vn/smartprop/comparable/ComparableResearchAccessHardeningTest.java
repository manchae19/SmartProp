package vn.smartprop.comparable;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.security.oauth2.jwt.Jwt;
import vn.smartprop.common.ApiException;
import vn.smartprop.common.RequestLimits;
import vn.smartprop.comparable.ComparableCandidateRepository.ExternalRow;
import vn.smartprop.comparable.ComparableCandidateRepository.PropertyRow;
import vn.smartprop.comparable.ComparableCandidateRepository.TinixRow;
import vn.smartprop.modules.auth.AccountAccess;
import vn.smartprop.modules.property.PropertyRepository;
import vn.smartprop.modules.user.User;
import vn.smartprop.modules.user.UserRepository;

/**
 * Phase 0 Task 1–3 — verifies ComparableController and ComparableRankingService
 * research data isolation, BROKER public comparable continuity, ADMIN non-auto-escalation,
 * and zero bypass through default rank(request) overload.
 */
class ComparableResearchAccessHardeningTest {

    private final ComparableCandidateRepository repo = mock(ComparableCandidateRepository.class);
    private final ComparableEligibilityService eligibility = new ComparableEligibilityService();
    private final PropertyRepository properties = mock(PropertyRepository.class);
    private final UserRepository users = mock(UserRepository.class);
    private final AccountAccess access = new AccountAccess(users);
    private final RequestLimits limits = mock(RequestLimits.class);
    private final HttpServletRequest httpReq = mock(HttpServletRequest.class);
    private final HttpServletResponse httpRes = mock(HttpServletResponse.class);
    private final ObjectMapper json = new ObjectMapper();

    @BeforeEach
    void setUp() {
        when(httpReq.getRemoteAddr()).thenReturn("127.0.0.1");
        when(users.findById(10L)).thenReturn(Optional.of(user(10L, User.Role.BUYER, User.Status.ACTIVE, null)));
        when(users.findById(20L)).thenReturn(Optional.of(user(20L, User.Role.BROKER, User.Status.ACTIVE, null)));
        when(users.findById(30L)).thenReturn(Optional.of(user(30L, User.Role.ADMIN, User.Status.ACTIVE, null)));
        when(users.findById(31L)).thenReturn(Optional.of(user(31L, User.Role.ADMIN, User.Status.LOCKED, null)));
        when(users.findById(32L)).thenReturn(Optional.of(user(32L, User.Role.ADMIN, User.Status.ACTIVE, Instant.now())));

        when(repo.tinixCandidates(any(), anyInt())).thenReturn(List.of(
            new TinixRow("tnx-500", "HOUSE", "Hải Châu", "Phước Ninh",
                new BigDecimal("80"), new BigDecimal("5000000000"),
                new BigDecimal("3"), new BigDecimal("5"), new BigDecimal("3"), new BigDecimal("6"), "g1")
        ));
        when(repo.eligibleCounts()).thenReturn(Map.of("SMARTPROP", 1, "EXTERNAL_LISTING", 1, "TINIX_RESEARCH", 55816));
        when(repo.publicEligibleCounts()).thenReturn(Map.of("SMARTPROP", 1, "EXTERNAL_LISTING", 1));
    }

    private static User user(Long id, User.Role role, User.Status status, Instant deletedAt) {
        User u = new User();
        u.id = id;
        u.role = role;
        u.status = status;
        u.deletedAt = deletedAt;
        u.tokenVersion = 1;
        return u;
    }

    private static Jwt jwt(Long id) {
        return Jwt.withTokenValue("tok-" + id)
            .header("alg", "HS256")
            .subject(String.valueOf(id))
            .claim("ver", 1)
            .issuedAt(Instant.now())
            .expiresAt(Instant.now().plusSeconds(900))
            .build();
    }

    private static ComparableDtos.Request sampleReq(Boolean includeResearch) {
        return new ComparableDtos.Request(
            null, "HOUSE", "Hải Châu", null,
            new BigDecimal("80"), new BigDecimal("5000000000"),
            3, 3, 5, includeResearch
        );
    }

    @Test
    @DisplayName("BROKER and default ADMIN calls receive public SMARTPROP + EXTERNAL_LISTING comparables without touching TiniX")
    void brokerAndDefaultAdminReceivePublicComparablesOnly() throws Exception {
        when(repo.propertyCandidates(any(), anyInt())).thenReturn(List.of(
            new PropertyRow("sp-01", "HOUSE", "Hải Châu", "Phước Ninh", new BigDecimal("82"), new BigDecimal("5100000000"), 3)
        ));
        when(repo.externalCandidates(any(), anyString(), anyInt())).thenReturn(List.of(
            new ExternalRow(77L, "CAFELAND", "Nhà ở", "Hải Châu", new BigDecimal("78"), new BigDecimal("4900000000"), "VALID", "https://cafeland.vn/77", "77", null)
        ));

        // Even when researchEnabled=true on the server, neither BROKER nor default ADMIN auto-triggers TiniX!
        ComparableRankingService service = new ComparableRankingService(repo, eligibility, properties, true);
        ComparableController controller = new ComparableController(service, limits, access);

        for (Long actorId : List.of(20L, 30L)) {
            ComparableDtos.Response res = controller.comparables(jwt(actorId), null, sampleReq(null), httpReq, httpRes);
            assertThat(res.comparables())
                .extracting(ComparableDtos.Candidate::sourceKind)
                .containsExactlyInAnyOrder(ComparableDtos.SourceKind.SMARTPROP, ComparableDtos.SourceKind.EXTERNAL_LISTING);
            assertThat(res.eligibleCountsBySource()).containsOnlyKeys("SMARTPROP", "EXTERNAL_LISTING");
            assertThat(json.writeValueAsString(res)).doesNotContain("TINIX_RESEARCH", "tnx-500", "CC BY-NC");
        }

        verify(repo, never()).tinixCandidates(any(), anyInt());
        verify(repo, never()).eligibleCounts();
    }

    @Test
    @DisplayName("Public Comparable search never falls back to TiniX when SMARTPROP and EXTERNAL_LISTING are empty")
    void emptyPublicCohortNeverFallsBackToTinix() {
        when(repo.propertyCandidates(any(), anyInt())).thenReturn(List.of());
        when(repo.externalCandidates(any(), anyString(), anyInt())).thenReturn(List.of());

        ComparableRankingService service = new ComparableRankingService(repo, eligibility, properties, true);
        ComparableController controller = new ComparableController(service, limits, access);

        ComparableDtos.Response res = controller.comparables(jwt(20L), false, sampleReq(false), httpReq, httpRes);
        assertThat(res.candidateCount()).isZero();
        assertThat(res.comparables()).isEmpty();
        assertThat(res.searchStage()).isEqualTo("NONE");
        assertThat(res.eligibleCountsBySource()).doesNotContainKey("TINIX_RESEARCH");

        verify(repo, never()).tinixCandidates(any(), anyInt());
        verify(repo, never()).eligibleCounts();
    }

    @Test
    @DisplayName("Default rank(request) overload cannot bypass research isolation and rejects includeResearch=true")
    void defaultRankOverloadCannotBypassIsolation() {
        when(repo.propertyCandidates(any(), anyInt())).thenReturn(List.of());
        when(repo.externalCandidates(any(), anyString(), anyInt())).thenReturn(List.of());

        ComparableRankingService service = new ComparableRankingService(repo, eligibility, properties, true);

        // 9-arg legacy constructor -> public-only
        ComparableDtos.Response pub = service.rank(new ComparableDtos.Request(
            null, "HOUSE", "Hải Châu", null, new BigDecimal("80"), new BigDecimal("5000000000"), null, null, 5));
        assertThat(pub.comparables()).isEmpty();

        // Passing includeResearch=true into public rank(request) -> 403 FORBIDDEN
        assertThatThrownBy(() -> service.rank(sampleReq(true)))
            .isInstanceOf(ApiException.class)
            .extracting(e -> ((ApiException) e).status).isEqualTo(403);

        // Disabled service rejects rankResearch and rank(req, true)
        ComparableRankingService disabled = new ComparableRankingService(repo, eligibility, properties, false);
        assertThatThrownBy(() -> disabled.rankResearch(sampleReq(true)))
            .isInstanceOf(ApiException.class)
            .extracting(e -> ((ApiException) e).status).isEqualTo(403);
        assertThatThrownBy(() -> disabled.rank(sampleReq(false), true))
            .isInstanceOf(ApiException.class)
            .extracting(e -> ((ApiException) e).status).isEqualTo(403);

        verify(repo, never()).tinixCandidates(any(), anyInt());
    }

    @Test
    @DisplayName("Unauthorized actors (Anonymous, BUYER, BROKER research, suspended/deleted ADMIN, research disabled) fail closed")
    void unauthorizedAndDisabledResearchRequestsFailClosed() {
        ComparableRankingService enabledService = new ComparableRankingService(repo, eligibility, properties, true);
        ComparableController controller = new ComparableController(enabledService, limits, access);

        // Missing JWT -> 401
        assertThatThrownBy(() -> controller.comparables(null, null, sampleReq(false), httpReq, httpRes))
            .isInstanceOf(ApiException.class)
            .extracting(e -> ((ApiException) e).status).isEqualTo(401);

        // BUYER -> 403 even on public comparable
        assertThatThrownBy(() -> controller.comparables(jwt(10L), null, sampleReq(false), httpReq, httpRes))
            .isInstanceOf(ApiException.class)
            .extracting(e -> ((ApiException) e).status).isEqualTo(403);

        // BROKER requesting research via query param or body -> 403
        assertThatThrownBy(() -> controller.comparables(jwt(20L), true, sampleReq(false), httpReq, httpRes))
            .isInstanceOf(ApiException.class)
            .extracting(e -> ((ApiException) e).status).isEqualTo(403);
        assertThatThrownBy(() -> controller.comparables(jwt(20L), null, sampleReq(true), httpReq, httpRes))
            .isInstanceOf(ApiException.class)
            .extracting(e -> ((ApiException) e).status).isEqualTo(403);

        // Suspended ADMIN (31L) and Soft-deleted ADMIN (32L) -> 401
        assertThatThrownBy(() -> controller.comparables(jwt(31L), true, sampleReq(true), httpReq, httpRes))
            .isInstanceOf(ApiException.class)
            .extracting(e -> ((ApiException) e).status).isEqualTo(401);
        assertThatThrownBy(() -> controller.comparables(jwt(32L), true, sampleReq(true), httpReq, httpRes))
            .isInstanceOf(ApiException.class)
            .extracting(e -> ((ApiException) e).status).isEqualTo(401);

        // Active ADMIN when research disabled -> 403
        ComparableController disabledController = new ComparableController(
            new ComparableRankingService(repo, eligibility, properties, false), limits, access);
        assertThatThrownBy(() -> disabledController.comparables(jwt(30L), true, sampleReq(true), httpReq, httpRes))
            .isInstanceOf(ApiException.class)
            .extracting(e -> ((ApiException) e).status).isEqualTo(403);

        verify(repo, never()).tinixCandidates(any(), anyInt());
    }

    @Test
    @DisplayName("Active non-deleted ADMIN with explicit includeResearch=true and research-enabled=true receives labelled TiniX rows")
    void authorizedAdminExplicitResearchSucceedsWhenEnabled() {
        when(repo.propertyCandidates(any(), anyInt())).thenReturn(List.of());
        when(repo.externalCandidates(any(), anyString(), anyInt())).thenReturn(List.of());

        ComparableRankingService enabledService = new ComparableRankingService(repo, eligibility, properties, true);
        ComparableController controller = new ComparableController(enabledService, limits, access);

        ComparableDtos.Response res = controller.comparables(jwt(30L), true, sampleReq(null), httpReq, httpRes);
        assertThat(res.comparables()).hasSize(1);
        ComparableDtos.Candidate c = res.comparables().get(0);
        assertThat(c.candidateId()).isEqualTo("tinix:tnx-500");
        assertThat(c.sourceKind()).isEqualTo(ComparableDtos.SourceKind.TINIX_RESEARCH);
        assertThat(c.listingUrl()).isNull();
        assertThat(c.datasetLicense()).isEqualTo("CC BY-NC 4.0");
        assertThat(res.eligibleCountsBySource()).containsEntry("TINIX_RESEARCH", 55816);
        verify(httpRes).setHeader("Cache-Control", "private, no-store");
    }
}
