package vn.smartprop.modules.recommendation;

import java.io.IOException;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;
import static vn.smartprop.modules.recommendation.RecommendationDtos.*;

/** Dataset rows are research observations, never public live advertisements. */
@Repository
public class TinixCandidateRepository {
    private static final Logger log = LoggerFactory.getLogger(TinixCandidateRepository.class);

    static final int DIRECT_SQL_CAP = 2500;
    private static final String[] PK_SPLITS = {"2", "4", "6", "8", "a", "c", "e"};
    private static final RowMapper<Candidate> ROW_MAPPER = (rs, n) -> new Candidate(
        "tinix:" + rs.getString("internal_id"),
        rs.getString("name"),
        PropertyType.valueOf(rs.getString("normalized_type")),
        rs.getBigDecimal("price_vnd"),
        rs.getBigDecimal("area_sqm"),
        rs.getString("district"),
        rs.getString("ward"),
        new Source("TINIX_AI", "TiniX AI — CC BY-NC 4.0", rs.getString("internal_id"), null),
        "HYBRID_ELIGIBLE_RESEARCH",
        "UNVERIFIED",
        rs.getString("duplicate_group"),
        true,
        false,
        List.of(),
        false
    );

    private record IndexProbe(long totalCount, long fingerprint, long budgetCount) {}
    private record Snapshot(String revision, long totalCount, long fingerprint, long holdoutHash,
                            List<Candidate> all) {}

    /** Where the current snapshot came from. Exposed for diagnostics/tests only. */
    public enum SnapshotSource { MEMORY, DISK_CACHE, REBUILT, NONE }

    private final JdbcTemplate jdbc;
    private final String revision;
    private final boolean diskCacheEnabled;
    private final Path cacheFile;
    private final int cacheMaxPayloadBytes;
    private final int cacheMaxCandidates;
    private final long cacheMaxAgeSeconds;

    private volatile Snapshot cached;
    private volatile SnapshotSource lastSource = SnapshotSource.NONE;
    private volatile long lastLoadMillis;
    private volatile long lastPayloadBytes;

    @org.springframework.beans.factory.annotation.Autowired
    public TinixCandidateRepository(JdbcTemplate jdbc,
            @Value("${app.recommendation.tinix-revision:ca3fedcbb089bf65f7e4cfb03316cce4bd0d779f}") String revision,
            @Value("${app.recommendation.tinix-disk-cache-enabled:true}") boolean diskCacheEnabled,
            @Value("${app.recommendation.tinix-disk-cache-dir:var/recommendation}") String cacheDir,
            @Value("${app.recommendation.tinix-disk-cache-max-payload-mb:128}") int maxPayloadMb,
            @Value("${app.recommendation.tinix-disk-cache-max-candidates:120000}") int maxCandidates,
            @Value("${app.recommendation.tinix-disk-cache-max-age-hours:720}") long maxAgeHours) {
        this.jdbc = jdbc;
        this.revision = revision;
        this.diskCacheEnabled = diskCacheEnabled;
        this.cacheFile = Path.of(cacheDir, "tinix-snapshot-" + revision + ".bin");
        this.cacheMaxPayloadBytes = Math.max(1, maxPayloadMb) * 1024 * 1024;
        this.cacheMaxCandidates = Math.max(1, maxCandidates);
        this.cacheMaxAgeSeconds = Math.max(1, maxAgeHours) * 3600L;
    }

    /**
     * Backwards-compatible constructor: no disk cache, exactly the pre-19.4.3A behaviour.
     * Existing tests and any programmatic wiring keep working unchanged.
     */
    TinixCandidateRepository(JdbcTemplate jdbc, String revision) {
        this(jdbc, revision, false, "var/recommendation", 128, 120_000, 720);
    }

