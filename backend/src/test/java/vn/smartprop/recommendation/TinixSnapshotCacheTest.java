package vn.smartprop.recommendation;

import java.io.IOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;
import static vn.smartprop.recommendation.RecommendationDtos.*;

class TinixSnapshotCacheTest {
    private static final String REV = "ca3fedcbb089bf65f7e4cfb03316cce4bd0d779f";
    private static final int MAX_PAYLOAD = 64 * 1024 * 1024;
    private static final int MAX_CANDIDATES = 200_000;

    static Candidate candidate(int i) {
        String key = String.format("%064x", i);
        return new Candidate("tinix:" + key, "Nhà " + i + " Hải Châu", PropertyType.HOUSE,
                new BigDecimal("1750000000.00"), new BigDecimal("80.125000"), "Hải Châu", null,
                new Source("TINIX_AI", "TiniX AI — CC BY-NC 4.0", key, null),
                "HYBRID_ELIGIBLE_RESEARCH", "UNVERIFIED", String.format("%064x", 900000 + i),
                true, false, List.of(), false);
    }

    static List<Candidate> candidates(int n) {
        var list = new ArrayList<Candidate>(n);
        for (int i = 0; i < n; i++) list.add(candidate(i));
        return List.copyOf(list);
    }

    static TinixSnapshotCache.Meta meta(int n, long fingerprint, long holdout, long builtAt) {
        return new TinixSnapshotCache.Meta(REV, n, fingerprint, holdout, n, builtAt);
    }

    @Test void roundTripPreservesEveryFieldAndOrder(@TempDir Path dir) throws Exception {
        var rows = candidates(500);
        Path file = dir.resolve("snap.bin");
        TinixSnapshotCache.write(file, meta(rows.size(), 42L, 7L, 1_000L), rows, MAX_PAYLOAD);

        var loaded = TinixSnapshotCache.read(file, MAX_PAYLOAD, MAX_CANDIDATES);
        assertEquals(REV, loaded.meta().revision());
        assertEquals(42L, loaded.meta().fingerprint());
        assertEquals(7L, loaded.meta().holdoutHash());
        assertEquals(rows, loaded.candidates(), "candidate list must round-trip byte-for-byte and in order");
        assertTrue(loaded.payloadBytes() > 0);
    }

    @Test void unicodeTitlesAndNullWardSurvive(@TempDir Path dir) throws Exception {
        var row = new Candidate("tinix:" + "a".repeat(64), "Biệt thự Đà Nẵng – view biển 🌊",
                PropertyType.VILLA, new BigDecimal("5000000000.00"), new BigDecimal("150.5"),
                "Ngũ Hành Sơn", null, new Source("TINIX_AI", "TiniX AI — CC BY-NC 4.0", "a".repeat(64), null),
                "HYBRID_ELIGIBLE_RESEARCH", "UNVERIFIED", "b".repeat(64), true, false, List.of(), false);
        Path file = dir.resolve("u.bin");
        TinixSnapshotCache.write(file, meta(1, 1L, 1L, 1L), List.of(row), MAX_PAYLOAD);
        var loaded = TinixSnapshotCache.read(file, MAX_PAYLOAD, MAX_CANDIDATES);
        assertEquals(row, loaded.candidates().get(0));
        assertNull(loaded.candidates().get(0).ward());
    }

    @Test void truncatedFileIsRejected(@TempDir Path dir) throws Exception {
        var rows = candidates(200);
        Path file = dir.resolve("t.bin");
        TinixSnapshotCache.write(file, meta(rows.size(), 1L, 1L, 1L), rows, MAX_PAYLOAD);
        byte[] bytes = Files.readAllBytes(file);
        Files.write(file, Arrays.copyOf(bytes, bytes.length / 2));
        var ex = assertThrows(TinixSnapshotCache.InvalidCacheException.class,
                () -> TinixSnapshotCache.read(file, MAX_PAYLOAD, MAX_CANDIDATES));
        assertTrue(ex.getMessage().contains("size mismatch") || ex.getMessage().contains("truncated"),
                "unexpected message: " + ex.getMessage());
    }

