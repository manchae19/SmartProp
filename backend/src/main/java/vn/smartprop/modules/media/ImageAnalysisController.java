package vn.smartprop.modules.media;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;
import vn.smartprop.common.ApiInputs;
import vn.smartprop.modules.auth.AccountAccess;
import vn.smartprop.modules.property.Property;
import vn.smartprop.modules.property.PropertyRepository;
import vn.smartprop.modules.property.PropertyService;
import vn.smartprop.modules.user.User;

import java.time.Instant;
import java.util.List;

/**
 * Read/retry endpoints for YOLOv8 object analysis.
 *
 * <p>Visibility mirrors the duplicate scanner exactly: a public listing's
 * analysis is public, a draft's analysis is owner/ADMIN only. Analysis of a
 * private listing must never leak through this route.
 */
@RestController
@RequestMapping("/api/v1")
public class ImageAnalysisController {
    private final PropertyImageAnalysisService service;
    private final PropertyRepository properties;
    private final AccountAccess access;

    public ImageAnalysisController(PropertyImageAnalysisService service,
                                   PropertyRepository properties,
                                   AccountAccess access) {
        this.service = service;
        this.properties = properties;
        this.access = access;
    }

    private Property property(String id) {
        return properties.findByIdAndDeletedAtIsNull(ApiInputs.uuid(id)).orElseThrow(ApiInputs::missing);
    }

    private void authorize(Property property, Jwt jwt, boolean write) {
        if (write) {
            if (jwt == null) throw ApiInputs.missing();
            User user = access.active(Long.valueOf(jwt.getSubject()));
            if (!property.ownerId.equals(user.id) && user.role != User.Role.ADMIN) throw ApiInputs.forbidden();
            return;
        }
        if (PropertyService.visible(property, Instant.now())) return;
        if (jwt == null) throw ApiInputs.missing();
        User user = access.active(Long.valueOf(jwt.getSubject()));
        if (!property.ownerId.equals(user.id) && user.role != User.Role.ADMIN) throw ApiInputs.missing();
    }

    @GetMapping("/properties/{id}/image-analysis")
    public ImageAnalysisDtos.AnalysisView view(@AuthenticationPrincipal Jwt jwt, @PathVariable String id) {
        Property property = property(id);
        authorize(property, jwt, false);
        return service.view(property.id);
    }

    @PostMapping("/properties/{id}/image-analysis/retry")
    public ImageAnalysisDtos.AnalysisView retry(@AuthenticationPrincipal Jwt jwt, @PathVariable String id) {
        Property property = property(id);
        authorize(property, jwt, true);
        // @Async rejects with TaskRejectedException when the queue is full. That
        // must not surface as a 500: the caller asked for a retry, and the honest
        // answer is "queued" or "busy", never "server error".
        try {
            service.schedule(property.id);
        } catch (RuntimeException rejected) {
            throw new org.springframework.web.server.ResponseStatusException(
                org.springframework.http.HttpStatus.SERVICE_UNAVAILABLE,
                "Hàng đợi phân tích ảnh đang đầy; vui lòng thử lại sau.");
        }
        return service.view(property.id);
    }

    @GetMapping("/admin/image-analysis")
    public List<ImageAnalysisDtos.AdminItem> admin(@AuthenticationPrincipal Jwt jwt) {
        if (jwt == null) throw ApiInputs.forbidden();
        access.admin(Long.valueOf(jwt.getSubject()));
        return service.adminList();
    }
}
