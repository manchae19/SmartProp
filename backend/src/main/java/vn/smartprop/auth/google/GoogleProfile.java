package vn.smartprop.auth.google;
import java.time.Instant;
import java.util.*;
import org.springframework.security.oauth2.core.oidc.OidcIdToken;
import org.springframework.security.oauth2.core.*;
/** This object is created only after Spring Security verifies the signed ID token. */
public record GoogleProfile(String subject,String email,String name) {
    public static GoogleProfile verified(OidcIdToken token,String clientId,Instant now){
        if(token==null||!Set.of("https://accounts.google.com","accounts.google.com").contains(String.valueOf(token.getIssuer()))||token.getAudience()==null||!token.getAudience().contains(clientId)||token.getExpiresAt()==null||!token.getExpiresAt().isAfter(now)||token.getIssuedAt()==null||token.getIssuedAt().isAfter(now.plusSeconds(60))||!Boolean.TRUE.equals(token.getEmailVerified())||token.getSubject()==null||!token.getSubject().matches("[A-Za-z0-9_-]{1,255}"))throw invalid();
        String email=token.getEmail();if(email==null||email.length()>254||!email.matches("[^\\s@]+@[^\\s@]+\\.[^\\s@]+"))throw invalid();
        String name=Optional.ofNullable(token.getFullName()).filter(v->!v.isBlank()).orElse(email.split("@",2)[0]).replaceAll("[\\p{Cntrl}]","").strip();if(name.length()>100)name=name.substring(0,100);
        return new GoogleProfile(token.getSubject(),vn.smartprop.auth.AuthService.email(email),name);
    }
    private static OAuth2AuthenticationException invalid(){return new OAuth2AuthenticationException(new OAuth2Error("invalid_id_token"),"Google identity is not verified.");}
    @Override public String toString(){return "GoogleProfile[redacted]";}
}