    @Test void corruptedPayloadIsRejected(@TempDir Path dir) throws Exception {
        var rows = candidates(200);
        Path file = dir.resolve("c.bin");
        TinixSnapshotCache.write(file, meta(rows.size(), 1L, 1L, 1L), rows, MAX_PAYLOAD);
        byte[] bytes = Files.readAllBytes(file);
        int pos = TinixSnapshotCache.HEADER_BYTES + (bytes.length - TinixSnapshotCache.HEADER_BYTES) / 2;
        bytes[pos] ^= 0x5A;
        Files.write(file, bytes);
        var ex = assertThrows(TinixSnapshotCache.InvalidCacheException.class,
                () -> TinixSnapshotCache.read(file, MAX_PAYLOAD, MAX_CANDIDATES));
        assertTrue(ex.getMessage().contains("sha256"), "unexpected message: " + ex.getMessage());
    }

    @Test void corruptedHeaderRejected(@TempDir Path dir) throws Exception {
        var rows = candidates(10);
        Path file = dir.resolve("h.bin");
        TinixSnapshotCache.write(file, meta(rows.size(), 1L, 1L, 1L), rows, MAX_PAYLOAD);
        byte[] bytes = Files.readAllBytes(file);
        bytes[0] = 'X'; // break magic
        Files.write(file, bytes);
        var ex = assertThrows(TinixSnapshotCache.InvalidCacheException.class,
                () -> TinixSnapshotCache.read(file, MAX_PAYLOAD, MAX_CANDIDATES));
        assertTrue(ex.getMessage().contains("magic"));
    }

    @Test void unknownFormatVersionIsRejected(@TempDir Path dir) throws Exception {
        var rows = candidates(10);
        Path file = dir.resolve("v.bin");
        TinixSnapshotCache.write(file, meta(rows.size(), 1L, 1L, 1L), rows, MAX_PAYLOAD);
        byte[] bytes = Files.readAllBytes(file);
        bytes[8] = 0; bytes[9] = 0; bytes[10] = 0; bytes[11] = 99;
        Files.write(file, bytes);
        var ex = assertThrows(TinixSnapshotCache.InvalidCacheException.class,
                () -> TinixSnapshotCache.read(file, MAX_PAYLOAD, MAX_CANDIDATES));
        assertTrue(ex.getMessage().contains("format version"), "unexpected: " + ex.getMessage());
    }

    @Test void appendedBytesAreRejected(@TempDir Path dir) throws Exception {
        var rows = candidates(10);
        Path file = dir.resolve("a.bin");
        TinixSnapshotCache.write(file, meta(rows.size(), 1L, 1L, 1L), rows, MAX_PAYLOAD);
        Files.write(file, new byte[]{1, 2, 3}, StandardOpenOption.APPEND);
        var ex = assertThrows(TinixSnapshotCache.InvalidCacheException.class,
                () -> TinixSnapshotCache.read(file, MAX_PAYLOAD, MAX_CANDIDATES));
        assertTrue(ex.getMessage().contains("size mismatch"), "unexpected: " + ex.getMessage());
    }

    @Test void payloadTooLargeForBudgetIsRejected(@TempDir Path dir) throws Exception {
        var rows = candidates(400);
        Path file = dir.resolve("big.bin");
        TinixSnapshotCache.write(file, meta(rows.size(), 1L, 1L, 1L), rows, MAX_PAYLOAD);
        var ex = assertThrows(TinixSnapshotCache.InvalidCacheException.class,
                () -> TinixSnapshotCache.read(file, 128, MAX_CANDIDATES));
        assertTrue(ex.getMessage().contains("payload size out of range"), "unexpected: " + ex.getMessage());
    }

    @Test void candidateCountCeilingIsEnforced(@TempDir Path dir) throws Exception {
        var rows = candidates(50);
        Path file = dir.resolve("cap.bin");
        TinixSnapshotCache.write(file, meta(rows.size(), 1L, 1L, 1L), rows, MAX_PAYLOAD);
        var ex = assertThrows(TinixSnapshotCache.InvalidCacheException.class,
                () -> TinixSnapshotCache.read(file, MAX_PAYLOAD, 10));
        assertTrue(ex.getMessage().contains("candidate count out of range"), "unexpected: " + ex.getMessage());
    }

    @Test void emptyFileIsRejected(@TempDir Path dir) throws Exception {
        Path file = dir.resolve("empty.bin");
        Files.write(file, new byte[0]);
        assertThrows(TinixSnapshotCache.InvalidCacheException.class,
                () -> TinixSnapshotCache.read(file, MAX_PAYLOAD, MAX_CANDIDATES));
    }

