package vn.smartprop.recommendation;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
import org.springframework.test.web.servlet.result.MockMvcResultMatchers;
import vn.smartprop.amenity.AmenityCatalogService;
import vn.smartprop.recommendation.RecommendationDtos.*;

import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;

/**
 * Opt-in live acceptance + V1/V1.1 benchmark against the real local MySQL dataset.
 *
 * <p>Read-only: no writes, no migrations, no imports and no account/session creation.
 * The ADMIN principal is a MockMvc test principal so the real controller guard, service,
 * catalog and MySQL stack are exercised without minting or extending a database session.
 */
@EnabledIfEnvironmentVariable(named = "SMARTPROP_HYBRID_V11_LIVE", matches = "true")
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.MOCK, properties = {
    "spring.profiles.active=hybrid-local-existing-v13","app.local-lineage.require-complete=true",
    "app.broker-applications.enabled=false","app.profile.avatar-enabled=false","app.google.enabled=false",
    "server.address=127.0.0.1","app.server.transport=NIO2","spring.jpa.hibernate.ddl-auto=validate",
    "spring.flyway.enabled=false","spring.sql.init.mode=never","spring.datasource.hikari.read-only=true",
    "spring.datasource.hikari.connection-init-sql=SET SESSION TRANSACTION READ ONLY",
    "app.recommendation.tinix-enabled=true","app.recommendation.v11-enabled=true",
    "app.recommendation.allow-unverified-external=true","app.seed.enabled=false",
    "app.database-seed.enabled=false","app.import.external-listings=","app.email.enabled=false",
    "app.email.worker-enabled=false","debug=false",
    "app.recommendation.tinix-revision=ca3fedcbb089bf65f7e4cfb03316cce4bd0d779f"})
@AutoConfigureMockMvc
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
class HybridV11MySqlIntegrationTest {
    static final String KEY = UUID.randomUUID().toString() + UUID.randomUUID();
    static final Path OUT = Path.of("..", ".scratch", "tinix-integration", "step19-4-2");
    static final ObjectMapper MAPPER = new ObjectMapper();

    @DynamicPropertySource static void local(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", () -> "jdbc:mysql://127.0.0.1:3306/smartprop?connectionTimeZone=UTC");
        r.add("spring.datasource.username", () -> Objects.requireNonNull(System.getenv("DB_USER")));
        r.add("spring.datasource.password", () -> Objects.requireNonNull(System.getenv("DB_PASSWORD")));
        r.add("app.jwt-secret", () -> UUID.randomUUID().toString() + UUID.randomUUID());
        r.add("app.recommendation.demo-key", () -> KEY);
    }

    @Autowired MockMvc mvc;
    @Autowired JdbcTemplate jdbc;
    @Autowired AmenityCatalogService catalog;

    /** ADMIN principal + loopback caller, applied as MockMvc post-processors. */
    static org.springframework.test.web.servlet.request.RequestPostProcessor[] admin() {
        org.springframework.test.web.servlet.request.RequestPostProcessor loopback = r -> {
            r.setRemoteAddr("127.0.0.1");
            return r;
        };
        return new org.springframework.test.web.servlet.request.RequestPostProcessor[]{
            jwt().authorities(new SimpleGrantedAuthority("ROLE_ADMIN")), loopback};
    }

    /** Applies the ADMIN post-processors to a MockMvc request builder. */
    static org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder asAdmin(
            org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder builder) {
        for (var p : admin()) builder.with(p);
        return builder;
    }

    @Test @Order(1) void databaseMatchesTheHandoverNumbers() {
        assertEquals(185973, jdbc.queryForObject("SELECT COUNT(*) FROM tinix_dataset_records", Integer.class));
        assertEquals(55816, jdbc.queryForObject(
            "SELECT COUNT(*) FROM tinix_dataset_records WHERE quality_status='HYBRID_ELIGIBLE_RESEARCH'"
            + " AND is_duplicate_representative=1 AND is_protected_holdout=0", Integer.class));
        assertEquals(1449, jdbc.queryForObject("SELECT COUNT(*) FROM points_of_interest", Integer.class));
        assertEquals(82, catalog.listAreas(null, null).size());
        assertEquals(1323, catalog.getSummary().totalEffectivePois());
    }

