package vn.smartprop.modules.auth.google;

import java.sql.Timestamp;
import java.time.Clock;
import java.util.List;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.smartprop.common.ApiException;
import vn.smartprop.modules.auth.AuthSession;
import vn.smartprop.modules.auth.AuthService;
import vn.smartprop.modules.auth.SessionPolicy;
import vn.smartprop.modules.auth.SessionRepository;
import vn.smartprop.modules.user.User;
import vn.smartprop.modules.user.UserRepository;

@Service
public class GoogleLinkService {
    public record Status(boolean linked) {}

    private final JdbcTemplate jdbc;
    private final UserRepository users;
    private final SessionRepository sessions;
    private final SessionPolicy sessionPolicy;
    private final PasswordEncoder passwords;
    private final Clock clock;

    public GoogleLinkService(JdbcTemplate jdbc, UserRepository users, SessionRepository sessions,
                             SessionPolicy sessionPolicy, PasswordEncoder passwords, Clock clock) {
        this.jdbc = jdbc;
        this.users = users;
        this.sessions = sessions;
        this.sessionPolicy = sessionPolicy;
        this.passwords = passwords;
        this.clock = clock;
    }

    @Transactional(readOnly = true)
    public Status status(Jwt jwt) {
        User user = requireLiveSession(jwt, false);
        Integer count = jdbc.queryForObject("SELECT COUNT(*) FROM user_external_identities WHERE user_id=? AND provider='GOOGLE'", Integer.class, user.id);
        return new Status(count != null && count > 0);
    }

    @Transactional
    public GoogleLinkFlowStore.Binding begin(Jwt jwt, String currentPassword) {
        if (currentPassword == null) throw new ApiException(400, "VALIDATION_ERROR", "Vui lòng nhập mật khẩu hiện tại.");
        AuthService.passwordLength(currentPassword);
        User user = requireLiveSession(jwt, true);
        if (!passwords.matches(currentPassword, user.passwordHash))
            throw new ApiException(400, "WRONG_PASSWORD", "Mật khẩu hiện tại không chính xác");
        Integer linked = jdbc.queryForObject("SELECT COUNT(*) FROM user_external_identities WHERE user_id=? AND provider='GOOGLE'", Integer.class, user.id);
        if (linked != null && linked > 0)
            throw new ApiException(409, "GOOGLE_ALREADY_LINKED", "Tài khoản SmartProp đã liên kết Google.");
        return new GoogleLinkFlowStore.Binding(user.id, jwt.getId());
    }

    @Transactional
    public void complete(GoogleLinkFlowStore.Ticket ticket, Jwt jwt) {
        User user = requireLiveSession(jwt, true);
        if (ticket.userId() != user.id || !ticket.sessionId().equals(jwt.getId()))
            throw new ApiException(409, "GOOGLE_LINK_SESSION_MISMATCH", "Phiên đăng nhập đã thay đổi. Vui lòng bắt đầu liên kết lại.");
        List<Long> owners = jdbc.query("SELECT user_id FROM user_external_identities WHERE provider='GOOGLE' AND subject_id=?",
            (row, index) -> row.getLong(1), ticket.profile().subject());
        if (!owners.isEmpty()) {
            if (owners.getFirst().equals(user.id)) throw new ApiException(409, "GOOGLE_ALREADY_LINKED", "Tài khoản SmartProp đã liên kết Google.");
            throw new ApiException(409, "GOOGLE_IDENTITY_CONFLICT", "Tài khoản Google này đã được liên kết với một tài khoản SmartProp khác.");
        }
        Integer existing = jdbc.queryForObject("SELECT COUNT(*) FROM user_external_identities WHERE user_id=? AND provider='GOOGLE'", Integer.class, user.id);
        if (existing != null && existing > 0) throw new ApiException(409, "GOOGLE_ALREADY_LINKED", "Tài khoản SmartProp đã liên kết Google.");
        try {
            jdbc.update("INSERT INTO user_external_identities(user_id,provider,subject_id,created_at) VALUES(?,'GOOGLE',?,?)",
                user.id, ticket.profile().subject(), Timestamp.from(clock.instant()));
        } catch (DataIntegrityViolationException conflict) {
            // The database unique keys are the final arbiter for concurrent linking attempts.
            throw new ApiException(409, "GOOGLE_IDENTITY_CONFLICT", "Tài khoản Google đã được liên kết. Vui lòng tải lại trạng thái bảo mật.");
        }
    }

    private User requireLiveSession(Jwt jwt, boolean lock) {
        long userId = safeUserId(jwt);
        User user = (lock ? users.lockById(userId) : users.findById(userId)).orElse(null);
        if (user == null || user.deletedAt != null || user.status != User.Status.ACTIVE)
            throw new ApiException(401, "UNAUTHENTICATED", "Phiên đăng nhập đã hết hạn hoặc bị thu hồi.");
        if (jwt.getId() == null || jwt.getId().isBlank())
            throw new ApiException(401, "UNAUTHENTICATED", "Phiên đăng nhập không hợp lệ.");
        AuthSession session = (lock ? sessions.lockById(jwt.getId()) : sessions.findById(jwt.getId())).orElse(null);
        Object version = jwt.getClaim("ver");
        if (session == null || !session.userId.equals(user.id) || !sessionPolicy.valid(session, user)
            || !(version instanceof Number number) || number.intValue() != user.tokenVersion)
            throw new ApiException(401, "UNAUTHENTICATED", "Phiên đăng nhập đã hết hạn hoặc bị thu hồi.");
        return user;
    }

    private long safeUserId(Jwt jwt) {
        try { return Long.parseLong(jwt.getSubject()); }
        catch (RuntimeException invalid) { throw new ApiException(401, "UNAUTHENTICATED", "Phiên đăng nhập không hợp lệ."); }
    }
}
