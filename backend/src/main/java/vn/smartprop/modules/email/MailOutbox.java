package vn.smartprop.modules.email;
import java.time.*;
import java.util.*;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import javax.crypto.*;
import javax.crypto.spec.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.transaction.PlatformTransactionManager;
import vn.smartprop.common.*;
import vn.smartprop.config.*;
@Service
public class MailOutbox {
    private final JdbcTemplate jdbc;private final MailTransport transport;private final TransactionTemplate tx;private final String key,frontend,keyId;public final boolean enabled;
    public MailOutbox(JdbcTemplate jdbc,MailTransport transport,PlatformTransactionManager manager,@Value("${app.email.enabled:false}") boolean enabled,@Value("${app.email.payload-key:}") String key,@Value("${app.email.frontend-url:http://localhost:5173}") String frontend,@Value("${app.email.key-id:v1}") String keyId){this.jdbc=jdbc;this.transport=transport;this.tx=new TransactionTemplate(manager);this.enabled=enabled;this.key=key;this.frontend=frontend;this.keyId=keyId;}
    private byte[] keyBytes(){try{byte[] bytes=Base64.getDecoder().decode(key);if(bytes.length!=32)throw new IllegalArgumentException();return bytes;}catch(IllegalArgumentException e){throw new ApiException(503,"FEATURE_UNAVAILABLE","Email key unavailable");}}
    public void ready(){if(!enabled||!transport.configured())throw new ApiException(503,"FEATURE_UNAVAILABLE","Email unavailable");keyBytes();try{var uri=java.net.URI.create(frontend);if(uri.getUserInfo()!=null||uri.getFragment()!=null||uri.getQuery()!=null||!("https".equals(uri.getScheme())||"http".equals(uri.getScheme())&&Set.of("localhost","127.0.0.1").contains(uri.getHost())))throw new IllegalArgumentException();}catch(RuntimeException e){throw new ApiException(503,"FEATURE_UNAVAILABLE","Email frontend URL unavailable");}}
    public void enqueue(Long user,String email,String purpose,String tokenId,String token){ready();try{
        String id=UUID.randomUUID().toString(),link=frontend+(purpose.equals("PASSWORD_RESET")?"/reset-password#token=":"/verify-email#token=")+token;
        byte[] nonce=new byte[12];new SecureRandom().nextBytes(nonce);Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.ENCRYPT_MODE,new SecretKeySpec(keyBytes(),"AES"),new GCMParameterSpec(128,nonce));cipher.updateAAD((id+":"+purpose+":"+user).getBytes(StandardCharsets.UTF_8));byte[] payload=cipher.doFinal(link.getBytes(StandardCharsets.UTF_8));
        jdbc.update("UPDATE mail_outbox SET status='CANCELLED',payload_ciphertext=NULL,nonce=NULL,updated_at=UTC_TIMESTAMP(6) WHERE user_id=? AND purpose=? AND status IN ('PENDING','PROCESSING')",user,purpose);
        jdbc.update("INSERT INTO mail_outbox(id,user_id,purpose,verification_token_id,password_reset_token_id,recipient_email,payload_ciphertext,nonce,key_id) VALUES(?,?,?,?,?,?,?,?,?)",id,user,purpose,purpose.equals("EMAIL_VERIFICATION")?tokenId:null,purpose.equals("PASSWORD_RESET")?tokenId:null,email,payload,nonce,keyId);
    }catch(java.security.GeneralSecurityException e){throw new ApiException(503,"FEATURE_UNAVAILABLE","Email encryption unavailable");}}
    private record Job(String id,Long user,String purpose,String recipient,byte[] ciphertext,byte[] nonce,String keyId,String lease,int attempts,String verifyId,String resetId) {@Override public String toString(){return "MailJob[redacted]";}}
    public int deliverBatch(){ready();List<Job> jobs=tx.execute(s->{
        var rows=jdbc.query("SELECT * FROM mail_outbox WHERE (status='PENDING' AND available_at<=UTC_TIMESTAMP(6)) OR (status='PROCESSING' AND lease_until<UTC_TIMESTAMP(6)) ORDER BY created_at,id LIMIT 10 FOR UPDATE SKIP LOCKED",(r,n)->new Job(r.getString("id"),r.getLong("user_id"),r.getString("purpose"),r.getString("recipient_email"),r.getBytes("payload_ciphertext"),r.getBytes("nonce"),r.getString("key_id"),UUID.randomUUID().toString(),r.getInt("attempts")+1,r.getString("verification_token_id"),r.getString("password_reset_token_id")));
        for(var j:rows)jdbc.update("UPDATE mail_outbox SET status='PROCESSING',attempts=?,lease_token=?,lease_until=UTC_TIMESTAMP(6)+INTERVAL 2 MINUTE,updated_at=UTC_TIMESTAMP(6) WHERE id=?",j.attempts(),j.lease(),j.id());return rows;
    });int sent=0;
    for(var j:jobs){try{if(j.attempts()>5){finish(j,"FAILED","RETRY_EXHAUSTED");continue;}
        String table=j.purpose().equals("PASSWORD_RESET")?"password_reset_tokens":"email_verification_tokens",tokenId=j.resetId()!=null?j.resetId():j.verifyId();
        int valid=jdbc.queryForObject("SELECT COUNT(*) FROM "+table+" t JOIN users u ON u.id=t.user_id WHERE t.id=? AND t.consumed_at IS NULL AND t.expires_at>UTC_TIMESTAMP(6) AND u.status='ACTIVE' AND u.deleted_at IS NULL AND u.email=? AND t.issued_token_version=u.token_version",Integer.class,tokenId,j.recipient());
        if(valid==0){finish(j,"CANCELLED",null);continue;}
        if(!keyId.equals(j.keyId()))throw new IllegalStateException("Unknown key id");Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.DECRYPT_MODE,new SecretKeySpec(keyBytes(),"AES"),new GCMParameterSpec(128,j.nonce()));cipher.updateAAD((j.id()+":"+j.purpose()+":"+j.user()).getBytes(StandardCharsets.UTF_8));String link=new String(cipher.doFinal(j.ciphertext()),StandardCharsets.UTF_8);
        transport.send(j.recipient(),j.purpose(),link,j.id());finish(j,"SENT",null);sent++;
    }catch(Exception e){if(j.attempts()>=5)finish(j,"FAILED","DELIVERY_FAILED");else jdbc.update("UPDATE mail_outbox SET status='PENDING',available_at=?,lease_until=NULL,lease_token=NULL,last_error_code='DELIVERY_FAILED',updated_at=UTC_TIMESTAMP(6) WHERE id=? AND status='PROCESSING' AND lease_token=?",java.sql.Timestamp.from(Instant.now().plusSeconds(Math.min(3600,60L*(1L<<j.attempts())))),j.id(),j.lease());}}
    return sent;}
    private void finish(Job j,String status,String error){jdbc.update("UPDATE mail_outbox SET status=?,payload_ciphertext=NULL,nonce=NULL,sent_at=IF(?='SENT',UTC_TIMESTAMP(6),NULL),lease_until=NULL,lease_token=NULL,last_error_code=?,updated_at=UTC_TIMESTAMP(6) WHERE id=? AND status='PROCESSING' AND lease_token=?",status,status,error,j.id(),j.lease());}
}
