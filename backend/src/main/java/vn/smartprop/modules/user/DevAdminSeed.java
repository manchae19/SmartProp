package vn.smartprop.modules.user;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.transaction.annotation.Transactional;
import vn.smartprop.modules.auth.AuthService;
@Component @Profile("dev") @ConditionalOnProperty(name="app.seed.enabled",havingValue="true")
class DevAdminSeed implements ApplicationRunner {
    private final UserRepository users;
    private final PasswordEncoder passwords;
    private final String email,password;
    DevAdminSeed(UserRepository users,PasswordEncoder passwords,@Value("${app.seed.email}") String email,@Value("${app.seed.password}") String password) {
        this.users=users; this.passwords=passwords; this.email=email; this.password=password;
    }
    @Override @Transactional public void run(ApplicationArguments args) {
        if(!email.matches("[^\\s@]+@[^\\s@]+\\.[^\\s@]+") || password.length()<12)
            throw new IllegalStateException("Development admin requires a valid email and password of at least 12 characters");
        AuthService.passwordLength(password);
        User existing=users.findByEmail(AuthService.email(email)).orElse(null);
        if(existing!=null) {
            if(existing.role!=User.Role.ADMIN) throw new IllegalStateException("Seed refuses to promote an existing user");
            return;
        }
        User u=new User(); u.email=AuthService.email(email); u.fullName="Development Administrator";
        u.passwordHash=passwords.encode(password); u.role=User.Role.ADMIN; u.status=User.Status.ACTIVE; users.save(u);
    }
}
