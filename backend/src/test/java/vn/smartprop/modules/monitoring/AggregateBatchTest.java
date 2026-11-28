package vn.smartprop.modules.monitoring;

import java.nio.charset.StandardCharsets;
import java.util.HexFormat;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.IntStream;
import java.util.stream.Stream;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;
import static vn.smartprop.modules.monitoring.MonitoringSchema.*;
import static vn.smartprop.modules.monitoring.TrustedOrigin.*;

class AggregateBatchTest {
    private static final Boundary ADVISOR = Boundary.ADVISOR_CONTROLLER;
    private final AtomicLong clock = new AtomicLong();
    private final SpringTelemetry telemetry = new SpringTelemetry(true, Population.SYNTHETIC, 0, clock::get);
    private final AggregateBatch.Producer producer = new AggregateBatch.Producer(3, 7, 0, Population.SYNTHETIC);

    @Test
    void emitsExactlyTheTwoSharedPythonFixtures() throws Exception {
        var consult = telemetry.begin(Kind.SURFACE, ADVISOR);
        var candidate = telemetry.begin(Kind.CANDIDATE, ADVISOR);
        clock.set(2_000_000);
        assertTrue(telemetry.finish(candidate, Outcome.ELIGIBLE));
        var opportunity = telemetry.begin(Kind.OPPORTUNITY, ADVISOR);
        var firstDispatch = telemetry.beginDispatch(ADVISOR, null);
        clock.set(20_000_000);
        assertTrue(telemetry.finish(firstDispatch, Outcome.TIMEOUT));
        var retry = telemetry.beginDispatch(ADVISOR, Retry.TRANSPORT);

        var low = telemetry.rotate(60);
        assertEquals(1, low.inFlight(Kind.DISPATCH, Surface.ADVISOR));
        assertEquals(0, low.opening(Kind.DISPATCH, Surface.ADVISOR));
        clock.set(36_000_000);
        assertTrue(telemetry.finish(retry, Outcome.AI_RESPONSE));
        assertTrue(telemetry.finish(opportunity, Outcome.VALID_POINT));
        assertTrue(telemetry.finish(consult, Outcome.SERVED));
        var high = telemetry.rotate(120);
        assertEquals(1, high.opening(Kind.DISPATCH, Surface.ADVISOR));
        assertEquals(0, high.inFlight(Kind.DISPATCH, Surface.ADVISOR));

        try (var file = getClass().getResourceAsStream("/wp06/b4-aggregate.hex")) {
            assertNotNull(file);
            var expected = new String(file.readAllBytes(), StandardCharsets.US_ASCII).lines().toList();
            assertEquals(expected, Stream.of(low, high)
                    .map(window -> HexFormat.of().formatHex(AggregateBatch.encode(producer, window).bytes())).toList());
        }
    }

    @Test
    void registryWireRangeIsFixedAndCannotClaimPythonInvocations() {
        assertEquals(445, MonitoringSchema.slots());
        assertEquals(3390, AggregateBatch.MAX_PACKET_BYTES);
        var expected = IntStream.concat(IntStream.range(0, 282), IntStream.range(388, 442)).boxed().toList();
        assertEquals(expected, wireOrder().stream().map(MonitoringSchema::wireSlot).toList());
        assertFalse(Stream.of(Kind.values()).anyMatch(kind -> kind.name().equals("INVOCATION")));
        assertFalse(Stream.of(TrustedOrigin.class.getDeclaredMethods())
                .flatMap(method -> Stream.of(method.getParameterTypes())).anyMatch(type -> type == String.class));
        assertFalse(Stream.of(SpringTelemetry.class.getDeclaredMethods())
                .flatMap(method -> Stream.of(method.getParameterTypes())).anyMatch(type -> type == String.class));
    }

    @Test
    void liveUnattributedWrongPopulationAndInvalidIdentitiesCannotBeExported() {
        assertThrows(IllegalArgumentException.class, () -> AggregateBatch.encode(producer, telemetry.snapshot()));
        var unknown = telemetry.begin(Kind.SURFACE, null);
        assertTrue(telemetry.finish(unknown, Outcome.SERVED));
        var closed = telemetry.rotate(60);
        assertEquals(1, closed.completed(Kind.SURFACE, Surface.UNATTRIBUTED));
        assertEquals("unprojectable_surface",
                assertThrows(IllegalArgumentException.class, () -> AggregateBatch.encode(producer, closed)).getMessage());
        var primary = new AggregateBatch.Producer(3, 7, 0, Population.PRIMARY);
        assertThrows(IllegalArgumentException.class, () -> AggregateBatch.encode(primary, closed));
        for (var invalid : List.of(0, 33)) {
            assertThrows(IllegalArgumentException.class,
                    () -> new AggregateBatch.Producer(invalid, 1, 0, Population.SYNTHETIC));
        }
        assertThrows(IllegalArgumentException.class,
                () -> new AggregateBatch.Producer(3, 0x1_0000_0000L, 0, Population.SYNTHETIC));
        assertThrows(IllegalArgumentException.class, () -> new AggregateBatch.Producer(3, 1, 59, Population.SYNTHETIC));
    }

    @Test
    void collectorOutageIsBoundedByCountAndBytesAndDoesNotRetryBusinessOperations() {
        var first = AggregateBatch.encode(producer, telemetry.rotate(60));
        var second = AggregateBatch.encode(producer, telemetry.rotate(120));
        var queue = new BatchBuffer(2, 128 * 1024);
        assertEquals(BatchBuffer.Offer.QUEUED, queue.offer(first));
        assertEquals(BatchBuffer.Offer.QUEUED, queue.offer(second));
        assertEquals(BatchBuffer.Offer.FULL, queue.offer(second));
        assertEquals(BatchBuffer.Offer.INVALID, queue.offer(null));
        assertSame(first, queue.poll());
        assertSame(second, queue.poll());
        assertNull(queue.poll());
        var byBytes = new BatchBuffer(64, first.size() + BatchBuffer.PER_PACKET_CHARGE);
        assertEquals(BatchBuffer.Offer.QUEUED, byBytes.offer(first));
        var businessCalls = new AtomicLong();
        assertEquals(200, MonitoringGuard.around(telemetry, () -> {}, () -> {
            businessCalls.incrementAndGet();
            return 200;
        }, ok -> {
            assertTrue(ok);
            if (byBytes.offer(second) == BatchBuffer.Offer.FULL) {
                telemetry.drop(Drop.QUEUE_FULL);
            }
        }));
        assertEquals(1, businessCalls.get());
        assertEquals(1, telemetry.snapshot().drops(Drop.QUEUE_FULL));
        assertSame(first, byBytes.poll());
        first.bytes()[0] = 0;
        assertEquals('W', first.bytes()[0]);
        assertNull(byBytes.poll());
        assertThrows(IllegalArgumentException.class, () -> new BatchBuffer(65, 128 * 1024));
        assertThrows(IllegalArgumentException.class, () -> new BatchBuffer(1, 128 * 1024 + 1));
    }
}