    public List<Candidate> find(Request r) {
        // Hard budget and eligibility checks happen in SQL and again in service.
        // Only the representative of a fully unprotected suspicion group passes.
        // Live covering-index probe verifies current MySQL state and counts budget matches without clustered I/O.
        var probe = jdbc.queryForObject("""
            SELECT COUNT(*) AS total_cnt,
                   COALESCE(BIT_XOR(CRC32(CONCAT_WS('|',internal_id,price_vnd))),0) AS fp,
                   COALESCE(SUM(price_vnd<=?),0) AS budget_cnt
            FROM tinix_dataset_records FORCE INDEX (ix_tinix_hybrid)
            WHERE quality_status='HYBRID_ELIGIBLE_RESEARCH'
              AND is_duplicate_representative=1
              AND is_protected_holdout=0
              AND transaction_type='SALE'
              AND price_vnd>0
            """, (rs, n) -> new IndexProbe(rs.getLong("total_cnt"), rs.getLong("fp"), rs.getLong("budget_cnt")),
            r.budgetVnd());
        if (probe == null || probe.budgetCount() == 0) return List.of();

        Snapshot snap = this.cached;
        if (isCurrent(snap, probe)) {
            lastSource = SnapshotSource.MEMORY;
            return filterInMemory(snap.all(), r);
        }

        if (probe.budgetCount() <= DIRECT_SQL_CAP) {
            // Narrow queries are cheap and always reflect live rows, so they never consult the cache.
            lastSource = SnapshotSource.NONE;
            return querySortedPk(r);
        }

        snap = loadSnapshot(probe.totalCount(), probe.fingerprint());
        return filterInMemory(snap.all(), r);
    }

    private boolean isCurrent(Snapshot snap, IndexProbe probe) {
        return snap != null && snap.revision().equals(revision)
                && snap.totalCount() == probe.totalCount() && snap.fingerprint() == probe.fingerprint();
    }

    /**
     * Returns a validated snapshot, loading it from the disk cache when possible.
     *
     * <p>{@code synchronized} so concurrent cold requests trigger exactly one rebuild; the losers
     * then observe the finished snapshot and return immediately.
     */
    private synchronized Snapshot loadSnapshot(long totalCount, long fingerprint) {
        Snapshot snap = this.cached;
        if (snap != null && snap.revision().equals(revision)
                && snap.totalCount() == totalCount && snap.fingerprint() == fingerprint) {
            return snap;
        }
        long started = System.nanoTime();

        Set<String> heldGroups = loadHeldGroups();
        long holdoutHash = TinixSnapshotCache.holdoutHash(heldGroups);

        if (diskCacheEnabled) {
            var fromDisk = tryReadCache(totalCount, fingerprint, holdoutHash);
            if (fromDisk != null) {
                this.cached = fromDisk;
                this.lastSource = SnapshotSource.DISK_CACHE;
                this.lastLoadMillis = (System.nanoTime() - started) / 1_000_000L;
                log.info("TiniX snapshot loaded from disk cache: {} candidates in {} ms ({})",
                        fromDisk.all().size(), lastLoadMillis, cacheFile);
                return fromDisk;
            }
        }

        List<Candidate> all = rebuild(totalCount, heldGroups);
        snap = new Snapshot(revision, totalCount, fingerprint, holdoutHash, List.copyOf(all));
        this.cached = snap;
        this.lastSource = SnapshotSource.REBUILT;
        this.lastLoadMillis = (System.nanoTime() - started) / 1_000_000L;
        log.info("TiniX snapshot rebuilt from MySQL: {} candidates in {} ms",
                snap.all().size(), lastLoadMillis);

        if (diskCacheEnabled) writeCache(snap, started);
        return snap;
    }

    private Set<String> loadHeldGroups() {
        return new HashSet<>(jdbc.queryForList("""
            SELECT DISTINCT h.duplicate_group
            FROM tinix_dataset_records h FORCE INDEX (ix_tinix_hybrid)
            WHERE h.quality_status IN ('HYBRID_ELIGIBLE_RESEARCH','NEEDS_REVIEW','EXCLUDED')
              AND h.is_duplicate_representative IN (0,1)
              AND h.is_protected_holdout=1
            """, String.class));
    }

