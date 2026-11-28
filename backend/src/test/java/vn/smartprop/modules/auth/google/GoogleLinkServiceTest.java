package vn.smartprop.modules.auth.google;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.jwt.Jwt;
import vn.smartprop.common.ApiException;
import vn.smartprop.modules.auth.AuthSession;
import vn.smartprop.modules.auth.SessionPolicy;
import vn.smartprop.modules.auth.SessionRepository;
import vn.smartprop.modules.user.User;
import vn.smartprop.modules.user.UserRepository;

class GoogleLinkServiceTest {
    private final JdbcTemplate jdbc = mock(JdbcTemplate.class);
    private final UserRepository users = mock(UserRepository.class);
    private final SessionRepository sessions = mock(SessionRepository.class);
    private final SessionPolicy policy = mock(SessionPolicy.class);
    private final PasswordEncoder passwords = mock(PasswordEncoder.class);
    private final Clock clock = Clock.fixed(Instant.parse("2026-11-24T00:00:00Z"), ZoneOffset.UTC);
    private GoogleLinkService service;
    private User user;
    private AuthSession session;
    private Jwt jwt;

    @BeforeEach void setUp() {
        service = new GoogleLinkService(jdbc, users, sessions, policy, passwords, clock);
        user = new User(); user.id = 42L; user.email = "owner@example.test"; user.passwordHash = "hash";
        user.role = User.Role.BROKER; user.status = User.Status.ACTIVE; user.tokenVersion = 3;
        session = new AuthSession(); session.id = "session-42"; session.userId = 42L;
        session.createdAt = clock.instant().minusSeconds(100); session.expiresAt = clock.instant().plusSeconds(3600);
        session.lastUsedAt = clock.instant();
        jwt = Jwt.withTokenValue("unit-test-only").header("alg", "HS256").subject("42").claim("jti", session.id).claim("ver", 3).build();
        when(users.lockById(42L)).thenReturn(Optional.of(user));
        when(users.findById(42L)).thenReturn(Optional.of(user));
        when(sessions.lockById(session.id)).thenReturn(Optional.of(session));
        when(sessions.findById(session.id)).thenReturn(Optional.of(session));
        when(policy.valid(session, user)).thenReturn(true);
    }

    @Test void rejectsIncorrectPasswordBeforeIssuingLinkBinding() {
        when(passwords.matches("wrong", "hash")).thenReturn(false);
        ApiException error = assertThrows(ApiException.class, () -> service.begin(jwt, "wrong"));
        assertEquals(400, error.status);
        assertEquals("WRONG_PASSWORD", error.code);
        assertEquals("Mật khẩu hiện tại không chính xác", error.getMessage());
        verifyNoInteractions(jdbc);
    }

    @Test void correctPasswordCreatesBindingToCurrentUserAndSession() {
        when(passwords.matches("correct", "hash")).thenReturn(true);
        when(jdbc.queryForObject(anyString(), eq(Integer.class), any(Object[].class))).thenReturn(0);
        var binding = service.begin(jwt, "correct");
        assertEquals(42L, binding.userId());
        assertEquals(session.id, binding.sessionId());
        verify(passwords).matches("correct", "hash");
    }

    @Test void rejectsRevokedOrExpiredSession() {
        session.revoked = true;
        when(policy.valid(session, user)).thenReturn(false);
        when(passwords.matches("correct", "hash")).thenReturn(true);
        ApiException error = assertThrows(ApiException.class, () -> service.begin(jwt, "correct"));
        assertEquals("UNAUTHENTICATED", error.code);
    }

    @Test void rejectsDifferentUserOrSessionAtCompletion() {
        var ticket = new GoogleLinkFlowStore.Ticket(new GoogleProfile("subject", "google@example.test", "Google"), 42L, "different-session");
        ApiException error = assertThrows(ApiException.class, () -> service.complete(ticket, jwt));
        assertEquals("GOOGLE_LINK_SESSION_MISMATCH", error.code);
        verifyNoInteractions(jdbc);
    }

    @Test void rejectsGoogleSubjectAlreadyOwnedByAnotherUser() {
        when(jdbc.query(anyString(), any(RowMapper.class), any(Object[].class))).thenReturn(List.of(99L));
        var ticket = new GoogleLinkFlowStore.Ticket(new GoogleProfile("subject", "same@example.test", "Google"), 42L, session.id);
        ApiException error = assertThrows(ApiException.class, () -> service.complete(ticket, jwt));
        assertEquals("GOOGLE_IDENTITY_CONFLICT", error.code);
        verify(jdbc, never()).update(anyString(), any(Object[].class));
        assertEquals(42L, user.id);
        assertEquals("owner@example.test", user.email);
        assertEquals("hash", user.passwordHash);
        assertEquals(User.Role.BROKER, user.role);
    }

