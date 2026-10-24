package vn.smartprop.auth;
import org.springframework.stereotype.Service;
import vn.smartprop.user.*;
import vn.smartprop.common.*;
@Service
public class AccountAccess {
    private final UserRepository users;
    public AccountAccess(UserRepository users) { this.users=users; }
    public User active(Long id) {
        User u=users.findById(id).orElseThrow(()->new ApiException(401,"UNAUTHENTICATED","Vui lòng đăng nhập"));
        if(u.deletedAt!=null || u.status!=User.Status.ACTIVE) throw new ApiException(401,"UNAUTHENTICATED","Tài khoản không hoạt động");
        return u;
    }
    public User publisher(Long id) { User u=active(id); if(u.role!=User.Role.BROKER && u.role!=User.Role.ADMIN) throw ApiInputs.forbidden(); return u; }
    public User admin(Long id) { User u=active(id); if(u.role!=User.Role.ADMIN) throw ApiInputs.forbidden(); return u; }
}