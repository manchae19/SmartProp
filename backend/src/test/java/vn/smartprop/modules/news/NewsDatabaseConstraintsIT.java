package vn.smartprop.modules.news;

import java.util.UUID;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.dao.DataIntegrityViolationException;
import static org.junit.jupiter.api.Assertions.*;

/** Existing V27 constraints, against synthetic data only. Approval-reference CHECK remains blocked. */
@SpringBootTest
@Transactional
@EnabledIfEnvironmentVariable(named="DB_URL",matches=".+")
class NewsDatabaseConstraintsIT {
    @Autowired JdbcTemplate jdbc;
    String source;
    @BeforeEach void sourceFixture() {
        vn.smartprop.testing.Pr41DatabaseTestSafety.require(jdbc);
        source=UUID.randomUUID().toString();
        jdbc.update("INSERT INTO news_sources(id,source_code,name,publisher,website_url,feed_url,rights_review_status,rights_reference,enabled) VALUES (?,?, 'SYNTHETIC TEST ONLY','SYNTHETIC TEST ONLY','https://example.invalid',?,'APPROVED','synthetic-fixture-only',1)",source,source,"https://example.invalid/"+source);
    }
    void article(String sourceId,String url,String guid,String status) {
        jdbc.update("INSERT INTO news_articles(id,source_id,canonical_url,canonical_url_hash,external_id,title,category,region,fetched_at,first_seen_at,last_seen_at,publication_status) VALUES (?,?,?,?,?,'SYNTHETIC TEST ONLY','MARKET','DA_NANG',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),?)",UUID.randomUUID().toString(),sourceId,url,NewsText.sha256(url),guid,status);
    }
    @Test void rejectsDuplicateUrlWithinSource() {
        article(source,"https://example.invalid/article","guid-a","VISIBLE");
        assertThrows(DataIntegrityViolationException.class,()->article(source,"https://example.invalid/article","guid-b","VISIBLE"));
    }
    @Test void rejectsDuplicateExternalIdWithinSource() {
        article(source,"https://example.invalid/a","guid","VISIBLE");
        assertThrows(DataIntegrityViolationException.class,()->article(source,"https://example.invalid/b","guid","VISIBLE"));
    }
    @Test void rejectsMissingSourceForeignKey() {
        assertThrows(DataIntegrityViolationException.class,()->article(UUID.randomUUID().toString(),"https://example.invalid/a",null,"VISIBLE"));
    }
    @Test void rejectsInvalidPublicationStatus() {
        var error=assertThrows(org.springframework.dao.DataAccessException.class,()->article(source,"https://example.invalid/a",null,"INVALID"));
        assertEquals(3819,((java.sql.SQLException)error.getMostSpecificCause()).getErrorCode());
    }
    @Test void rejectsInvalidRightsStatus() {
        var error=assertThrows(org.springframework.dao.DataAccessException.class,()->jdbc.update("UPDATE news_sources SET rights_review_status='INVALID' WHERE id=?",source));
        assertEquals(3819,((java.sql.SQLException)error.getMostSpecificCause()).getErrorCode());
    }
}