    private Snapshot tryReadCache(long totalCount, long fingerprint, long holdoutHash) {
        if (!Files.isRegularFile(cacheFile)) return null;
        try {
            var loaded = TinixSnapshotCache.read(cacheFile, cacheMaxPayloadBytes, cacheMaxCandidates);
            var meta = loaded.meta();
            String rejection = validateMeta(meta, totalCount, fingerprint, holdoutHash);
            if (rejection != null) {
                log.warn("TiniX disk cache rejected ({}): {}", rejection, cacheFile);
                return null;
            }
            long ageSeconds = Math.max(0, (System.currentTimeMillis() - meta.builtAtEpochMillis()) / 1000L);
            if (ageSeconds > cacheMaxAgeSeconds) {
                log.warn("TiniX disk cache too old ({} s > {} s): {}; rebuilding", ageSeconds,
                        cacheMaxAgeSeconds, cacheFile);
                return null;
            }
            if (meta.candidateCount() != totalCount && meta.candidateCount() <= 0) {
                log.warn("TiniX disk cache is empty but probe reports {} candidates; rebuilding", totalCount);
                return null;
            }
            this.lastPayloadBytes = loaded.payloadBytes();
            return new Snapshot(meta.revision(), meta.totalCount(), meta.fingerprint(), meta.holdoutHash(),
                    loaded.candidates());
        } catch (TinixSnapshotCache.InvalidCacheException e) {
            log.warn("TiniX disk cache unusable ({}): {}; falling back to a full rebuild", e.getMessage(), cacheFile);
            return null;
        } catch (RuntimeException e) {
            log.warn("TiniX disk cache threw while loading: {}; falling back to a full rebuild", e.toString());
            return null;
        }
    }

    private String validateMeta(TinixSnapshotCache.Meta meta, long totalCount, long fingerprint, long holdoutHash) {
        if (!revision.equals(meta.revision())) return "revision " + meta.revision() + " != " + revision;
        if (meta.totalCount() != totalCount) return "totalCount " + meta.totalCount() + " != " + totalCount;
        if (meta.fingerprint() != fingerprint) return "fingerprint drift (ids/prices changed)";
        if (meta.holdoutHash() != holdoutHash) return "protected holdout set changed";
        return null;
    }

    private void writeCache(Snapshot snap, long loadStartedNanos) {
        long started = System.nanoTime();
        try {
            var meta = new TinixSnapshotCache.Meta(revision, snap.totalCount(), snap.fingerprint(),
                    snap.holdoutHash(), snap.all().size(), System.currentTimeMillis());
            TinixSnapshotCache.write(cacheFile, meta, snap.all(), cacheMaxPayloadBytes);
            long size = Files.size(cacheFile);
            log.info("TiniX disk cache written: {} bytes in {} ms (snapshot built in {} ms)",
                    size, (System.nanoTime() - started) / 1_000_000L,
                    (loadStartedNanos == 0 ? -1 : (System.nanoTime() - loadStartedNanos) / 1_000_000L));
        } catch (IOException | RuntimeException e) {
            log.warn("TiniX disk cache could not be written ({}); serving from memory only", e.toString());
        }
    }

    private List<Candidate> rebuild(long totalCount, Set<String> heldGroups) {
        var all = new ArrayList<Candidate>((int) Math.min(totalCount, 100_000));
        for (int i = 0; i <= PK_SPLITS.length; i++) {
            String rangeClause = i == 0 ? "t.internal_id<?"
                : (i == PK_SPLITS.length ? "t.internal_id>=?" : "t.internal_id>=? AND t.internal_id<?");
            Object[] args = i == 0 ? new Object[]{PK_SPLITS[0], revision}
                : (i == PK_SPLITS.length ? new Object[]{PK_SPLITS[PK_SPLITS.length - 1], revision}
                : new Object[]{PK_SPLITS[i - 1], PK_SPLITS[i], revision});
            var chunk = jdbc.query("""
                SELECT t.internal_id,t.name,t.normalized_type,t.price_vnd,t.area_sqm,t.district,t.ward,t.duplicate_group
                FROM tinix_dataset_records t FORCE INDEX (PRIMARY)
                WHERE """ + " " + rangeClause + """
                  AND t.dataset_revision=? AND t.source_name='TINIX_AI'
                  AND t.quality_status='HYBRID_ELIGIBLE_RESEARCH' AND JSON_LENGTH(t.quality_issues)=0
                  AND t.verification_status='UNVERIFIED' AND t.research_only=1 AND t.listing_availability='UNKNOWN'
                  AND t.transaction_type='SALE' AND t.transaction_basis='EXPLICIT_SALE_TEXT'
                  AND t.is_protected_holdout=0 AND t.is_duplicate_representative=1
                  AND t.price_vnd>0 AND t.area_sqm>0
                ORDER BY t.internal_id
                """, ROW_MAPPER, args);
            for (var c : chunk) {
                if (!heldGroups.contains(c.duplicateGroup())) all.add(c);
            }
        }
        return all;
    }

