# SmartProp — News Backend V1

Ngày cập nhật: 2026-11-27. Branch: `feature/news-backend-v1`.
Main tích hợp: `1f36205fbff5ef04f43c27af83c1694d500a9d61`.

## Trạng thái release

- `VALIDATION_PARTIAL`: chưa đạt điều kiện phát hành hoặc push.
- `LIVE_INGESTION_DISABLED`: hằng số `LIVE_INGESTION_PERMITTED=false` bắt buộc giữ nguyên.
- `SOURCE_RIGHTS_APPROVAL_PENDING`: không có nguồn báo chí thật nào được phê duyệt trong đợt này.
- Không công bố `NEWS_BACKEND_READY` hoặc `READY_FOR_FINAL_REVIEW` khi còn blocker.

News V1 phục vụ dữ liệu đã lưu qua REST. Scheduler, manual sync, gọi trực tiếp ingestion
service và production fetcher đều dừng tại hard release gate. Config/environment không
mở được gate. Scheduler trả danh sách rỗng trước mọi truy vấn repository.
Private transport chỉ được kiểm thử bằng fixture loopback trong `src/test`; artifact
production không chứa `TestNewsFeedFetcher` hay đường gọi package-private để bỏ gate.
Không dùng LLM; không thay đổi valuation, RAG hoặc Advisor.

## Kiến trúc và contract

```text
Public GET -> NewsService -> rights-filtered repository -> stored articles
Admin request -> Spring Security -> AccountAccess.admin -> schema availability -> service
Scheduler/manual/service/fetcher -> immutable release gate -> no outbound RSS
```

- `GET /api/v1/news`: `items`, pagination, `lastUpdatedAt`, `refreshing=false`, `sources`.
- `GET /api/v1/news/featured`: cùng cấu trúc page; ưu tiên featured, Đà Nẵng, ngày đăng, ID.
- `GET /api/v1/news/sources`: **array trực tiếp**, tương thích PR #37.
- Search title; chỉ search summary khi nguồn cho phép. LIKE wildcard được escape.
- Category/nhóm category và khu vực Đà Nẵng; newest/oldest tại DB trước pagination.
- `publishedAt=NULL` xuống cuối ở cả hai chiều. Không thay bằng fetchedAt.
- Tiebreaker ID giữ pagination/featured ổn định.
- Public chỉ có bài VISIBLE, nguồn enabled + APPROVED + rightsReference không whitespace.
- Summary bị ẩn khi không có quyền; không trả ảnh báo chí. `allowImages` không mở thêm
  image field trong public DTO.
- Public không trả rightsReference, lease token, revision, ETag, lastError hay stack trace.

Admin surface: nguồn (list/detail/create/update), articles (list/visibility/featured),
stats, ingestion runs, manual sync. Guest bị 401, Buyer/Broker bị 403, Admin phải được
xác minh role trong DB. Manual sync trả `SKIPPED / LIVE_INGESTION_LOCKED`; không claim
lease, tạo run, ghi article hoặc fetch mạng.

## Migration lineage

`MigrationLineageConfiguration` lấy strict ordered history validation từ main.
Danh sách Local: 13 BASELINE, crawler14 đúng checksum, 17..27 đúng thứ tự; V27 đứng sau
V26. Missing intermediate, failed, duplicate, unknown và out-of-order đều bị từ chối.
Runtime pending V26 guard từ main vẫn giữ nguyên. Flyway validate kiểm tra checksum;
không repair, baseline tự động, auto-migrate hoặc sửa history.

Local target = **27**; Standard target = **23**. V13–V27 không được chỉnh sửa.
V26 từ main và V27 từ PR #41 vẫn nguyên byte. Existing Local runtime identity guard
không được nới lỏng: profile staging vẫn chỉ cho URL/schema/datadir cố định của main.

**Blocker database constraint:** V27 chỉ CHECK enum rights status, chưa CHECK rằng
APPROVED phải có rightsReference khác NULL/rỗng/whitespace. App policy, public SQL,
lease SQL và entity callbacks đã bảo vệ yêu cầu này, nhưng chưa thay thế được DB CHECK.
Không tạo V28, không tăng target 28: nhóm trưởng chưa phê duyệt version. Cần kiểm tra
cả migration chưa push của WP-01 và phê duyệt chính thức cho migration forward-only.
Không tự điền reference hoặc sửa legacy data để constraint đạt.

