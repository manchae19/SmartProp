package vn.smartprop.auth;
import java.time.*;
import java.util.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import vn.smartprop.user.*;
import vn.smartprop.common.*;
@Service
public class RefreshService {
    private final JdbcTemplate jdbc;private final UserRepository users;private final SessionRepository sessions;private final TokenService tokens;private final JwtDecoder decoder;private final boolean enabled;public boolean enabled(){return enabled;}private final RequestLimits limits;
    public record Result(AuthDtos.Token access,String refresh) {@Override public String toString(){return "RefreshResult[redacted]";}}
    public RefreshService(JdbcTemplate jdbc,UserRepository users,SessionRepository sessions,TokenService tokens,JwtDecoder decoder,RequestLimits limits,@Value("${app.refresh.enabled:false}") boolean enabled){this.jdbc=jdbc;this.users=users;this.sessions=sessions;this.tokens=tokens;this.decoder=decoder;this.enabled=enabled;this.limits=limits;}
    private void ready(){if(!enabled)throw new ApiException(503,"FEATURE_DISABLED","Refresh is disabled");}
    private ApiException invalid(){return new ApiException(401,"UNAUTHENTICATED","Invalid refresh session");}
    private User lock(Long id){User u=users.lockById(id).orElseThrow(this::invalid);if(u.deletedAt!=null||u.status!=User.Status.ACTIVE)throw invalid();return u;}
    private void lockSession(String id){jdbc.queryForList("SELECT id FROM auth_sessions WHERE id=? FOR UPDATE",id);}
    @Transactional public Result activate(AuthDtos.Token access,String agent){ready();var jwt=decoder.decode(access.accessToken());User u=lock(Long.valueOf(jwt.getSubject()));lockSession(jwt.getId());AuthSession s=sessions.findById(jwt.getId()).orElseThrow(this::invalid);if(s.revoked||!s.expiresAt.isAfter(Instant.now()))throw invalid();String refresh=s.id+"."+SecretTokens.random();s.refreshTokenHash=SecretTokens.hash(refresh);s.expiresAt=Instant.now().plusSeconds(7*86400L);s.userAgent=agent==null?null:agent.replaceAll("[\\p{Cntrl}]","").substring(0,Math.min(256,agent.replaceAll("[\\p{Cntrl}]","").length()));sessions.saveAndFlush(s);jdbc.update("UPDATE auth_sessions SET issued_token_version=? WHERE id=?",u.tokenVersion,s.id);return new Result(access,refresh);}
    @Transactional(noRollbackFor=ApiException.class) public Result rotate(String raw){ready();if(raw==null||!raw.matches("[a-f0-9-]{36}\\.[A-Za-z0-9_-]{43}"))throw invalid();String id;try{id=UUID.fromString(raw.substring(0,36)).toString();if(!id.equals(raw.substring(0,36)))throw invalid();}catch(IllegalArgumentException e){throw invalid();}String hash=SecretTokens.hash(raw);var ids=jdbc.query("SELECT user_id FROM auth_sessions WHERE id=?",(r,n)->r.getLong(1),id);if(ids.isEmpty())throw invalid();User u=lock(ids.get(0));lockSession(id);AuthSession s=sessions.lockById(id).orElseThrow(this::invalid);Integer issued=jdbc.queryForObject("SELECT issued_token_version FROM auth_sessions WHERE id=?",Integer.class,id);if(s.revoked||Duration.between(Instant.now(),s.expiresAt).getSeconds()<1||issued==null||issued!=u.tokenVersion)throw invalid();
        if(!SecretTokens.equal(hash,s.refreshTokenHash)){if(!jdbc.query("SELECT id FROM auth_refresh_token_history WHERE session_id=? AND token_hash=? FOR UPDATE",(r,n)->r.getString(1),id,hash).isEmpty()){s.revoked=true;sessions.saveAndFlush(s);}throw invalid();}
        limits.check("refresh-session:"+s.id,10,60);
        jdbc.update("INSERT INTO auth_refresh_token_history(id,session_id,token_hash,used_at,expires_at) VALUES(?,?,?,UTC_TIMESTAMP(6),?)",UUID.randomUUID().toString(),id,hash,java.sql.Timestamp.from(s.expiresAt));String next=s.id+"."+SecretTokens.random();s.refreshTokenHash=SecretTokens.hash(next);s.lastUsedAt=Instant.now();sessions.saveAndFlush(s);return new Result(new AuthDtos.Token(tokens.issueFresh(s,u.tokenVersion),"Bearer",Math.min(tokens.seconds,Duration.between(Instant.now(),s.expiresAt).getSeconds()),UserDtos.Profile.of(u)),next);
    }
    @Transactional(noRollbackFor=ApiException.class) public void cookieLogout(String raw){var result=rotate(raw);String id=raw.substring(0,36);sessions.findById(id).ifPresent(s->{s.revoked=true;sessions.save(s);});}
    public record SessionView(String id,boolean current,Instant createdAt,Instant expiresAt,Instant lastUsedAt,String userAgent,boolean revoked) {}
    @Transactional(readOnly=true) public PageResponse<SessionView> list(Long actor,String current,int page,int size){new AccountAccess(users).active(actor);ApiInputs.newest(page,size);long count=jdbc.queryForObject("SELECT COUNT(*) FROM auth_sessions WHERE user_id=?",Long.class,actor);var items=jdbc.query("SELECT id,created_at,expires_at,last_used_at,user_agent,revoked FROM auth_sessions WHERE user_id=? ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?",(r,n)->new SessionView(r.getString(1),r.getString(1).equals(current),r.getTimestamp(2).toInstant(),r.getTimestamp(3).toInstant(),r.getTimestamp(4)==null?null:r.getTimestamp(4).toInstant(),r.getString(5),r.getBoolean(6)),actor,size,(long)page*size);return new PageResponse<>(items,page,size,count,(int)((count+size-1)/size));}
    @Transactional public void revoke(Long actor,String id){lock(actor);id=ApiInputs.uuid(id);if(jdbc.update("UPDATE auth_sessions SET revoked=1 WHERE id=? AND user_id=?",id,actor)!=1)throw ApiInputs.missing();}
    @Transactional public void revokeAll(Long actor){User u=lock(actor);u.tokenVersion=Math.incrementExact(u.tokenVersion);users.save(u);sessions.revokeAll(actor);}
}
