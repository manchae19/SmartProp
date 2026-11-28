package vn.smartprop.modules.auth.google;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.Callable;
import java.util.concurrent.Executors;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Assumptions;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.datasource.init.ResourceDatabasePopulator;
import org.testcontainers.DockerClientFactory;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.aop.framework.ProxyFactory;
import org.springframework.aop.support.AopUtils;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.transaction.annotation.AnnotationTransactionAttributeSource;
import org.springframework.transaction.interceptor.TransactionInterceptor;
import org.testcontainers.containers.MySQLContainer;
import vn.smartprop.common.ApiException;
import vn.smartprop.modules.auth.AuthSession;
import vn.smartprop.modules.auth.SessionPolicy;
import vn.smartprop.modules.auth.SessionRepository;
import vn.smartprop.modules.user.User;
import vn.smartprop.modules.user.UserRepository;

/** Defaults to disposable Testcontainers. A standalone test server requires a matching fixture marker. */
class GoogleLinkServiceIntegrationTest {
    private static MySQLContainer<?> container;
    private static DriverManagerDataSource source;
    private JdbcTemplate jdbc;
    private Clock clock;

    @BeforeAll static void connectOnlyToFixture() {
        String target = System.getenv("SMARTPROP_PR40_TEST_DB");
        if (target == null) {
            Assumptions.assumeTrue(DockerClientFactory.instance().isDockerAvailable(), "Requires isolated MySQL");
            container = new MySQLContainer<>("mysql:8.0.46")
                .withDatabaseName("smartprop_link_test").withUsername("link_test").withPassword("isolated-test-password");
            container.start();
            source = new DriverManagerDataSource(container.getJdbcUrl(), container.getUsername(), container.getPassword());
            return;
        }
        var match = java.util.regex.Pattern.compile("([1-9][0-9]{4})/smartprop_pr40_test").matcher(target);
        if (!match.matches() || Integer.parseInt(match.group(1)) > 65535)
            throw new IllegalArgumentException("Expected dedicated high-port loopback MySQL fixture");
        String proof = System.getenv("SMARTPROP_PR40_FIXTURE_MARKER");
        if (proof == null || !proof.matches("[a-f0-9]{32}")) throw new IllegalArgumentException("Missing fixture marker");
        source = new DriverManagerDataSource("jdbc:mysql://127.0.0.1:" + target
            + "?connectionTimeZone=UTC&allowPublicKeyRetrieval=true&useSSL=false", "root", "");
        String actual = new JdbcTemplate(source).queryForObject("SELECT marker FROM pr40_isolation_marker", String.class);
        assertEquals(proof, actual, "Refusing to write without the marker created by the fixture launcher");
    }

    @AfterAll static void stopContainer() {
        if (container != null) container.stop();
    }

    @BeforeEach void createIsolatedSchema() {
        jdbc = new JdbcTemplate(source);
        jdbc.execute("DROP TABLE IF EXISTS user_avatars, user_external_identities, fixture_listings, fixture_favorites, fixture_valuations, users");
        jdbc.execute("CREATE TABLE users (id BIGINT NOT NULL PRIMARY KEY, email VARCHAR(254), password_hash VARCHAR(100), role VARCHAR(20), status VARCHAR(20), full_name VARCHAR(100)) ENGINE=InnoDB");
        jdbc.execute("CREATE TABLE fixture_listings (id BIGINT NOT NULL PRIMARY KEY, owner_id BIGINT NOT NULL, FOREIGN KEY(owner_id) REFERENCES users(id)) ENGINE=InnoDB");
        jdbc.execute("CREATE TABLE fixture_favorites (user_id BIGINT NOT NULL, listing_id BIGINT NOT NULL, PRIMARY KEY(user_id,listing_id)) ENGINE=InnoDB");
        jdbc.execute("CREATE TABLE fixture_valuations (id BIGINT NOT NULL PRIMARY KEY, user_id BIGINT NOT NULL, price DECIMAL(18,2), FOREIGN KEY(user_id) REFERENCES users(id)) ENGINE=InnoDB");
        new ResourceDatabasePopulator(new ClassPathResource("database/migrations/V15__profile_avatar_and_google_identity.sql")).execute(source);
        jdbc.update("INSERT INTO users VALUES(1,'a@example.test','fixture-hash','BROKER','ACTIVE','Owner'),(2,'b@example.test','other-hash','BUYER','ACTIVE','Buyer')");
        jdbc.update("INSERT INTO fixture_listings VALUES(15,1)");
        jdbc.update("INSERT INTO fixture_favorites VALUES(1,15)");
        jdbc.update("INSERT INTO fixture_valuations VALUES(21,1,2000000000.00)");
        clock = Clock.fixed(Instant.parse("2026-11-24T00:00:00Z"), ZoneOffset.UTC);
    }

    @Test void preservesAccountAndRelatedData() {
        var accounts = jdbc.queryForList("SELECT * FROM users ORDER BY id");
        var listings = jdbc.queryForList("SELECT * FROM fixture_listings");
        var favorites = jdbc.queryForList("SELECT * FROM fixture_favorites");
        var valuations = jdbc.queryForList("SELECT * FROM fixture_valuations");
        var profile = new GoogleProfile("fresh-subject", "b@example.test", "Another name");
        serviceFor(1, "session-1").complete(new GoogleLinkFlowStore.Ticket(profile, 1L, "session-1"), jwt(1, "session-1"));

        assertEquals(accounts, jdbc.queryForList("SELECT * FROM users ORDER BY id"));
        assertEquals(listings, jdbc.queryForList("SELECT * FROM fixture_listings"));
        assertEquals(favorites, jdbc.queryForList("SELECT * FROM fixture_favorites"));
        assertEquals(valuations, jdbc.queryForList("SELECT * FROM fixture_valuations"));
        assertEquals(1L, jdbc.queryForObject("SELECT user_id FROM user_external_identities WHERE provider='GOOGLE' AND subject_id='fresh-subject'", Long.class));
    }

