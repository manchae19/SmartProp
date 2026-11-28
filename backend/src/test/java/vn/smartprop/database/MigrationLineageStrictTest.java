package vn.smartprop.database;

import static org.junit.jupiter.api.Assertions.*;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

/**
 * Migration lineage guard — kiểm tra nghiêm ngặt.
 *
 * <p>Bổ sung cho bộ test cũ: các ca mà {@code history.size()} không đủ để kết luận
 * V17/V18 đã tồn tại, và các ca gap/duplicate/out-of-order.
 */
class MigrationLineageStrictTest {

    private static Map<String, Object> row(String version, String type, Integer checksum) {
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("version", version);
        map.put("type", type);
        map.put("checksum", checksum);
        map.put("success", true);
        return map;
    }

    private static Map<String, Object> failed(String version) {
        Map<String, Object> map = row(version, "SQL", 1);
        map.put("success", false);
        return map;
    }

    /** Baseline hợp lệ: V13 BASELINE + V14 với checksum gốc. */
    private static List<Map<String, Object>> baseline() {
        return new ArrayList<>(List.of(
            row("13", "BASELINE", null),
            row("14", "SQL", -1382804267)));
    }

    private static List<Map<String, Object>> with(List<Map<String, Object>> base, String... versions) {
        List<Map<String, Object>> copy = new ArrayList<>(base);
        for (String version : versions) copy.add(row(version, "SQL", 1));
        return copy;
    }

    // ---------- Baseline ----------

    @Test
    void baselineOnlyIsAcceptedWhenNotComplete() {
        assertDoesNotThrow(() ->
            MigrationLineageConfiguration.checkHistory(baseline(), true, false));
    }

    @Test
    void baselineOnlyIsRejectedWhenComplete() {
        // require-complete=true nhưng thiếu V17/V18.
        assertThrows(IllegalStateException.class, () ->
            MigrationLineageConfiguration.checkHistory(baseline(), true, true));
    }

    // ---------- V17/V18 direct check ----------

    @Test
    void missingV17IsRejectedWhenComplete() {
        // Có V18 nhưng thiếu V17.
        var history = with(baseline(), "18");
        assertThrows(IllegalStateException.class, () ->
            MigrationLineageConfiguration.checkHistory(history, true, true));
    }

    @Test
    void missingV18IsRejectedWhenComplete() {
        var history = with(baseline(), "17");
        assertThrows(IllegalStateException.class, () ->
            MigrationLineageConfiguration.checkHistory(history, true, true));
    }

    @Test
    void fourRowsWithoutV17V18IsRejected() {
        // Bốn dòng history nhưng KHÔNG có V17/V18 — history.size() >= 4 vẫn phải fail.
        var history = with(baseline(), "19", "20");
        assertEquals(4, history.size());
        assertThrows(IllegalStateException.class, () ->
            MigrationLineageConfiguration.checkHistory(history, true, true),
            "history.size() không được dùng thay cho kiểm tra V17/V18");
    }

    @Test
    void bothV17AndV18PresentIsAccepted() {
        var history = with(baseline(), "17", "18");
        assertDoesNotThrow(() ->
            MigrationLineageConfiguration.checkHistory(history, true, true));
    }

    // ---------- Gap / duplicate / order ----------

    @Test
    void unknownVersionIsRejected() {
        var history = with(baseline(), "15");
        assertThrows(IllegalStateException.class, () ->
            MigrationLineageConfiguration.checkHistory(history, true, false));
    }

    @Test
    void duplicateVersionIsRejected() {
        var history = with(baseline(), "17", "17");
        assertThrows(IllegalStateException.class, () ->
            MigrationLineageConfiguration.checkHistory(history, true, false));
    }

    @Test
    void failedMigrationIsRejected() {
        var history = baseline();
        history.add(failed("17"));
        assertThrows(IllegalStateException.class, () ->
            MigrationLineageConfiguration.checkHistory(history, true, false));
    }

    @Test
    void outOfOrderIsRejected() {
        // V20 trước V19.
        var history = with(baseline(), "20", "19");
        assertThrows(IllegalStateException.class, () ->
            MigrationLineageConfiguration.checkHistory(history, true, false));
    }

    @Test
    void wrongCrawlerChecksumIsRejected() {
        var history = new ArrayList<>(List.of(
            row("13", "BASELINE", null),
            row("14", "SQL", 679419338)));
        assertThrows(IllegalStateException.class, () ->
            MigrationLineageConfiguration.checkHistory(history, true, false));
    }

    // ---------- V26 / V27 ----------

    @Test
    void v27WithoutV26IsRejected() {
        // V27 (news) phụ thuộc V26 (coordinate provenance). Database có V27 mà thiếu
        // V26 là dấu hiệu history bị sửa tay hoặc migration bị bỏ qua.
        var history = with(baseline(), "17", "18", "19", "20", "21", "22", "23", "24", "25", "27");
        assertThrows(IllegalStateException.class, () ->
            MigrationLineageConfiguration.checkHistory(history, true, true),
            "V27 thiếu V26 phải bị từ chối");
    }

    @Test
    void v26AloneIsAccepted() {
        // PR #38 chưa merge: database dừng ở V26 vẫn hợp lệ.
        var history = with(baseline(), "17", "18", "19", "20", "21", "22", "23", "24", "25", "26");
        assertDoesNotThrow(() ->
            MigrationLineageConfiguration.checkHistory(history, true, true));
    }

    @Test
    void v26AndV27InOrderIsAccepted() {
        var history = with(baseline(), "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27");
        assertDoesNotThrow(() ->
            MigrationLineageConfiguration.checkHistory(history, true, true));
    }

    @Test
    void v27BeforeV26IsRejected() {
        var history = with(baseline(), "17", "18", "19", "20", "21", "22", "23", "24", "25", "27", "26");
        assertThrows(IllegalStateException.class, () ->
            MigrationLineageConfiguration.checkHistory(history, true, true),
            "V27 trước V26 phải bị từ chối");
    }

    // ---------- Valid stopping points ----------

    @Test
    void stoppingAtV21IsAccepted() {
        var history = with(baseline(), "17", "18", "19", "20", "21");
        assertDoesNotThrow(() ->
            MigrationLineageConfiguration.checkHistory(history, true, true));
    }

    @Test
    void stoppingAtV25IsAccepted() {
        var history = with(baseline(), "17", "18", "19", "20", "21", "22", "23", "24", "25");
        assertDoesNotThrow(() ->
            MigrationLineageConfiguration.checkHistory(history, true, true));
    }

    // ---------- Non-local profile ----------

    @Test
    void nonLocalProfileRejectsCrawlerHistory() {
        assertThrows(IllegalStateException.class, () ->
            MigrationLineageConfiguration.checkHistory(baseline(), false, true));
    }
}