    private List<Candidate> querySortedPk(Request r) {
        var minArea = r.minAreaSqm() == null ? BigDecimal.ZERO : r.minAreaSqm();
        String dist = blank(r.district()), ward = blank(r.ward());
        return jdbc.query("""
            SELECT t.internal_id,t.name,t.normalized_type,t.price_vnd,t.area_sqm,t.district,t.ward,t.duplicate_group
            FROM (
              SELECT k.internal_id
              FROM tinix_dataset_records k FORCE INDEX (ix_tinix_hybrid)
              WHERE k.quality_status='HYBRID_ELIGIBLE_RESEARCH'
                AND k.is_duplicate_representative=1
                AND k.is_protected_holdout=0
                AND k.transaction_type='SALE'
                AND k.price_vnd>0 AND k.price_vnd<=?
              ORDER BY k.internal_id
            ) ids
            STRAIGHT_JOIN tinix_dataset_records t ON t.internal_id=ids.internal_id
            LEFT JOIN (
              SELECT DISTINCT h.duplicate_group
              FROM tinix_dataset_records h FORCE INDEX (ix_tinix_hybrid)
              WHERE h.quality_status IN ('HYBRID_ELIGIBLE_RESEARCH','NEEDS_REVIEW','EXCLUDED')
                AND h.is_duplicate_representative IN (0,1)
                AND h.is_protected_holdout=1
            ) held ON held.duplicate_group=t.duplicate_group
            WHERE t.dataset_revision=? AND t.source_name='TINIX_AI'
              AND t.quality_status='HYBRID_ELIGIBLE_RESEARCH' AND JSON_LENGTH(t.quality_issues)=0
              AND t.verification_status='UNVERIFIED' AND t.research_only=1 AND t.listing_availability='UNKNOWN'
              AND t.transaction_type='SALE' AND t.transaction_basis='EXPLICIT_SALE_TEXT'
              AND t.is_protected_holdout=0 AND t.is_duplicate_representative=1
              AND held.duplicate_group IS NULL
              AND t.price_vnd>0 AND t.price_vnd<=? AND t.area_sqm>0 AND t.area_sqm>=?
              AND (?='ALL' OR t.normalized_type=?)
              AND (? IS NULL OR t.district=?) AND (? IS NULL OR t.ward=?)
            ORDER BY t.internal_id
            """, ROW_MAPPER,
            r.budgetVnd(), revision, r.budgetVnd(), minArea,
            r.propertyType().name(), r.propertyType().name(),
            dist, dist, ward, ward);
    }

    private static List<Candidate> filterInMemory(List<Candidate> all, Request r) {
        var minArea = r.minAreaSqm() == null ? BigDecimal.ZERO : r.minAreaSqm();
        String dist = blank(r.district()), ward = blank(r.ward());
        String normDist = dist == null ? null : HybridRecommendationService.normalize(dist);
        String normWard = ward == null ? null : HybridRecommendationService.normalize(ward);
        var out = new ArrayList<Candidate>();
        for (var c : all) {
            if (c.price().compareTo(r.budgetVnd()) > 0 || c.area().compareTo(minArea) < 0) continue;
            if (r.propertyType() != PropertyType.ALL && c.type() != r.propertyType()) continue;
            if (normDist != null && (c.district() == null || !normDist.equals(HybridRecommendationService.normalize(c.district())))) continue;
            if (normWard != null && (c.ward() == null || !normWard.equals(HybridRecommendationService.normalize(c.ward())))) continue;
            out.add(c);
        }
        return out;
    }

    private static String blank(String s) { return s == null || s.isBlank() ? null : s.strip(); }

    // ------------------------------------------------------------ diagnostics

    public SnapshotSource lastSnapshotSource() { return lastSource; }
    public long lastLoadMillis() { return lastLoadMillis; }
    public long lastPayloadBytes() { return lastPayloadBytes; }
    public boolean diskCacheEnabled() { return diskCacheEnabled; }
    public Path cacheFile() { return cacheFile; }
    /** Drops the in-memory snapshot (used by tests to simulate a JVM restart within one JVM). */
    public synchronized void evictMemory() { this.cached = null; this.lastSource = SnapshotSource.NONE; }
}
