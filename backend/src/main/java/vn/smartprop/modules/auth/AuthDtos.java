package vn.smartprop.modules.auth;
import jakarta.validation.constraints.*;
import vn.smartprop.modules.user.UserDtos.Profile;
public final class AuthDtos {
    public record Register(@NotBlank @Size(max=100) String fullName,
        @NotBlank @Email @Size(max=254) String email,
        @NotBlank @Size(min=8,max=72) String password,
        @NotBlank @Pattern(regexp="BUYER") String role) { @Override public String toString() { return "Register[redacted]"; } }
    public record Login(@NotBlank @Email @Size(max=254) String email,@NotBlank @Size(max=72) String password,Boolean rememberMe) { public Login(String email,String password){this(email,password,false);} @Override public String toString() { return "Login[redacted]"; } }
    public record Token(String accessToken,String tokenType,long expiresIn,Profile user) { @Override public String toString() { return "Token[redacted]"; } }
}
