package vn.smartprop.modules.prepurchase;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import org.springframework.stereotype.Service;
import vn.smartprop.modules.property.Property;
import vn.smartprop.modules.property.PropertyDtos;

/**
 * Public pre-purchase evidence for one listing.
 *
 * <p>Two different things are reported separately: the scope the source itself covers
 * (a lot, a project, a region) and how closely the listing matches it. A document about
 * lot A1 is parcel-level evidence, but a listing that only names the project matches it
 * at project level, and a listing that only shares the ward matches it at region level.
 */
@Service
public class PrePurchaseService {
    private final PrePurchaseRepository repository;
    private final AdminAreaMapping areas;

    public PrePurchaseService(PrePurchaseRepository repository, AdminAreaMapping areas) {
        this.repository = repository;
        this.areas = areas;
    }

    /**
     * How closely a record matches the listing being viewed.
     *
     * <p>{@link #SUGGESTED} is not evidence: the listing title merely names the project or the
     * lot, so the document is worth reading but says nothing verified about this listing.
     */
    public enum Match { LAND_PARCEL, PROJECT, REGION, STREET, SUGGESTED }

    public record PlanningView(String id, String eventType, String projectName, String lotCode,
                               String landParcel, String documentNumber, LocalDate documentDate,
                               LocalDate publicationDate, String sourceScope, String match,
                               String sourceUrl, String sourceTitle, LocalDate checkedAt) {}

    public record FloodView(String id, String recordType, String locationText, String street,
                            String ward, String district, String sourceScope, String match,
                            String depthNote, LocalDate eventDate, LocalDate publicationDate,
                            String sourceUrl, String sourceTitle, LocalDate checkedAt,
                            String currentUnit, String areaBasis) {}

    public record Checks(String propertyId, List<PlanningView> planning, List<FloodView> flood) {}

    public Checks forListing(PropertyDtos.View listing) {
        if (listing == null || listing.status() != Property.Status.PUBLISHED) {
            return new Checks(null, List.of(), List.of());
        }
        String project = projectOf(listing);
        String lot = lotOf(listing);
        String street = streetOf(listing.address());
        // Listings still carry the pre-2025 ward name; flood records carry the current one.
        String currentUnit = areas.currentUnit(listing.ward());

        List<PlanningView> planning = new ArrayList<>();
        for (var row : repository.planning(project, lot, listing.ward(), listing.district())) {
            Match match = planningMatch(row, project, lot, listing);
            if (match == null) continue;
            planning.add(new PlanningView(row.id(), row.eventType(), row.projectName(),
                row.lotCode(), row.landParcel(), row.documentNumber(), row.documentDate(),
                row.publicationDate(), row.scope(), match.name(), row.sourceUrl(),
                row.sourceTitle(), row.checkedAt()));
        }

        List<FloodView> flood = new ArrayList<>();
        for (var row : repository.flood(street, currentUnit)) {
            Match match = floodMatch(row, street, currentUnit);
            if (match == null) continue;
            flood.add(new FloodView(row.id(), row.recordType(), row.locationText(), row.street(),
                row.ward(), row.district(), row.scope(), match.name(), row.depthNote(),
                row.eventDate(), row.publicationDate(), row.sourceUrl(), row.sourceTitle(),
                row.checkedAt(), row.currentUnit(), row.areaBasis()));
        }
        return new Checks(listing.id(), List.copyOf(planning), List.copyOf(flood));
    }

    /**
     * A lot code only counts inside the project it belongs to: the same code appears in
     * other projects. Without a project or lot on the listing, only the ward matches.
     *
     * <p>A project or lot read from the listing title is a hint, never evidence: "Nhà gần
     * ALIZÉ, lô A1" names both and still proves nothing about this listing. Such a row is
     * reported as {@link Match#SUGGESTED} so the buyer can read the document himself.
     * {@link Match#LAND_PARCEL} and {@link Match#PROJECT} need a verified link between the
     * listing and the project or lot, which the system does not store yet.
     */
    static Match planningMatch(PrePurchaseRepository.Planning row, String project, String lot,
                               PropertyDtos.View listing) {
        boolean sameProject = project != null && sameText(project, row.projectName());
        boolean sameLot = lot != null && sameText(lot, row.lotCode());
        if (sameProject && sameLot) return Match.SUGGESTED;
        if (sameProject) return Match.SUGGESTED;
        if (sameLot) return null; // a lot code from another project is not this listing
        if (sameText(listing.ward(), row.ward()) && sameText(listing.district(), row.district()))
            return Match.REGION;
        return null;
    }

