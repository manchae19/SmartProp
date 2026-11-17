package vn.smartprop.modules.gis.geocoding;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.http.CacheControl;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import vn.smartprop.common.ApiException;
import vn.smartprop.common.RequestLimits;

/**
 * Address lookup for the public advisor chat.
 *
 * <p>The broker geocoder stays exactly as it was: authenticated, publisher-only.
 * The advisor needs a different door because its chat is anonymous, so this route
 * takes no account, requires explicit consent on every call, and is capped per IP.
 * Nothing is stored: the candidate coordinates live only in the RAG session.
 */
@RestController
@RequestMapping("/api/v1/advisor")
public class AdvisorGeocodingController {
    private static final String CITY = "Đà Nẵng";
    private final GeocodingService service;
    private final RequestLimits limits;
    public AdvisorGeocodingController(GeocodingService service, RequestLimits limits) {
        this.service = service;
        this.limits = limits;
    }
    public record Lookup(String address, Boolean shareAddress) {}
    /** Only what the chat needs: a label to confirm and a coordinate to route from. */
    public record Point(String id, String label, double latitude, double longitude, boolean approximate) {}
    public record Result(String status, java.util.List<Point> candidates) {}

    @PostMapping("/geocoding")
    public ResponseEntity<Result> lookup(@Valid @RequestBody Lookup body, HttpServletRequest http) {
        // Consent is per call: a previous "yes" never carries over.
        if (!Boolean.TRUE.equals(body.shareAddress()))
            throw new ApiException(422, "ADDRESS_SHARE_REQUIRED",
                "Cần đồng ý gửi địa chỉ tới dịch vụ bản đồ trước khi tìm vị trí.");
        String address = body.address() == null ? "" : body.address().strip();
        if (address.length() < 3 || address.length() > 300)
            throw new ApiException(400, "INVALID_ADDRESS", "Địa điểm cần từ 3 đến 300 ký tự.");
        limits.check("advisor:geocode:ip:" + http.getRemoteAddr(), 8, 3600);
        var search = new GeocodingDtos.Search(address, CITY, null, null, true);
        // Anonymous advisor traffic shares one server-side bucket (-1) so a single
        // caller cannot drain the paid daily budget on behalf of everyone else.
        var found = service.search(-1L, http.getRemoteAddr(), search);
        if (!"OK".equals(found.status())) return ResponseEntity.ok()
            .cacheControl(CacheControl.noStore()).body(new Result(found.status(), java.util.List.of()));
        var points = new java.util.ArrayList<Point>();
        for (var candidate : found.candidates()) {
            // Only candidates the provider matched to the address, and only those inside
            // the supported city. An approximate hit is surfaced as such, never hidden.
            if (!candidate.addressMatched()) continue;
            if (!Double.isFinite(candidate.latitude()) || !Double.isFinite(candidate.longitude())) continue;
            if (candidate.latitude() < 15.9 || candidate.latitude() > 16.2
                || candidate.longitude() < 107.9 || candidate.longitude() > 108.4) continue;
            boolean approximate = candidate.locationLevel() != GeocodingDtos.Level.EXACT_PROPERTY
                && candidate.locationLevel() != GeocodingDtos.Level.BUILDING_ONLY;
            points.add(new Point(candidate.id(), candidate.formattedAddress(),
                candidate.latitude(), candidate.longitude(), approximate));
            if (points.size() >= 5) break;
        }
        return ResponseEntity.ok().cacheControl(CacheControl.noStore())
            .body(new Result(points.isEmpty() ? "NO_MATCH" : "OK", java.util.List.copyOf(points)));
    }
}
