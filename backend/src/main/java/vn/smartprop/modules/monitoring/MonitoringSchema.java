package vn.smartprop.modules.monitoring;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;

import static vn.smartprop.modules.monitoring.TrustedOrigin.Surface;

/** Fixed Spring-only projection of the accepted WP06 v3 wire registry. */
public final class MonitoringSchema {
    public static final int VERSION = 3;
    public static final int WINDOW_SECONDS = 60;
    public static final long MAX_UTC = 4_102_444_800L;
    public static final long MAX_VALUE = (1L << 53) - 1;
    public static final long MAX_DURATION_US = 3_600_000_000L;

    public enum Kind { SURFACE, OPPORTUNITY, CANDIDATE, DISPATCH }
    public enum Outcome {
        SERVED, NO_POINT, VALIDATION_REJECTION, TIMEOUT, CANCELLED, DEPENDENCY_UNAVAILABLE,
        FAILED, INTERRUPTED, VALID_POINT, CACHE_HIT, SKIP, ELIGIBLE, AI_RESPONSE
    }
    public enum Retry { TRANSPORT, AUTH }
    public enum Skip { OPT_OUT, RESEARCH, UNSUPPORTED, INCOMPLETE }
    public enum Cache { HIT, MISS, ERROR }
    public enum Probe { HEALTH, OPTIONS }
    public enum Readiness { READY, NOT_READY, FAILED }
    public enum Drop {
        INVALID, NUMERIC_OVERFLOW, LOCK_BUSY, ACTIVE_LIMIT, QUEUE_FULL,
        BATCH_REJECTED, CLOCK_DISCONTINUITY, MONITOR_FAULT
    }

    private static final long[] EDGES = {
            10_000, 25_000, 50_000, 100_000, 200_000, 500_000, 1_000_000, 5_000_000, 15_000_000
    };
    static final int BUCKETS = EDGES.length + 1;
    private static final int HISTOGRAM_SLOTS = BUCKETS + 2;
    private static final int WIRE_SURFACES = 3;

    private static final Map<Kind, List<Outcome>> OUTCOMES = Map.of(
            Kind.SURFACE, List.of(Outcome.SERVED, Outcome.NO_POINT, Outcome.VALIDATION_REJECTION, Outcome.TIMEOUT,
                    Outcome.CANCELLED, Outcome.DEPENDENCY_UNAVAILABLE, Outcome.FAILED, Outcome.INTERRUPTED),
            Kind.OPPORTUNITY, List.of(Outcome.VALID_POINT, Outcome.CACHE_HIT, Outcome.SKIP, Outcome.VALIDATION_REJECTION,
                    Outcome.TIMEOUT, Outcome.CANCELLED, Outcome.DEPENDENCY_UNAVAILABLE, Outcome.FAILED, Outcome.INTERRUPTED),
            Kind.CANDIDATE, List.of(Outcome.ELIGIBLE, Outcome.SKIP, Outcome.INTERRUPTED),
            Kind.DISPATCH, List.of(Outcome.AI_RESPONSE, Outcome.TIMEOUT, Outcome.CANCELLED,
                    Outcome.DEPENDENCY_UNAVAILABLE, Outcome.FAILED, Outcome.INTERRUPTED));

    record Life(int started, int completed, int lost, int active, int opening,
                Map<Outcome, Integer> outcomes, int histogram) {}

    private static final Map<Kind, Map<Surface, Life>> LIFECYCLES;
    private static final int RETRY_BASE;
    private static final int SKIP_BASE;
    private static final int CACHE_BASE;
    private static final int PROBE_BASE;
    static final int DROP_BASE;
    static final int DUPLICATES;
    private static final int[] WIRE_BY_SLOT;
    private static final List<Integer> WIRE_ORDER;

