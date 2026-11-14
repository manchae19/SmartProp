package vn.smartprop.modules.recommendation;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import vn.smartprop.modules.amenity.AmenityCatalogService;
import vn.smartprop.modules.recommendation.RecommendationDtos.*;

import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Cold vs warm latency probe for the large-budget path.
 *
 * <p>V1 and V1.1 share {@link TinixCandidateRepository}, whose snapshot is loaded once when the
 * eligible budget set exceeds 2500 rows. This test measures that cost explicitly instead of
 * attributing it to a scoring change.
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
class HybridV11LatencyProbeTest {
    static final Path OUT = Path.of("..", ".scratch", "tinix-integration", "step19-4-2");

    @DynamicPropertySource static void local(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", () -> "jdbc:mysql://127.0.0.1:3306/smartprop?connectionTimeZone=UTC");
        r.add("spring.datasource.username", () -> Objects.requireNonNull(System.getenv("DB_USER")));
        r.add("spring.datasource.password", () -> Objects.requireNonNull(System.getenv("DB_PASSWORD")));
        r.add("app.jwt-secret", () -> UUID.randomUUID().toString() + UUID.randomUUID());
        r.add("app.recommendation.demo-key", () -> "");
    }

    @Autowired JdbcTemplate jdbc;
    @Autowired AmenityCatalogService catalog;

    @Test void coldSnapshotLoadAndWarmRequests() throws Exception {
        var repo = new RecommendationCandidateRepository(jdbc, new com.fasterxml.jackson.databind.ObjectMapper());
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

        var lines = new ArrayList<String>();
        lines.add("path,cold_ms,p50_warm_ms,p95_warm_ms,heap_after_mb");
        long baseline = Runtime.getRuntime().totalMemory() - Runtime.getRuntime().freeMemory();

        for (var budget : List.of(5_000_000_000L, 20_000_000_000L, 60_000_000_000L)) {
            var request = new Request(BigDecimal.valueOf(budget), Purpose.LIVING, PropertyType.ALL, null, null, null, 10);
            long t0 = System.nanoTime();
            var cold = v11.recommendResearch(request);
            long coldMs = (System.nanoTime() - t0) / 1_000_000;
            var warm = new ArrayList<Long>();
            for (int i = 0; i < 8; i++) {
                t0 = System.nanoTime();
                v11.recommendResearch(request);
                warm.add((System.nanoTime() - t0) / 1_000_000);
            }
            Collections.sort(warm);
            long p50 = warm.get(warm.size() / 2);
            long p95 = warm.get((int) Math.ceil(warm.size() * 0.95) - 1);
            long heap = (Runtime.getRuntime().totalMemory() - Runtime.getRuntime().freeMemory() - baseline) / (1024 * 1024);
            lines.add("V1.1-research@" + budget + "," + coldMs + "," + p50 + "," + p95 + "," + heap);
            System.out.println("PROBE V1.1 budget=" + budget + " cold=" + coldMs + "ms p50=" + p50 + "ms p95=" + p95
                + "ms heapDelta=" + heap + "MB candidates=" + cold.eligibleCandidateCount());

            t0 = System.nanoTime();
            v1.recommendResearch(request);
            long v1Warm = (System.nanoTime() - t0) / 1_000_000;
            lines.add("V1-research@" + budget + ",-," + v1Warm + ",-,-");
            System.out.println("PROBE V1   budget=" + budget + " warm=" + v1Warm + "ms");
        }

        // Public SAFE path never touches the TiniX snapshot.
        var safeRequest = new Request(BigDecimal.valueOf(5_000_000_000L), Purpose.LIVING, PropertyType.ALL, null, null, null, 10);
        long t0 = System.nanoTime();
        v11.recommend(safeRequest);
        long safeCold = (System.nanoTime() - t0) / 1_000_000;
        var safeWarm = new ArrayList<Long>();
        for (int i = 0; i < 8; i++) {
            t0 = System.nanoTime();
            v11.recommend(safeRequest);
            safeWarm.add((System.nanoTime() - t0) / 1_000_000);
        }
        Collections.sort(safeWarm);
        lines.add("V1.1-safe@" + 5_000_000_000L + "," + safeCold + ","
            + safeWarm.get(safeWarm.size() / 2) + "," + safeWarm.get(safeWarm.size() - 1) + ",0");
        System.out.println("PROBE V1.1 SAFE cold=" + safeCold + "ms p50=" + safeWarm.get(safeWarm.size() / 2) + "ms");

        Files.writeString(OUT.resolve("latency_probe.csv"), String.join("\n", lines), StandardCharsets.UTF_8);
    }
}