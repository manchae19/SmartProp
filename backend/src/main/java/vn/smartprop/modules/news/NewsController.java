package vn.smartprop.modules.news;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.web.bind.annotation.*;

/**
 * API công khai cho News.
 *
 * <p>Ba endpoint, tất cả GET, không cần đăng nhập:
 * <ul>
 *   <li>{@code GET /api/v1/news} — danh sách có phân trang, lọc, tìm kiếm</li>
 *   <li>{@code GET /api/v1/news/featured} — bài nổi bật</li>
 *   <li>{@code GET /api/v1/news/sources} — metadata nguồn tin</li>
 * </ul>
 *
 * <p>Không fetch RSS trong request. Chỉ đọc dữ liệu đã lưu.
 */
@RestController
@RequestMapping("/api/v1/news")
@ConditionalOnProperty(name = "app.news.enabled", havingValue = "true", matchIfMissing = true)
public class NewsController {
    private final NewsService service;

    public NewsController(NewsService service) { this.service = service; }

    @GetMapping
    public NewsDtos.Page list(
            @RequestParam(required = false) String category,
            @RequestParam(required = false) String q,
            @RequestParam(required = false, defaultValue = "newest") String sort,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "12") int size) {
        return service.list(category, q, sort, page, size);
    }

    @GetMapping("/featured")
    public NewsDtos.Page featured() {
        return service.featured();
    }

    /**
     * Metadata nguồn tin.
     *
     * <p>Trả <b>mảng trực tiếp</b>, không bọc trong object: Frontend PR #37 gọi
     * {@code sources.some(...)} trên kết quả ({@code hasNewNewsSnapshot} trong
     * {@code newsPresentation.js}). Bọc trong {@code {sources: [...]}} sẽ làm
     * {@code .some} undefined và ném TypeError.
     */
    @GetMapping("/sources")
    public java.util.List<NewsDtos.Source> sources() {
        return service.sources().sources();
    }
}