    @Test void linksOnlyVerifiedSubjectAndLeavesExistingAccountFieldsUntouched() {
        when(jdbc.query(anyString(), any(RowMapper.class), any(Object[].class))).thenReturn(List.of());
        when(jdbc.queryForObject(anyString(), eq(Integer.class), any(Object[].class))).thenReturn(0);
        when(jdbc.update(anyString(), any(Object[].class))).thenReturn(1);
        var ticket = new GoogleLinkFlowStore.Ticket(new GoogleProfile("verified-subject", "different-google-email@example.test", "Google"), 42L, session.id);

        service.complete(ticket, jwt);

        verify(jdbc).update(contains("INSERT INTO user_external_identities"), eq(42L), eq("verified-subject"), any());
        assertEquals(42L, user.id);
        assertEquals("owner@example.test", user.email);
        assertEquals("hash", user.passwordHash);
        assertEquals(User.Role.BROKER, user.role);
        assertEquals(User.Status.ACTIVE, user.status);
    }

    @Test void databaseUniqueConflictIsReturnedAsSafeConflict() {
        when(jdbc.query(anyString(), any(RowMapper.class), any(Object[].class))).thenReturn(List.of());
        when(jdbc.queryForObject(anyString(), eq(Integer.class), any(Object[].class))).thenReturn(0);
        doThrow(new DuplicateKeyException("duplicate")).when(jdbc).update(anyString(), any(Object[].class));
        var ticket = new GoogleLinkFlowStore.Ticket(new GoogleProfile("racing-subject", "g@example.test", "G"), 42L, session.id);
        ApiException error = assertThrows(ApiException.class, () -> service.complete(ticket, jwt));
        assertEquals("GOOGLE_IDENTITY_CONFLICT", error.code);
    }

    @Test void rejectsCompletionAfterAccountIsDisabledDeletedOrChangesTokenVersion() {
        var ticket = new GoogleLinkFlowStore.Ticket(
            new GoogleProfile("subject", "owner@example.test", "Owner"), 42L, session.id);
        user.status = User.Status.LOCKED;
        assertEquals(401, assertThrows(ApiException.class, () -> service.complete(ticket, jwt)).status);
        user.status = User.Status.ACTIVE;
        user.deletedAt = clock.instant();
        assertEquals(401, assertThrows(ApiException.class, () -> service.complete(ticket, jwt)).status);
        user.deletedAt = null;
        user.tokenVersion++;
        assertEquals(401, assertThrows(ApiException.class, () -> service.complete(ticket, jwt)).status);
        verifyNoInteractions(jdbc);
    }

    @Test void rejectsAnotherUserEvenWhenTicketSessionMatches() {
        var ticket = new GoogleLinkFlowStore.Ticket(
            new GoogleProfile("subject", "owner@example.test", "Owner"), 43L, session.id);
        assertEquals("GOOGLE_LINK_SESSION_MISMATCH",
            assertThrows(ApiException.class, () -> service.complete(ticket, jwt)).code);
        verifyNoInteractions(jdbc);
    }

    @Test void returnsExistingLinkWithoutCreatingAnotherAssociation() {
        when(jdbc.query(anyString(), any(RowMapper.class), any(Object[].class))).thenReturn(List.of(42L));
        var ticket = new GoogleLinkFlowStore.Ticket(
            new GoogleProfile("subject", "owner@example.test", "Owner"), 42L, session.id);
        assertEquals("GOOGLE_ALREADY_LINKED",
            assertThrows(ApiException.class, () -> service.complete(ticket, jwt)).code);
        verify(jdbc, never()).update(anyString(), any(Object[].class));
    }

    @Test void previouslyIssuedTicketCannotBeUsedAfterSessionRevocation() {
        var ticket = new GoogleLinkFlowStore.Ticket(
            new GoogleProfile("subject", "owner@example.test", "Owner"), 42L, session.id);
        session.revoked = true;
        when(policy.valid(session, user)).thenReturn(false);
        assertEquals(401, assertThrows(ApiException.class, () -> service.complete(ticket, jwt)).status);
        verifyNoInteractions(jdbc);
    }

}
