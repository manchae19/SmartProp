package vn.smartprop.modules.auth.google;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.nimbusds.jose.*;
import com.nimbusds.jose.crypto.RSASSASigner;
import com.nimbusds.jose.jwk.RSAKey;
import com.nimbusds.jose.jwk.gen.RSAKeyGenerator;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.SignedJWT;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.URLDecoder;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.Base64;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

final class GoogleLinkLocalOidcProvider implements AutoCloseable {
    static final String EMAIL = "pr48-other-" + UUID.randomUUID() + "@example.invalid";
    private final ObjectMapper json = new ObjectMapper();
    private final HttpServer server;
    private final RSAKey key;
    private final String client, secret, redirect, subject;
    private final Map<String, Authorization> codes = new ConcurrentHashMap<>();
    private final AtomicInteger exchanges = new AtomicInteger();

    private record Authorization(String nonce, String challenge) {}

    GoogleLinkLocalOidcProvider(String client, String secret, String redirect, String subject) throws Exception {
        this.client = client;
        this.secret = secret;
        this.redirect = redirect;
        this.subject = subject;
        key = new RSAKeyGenerator(2048).keyID("pr48-fixture-key").generate();
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/authorize", this::authorize);
        server.createContext("/token", this::token);
        server.createContext("/keys", request -> send(request, 200, Map.of("keys", java.util.List.of(key.toPublicJWK().toJSONObject()))));
        server.start();
    }

    String origin() { return "http://localhost:" + server.getAddress().getPort(); }
    int exchanges() { return exchanges.get(); }

    private void authorize(HttpExchange request) throws IOException {
        var params = parameters(request.getRequestURI().getRawQuery());
        String state = params.getOrDefault("state", "");
        String nonce = params.getOrDefault("nonce", "");
        String challenge = params.getOrDefault("code_challenge", "");
        if (!"GET".equals(request.getRequestMethod()) || !client.equals(params.get("client_id"))
            || !redirect.equals(params.get("redirect_uri")) || !"code".equals(params.get("response_type"))
            || !"S256".equals(params.get("code_challenge_method")) || state.isBlank() || nonce.isBlank()
            || !challenge.matches("[A-Za-z0-9_-]{43}") || codes.size() >= 10) {
            send(request, 400, Map.of("error", "invalid_request"));
            return;
        }
        String code = UUID.randomUUID().toString();
        codes.put(code, new Authorization(nonce, challenge));
        request.getResponseHeaders().set("Location", redirect + "?code=" + code + "&state=" + URLEncoder.encode(state, StandardCharsets.UTF_8));
        request.sendResponseHeaders(302, -1);
        request.close();
    }

    private void token(HttpExchange request) throws IOException {
        try {
            var params = parameters(new String(request.getRequestBody().readNBytes(8192), StandardCharsets.UTF_8));
            var auth = codes.remove(params.getOrDefault("code", ""));
            byte[] verifier = params.getOrDefault("code_verifier", "").getBytes(StandardCharsets.US_ASCII);
            String challenge = Base64.getUrlEncoder().withoutPadding()
                .encodeToString(MessageDigest.getInstance("SHA-256").digest(verifier));
            if (!"POST".equals(request.getRequestMethod()) || auth == null || !auth.challenge().equals(challenge)
                || !redirect.equals(params.get("redirect_uri")) || !client.equals(params.get("client_id"))
                || !"authorization_code".equals(params.get("grant_type")) || !secret.equals(params.get("client_secret"))) {
                send(request, 400, Map.of("error", "invalid_grant"));
                return;
            }
            Instant now = Instant.now();
            String verifiedSubject = exchanges.get() < 2 ? subject : subject + "-revoked";
            var claims = new JWTClaimsSet.Builder().issuer("https://accounts.google.com")
                .audience(client).subject(verifiedSubject).claim("nonce", auth.nonce()).claim("email", EMAIL)
                .claim("email_verified", true).claim("name", "PR48 Provider Identity")
                .issueTime(Date.from(now)).expirationTime(Date.from(now.plusSeconds(120))).build();
            var token = new SignedJWT(new JWSHeader.Builder(JWSAlgorithm.RS256).keyID(key.getKeyID()).build(), claims);
            token.sign(new RSASSASigner(key));
            exchanges.incrementAndGet();
            send(request, 200, Map.of("access_token", UUID.randomUUID().toString(), "token_type", "Bearer",
                "expires_in", 120, "scope", "openid email profile", "id_token", token.serialize()));
        } catch (Exception invalid) {
            send(request, 400, Map.of("error", "invalid_request"));
        }
    }

    private Map<String, String> parameters(String raw) {
        var values = new HashMap<String, String>();
        if (raw != null) for (String part : raw.split("&")) {
            int separator = part.indexOf('=');
            if (separator >= 0) values.put(URLDecoder.decode(part.substring(0, separator), StandardCharsets.UTF_8),
                URLDecoder.decode(part.substring(separator + 1), StandardCharsets.UTF_8));
        }
        return values;
    }

    private void send(HttpExchange request, int status, Map<String, ?> value) throws IOException {
        byte[] content = json.writeValueAsBytes(value);
        request.getResponseHeaders().set("Content-Type", "application/json");
        request.getResponseHeaders().set("Cache-Control", "no-store");
        request.sendResponseHeaders(status, content.length);
        try (var body = request.getResponseBody()) { body.write(content); }
    }

    @Override public void close() { server.stop(0); }
}
