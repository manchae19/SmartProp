package vn.smartprop.modules.monitoring;

import java.net.ConnectException;
import java.net.http.HttpTimeoutException;
import java.time.Duration;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.CancellationException;
import java.util.concurrent.CompletionException;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.locks.ReentrantLock;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;
import static vn.smartprop.modules.monitoring.MonitoringSchema.*;
import static vn.smartprop.modules.monitoring.TrustedOrigin.*;

class SpringTelemetryTest {
    private static final Boundary ADVISOR = Boundary.ADVISOR_CONTROLLER;
    private static final Surface A = Surface.ADVISOR;
    private final AtomicLong clock = new AtomicLong();
    private final SpringTelemetry telemetry = new SpringTelemetry(true, Population.SYNTHETIC, 0, clock::get);

    @Test
    void disabledRecorderDoesNotCallObserversOrClock() {
        var dark = new SpringTelemetry(false, Population.PRIMARY, -1, () -> fail("clock"));
        assertFalse(new SpringTelemetry().enabled());
        assertFalse(dark.enabled());
        assertNull(dark.begin(Kind.SURFACE, ADVISOR));
        assertNull(dark.beginDispatch(ADVISOR, Retry.AUTH));
        assertFalse(dark.finish(telemetry.begin(Kind.SURFACE, ADVISOR), Outcome.SERVED));
        assertFalse(dark.observeCache(ADVISOR, Cache.HIT));
        assertFalse(dark.observeProbe(ADVISOR, Probe.OPTIONS, Readiness.READY));
        assertFalse(dark.observeSkip(ADVISOR, Skip.OPT_OUT));
        dark.drop(Drop.MONITOR_FAULT);
        assertNull(dark.snapshot());
        assertNull(dark.rotate(60));
        assertEquals(200, MonitoringGuard.around(dark, () -> fail("before"), () -> 200,
                ok -> fail("after")));
    }

    @Test
    void requestWithNoValuationHasOneSurfaceAndExplicitSkipOnly() {
        var consult = telemetry.begin(Kind.SURFACE, ADVISOR);
        assertTrue(telemetry.observeSkip(ADVISOR, Skip.OPT_OUT));
        assertTrue(telemetry.finish(consult, Outcome.SERVED));
        var snapshot = telemetry.snapshot();
        assertCounts(snapshot, Kind.SURFACE, 1, 1);
        assertCounts(snapshot, Kind.OPPORTUNITY, 0, 0);
        assertCounts(snapshot, Kind.CANDIDATE, 0, 0);
        assertCounts(snapshot, Kind.DISPATCH, 0, 0);
        assertEquals(1, snapshot.skips(A, Skip.OPT_OUT));
    }

    @Test
    void requestWithNoEligibleCandidateRecordsIncompleteAndResearchSkips() {
        var consult = telemetry.begin(Kind.SURFACE, ADVISOR);
        candidateSkipped(Skip.INCOMPLETE);
        candidateSkipped(Skip.RESEARCH);
        assertTrue(telemetry.finish(consult, Outcome.SERVED));
        var snapshot = telemetry.snapshot();
        assertCounts(snapshot, Kind.SURFACE, 1, 1);
        assertCounts(snapshot, Kind.CANDIDATE, 2, 2);
        assertEquals(2, snapshot.outcomes(Kind.CANDIDATE, A, Outcome.SKIP));
        assertEquals(0, snapshot.outcomes(Kind.CANDIDATE, A, Outcome.ELIGIBLE));
        assertCounts(snapshot, Kind.OPPORTUNITY, 0, 0);
        assertCounts(snapshot, Kind.DISPATCH, 0, 0);
        assertEquals(1, snapshot.skips(A, Skip.INCOMPLETE));
        assertEquals(1, snapshot.skips(A, Skip.RESEARCH));
    }

    @Test
    void requestWithOneEligibleCandidateAndOneDispatch() {
        var consult = telemetry.begin(Kind.SURFACE, ADVISOR);
        var opportunity = eligibleCandidate();
        var dispatch = telemetry.beginDispatch(ADVISOR, null);
        assertTrue(telemetry.finish(dispatch, DispatchOutcome.response(200)));
        assertTrue(telemetry.finish(opportunity, Outcome.VALID_POINT));
        assertTrue(telemetry.finish(consult, Outcome.SERVED));
        for (Kind kind : Kind.values()) {
            assertCounts(telemetry.snapshot(), kind, 1, 1);
        }
    }

