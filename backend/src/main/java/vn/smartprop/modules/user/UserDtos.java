package vn.smartprop.modules.user;
import jakarta.validation.constraints.*;
import java.time.Instant;
public final class UserDtos {
    public record Profile(Long id,String email,String fullName,String phone,String district,String address,
                          User.Role role,User.Status status,Instant createdAt,Instant updatedAt,Instant emailVerifiedAt) {
        public Profile(Long id,String email,String fullName,String phone,String district,String address,User.Role role,User.Status status,Instant createdAt,Instant updatedAt){this(id,email,fullName,phone,district,address,role,status,createdAt,updatedAt,null);}
        public static Profile of(User u) { return new Profile(u.id,u.email,u.fullName,u.phone,u.district,u.address,u.role,u.status,u.createdAt,u.updatedAt,u.emailVerifiedAt); }
    }
    public record Patch(@Size(min=1,max=100) @Pattern(regexp="(?s).*\\S.*") String fullName,
        @Size(max=30) @Pattern(regexp="[+0-9 ()-]*") String phone,@Size(max=100) String district,@Size(max=255) String address) {}
    public record Password(@NotBlank @Size(max=72) String currentPassword,@NotBlank @Size(min=8,max=72) String newPassword) { @Override public String toString() { return "Password[redacted]"; } }
}
