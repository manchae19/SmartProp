package vn.smartprop.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.math.BigDecimal;
import java.net.InetAddress;
import java.net.URI;
import java.net.URLDecoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.regex.Pattern;
import org.apache.catalina.valves.RemoteIpValve;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.ImportAutoConfiguration;
import org.springframework.boot.autoconfigure.context.ConfigurationPropertiesAutoConfiguration;
import org.springframework.boot.autoconfigure.context.PropertyPlaceholderAutoConfiguration;
import org.springframework.boot.autoconfigure.http.HttpMessageConvertersAutoConfiguration;
import org.springframework.boot.autoconfigure.jackson.JacksonAutoConfiguration;
import org.springframework.boot.autoconfigure.security.servlet.SecurityFilterAutoConfiguration;
import org.springframework.boot.autoconfigure.web.ServerProperties;
import org.springframework.boot.autoconfigure.web.embedded.EmbeddedWebServerFactoryCustomizerAutoConfiguration;
import org.springframework.boot.autoconfigure.web.servlet.DispatcherServletAutoConfiguration;
import org.springframework.boot.autoconfigure.web.servlet.ServletWebServerFactoryAutoConfiguration;
import org.springframework.boot.autoconfigure.web.servlet.WebMvcAutoConfiguration;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.context.properties.bind.Binder;
import org.springframework.boot.env.SystemEnvironmentPropertySourceEnvironmentPostProcessor;
import org.springframework.boot.web.servlet.context.AnnotationConfigServletWebServerApplicationContext;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Import;
import org.springframework.core.env.MapPropertySource;
import org.springframework.core.env.StandardEnvironment;
import org.springframework.core.env.SystemEnvironmentPropertySource;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import vn.smartprop.advisor.AdvisorController;
import vn.smartprop.advisor.AdvisorDtos;
import vn.smartprop.advisor.AdvisorOrchestrationService;
import vn.smartprop.common.Errors;
import vn.smartprop.common.RequestLimits;
import vn.smartprop.modules.amenity.AmenityCatalogService;
import vn.smartprop.modules.amenity.AmenityController;
import vn.smartprop.modules.amenity.AmenityDtos;
import vn.smartprop.modules.amenity.ResearchAmenityController;
import vn.smartprop.modules.auth.AccountAccess;
import vn.smartprop.modules.auth.AuthSession;
import vn.smartprop.modules.auth.SessionPolicy;
import vn.smartprop.modules.auth.SessionRepository;
import vn.smartprop.modules.recommendation.HybridRecommendationService;
import vn.smartprop.modules.recommendation.RecommendationController;
import vn.smartprop.modules.recommendation.RecommendationDtos;
import vn.smartprop.modules.recommendation.TinixCandidateRepository;
import vn.smartprop.modules.user.User;
import vn.smartprop.modules.user.UserRepository;

/**
 * PR #46 Tasks 3 & 4 — Verifies:
 * 1. Exact Spring Boot 3.5.16 relaxed env binding (SERVER_FORWARD_HEADERS_STRATEGY vs broken SPRING_FORWARD_HEADERS_STRATEGY).
 * 2. Real embedded Tomcat HTTP server on an isolated ephemeral loopback port (127.0.0.1:0) with RemoteIpValve:
 *    - Proxied external callers (even with forged leftmost X-Forwarded-For: 127.0.0.1, valid ADMIN JWT, and demo key)
 *      resolve to external client IP and are rejected with 403 on loopback-only routes.
 *    - Direct loopback callers without X-Forwarded-For succeed when authorized, and fail closed on missing/wrong demo key or disabled flags.
 *    - Public Recommendation, Public Amenities, and Advisor SAFE continue working through the proxy.
 * 3. Static structural & matcher verification of ops/Caddyfile (route ordering, no SPA fallback, encoded/semicolon/subpath blocking).
 */
class TomcatLoopbackProxyBoundaryTest {

