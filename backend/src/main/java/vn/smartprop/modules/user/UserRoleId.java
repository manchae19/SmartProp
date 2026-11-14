package vn.smartprop.modules.user;
import jakarta.persistence.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import java.io.Serializable;
import java.time.LocalDate;
import java.util.Objects;
@Embeddable
public class UserRoleId implements Serializable {
    private static final long serialVersionUID=1L;
    @Column(name="user_id",length=20,nullable=false) public Long userId;
    @Column(name="role_code",length=20,nullable=false) public String roleCode;
    public UserRoleId() {}
    public UserRoleId(Long userId,String roleCode) { this.userId=userId; this.roleCode=roleCode; }
    @Override public boolean equals(Object other) { return other instanceof UserRoleId k && Objects.equals(userId,k.userId) && Objects.equals(roleCode,k.roleCode); }
    @Override public int hashCode() { return Objects.hash(userId,roleCode); }
}
