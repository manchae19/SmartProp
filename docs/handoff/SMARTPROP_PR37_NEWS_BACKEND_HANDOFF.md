# HANDOFF TÍCH HỢP NEWS BACKEND CHO PR #37 (`integration/pr37-ui-validation`)

- **Baseline `origin/main` đã xác minh**: `f972d3a3465e5cc0ebe4260ddfbee7a8d32eee42`
- **Trạng thái hiện tại của News Backend trên `main`**: **CHƯA MERGE** (module `vn.smartprop.modules.news` hiện nằm trên nhánh độc lập `feature/news-backend-v1` / PR #41 đang mở). Trên `main`, `SecurityConfig` đóng mặc định `.anyRequest().denyAll()`, nên mọi truy vấn `GET /api/v1/news*` chưa có controller sẽ trả lỗi HTTP (`401`/`403`/`404`/`502`/`503`).
- **Nguyên tắc trong PR #37**:
  - **Không sửa `SecurityConfig.java`** và không tự cài đặt News backend giả trong PR frontend này.
  - Mọi request News từ `frontend/src/features/news/useNews.js` gọi `api(..., { authenticated: false })`, đảm bảo lỗi từ `/api/v1/news*` **không bao giờ** làm hết hạn phiên đăng nhập hiện có của người dùng.
  - Khi API chưa khả dụng, cả `HomeNewsPreview` (`/home#news`) và `NewsView` (`/news`) hiển thị thông báo rõ ràng (`role="alert"`, *"Nguồn tin tức tạm thời không khả dụng. Vui lòng thử lại."*) kèm nút **"Thử lại"**, `0` thẻ tin giả lập (`.news-card`), và `0` lỗi runtime JS.

---

## 1. Hợp đồng Endpoint mà Frontend News (`PR #37`) mong đợi

Tất cả các đường dẫn tính từ `VITE_API_BASE_URL` (mặc định `/api/v1`), phương thức `GET`, công khai (`permitAll` cho `HttpMethod.GET` khi PR #41 tích hợp):

### 1.1. `GET /api/v1/news`
- **Query parameters**:
  - `category` (`string`, ví dụ: `'Tất cả'`, `'Thị trường BĐS'`, `'Quy hoạch & hạ tầng'`, `'Chính sách & pháp lý'`, `'Dự án'`, `'Tin tức Đà Nẵng'`)
  - `q` (`string`, tối đa `200` ký tự)
  - `sort` (`'newest' | 'oldest'`, mặc định `'newest'`)
  - `page` (`integer >= 0`, mặc định `0`)
  - `size` (`integer`, mặc định `12`)
- **Response `200 OK` (`application/json`)**:
  ```json
  {
    "items": [
      {
        "id": "uuid-or-stable-id",
        "title": "Tiêu đề bài viết từ RSS",
        "summary": "Trích đoạn tóm tắt ngắn từ RSS (tùy chọn)",
        "category": "Quy hoạch & hạ tầng",
        "region": "DA_NANG",
        "articleUrl": "https://baoxaydung.vn/...",
        "sourceName": "Báo Xây dựng",
        "sourceUrl": "https://baoxaydung.vn",
        "publishedAt": "2026-11-28T03:00:00Z",
        "fetchedAt": "2026-11-28T04:00:00Z",
        "locationTags": "Đà Nẵng"
      }
    ],
    "page": 0,
    "size": 12,
    "totalElements": 1,
    "totalPages": 1,
    "lastUpdatedAt": "2026-11-28T04:00:00Z",
    "refreshing": false,
    "sources": [
      {
        "id": "baoxaydung-bds",
        "name": "Báo Xây dựng",
        "feedUrl": "https://baoxaydung.vn/rss/bat-dong-san.rss",
        "count": 1,
        "lastSuccessAt": "2026-11-28T04:00:00Z",
        "status": "AVAILABLE"
      }
    ]
  }
  ```

### 1.2. `GET /api/v1/news/featured`
- Không nhận tham số bắt buộc; trả cùng cấu trúc `Page` như `GET /api/v1/news` (ưu tiên bài có liên quan tới Đà Nẵng).

### 1.3. `GET /api/v1/news/sources`
- Chỉ được gọi khi tab quay lại trạng thái hiển thị (`focus` / `visibilitychange`, tối thiểu cách nhau `60s`, không polling nền).
- **Response `200 OK`**: Mảng trực tiếp `Source[]` (hoặc object `{ "sources": Source[] }` — `hasNewNewsSnapshot` trong `newsPresentation.js` đã hỗ trợ an toàn cả hai dạng):
  ```json
  [
    {
      "id": "baoxaydung-bds",
      "name": "Báo Xây dựng",
      "feedUrl": "https://baoxaydung.vn/rss/bat-dong-san.rss",
      "count": 12,
      "lastSuccessAt": "2026-11-28T04:00:00Z",
      "status": "AVAILABLE"
    }
  ]
  ```

---

## 2. Ràng buộc Bảo mật & Bản quyền Hình ảnh Phía Frontend (Phải Giữ Nguyên Khi Nối Backend)

1. **Sanitize URL bài gốc/nguồn (`safeNewsUrl`)**: Chỉ chấp nhận URL `https:` hợp lệ không chứa `username`/`password`; mọi scheme khác (`http:`, `javascript:`, `data:`) đều bị chặn không render thẻ `<a>`.
2. **Chính sách ảnh nhà xuất bản (`newsImagePolicy.js`)**: `NEWS_IMAGE_PERMISSIONS` mặc định đóng (`{}`). Kể cả khi backend trả `imageUrl` từ RSS, frontend **không tải ảnh từ CDN báo chí** nếu chưa có bằng chứng cấp phép hiển thị bằng văn bản cho SmartProp.
3. **Ảnh minh họa thay thế (`NewsCardImage.jsx`)**:
   - Ảnh Wikimedia Commons đã kiểm chứng giấy phép (`CC0 1.0`, `CC BY 4.0`, `CC BY 2.0`, `CC BY-SA 3.0/4.0`) luôn đi kèm `<details class="news-image-credit">` ghi rõ tác giả, liên kết gốc, giấy phép và sửa đổi.
   - Ảnh minh họa khái niệm tạo bằng AI (`editorial-*.webp`, `kind === 'AI_CONCEPT'`) luôn gắn huy hiệu **`Ảnh minh họa · AI`** và chú thích rõ *"Không phải ảnh chụp địa điểm hoặc dự án được đề cập"*.
