package vn.smartprop.modules.monitoring;

import java.util.ArrayList;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLongArray;
import java.util.concurrent.locks.ReentrantLock;
import java.util.function.LongSupplier;

import static vn.smartprop.modules.monitoring.MonitoringSchema.*;
import static vn.smartprop.modules.monitoring.TrustedOrigin.*;

/** An opt-in, process-local recorder. No Spring bean, scheduler, transport, or prediction calls. */
public final class SpringTelemetry {
    public static final int MAX_ACTIVE = 1024;
    private static final int MAX_TICKET_AGE_SECONDS = 10 * WINDOW_SECONDS;
    private static final int OPEN = 0;
    private static final int FINISHING = 1;
    private static final int LOST = 2;
    private static final int CLOSED = 3;

    private static final class State {
        final ReentrantLock lock;
        final LongSupplier clock;
        final Object owner = new Object();
        final IdentityHashMap<Ticket, Boolean> active = new IdentityHashMap<>(MAX_ACTIVE);
        final AtomicLongArray health = new AtomicLongArray(Drop.values().length + 1);
        long[] cells = new long[slots()];
        long start;

        State(long start, LongSupplier clock, ReentrantLock lock) {
            this.start = start;
            this.clock = clock;
            this.lock = lock;
        }
    }

    /** A local identity for deduplication while active. Its fields never leave the recorder. */
    public static final class Ticket {
        private final Object owner;
        private final Life life;
        private final long startNs;
        private final long startWindow;
        private final AtomicInteger phase = new AtomicInteger(OPEN);

        private Ticket(Object owner, Life life, long startNs, long startWindow) {
            this.owner = owner;
            this.life = life;
            this.startNs = startNs;
            this.startWindow = startWindow;
        }
    }

    private final Population population;
    private final State state;

    public SpringTelemetry() {
        this(false, Population.PRIMARY, 0, System::nanoTime);
    }

    public SpringTelemetry(boolean enabled, Population population, long startUtc, LongSupplier clock) {
        this(enabled, population, startUtc, clock, enabled ? new ReentrantLock() : null);
    }

    SpringTelemetry(boolean enabled, Population population, long startUtc, LongSupplier clock, ReentrantLock lock) {
        this.population = Objects.requireNonNull(population);
        if (enabled && (!boundary(startUtc) || startUtc >= MAX_UTC || clock == null || lock == null)) {
            throw new IllegalArgumentException("invalid_recorder_config");
        }
        state = enabled ? new State(startUtc, clock, lock) : null;
    }

    public boolean enabled() {
        return state != null;
    }

    public Ticket begin(Kind kind, Boundary source) {
        return begin(kind, source, null);
    }

    /** A retry label accompanies a dispatch the caller has already chosen to execute. */
    public Ticket beginDispatch(Boundary source, Retry retry) {
        return begin(Kind.DISPATCH, source, retry);
    }

    private Ticket begin(Kind kind, Boundary source, Retry reason) {
        if (!enabled()) {
            return null;
        }
        Scope scope = allowed(source);
        if (kind == null || scope == null) {
            if (kind == null && scope != null) {
                drop(Drop.INVALID);
            }
            return null;
        }
        if (!state.lock.tryLock()) {
            drop(Drop.LOCK_BUSY);
            return null;
        }
        try {
            reconcile();
            Life life = life(kind, scope.surface());
            if (state.active.size() >= MAX_ACTIVE) {
                drop(Drop.ACTIVE_LIMIT);
                return null;
            }
            int retrySlot = reason == null ? -1 : retry(scope.surface(), reason);
            if (state.cells[life.opening()] + state.cells[life.started()] >= MAX_VALUE
                    || retrySlot >= 0 && state.cells[retrySlot] == MAX_VALUE) {
                drop(Drop.NUMERIC_OVERFLOW);
                return null;
            }
            long now;
            try {
                now = state.clock.getAsLong();
            } catch (RuntimeException unavailable) {
                drop(Drop.MONITOR_FAULT);
                return null;
            }
            Ticket ticket = new Ticket(state.owner, life, now, state.start);
            state.active.put(ticket, Boolean.TRUE);
            state.cells[life.started()]++;
            state.cells[life.active()]++;
            if (retrySlot >= 0) {
                state.cells[retrySlot]++;
            }
            return ticket;
        } finally {
            state.lock.unlock();
        }
    }

