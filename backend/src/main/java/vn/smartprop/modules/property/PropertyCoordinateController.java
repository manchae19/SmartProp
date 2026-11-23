package vn.smartprop.modules.property;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.util.List;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;
import vn.smartprop.common.ApiInputs;
import vn.smartprop.modules.auth.AccountAccess;

/**
 * Coordinate Provenance V1 — đọc trạng thái tọa độ và quy trình xác minh.
 *
 * <p>Phân quyền:
 * <ul>
 *   <li>{@code GET /properties/{id}/coordinate} — công khai cho tin PUBLISHED,
 *       chủ tin xem được tin của mình ở mọi trạng thái.</li>
 *   <li>{@code GET /properties/{id}/coordinate/history} — chỉ chủ tin và admin.</li>
 *   <li>{@code POST /properties/{id}/coordinate/verify} — chỉ admin.</li>
 *   <li>{@code GET /admin/coordinates/pending} — chỉ admin.</li>
 * </ul>
 */
@RestController
@RequestMapping("/api/v1")
public class PropertyCoordinateController {
    private final PropertyCoordinateAuditService audit;
    private final PropertyService properties;
    private final AccountAccess access;

    public PropertyCoordinateController(PropertyCoordinateAuditService audit,
                                        PropertyService properties, AccountAccess access) {
        this.audit = audit;
        this.properties = properties;
        this.access = access;
    }

    private Long actor(Jwt jwt) { return Long.valueOf(jwt.getSubject()); }

    /** Trạng thái tọa độ công khai của một tin. */
    @GetMapping("/properties/{id}/coordinate")
    public PropertyCoordinateAudit.Status status(@AuthenticationPrincipal Jwt jwt,
                                                 @PathVariable String id) {
        // Tin công khai: ai cũng đọc được. Tin chưa công khai: chỉ chủ tin hoặc admin.
        try {
            properties.publicProperty(id);
        } catch (RuntimeException notPublic) {
            Long viewer = jwt == null ? null : actor(jwt);
            if (viewer == null) throw notPublic;
            var user = access.active(viewer);
            if (user.role != vn.smartprop.modules.user.User.Role.ADMIN) {
                properties.owned(viewer, id);
            }
        }
        return audit.status(id);
    }

    /** Lịch sử thay đổi tọa độ — chỉ chủ tin và admin. */
    @GetMapping("/properties/{id}/coordinate/history")
    public List<PropertyCoordinateAuditRepository.HistoryRow> history(
            @AuthenticationPrincipal Jwt jwt, @PathVariable String id) {
        Long viewer = actor(jwt);
        var user = access.active(viewer);
        if (user.role != vn.smartprop.modules.user.User.Role.ADMIN) {
            properties.owned(viewer, id);
        }
        return audit.history(id);
    }

    /** Danh sách tin chờ xác minh — chỉ admin. */
    @GetMapping("/admin/coordinates/pending")
    public List<PropertyCoordinateAuditRepository.PendingRow> pending(
            @AuthenticationPrincipal Jwt jwt,
            @RequestParam(defaultValue = "50") int limit,
            @RequestParam(required = false) String verificationStatus,
            @RequestParam(required = false) String q) {
        access.admin(actor(jwt));
        return audit.pending(limit, verificationStatus, q);
    }

    /** Thống kê hàng đợi xác minh — chỉ admin. Đếm toàn bộ, không suy từ trang. */
    @GetMapping("/admin/coordinates/stats")
    public PropertyCoordinateAuditRepository.Stats stats(@AuthenticationPrincipal Jwt jwt) {
        access.admin(actor(jwt));
        return audit.stats();
    }

    /**
     * Chi tiết một tin cho admin review — chỉ admin.
     *
     * <p>Trả tọa độ, địa chỉ, metadata provenance và bằng chứng. Không dùng cho public
     * response: public detail chỉ trả {@code PropertyDtos.Coordinate} đã lọc.
     */
    @GetMapping("/admin/coordinates/{propertyId}")
    public PropertyCoordinateAuditRepository.ReviewDetail reviewDetail(
            @AuthenticationPrincipal Jwt jwt, @PathVariable String propertyId) {
        access.admin(actor(jwt));
        return audit.reviewDetail(propertyId);
    }

    /**
     * Ghi quyết định xác minh — chỉ admin.
     *
     * <p>Không có endpoint nào cho phép người đăng tự đặt {@code verificationStatus}.
     * Quyền được kiểm tra ở đây, không dựa vào giá trị client gửi.
     *
     * <p>{@code expectedRevision} bắt buộc: admin phải gửi revision đã thấy. Nếu người
     * đăng đã sửa tọa độ trong lúc admin xem, UPDATE không khớp dòng nào → 409.
     */
    @PostMapping("/properties/{id}/coordinate/verify")
    public PropertyCoordinateAudit.Status verify(@AuthenticationPrincipal Jwt jwt,
                                                 @PathVariable String id,
                                                 @Valid @RequestBody VerifyRequest request) {
        Long admin = actor(jwt);
        access.admin(admin);
        properties.existing(id);

        boolean applied = audit.verify(id, request.expectedRevision(),
            request.verificationStatus(), request.verificationMethod(), admin,
            request.evidenceReference(), request.accuracyLevel(),
            request.accuracyMeters(), request.accuracyMethod());
        if (!applied) {
            throw ApiInputs.conflict(
                "Revision tọa độ đã thay đổi; tải lại trước khi xác minh");
        }
        return audit.status(id);
    }

    public record VerifyRequest(
        @NotNull @Min(1) Integer expectedRevision,
        @NotNull PropertyCoordinateAudit.Verification verificationStatus,
        PropertyCoordinateAudit.VerificationMethod verificationMethod,
        @Size(max = 500) String evidenceReference,
        @NotNull PropertyCoordinateAudit.Accuracy accuracyLevel,
        Double accuracyMeters,
        @Size(max = 40) String accuracyMethod) {}
}
