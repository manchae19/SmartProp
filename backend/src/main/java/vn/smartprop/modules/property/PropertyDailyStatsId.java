package vn.smartprop.modules.property;
import jakarta.persistence.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import java.io.Serializable;
import java.time.LocalDate;
import java.util.Objects;
@Embeddable
public class PropertyDailyStatsId implements Serializable {
    private static final long serialVersionUID=1L;
    @JdbcTypeCode(SqlTypes.CHAR) @Column(name="property_id",length=36,nullable=false) public String propertyId;
    @Column(name="stat_date",length=20,nullable=false) public LocalDate statDate;
    public PropertyDailyStatsId() {}
    public PropertyDailyStatsId(String propertyId,LocalDate statDate) { this.propertyId=propertyId; this.statDate=statDate; }
    @Override public boolean equals(Object other) { return other instanceof PropertyDailyStatsId k && Objects.equals(propertyId,k.propertyId) && Objects.equals(statDate,k.statDate); }
    @Override public int hashCode() { return Objects.hash(propertyId,statDate); }
}