    static {
        var wires = new ArrayList<Integer>();
        var kinds = new EnumMap<Kind, Map<Surface, Life>>(Kind.class);
        int family = 0;
        for (Kind kind : Kind.values()) {
            var surfaces = new EnumMap<Surface, Life>(Surface.class);
            var outcomes = OUTCOMES.get(kind);
            int width = outcomes.size();
            for (Surface surface : Surface.values()) {
                int i = surface.ordinal();
                int started = slot(wires, surface, family + i);
                int completed = slot(wires, surface, family + 3 + i);
                int lost = slot(wires, surface, family + 6 + i);
                var terminals = new EnumMap<Outcome, Integer>(Outcome.class);
                for (int j = 0; j < width; j++) {
                    terminals.put(outcomes.get(j), slot(wires, surface, family + 9 + i * width + j));
                }
                int active = slot(wires, surface, family + 9 + 3 * width + i);
                int opening = slot(wires, surface, family + 12 + 3 * width + i);
                int histogram = wires.size();
                for (int j = 0; j < HISTOGRAM_SLOTS; j++) {
                    slot(wires, surface, family + 15 + 3 * width + i * HISTOGRAM_SLOTS + j);
                }
                surfaces.put(surface, new Life(started, completed, lost, active, opening, Map.copyOf(terminals), histogram));
            }
            kinds.put(kind, Map.copyOf(surfaces));
            family += WIRE_SURFACES * (5 + width + HISTOGRAM_SLOTS);
        }
        LIFECYCLES = Map.copyOf(kinds);
        // v3 reserves 282–387 for Python invocation/API families. Spring cannot emit those.
        DROP_BASE = wires.size();
        for (Drop reason : Drop.values()) {
            wires.add(388 + reason.ordinal());
        }
        DUPLICATES = wires.size();
        wires.add(396);
        RETRY_BASE = additional(wires, 397, Retry.values().length);
        SKIP_BASE = additional(wires, 403, Skip.values().length);
        CACHE_BASE = additional(wires, 415, Cache.values().length);
        PROBE_BASE = additional(wires, 424, Probe.values().length * Readiness.values().length);
        WIRE_BY_SLOT = wires.stream().mapToInt(Integer::intValue).toArray();
        var order = new ArrayList<Integer>();
        for (int i = 0; i < WIRE_BY_SLOT.length; i++) {
            if (WIRE_BY_SLOT[i] >= 0) {
                order.add(i);
            }
        }
        order.sort((left, right) -> Integer.compare(WIRE_BY_SLOT[left], WIRE_BY_SLOT[right]));
        WIRE_ORDER = List.copyOf(order);
    }

    private MonitoringSchema() {}

    private static int slot(List<Integer> wires, Surface surface, int wire) {
        int local = wires.size();
        wires.add(surface == Surface.UNATTRIBUTED ? -1 : wire);
        return local;
    }

    private static int additional(List<Integer> wires, int wire, int width) {
        int base = wires.size();
        for (Surface surface : Surface.values()) {
            for (int i = 0; i < width; i++) {
                slot(wires, surface, wire + surface.ordinal() * width + i);
            }
        }
        return base;
    }

    public static int slots() {
        return WIRE_BY_SLOT.length;
    }

    static int wireSlot(int local) {
        return WIRE_BY_SLOT[local];
    }

    static List<Integer> wireOrder() {
        return WIRE_ORDER;
    }

    static Life life(Kind kind, Surface surface) {
        return LIFECYCLES.get(kind).get(surface);
    }

    static int retry(Surface surface, Retry reason) {
        return RETRY_BASE + surface.ordinal() * Retry.values().length + reason.ordinal();
    }

    static int skip(Surface surface, Skip reason) {
        return SKIP_BASE + surface.ordinal() * Skip.values().length + reason.ordinal();
    }

    static int cache(Surface surface, Cache result) {
        return CACHE_BASE + surface.ordinal() * Cache.values().length + result.ordinal();
    }

    static int probe(Surface surface, Probe probe, Readiness result) {
        int width = Readiness.values().length;
        return PROBE_BASE + surface.ordinal() * Probe.values().length * width + probe.ordinal() * width + result.ordinal();
    }

    static int bucket(long micros) {
        int index = 0;
        while (index < EDGES.length && micros > EDGES[index]) {
            index++;
        }
        return index;
    }

    static long edge(int bin) {
        return EDGES[bin];
    }

    static boolean boundary(long utc) {
        return utc >= 0 && utc <= MAX_UTC && utc % WINDOW_SECONDS == 0;
    }
}
