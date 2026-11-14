package vn.smartprop.modules.recommendation;

import java.math.BigDecimal;
import java.nio.file.*;
import java.sql.ResultSet;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.invocation.InvocationOnMock;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static vn.smartprop.modules.recommendation.RecommendationDtos.*;

/**
 * Repository-level cache behaviour against a mocked JdbcTemplate: no database, no disk scan.
 * One unified answer inspects the SQL so stub ordering can never mask a production code path.
 */
class TinixRepositoryCacheTest {
    static final String REV = "ca3fedcbb089bf65f7e4cfb03316cce4bd0d779f";
    static final long FINGERPRINT = 424242L;
    static final long TOTAL = 13_340L; // above DIRECT_SQL_CAP so the snapshot path runs
    static final int PK_CHUNKS = 8;    // PK_SPLITS.length + 1

    /** Mutable knobs for the fake database. */
    static final class Db {
        int eligibleRows;
        long fingerprint = FINGERPRINT;
        List<String> holdoutGroups = List.of("some-held-group");
        final AtomicInteger rebuilds = new AtomicInteger();
        final AtomicInteger chunkCalls = new AtomicInteger();
        final AtomicInteger heldCalls = new AtomicInteger();
        Db(int rows) { this.eligibleRows = rows; }
    }

    static RowMapper<?> mapperOf(InvocationOnMock inv) {
        return inv.getArgument(1);
    }

    static ResultSet probeRow(Db db) throws Exception {
        ResultSet rs = mock(ResultSet.class);
        // Register the catch-all first: Mockito lets later stubs win, so the specific
        // column stubs below must be registered after it or they would be shadowed.
        when(rs.getLong(anyString())).thenReturn(TOTAL);
        when(rs.getLong("total_cnt")).thenReturn(TOTAL);
        when(rs.getLong("fp")).thenReturn(db.fingerprint);
        when(rs.getLong("budget_cnt")).thenReturn(TOTAL);
        return rs;
    }

    static Candidate candidate(int i) {
        String key = String.format("%064x", i);
        return new Candidate("tinix:" + key, "Nhà " + i, PropertyType.HOUSE,
                new BigDecimal("1750000000.00"), new BigDecimal("80.000000"), "Hải Châu", null,
                new Source("TINIX_AI", "TiniX AI — CC BY-NC 4.0", key, null),
                "HYBRID_ELIGIBLE_RESEARCH", "UNVERIFIED", String.format("%064x", 500_000 + i),
                true, false, List.of(), false);
    }

    static JdbcTemplate jdbc(Db db) {
        var jdbc = mock(JdbcTemplate.class);

        // JdbcTemplate exposes both (String, RowMapper, Object) and (String, RowMapper, Object...)
        // overloads; stub both so the probe answer is independent of which one Java picks.
        org.mockito.stubbing.Answer<Object> probeAnswer = inv -> {
            if (!inv.getArgument(0, String.class).contains("budget_cnt")) return null;
            return mapperOf(inv).mapRow(probeRow(db), 0);
        };
        when(jdbc.queryForObject(anyString(), any(RowMapper.class), any(Object.class)))
                .thenAnswer(probeAnswer);
        when(jdbc.queryForObject(anyString(), any(RowMapper.class), any(Object[].class)))
                .thenAnswer(probeAnswer);

        when(jdbc.query(anyString(), any(RowMapper.class), any(Object[].class)))
                .thenAnswer(inv -> {
                    String sql = inv.getArgument(0, String.class);
                    db.chunkCalls.incrementAndGet();
                    // Chunk 0 is the only range query without a lower bound; every rebuild
                    // runs it exactly once, so it is our "one rebuild happened" marker.
                    if (sql.contains("t.internal_id>=?")) return List.of();
                    db.rebuilds.incrementAndGet();
                    var out = new ArrayList<Candidate>(db.eligibleRows);
                    for (int i = 0; i < db.eligibleRows; i++) out.add(candidate(i));
                    return out;
                });

        when(jdbc.queryForList(anyString(), eq(String.class)))
                .thenAnswer(inv -> {
                    db.heldCalls.incrementAndGet();
                    return db.holdoutGroups;
                });
        return jdbc;
    }