    /**
     * A street name is only evidence inside the current ward/commune it was recorded in:
     * Nguyễn Lương Bằng runs through Hải Vân, Liên Chiểu and Hòa Khánh, and the catalogue
     * puts a different flood point in each. A record whose source names no ward is never
     * attached, because the listing cannot be verified against it.
     */
    static Match floodMatch(PrePurchaseRepository.Flood row, String street, String currentUnit) {
        if (currentUnit == null || row.currentUnit() == null) return null;
        if (row.street() == null || row.street().isBlank()) return null;
        if (street == null || !sameText(street, row.street())) return null;
        if (!sameText(currentUnit, row.currentUnit())) return null;
        return Match.STREET;
    }

    /** The project named in the listing title, when the title names one. */
    static String projectOf(PropertyDtos.View listing) {
        String title = listing.title();
        if (title == null) return null;
        int at = title.toUpperCase(Locale.ROOT).indexOf("ALIZÉ");
        if (at < 0) at = title.toUpperCase(Locale.ROOT).indexOf("ALIZE");
        return at < 0 ? null : "Khu phức hợp thương mại, căn hộ du lịch ALIZÉ";
    }

    /** The lot code named in the listing title, e.g. "lô A1". */
    static String lotOf(PropertyDtos.View listing) {
        String title = listing.title();
        if (title == null) return null;
        var matcher = java.util.regex.Pattern.compile("(?iu)lô\\s+([A-Za-z0-9.\\-]+)").matcher(title);
        return matcher.find() ? matcher.group(1) : null;
    }

    /**
     * The street named in the listing address, or null when it cannot be read.
     *
     * <p>Listings write the street three ways:
     * <ul>
     *   <li>"Đường Trần Cao Vân, …" — the plain form.</li>
     *   <li>"Kiệt Trần Cao Vân, …" — the alley names the street it opens onto.</li>
     *   <li>"Kiệt 350, Đường Điện Biên Phủ, …" — the alley number and the street are
     *       separate parts, so the "Đường …" part must win over the bare number.</li>
     * </ul>
     *
     * <p>A part that only carries an alley number ("Kiệt 350") names no street and is
     * never used as one. The "Đường …" form is preferred over the alley form because it
     * is the explicit one; the alley form is the fallback for addresses that only have it.
     */
    static String streetOf(String address) {
        if (address == null || address.isBlank()) return null;
        String alley = null;
        for (String part : address.split(",")) {
            String text = part.strip();
            if (text.regionMatches(true, 0, "đường ", 0, 6)) {
                String name = text.substring(6).strip();
                if (!name.isBlank()) return name;
            } else if (text.regionMatches(true, 0, "duong ", 0, 6)) {
                String name = text.substring(6).strip();
                if (!name.isBlank()) return name;
            } else if (alley == null) {
                alley = alleyStreet(text);
            }
        }
        return alley;
    }

    /**
     * "Kiệt 350 Điện Biên Phủ" -> "Điện Biên Phủ"; "Kiệt Trần Cao Vân" -> "Trần Cao Vân".
     *
     * <p>Returns null when the part carries only an alley number ("Kiệt 350"), because a
     * number is not a street name.
     */
    private static String alleyStreet(String text) {
        String rest;
        if (text.regionMatches(true, 0, "kiệt ", 0, 5)) rest = text.substring(5).strip();
        else if (text.regionMatches(true, 0, "kiet ", 0, 5)) rest = text.substring(5).strip();
        else return null;
        // Bỏ số kiệt ở đầu, giữ phần tên đường.
        int space = rest.indexOf(' ');
        if (space > 0 && rest.substring(0, space).chars().allMatch(Character::isDigit)) {
            rest = rest.substring(space + 1).strip();
        } else if (space < 0 && !rest.isEmpty()
                   && rest.chars().allMatch(Character::isDigit)) {
            // "Kiệt 350" — chỉ có số, không phải tên đường.
            return null;
        }
        return rest.isBlank() ? null : rest;
    }

    private static boolean sameText(String left, String right) {
        return left != null && right != null && !left.isBlank()
            && left.strip().equalsIgnoreCase(right.strip());
    }
}
