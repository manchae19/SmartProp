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
import org.junit.jupiter.api.BeforeEach;
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
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import vn.smartprop.common.ApiException;
import vn.smartprop.modules.auth.AuthSession;
import vn.smartprop.modules.auth.SessionPolicy;
import vn.smartprop.modules.auth.SessionRepository;
import vn.smartprop.modules.user.User;
import vn.smartprop.modules.user.UserRepository;

/** Writes only to the disposable Testcontainers database; this never uses the configured SmartProp datasource. */
@Testcontainers(disabledWithoutDocker = true)
class GoogleLinkServiceIntegrationTest {
    @Container static final MySQLContainer<?> MYSQL = new MySQLContainer<>("mysql:8.0.46")
        .withDatabaseName("smartprop_link_test").withUsername("link_test").withPassword("isolated-test-password");

    private JdbcTemplate jdbc;
    private DriverManagerDataSource source;
    private Clock clock;

    @BeforeEach void createIsolatedSchema() {
        source = new DriverManagerDataSource(MYSQL.getJdbcUrl(), MYSQL.getUsername(), MYSQL.getPassword());
        jdbc = new JdbcTemplate(source);
        jdbc.execute("DROP TABLE IF EXISTS user_external_identities");
        jdbc.execute("DROP TABLE IF EXISTS users");
        jdbc.execute("CREATE TABLE users (id BIGINT NOT NULL PRIMARY KEY) ENGINE=InnoDB");
        jdbc.execute("CREATE TABLE user_external_identities (id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, user_id BIGINT NOT NULL, provider VARCHAR(20) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, subject_id VARCHAR(255) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, created_at DATETIME(6) NOT NULL, UNIQUE KEY uq_external_subject (provider,subject_id), UNIQUE KEY uq_external_user_provider (user_id,provider), CONSTRAINT fk_external_identity_owner FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT, CONSTRAINT ck_external_provider CHECK (provider='GOOGLE')) ENGINE=InnoDB");
        jdbc.update("INSERT INTO users(id) VALUES(1),(2)");
        clock = Clock.fixed(Instant.parse("2026-11-24T00:00:00Z"), ZoneOffset.UTC);
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
