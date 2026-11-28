package vn.smartprop.modules.auth.google;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.client.endpoint.OAuth2AccessTokenResponseClient;
import org.springframework.security.oauth2.client.endpoint.OAuth2AuthorizationCodeGrantRequest;
import org.springframework.security.oauth2.client.registration.ClientRegistration;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import vn.smartprop.common.RequestLimits;
import vn.smartprop.modules.user.User;
import vn.smartprop.modules.user.UserRepository;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
    properties = {"server.address=127.0.0.1", "app.refresh.enabled=true", "app.google.enabled=true",
        "spring.flyway.enabled=false", "spring.jpa.hibernate.ddl-auto=validate", "spring.sql.init.mode=never",
        "server.forward-headers-strategy=native", "server.tomcat.remoteip.protocol-header=X-Forwarded-Proto",
        "server.tomcat.remoteip.port-header=X-Forwarded-Port", "server.tomcat.remoteip.internal-proxies=127[.]0[.]0[.]1"})
@ActiveProfiles("standard-migrations")
@Import(GoogleLinkBrowserRuntimeIT.ProviderConfiguration.class)
@EnabledIfEnvironmentVariable(named = "PR48_RUNTIME", matches = "true")
class GoogleLinkBrowserRuntimeIT {
    private static final String EMAIL = "pr48-owner-" + UUID.randomUUID() + "@example.invalid";
    private static final String PASSWORD = "Password-for-isolated-browser-fixture-only";
    private static final String SECOND_PASSWORD = "other-fixture-password";
    private static final String CLIENT = "pr48-controlled-provider.apps.googleusercontent.com";
    private static final String SECRET = UUID.randomUUID().toString();
    private static final String SUBJECT = "pr48-linked-fixture-" + UUID.randomUUID();
    private static GoogleLinkLocalOidcProvider provider;

    @LocalServerPort int backendPort;
    @Autowired UserRepository users;
    @Autowired PasswordEncoder passwords;
    @Autowired JdbcTemplate jdbc;

    @DynamicPropertySource
    static void configure(DynamicPropertyRegistry settings) throws Exception {
        int port = Integer.parseInt(required("PR48_DB_PORT"));
        int front = Integer.parseInt(required("PR48_FRONTEND_PORT"));
        if (port < 49152 || port > 65535 || front < 49152 || front > 65535 || front == port)
            throw new IllegalArgumentException("Runtime fixture requires distinct high loopback ports");
        String marker = required("PR48_DB_MARKER");
        String password = required("PR48_DB_PASSWORD");
        String url = "jdbc:mysql://127.0.0.1:" + port
            + "/smartprop_pr48_runtime?connectionTimeZone=UTC&allowPublicKeyRetrieval=true&useSSL=false";
        var dataSource = new DriverManagerDataSource(url, "pr48_fixture", password);
        verifyIdentity(new JdbcTemplate(dataSource), port, marker);
        // V0 only acknowledges the isolation marker. The complete, unchanged standard SQL follows.
        Flyway.configure().dataSource(dataSource)
            .locations("classpath:database/migrations", "classpath:database/research-migrations/poi")
            .baselineVersion("0").baselineOnMigrate(true).cleanDisabled(true).createSchemas(false).load().migrate();

        boolean secure = System.getenv("PR48_TLS_CERT") != null;
        String origin = (secure ? "https" : "http") + "://127.0.0.1:" + front;
        String redirect = origin + "/api/v1/auth/oauth2/callback/google";
        provider = new GoogleLinkLocalOidcProvider(CLIENT, SECRET, redirect, SUBJECT);
        String jwtSecret = UUID.randomUUID().toString() + UUID.randomUUID();
        settings.add("spring.datasource.url", () -> url);
        settings.add("spring.datasource.username", () -> "pr48_fixture");
        settings.add("spring.datasource.password", () -> password);
        settings.add("app.jwt-secret", () -> jwtSecret);
        settings.add("app.cors-origins", () -> origin);
        settings.add("app.google.frontend-origin", () -> origin);
        settings.add("app.google.redirect-uri", () -> redirect);
        settings.add("app.google.client-id", () -> CLIENT);
        settings.add("app.google.client-secret", () -> SECRET);
        settings.add("app.refresh.secure-cookie", () -> secure);
        settings.add("app.storage-root", () -> required("PR48_STORAGE_ROOT"));
    }

    private static void verifyIdentity(JdbcTemplate db, int port, String marker) {
        assertEquals("smartprop_pr48_runtime", db.queryForObject("SELECT DATABASE()", String.class));
        assertEquals(port, db.queryForObject("SELECT @@port", Integer.class));
        assertTrue(required("PR48_DB_UUID").equals(db.queryForObject("SELECT @@server_uuid", String.class)), "Unexpected server identity");
        assertTrue(Path.of(db.queryForObject("SELECT @@datadir", String.class)).normalize()
            .equals(Path.of(required("PR48_DB_DATADIR")).normalize()), "Unexpected datadir");
        assertEquals("pr48_fixture@127.0.0.1", db.queryForObject("SELECT CURRENT_USER()", String.class));
        assertTrue(marker.matches("[0-9a-f]{32}") && marker.equals(db.queryForObject(
            "SELECT marker FROM pr48_isolation_marker", String.class)), "Fixture identity mismatch");
    }