    @Test
    void oneAdvisorResponseCanServePartialResultsAfterMultipleDispatches() {
        var consult = telemetry.begin(Kind.SURFACE, ADVISOR);
        candidateSkipped(Skip.INCOMPLETE);
        var first = eligibleCandidate();
        var second = eligibleCandidate();
        assertTrue(telemetry.finish(telemetry.beginDispatch(ADVISOR, null),
                DispatchOutcome.failure(new TimeoutException())));
        assertTrue(telemetry.finish(telemetry.beginDispatch(ADVISOR, Retry.TRANSPORT),
                DispatchOutcome.response(200)));
        assertTrue(telemetry.finish(first, Outcome.VALID_POINT));
        assertTrue(telemetry.finish(telemetry.beginDispatch(ADVISOR, null),
                DispatchOutcome.failure(new ConnectException())));
        assertTrue(telemetry.finish(second, Outcome.DEPENDENCY_UNAVAILABLE));
        assertTrue(telemetry.finish(consult, Outcome.SERVED));
        var s = telemetry.snapshot();
        assertCounts(s, Kind.SURFACE, 1, 1);
        assertCounts(s, Kind.OPPORTUNITY, 2, 2);
        assertCounts(s, Kind.CANDIDATE, 3, 3);
        assertCounts(s, Kind.DISPATCH, 3, 3);
        assertEquals(2, s.outcomes(Kind.CANDIDATE, A, Outcome.ELIGIBLE));
        assertEquals(1, s.outcomes(Kind.OPPORTUNITY, A, Outcome.VALID_POINT));
        assertEquals(1, s.outcomes(Kind.OPPORTUNITY, A, Outcome.DEPENDENCY_UNAVAILABLE));
        assertEquals(1, s.outcomes(Kind.DISPATCH, A, Outcome.TIMEOUT));
        assertEquals(1, s.outcomes(Kind.DISPATCH, A, Outcome.DEPENDENCY_UNAVAILABLE));
        assertEquals(1, s.outcomes(Kind.DISPATCH, A, Outcome.AI_RESPONSE));
        assertEquals(1, s.retries(A, Retry.TRANSPORT));
        assertEquals(0, s.retries(A, Retry.AUTH));
    }

    @Test
    void surfacesCacheAndReadinessStaySeparate() {
        var posting = Boundary.POSTING_CONTROLLER;
        assertTrue(telemetry.finish(telemetry.begin(Kind.SURFACE, posting), Outcome.SERVED));
        assertTrue(telemetry.finish(telemetry.begin(Kind.OPPORTUNITY, posting), Outcome.CACHE_HIT));
        assertTrue(telemetry.observeCache(posting, Cache.HIT));
        assertTrue(telemetry.observeProbe(posting, Probe.OPTIONS, Readiness.NOT_READY));
        var standalone = Boundary.VERIFIED_STANDALONE_PROXY;
        assertTrue(telemetry.finish(telemetry.begin(Kind.SURFACE, standalone), Outcome.VALIDATION_REJECTION));
        var s = telemetry.snapshot();
        assertEquals(1, s.started(Kind.SURFACE, Surface.POSTING));
        assertEquals(1, s.started(Kind.SURFACE, Surface.STANDALONE));
        assertEquals(0, s.started(Kind.SURFACE, A));
        assertEquals(1, s.outcomes(Kind.OPPORTUNITY, Surface.POSTING, Outcome.CACHE_HIT));
        assertEquals(0, s.started(Kind.DISPATCH, Surface.POSTING));
        assertEquals(1, s.caches(Surface.POSTING, Cache.HIT));
        assertEquals(1, s.probes(Surface.POSTING, Probe.OPTIONS, Readiness.NOT_READY));
    }

