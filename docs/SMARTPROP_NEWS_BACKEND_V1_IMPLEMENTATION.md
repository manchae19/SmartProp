# SmartProp — News Backend V1

Ngày cập nhật: 2026-11-27. Branch: `feature/news-backend-v1`.
Main tích hợp: `1f36205fbff5ef04f43c27af83c1694d500a9d61`.

## Trạng thái release

- `NEWS_BACKEND_READY` / `READY_FOR_TARGETED_FINAL_REVIEW`: xác nhận bằng fresh validation trên final commit và final manifest trước push.
- `LIVE_INGESTION_DISABLED`: hằng số `LIVE_INGESTION_PERMITTED=false` bắt buộc giữ nguyên.
- `SOURCE_RIGHTS_APPROVAL_PENDING`: không có nguồn báo chí thật nào được phê duyệt trong đợt này.
- Không công bố `NEWS_BACKEND_READY` hoặc `READY_FOR_TARGETED_FINAL_REVIEW` khi còn blocker.

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

Local/Staging target = **28**; Standard target = **23**. V13–V27 giữ nguyên checksum.
Nhóm trưởng đã dành V28 cho `V28__news_source_rights_constraint.sql`: CHECK từ chối
APPROVED với reference NULL, rỗng hoặc toàn whitespace, gồm Unicode whitespace.
Preflight phải có 0 invalid APPROVED rows trước migration; nếu có, dừng để chủ dữ liệu
xử lý theo quy trình review. Không tạo reference giả, tự approve nguồn hoặc sửa history.

Local/Staging identity boundaries cũ giữ nguyên. Profile riêng
`hybrid-local-existing-v13-pr41-isolated` chỉ chấp nhận literal JDBC URL
`jdbc:mysql://127.0.0.1:3311/pr41_local?connectionTimeZone=UTC`, exact UUID/datadir
ở dưới; không cho profile mixing, auto-DDL, auto-migrate hoặc pending-schema override.
Runtime yêu cầu V26/V27/V28 hoàn tất, validate checksum bằng Flyway và Hibernate.

## Standard V23

Standard V23 capability được xác định từ ordered history và Flyway checksum thực tế,
không dựa vào tên dev/prod/standard-migrations. Bean capability là dependency của Hibernate
customizer, vì vậy hoàn tất trước EntityManagerFactory/schema validation. Chỉ Standard23
đã validate và vắng cả3 bảng News mới dùng filter. Unknown/partial schema fail closed.
Mọi bảng/entity khác giữ ddl-auto=validate; Local V28 luôn validate đủ News, yêu cầu CHECK
V28 enforced và giữ nguyên identity/pending/strict history guards.
NewsSchemaAvailability dùng cùng capability: News public503, Admin auth trước503.
Runtime regression gồm Standard/dev/prod/dev+prod và property create/detail/search.

Admin featured/visibility dùng targeted UPDATE riêng, kiểm tra affected rows, clear persistence
context rồi đọc lại. Transaction/latch tests kiểm tra stale snapshots, cả hai thứ tự commit,
source identity bulk hide và actual SQL; HIDDEN không xuất hiện ở list/featured public.

Shared Coordinate integration dùng [manifest fixture độc lập](testing/ISOLATED_DATABASE_FIXTURES.md)
và bootstrap test-only với validation history/checksum/Hibernate đầy đủ; không hardcode
identity tác giả, không thay guard production. Frontend/Chrome evidence từ765cc5e được ghi
REUSED_EVIDENCE trong vòng targeted này; backend và targeted runtime chạy fresh.

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
`0f29afde-ea54-11f1-bcac-088fc36287dc`. PID khởi tạo 7604, lần chạy V28 PID7804, executable/config/datadir
đã xác minh; backup trước migration. Không kết nối 3306/3307, không dừng MySQL80/WP-01.
Schema `pr41_standard` là V1–V23. `pr41_local` dùng schema-only synthetic baseline,
Flyway baseline13 mới qua CLI chính thức, nguyên bản crawler14 và Local17–28.
Không copy/sửa history hay nhập dữ liệu từ DB thật. Hai schema mới độc lập xác minh
V26 → V27 → V28 và V27 → V28; backup trước mỗi bước, preflight trước V28.
Runtime identity gồm port/schema/UUID/datadir/JDBC URL; process ownership được ghi
trong evidence. Guard Local3306/Staging3307 cũ được kiểm thử bằng mocks, không kết nối.

PR #37 được kiểm thử detached ở `151a07b4472ea0fd3134fb50f4f3de757e83d46f`, API Spring
thật và MySQL thật, fixtures ghi rõ SYNTHETIC TEST ONLY. Không sửa/push branch PR #37.
Không phê duyệt nguồn báo thật, không fetch live RSS.

Chỉ push branch hiện tại sau khi fresh validation trên final commit đạt đầy đủ. Không tự merge/approve PR. Rollback
code bằng quy trình review riêng; giữ schema và dữ liệu lịch sử, không DROP bảng.
