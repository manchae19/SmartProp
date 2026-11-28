package vn.smartprop.comparable;

import java.math.BigDecimal;
import java.util.List;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import vn.smartprop.modules.property.PropertyRepository;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static vn.smartprop.comparable.ComparableDtos.*;

/** Invoked explicitly against a freshly initialized loopback server with only synthetic rows. */
@EnabledIfEnvironmentVariable(named = "WP02_FIXTURE_UUID", matches = "[a-f0-9-]{36}")
class ComparableSyntheticMysqlIT {
    private static final String DISTRICT = "Hải Châu";
    private static final String WARD = "Hòa Cường Bắc";
    private static final BigDecimal REF_AREA = BigDecimal.valueOf(80);
    private static final BigDecimal MIN_PRICE = BigDecimal.valueOf(200_000_000);
    private static final BigDecimal MAX_PRICE = BigDecimal.valueOf(1_000_000_000_000L);
    private static final SubjectIdentity SUBJECT = new SubjectIdentity(901L, "A", "own", "self", null);
    private static JdbcTemplate jdbc;
    private static ComparableCandidateRepository repo;

    @BeforeAll
    static void fixture() {
        int port = Integer.parseInt(System.getenv("WP02_FIXTURE_PORT"));
        if (port < 49152 || port > 65535) throw new IllegalArgumentException("Expected ephemeral fixture port");
        var source = new DriverManagerDataSource("jdbc:mysql://127.0.0.1:" + port
            + "/wp02_phase_b_fixture?connectTimeout=2000&socketTimeout=5000", "root", "");
        jdbc = new JdbcTemplate(source);
        assertThat(jdbc.queryForObject("SELECT @@server_uuid", String.class)).isEqualTo(System.getenv("WP02_FIXTURE_UUID"));
        repo = new ComparableCandidateRepository(new NamedParameterJdbcTemplate(source));

        jdbc.execute("""
            CREATE TABLE properties (
                id VARCHAR(36) PRIMARY KEY, property_type VARCHAR(30), district VARCHAR(100), ward VARCHAR(100),
                area_sqm DECIMAL(12,2), price DECIMAL(18,2), bedrooms SMALLINT, status VARCHAR(30),
                deleted_at DATETIME(6), expires_at DATETIME(6), transaction_type VARCHAR(10), price_unit VARCHAR(20),
                currency CHAR(3)
            ) COLLATE utf8mb4_0900_ai_ci
            """);
        jdbc.execute("""
            CREATE TABLE external_listings (
                id BIGINT PRIMARY KEY, source VARCHAR(50), category VARCHAR(50), district VARCHAR(100),
                area_sqm DECIMAL(12,2), price DECIMAL(18,2), quality_status VARCHAR(50), detail_url TEXT,
                source_listing_id VARCHAR(100), duplicate_group VARCHAR(100), verification_status VARCHAR(50),
                quality_issues JSON, is_protected_holdout BOOLEAN, is_duplicate BOOLEAN, transaction_type VARCHAR(10)
            ) COLLATE utf8mb4_0900_ai_ci
            """);

        // Each invalid row would win an area-first cap ahead of the valid 81 m² rows.
        jdbc.update("""
            INSERT INTO properties
            WITH RECURSIVE seq(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM seq WHERE n<210)
            SELECT CONCAT('invalid-',n), 'HOUSE', ?, ?, 80, 3000000000, 3, 'PUBLISHED', NULL,
                UTC_TIMESTAMP(6) - INTERVAL 1 DAY, 'SALE', 'TOTAL', 'VND' FROM seq
            """, DISTRICT, WARD);
        jdbc.update("""
            INSERT INTO external_listings
            WITH RECURSIVE seq(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM seq WHERE n<410)
            SELECT n, 'A', 'Nhà ở', ?, 80, 3000000000, 'VALID', '', CAST(n AS CHAR), NULL,
                'UNVERIFIED', JSON_ARRAY(), FALSE, FALSE, 'SALE' FROM seq
            """, DISTRICT);
        jdbc.update("""
            INSERT INTO properties VALUES
            ('valid-a','HOUSE',?,?,81,3000000000,3,'PUBLISHED',NULL,NULL,'SALE','TOTAL','VND'),
            ('valid-b','HOUSE',?,?,81,6000000000,3,'PUBLISHED',NULL,UTC_TIMESTAMP(6)+INTERVAL 1 DAY,'SALE','TOTAL','VND'),
            ('wrong-ward','HOUSE',?,'Hòa Cường Nam',80,3000000000,3,'PUBLISHED',NULL,NULL,'SALE','TOTAL','VND'),
            ('accent-district','HOUSE','Hai Chau',?,80,3000000000,3,'PUBLISHED',NULL,NULL,'SALE','TOTAL','VND'),
            ('adjacent','HOUSE','Thanh Khê',?,80,3000000000,3,'PUBLISHED',NULL,NULL,'SALE','TOTAL','VND'),
            ('villa','VILLA',?,?,80,3000000000,3,'PUBLISHED',NULL,NULL,'SALE','TOTAL','VND'),
            ('draft','HOUSE',?,?,80,3000000000,3,'DRAFT',NULL,NULL,'SALE','TOTAL','VND'),
            ('hidden','HOUSE',?,?,80,3000000000,3,'HIDDEN',NULL,NULL,'SALE','TOTAL','VND'),
            ('deleted','HOUSE',?,?,80,3000000000,3,'PUBLISHED',UTC_TIMESTAMP(6),NULL,'SALE','TOTAL','VND'),
            ('rent','HOUSE',?,?,80,3000000000,3,'PUBLISHED',NULL,NULL,'RENT','PER_MONTH','VND'),
            ('currency','HOUSE',?,?,80,3000000000,3,'PUBLISHED',NULL,NULL,'SALE','TOTAL','USD')
            """, DISTRICT, WARD, DISTRICT, WARD, DISTRICT, WARD, WARD, DISTRICT, WARD, DISTRICT, WARD,
                DISTRICT, WARD, DISTRICT, WARD, DISTRICT, WARD, DISTRICT, WARD);
        jdbc.update("""
            INSERT INTO external_listings VALUES
            (901,'A','Nhà ở',?,80,3000000000,'VALID','', 'own',NULL,'VERIFIED',JSON_ARRAY(),FALSE,FALSE,'SALE'),
            (902,'a','Nhà ở',?,80,3000000000,'VALID','', ' own ',NULL,'VERIFIED',JSON_ARRAY(),FALSE,FALSE,'SALE'),
            (903,'B','Nhà ở',?,81,3000000000,'VALID','', 'own',NULL,'VERIFIED',JSON_ARRAY(),FALSE,FALSE,'SALE'),
            (904,'A','Nhà ở',?,81,3000000000,'VALID','', 'other','','VERIFIED',JSON_ARRAY(),FALSE,FALSE,'SALE'),
            (905,'A','Nhà ở',?,80,3000000000,'VALID','', 'bad',NULL,'VERIFIED',JSON_ARRAY('X'),FALSE,FALSE,'SALE'),
            (906,'A','Nhà ở',?,80,3000000000,'VALID','', 'bad','held','VERIFIED',JSON_ARRAY(),FALSE,FALSE,'SALE'),
            (907,'A','Nhà ở',?,80,3000000000,'VALID','', 'bad','held','VERIFIED',JSON_ARRAY(),TRUE,FALSE,'SALE'),
            (908,'A','Đất nền',?,80,3000000000,'VALID','', 'bad',NULL,'VERIFIED',JSON_ARRAY(),FALSE,FALSE,'SALE'),
            (909,'A','Nhà ở',?,80,3000000000,'VALID','', 'bad','','VERIFIED',JSON_ARRAY(),TRUE,FALSE,'SALE')
            """, DISTRICT, DISTRICT, DISTRICT, DISTRICT, DISTRICT, DISTRICT, DISTRICT, DISTRICT, DISTRICT);
        jdbc.execute("ALTER TABLE properties ADD COLUMN project_id CHAR(36)");
    }

