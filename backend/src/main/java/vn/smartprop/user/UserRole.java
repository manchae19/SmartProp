package vn.smartprop.user;

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
@Entity @Table(name="user_roles")
public class UserRole {

    @EmbeddedId public UserRoleId id;
    @Column(name="granted_by") public Long grantedBy;
    @CreationTimestamp @Column(name="created_at",nullable=false) public Instant createdAt;
}
