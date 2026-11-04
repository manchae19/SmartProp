package vn.smartprop.modules.user;

import jakarta.persistence.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;
import org.hibernate.type.SqlTypes;
import java.time.*;
import java.math.BigDecimal;
import com.fasterxml.jackson.databind.JsonNode;
import org.locationtech.jts.geom.Point;

/** Persistence mapping only. Foreign-key IDs do not imply cascade operations. */
@Entity @Table(name="roles")
public class Role {

    @Id @Column(name="code",length=20,nullable=false) public String code;
    @Column(name="name",length=100,nullable=false) public String name;
}