    @Test void rollsBackIdentityWhenRuntimeFailureOccursAfterInsert() {
        JdbcTemplate failAfterInsert = new JdbcTemplate(source) {
            @Override public int update(String sql, Object... args) {
                int changed = super.update(sql, args);
                if (sql.startsWith("INSERT INTO user_external_identities"))
                    throw new IllegalStateException("simulated failure after identity insert");
                return changed;
            }
        };
        GoogleLinkService service = serviceFor(1L, "session-1", failAfterInsert);
        var ticket = new GoogleLinkFlowStore.Ticket(new GoogleProfile("rollback-subject", "one@example.test", "One"), 1L, "session-1");

        assertTrue(AopUtils.isAopProxy(service), "GoogleLinkService must be called through a Spring transaction proxy");
        assertThrows(IllegalStateException.class, () -> service.complete(ticket, jwt(1L, "session-1")));
        assertEquals(0, jdbc.queryForObject("SELECT COUNT(*) FROM user_external_identities WHERE provider='GOOGLE' AND subject_id='rollback-subject'", Integer.class));
    }

    @Test void persistsVerifiedSubjectAndUniqueConstraintAllowsOnlyOneConcurrentOwner() throws Exception {
        GoogleLinkService firstService = serviceFor(1L, "session-1");
        GoogleLinkService secondService = serviceFor(2L, "session-2");
        var first = new GoogleLinkFlowStore.Ticket(new GoogleProfile("same-google-subject", "one@example.test", "One"), 1L, "session-1");
        var second = new GoogleLinkFlowStore.Ticket(new GoogleProfile("same-google-subject", "two@example.test", "Two"), 2L, "session-2");
        Jwt firstJwt = jwt(1L, "session-1"), secondJwt = jwt(2L, "session-2");

        try (var executor = Executors.newFixedThreadPool(2)) {
            List<Callable<Boolean>> calls = List.of(
                () -> complete(firstService, first, firstJwt),
                () -> complete(secondService, second, secondJwt));
            long successes = executor.invokeAll(calls).stream().filter(future -> {
                try { return future.get(); } catch (Exception failure) { throw new RuntimeException(failure); }
            }).count();
            assertEquals(1, successes);
        }
        assertEquals(1, jdbc.queryForObject("SELECT COUNT(*) FROM user_external_identities WHERE provider='GOOGLE' AND subject_id='same-google-subject'", Integer.class));
        assertEquals(1, jdbc.queryForObject("SELECT COUNT(*) FROM user_external_identities WHERE user_id=1 AND provider='GOOGLE' OR user_id=2 AND provider='GOOGLE'", Integer.class));
    }

    @Test void foreignKeyRejectsMissingSmartPropOwnerWithoutLeavingAnIdentity() {
        GoogleLinkService service = serviceFor(1L, "session-1");
        var ticket = new GoogleLinkFlowStore.Ticket(new GoogleProfile("orphan", "one@example.test", "One"), 1L, "session-1");
        // The service's owner comes from the authenticated repository. Remove it from the isolated DB to exercise the FK.
        jdbc.update("DELETE FROM fixture_listings WHERE owner_id=1");
        jdbc.update("DELETE FROM fixture_valuations WHERE user_id=1");
        jdbc.update("DELETE FROM users WHERE id=1");
        ApiException conflict = assertThrows(ApiException.class, () -> service.complete(ticket, jwt(1L, "session-1")));
        assertEquals("GOOGLE_IDENTITY_CONFLICT", conflict.code);
        assertEquals(0, jdbc.queryForObject("SELECT COUNT(*) FROM user_external_identities", Integer.class));
    }

    private boolean complete(GoogleLinkService service, GoogleLinkFlowStore.Ticket ticket, Jwt jwt) {
        try { service.complete(ticket, jwt); return true; }
        catch (ApiException expectedConflict) { return false; }
    }

    private GoogleLinkService serviceFor(long id, String sessionId) {
        return serviceFor(id, sessionId, jdbc);
    }

    private GoogleLinkService serviceFor(long id, String sessionId, JdbcTemplate serviceJdbc) {
        User user = new User(); user.id = id; user.email = id + "@example.test"; user.passwordHash = "hash";
        user.role = User.Role.BROKER; user.status = User.Status.ACTIVE; user.tokenVersion = 0;
        AuthSession session = new AuthSession(); session.id = sessionId; session.userId = id;
        session.createdAt = clock.instant().minusSeconds(60); session.expiresAt = clock.instant().plusSeconds(600); session.lastUsedAt = clock.instant();
        UserRepository users = mock(UserRepository.class); when(users.lockById(id)).thenReturn(Optional.of(user));
        SessionRepository sessions = mock(SessionRepository.class); when(sessions.lockById(sessionId)).thenReturn(Optional.of(session));
        SessionPolicy policy = new SessionPolicy(clock);
        var target = new GoogleLinkService(serviceJdbc, users, sessions, policy, mock(PasswordEncoder.class), clock);
        var proxy = new ProxyFactory(target);
        proxy.setProxyTargetClass(true);
        proxy.addAdvice(new TransactionInterceptor(new DataSourceTransactionManager(source), new AnnotationTransactionAttributeSource()));
        return (GoogleLinkService) proxy.getProxy();
    }

    private Jwt jwt(long userId, String sessionId) {
        return Jwt.withTokenValue("isolated-test-token").header("alg", "HS256").subject(Long.toString(userId))
            .claim("jti", sessionId).claim("ver", 0).build();
    }
}