    @AfterAll static void stopProvider() { if (provider != null) provider.close(); }

    @Test void browsesPasswordLinkingAndSubsequentSignInAgainstFullSchema() throws Exception {
        verifyIdentity(jdbc, Integer.parseInt(required("PR48_DB_PORT")), required("PR48_DB_MARKER"));
        int identitiesBefore = jdbc.queryForObject("SELECT COUNT(*) FROM user_external_identities", Integer.class);

        User owner = account(EMAIL, PASSWORD, "PR48 Fixture Owner", User.Role.BROKER);
        account(GoogleLinkLocalOidcProvider.EMAIL, SECOND_PASSWORD, "PR48 Fixture Other", User.Role.BUYER);
        String id = UUID.randomUUID().toString();
        jdbc.update("""
            INSERT INTO properties(id,owner_id,title,property_type,transaction_type,price,price_unit,area_sqm,location)
            VALUES(?,?,?,'HOUSE','SALE',2000000000,'TOTAL',100,ST_GeomFromText('POINT(108.2 16.05)',4326,'axis-order=long-lat'))
            """, id, owner.id, "PR48 synthetic home");
        jdbc.update("INSERT INTO saved_properties(user_id,property_id) VALUES(?,?)", owner.id, id);
        jdbc.update("""
            INSERT INTO valuation_history(id,user_id,request_key,request_sha256,input_snapshot,prediction_snapshot,created_at)
            VALUES(?,?,?,?,JSON_OBJECT(),JSON_OBJECT(),UTC_TIMESTAMP(6))
            """, UUID.randomUUID().toString(), owner.id, UUID.randomUUID().toString(), "0".repeat(64));
        var before = snapshots();

        var runner = new ProcessBuilder("node", "frontend/tests/browser/pr48-oauth-runtime.cjs")
            .directory(Path.of("..").toRealPath().toFile()).inheritIO();
        runner.environment().put("PR48_BACKEND_PORT", Integer.toString(backendPort));
        runner.environment().put("PR48_EXPECTED_EMAIL", EMAIL);
        runner.environment().put("PR48_FIXTURE_PASSWORD", PASSWORD);
        runner.environment().put("PR48_REVOKE_EMAIL", GoogleLinkLocalOidcProvider.EMAIL);
        runner.environment().put("PR48_REVOKE_PASSWORD", SECOND_PASSWORD);
        for (String field : List.of("PR48_DB_PASSWORD", "PR48_DB_MARKER", "SMARTPROP_PR40_FIXTURE_MARKER"))
            runner.environment().remove(field);
        Process browser = runner.start();
        try {
            assertTrue(browser.waitFor(100, TimeUnit.SECONDS), "Browser fixture timed out");
            assertEquals(0, browser.exitValue(), "Browser fixture failed");
        } finally {
            if (browser.isAlive()) browser.destroyForcibly();
        }
        assertEquals(3, provider.exchanges(), "Expected PKCE exchanges for linking, sign-in and a revoked session");
        assertEquals(List.of(owner.id), jdbc.queryForList(
            "SELECT user_id FROM user_external_identities WHERE provider='GOOGLE' AND subject_id=?", Long.class, SUBJECT));
        assertEquals(identitiesBefore + 1, jdbc.queryForObject("SELECT COUNT(*) FROM user_external_identities", Integer.class));
        assertTrue(before.equals(snapshots()), "Account, listing, favorite or valuation rows changed");
    }

    private User account(String email, String password, String name, User.Role role) {
        var user = new User();
        user.email = email;
        user.passwordHash = passwords.encode(password);
        user.fullName = name;
        user.role = role;
        user.status = User.Status.ACTIVE;
        user.emailVerifiedAt = Instant.now();
        return users.saveAndFlush(user);
    }

    private List<List<Map<String, Object>>> snapshots() {
        return List.of("SELECT * FROM users ORDER BY id", "SELECT * FROM properties ORDER BY id",
                "SELECT * FROM saved_properties ORDER BY user_id, property_id", "SELECT * FROM valuation_history ORDER BY id")
            .stream().map(sql -> {
                var rows = jdbc.queryForList(sql);
                for (var row : rows) row.replaceAll((column, value) -> value instanceof byte[] bytes
                    ? java.util.HexFormat.of().formatHex(bytes) : value);
                return rows;
            }).toList();
    }

    static String required(String name) {
        String value = System.getenv(name);
        if (value == null || value.isBlank()) throw new IllegalArgumentException("Missing fixture variable " + name);
        return value;
    }

    @TestConfiguration
    static class ProviderConfiguration {
        @Bean @Primary GoogleOAuthConfigurer controlledProvider(GoogleSettings settings, GoogleFlowStore login,
            GoogleLinkFlowStore link, RequestLimits limits, Clock clock, ObjectMapper json,
            ObjectProvider<OAuth2AccessTokenResponseClient<OAuth2AuthorizationCodeGrantRequest>> clients) {
            return new GoogleOAuthConfigurer(settings, login, link, limits, clock, json, clients, true) {
                @Override public ClientRegistration registration() {
                    return ClientRegistration.withClientRegistration(super.registration())
                        .authorizationUri(provider.origin() + "/authorize")
                        .tokenUri(provider.origin() + "/token")
                        .jwkSetUri(provider.origin() + "/keys")
                        .build();
                }
            };
        }
    }
}