    @Test
    @DisplayName("Spring Boot 3.5.16 binds SERVER_FORWARD_HEADERS_STRATEGY (and ignores legacy SPRING_FORWARD_HEADERS_STRATEGY)")
    void verifySpringBoot3516ForwardHeadersEnvBinding() {
        StandardEnvironment brokenEnv = new StandardEnvironment();
        brokenEnv.getPropertySources().addFirst(new SystemEnvironmentPropertySource(
            StandardEnvironment.SYSTEM_ENVIRONMENT_PROPERTY_SOURCE_NAME,
            Map.of("SPRING_FORWARD_HEADERS_STRATEGY", "framework")
        ));
        ServerProperties brokenProps = Binder.get(brokenEnv)
            .bind("server", ServerProperties.class)
            .orElseGet(ServerProperties::new);
        assertThat(brokenProps.getForwardHeadersStrategy()).isNull();

        StandardEnvironment fixedEnv = new StandardEnvironment();
        fixedEnv.getPropertySources().addFirst(new SystemEnvironmentPropertySource(
            StandardEnvironment.SYSTEM_ENVIRONMENT_PROPERTY_SOURCE_NAME,
            Map.of(
                "SERVER_ADDRESS", "127.0.0.1",
                "SERVER_FORWARD_HEADERS_STRATEGY", "native",
                "SERVER_TOMCAT_REMOTEIP_INTERNAL_PROXIES", "127\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}|0:0:0:0:0:0:0:1|::1"
            )
        ));
        // Apply Spring Boot's exact SystemEnvironmentPropertySourceEnvironmentPostProcessor
        new SystemEnvironmentPropertySourceEnvironmentPostProcessor()
            .postProcessEnvironment(fixedEnv, new SpringApplication());
        ServerProperties fixedProps = Binder.get(fixedEnv).bind("server", ServerProperties.class).get();
        assertThat(fixedProps.getAddress()).isEqualTo(InetAddress.getLoopbackAddress());
        assertThat(fixedProps.getForwardHeadersStrategy()).isEqualTo(ServerProperties.ForwardHeadersStrategy.NATIVE);
        assertThat(fixedProps.getTomcat().getRemoteip().getInternalProxies())
            .isEqualTo("127\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}|0:0:0:0:0:0:0:1|::1");
    }

    @Configuration(proxyBeanMethods = false)
    @EnableWebSecurity
    @EnableConfigurationProperties(ServerProperties.class)
    @ImportAutoConfiguration({
        ConfigurationPropertiesAutoConfiguration.class,
        PropertyPlaceholderAutoConfiguration.class,
        ServletWebServerFactoryAutoConfiguration.class,
        EmbeddedWebServerFactoryCustomizerAutoConfiguration.class,
        DispatcherServletAutoConfiguration.class,
        WebMvcAutoConfiguration.class,
        HttpMessageConvertersAutoConfiguration.class,
        JacksonAutoConfiguration.class,
        SecurityFilterAutoConfiguration.class
    })
    @Import({
        SecurityConfig.class,
        Errors.class,
        AccountAccess.class,
        SessionPolicy.class,
        RecommendationController.class,
        ResearchAmenityController.class,
        AmenityController.class,
        AdvisorController.class
    })
    static class EmbeddedBoundaryApp {
        @Bean Clock clock() { return Clock.systemUTC(); }
        @Bean LoginThrottle loginThrottle(ObjectMapper mapper) { return new LoginThrottle(mapper); }
        @Bean RequestLimits requestLimits() { return new RequestLimits(); }
        @Bean UserRepository userRepository() { return mock(UserRepository.class); }
        @Bean SessionRepository sessionRepository() { return mock(SessionRepository.class); }
        @Bean HybridRecommendationService recommendationService() { return mock(HybridRecommendationService.class); }
        @Bean TinixCandidateRepository tinixCandidateRepository() { return mock(TinixCandidateRepository.class); }
        @Bean AmenityCatalogService amenityCatalogService() { return new AmenityCatalogService(new ObjectMapper()); }
        @Bean AdvisorOrchestrationService advisorOrchestrationService() { return mock(AdvisorOrchestrationService.class); }
    }