    @Test @Order(2) void researchApiReturnsRealV11EvidenceForTwoBillionLiving() throws Exception {
        var body = "{\"budgetVnd\":2000000000,\"purpose\":\"LIVING\",\"propertyType\":\"ALL\",\"limit\":10}";
        var response = mvc.perform(MockMvcRequestBuilders.post("/api/v1/recommendations/research")
                .with(admin()[0]).with(admin()[1]).header("X-SmartProp-Demo-Key", KEY)
                .contentType(MediaType.APPLICATION_JSON).content(body))
            .andExpect(MockMvcResultMatchers.status().isOk())
            .andReturn().getResponse();
        var json = MAPPER.readTree(response.getContentAsString(StandardCharsets.UTF_8));
        assertEquals("HEURISTIC_V1_1", json.path("method").asText());
        assertEquals("INTERNAL_DEMO", json.path("mode").asText());
        assertEquals(10, json.path("topProperties").size());
        assertTrue(json.path("topAreas").size() > 0 && json.path("topAreas").size() <= 5);
        assertFalse(json.path("scoringWeights").isMissingNode());
        boolean anyEvidence = false;
        for (var p : json.path("topProperties")) {
            assertTrue(p.path("priceVnd").decimalValue().compareTo(BigDecimal.valueOf(2_000_000_000L)) <= 0);
            double score = p.path("score").asDouble();
            assertTrue(score >= 0 && score <= 100);
            assertTrue(p.path("scoreBreakdown").has("propertyTypeFit"));
            var evidence = p.path("amenityEvidence");
            if (!evidence.isMissingNode() && !evidence.isNull() && !evidence.path("areaAmenityScore").isNull()) {
                anyEvidence = true;
                double amenity = evidence.path("areaAmenityScore").asDouble();
                assertTrue(amenity >= 0 && amenity <= 100);
                assertTrue(evidence.path("confidence").asDouble() <= 1.0);
                assertTrue(evidence.path("dataLimitations").size() > 0);
            }
            for (var text : p.path("explanations")) assertFalse(text.asText().matches(".*\\bcách\\s+\\d+.*"));
        }
        assertTrue(anyEvidence, "at least one TiniX candidate must resolve to an amenity profile");
        assertFalse(json.toString().contains("sampleListingCount"), "restricted research metadata must not reach the API");
        System.out.println("SMARTPROP_V11_LIVE: candidates=" + json.path("eligibleCandidateCount").asInt()
            + " types=" + typeDistribution(json) + " weights=" + json.path("scoringWeights"));
    }

    @Test @Order(3) void amenityApiHidesResearchCountsAndGuardedResearchRouteNeedsAdmin() throws Exception {
        var pub = mvc.perform(MockMvcRequestBuilders.get("/api/v1/amenities/lookup?district=Ngu+Hanh+Son&ward=My+An"))
            .andExpect(MockMvcResultMatchers.status().isOk())
            .andReturn().getResponse();
        var body = MAPPER.readTree(pub.getContentAsString(StandardCharsets.UTF_8));
        assertEquals("WARD", body.path("areaLevel").asText());
        assertTrue(body.path("livingScore").asDouble() > 0);
        assertFalse(body.has("sampleListingCount"), "public amenities must not expose TiniX sample counts");

        mvc.perform(MockMvcRequestBuilders.get("/api/v1/amenities/research/ward-my-an-ngu-hanh-son"))
            .andExpect(MockMvcResultMatchers.status().isUnauthorized());

        mvc.perform(MockMvcRequestBuilders.get("/api/v1/amenities/research/ward-my-an-ngu-hanh-son")
                .with(admin()[0]).with(admin()[1]).header("X-SmartProp-Demo-Key", "wrong-key"))
            .andExpect(MockMvcResultMatchers.status().isForbidden());

        var allowed = mvc.perform(MockMvcRequestBuilders.get("/api/v1/amenities/research/ward-my-an-ngu-hanh-son")
                .with(admin()[0]).with(admin()[1]).header("X-SmartProp-Demo-Key", KEY))
            .andExpect(MockMvcResultMatchers.status().isOk())
            .andReturn().getResponse();
        assertTrue(MAPPER.readTree(allowed.getContentAsString(StandardCharsets.UTF_8))
            .path("sampleListingCount").asInt() > 0);
    }

