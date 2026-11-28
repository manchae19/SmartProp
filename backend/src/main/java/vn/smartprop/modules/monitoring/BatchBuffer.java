package vn.smartprop.modules.monitoring;

import java.util.ArrayDeque;
import java.util.concurrent.locks.ReentrantLock;

import static vn.smartprop.modules.monitoring.AggregateBatch.Packet;

/** Explicit in-memory handoff. Capacity exhaustion does not trigger a send or retry. */
public final class BatchBuffer {
    public static final int MAX_PENDING = 64;
    public static final int MAX_RETAINED_BYTES = 128 * 1024;
    static final int PER_PACKET_CHARGE = 64;

    public enum Offer { QUEUED, FULL, BUSY, INVALID }

    private final int countLimit;
    private final int byteLimit;
    private final ArrayDeque<Packet> pending;
    private final ReentrantLock lock = new ReentrantLock();
    private int retained;

    public BatchBuffer() {
        this(MAX_PENDING, MAX_RETAINED_BYTES);
    }

    public BatchBuffer(int countLimit, int byteLimit) {
        if (countLimit < 1 || countLimit > MAX_PENDING || byteLimit < 1 || byteLimit > MAX_RETAINED_BYTES) {
            throw new IllegalArgumentException("invalid_buffer_capacity");
        }
        this.countLimit = countLimit;
        this.byteLimit = byteLimit;
        pending = new ArrayDeque<>(countLimit);
    }

    public Offer offer(Packet packet) {
        if (packet == null) {
            return Offer.INVALID;
        }
        if (!lock.tryLock()) {
            return Offer.BUSY;
        }
        try {
            int charge = packet.size() + PER_PACKET_CHARGE;
            if (pending.size() >= countLimit || charge > byteLimit - retained) {
                return Offer.FULL;
            }
            pending.addLast(packet);
            retained += charge;
            return Offer.QUEUED;
        } finally {
            lock.unlock();
        }
    }

    public Packet poll() {
        if (!lock.tryLock()) {
            return null;
        }
        try {
            Packet packet = pending.pollFirst();
            if (packet != null) {
                retained -= packet.size() + PER_PACKET_CHARGE;
            }
            return packet;
        } finally {
            lock.unlock();
        }
    }
}
