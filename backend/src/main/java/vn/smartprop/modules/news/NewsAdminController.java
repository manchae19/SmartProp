package vn.smartprop.modules.news;

import jakarta.validation.Valid;
import org.springframework.data.domain.Page;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;
import vn.smartprop.modules.auth.AccountAccess;

/**
 * API quản trị News — chỉ ADMIN.
 *
 * <p>Quyền kiểm tra độc lập ở đây bằng {@link AccountAccess#admin(Long)}, không dựa
 * vào SecurityConfig. SecurityConfig chỉ là lớp đầu tiên.
 *
 * <p>Không có endpoint nhận URL tùy ý để fetch. Sync chỉ chạy trên nguồn đã lưu.
 */
@RestController
@RequestMapping("/api/v1/admin/news")
public class NewsAdminController {
    private final NewsService read;
    private final NewsAdminService admin;
    private final AccountAccess access;

    public NewsAdminController(NewsService read, NewsAdminService admin, AccountAccess access) {
        this.read = read;
        this.admin = admin;
        this.access = access;
    }

    private Long actor(Jwt jwt) { return Long.valueOf(jwt.getSubject()); }

    @GetMapping("/sources")
    public java.util.List<NewsDtos.AdminSource> sources(@AuthenticationPrincipal Jwt jwt) {
        access.admin(actor(jwt));
        return read.adminSources();
    }

    @GetMapping("/sources/{id}")
    public NewsDtos.AdminSource source(@AuthenticationPrincipal Jwt jwt,
                                       @PathVariable String id) {
        access.admin(actor(jwt));
        return read.adminSource(id);
    }

    @PostMapping("/sources")
    public NewsDtos.AdminSource create(@AuthenticationPrincipal Jwt jwt,
                                       @Valid @RequestBody NewsDtos.CreateSource input) {
        access.admin(actor(jwt));
        return admin.create(input);
    }

    @PatchMapping("/sources/{id}")
    public NewsDtos.AdminSource update(@AuthenticationPrincipal Jwt jwt,
                                       @PathVariable String id,
                                       @Valid @RequestBody NewsDtos.UpdateSource input) {
        access.admin(actor(jwt));
        return admin.update(id, input);
    }

    /** Sync thủ công. Chỉ chạy trên nguồn đã duyệt quyền và đang bật. */
    @PostMapping("/sources/{id}/sync")
    public NewsIngestionService.Outcome sync(@AuthenticationPrincipal Jwt jwt,
                                             @PathVariable String id) {
        access.admin(actor(jwt));
        return admin.sync(id);
    }

    @GetMapping("/articles")
    public Page<NewsDtos.AdminArticle> articles(@AuthenticationPrincipal Jwt jwt,
                                                @RequestParam(defaultValue = "0") int page,
                                                @RequestParam(defaultValue = "20") int size) {
        access.admin(actor(jwt));
        return read.adminArticles(page, size);
    }

    @PatchMapping("/articles/{id}/visibility")
    public NewsDtos.AdminArticle visibility(@AuthenticationPrincipal Jwt jwt,
                                            @PathVariable String id,
                                            @Valid @RequestBody NewsDtos.VisibilityPatch input) {
        access.admin(actor(jwt));
        return admin.setVisibility(id, input.publicationStatus());
    }

    @PatchMapping("/articles/{id}/featured")
    public NewsDtos.AdminArticle featured(@AuthenticationPrincipal Jwt jwt,
                                          @PathVariable String id,
                                          @Valid @RequestBody NewsDtos.FeaturedPatch input) {
        access.admin(actor(jwt));
        return admin.setFeatured(id, input.featured());
    }

    @GetMapping("/ingestion-runs")
    public Page<NewsDtos.AdminRun> runs(@AuthenticationPrincipal Jwt jwt,
                                        @RequestParam(defaultValue = "0") int page,
                                        @RequestParam(defaultValue = "20") int size) {
        access.admin(actor(jwt));
        return read.adminRuns(page, size);
    }

    @GetMapping("/stats")
    public NewsDtos.Stats stats(@AuthenticationPrincipal Jwt jwt) {
        access.admin(actor(jwt));
        return read.stats();
    }
}
