package vn.smartprop.modules.amenity;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.CacheControl;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.web.bind.annotation.*;
import vn.smartprop.common.ApiException;
import vn.smartprop.common.ApiInputs;
import vn.smartprop.modules.auth.AccountAccess;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.List;
import java.util.Set;
import static vn.smartprop.modules.amenity.AmenityDtos.*;

/**
 * Internal research view of the amenity catalog.
 *
 * <p>The public {@code /api/v1/amenities/**} routes never expose {@code sampleListingCount},
 * which is derived from the TiniX research set. This controller mirrors the guard used by
 * {@code /api/v1/recommendations/research}: active ADMIN account, loopback caller and demo key.
 */
@RestController
@RequestMapping("/api/v1/amenities/research")
public class ResearchAmenityController {
    private final AmenityCatalogService catalog;
    private final String demoKey;
    private final AccountAccess access;

    @org.springframework.beans.factory.annotation.Autowired
    public ResearchAmenityController(
            AmenityCatalogService catalog,
            @Value("${app.recommendation.demo-key:}") String demoKey,
            AccountAccess access) {
        this.catalog = catalog;
        this.demoKey = demoKey;
        this.access = access;
    }

    public ResearchAmenityController(AmenityCatalogService catalog, String demoKey) {
        this(catalog, demoKey, null);
    }

    @GetMapping("/{areaId}")
    public ResponseEntity<ResearchAmenityProfile> profile(@PathVariable String areaId, HttpServletRequest http,
            Authentication authentication) {
        guard(http, authentication);
        return catalog.getById(areaId)
            .map(p -> ResponseEntity.ok().cacheControl(CacheControl.noStore().cachePrivate())
                .body(new ResearchAmenityProfile(p, p.sampleListingCount())))
            .orElseGet(() -> ResponseEntity.notFound().build());
    }

    @GetMapping("/areas")
    public ResponseEntity<List<AreaSummary>> areas(@RequestParam(required = false) String level,
            @RequestParam(required = false) String district, HttpServletRequest http, Authentication authentication) {
        guard(http, authentication);
        return ResponseEntity.ok().cacheControl(CacheControl.noStore().cachePrivate())
            .body(catalog.listAreas(level, district));
    }

    private void guard(HttpServletRequest http, Authentication authentication) {
        if (!(authentication instanceof JwtAuthenticationToken jwtAuth) || !jwtAuth.isAuthenticated()
            || !Set.of("127.0.0.1", "::1", "0:0:0:0:0:0:0:1").contains(http.getRemoteAddr())) {
            throw ApiInputs.forbidden();
        }
        if (access != null) {
            try {
                access.admin(Long.valueOf(jwtAuth.getToken().getSubject()));
            } catch (NumberFormatException | NullPointerException ex) {
                throw new ApiException(401, "UNAUTHENTICATED", "Phiên không hợp lệ");
            }
        }
        if (jwtAuth.getAuthorities().stream().noneMatch(a -> "ROLE_ADMIN".equals(a.getAuthority()))
            || demoKey.isBlank()) {
            throw ApiInputs.forbidden();
        }
        String provided = http.getHeader("X-SmartProp-Demo-Key");
        if (provided == null || !MessageDigest.isEqual(demoKey.getBytes(StandardCharsets.UTF_8),
                provided.getBytes(StandardCharsets.UTF_8))) {
            throw ApiInputs.forbidden();
        }
    }
}