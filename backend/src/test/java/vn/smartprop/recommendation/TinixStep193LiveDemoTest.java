package vn.smartprop.modules.recommendation;

import com.fasterxml.jackson.databind.*;
import java.math.BigDecimal;
import java.nio.file.*;
import java.util.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.*;
import vn.smartprop.modules.auth.*;
import vn.smartprop.modules.user.*;
import static org.junit.jupiter.api.Assertions.*;
import static vn.smartprop.modules.recommendation.RecommendationDtos.*;

/** Step 19.3 read-only live verification against MySQL Local smartprop. */
@EnabledIfEnvironmentVariable(named = "SMARTPROP_TINIX_STEP193_TEST", matches = "true")
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = {
    "spring.profiles.active=hybrid-local-existing-v13",
    "app.local-lineage.require-complete=true",
    "server.address=127.0.0.1",
    "app.server.transport=NIO2",
    "spring.jpa.hibernate.ddl-auto=validate",
    "spring.flyway.enabled=false",
    "spring.sql.init.mode=never",
    "spring.datasource.hikari.read-only=true",
    "spring.datasource.hikari.connection-init-sql=SET SESSION TRANSACTION READ ONLY",
    "app.recommendation.allow-unverified-external=false",
    "app.recommendation.tinix-enabled=true",
    "app.broker-applications.enabled=false",
    "app.profile.avatar-enabled=false",
    "app.google.enabled=false",
    "app.seed.enabled=false",
    "app.database-seed.enabled=false",
    "app.import.external-listings=",
    "app.email.enabled=false",
    "app.email.worker-enabled=false",
    "debug=false"
})
class TinixStep193LiveDemoTest {
    static final String KEY = UUID.randomUUID().toString() + UUID.randomUUID();
    static final Path OUT = Path.of("../.scratch/tinix-integration/step19-3");
    static final long[] STEP193_BUDGETS = {
        850_000_000L, 1_500_000_000L, 2_350_000_000L,
        3_780_000_000L, 5_000_000_000L, 10_000_000_000L
    };
    static final long[] ARBITRARY_BUDGETS = {
        1_234_567_890L, 2_350_000_001L, 7_654_321_123L
    };

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", () -> "jdbc:mysql://127.0.0.1:3306/smartprop?connectionTimeZone=UTC");
        r.add("spring.datasource.username", () -> Objects.requireNonNull(System.getenv("DB_USER")));
        r.add("spring.datasource.password", () -> Objects.requireNonNull(System.getenv("DB_PASSWORD")));
        r.add("app.jwt-secret", () -> Objects.requireNonNull(System.getenv("JWT_SECRET")));
        r.add("app.recommendation.demo-key", () -> KEY);
    }

    @Autowired JdbcTemplate jdbc;
    @Autowired HybridRecommendationService service;
    @Autowired RecommendationCandidateRepository publicRepo;
    @Autowired TinixCandidateRepository tinixRepo;
    @Autowired TestRestTemplate http;
    @Autowired ObjectMapper mapper;
    @Autowired SessionRepository sessions;
    @Autowired UserRepository users;
    @Autowired SessionPolicy policy;
    @Autowired TokenService tokens;
    @LocalServerPort int port;

    Request req(long budget, Purpose purpose) {
        return new Request(BigDecimal.valueOf(budget), purpose, PropertyType.ALL, null, null, null, 10);
    }

    List<Map<String, Object>> checksum() {
        var result = new ArrayList<>(jdbc.queryForList(
            "CHECKSUM TABLE external_listings,external_duplicate_groups,properties,property_images,auth_sessions,flyway_schema_history EXTENDED"));
        result.addAll(jdbc.queryForList(
            "SELECT COUNT(*) AS rows_count,BIT_XOR(CRC32(CONCAT_WS('|',internal_id,quality_status,is_protected_holdout,is_duplicate_representative,transaction_type,price_vnd))) AS metadata_fingerprint FROM tinix_dataset_records FORCE INDEX (ix_tinix_hybrid)"));
        return result;
    }

    void verifyResponseInvariants(Response r, long budget, boolean allowTinix) {
        assertNotNull(r);
        assertTrue(r.topProperties().size() <= 10);
        assertTrue(r.topAreas().size() <= 5);
        Set<String> seenIds = new HashSet<>();
        Set<String> seenGroups = new HashSet<>();
        for (var p : r.topProperties()) {
            assertTrue(seenIds.add(p.id()), "Duplicate property id: " + p.id());
            assertTrue(p.priceVnd().compareTo(BigDecimal.valueOf(budget)) <= 0, "Over budget: " + p.priceVnd());
            assertTrue(p.priceVnd().signum() > 0 && p.areaSqm().signum() > 0);
            assertTrue(p.score() >= 0 && p.score() <= 100);
            assertFalse(p.explanations().isEmpty());
            if ("TINIX_AI".equals(p.source().kind())) {
                assertTrue(allowTinix, "TINIX_AI leaked into SAFE mode");
                assertNotNull(p.duplicateGroup());
                assertTrue(seenGroups.add(p.duplicateGroup()), "Duplicate group in Top 10: " + p.duplicateGroup());
                assertNull(p.source().detailUrl());
                assertEquals("HYBRID_ELIGIBLE_RESEARCH", p.qualityStatus());
                assertEquals("UNVERIFIED", p.verificationStatus());
                assertTrue(p.warnings().stream().anyMatch(w -> w.contains("Dữ liệu nghiên cứu TiniX AI — chưa xác minh")));
                Integer dbMatch = jdbc.queryForObject("""
                    SELECT COUNT(*) FROM tinix_dataset_records
                    WHERE internal_id=? AND quality_status='HYBRID_ELIGIBLE_RESEARCH'
                      AND verification_status='UNVERIFIED' AND research_only=1
                      AND transaction_type='SALE' AND transaction_basis='EXPLICIT_SALE_TEXT'
                      AND is_protected_holdout=0 AND is_duplicate_representative=1
                      AND JSON_LENGTH(quality_issues)=0
                    """, Integer.class, p.source().recordKey());
                assertEquals(1, dbMatch, "Top property not backed by eligible MySQL representative: " + p.id());
                Integer groupHeld = jdbc.queryForObject(
                    "SELECT COUNT(*) FROM tinix_dataset_records FORCE INDEX (ix_tinix_group) WHERE duplicate_group=? AND is_protected_holdout=1",
                    Integer.class, p.duplicateGroup());
                assertEquals(0, groupHeld, "Protected holdout group leaked: " + p.duplicateGroup());
            } else {
                assertNotEquals("UNVERIFIED", p.verificationStatus());
                assertNotEquals("NEEDS_REVIEW", p.qualityStatus());
                assertNotEquals("EXCLUDED", p.qualityStatus());
            }
        }
    }

    @Test
    void runStep193FullVerification() throws Exception {
        Files.createDirectories(OUT);
        var before = checksum();

        assertEquals("smartprop", jdbc.queryForObject("SELECT DATABASE()", String.class));
        assertEquals(3306, jdbc.queryForObject("SELECT @@port", Integer.class));
        assertEquals(185973, jdbc.queryForObject("SELECT COUNT(*) FROM tinix_dataset_records FORCE INDEX (ix_tinix_hybrid)", Integer.class));
        assertEquals(983, jdbc.queryForObject("SELECT COUNT(*) FROM external_listings WHERE is_protected_holdout=1", Integer.class));

        Map<String, Object> fullReport = new LinkedHashMap<>();

        // 1. Primary Test: 2,350,000,000 VND - ALL - LIVING
        Request mainReq = req(2_350_000_000L, Purpose.LIVING);
        long tPub0 = System.nanoTime();
        var rawPublic = publicRepo.find(mainReq, false);
        double pubMs = (System.nanoTime() - tPub0) / 1_000_000.0;

        long tTinix0 = System.nanoTime();
        var rawTinix = tinixRepo.find(mainReq);
        double tinixMs = (System.nanoTime() - tTinix0) / 1_000_000.0;

        long tSvc0 = System.nanoTime();
        Response mainResearch = service.recommendResearch(mainReq);
        double mainSvcMs = (System.nanoTime() - tSvc0) / 1_000_000.0;

        verifyResponseInvariants(mainResearch, 2_350_000_000L, true);
        assertEquals("INTERNAL_DEMO", mainResearch.mode());
        assertEquals("HEURISTIC_V1", mainResearch.method());
        assertEquals(10, mainResearch.topProperties().size());
        assertEquals(5, mainResearch.topAreas().size());
        assertTrue(mainResearch.topProperties().stream().allMatch(p ->
            p.explanations().stream().anyMatch(e -> e.contains("Heuristic LIVING: trọng số ngân sách 60.0%"))));

        Files.writeString(OUT.resolve("main-2350m-living.json"),
            mapper.writerWithDefaultPrettyPrinter().writeValueAsString(mainResearch));

        Map<String, Object> mainStats = new LinkedHashMap<>();
        mainStats.put("budgetVnd", 2_350_000_000L);
        mainStats.put("rawPublicCandidates", rawPublic.size());
        mainStats.put("rawTinixAdapterCandidates", rawTinix.size());
        mainStats.put("totalRawLoadedForRequest", rawPublic.size() + rawTinix.size());
        mainStats.put("eligibleUniqueCandidatesAfterFilterAndDedup", mainResearch.eligibleCandidateCount());
        mainStats.put("topPropertiesCount", mainResearch.topProperties().size());
        mainStats.put("topAreasCount", mainResearch.topAreas().size());
        mainStats.put("publicRepoMs", Math.round(pubMs * 100.0) / 100.0);
        mainStats.put("tinixRepoFirstCallMs", Math.round(tinixMs * 100.0) / 100.0);
        mainStats.put("recommendResearchCallMs", Math.round(mainSvcMs * 100.0) / 100.0);
        fullReport.put("mainTest2350M", mainStats);

        // 2. All 6 Step 19.3 budgets (Research Service + Live SAFE HTTP)
        List<Map<String, Object>> budgetRuns = new ArrayList<>();
        for (long b : STEP193_BUDGETS) {
            Runtime rt = Runtime.getRuntime();
            long heapBeforeMb = (rt.totalMemory() - rt.freeMemory()) / (1024 * 1024);

            long t0 = System.nanoTime();
            Response res = service.recommendResearch(req(b, Purpose.LIVING));
            double researchMs = (System.nanoTime() - t0) / 1_000_000.0;
            verifyResponseInvariants(res, b, true);
            assertEquals(10, res.topProperties().size());
            assertEquals(5, res.topAreas().size());

            long tWarm0 = System.nanoTime();
            Response resWarm = service.recommendResearch(req(b, Purpose.LIVING));
            double researchWarmMs = (System.nanoTime() - tWarm0) / 1_000_000.0;
            assertEquals(res.eligibleCandidateCount(), resWarm.eligibleCandidateCount());
            assertEquals(res.topProperties().stream().map(PropertyResult::id).toList(),
                resWarm.topProperties().stream().map(PropertyResult::id).toList());

            long tSafe0 = System.nanoTime();
            ResponseEntity<Response> safeHttp = http.postForEntity("/api/v1/recommendations", req(b, Purpose.LIVING), Response.class);
            double safeHttpMs = (System.nanoTime() - tSafe0) / 1_000_000.0;
            assertEquals(HttpStatus.OK, safeHttp.getStatusCode());
            assertEquals("no-store", safeHttp.getHeaders().getCacheControl());
            assertEquals("SAFE", safeHttp.getBody().mode());
            verifyResponseInvariants(safeHttp.getBody(), b, false);

            long heapAfterMb = (rt.totalMemory() - rt.freeMemory()) / (1024 * 1024);

            Files.writeString(OUT.resolve("research-" + b + ".json"),
                mapper.writerWithDefaultPrettyPrinter().writeValueAsString(res));
            Files.writeString(OUT.resolve("safe-http-" + b + ".json"),
                mapper.writerWithDefaultPrettyPrinter().writeValueAsString(safeHttp.getBody()));

            Map<String, Object> row = new LinkedHashMap<>();
            row.put("budgetVnd", b);
            row.put("eligibleCandidateCount", res.eligibleCandidateCount());
            row.put("researchTopProperties", res.topProperties().size());
            row.put("researchTopAreas", res.topAreas().size());
            row.put("tinixInTop10", res.topProperties().stream().filter(p -> "TINIX_AI".equals(p.source().kind())).count());
            row.put("propertyInTop10", res.topProperties().stream().filter(p -> "PROPERTY".equals(p.source().kind())).count());
            row.put("researchFirstMs", Math.round(researchMs * 100.0) / 100.0);
            row.put("researchWarmMs", Math.round(researchWarmMs * 100.0) / 100.0);
            row.put("safeHttpStatus", safeHttp.getStatusCode().value());
            row.put("safeEligibleCandidates", safeHttp.getBody().eligibleCandidateCount());
            row.put("safeTopProperties", safeHttp.getBody().topProperties().size());
            row.put("safeTopAreas", safeHttp.getBody().topAreas().size());
            row.put("safeHttpMs", Math.round(safeHttpMs * 100.0) / 100.0);
            row.put("heapBeforeMb", heapBeforeMb);
            row.put("heapAfterMb", heapAfterMb);
            budgetRuns.add(row);
        }
        fullReport.put("sixBudgets", budgetRuns);

        // 3. Arbitrary non-round VND budgets & all 3 purposes
        List<Map<String, Object>> arbitraryRuns = new ArrayList<>();
        for (long b : ARBITRARY_BUDGETS) {
            long t0 = System.nanoTime();
            Response res = service.recommendResearch(req(b, Purpose.LIVING));
            double ms = (System.nanoTime() - t0) / 1_000_000.0;
            verifyResponseInvariants(res, b, true);
            ResponseEntity<Response> safeHttp = http.postForEntity("/api/v1/recommendations", req(b, Purpose.LIVING), Response.class);
            assertEquals(HttpStatus.OK, safeHttp.getStatusCode());
            verifyResponseInvariants(safeHttp.getBody(), b, false);
            arbitraryRuns.add(Map.of(
                "budgetVnd", b,
                "eligibleCandidateCount", res.eligibleCandidateCount(),
                "topProperties", res.topProperties().size(),
                "ms", Math.round(ms * 100.0) / 100.0,
                "safeHttpStatus", safeHttp.getStatusCode().value()
            ));
        }
        fullReport.put("arbitraryBudgets", arbitraryRuns);

        for (Purpose p : Purpose.values()) {
            Response r = service.recommendResearch(req(2_350_000_000L, p));
            verifyResponseInvariants(r, 2_350_000_000L, true);
        }

        // 4. Live HTTP Security Checks
        Map<String, Object> securityChecks = new LinkedHashMap<>();
        var anonResearch = http.postForEntity("/api/v1/recommendations/research", mainReq, JsonNode.class);
        assertEquals(HttpStatus.UNAUTHORIZED, anonResearch.getStatusCode());
        securityChecks.put("anonymousPostResearchHttp", anonResearch.getStatusCode().value());

        var anonConfig = http.getForEntity("/api/v1/recommendations/research/config", JsonNode.class);
        assertEquals(HttpStatus.UNAUTHORIZED, anonConfig.getStatusCode());
        securityChecks.put("anonymousGetResearchConfigHttp", anonConfig.getStatusCode().value());

        var keyOnlyHeaders = new HttpHeaders();
        keyOnlyHeaders.set("X-SmartProp-Demo-Key", KEY);
        var keyOnlyResearch = http.postForEntity("/api/v1/recommendations/research",
            new HttpEntity<>(mainReq, keyOnlyHeaders), JsonNode.class);
        assertEquals(HttpStatus.UNAUTHORIZED, keyOnlyResearch.getStatusCode());
        securityChecks.put("demoKeyWithoutJwtHttp", keyOnlyResearch.getStatusCode().value());

        var badTokenHeaders = new HttpHeaders();
        badTokenHeaders.setBearerAuth("invalid-jwt-token");
        badTokenHeaders.set("X-SmartProp-Demo-Key", KEY);
        var badTokenResearch = http.postForEntity("/api/v1/recommendations/research",
            new HttpEntity<>(mainReq, badTokenHeaders), JsonNode.class);
        assertEquals(HttpStatus.UNAUTHORIZED, badTokenResearch.getStatusCode());
        securityChecks.put("invalidJwtWithValidDemoKeyHttp", badTokenResearch.getStatusCode().value());

        // Check existing valid ADMIN session in MySQL without creating/modifying any session
        AuthSession validAdminSession = null;
        User adminUser = null;
        for (var s : sessions.findAll()) {
            var u = users.findById(s.userId).orElse(null);
            if (u != null && u.role == User.Role.ADMIN && u.status == User.Status.ACTIVE
                    && u.deletedAt == null && policy.valid(s, u)) {
                validAdminSession = s;
                adminUser = u;
                break;
            }
        }
        if (validAdminSession == null) {
            securityChecks.put("liveAdminSessionStatus", "BLOCKED_AUTH");
            securityChecks.put("liveAdminSessionReason", "No existing valid ADMIN session in auth_sessions; session fabrication/mutation prohibited.");
        } else {
            String token = tokens.issueFresh(validAdminSession, adminUser.tokenVersion);
            var h = new HttpHeaders();
            h.setBearerAuth(token);
            assertEquals(HttpStatus.FORBIDDEN, http.postForEntity("/api/v1/recommendations/research",
                new HttpEntity<>(mainReq, h), JsonNode.class).getStatusCode());
            h.set("X-SmartProp-Demo-Key", KEY);
            var liveAdminResp = http.postForEntity("/api/v1/recommendations/research",
                new HttpEntity<>(mainReq, h), Response.class);
            assertEquals(HttpStatus.OK, liveAdminResp.getStatusCode());
            verifyResponseInvariants(liveAdminResp.getBody(), 2_350_000_000L, true);
            securityChecks.put("liveAdminSessionStatus", "PASS");
            securityChecks.put("liveAdminResearchHttp", liveAdminResp.getStatusCode().value());
        }
        fullReport.put("securityChecks", securityChecks);

        // 5. Verify zero database mutation
        var after = checksum();
        assertEquals(before, after, "Database checksum changed during read-only test!");
        fullReport.put("databaseUnchangedVerified", true);

        Files.writeString(OUT.resolve("hybrid-step19-3-results.json"),
            mapper.writerWithDefaultPrettyPrinter().writeValueAsString(fullReport));
    }
}
