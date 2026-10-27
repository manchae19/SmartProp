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
    private final JdbcTemplate jdbc;private final UserRepository users;private final SessionRepository sessions;private final TokenService tokens;private final JwtDecoder decoder;private final boolean enabled;private final RequestLimits limits;private final SessionPolicy policy;
    public boolean enabled(){return enabled;}
    public record Result(AuthDtos.Token access,String refresh,long cookieSeconds){@Override public String toString(){return "RefreshResult[redacted]";}}
    public RefreshService(JdbcTemplate jdbc,UserRepository users,SessionRepository sessions,TokenService tokens,JwtDecoder decoder,RequestLimits limits,SessionPolicy policy,@Value("${app.refresh.enabled:false}") boolean enabled){this.jdbc=jdbc;this.users=users;this.sessions=sessions;this.tokens=tokens;this.decoder=decoder;this.enabled=enabled;this.limits=limits;this.policy=policy;}
    private void ready(){if(!enabled)throw new ApiException(503,"FEATURE_DISABLED","Refresh is disabled");}
    private ApiException invalid(){return new ApiException(401,"UNAUTHENTICATED","Phiên đăng nhập đã hết hạn hoặc bị thu hồi");}
    private User lock(Long id){User u=users.lockById(id).orElseThrow(this::invalid);if(u.deletedAt!=null||u.status!=User.Status.ACTIVE)throw invalid();return u;}
    private void lockSession(String id){jdbc.queryForList("SELECT id FROM auth_sessions WHERE id=? FOR UPDATE",id);}
    private String sessionId(String raw){
        if(raw==null||!raw.matches("[a-f0-9-]{36}\\.[A-Za-z0-9_-]{43}"))throw invalid();
        try{String id=UUID.fromString(raw.substring(0,36)).toString();if(!id.equals(raw.substring(0,36)))throw invalid();return id;}catch(IllegalArgumentException e){throw invalid();}
    }
    private Result result(AuthSession s,User u,String raw){return new Result(new AuthDtos.Token(tokens.issueFresh(s,u.tokenVersion),"Bearer",Math.min(tokens.seconds,policy.remaining(s,u)),UserDtos.Profile.of(u)),raw,policy.remaining(s,u));}
    @Transactional public Result activate(AuthDtos.Token access,String agent){return activate(access,agent,false);}
    @Transactional public Result activate(AuthDtos.Token access,String agent,boolean remember){
        ready();var jwt=decoder.decode(access.accessToken());User u=lock(Long.valueOf(jwt.getSubject()));lockSession(jwt.getId());AuthSession s=sessions.lockById(jwt.getId()).orElseThrow(this::invalid);
        if(s.revoked||!s.expiresAt.isAfter(policy.now())||s.refreshTokenHash!=null)throw invalid();
        String refresh=s.id+"."+SecretTokens.random();s.refreshTokenHash=SecretTokens.hash(refresh);
        s.expiresAt=s.createdAt.plus(policy.lifetime(u.role,remember));s.lastUsedAt=policy.now();
        String clean=agent==null?null:agent.replaceAll("[\\p{Cntrl}]","");s.userAgent=clean==null?null:clean.substring(0,Math.min(256,clean.length()));
        sessions.saveAndFlush(s);jdbc.update("UPDATE auth_sessions SET issued_token_version=? WHERE id=?",u.tokenVersion,s.id);return result(s,u,refresh);
    }
    @Transactional(noRollbackFor=ApiException.class) public Result rotate(String raw){return rotate(raw,true);}
    @Transactional(noRollbackFor=ApiException.class) public Result rotate(String raw,boolean activity){
        ready();String id=sessionId(raw),hash=SecretTokens.hash(raw);var ids=jdbc.query("SELECT user_id FROM auth_sessions WHERE id=?",(r,n)->r.getLong(1),id);if(ids.isEmpty())throw invalid();
        User u=lock(ids.get(0));lockSession(id);AuthSession s=sessions.lockById(id).orElseThrow(this::invalid);
        Integer issued=jdbc.queryForObject("SELECT issued_token_version FROM auth_sessions WHERE id=?",Integer.class,id);
        if(!policy.valid(s,u)||policy.remaining(s,u)<1||issued==null||issued!=u.tokenVersion)throw invalid();
        if(!SecretTokens.equal(hash,s.refreshTokenHash)){
            if(!jdbc.query("SELECT id FROM auth_refresh_token_history WHERE session_id=? AND token_hash=? FOR UPDATE",(r,n)->r.getString(1),id,hash).isEmpty()){s.revoked=true;sessions.saveAndFlush(s);}
            throw invalid();
        }
        limits.check("refresh-session:"+s.id,10,60);
        jdbc.update("INSERT INTO auth_refresh_token_history(id,session_id,token_hash,used_at,expires_at) VALUES(?,?,?,?,?)",UUID.randomUUID().toString(),id,hash,java.sql.Timestamp.from(policy.now()),java.sql.Timestamp.from(s.expiresAt));
        String next=s.id+"."+SecretTokens.random();s.refreshTokenHash=SecretTokens.hash(next);
        if(u.role!=User.Role.ADMIN||activity)s.lastUsedAt=policy.now();
        sessions.saveAndFlush(s);return result(s,u,next);
    }
    /** Logout does not rotate, depend on rate limits or require an unexpired access token. */
    @Transactional public void cookieLogout(String raw){
        ready();String id;try{id=sessionId(raw);}catch(ApiException e){return;}
        var ids=jdbc.query("SELECT user_id FROM auth_sessions WHERE id=?",(r,n)->r.getLong(1),id);if(ids.isEmpty())return;
        if(users.lockById(ids.get(0)).isEmpty())return;lockSession(id);AuthSession s=sessions.lockById(id).orElse(null);if(s==null)return;
        String hash=SecretTokens.hash(raw);
        if(SecretTokens.equal(hash,s.refreshTokenHash)||!jdbc.query("SELECT id FROM auth_refresh_token_history WHERE session_id=? AND token_hash=?",(r,n)->r.getString(1),id,hash).isEmpty()){s.revoked=true;sessions.saveAndFlush(s);}
    }
    public record SessionView(String id,boolean current,Instant createdAt,Instant expiresAt,Instant lastUsedAt,String userAgent,boolean revoked) {}
    @Transactional(readOnly=true) public PageResponse<SessionView> list(Long actor,String current,int page,int size){new AccountAccess(users).active(actor);ApiInputs.newest(page,size);long count=jdbc.queryForObject("SELECT COUNT(*) FROM auth_sessions WHERE user_id=?",Long.class,actor);var items=jdbc.query("SELECT id,created_at,expires_at,last_used_at,user_agent,revoked FROM auth_sessions WHERE user_id=? ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?",(r,n)->new SessionView(r.getString(1),r.getString(1).equals(current),r.getTimestamp(2).toInstant(),r.getTimestamp(3).toInstant(),r.getTimestamp(4)==null?null:r.getTimestamp(4).toInstant(),r.getString(5),r.getBoolean(6)),actor,size,(long)page*size);return new PageResponse<>(items,page,size,count,(int)((count+size-1)/size));}
    @Transactional public void revoke(Long actor,String id){lock(actor);id=ApiInputs.uuid(id);if(jdbc.update("UPDATE auth_sessions SET revoked=1 WHERE id=? AND user_id=?",id,actor)!=1)throw ApiInputs.missing();}
    @Transactional public void revokeAll(Long actor){User u=lock(actor);u.tokenVersion=Math.incrementExact(u.tokenVersion);users.save(u);sessions.revokeAll(actor);}
}