    public boolean finish(Ticket ticket, Outcome outcome) {
        if (!enabled() || ticket == null) {
            return false;
        }
        Integer slot = outcome == null ? null : ticket.life.outcomes().get(outcome);
        if (ticket.owner != state.owner || slot == null) {
            drop(Drop.INVALID);
            return false;
        }
        if (!ticket.phase.compareAndSet(OPEN, FINISHING)) {
            bump(DUPLICATES - DROP_BASE);
            return false;
        }
        if (!state.lock.tryLock()) {
            return lose(ticket, Drop.LOCK_BUSY);
        }
        try {
            if (ticket.phase.get() != FINISHING) {
                return false;
            }
            long elapsed;
            try {
                elapsed = state.clock.getAsLong() - ticket.startNs;
            } catch (RuntimeException unavailable) {
                return lose(ticket, Drop.MONITOR_FAULT);
            }
            long micros = elapsed / 1000;
            if (elapsed < 0 || micros > MAX_DURATION_US) {
                return lose(ticket, Drop.INVALID);
            }
            Life life = ticket.life;
            int bucket = life.histogram() + bucket(micros);
            int sum = life.histogram() + BUCKETS;
            int count = sum + 1;
            if (state.cells[sum] > MAX_VALUE - micros || state.cells[count] == MAX_VALUE) {
                return lose(ticket, Drop.NUMERIC_OVERFLOW);
            }
            state.cells[life.completed()]++;
            state.cells[life.active()]--;
            state.cells[slot]++;
            state.cells[bucket]++;
            state.cells[sum] += micros;
            state.cells[count]++;
            ticket.phase.set(CLOSED);
            state.active.remove(ticket);
            return true;
        } finally {
            state.lock.unlock();
        }
    }

    private boolean lose(Ticket ticket, Drop reason) {
        drop(reason);
        ticket.phase.compareAndSet(FINISHING, LOST);
        return false;
    }

    private void reconcile() {
        reconcile(state.start);
    }

    private void reconcile(long boundary) {
        var tickets = state.active.keySet().iterator();
        while (tickets.hasNext()) {
            var ticket = tickets.next();
            if (boundary - ticket.startWindow >= MAX_TICKET_AGE_SECONDS) {
                ticket.phase.set(LOST);
            }
            if (ticket.phase.compareAndSet(LOST, CLOSED)) {
                state.cells[ticket.life.lost()]++;
                state.cells[ticket.life.active()]--;
                tickets.remove();
            }
        }
    }

    public boolean observeSkip(Boundary source, Skip reason) {
        Scope scope = allowed(source);
        return scope != null && valid(reason) && increment(skip(scope.surface(), reason));
    }

    public boolean observeCache(Boundary source, Cache result) {
        Scope scope = allowed(source);
        return scope != null && valid(result) && increment(cache(scope.surface(), result));
    }

    public boolean observeProbe(Boundary source, Probe kind, Readiness result) {
        Scope scope = allowed(source);
        return scope != null && valid(kind) && valid(result) && increment(probe(scope.surface(), kind, result));
    }

    private Scope allowed(Boundary source) {
        if (!enabled()) {
            return null;
        }
        Scope scope = classify(source);
        if (!accepts(population, scope)) {
            drop(Drop.INVALID);
            return null;
        }
        return scope;
    }

    private boolean valid(Enum<?> value) {
        if (value == null) {
            drop(Drop.INVALID);
        }
        return value != null;
    }

    private boolean increment(int slot) {
        if (!state.lock.tryLock()) {
            drop(Drop.LOCK_BUSY);
            return false;
        }
        try {
            if (state.cells[slot] == MAX_VALUE) {
                drop(Drop.NUMERIC_OVERFLOW);
                return false;
            }
            state.cells[slot]++;
            return true;
        } finally {
            state.lock.unlock();
        }
    }

    public void drop(Drop reason) {
        if (enabled()) {
            bump((reason == null ? Drop.INVALID : reason).ordinal());
        }
    }

    private void bump(int index) {
        state.health.updateAndGet(index, value -> value < MAX_VALUE ? value + 1 : value);
    }

    public Snapshot snapshot() {
        return snapshot(false, 0);
    }

    /** The caller advances a trusted UTC boundary. Skipped minutes produce no phantom batches. */
    public Snapshot rotate(long nextStartUtc) {
        return snapshot(true, nextStartUtc);
    }

