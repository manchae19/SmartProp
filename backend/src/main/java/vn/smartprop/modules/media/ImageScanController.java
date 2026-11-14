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

@RestController
@RequestMapping("/api/v1")
public class ImageScanController {
    private final PropertyImageScanService service;
    private final PropertyRepository properties;
    private final AccountAccess access;

    public ImageScanController(PropertyImageScanService service, PropertyRepository properties, AccountAccess access) {
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

    @GetMapping("/properties/{id}/image-scan")
    public ImageScanDtos.ScanView view(@AuthenticationPrincipal Jwt jwt, @PathVariable String id) {
        Property property = property(id);
        authorize(property, jwt, false);
        return service.view(property.id);
    }

    @PostMapping("/properties/{id}/image-scan/retry")
    public ImageScanDtos.ScanView retry(@AuthenticationPrincipal Jwt jwt, @PathVariable String id) {
        Property property = property(id);
        authorize(property, jwt, true);
        // Same guard as the analysis retry: a full queue is a busy signal, not a
        // server error, and it must never look like the scan itself failed.
        try {
            service.schedule(property.id);
        } catch (RuntimeException rejected) {
            throw new org.springframework.web.server.ResponseStatusException(
                org.springframework.http.HttpStatus.SERVICE_UNAVAILABLE,
                "Hàng đợi kiểm tra ảnh đang đầy; vui lòng thử lại sau.");
        }
        return service.view(property.id);
    }

    @GetMapping("/admin/image-scans")
    public List<ImageScanDtos.AdminItem> admin(@AuthenticationPrincipal Jwt jwt) {
        if (jwt == null) throw ApiInputs.forbidden();
        access.admin(Long.valueOf(jwt.getSubject()));
        return service.adminList();
    }
}