    @Test @Order(4) void benchmarkV1VersusV11OnTheSameCandidates() throws Exception {
        var repo = new RecommendationCandidateRepository(jdbc, new ObjectMapper());
        var areaV1 = new AreaScoringService();
        var v1 = new HybridRecommendationService(repo, new PropertyScoringService(), areaV1, true);
        var resolver = new PropertyLocationResolver(catalog);
        var evidence = new AmenityEvidenceService();
        var v11 = new HybridRecommendationService(repo, new PropertyScoringService(), areaV1, true,
            new PropertyScoringV11Service(resolver, 0.38, 0.17, 0.20, 0.25, 0.45, 0.25, 0.20, 0.10, 0.40, 0.20, 0.25, 0.15),
            new AreaScoringV11Service(resolver, evidence), evidence, resolver, true);

        record Scenario(String name, long budget, Purpose purpose, PropertyType type, String district, BigDecimal minArea) {}
        var scenarios = List.of(
            new Scenario("LIVING-1B-ALL", 1_000_000_000L, Purpose.LIVING, PropertyType.ALL, null, null),
            new Scenario("LIVING-2B-ALL", 2_000_000_000L, Purpose.LIVING, PropertyType.ALL, null, null),
            new Scenario("LIVING-2.35B-ALL", 2_350_000_000L, Purpose.LIVING, PropertyType.ALL, null, null),
            new Scenario("LIVING-5B-ALL", 5_000_000_000L, Purpose.LIVING, PropertyType.ALL, null, null),
            new Scenario("LIVING-5B-HOUSE", 5_000_000_000L, Purpose.LIVING, PropertyType.HOUSE, null, null),
            new Scenario("LIVING-5B-APARTMENT", 5_000_000_000L, Purpose.LIVING, PropertyType.APARTMENT, null, null),
            new Scenario("RENTAL-5B-ALL", 5_000_000_000L, Purpose.RENTAL, PropertyType.ALL, null, null),
            new Scenario("INVESTMENT-5B-ALL", 5_000_000_000L, Purpose.INVESTMENT, PropertyType.ALL, null, null),
            new Scenario("LIVING-2.35B-ALL-MinArea60", 2_350_000_000L, Purpose.LIVING, PropertyType.ALL, null, new BigDecimal("60")),
            new Scenario("LIVING-2B-ALL-HoaVang", 2_000_000_000L, Purpose.LIVING, PropertyType.ALL, "Hòa Vang", null),
            new Scenario("LIVING-2B-ALL-UnknownDistrict", 2_000_000_000L, Purpose.LIVING, PropertyType.ALL, "Huyện Không Tồn Tại", null));

        var root = MAPPER.createObjectNode();
        var scenarioNodes = root.putArray("scenarios");
        var csv = new StringBuilder("scenario,eligible,v1_ms,v11_ms,types_v1,types_v11,properties_with_amenity_evidence,ward_level_evidence,district_level_evidence,top10_overlap\n");
        for (var sc : scenarios) {
            var request = new Request(BigDecimal.valueOf(sc.budget()), sc.purpose(), sc.type(), sc.minArea(), sc.district(), null, 10);
            long t0 = System.nanoTime();
            var r1 = v1.recommend(request);
            long ms1 = (System.nanoTime() - t0) / 1_000_000;
            t0 = System.nanoTime();
            var r11 = v11.recommend(request);
            long ms11 = (System.nanoTime() - t0) / 1_000_000;
            var ids1 = r1.topProperties().stream().map(PropertyResult::id).toList();
            var ids11 = r11.topProperties().stream().map(PropertyResult::id).toList();
            var typesV1 = distribution(r1.topProperties().stream().map(p -> p.propertyType().name()).toList());
            var typesV11 = distribution(r11.topProperties().stream().map(p -> p.propertyType().name()).toList());
            long withEvidence = r11.topProperties().stream()
                .filter(p -> p.amenityEvidence() != null && p.amenityEvidence().areaAmenityScore() != null).count();
            long wardLevel = r11.topProperties().stream()
                .filter(p -> p.amenityEvidence() != null && "WARD".equals(p.amenityEvidence().areaLevel())).count();
            long districtLevel = r11.topProperties().stream()
                .filter(p -> p.amenityEvidence() != null && "DISTRICT".equals(p.amenityEvidence().areaLevel())).count();
            long violations = r11.topProperties().stream()
                .filter(p -> p.priceVnd().compareTo(request.budgetVnd()) > 0).count();
            int overlap = overlap(ids1, ids11);

            ObjectNode node = scenarioNodes.addObject();
            node.put("name", sc.name());
            node.put("budgetVnd", sc.budget());
            node.put("purpose", sc.purpose().name());
            node.put("propertyType", sc.type().name());
            if (sc.district() == null) node.putNull("district"); else node.put("district", sc.district());
            node.put("eligibleCandidates", r11.eligibleCandidateCount());
            node.put("v1Ms", ms1);
            node.put("v11Ms", ms11);
            var a1 = node.putArray("v1Top10"); ids1.forEach(a1::add);
            var a11 = node.putArray("v11Top10"); ids11.forEach(a11::add);
            node.put("typeDistributionV1", typesV1);
            node.put("typeDistributionV11", typesV11);
            node.put("budgetViolations", violations);
            node.put("propertiesWithAmenityEvidence", withEvidence);
            node.put("wardLevelEvidence", wardLevel);
            node.put("districtLevelEvidence", districtLevel);
            node.put("top10Overlap", overlap);
            var areas = node.putArray("topAreasV11");
            r11.topAreas().forEach(a -> {
                var an = areas.addObject();
                an.put("district", a.district());
                an.put("ward", a.ward() == null ? "" : a.ward());
                an.put("candidateCount", a.candidateCount());
                an.put("areaScore", a.score());
                if (a.amenityScore() == null) an.putNull("amenityScore"); else an.put("amenityScore", a.amenityScore());
                an.put("amenityBasis", a.amenityEvidenceBasis());
            });
            csv.append(sc.name()).append(',').append(r11.eligibleCandidateCount()).append(',')
                .append(ms1).append(',').append(ms11).append(',')
                .append('"').append(typesV1).append('"').append(',').append('"').append(typesV11).append('"').append(',')
                .append(withEvidence).append(',').append(wardLevel).append(',').append(districtLevel).append(',')
                .append(overlap).append('\n');
            System.out.println("BENCH " + sc.name() + ": eligible=" + r11.eligibleCandidateCount()
                + " v1=" + ms1 + "ms v11=" + ms11 + "ms types(V1)=" + typesV1 + " types(V1.1)=" + typesV11
                + " evidence=" + withEvidence + "/10 (ward " + wardLevel + ", district " + districtLevel + ")"
                + " overlap=" + overlap + " budgetViolations=" + violations);
            assertEquals(0, violations, "V1.1 must never return an over-budget property");
        }
        assertTrue(Files.isDirectory(OUT), "step19-4-2 output directory must exist");
        Files.writeString(OUT.resolve("benchmark_results.json"),
            MAPPER.writerWithDefaultPrettyPrinter().writeValueAsString(root), StandardCharsets.UTF_8);
        Files.writeString(OUT.resolve("ranking_comparison.csv"), csv.toString(), StandardCharsets.UTF_8);
    }

