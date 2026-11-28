# Handoff News API cho PR #37

Tài liệu này ghi contract của backend PR #41 để PR #37 gọi API thật. Không sửa branch PR #37 trong lúc thực hiện handoff.

## Release và truy cập

Ba endpoint News dưới đây là GET công khai, không yêu cầu đăng nhập. Chỉ ba route này được public; mọi endpoint Admin nằm dưới `/api/v1/admin/news/**`, yêu cầu ADMIN và kiểm tra account/session.

`LIVE_INGESTION_DISABLED` và `SOURCE_RIGHTS_APPROVAL_PENDING` vẫn bật. Không có live RSS, article giả, hoặc source approval trong V1. Khi schema News chưa khả dụng, frontend phải xử lý HTTP 503 bằng graceful error state và nút retry, không hiển thị bài giả.

## `GET /api/v1/news`

Query:

| Tham số | Hành vi |
|---|---|
| `category` | Lọc category được hỗ trợ; bỏ trống nghĩa là mọi category |
| `q` | Trim; tối đa 200 ký tự; tìm title và chỉ tìm summary khi rights policy cho phép |
| `sort` | `newest` mặc định hoặc `oldest`; giá trị khác trả HTTP 400 |
| `page` | Mặc định 0, clamp tối thiểu về 0 |
| `size` | Mặc định 12; giá trị nhỏ hơn 1 quay về 12; tối đa cấu hình 50 |

Trả về `NewsDtos.Page`:

```text
Page {
  items: Article[], page: integer, size: integer,
  totalElements: integer, totalPages: integer,
  lastUpdatedAt: timestamp|null, refreshing: boolean,
  sources: Source[]
}
```

`Article` fields: `id`, `title`, `summary`, `category`, `region`, `articleUrl`, `sourceName`, `sourceUrl`, `publishedAt`, `fetchedAt`, `locationTags`. `summary`, `sourceUrl`, `publishedAt` và `locationTags` có thể null. Backend không trả image URL hoặc trường nội bộ quyền sử dụng.

## `GET /api/v1/news/featured`

Không nhận query bắt buộc. Trả cùng envelope Page như endpoint list; tối đa 12 kết quả. Bài phải thỏa cùng điều kiện visibility và source rights như public list.

## `GET /api/v1/news/sources`

Không nhận query bắt buộc. Trả `Source[]` trực tiếp, không bọc trong `{ "sources": ... }`. `Source` fields: `id`, `name`, `publisher`, `websiteUrl`, `feedUrl`, `count`, `lastSuccessAt`, `status`.

## Empty state, lỗi và quyền hiển thị

Dataset rỗng trả `items: []`, tổng số phần tử/trang bằng 0 và `sources: []`. Không tạo fixture content trong môi trường dùng chung.

Trước Local V28 hoặc khi schema/constraint không hợp lệ, cả ba News endpoint trả HTTP 503 với mã `NEWS_SCHEMA_UNAVAILABLE`. Error envelope: `{code, message, fields, timestamp}`. Query sai trả HTTP 400 cùng error envelope. Không retry vô hạn; giữ trạng thái graceful degradation.

Public chỉ nhận bài `VISIBLE` của source đang enabled, được đánh dấu `APPROVED`, và có `rightsReference` chứa ký tự không phải whitespace. Reference không tự chứng minh quyền sử dụng; source review vẫn thuộc quy trình riêng. Summary bị ẩn nếu quyền không cho phép; ảnh publisher không được phát hành trong DTO.

Frontend cần tiếp tục dùng URL sanitizer hiện có cho article/source links. Image policy mặc định đóng; không tải ảnh publisher khi chưa có permission rõ ràng. Handoff này không cung cấp nội dung bài, tên báo hay feed URL mẫu để tránh hiểu nhầm thành source đã được duyệt.

## Validation đã thực hiện

Chrome kiểm thử PR #37 gọi Spring backend thật trên fixture MySQL synthetic cô lập, gồm dataset rỗng và backend outage. Bằng chứng tương ứng trong `.scratch/evidence/chrome-real-integration.json` và `.scratch/evidence/chrome-error-state.json`; fixture synthetic không đại diện cho nội dung báo chí thật. Frontend PR37 65/65 là `REUSED_EVIDENCE` trong follow-up này vì không đổi frontend/API contract.
