package vn.smartprop.recommendation;

import java.io.*;
import java.nio.channels.Channels;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.DigestOutputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.*;
import java.util.zip.GZIPInputStream;
import java.util.zip.GZIPOutputStream;
import static vn.smartprop.recommendation.RecommendationDtos.*;

/**
 * On-disk binary cache for the TiniX research candidate set (Step 19.4.3A).
 *
 * <p>Rebuilding the snapshot means scanning ~124.690 clustered rows (~889 MB), which takes
 * 117-173 s on the target HDD. The candidate set only changes when the upstream dataset
 * changes, so the exact same {@link Candidate} list can be persisted and reloaded.
 *
 * <p>Safety model:
 * <ul>
 *   <li>Fixed-size header carries a format version, dataset revision, live index-probe values
 *       ({@code totalCount}, {@code fingerprint}), a holdout-group hash, the candidate count and
 *       a SHA-256 of the compressed payload.</li>
 *   <li>Writes go to a temp file in the same directory, are fsynced, then moved with
 *       {@code ATOMIC_MOVE} so a reader never observes a partially written cache.</li>
 *   <li>Reads reject wrong magic, unknown format version, oversized payload/count, checksum
 *       mismatch, truncation and trailing bytes.</li>
 *   <li>The caller re-validates revision/probe/holdout values against MySQL before trusting the
 *       payload. A cache is never trusted on its own metadata.</li>
 * </ul>
 *
 * <p>This cache holds research-only data and is only reachable from the Internal Research path.
 */
final class TinixSnapshotCache {
    static final String MAGIC = "SPTXSNP1";
    static final int FORMAT_VERSION = 1;

    static final int HEADER_BYTES = 8 + 4 + 40 + 8 + 8 + 4 + 32 + 32 + 8 + 8;
    static final int REVISION_BYTES = 40;
    static final int HASH_BYTES = 32;
    private static final int MAX_STRING_BYTES = 1 << 20;
    private static final int MAX_ISSUES = 4096;

    private TinixSnapshotCache() {}

    record Meta(String revision, long totalCount, long fingerprint, long holdoutHash,
                int candidateCount, long builtAtEpochMillis) {
        Meta withCandidateCount(int n, long builtAt) {
            return new Meta(revision, totalCount, fingerprint, holdoutHash, n, builtAt);
        }
    }

    record Loaded(Meta meta, List<Candidate> candidates, long payloadBytes) {}

    static final class InvalidCacheException extends Exception {
        InvalidCacheException(String message) { super(message); }
        InvalidCacheException(String message, Throwable cause) { super(message, cause); }
    }

    static long holdoutHash(Collection<String> holdoutGroups) {
        var sorted = new ArrayList<String>(holdoutGroups);
        Collections.sort(sorted);
        var digest = sha256();
        for (String g : sorted) {
            digest.update((byte) 0x1f);
            if (g != null) digest.update(g.getBytes(StandardCharsets.UTF_8));
        }
        return firstLong(digest.digest());
    }

    static long firstLong(byte[] hash) {
        long v = 0;
        for (int i = 0; i < 8; i++) v = (v << 8) | (hash[i] & 0xffL);
        return v;
    }