    @Test
    void statusTimeoutCancellationAndDependencyAreDistinct() {
        assertEquals(Outcome.AI_RESPONSE, DispatchOutcome.response(503));
        assertEquals(Outcome.FAILED, DispatchOutcome.response(0));
        assertEquals(Outcome.TIMEOUT, DispatchOutcome.failure(new CompletionException(new HttpTimeoutException("x"))));
        assertEquals(Outcome.TIMEOUT, DispatchOutcome.failure(new TimeoutException()));
        assertEquals(Outcome.CANCELLED, DispatchOutcome.failure(new CancellationException()));
        assertEquals(Outcome.CANCELLED, DispatchOutcome.failure(new InterruptedException()));
        assertEquals(Outcome.DEPENDENCY_UNAVAILABLE, DispatchOutcome.failure(new ConnectException()));
        assertEquals(Outcome.FAILED, DispatchOutcome.failure(new IllegalStateException()));
        assertTrue(telemetry.finish(telemetry.beginDispatch(ADVISOR, null), Outcome.CANCELLED));
        var s = telemetry.snapshot();
        assertEquals(1, s.completed(Kind.DISPATCH, A));
        assertEquals(1, s.outcomes(Kind.DISPATCH, A, Outcome.CANCELLED));
        assertEquals(0, s.outcomes(Kind.DISPATCH, A, Outcome.TIMEOUT));
        assertEquals(0, s.retries(A, Retry.TRANSPORT));
    }

    @Test
    void scopeIsServerSelectedAndPopulationIsolated() {
        assertEquals(Surface.UNATTRIBUTED, TrustedOrigin.classify(null).surface());
        assertEquals(Population.PREVIEW, TrustedOrigin.classify(Boundary.INTERNAL_PREVIEW).population());
        assertEquals(Population.INTERNAL_DIAGNOSTIC, TrustedOrigin.classify(Boundary.INTERNAL_DIAGNOSTIC).population());
        assertEquals(Population.HISTORICAL_COMPATIBILITY,
                TrustedOrigin.classify(Boundary.HISTORICAL_COMPATIBILITY).population());
        assertNull(telemetry.begin(Kind.SURFACE, Boundary.INTERNAL_DIAGNOSTIC));
        assertNull(telemetry.begin(Kind.SURFACE, Boundary.HISTORICAL_COMPATIBILITY));
        assertNull(telemetry.begin(Kind.SURFACE, Boundary.INTERNAL_PREVIEW));
        assertFalse(telemetry.observeSkip(ADVISOR, null));
        assertEquals(4, telemetry.snapshot().drops(Drop.INVALID));
        var diagnostic = new SpringTelemetry(true, Population.INTERNAL_DIAGNOSTIC, 0, clock::get);
        assertNull(diagnostic.begin(Kind.SURFACE, ADVISOR));
        assertTrue(diagnostic.finish(diagnostic.begin(Kind.SURFACE, Boundary.INTERNAL_DIAGNOSTIC), Outcome.SERVED));
        assertEquals(1, diagnostic.snapshot().completed(Kind.SURFACE, Surface.UNATTRIBUTED));
    }

    @Test
    void saturationAndTicketExpiryLeaveExplicitEvidenceLoss() {
        for (int i = 0; i < SpringTelemetry.MAX_ACTIVE; i++) {
            assertNotNull(telemetry.begin(Kind.SURFACE, ADVISOR));
        }
        assertNull(telemetry.begin(Kind.SURFACE, ADVISOR));
        var early = telemetry.snapshot();
        assertEquals(1, early.drops(Drop.ACTIVE_LIMIT));
        assertEquals(SpringTelemetry.MAX_ACTIVE, early.inFlight(Kind.SURFACE, A));
        assertNull(telemetry.rotate(59));
        var expired = telemetry.rotate(600);
        assertEquals(2, expired.drops(Drop.CLOCK_DISCONTINUITY));
        assertEquals(SpringTelemetry.MAX_ACTIVE, expired.lost(Kind.SURFACE, A));
        assertEquals(0, expired.inFlight(Kind.SURFACE, A));
        assertEquals(0, expired.completed(Kind.SURFACE, A));
        assertNotNull(telemetry.begin(Kind.SURFACE, ADVISOR));
    }

    @Test
    void lockContentionDoesNotWaitOrInventCompletedOutcomes() throws Exception {
        var lock = new ReentrantLock();
        var recorder = new SpringTelemetry(true, Population.SYNTHETIC, 0, clock::get, lock);
        var ticket = recorder.beginDispatch(ADVISOR, null);
        var locked = new CountDownLatch(1);
        var release = new CountDownLatch(1);
        Thread holder = Thread.ofVirtual().start(() -> {
            lock.lock();
            try {
                locked.countDown();
                release.await();
            } catch (InterruptedException ex) {
                Thread.currentThread().interrupt();
            } finally {
                lock.unlock();
            }
        });
        try {
            assertTrue(locked.await(5, TimeUnit.SECONDS));
            assertTimeoutPreemptively(Duration.ofSeconds(2), () -> {
                assertFalse(recorder.finish(ticket, Outcome.TIMEOUT));
                assertNull(recorder.begin(Kind.SURFACE, ADVISOR));
                assertNull(recorder.snapshot());
            });
        } finally {
            release.countDown();
            holder.join();
        }
        assertFalse(recorder.finish(ticket, Outcome.AI_RESPONSE));
        var s = recorder.snapshot();
        assertEquals(1, s.lost(Kind.DISPATCH, A));
        assertEquals(0, s.completed(Kind.DISPATCH, A));
        assertEquals(0, s.histogram(Kind.DISPATCH, A).count());
        assertEquals(3, s.drops(Drop.LOCK_BUSY));
        assertEquals(1, s.duplicates());
    }

