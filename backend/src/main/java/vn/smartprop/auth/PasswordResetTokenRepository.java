package vn.smartprop.auth;
import org.springframework.data.jpa.repository.JpaRepository;
public interface PasswordResetTokenRepository extends JpaRepository<PasswordResetToken,String> {
}
