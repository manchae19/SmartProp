package vn.smartprop.modules.favorite;

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
@Entity @Table(name="saved_properties")
public class SavedProperty {

    @EmbeddedId public SavedPropertyId id;
    @CreationTimestamp @Column(name="saved_at",nullable=false) public Instant savedAt;
}
