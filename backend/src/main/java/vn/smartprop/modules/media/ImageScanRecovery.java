package vn.smartprop.modules.media;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Recovers image scans left in SCANNING after a process restart.
 *
 * The update is conditional on the lease timestamp, so two instances cannot
 * claim the same stale row. A recovered row is moved to PENDING_RETRY and then
 * queued through the existing bounded scanner; no new row is inserted.
 */
@Component
public class ImageScanRecovery {
    private static final Logger log = LoggerFactory.getLogger(ImageScanRecovery.class);
    private final JdbcTemplate jdbc;
    private final PropertyImageScanService scanner;
    private final int staleAfterSeconds;
    private final AtomicBoolean recoveryRunning = new AtomicBoolean();

    public ImageScanRecovery(JdbcTemplate jdbc, PropertyImageScanService scanner,
            @Value("${app.image-scan.stale-after-seconds:180}") int staleAfterSeconds) {
        this.jdbc = jdbc;
        this.scanner = scanner;
        this.staleAfterSeconds = staleAfterSeconds;
    }

    @EventListener(ApplicationReadyEvent.class)
    public void recoverOnStartup() {
        recoverInterruptedScans();
    }

    @Scheduled(fixedDelayString = "${app.image-scan.recovery-interval-ms:60000}",
        initialDelayString = "${app.image-scan.recovery-interval-ms:60000}")
    public void recoverInterruptedScans() {
        if (!recoveryRunning.compareAndSet(false, true)) return;
        try {
            recoverStaleScans();
        } finally {
            recoveryRunning.set(false);
        }
    }

    private void recoverStaleScans() {
        if (staleAfterSeconds < 1 || staleAfterSeconds > 3600) {
            log.warn("Image scan recovery skipped: stale-after-seconds out of range ({})", staleAfterSeconds);
            return;
        }
        try {
            var propertyIds = jdbc.queryForList(
                "SELECT DISTINCT property_id FROM property_image_scan "
                    + "WHERE scan_status='SCANNING' AND updated_at < DATE_SUB(UTC_TIMESTAMP(6), INTERVAL ? SECOND) "
                    + "ORDER BY property_id",
                String.class, staleAfterSeconds);
            for (String propertyId : propertyIds) {
                int claimed = jdbc.update(
                    "UPDATE property_image_scan SET scan_status='PENDING_RETRY', classification=NULL, "
                        + "similarity=NULL, matched_property_id=NULL, matched_property_image_id=NULL, "
                        + "matched_listing_code=NULL, detection_method=NULL, evidence=JSON_OBJECT(), "
                        + "error_code='JOB_INTERRUPTED', scanned_at=UTC_TIMESTAMP(6), updated_at=UTC_TIMESTAMP(6) "
                        + "WHERE property_id=? AND scan_status='SCANNING' "
                        + "AND updated_at < DATE_SUB(UTC_TIMESTAMP(6), INTERVAL ? SECOND)",
                    propertyId, staleAfterSeconds);
                if (claimed == 0) continue;
                try {
                    scanner.schedule(propertyId);
                } catch (RuntimeException error) {
                    // Leave PENDING_RETRY visible for owner/ADMIN retry if the executor queue is full.
                    log.warn("Recovered image scan could not be queued for property {}", propertyId);
                }
            }
        } catch (RuntimeException error) {
            // The schema may not exist during a pre-V20 startup. Never crash the app or invent a scan result.
            log.warn("Image scan recovery skipped: {}", error.getClass().getSimpleName());
        }
    }
}
