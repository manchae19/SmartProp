package vn.smartprop.modules.auth;
import java.time.Instant;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.security.oauth2.jwt.*;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
@Service
public class TokenService {
    private final JwtEncoder encoder;
    private final java.time.Clock clock;
    public Instant now(){return clock.instant();}
    public final long seconds;
    public TokenService(JwtEncoder encoder,@Value("${app.token-minutes}") long minutes,java.time.Clock clock) { if(minutes<1||minutes>15)throw new IllegalArgumentException("Access lifetime must be 1-15 minutes");this.encoder=encoder;this.clock=clock;seconds=minutes*60; }
    /** Compatibility overload for synthetic fixtures at initial account version zero. */
    public String issue(AuthSession session) { return issue(session,0); }
    public String issue(AuthSession session,int version) {
        var claims=JwtClaimsSet.builder().issuer("smartprop").subject(session.userId.toString())
            .issuedAt(now()).expiresAt(session.expiresAt.isBefore(now().plusSeconds(seconds))?session.expiresAt:now().plusSeconds(seconds)).id(session.id).claim("ver",version).build();
        return encoder.encode(JwtEncoderParameters.from(JwsHeader.with(MacAlgorithm.HS256).build(),claims)).getTokenValue();
    }
    public String issueFresh(AuthSession session,int version) {
        Instant now=now(),expiry=now.plusSeconds(seconds);if(session.expiresAt.isBefore(expiry))expiry=session.expiresAt;
        var claims=JwtClaimsSet.builder().issuer("smartprop").subject(session.userId.toString()).issuedAt(now).expiresAt(expiry).id(session.id).claim("ver",version).build();
        return encoder.encode(JwtEncoderParameters.from(JwsHeader.with(MacAlgorithm.HS256).build(),claims)).getTokenValue();
    }}