    @Test
    void publicSqlFiltersBeforeCapsAndUsesStableTieBreakers() {
        var search = search(WARD, "valid-a", MAX_PRICE);
        var rows = repo.propertyCandidates(search, 1);
        assertThat(rows).extracting(ComparableCandidateRepository.PropertyRow::id).containsExactly("valid-b");
        assertThat(repo.propertyCandidates(search(WARD, null, MAX_PRICE), 2))
            .extracting(ComparableCandidateRepository.PropertyRow::id).containsExactly("valid-a", "valid-b");
        assertThat(repo.propertyCandidates(search(WARD, null, MIN_PRICE), 2)).isEmpty();
        assertThat(repo.externalCandidates(search, "Nhà ở", 400)).isEmpty();
        assertThat(repo.externalCandidates(search(null, null, MAX_PRICE), "Nhà ở", 1))
            .extracting(ComparableCandidateRepository.ExternalRow::id).containsExactly(903L);
        assertThat(repo.externalCandidates(search(null, null, MAX_PRICE), "Nhà ở", 400))
            .extracting(ComparableCandidateRepository.ExternalRow::id).containsExactly(903L, 904L);
    }

    @Test
    void safeWireServiceKeepsBuyerBudgetAndTargetPriceInvarianceWithoutResearchSchema() {
        // No TiniX staging table is created. Any accidental research query fails this test.
        var service = new ComparableRankingService(repo, new ComparableEligibilityService(), mock(PropertyRepository.class), true);
        var first = service.rank(request("1500000000", Purpose.VALUATION_SUPPORT, null));
        var second = service.rank(request("18000000000", Purpose.VALUATION_SUPPORT, null));
        assertThat(first).isEqualTo(second);
        assertThat(first.comparables()).extracting(Candidate::candidateId)
            .containsExactly("property:wrong-ward", "property:valid-a", "property:valid-b", "external:903", "external:904");
        assertThat(first.comparables()).allSatisfy(row -> assertThat(row.scoreBreakdown()).doesNotContainKey("price"));
        var buyer = service.rank(request("18000000000", Purpose.BUYER_BUDGET_SEARCH, BigDecimal.valueOf(3_000_000_000L)));
        assertThat(buyer.comparables()).extracting(Candidate::candidateId)
            .containsExactly("property:wrong-ward", "property:valid-a", "external:903", "external:904");
        assertThat(buyer.eligibleCountsBySource()).containsOnlyKeys("SMARTPROP", "EXTERNAL_LISTING");
    }

