package vn.smartprop.database;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;

class NewsRightsConstraintVerifierTest {
    private static final String APPROVED = "rights_review_status <> 'APPROVED' OR (rights_reference IS NOT NULL AND REGEXP_LIKE(rights_reference, '[^[:space:]]'))";

    @Test void acceptsExactInvariantAndHarmlessMysqlNormalization() {
        verifyClause(APPROVED, "news_sources", "CHECK", "YES");
        verifyClause("((`rights_review_status` <> _ascii'APPROVED')) or ((`rights_reference` is not null) and regexp_like(`rights_reference`,_utf8mb4'[^[:space:]]'))", "news_sources", "CHECK", "YES");
        String escaped = "(rights_review_status <> _ascii" + (char) 92 + "'APPROVED" + (char) 92 + "') or (rights_reference is not null and regexp_like(rights_reference,_utf8mb4" + (char) 92 + "'[^[:space:]]" + (char) 92 + "'))";
        verifyClause(escaped, "news_sources", "CHECK", "YES");
    }

    @Test void rejectsWrongTableTypeOrUnenforcedMetadata() {
        assertRefused(APPROVED, "news_articles", "CHECK", "YES");
        assertRefused(APPROVED, "news_sources", "UNIQUE", "YES");
        assertRefused(APPROVED, "news_sources", "CHECK", "NO");
    }

    @Test void rejectsMissingOrAmbiguousConstraintMetadata() {
        JdbcTemplate jdbc = jdbc(List.of());
        assertThrows(IllegalStateException.class, () -> NewsRightsConstraintVerifier.requireValid(jdbc));
        JdbcTemplate ambiguous = jdbc(List.of(row("news_sources", "CHECK", "YES", APPROVED), row("news_articles", "CHECK", "YES", APPROVED)));
        assertThrows(IllegalStateException.class, () -> NewsRightsConstraintVerifier.requireValid(ambiguous));
    }

    @Test void rejectsWeakenedOrAlteredExpressions() {
        assertRefused("rights_review_status <> 'APPROVED' OR rights_reference IS NOT NULL OR TRUE", "news_sources", "CHECK", "YES");
        assertRefused("rights_review_status != 'APPROVED' OR (rights_reference IS NOT NULL AND REGEXP_LIKE(rights_reference, '[^[:space:]]'))", "news_sources", "CHECK", "YES");
        assertRefused("rights_review_status <> 'approved' OR (rights_reference IS NOT NULL AND REGEXP_LIKE(rights_reference, '[^[:space:]]'))", "news_sources", "CHECK", "YES");
        assertRefused("rights_review_status <> 'APPROVED' OR (other_reference IS NOT NULL AND REGEXP_LIKE(other_reference, '[^[:space:]]'))", "news_sources", "CHECK", "YES");
        assertRefused("rights_review_status <> 'APPROVED' OR (rights_reference IS NOT NULL AND REGEXP_LIKE(rights_reference, '.*'))", "news_sources", "CHECK", "YES");
    }

    private static void assertRefused(String clause, String table, String type, String enforced) {
        assertThrows(IllegalStateException.class, () -> NewsRightsConstraintVerifier.requireValid(jdbc(List.of(row(table, type, enforced, clause)))));
    }
    private static void verifyClause(String clause, String table, String type, String enforced) {
        assertDoesNotThrow(() -> NewsRightsConstraintVerifier.requireValid(jdbc(List.of(row(table, type, enforced, clause)))));
    }
    private static Map<String, Object> row(String table, String type, String enforced, String clause) {
        return Map.of("table_name", table, "constraint_type", type, "enforced", enforced, "check_clause", clause);
    }
    private static JdbcTemplate jdbc(List<Map<String, Object>> rows) {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForObject("SELECT DATABASE()", String.class)).thenReturn("pr41_local");
        when(jdbc.queryForList(anyString(), eq("pr41_local"), eq(NewsRightsConstraintVerifier.CONSTRAINT))).thenReturn(rows);
        return jdbc;
    }
}
