package vn.smartprop.modules.auth.google;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.security.crypto.password.PasswordEncoder;
import vn.smartprop.modules.user.*;
import vn.smartprop.modules.auth.*;
import vn.smartprop.common.*;

@Service
public class GoogleAccountService {
    private final JdbcTemplate jdbc;private final UserRepository users;private final PasswordEncoder passwords;private final AuthService auth;private final RefreshService refresh;
    public GoogleAccountService(JdbcTemplate jdbc,UserRepository users,PasswordEncoder passwords,AuthService auth,RefreshService refresh){this.jdbc=jdbc;this.users=users;this.passwords=passwords;this.auth=auth;this.refresh=refresh;}
    @Transactional public RefreshService.Result login(GoogleProfile profile,String agent){
        List<Long> matches=jdbc.query("SELECT user_id FROM user_external_identities WHERE provider='GOOGLE' AND subject_id=?",(r,n)->r.getLong(1),profile.subject());
        Long id;
        if(matches.isEmpty()){
            if(users.findByEmail(profile.email()).isPresent())throw new ApiException(409,"GOOGLE_LINK_REQUIRED","Email này đã có tài khoản. Vui lòng đăng nhập bằng email và mật khẩu; tài khoản chưa liên kết Google.");
            User user=new User();user.email=profile.email();user.fullName=profile.name();user.passwordHash=passwords.encode(SecretTokens.random());user.role=User.Role.BUYER;user.status=User.Status.ACTIVE;user.emailVerifiedAt=Instant.now();user=users.saveAndFlush(user);id=user.id;
            jdbc.update("INSERT INTO user_external_identities(user_id,provider,subject_id,created_at) VALUES(?,'GOOGLE',?,?)",id,profile.subject(),Timestamp.from(Instant.now()));
        }else id=matches.getFirst();
        // Subject identity resolves an existing account; roles/status always come from the DB.
        return refresh.activate(auth.federatedLogin(id),agent,false);
    }
}
