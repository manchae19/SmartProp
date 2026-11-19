package vn.smartprop.modules.user;

import java.util.ArrayList;
import java.util.List;
import org.springframework.http.CacheControl;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;
import vn.smartprop.common.ApiException;
import vn.smartprop.common.RequestLimits;
import vn.smartprop.modules.gis.geocoding.GeocodingDtos;
import vn.smartprop.modules.gis.geocoding.GeocodingService;

/**
 * The saved workplace, resolved to coordinates on the server.
 *
 * <p>The raw {@code workArea} string never leaves this class: it is not returned, not
 * placed in a URL, not logged, and not handed to the language model. What comes back is
 * a list of candidate points the user must confirm before any route is computed.
 */
@RestController
@RequestMapping("/api/v1/users/me/advisor-context")
public class AdvisorWorkplaceController {
    private static final String CITY = "Đà Nẵng";
    private final AdvisorPreferencesService preferences;
    private final GeocodingService geocoding;
    private final RequestLimits limits;
    public AdvisorWorkplaceController(AdvisorPreferencesService preferences, GeocodingService geocoding,
                                      RequestLimits limits) {
        this.preferences = preferences;
        this.geocoding = geocoding;
        this.limits = limits;
    }
    public record Point(double latitude, double longitude, String label, boolean approximate) {}
    public record Workplace(boolean available, String reason, List<Point> candidates) {}

    @GetMapping("/workplace")
    public ResponseEntity<Workplace> workplace(@AuthenticationPrincipal Jwt jwt,
                                               jakarta.servlet.http.HttpServletRequest request) {
        Long actor = Long.valueOf(jwt.getSubject());
        limits.check("advisor:workplace:" + actor, 6, 3600);
        var saved = preferences.saved(actor);
        if (!saved.enabled())
            return body(new Workplace(false, "PROFILE_DISABLED", List.of()));
        String area = (saved.workArea() == null ? "" : saved.workArea()).strip();
        if (area.length() < 3)
            return body(new Workplace(false, "NO_WORK_AREA", List.of()));
        if (area.length() > 180)
            return body(new Workplace(false, "WORK_AREA_TOO_LONG", List.of()));
        GeocodingDtos.Result found;
        try {
            found = geocoding.search(actor, request.getRemoteAddr(),
                new GeocodingDtos.Search(area, CITY, null, null, true));
        } catch (ApiException unavailable) {
            return body(new Workplace(false, "GEOCODING_UNAVAILABLE", List.of()));
        }
        if (!"OK".equals(found.status()))
            return body(new Workplace(false, "NOT_RESOLVED", List.of()));
        List<Point> points = new ArrayList<>();
        for (var candidate : found.candidates()) {
            if (!candidate.addressMatched()) continue;
            if (!Double.isFinite(candidate.latitude()) || !Double.isFinite(candidate.longitude())) continue;
            if (candidate.latitude() < 15.9 || candidate.latitude() > 16.2
                || candidate.longitude() < 107.9 || candidate.longitude() > 108.4) continue;
            boolean approximate = candidate.locationLevel() != GeocodingDtos.Level.EXACT_PROPERTY
                && candidate.locationLevel() != GeocodingDtos.Level.BUILDING_ONLY;
            points.add(new Point(candidate.latitude(), candidate.longitude(),
                candidate.formattedAddress(), approximate));
            if (points.size() >= 3) break;
        }
        return body(points.isEmpty() ? new Workplace(false, "NOT_RESOLVED", List.of())
            : new Workplace(true, "OK", List.copyOf(points)));
    }

    private static ResponseEntity<Workplace> body(Workplace value) {
        return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(value);
    }
}