    static void write(Path target, Meta meta, List<Candidate> candidates, int maxPayloadBytes)
            throws IOException {
        if (meta.revision() == null || meta.revision().length() != REVISION_BYTES)
            throw new IOException("revision must be exactly " + REVISION_BYTES + " chars");
        if (candidates.size() != meta.candidateCount())
            throw new IOException("candidate count mismatch: meta=" + meta.candidateCount()
                    + " actual=" + candidates.size());

        Path absolute = target.toAbsolutePath();
        Path dir = absolute.getParent();
        Files.createDirectories(dir);
        Path tmp = Files.createTempFile(dir, ".tinix-snapshot-", ".tmp");
        boolean published = false;
        try {
            long payloadLength;
            byte[] payloadHash = new byte[HASH_BYTES];
            try (var raf = new RandomAccessFile(tmp.toFile(), "rw")) {
                raf.write(new byte[HEADER_BYTES]);
                long start = raf.getFilePointer();
                var digest = sha256();
                var channel = raf.getChannel();
                // Flush the gzip stream but never close it: closing would close the channel
                // owned by RandomAccessFile and break the header write below.
                var buffered = new BufferedOutputStream(Channels.newOutputStream(channel), 1 << 16);
                var digestOut = new DigestOutputStream(buffered, digest);
                var gzip = new GZIPOutputStream(digestOut, 1 << 16);
                var data = new DataOutputStream(gzip);
                encodeCandidates(data, candidates);
                data.flush();
                gzip.finish();
                gzip.flush();
                digestOut.flush();
                buffered.flush();
                payloadLength = channel.position() - start;
                System.arraycopy(digest.digest(), 0, payloadHash, 0, HASH_BYTES);
                if (payloadLength <= 0 || payloadLength > maxPayloadBytes)
                    throw new IOException("payload size out of range: " + payloadLength);
                raf.seek(0);
                raf.write(header(meta, payloadLength, payloadHash));
                channel.force(true);
            }
            try {
                Files.move(tmp, absolute, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            } catch (AtomicMoveNotSupportedException e) {
                Files.move(tmp, absolute, StandardCopyOption.REPLACE_EXISTING);
            }
            published = true;
        } finally {
            if (!published) Files.deleteIfExists(tmp);
        }
    }

    private static byte[] header(Meta meta, long payloadLength, byte[] payloadHash) throws IOException {
        var buffer = new ByteArrayOutputStream(HEADER_BYTES);
        var h = new DataOutputStream(buffer);
        h.write(MAGIC.getBytes(StandardCharsets.US_ASCII));
        h.writeInt(FORMAT_VERSION);
        h.write(fixedAscii(meta.revision(), REVISION_BYTES));
        h.writeLong(meta.totalCount());
        h.writeLong(meta.fingerprint());
        h.writeInt(meta.candidateCount());
        h.write(fixedHash(meta.holdoutHash()));
        h.write(payloadHash);
        h.writeLong(payloadLength);
        h.writeLong(meta.builtAtEpochMillis());
        h.flush();
        if (buffer.size() != HEADER_BYTES) throw new IOException("header size drift: " + buffer.size());
        return buffer.toByteArray();
    }

    private static void encodeCandidates(DataOutputStream out, List<Candidate> candidates) throws IOException {
        out.writeInt(candidates.size());
        for (Candidate c : candidates) {
            boolean derived = c.source() != null && c.source().recordKey() != null
                    && ("tinix:" + c.source().recordKey()).equals(c.id());
            out.writeBoolean(derived);
            if (!derived) writeString(out, c.id());
            writeString(out, c.title());
            writeString(out, c.type() == null ? null : c.type().name());
            writeString(out, c.price() == null ? null : c.price().toPlainString());
            writeString(out, c.area() == null ? null : c.area().toPlainString());
            writeString(out, c.district());
            writeString(out, c.ward());
            writeString(out, c.source() == null ? null : c.source().kind());
            writeString(out, c.source() == null ? null : c.source().name());
            writeString(out, c.source() == null ? null : c.source().recordKey());
            writeString(out, c.source() == null ? null : c.source().detailUrl());
            writeString(out, c.quality());
            writeString(out, c.verification());
            writeString(out, c.duplicateGroup());
            out.writeBoolean(c.duplicate());
            out.writeBoolean(c.holdout());
            out.writeBoolean(c.groupHasHoldout());
            var issues = c.issues() == null ? List.<String>of() : c.issues();
            out.writeInt(issues.size());
            for (String issue : issues) writeString(out, issue);
        }
        out.flush();
    }

    private static void writeString(DataOutputStream out, String value) throws IOException {
        if (value == null) { out.writeInt(-1); return; }
        byte[] bytes = value.getBytes(StandardCharsets.UTF_8);
        out.writeInt(bytes.length);
        out.write(bytes);
    }

    private static byte[] fixedAscii(String value, int length) {
        byte[] out = new byte[length];
        byte[] src = value.getBytes(StandardCharsets.US_ASCII);
        System.arraycopy(src, 0, out, 0, Math.min(src.length, length));
        return out;
    }

    private static byte[] fixedHash(long hash) {
        byte[] out = new byte[HASH_BYTES];
        for (int i = 0; i < 8; i++) out[i] = (byte) (hash >>> (56 - 8 * i));
        return out;
    }

    static Loaded read(Path file, int maxPayloadBytes, int maxCandidates) throws InvalidCacheException {
        long size;
        try {
            size = Files.size(file);
        } catch (IOException e) {
            throw new InvalidCacheException("cannot stat cache: " + e.getMessage(), e);
        }
        if (size < HEADER_BYTES) throw new InvalidCacheException("file too short: " + size + " bytes");

        Meta meta;
        byte[] payloadHash = new byte[HASH_BYTES];
        long payloadLength;
        byte[] payload;
        try (var in = new DataInputStream(new BufferedInputStream(Files.newInputStream(file), 1 << 16))) {
            byte[] magic = new byte[MAGIC.length()];
            in.readFully(magic);
            if (!MAGIC.equals(new String(magic, StandardCharsets.US_ASCII)))
                throw new InvalidCacheException("bad magic");
            int version = in.readInt();
            if (version != FORMAT_VERSION)
                throw new InvalidCacheException("unsupported format version " + version
                        + " (expected " + FORMAT_VERSION + ")");
            byte[] revBytes = new byte[REVISION_BYTES];
            in.readFully(revBytes);
            String revision = new String(revBytes, StandardCharsets.US_ASCII).trim();
            long totalCount = in.readLong();
            long fingerprint = in.readLong();
            int candidateCount = in.readInt();
            byte[] holdout = new byte[HASH_BYTES];
            in.readFully(holdout);
            in.readFully(payloadHash);
            payloadLength = in.readLong();
            long builtAt = in.readLong();
            meta = new Meta(revision, totalCount, fingerprint, firstLong(holdout), candidateCount, builtAt);

            if (candidateCount < 0 || candidateCount > maxCandidates)
                throw new InvalidCacheException("candidate count out of range: " + candidateCount);
            if (payloadLength < 0 || payloadLength > maxPayloadBytes)
                throw new InvalidCacheException("payload size out of range: " + payloadLength);
            if (HEADER_BYTES + payloadLength != size)
                throw new InvalidCacheException("size mismatch: header+payload=" + (HEADER_BYTES + payloadLength)
                        + " but file is " + size + " (truncated or trailing bytes)");
            payload = new byte[(int) payloadLength];
            in.readFully(payload);
        } catch (InvalidCacheException e) {
            throw e;
        } catch (EOFException e) {
            throw new InvalidCacheException("truncated cache header/payload", e);
        } catch (IOException e) {
            throw new InvalidCacheException("cannot read cache: " + e.getMessage(), e);
        }

        if (!Arrays.equals(sha256().digest(payload), payloadHash))
            throw new InvalidCacheException("sha256 mismatch (cache is corrupt or was not fully written)");

        List<Candidate> candidates;
        try (var gz = new GZIPInputStream(new ByteArrayInputStream(payload), 1 << 16)) {
            var data = new DataInputStream(new BufferedInputStream(gz, 1 << 16));
            int n = data.readInt();
            if (n != meta.candidateCount())
                throw new InvalidCacheException("declared candidate count " + meta.candidateCount()
                        + " != payload count " + n);
            var list = new ArrayList<Candidate>(n);
            for (int i = 0; i < n; i++) list.add(decodeCandidate(data));
            if (data.read() != -1) throw new InvalidCacheException("trailing bytes after payload");
            candidates = List.copyOf(list);
        } catch (InvalidCacheException e) {
            throw e;
        } catch (IOException | RuntimeException e) {
            throw new InvalidCacheException("cannot decode payload: " + e.getMessage(), e);
        }
        return new Loaded(meta, candidates, payloadLength);
    }

    private static Candidate decodeCandidate(DataInputStream in) throws IOException {
        boolean derived = in.readBoolean();
        String id = derived ? null : readString(in);
        String title = readString(in);
        String typeName = readString(in);
        String price = readString(in);
        String area = readString(in);
        String district = readString(in);
        String ward = readString(in);
        String kind = readString(in);
        String sourceName = readString(in);
        String recordKey = readString(in);
        String detailUrl = readString(in);
        String quality = readString(in);
        String verification = readString(in);
        String duplicateGroup = readString(in);
        boolean duplicate = in.readBoolean();
        boolean holdout = in.readBoolean();
        boolean groupHasHoldout = in.readBoolean();
        int issueCount = in.readInt();
        if (issueCount < 0 || issueCount > MAX_ISSUES) throw new IOException("issue count out of range: " + issueCount);
        List<String> issues = new ArrayList<>(issueCount);
        for (int i = 0; i < issueCount; i++) issues.add(readString(in));

        if (derived) {
            if (recordKey == null) throw new IOException("derived id without recordKey");
            id = "tinix:" + recordKey;
        }
        return new Candidate(id, title, typeName == null ? null : PropertyType.valueOf(typeName),
                price == null ? null : new java.math.BigDecimal(price),
                area == null ? null : new java.math.BigDecimal(area),
                district, ward, new Source(kind, sourceName, recordKey, detailUrl),
                quality, verification, duplicateGroup, duplicate, holdout, List.copyOf(issues), groupHasHoldout);
    }

    private static String readString(DataInputStream in) throws IOException {
        int len = in.readInt();
        if (len == -1) return null;
        if (len < 0 || len > MAX_STRING_BYTES) throw new IOException("string length out of range: " + len);
        byte[] bytes = new byte[len];
        in.readFully(bytes);
        return new String(bytes, StandardCharsets.UTF_8);
    }

    private static MessageDigest sha256() {
        try {
            return MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 unavailable", e);
        }
    }
}