    private Snapshot snapshot(boolean rotate, long nextStartUtc) {
        if (!enabled()) {
            return null;
        }
        if (!state.lock.tryLock()) {
            drop(Drop.LOCK_BUSY);
            return null;
        }
        try {
            if (rotate && (!boundary(nextStartUtc) || nextStartUtc <= state.start || nextStartUtc >= MAX_UTC)) {
                drop(Drop.CLOCK_DISCONTINUITY);
                return null;
            }
            if (rotate && nextStartUtc - state.start > WINDOW_SECONDS) {
                drop(Drop.CLOCK_DISCONTINUITY);
            }
            reconcile(rotate ? nextStartUtc : state.start);
            long[] cells = state.cells.clone();
            for (int i = 0; i < state.health.length(); i++) {
                cells[DROP_BASE + i] = rotate ? state.health.getAndSet(i, 0) : state.health.get(i);
            }
            Snapshot result = new Snapshot(population, state.start, rotate, cells);
            if (rotate) {
                state.start = nextStartUtc;
                state.cells = new long[slots()];
                for (Kind kind : Kind.values()) {
                    for (Surface surface : Surface.values()) {
                        Life life = life(kind, surface);
                        state.cells[life.opening()] = state.cells[life.active()] = cells[life.active()];
                    }
                }
            }
            return result;
        } finally {
            state.lock.unlock();
        }
    }

    public static final class Snapshot {
        private final Population population;
        private final long start;
        private final boolean closed;
        private final long[] cells;

        private Snapshot(Population population, long start, boolean closed, long[] cells) {
            this.population = population;
            this.start = start;
            this.closed = closed;
            this.cells = cells;
        }

        public Population population() { return population; }
        public long start() { return start; }
        public long end() { return start + WINDOW_SECONDS; }
        public boolean closed() { return closed; }
        long cell(int slot) { return cells[slot]; }

        public long started(Kind kind, Surface surface) { return cell(life(kind, surface).started()); }
        public long completed(Kind kind, Surface surface) { return cell(life(kind, surface).completed()); }
        public long lost(Kind kind, Surface surface) { return cell(life(kind, surface).lost()); }
        public long opening(Kind kind, Surface surface) { return cell(life(kind, surface).opening()); }
        public long inFlight(Kind kind, Surface surface) { return cell(life(kind, surface).active()); }
        public long drops(Drop reason) { return cell(DROP_BASE + reason.ordinal()); }
        public long duplicates() { return cell(DUPLICATES); }
        public long retries(Surface surface, Retry retry) { return cell(MonitoringSchema.retry(surface, retry)); }
        public long skips(Surface surface, Skip skip) { return cell(MonitoringSchema.skip(surface, skip)); }
        public long caches(Surface surface, Cache cache) { return cell(MonitoringSchema.cache(surface, cache)); }
        public long probes(Surface surface, Probe probe, Readiness result) { return cell(MonitoringSchema.probe(surface, probe, result)); }

        public long outcomes(Kind kind, Surface surface, Outcome outcome) {
            Integer slot = outcome == null ? null : life(kind, surface).outcomes().get(outcome);
            if (slot == null) {
                throw new IllegalArgumentException("invalid_outcome");
            }
            return cell(slot);
        }

        public Histogram histogram(Kind kind, Surface surface) {
            int start = life(kind, surface).histogram();
            var bins = new ArrayList<Long>(BUCKETS);
            for (int i = 0; i < BUCKETS; i++) {
                bins.add(cells[start + i]);
            }
            return new Histogram(bins, cells[start + BUCKETS], cells[start + BUCKETS + 1]);
        }
    }

    public record Bucket(long lowerUs, Long upperUs) {}

    public record Histogram(List<Long> counts, long sumUs, long count) {
        public Histogram {
            if (counts == null || counts.size() != BUCKETS || count < 0 || count > MAX_VALUE
                    || sumUs < 0 || sumUs > MAX_VALUE || count == 0 && sumUs != 0) {
                throw new IllegalArgumentException("invalid_histogram");
            }
            counts = List.copyOf(counts);
            long remaining = count;
            for (long n : counts) {
                if (n < 0 || n > remaining) {
                    throw new IllegalArgumentException("invalid_histogram");
                }
                remaining -= n;
            }
            if (remaining != 0) {
                throw new IllegalArgumentException("invalid_histogram");
            }
        }

        public Bucket percentile(int percentile) {
            if (percentile < 1 || percentile > 100) {
                throw new IllegalArgumentException("invalid_percentile");
            }
            if (count == 0) {
                return null;
            }
            long rank = (count * percentile + 99) / 100;
            for (int i = 0; i < counts.size(); i++) {
                rank -= counts.get(i);
                if (rank <= 0) {
                    return new Bucket(i == 0 ? 0 : edge(i - 1) + 1, i == BUCKETS - 1 ? null : edge(i));
                }
            }
            throw new IllegalStateException("invalid_histogram_counts");
        }
    }
}