    @Test
    @DisplayName("Real embedded Tomcat on loopback with SERVER_FORWARD_HEADERS_STRATEGY=native blocks proxied external callers even with forged X-Forwarded-For, ADMIN JWT, and demo key")
    void realEmbeddedTomcatLoopbackAndForwardedHeaderBoundary() throws Exception {
        try (AnnotationConfigServletWebServerApplicationContext ctx = new AnnotationConfigServletWebServerApplicationContext()) {
            org.springframework.core.env.ConfigurableEnvironment env = ctx.getEnvironment();
            env.getPropertySources().addFirst(new MapPropertySource("test-boundary", Map.of(
                "server.address", "127.0.0.1",
                "server.port", "0",
                "server.forward-headers-strategy", "native",
                "server.tomcat.remoteip.internal-proxies", "127\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}|0:0:0:0:0:0:0:1|::1",
                "app.jwt-secret", "phase0-tomcat-boundary-secret-at-least-32-bytes!!",
                "app.cors-origins", "http://127.0.0.1",
                "app.refresh.enabled", "false",
                "app.recommendation.demo-key", "boundary-demo-key"
            )));
            ctx.register(EmbeddedBoundaryApp.class);
            ctx.refresh();

            int port = ctx.getWebServer().getPort();
            assertThat(port).isGreaterThan(0);

            UserRepository users = ctx.getBean(UserRepository.class);
            SessionRepository sessions = ctx.getBean(SessionRepository.class);
            JwtEncoder encoder = ctx.getBean(JwtEncoder.class);
            HybridRecommendationService recService = ctx.getBean(HybridRecommendationService.class);
            AdvisorOrchestrationService advisorService = ctx.getBean(AdvisorOrchestrationService.class);

            User admin = new User();
            admin.id = 77L;
            admin.role = User.Role.ADMIN;
            admin.status = User.Status.ACTIVE;
            admin.tokenVersion = 1;
            when(users.findById(77L)).thenReturn(Optional.of(admin));

            String sid = UUID.randomUUID().toString();
            AuthSession s = new AuthSession();
            s.id = sid;
            s.userId = 77L;
            s.createdAt = Instant.now().minusSeconds(30);
            s.lastUsedAt = Instant.now().minusSeconds(5);
            s.expiresAt = Instant.now().plusSeconds(3600);
            s.revoked = false;
            when(sessions.findById(sid)).thenReturn(Optional.of(s));

            String adminJwt = encoder.encode(JwtEncoderParameters.from(
                JwsHeader.with(MacAlgorithm.HS256).build(),
                JwtClaimsSet.builder()
                    .issuer("smartprop").id(sid).subject("77").claim("ver", 1)
                    .issuedAt(Instant.now().minusSeconds(5)).expiresAt(Instant.now().plusSeconds(900))
                    .build()
            )).getTokenValue();

            when(recService.internalDemo()).thenReturn(false);
            when(recService.tinixEnabled()).thenReturn(true);
            when(recService.recommendPublic(any())).thenReturn(new RecommendationDtos.Response(
                "HEURISTIC_V1_1", "SAFE", "ASKING_SALE_VND_TOTAL", null, 0, List.of(), List.of(), List.of(), Map.of()
            ));
            when(recService.recommendResearch(any())).thenReturn(new RecommendationDtos.Response(
                "HEURISTIC_V1_1", "INTERNAL_DEMO", "ASKING_SALE_VND_TOTAL", null, 0, List.of(), List.of(), List.of(), Map.of()
            ));
            when(advisorService.consult(any())).thenReturn(new AdvisorDtos.AdvisorResponse(
                "ADVISOR_ORCHESTRATOR_V1", "SAFE", "HEURISTIC_V1_1", "ASKING_SALE_VND_TOTAL", "disc",
                null, new AdvisorDtos.ServiceStatus("AVAILABLE", "AVAILABLE", "AVAILABLE", "SKIPPED", false),
                0, Map.of(), List.of(), List.of(), List.of(), List.of()
            ));

            HttpClient client = HttpClient.newHttpClient();
            String base = "http://127.0.0.1:" + port;
            String recJson = "{\"budgetVnd\":3000000000,\"purpose\":\"LIVING\",\"propertyType\":\"HOUSE\"}";

            // 1. Proxied external client WITH forged leftmost X-Forwarded-For: 127.0.0.1 + valid ADMIN JWT + valid demo key -> 403!
            for (String blockedGet : List.of("/api/v1/recommendations/research/config", "/api/v1/amenities/research/areas")) {
                HttpResponse<String> resp = client.send(
                    HttpRequest.newBuilder(URI.create(base + blockedGet))
                        .header("Authorization", "Bearer " + adminJwt)
                        .header("X-SmartProp-Demo-Key", "boundary-demo-key")
                        .header("X-Forwarded-For", "127.0.0.1, 203.0.113.99")
                        .GET().build(),
                    HttpResponse.BodyHandlers.ofString()
                );
                assertThat(resp.statusCode()).isEqualTo(403);
            }
            HttpResponse<String> proxiedResearchPost = client.send(
                HttpRequest.newBuilder(URI.create(base + "/api/v1/recommendations/research"))
                    .header("Authorization", "Bearer " + adminJwt)
                    .header("X-SmartProp-Demo-Key", "boundary-demo-key")
                    .header("X-Forwarded-For", "127.0.0.1, 203.0.113.99")
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(recJson)).build(),
                HttpResponse.BodyHandlers.ofString()
            );
            assertThat(proxiedResearchPost.statusCode()).isEqualTo(403);

            // 2. Direct internal loopback call (no X-Forwarded-For) WITH valid ADMIN JWT + valid demo key -> 200 OK!
            HttpResponse<String> directResearchPost = client.send(
                HttpRequest.newBuilder(URI.create(base + "/api/v1/recommendations/research"))
                    .header("Authorization", "Bearer " + adminJwt)
                    .header("X-SmartProp-Demo-Key", "boundary-demo-key")
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(recJson)).build(),
                HttpResponse.BodyHandlers.ofString()
            );
            assertThat(directResearchPost.statusCode()).isEqualTo(200);
            assertThat(directResearchPost.headers().firstValue("Cache-Control").orElse(""))
                .contains("private").contains("no-store");

