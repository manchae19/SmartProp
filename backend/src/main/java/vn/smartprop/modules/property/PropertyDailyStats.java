package vn.smartprop.modules.property;

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
@Entity @Table(name="property_daily_stats")
public class PropertyDailyStats {

    @EmbeddedId public PropertyDailyStatsId id;
    @Column(name="view_count",nullable=false) public Long viewCount;
    @UpdateTimestamp @Column(name="updated_at",nullable=false) public Instant updatedAt;
}
