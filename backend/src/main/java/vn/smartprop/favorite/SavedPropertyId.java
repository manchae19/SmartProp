package vn.smartprop.favorite;
import jakarta.persistence.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import java.io.Serializable;
import java.time.LocalDate;
import java.util.Objects;
@Embeddable
public class SavedPropertyId implements Serializable {
    private static final long serialVersionUID=1L;
    @Column(name="user_id",length=20,nullable=false) public Long userId;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name="property_id",length=36,nullable=false) public String propertyId;
    public SavedPropertyId() {}
    public SavedPropertyId(Long userId,String propertyId) { this.userId=userId; this.propertyId=propertyId; }
    @Override public boolean equals(Object other) { return other instanceof SavedPropertyId k && Objects.equals(userId,k.userId) && Objects.equals(propertyId,k.propertyId); }
    @Override public int hashCode() { return Objects.hash(userId,propertyId); }
}