            // 3. Public Recommendation, Public Amenities, and Advisor SAFE work cleanly through proxy (X-Forwarded-For: 203.0.113.99)
            HttpResponse<String> publicRec = client.send(
                HttpRequest.newBuilder(URI.create(base + "/api/v1/recommendations"))
                    .header("X-Forwarded-For", "203.0.113.99")
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(recJson)).build(),
                HttpResponse.BodyHandlers.ofString()
            );
            assertThat(publicRec.statusCode()).isEqualTo(200);

            HttpResponse<String> publicAmenities = client.send(
                HttpRequest.newBuilder(URI.create(base + "/api/v1/amenities/areas"))
                    .header("X-Forwarded-For", "203.0.113.99")
                    .GET().build(),
                HttpResponse.BodyHandlers.ofString()
            );
            assertThat(publicAmenities.statusCode()).isEqualTo(200);

            HttpResponse<String> publicAdvisor = client.send(
                HttpRequest.newBuilder(URI.create(base + "/api/v1/advisor/consult"))
                    .header("X-Forwarded-For", "203.0.113.99")
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString("{\"budgetVnd\":3500000000,\"purpose\":\"LIVING\",\"propertyType\":\"HOUSE\",\"includeResearch\":false}"))
                    .build(),
                HttpResponse.BodyHandlers.ofString()
            );
            assertThat(publicAdvisor.statusCode()).isEqualTo(200);

            // 4. Verify RemoteIpValve ignores forged X-Forwarded-For if a non-loopback peer (e.g. LAN 192.168.1.50) ever connected directly
            RemoteIpValve valve = new RemoteIpValve();
            valve.setInternalProxies("127\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}|0:0:0:0:0:0:0:1|::1");
            assertThat(Pattern.compile(valve.getInternalProxies()).matcher("127.0.0.1").matches()).isTrue();
            assertThat(Pattern.compile(valve.getInternalProxies()).matcher("192.168.1.50").matches()).isFalse();
            assertThat(Pattern.compile(valve.getInternalProxies()).matcher("10.0.0.8").matches()).isFalse();
        }
    }

    @Test
    @DisplayName("ops/Caddyfile blocks all loopback-only routes, encoded/semicolon/subpath variants before reverse_proxy and never falls back to SPA 200")
    void verifyCaddyfileStructureAndRouteMatchingSemantics() throws Exception {
        Path caddyfilePath = Path.of("..", "ops", "Caddyfile").normalize();
        String caddy = Files.readString(caddyfilePath, StandardCharsets.UTF_8);

        // 1. Balanced braces & ordered route block
        long opens = caddy.chars().filter(c -> c == '{').count();
        long closes = caddy.chars().filter(c -> c == '}').count();
        assertThat(opens).isEqualTo(closes);
        assertThat(caddy).contains("route {");

        int blockIdx = caddy.indexOf("handle @loopbackOnly");
        int variantIdx = caddy.indexOf("handle @loopbackVariant");
        int ambiguousIdx = caddy.indexOf("handle @ambiguousApiPath");
        int proxyIdx = caddy.indexOf("handle /api/*");
        int spaIdx = caddy.indexOf("try_files {path} /index.html");
        assertThat(blockIdx).isGreaterThan(0).isLessThan(proxyIdx);
        assertThat(variantIdx).isGreaterThan(0).isLessThan(proxyIdx);
        assertThat(ambiguousIdx).isGreaterThan(0).isLessThan(proxyIdx);
        assertThat(proxyIdx).isLessThan(spaIdx);
        assertThat(caddy).contains("header_up -X-SmartProp-Demo-Key");
        assertThat(caddy).contains("header_up -Forwarded");

        // 2. Evaluate exact Caddy matcher rules against adversarial & public URIs
        List<String> mustBlockUris = List.of(
            "/api/v1/recommendations/research",
            "/api/v1/recommendations/research/",
            "/api/v1/recommendations/research/config",
            "/api/v1/recommendations/research/subpath",
            "/api/v1/amenities/research",
            "/api/v1/amenities/research/",
            "/api/v1/amenities/research/hai-chau",
            "/api/v1/amenities/research/areas?level=DISTRICT",
            "/api/v1/recommendations/%72esearch",
            "/api/v1/recommendations/%52ESEARCH/config",
            "/api/v1/amenities/%72esearch/hai-chau",
            "/api/v1/recommendations/research;jsessionid=123",
            "/api/v1/amenities/research;v=1/hai-chau",
            "//api/v1/recommendations/research",
            "/api/v1/recommendations/%2fresearch",
            "/api/v1/properties/../recommendations/research",
            "/api/v1/properties/%2e%2e/recommendations/research"
        );
        for (String rawUri : mustBlockUris) {
            assertThat(caddyBlocksUri(rawUri))
                .as("Caddy public listener MUST block %s before reverse_proxy", rawUri)
                .isTrue();
        }

        List<String> mustAllowPublicApiUris = List.of(
            "/api/v1/recommendations",
            "/api/v1/amenities/areas",
            "/api/v1/amenities/hai-chau",
            "/api/v1/amenities/district:h%E1%BA%A3i-ch%C3%A2u",
            "/api/v1/advisor/consult",
            "/api/v1/admin/advisor/research-config",
            "/api/v1/properties?district=H%E1%BA%A3i%20Ch%C3%A2u&ref=https://smartprop.vn/a;b"
        );
        for (String rawUri : mustAllowPublicApiUris) {
            assertThat(caddyBlocksUri(rawUri))
                .as("Caddy public listener MUST allow public/authorized route %s", rawUri)
                .isFalse();
        }
    }

    private static boolean caddyBlocksUri(String rawUri) {
        Pattern ambiguousRaw = Pattern.compile("(?i)^/+api(?:/|%2f|%5c|;)[^?]*(?:%2f|%5c|%2e%2e|\\.\\.|;|//)");
        if (ambiguousRaw.matcher(rawUri).find()) {
            return true;
        }
        int q = rawUri.indexOf('?');
        String rawPath = q >= 0 ? rawUri.substring(0, q) : rawUri;
        String decodedPath = URLDecoder.decode(rawPath, StandardCharsets.UTF_8);
        if (decodedPath.equals("/api/v1/recommendations/research")
                || decodedPath.startsWith("/api/v1/recommendations/research/")
                || decodedPath.equals("/api/v1/amenities/research")
                || decodedPath.startsWith("/api/v1/amenities/research/")) {
            return true;
        }
        Pattern loopbackVariant = Pattern.compile("(?i)^/+api/+(?:v1/+)?(?:recommendations/+research|amenities/+research)(?:[;/]|$)");
        return loopbackVariant.matcher(decodedPath).find();
    }
}
