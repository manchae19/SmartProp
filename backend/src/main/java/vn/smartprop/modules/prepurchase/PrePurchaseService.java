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

    public PrePurchaseService(PrePurchaseRepository repository) { this.repository = repository; }

    /** How closely a record matches the listing being viewed. */
    public enum Match { LAND_PARCEL, PROJECT, REGION, STREET }

    public record PlanningView(String id, String eventType, String projectName, String lotCode,
                               String landParcel, String documentNumber, LocalDate documentDate,
                               LocalDate publicationDate, String sourceScope, String match,
                               String sourceUrl, String sourceTitle, LocalDate checkedAt) {}

    public record FloodView(String id, String recordType, String locationText, String street,
                            String ward, String district, String sourceScope, String match,
                            String depthNote, LocalDate eventDate, LocalDate publicationDate,
                            String sourceUrl, String sourceTitle, LocalDate checkedAt) {}

    public record Checks(String propertyId, List<PlanningView> planning, List<FloodView> flood) {}

    public Checks forListing(PropertyDtos.View listing) {
        if (listing == null || listing.status() != Property.Status.PUBLISHED) {
            return new Checks(null, List.of(), List.of());
        }
        String project = projectOf(listing);
        String lot = lotOf(listing);
        String street = streetOf(listing.address());

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
        for (var row : repository.flood(street, listing.ward(), listing.district())) {
            Match match = floodMatch(row, street, listing);
            if (match == null) continue;
            flood.add(new FloodView(row.id(), row.recordType(), row.locationText(), row.street(),
                row.ward(), row.district(), row.scope(), match.name(), row.depthNote(),
                row.eventDate(), row.publicationDate(), row.sourceUrl(), row.sourceTitle(),
                row.checkedAt()));
        }
        return new Checks(listing.id(), List.copyOf(planning), List.copyOf(flood));
    }

    /**
     * A lot code only counts inside the project it belongs to: the same code appears in
     * other projects. Without a project or lot on the listing, only the ward matches.
     */
    static Match planningMatch(PrePurchaseRepository.Planning row, String project, String lot,
                               PropertyDtos.View listing) {
        boolean sameProject = project != null && sameText(project, row.projectName());
        boolean sameLot = lot != null && sameText(lot, row.lotCode());
        if (sameProject && sameLot) return Match.LAND_PARCEL;
        if (sameProject) return Match.PROJECT;
        if (sameLot) return null; // a lot code from another project is not this listing
        if (sameText(listing.ward(), row.ward()) && sameText(listing.district(), row.district()))
            return Match.REGION;
        return null;
    }

    /**
     * A street name is only evidence inside the district it was recorded in: the same name
     * exists elsewhere. Without a street, only the ward matches.
     */
    static Match floodMatch(PrePurchaseRepository.Flood row, String street,
                            PropertyDtos.View listing) {
        if (row.street() != null && !row.street().isBlank()) {
            if (street == null || !sameText(street, row.street())) return null;
            if (!sameText(listing.district(), row.district())) return null;
            return Match.STREET;
        }
        if (sameText(listing.ward(), row.ward()) && sameText(listing.district(), row.district()))
            return Match.REGION;
        return null;
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

    /** The street named in the listing address, or null when it cannot be read. */
    static String streetOf(String address) {
        if (address == null || address.isBlank()) return null;
        for (String part : address.split(",")) {
            String text = part.strip();
            if (text.regionMatches(true, 0, "đường ", 0, 6)) return text.substring(6).strip();
            if (text.regionMatches(true, 0, "duong ", 0, 6)) return text.substring(6).strip();
        }
        return null;
    }

    private static boolean sameText(String left, String right) {
        return left != null && right != null && !left.isBlank()
            && left.strip().equalsIgnoreCase(right.strip());
    }
}