    @Test
    void refillPassesDuplicateHeavyAndCanonicalSelfMatchPrefixes() {
        jdbc.update("""
            INSERT INTO external_listings
            WITH RECURSIVE seq(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM seq WHERE n<820)
            SELECT 2000+n, 'A', 'Nhà ở', IF(n<=410,'Liên Chiểu','Ngũ Hành Sơn'), IF(MOD(n-1,410)<405,80,81),
                3000000000, 'VALID',
                IF(MOD(n-1,410)<405,'https://example.test/listings/77', CONCAT('https://example.test/listings/',n+100)),
                CAST(n AS CHAR), NULL, 'VERIFIED', JSON_ARRAY(), FALSE, FALSE, 'SALE' FROM seq
            """);
        var service = new ComparableRankingService(repo, new ComparableEligibilityService(), mock(PropertyRepository.class), false);
        var subject = new SubjectIdentity(null, null, null, null, "https://example.test/listings/77?utm_source=search");
        var canonical = service.rank(new Request(null, "HOUSE", "Liên Chiểu", null, REF_AREA, null, null, null, 5,
            false, Purpose.VALUATION_SUPPORT, null, subject));
        assertThat(canonical.comparables()).extracting(Candidate::candidateId)
            .containsExactly("external:2406","external:2407","external:2408","external:2409","external:2410");
        var duplicates = service.rank(new Request(null, "HOUSE", "Ngũ Hành Sơn", null, REF_AREA, null, null, null, 5,
            false, Purpose.VALUATION_SUPPORT, null, null));
        assertThat(duplicates.comparables()).extracting(Candidate::candidateId)
            .containsExactly("external:2411","external:2816","external:2817","external:2818","external:2819");
        assertThat(duplicates.warnings()).noneMatch(w -> w.startsWith("SCAN_LIMIT_REACHED"));
    }

    private static ComparableCandidateRepository.Search search(String ward, String propertyId, BigDecimal maxPrice) {
        return new ComparableCandidateRepository.Search(DISTRICT, ward, "HOUSE", REF_AREA, BigDecimal.valueOf(32),
            BigDecimal.valueOf(200), MIN_PRICE, maxPrice, propertyId, SUBJECT);
    }

    private static Request request(String target, Purpose purpose, BigDecimal budget) {
        return new Request(null, "HOUSE", DISTRICT, null, REF_AREA, new BigDecimal(target), null, null, 5,
            false, purpose, budget, SUBJECT);
    }
}