    static Request request(long budget) {
        return new Request(BigDecimal.valueOf(budget), Purpose.LIVING, PropertyType.ALL, null, null, null, 10);
    }

    static long filesIn(Path dir) throws Exception {
        try (var s = Files.list(dir)) { return s.count(); }
    }

    // ------------------------------------------------------------------ tests

    @Test void cacheDisabledNeverWritesAFile(@TempDir Path dir) throws Exception {
        var db = new Db(50);
        var repo = new TinixCandidateRepository(jdbc(db), REV, false, dir.toString(), 128, 200_000, 720);

        var first = repo.find(request(5_000_000_000L));
        assertEquals(50, first.size());
        assertEquals(TinixCandidateRepository.SnapshotSource.REBUILT, repo.lastSnapshotSource());
        assertEquals(0, filesIn(dir), "cache disabled must not create any file");

        repo.find(request(5_000_000_000L));
        assertEquals(1, db.rebuilds.get(), "second call is served from memory");
    }

    @Test void cacheHitAfterEvictingMemoryAvoidsRebuild(@TempDir Path dir) throws Exception {
        var db = new Db(50);
        var repo = new TinixCandidateRepository(jdbc(db), REV, true, dir.toString(), 128, 200_000, 720);

        var first = repo.find(request(5_000_000_000L));
        assertEquals(TinixCandidateRepository.SnapshotSource.REBUILT, repo.lastSnapshotSource());
        assertEquals(1, db.rebuilds.get());
        assertEquals(1, filesIn(dir), "rebuild must publish exactly one cache file");

        repo.evictMemory(); // simulate a JVM restart
        var second = repo.find(request(5_000_000_000L));

        assertEquals(TinixCandidateRepository.SnapshotSource.DISK_CACHE, repo.lastSnapshotSource());
        assertEquals(1, db.rebuilds.get(), "cache hit must not scan clustered rows");
        assertEquals(first, second, "identical candidate list");
        assertTrue(repo.lastLoadMillis() >= 0);
    }

    @Test void changedHoldoutSetInvalidatesCache(@TempDir Path dir) {
        var db = new Db(40);
        var repo = new TinixCandidateRepository(jdbc(db), REV, true, dir.toString(), 128, 200_000, 720);
        repo.find(request(5_000_000_000L));
        repo.evictMemory();

        db.holdoutGroups = List.of("some-held-group", "a-new-held-group");
        var after = repo.find(request(5_000_000_000L));

        assertEquals(TinixCandidateRepository.SnapshotSource.REBUILT, repo.lastSnapshotSource(),
                "a changed protected-holdout set must invalidate the cache");
        assertEquals(2, db.rebuilds.get());
        assertEquals(40, after.size());
    }

    @Test void fingerprintDriftInvalidatesCache(@TempDir Path dir) {
        var db = new Db(30);
        var repo = new TinixCandidateRepository(jdbc(db), REV, true, dir.toString(), 128, 200_000, 720);
        repo.find(request(5_000_000_000L));
        repo.evictMemory();

        db.fingerprint = FINGERPRINT + 1; // ids or prices changed upstream
        repo.find(request(5_000_000_000L));

        assertEquals(TinixCandidateRepository.SnapshotSource.REBUILT, repo.lastSnapshotSource());
        assertEquals(2, db.rebuilds.get());
    }

    @Test void corruptCacheFallsBackToRebuild(@TempDir Path dir) throws Exception {
        var db = new Db(30);
        var repo = new TinixCandidateRepository(jdbc(db), REV, true, dir.toString(), 128, 200_000, 720);
        repo.find(request(5_000_000_000L));

        byte[] bytes = Files.readAllBytes(repo.cacheFile());
        bytes[TinixSnapshotCache.HEADER_BYTES + 5] ^= 0x7f; // flip a payload byte -> sha256 mismatch
        Files.write(repo.cacheFile(), bytes);

        repo.evictMemory();
        var result = repo.find(request(5_000_000_000L));

        assertEquals(TinixCandidateRepository.SnapshotSource.REBUILT, repo.lastSnapshotSource(),
                "a corrupt cache must never be served");
        assertEquals(30, result.size());
        assertEquals(2, db.rebuilds.get());
    }