    @Test @Order(5) void researchBenchmarkIncludesTinixCandidatesWithWardEvidence() throws Exception {
        var repo = new RecommendationCandidateRepository(jdbc, new ObjectMapper());
        var tinixRepo = new TinixCandidateRepository(jdbc, "ca3fedcbb089bf65f7e4cfb03316cce4bd0d779f");
        var areaV1 = new AreaScoringService();
        var v1 = new HybridRecommendationService(repo, new PropertyScoringService(), areaV1, true);
        v1.configureTinix(tinixRepo, true);
        var resolver = new PropertyLocationResolver(catalog);
        var evidence = new AmenityEvidenceService();
        var v11 = new HybridRecommendationService(repo, new PropertyScoringService(), areaV1, true,
            new PropertyScoringV11Service(resolver, 0.38, 0.17, 0.20, 0.25, 0.45, 0.25, 0.20, 0.10, 0.40, 0.20, 0.25, 0.15),
            new AreaScoringV11Service(resolver, evidence), evidence, resolver, true);
        v11.configureTinix(tinixRepo, true);

        var root = MAPPER.createObjectNode();
        root.put("mode", "INTERNAL_RESEARCH");
        var nodes = root.putArray("scenarios");
        var csv = new StringBuilder("scenario,eligible,v1_ms,v11_ms,types_v1,types_v11,properties_with_amenity_evidence,ward_level_evidence,district_level_evidence,no_evidence,top10_overlap,budget_violations\n");
        record R(String name, long budget, Purpose purpose, PropertyType type, String district) {}
        for (var sc : List.of(
                new R("RESEARCH-LIVING-2B-ALL", 2_000_000_000L, Purpose.LIVING, PropertyType.ALL, null),
                new R("RESEARCH-LIVING-2.35B-ALL", 2_350_000_000L, Purpose.LIVING, PropertyType.ALL, null),
                new R("RESEARCH-LIVING-5B-ALL", 5_000_000_000L, Purpose.LIVING, PropertyType.ALL, null),
                new R("RESEARCH-LIVING-2B-HOUSE", 2_000_000_000L, Purpose.LIVING, PropertyType.HOUSE, null),
                new R("RESEARCH-LIVING-2B-APARTMENT", 2_000_000_000L, Purpose.LIVING, PropertyType.APARTMENT, null),
                new R("RESEARCH-RENTAL-5B-ALL", 5_000_000_000L, Purpose.RENTAL, PropertyType.ALL, null),
                new R("RESEARCH-INVESTMENT-5B-ALL", 5_000_000_000L, Purpose.INVESTMENT, PropertyType.ALL, null),
                new R("RESEARCH-LIVING-2B-HoaVang", 2_000_000_000L, Purpose.LIVING, PropertyType.ALL, "Hòa Vang"),
                new R("RESEARCH-LIVING-2B-NguHanhSon", 2_000_000_000L, Purpose.LIVING, PropertyType.ALL, "Ngũ Hành Sơn"))) {
            var request = new Request(BigDecimal.valueOf(sc.budget()), sc.purpose(), sc.type(), null, sc.district(), null, 10);
            long t0 = System.nanoTime();
            var r1 = v1.recommendResearch(request);
            long ms1 = (System.nanoTime() - t0) / 1_000_000;
            t0 = System.nanoTime();
            var r11 = v11.recommendResearch(request);
            long ms11 = (System.nanoTime() - t0) / 1_000_000;
            var ids1 = r1.topProperties().stream().map(PropertyResult::id).toList();
            var ids11 = r11.topProperties().stream().map(PropertyResult::id).toList();
            var typesV1 = distribution(r1.topProperties().stream().map(p -> p.propertyType().name()).toList());
            var typesV11 = distribution(r11.topProperties().stream().map(p -> p.propertyType().name()).toList());
            long withEvidence = r11.topProperties().stream().filter(p -> p.amenityEvidence() != null && p.amenityEvidence().areaAmenityScore() != null).count();
            long wardLevel = r11.topProperties().stream().filter(p -> p.amenityEvidence() != null && "WARD".equals(p.amenityEvidence().areaLevel())).count();
            long districtLevel = r11.topProperties().stream().filter(p -> p.amenityEvidence() != null && "DISTRICT".equals(p.amenityEvidence().areaLevel())).count();
            long noEvidence = r11.topProperties().stream().filter(p -> p.amenityEvidence() == null || p.amenityEvidence().areaAmenityScore() == null).count();
            long violations = r11.topProperties().stream().filter(p -> p.priceVnd().compareTo(request.budgetVnd()) > 0).count();
            int overlap = overlap(ids1, ids11);
            var node = nodes.addObject();
            node.put("name", sc.name());
            node.put("budgetVnd", sc.budget());
            node.put("purpose", sc.purpose().name());
            node.put("propertyType", sc.type().name());
            node.put("eligibleCandidates", r11.eligibleCandidateCount());
            node.put("v1Ms", ms1);
            node.put("v11Ms", ms11);
            node.put("typeDistributionV1", typesV1);
            node.put("typeDistributionV11", typesV11);
            node.put("propertiesWithAmenityEvidence", withEvidence);
            node.put("wardLevelEvidence", wardLevel);
            node.put("districtLevelEvidence", districtLevel);
            node.put("noEvidence", noEvidence);
            node.put("top10Overlap", overlap);
            node.put("budgetViolations", violations);
            var a1 = node.putArray("v1Top10"); ids1.forEach(a1::add);
            var a11 = node.putArray("v11Top10"); ids11.forEach(a11::add);
            assertEquals(0, violations);
            csv.append(sc.name()).append(',').append(r11.eligibleCandidateCount()).append(',')
                .append(ms1).append(',').append(ms11).append(',')
                .append('"').append(typesV1).append('"').append(',').append('"').append(typesV11).append('"').append(',')
                .append(withEvidence).append(',').append(wardLevel).append(',').append(districtLevel).append(',')
                .append(noEvidence).append(',').append(overlap).append(',').append(violations).append('\n');
            System.out.println("BENCH-RESEARCH " + sc.name() + ": eligible=" + r11.eligibleCandidateCount()
                + " v1=" + ms1 + "ms v11=" + ms11 + "ms types(V1)=" + typesV1 + " types(V1.1)=" + typesV11
                + " evidence=" + withEvidence + "/10 (ward " + wardLevel + ", district " + districtLevel + ", none " + noEvidence + ")"
                + " overlap=" + overlap);
        }
        Files.writeString(OUT.resolve("benchmark_research_results.json"),
            MAPPER.writerWithDefaultPrettyPrinter().writeValueAsString(root), StandardCharsets.UTF_8);
        Files.writeString(OUT.resolve("ranking_comparison_research.csv"), csv.toString(), StandardCharsets.UTF_8);
    }

    static String typeDistribution(JsonNode response) {
        var counts = new TreeMap<String, Integer>();
        for (var p : response.path("topProperties")) counts.merge(p.path("propertyType").asText(), 1, Integer::sum);
        return counts.toString();
    }

    static String distribution(List<String> types) {
        var counts = new TreeMap<String, Integer>();
        for (var t : types) counts.merge(t, 1, Integer::sum);
        return counts.toString();
    }

    static int overlap(List<String> a, List<String> b) {
        var set = new HashSet<>(a);
        return (int) b.stream().filter(set::contains).count();
    }
}