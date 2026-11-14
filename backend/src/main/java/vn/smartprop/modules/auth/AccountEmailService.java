package vn.smartprop.modules.auth;
import java.time.*;
import java.util.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.security.crypto.password.PasswordEncoder;
import vn.smartprop.modules.email.MailOutbox;
import vn.smartprop.modules.user.*;
import vn.smartprop.common.*;
import vn.smartprop.config.*;
@Service
public class AccountEmailService {
    private final JdbcTemplate jdbc;private final UserRepository users;private final SessionRepository sessions;private final MailOutbox outbox;private final PasswordEncoder passwords;
    public AccountEmailService(JdbcTemplate jdbc,UserRepository users,SessionRepository sessions,MailOutbox outbox,PasswordEncoder passwords){this.jdbc=jdbc;this.users=users;this.sessions=sessions;this.outbox=outbox;this.passwords=passwords;}
    private ApiException invalid(){return new ApiException(400,"INVALID_OR_EXPIRED_TOKEN","Invalid or expired token");}
    @Transactional public void forgot(String email){outbox.ready();users.findByEmail(AuthService.email(email)).ifPresent(u->issue(u.id,false));}
    @Transactional public void request(Long actor){outbox.ready();issue(actor,true);}
    private void issue(Long id,boolean verification){User u=users.lockById(id).orElse(null);if(u==null||u.deletedAt!=null||u.status!=User.Status.ACTIVE||verification&&u.emailVerifiedAt!=null)return;
        String table=verification?"email_verification_tokens":"password_reset_tokens";if(jdbc.queryForObject("SELECT COUNT(*) FROM "+table+" WHERE user_id=? AND created_at>UTC_TIMESTAMP(6)-INTERVAL 60 SECOND",Integer.class,id)>0)return;
        jdbc.update("UPDATE "+table+" SET consumed_at=UTC_TIMESTAMP(6) WHERE user_id=? AND consumed_at IS NULL",id);
        String token=SecretTokens.random(),tokenId=UUID.randomUUID().toString();Instant expiry=Instant.now().plusSeconds(verification?86400:1800);
        if(verification)jdbc.update("INSERT INTO email_verification_tokens(id,user_id,email_snapshot,token_hash,issued_token_version,expires_at) VALUES(?,?,?,?,?,?)",tokenId,id,u.email,SecretTokens.hash(token),u.tokenVersion,java.sql.Timestamp.from(expiry));
        else jdbc.update("INSERT INTO password_reset_tokens(id,user_id,token_hash,issued_token_version,expires_at) VALUES(?,?,?,?,?)",tokenId,id,SecretTokens.hash(token),u.tokenVersion,java.sql.Timestamp.from(expiry));
        outbox.enqueue(id,u.email,verification?"EMAIL_VERIFICATION":"PASSWORD_RESET",tokenId,token);
    }
    @Transactional public void consume(String token,boolean verification,String password){outbox.ready();if(token==null||!token.matches("[A-Za-z0-9_-]{43}"))throw invalid();if(!verification){if(password==null||password.length()<8)throw ApiInputs.bad("Password minimum 8 characters");AuthService.passwordLength(password);}
        String table=verification?"email_verification_tokens":"password_reset_tokens",hash=SecretTokens.hash(token);var owners=jdbc.query("SELECT user_id FROM "+table+" WHERE token_hash=?",(r,n)->r.getLong(1),hash);if(owners.isEmpty())throw invalid();User u=users.lockById(owners.get(0)).orElseThrow(this::invalid);if(u.deletedAt!=null||u.status!=User.Status.ACTIVE)throw invalid();
        var valid=jdbc.queryForList("SELECT id FROM "+table+" WHERE token_hash=? AND consumed_at IS NULL AND expires_at>UTC_TIMESTAMP(6) AND issued_token_version=?"+(verification?" AND email_snapshot=?":"")+" FOR UPDATE",verification?new Object[]{hash,u.tokenVersion,u.email}:new Object[]{hash,u.tokenVersion});if(valid.isEmpty())throw invalid();
        if(verification){u.emailVerifiedAt=Instant.now();jdbc.update("UPDATE email_verification_tokens SET consumed_at=UTC_TIMESTAMP(6) WHERE user_id=? AND consumed_at IS NULL",u.id);}
        else{u.passwordHash=passwords.encode(password);u.tokenVersion=Math.incrementExact(u.tokenVersion);sessions.revokeAll(u.id);jdbc.update("UPDATE password_reset_tokens SET consumed_at=UTC_TIMESTAMP(6) WHERE user_id=? AND consumed_at IS NULL",u.id);}
        users.saveAndFlush(u);jdbc.update("UPDATE mail_outbox SET status='CANCELLED',payload_ciphertext=NULL,nonce=NULL WHERE user_id=? AND purpose=? AND status IN ('PENDING','PROCESSING')",u.id,verification?"EMAIL_VERIFICATION":"PASSWORD_RESET");
    }
}