## Standard V23

Standard không có ba bảng News. Hibernate vẫn dùng `ddl-auto=validate`; schema filter
riêng cho profile Standard chỉ loại đúng `news_sources`, `news_articles`,
`news_ingestion_runs` khỏi bước validation. Mọi bảng/entity hiện có vẫn được validate.
Public News trả 503 `NEWS_SCHEMA_UNAVAILABLE` trước truy vấn. Admin kiểm tra auth/role
trước schema gate; Admin hợp lệ nhận 503, Guest/Buyer/Broker vẫn nhận 401/403.
Runtime regression xác minh property create/detail/search vẫn hoạt động.

## Source rights lifecycle

`NewsRightsPolicy` là policy dùng chung cho ingestion, persistence và summary reads.
Entity callbacks chặn APPROVED thiếu reference hoặc enabled khi không được duyệt.
Public/lease SQL cũng từ chối reference NULL, rỗng và whitespace, kể cả legacy rows.

Publisher, website URL và feed URL là identity. Đổi identity:

1. Khoá source row cùng transaction với admin update.
2. Reset PENDING_REVIEW, disabled, xoá reference/checkedAt/conditional GET/cooldown;
   summary/images trở về false.
3. Ẩn bài cũ, giữ nguyên nội dung và các bản ghi lịch sử; không xoá article.
4. Không approve/enable trong cùng request; approval mới cần request review riêng.

Thay rightsReference của nguồn APPROVED cũng mất approval và cần review lại.
APPROVED -> PENDING_REVIEW/REJECTED tắt ingestion. Mọi admin edit tăng sourceRevision.
Approval mới không tự công khai lại các bài cũ đã bị ẩn do thay identity.
Nguồn mới mặc định PENDING_REVIEW, disabled, summary/images false.

## Security và concurrency

Giữ SSRF private/loopback/link-local/metadata protection, host allowlist, XXE hardening,
connect/read timeout, body read deadline, max bytes, Retry-After và conditional GET 304.
DNS rebinding vẫn là limitation V1: kiểm tra DNS và kết nối chưa được pin resolver;
hard release gate vì vậy vẫn bắt buộc đóng. Không mở rộng sang V1.1.

Lease claim là atomic SQL. Persistence khoá source row, kiểm tra token, thời gian lease
**sau khi lấy lock**, revision và rights trên trạng thái mới nhất. Success/failure
metadata cũng bị fence theo lease/revision/rights. Caller timestamp cũ không hồi sinh
lease đã hết hạn. Targeted article updates không ghi đè visibility/featured của admin.
Fixture DB tests kiểm tra lease, fencing, idempotency/dedup và constraints trực tiếp;
không đi qua network ingestion hoặc tạo production bypass.

## Kiểm thử và triển khai

Xem [test matrix](SMARTPROP_NEWS_BACKEND_V1_TEST_MATRIX.md) và
[final report](SMARTPROP_NEWS_BACKEND_V1_FINAL_REPORT.md). SHA của final commit và exit
codes sau commit được lưu ở `.scratch/evidence/final-head.txt` và final evidence manifest.
Không tái dùng kết quả live ingestion cũ như fresh PASS của release hiện tại.

Môi trường duy nhất dùng trong đợt kiểm thử này: MySQL riêng `127.0.0.1:3311`, datadir
`D:/Cap2_HoangDuy/SmartProp-News-Backend/.scratch/mysql-pr41/data/`, UUID
`0f29afde-ea54-11f1-bcac-088fc36287dc`. PID khởi tạo 7604, executable/config/datadir
đã xác minh; backup trước migration. Không kết nối 3306/3307, không dừng MySQL80/WP-01.
Schema `pr41_standard` là V1–V23. Schema News synthetic là Standard V23 + nguyên bản
V26 + nguyên bản V27; không gọi đây là bản triển khai Local BASELINE13.

PR #37 được kiểm thử detached ở `151a07b4472ea0fd3134fb50f4f3de757e83d46f`, API Spring
thật và MySQL thật, fixtures ghi rõ SYNTHETIC TEST ONLY. Không sửa/push branch PR #37.
Không phê duyệt nguồn báo thật, không fetch live RSS.

Chưa push khi mandatory validation còn BLOCKED. Không tự merge/approve PR. Rollback
code bằng quy trình review riêng; giữ schema và dữ liệu lịch sử, không DROP bảng.