    @Test
    void invalidNumericAndDuplicateCompletionDoNotAlterHistogram() {
        var bad = telemetry.beginDispatch(ADVISOR, null);
        clock.set(-1);
        assertFalse(telemetry.finish(bad, Outcome.AI_RESPONSE));
        var badAgain = telemetry.beginDispatch(ADVISOR, null);
        clock.addAndGet((MAX_DURATION_US + 1) * 1000);
        assertFalse(telemetry.finish(badAgain, Outcome.AI_RESPONSE));
        var good = telemetry.beginDispatch(ADVISOR, null);
        clock.addAndGet(15_000_001_000L);
        assertTrue(telemetry.finish(good, Outcome.AI_RESPONSE));
        assertFalse(telemetry.finish(good, Outcome.TIMEOUT));
        var s = telemetry.snapshot();
        assertEquals(2, s.drops(Drop.INVALID));
        assertEquals(2, s.lost(Kind.DISPATCH, A));
        assertEquals(1, s.duplicates());
        var h = s.histogram(Kind.DISPATCH, A);
        assertEquals(1, h.count());
        assertEquals(15_000_001, h.sumUs());
        assertEquals(new SpringTelemetry.Bucket(15_000_001, null), h.percentile(99));
        assertThrows(UnsupportedOperationException.class, () -> h.counts().clear());
        assertThrows(IllegalArgumentException.class, () -> new SpringTelemetry.Histogram(List.of(1L), 0, 1));
        assertThrows(IllegalArgumentException.class,
                () -> new SpringTelemetry.Histogram(Collections.nCopies(BUCKETS, 1L), 0, 1));
    }

    @Test
    void recorderFaultsDoNotChangeBusinessResultStatusOrInvocationCount() {
        var faultyClock = new SpringTelemetry(true, Population.SYNTHETIC, 0,
                () -> { throw new IllegalStateException("observation"); });
        record Result(int httpStatus, List<String> recommendations) {}
        var response = new Result(200, List.of("synthetic"));
        var operations = new AtomicInteger();
        var error = new IllegalArgumentException("business");
        assertSame(response, MonitoringGuard.around(faultyClock, () -> {
            assertNull(faultyClock.begin(Kind.SURFACE, ADVISOR));
            throw new IllegalStateException("recorder start");
        }, () -> {
            operations.incrementAndGet();
            return response;
        }, ok -> {
            assertTrue(ok);
            throw new IllegalStateException("recorder finish");
        }));
        assertSame(error, assertThrows(IllegalArgumentException.class,
                () -> MonitoringGuard.around(faultyClock, () -> {}, () -> {
                    operations.incrementAndGet();
                    throw error;
                }, ok -> {
                    assertFalse(ok);
                    throw new IllegalStateException("collector offline");
                })));
        assertEquals(2, operations.get());
        assertEquals(4, faultyClock.snapshot().drops(Drop.MONITOR_FAULT));
    }

    private void candidateSkipped(Skip skip) {
        assertTrue(telemetry.finish(telemetry.begin(Kind.CANDIDATE, ADVISOR), Outcome.SKIP));
        assertTrue(telemetry.observeSkip(ADVISOR, skip));
    }

    private SpringTelemetry.Ticket eligibleCandidate() {
        assertTrue(telemetry.finish(telemetry.begin(Kind.CANDIDATE, ADVISOR), Outcome.ELIGIBLE));
        return telemetry.begin(Kind.OPPORTUNITY, ADVISOR);
    }

    private void assertCounts(SpringTelemetry.Snapshot s, Kind kind, long started, long completed) {
        assertEquals(started, s.started(kind, A));
        assertEquals(completed, s.completed(kind, A));
        assertEquals(completed, s.histogram(kind, A).count());
    }
}
