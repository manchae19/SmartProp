package vn.smartprop.auth;
import vn.smartprop.user.*;
import vn.smartprop.common.ApiException;
import org.springframework.stereotype.Service;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.transaction.annotation.Transactional;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.*;
import org.springframework.dao.DataIntegrityViolationException;
import java.sql.SQLException;
@Service
public class AuthService {
    private final UserRepository users;
    private final SessionRepository sessions;
    private final PasswordEncoder passwords;
    private final TokenService tokens;
    private final String dummyHash;
    public AuthService(UserRepository users,SessionRepository sessions,PasswordEncoder passwords,TokenService tokens) {
        this.users=users; this.sessions=sessions; this.passwords=passwords; this.tokens=tokens;
        dummyHash=passwords.encode(UUID.randomUUID().toString());
    }
    public static String email(String raw) { return raw.strip().toLowerCase(Locale.ROOT); }
    public static void passwordLength(String value) {
        if(value.getBytes(StandardCharsets.UTF_8).length>72)
            throw new ApiException(400,"VALIDATION_ERROR","Mật khẩu tối đa 72 byte UTF-8");
    }
    @Transactional public UserDtos.Profile register(AuthDtos.Register r) {
        if(!"BUYER".equals(r.role()) && !"BROKER".equals(r.role())) throw new ApiException(400,"VALIDATION_ERROR","Vai trò đăng ký không hợp lệ");
        passwordLength(r.password());
        if(users.findByEmail(email(r.email())).isPresent()) throw new ApiException(409,"EMAIL_EXISTS","Email đã được đăng ký");
        User u=new User(); u.email=email(r.email()); u.fullName=r.fullName().strip();
        u.passwordHash=passwords.encode(r.password()); u.role=User.Role.valueOf(r.role()); u.status=User.Status.ACTIVE;
        try { return UserDtos.Profile.of(users.saveAndFlush(u)); }
        catch(DataIntegrityViolationException e) {
            Throwable cause=e.getMostSpecificCause();
            if(cause instanceof SQLException sql && sql.getErrorCode()==1062 &&
               sql.getMessage()!=null && sql.getMessage().toLowerCase(Locale.ROOT).contains("uq_users_email"))
                throw new ApiException(409,"EMAIL_EXISTS","Email đã được đăng ký");
            throw e;
        }
    }
    @Transactional public AuthDtos.Token login(AuthDtos.Login r) {
        passwordLength(r.password());
        User found=users.findByEmail(email(r.email())).orElse(null);
        if(found==null) { passwords.matches(r.password(),dummyHash); throw invalidLogin(); }
        User u=users.lockById(found.id).orElseThrow(AuthService::invalidLogin);
        if(!passwords.matches(r.password(),u.passwordHash) || u.deletedAt!=null) throw invalidLogin();
        if(u.status!=User.Status.ACTIVE) throw new ApiException(403,"ACCOUNT_LOCKED","Tài khoản đã bị khóa");
        AuthSession s=new AuthSession(); s.id=UUID.randomUUID().toString(); s.userId=u.id;
        s.createdAt=Instant.now(); s.expiresAt=s.createdAt.plusSeconds(tokens.seconds); sessions.save(s);
        return new AuthDtos.Token(tokens.issue(s,u.tokenVersion),"Bearer",tokens.seconds,UserDtos.Profile.of(u));
    }
    private static ApiException invalidLogin() { return new ApiException(401,"INVALID_CREDENTIALS","Email hoặc mật khẩu không đúng"); }
    @Transactional public void logout(String sessionId) {
        sessions.findById(sessionId).ifPresent(s -> { s.revoked=true; sessions.save(s); });
    }
}
