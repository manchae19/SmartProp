package vn.smartprop.modules.monitoring;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;

import static vn.smartprop.modules.monitoring.MonitoringSchema.*;
import static vn.smartprop.modules.monitoring.TrustedOrigin.Population;

/** Canonical WPT3 bytes for the authorized collector's Spring slot. No transport is attached. */
public final class AggregateBatch {
    private static final int HEADER_BYTES = 30;
    private static final int ENTRY_BYTES = 10;
    private static final int RELEASE = 1;
    public static final int MAX_PACKET_BYTES = HEADER_BYTES + ENTRY_BYTES * wireOrder().size();

    private AggregateBatch() {}

    public record Producer(int slot, long generation, long firstWindow, Population population) {
        public Producer {
            if (slot < 1 || slot > 32 || generation < 1 || generation > 0xffff_ffffL || population == null
                    || !boundary(firstWindow) || firstWindow >= MAX_UTC) {
                throw new IllegalArgumentException("invalid_producer");
            }
        }
    }

    /** Only the encoder can construct a packet, and callers cannot mutate its contents. */
    public static final class Packet {
        private final byte[] wire;

        private Packet(byte[] wire) {
            this.wire = wire;
        }

        public int size() {
            return wire.length;
        }

        public byte[] bytes() {
            return wire.clone();
        }
    }

    public static Packet encode(Producer producer, SpringTelemetry.Snapshot snapshot) {
        if (producer == null || snapshot == null || !snapshot.closed()
                || producer.population() != snapshot.population() || snapshot.start() < producer.firstWindow()) {
            throw new IllegalArgumentException("invalid_batch_identity");
        }
        int entries = 0;
        for (int i = 0; i < slots(); i++) {
            long value = snapshot.cell(i);
            if (value > 0) {
                if (wireSlot(i) < 0) {
                    // A local unattributed record cannot masquerade as a verified Spring surface.
                    throw new IllegalArgumentException("unprojectable_surface");
                }
                entries++;
            }
        }
        long seq = 1 + (snapshot.start() - producer.firstWindow()) / WINDOW_SECONDS;
        ByteBuffer wire = ByteBuffer.allocate(HEADER_BYTES + ENTRY_BYTES * entries).order(ByteOrder.LITTLE_ENDIAN);
        wire.put((byte) 'W').put((byte) 'P').put((byte) 'T').put((byte) '3');
        wire.put((byte) VERSION).put((byte) producer.slot()).putInt((int) producer.generation());
        wire.put((byte) producer.population().wireCode()).putLong(seq).put((byte) RELEASE);
        wire.putInt((int) snapshot.start()).putInt((int) snapshot.end()).putShort((short) entries);
        for (int slot : wireOrder()) {
            long count = snapshot.cell(slot);
            if (count != 0) {
                wire.putShort((short) wireSlot(slot)).putLong(count);
            }
        }
        return new Packet(wire.array());
    }
}