    @Test void truncatedCacheFallsBackToRebuild(@TempDir Path dir) throws Exception {
        var db = new Db(25);
        var repo = new TinixCandidateRepository(jdbc(db), REV, true, dir.toString(), 128, 200_000, 720);
        repo.find(request(5_000_000_000L));

        byte[] bytes = Files.readAllBytes(repo.cacheFile());
        Files.write(repo.cacheFile(), Arrays.copyOf(bytes, bytes.length / 3));

        repo.evictMemory();
        var result = repo.find(request(5_000_000_000L));

        assertEquals(TinixCandidateRepository.SnapshotSource.REBUILT, repo.lastSnapshotSource());
        assertEquals(25, result.size());
    }

    @Test void expiredCacheIsRebuilt(@TempDir Path dir) throws Exception {
        var db = new Db(20);
        var repo = new TinixCandidateRepository(jdbc(db), REV, true, dir.toString(), 128, 200_000, 1);
        repo.find(request(5_000_000_000L));

        var loaded = TinixSnapshotCache.read(repo.cacheFile(), 128 * 1024 * 1024, 200_000);
        TinixSnapshotCache.write(repo.cacheFile(),
                loaded.meta().withCandidateCount(loaded.meta().candidateCount(),
                        System.currentTimeMillis() - 2L * 3600L * 1000L),
                loaded.candidates(), 128 * 1024 * 1024);

        repo.evictMemory();
        repo.find(request(5_000_000_000L));

        assertEquals(TinixCandidateRepository.SnapshotSource.REBUILT, repo.lastSnapshotSource(),
                "a cache older than the configured max age must be rebuilt");
    }

    @Test void concurrentColdRequestsRebuildOnlyOnce(@TempDir Path dir) throws Exception {
        var db = new Db(40);
        var repo = new TinixCandidateRepository(jdbc(db), REV, true, dir.toString(), 128, 200_000, 720);

        int threads = 8;
        var pool = Executors.newFixedThreadPool(threads);
        var start = new CountDownLatch(1);
        var done = new CountDownLatch(threads);
        var sizes = new ConcurrentLinkedQueue<Integer>();
        for (int i = 0; i < threads; i++) {
            pool.submit(() -> {
                try {
                    start.await();
                    sizes.add(repo.find(request(5_000_000_000L)).size());
                } catch (Exception e) {
                    sizes.add(-1);
                } finally {
                    done.countDown();
                }
            });
        }
        start.countDown();
        assertTrue(done.await(60, TimeUnit.SECONDS));
        pool.shutdownNow();

        assertEquals(1, db.rebuilds.get(), "exactly one rebuild under concurrent cold load");
        assertEquals(threads, sizes.size());
        assertTrue(sizes.stream().allMatch(s -> s == 40), "all callers see the same candidate count: " + sizes);
        assertEquals(PK_CHUNKS, db.chunkCalls.get(), "only one rebuild's worth of chunk queries");
    }

    @Test void legacyConstructorBehavesWithoutCache(@TempDir Path dir) {
        var db = new Db(10);
        var repo = new TinixCandidateRepository(jdbc(db), REV); // 2-arg == cache off
        assertFalse(repo.diskCacheEnabled());
        repo.find(request(5_000_000_000L));
        assertEquals(TinixCandidateRepository.SnapshotSource.REBUILT, repo.lastSnapshotSource());
    }

    @Test void cacheFileIsNamedAfterRevision(@TempDir Path dir) {
        var db = new Db(10);
        var repo = new TinixCandidateRepository(jdbc(db), REV, true, dir.toString(), 128, 200_000, 720);
        assertEquals("tinix-snapshot-" + REV + ".bin", repo.cacheFile().getFileName().toString());
    }
}
