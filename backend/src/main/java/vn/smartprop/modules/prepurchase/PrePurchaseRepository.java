package vn.smartprop.modules.prepurchase;

import java.time.LocalDate;
import java.util.List;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

/**
 * Public pre-purchase evidence: reviewed planning documents and flood records.
 *
 * <p>Both tables hold only material the publisher made public, and every row carries the
 * source URL it came from. Nothing here is derived from an address alone.
 */
@Repository
public class PrePurchaseRepository {
    private final JdbcTemplate jdbc;

    public PrePurchaseRepository(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    public record Planning(String id, String eventType, String projectName, String lotCode,
                            String landParcel, String ward, String district, String documentNumber,
                            LocalDate documentDate, LocalDate publicationDate, String scope,
                            String sourceUrl, String sourceTitle, LocalDate checkedAt) {}

    public record Flood(String id, String recordType, String locationText, String street,
                        String ward, String district, String scope, String depthNote,
                        LocalDate eventDate, LocalDate publicationDate, String sourceUrl,
                        String sourceTitle, LocalDate checkedAt, String currentUnit,
                        String areaBasis) {}

    /**
     * Planning documents that name this project, this lot, or this ward.
     *
     * <p>The caller decides how closely each row matches; this query only narrows the set.
     */
    public List<Planning> planning(String projectName, String lotCode, String ward, String district) {
        return jdbc.query("""
            SELECT id,event_type,project_name,lot_code,land_parcel,ward,district,document_number,
                   document_date,publication_date,scope,source_url,source_title,checked_at
            FROM planning_publications
            WHERE (project_name = ? OR (lot_code IS NOT NULL AND lot_code = ?)
                   OR (ward IS NOT NULL AND ward = ? AND district IS NOT NULL AND district = ?))
            ORDER BY publication_date DESC, id
            LIMIT 10
            """,
            (rs, i) -> new Planning(rs.getString("id"), rs.getString("event_type"),
                rs.getString("project_name"), rs.getString("lot_code"), rs.getString("land_parcel"),
                rs.getString("ward"), rs.getString("district"), rs.getString("document_number"),
                rs.getObject("document_date", LocalDate.class),
                rs.getObject("publication_date", LocalDate.class), rs.getString("scope"),
                rs.getString("source_url"), rs.getString("source_title"),
                rs.getObject("checked_at", LocalDate.class)),
            projectName == null ? "" : projectName, lotCode == null ? "" : lotCode,
            ward == null ? "" : ward, district == null ? "" : district);
    }

    /**
     * Flood records on this street inside this current ward/commune.
     *
     * <p>A street name alone is not enough: Nguyễn Lương Bằng runs through Hải Vân, Liên
     * Chiểu and Hòa Khánh, and the catalogue puts a different flood point in each. The
     * current unit is filtered in the query, before the row limit, so a record from
     * another ward can never take the place of a matching one.
     *
     * <p>Records without a current unit (the 77 catalogue rows whose source names no
     * ward) are never attached to a listing: the caller cannot verify them.
     */
    public List<Flood> flood(String street, String currentUnit) {
        if (currentUnit == null || currentUnit.isBlank()) return List.of();
        return jdbc.query("""
            SELECT id,record_type,location_text,street,ward,district,scope,depth_note,
                   event_date,publication_date,source_url,source_title,checked_at,
                   current_unit,area_basis
            FROM flood_records
            WHERE street IS NOT NULL AND street = ? AND current_unit = ?
            ORDER BY publication_date DESC, id
            LIMIT 10
            """,
            (rs, i) -> new Flood(rs.getString("id"), rs.getString("record_type"),
                rs.getString("location_text"), rs.getString("street"), rs.getString("ward"),
                rs.getString("district"), rs.getString("scope"), rs.getString("depth_note"),
                rs.getObject("event_date", LocalDate.class),
                rs.getObject("publication_date", LocalDate.class), rs.getString("source_url"),
                rs.getString("source_title"), rs.getObject("checked_at", LocalDate.class),
                rs.getString("current_unit"), rs.getString("area_basis")),
            street == null ? "" : street, currentUnit);
    }
}
