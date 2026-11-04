package vn.smartprop.modules.user;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.security.crypto.password.PasswordEncoder;
import vn.smartprop.modules.auth.*;
import vn.smartprop.common.ApiException;
@Service
public class UserService {
    private final UserRepository users;
    private final SessionRepository sessions;
    private final PasswordEncoder passwords;
    public UserService(UserRepository users,SessionRepository sessions,PasswordEncoder passwords) { this.users=users; this.sessions=sessions; this.passwords=passwords; }
    @Transactional(readOnly=true) public UserDtos.Profile me(Long id) { return UserDtos.Profile.of(active(id,false)); }
    private User active(Long id,boolean lock) {
        User u=(lock?users.lockById(id):users.findById(id)).orElseThrow(() -> new ApiException(401,"UNAUTHENTICATED","Vui lòng đăng nhập"));
        if(u.deletedAt!=null) throw new ApiException(401,"UNAUTHENTICATED","Vui lòng đăng nhập");
        if(u.status!=User.Status.ACTIVE) throw new ApiException(403,"ACCOUNT_LOCKED","Tài khoản đã bị khóa");
        return u;
    }
    @Transactional public UserDtos.Profile update(Long id,UserDtos.Patch r) {
        User u=active(id,true);
        if(r.fullName()!=null) u.fullName=r.fullName().strip();
        if(r.phone()!=null) u.phone=r.phone().strip();
        if(r.district()!=null) u.district=r.district().strip();
        if(r.address()!=null) u.address=r.address().strip();
        return UserDtos.Profile.of(users.saveAndFlush(u));
    }
    @Transactional public void password(Long id,UserDtos.Password r) {
        AuthService.passwordLength(r.currentPassword()); AuthService.passwordLength(r.newPassword());
        User u=active(id,true);
        if(!passwords.matches(r.currentPassword(),u.passwordHash)) throw new ApiException(400,"WRONG_PASSWORD","Mật khẩu hiện tại không đúng");
        u.tokenVersion=Math.incrementExact(u.tokenVersion);
        u.passwordHash=passwords.encode(r.newPassword()); users.save(u); sessions.revokeAll(id);
    }
}