    @Test void writeNeverLeavesPartialTargetOnFailure(@TempDir Path dir) throws Exception {
        var rows = candidates(100);
        Path file = dir.resolve("keep.bin");
        TinixSnapshotCache.write(file, meta(rows.size(), 1L, 1L, 1L), rows, MAX_PAYLOAD);
        byte[] original = Files.readAllBytes(file);

        // Meta/count mismatch makes write() fail before publishing.
        assertThrows(IOException.class,
                () -> TinixSnapshotCache.write(file, meta(rows.size() + 1, 2L, 2L, 2L), rows, MAX_PAYLOAD));

        assertArrayEquals(original, Files.readAllBytes(file), "previous good cache must survive a failed write");
        try (var stream = Files.list(dir)) {
            assertEquals(1, stream.count(), "no leftover temp files");
        }
    }

    @Test void payloadOversizeAbortsWithoutPublishing(@TempDir Path dir) throws Exception {
        var rows = candidates(300);
        Path file = dir.resolve("oversize.bin");
        assertThrows(IOException.class,
                () -> TinixSnapshotCache.write(file, meta(rows.size(), 1L, 1L, 1L), rows, 32));
        assertFalse(Files.exists(file), "no cache file may be published when the payload exceeds the budget");
        try (var stream = Files.list(dir)) {
            assertEquals(0, stream.count(), "temp file must be cleaned up");
        }
    }

    @Test void holdoutHashIsOrderIndependentAndSensitive() {
        var a = List.of("g1", "g2", "g3");
        var b = List.of("g3", "g1", "g2");
        assertEquals(TinixSnapshotCache.holdoutHash(a), TinixSnapshotCache.holdoutHash(b));
        assertNotEquals(TinixSnapshotCache.holdoutHash(a), TinixSnapshotCache.holdoutHash(List.of("g1", "g2")));
        assertNotEquals(TinixSnapshotCache.holdoutHash(a), TinixSnapshotCache.holdoutHash(List.of("g1", "g2", "g4")));
    }

    @Test void concurrentReadsOfOneFileAreSafe(@TempDir Path dir) throws Exception {
        var rows = candidates(2000);
        Path file = dir.resolve("conc.bin");
        TinixSnapshotCache.write(file, meta(rows.size(), 1L, 1L, 1L), rows, MAX_PAYLOAD);

        int threads = 8;
        var pool = Executors.newFixedThreadPool(threads);
        var failures = new AtomicInteger();
        var start = new CountDownLatch(1);
        var done = new CountDownLatch(threads);
        for (int i = 0; i < threads; i++) {
            pool.submit(() -> {
                try {
                    start.await();
                    for (int k = 0; k < 5; k++) {
                        var loaded = TinixSnapshotCache.read(file, MAX_PAYLOAD, MAX_CANDIDATES);
                        if (!loaded.candidates().equals(rows)) failures.incrementAndGet();
                    }
                } catch (Exception e) {
                    failures.incrementAndGet();
                } finally {
                    done.countDown();
                }
            });
        }
        start.countDown();
        assertTrue(done.await(60, TimeUnit.SECONDS), "reads did not finish");
        pool.shutdownNow();
        assertEquals(0, failures.get());
    }

    @Test void concurrentWritesLeaveAValidFile(@TempDir Path dir) throws Exception {
        var rows = candidates(300);
        Path file = dir.resolve("w.bin");
        int threads = 4;
        var pool = Executors.newFixedThreadPool(threads);
        var start = new CountDownLatch(1);
        var done = new CountDownLatch(threads);
        for (int i = 0; i < threads; i++) {
            pool.submit(() -> {
                try {
                    start.await();
                    TinixSnapshotCache.write(file, meta(rows.size(), 1L, 1L, 1L), rows, MAX_PAYLOAD);
                } catch (Exception ignored) {
                    // Losing a race is acceptable; the published file must still be valid.
                } finally {
                    done.countDown();
                }
            });
        }
        start.countDown();
        assertTrue(done.await(60, TimeUnit.SECONDS));
        pool.shutdownNow();
        var loaded = TinixSnapshotCache.read(file, MAX_PAYLOAD, MAX_CANDIDATES);
        assertEquals(rows, loaded.candidates());
    }
}
