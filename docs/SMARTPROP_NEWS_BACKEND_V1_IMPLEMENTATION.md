# SmartProp — News Backend V1

Ngày cập nhật: 2026-11-28. Branch: `feature/news-backend-v1`.

Main frozen được nhóm trưởng duyệt và đã normal-merge: `b49a98fc333cbda1ff38d5511259a5329881812e`. Source HEAD `abf0e3a19018e35e93c113e9e1f625ed0148507d`; product source không đổi so với cây integrated regression.

## Release boundaries

- `LIVE_INGESTION_DISABLED`: `LIVE_INGESTION_PERMITTED=false`; scheduler, manual sync và fetcher đều bị hard-lock.
- `SOURCE_RIGHTS_APPROVAL_PENDING`: không duyệt nguồn báo thật hoặc giả lập bằng chứng quyền sử dụng.
- Không fetch RSS thật, publisher content hoặc tạo article giả trên hệ thống thật.
- DNS rebinding còn là giới hạn V1; race logging 304 nằm trong backlog trước V1.1.

## Public API

Ba route công khai duy nhất:

- `GET /api/v1/news`: phân trang; `category`, `q` tối đa 200 ký tự sau trim, `sort=newest|oldest`, `page` mặc định 0 và không âm, `size` mặc định 12 và giới hạn 1–50.
- `GET /api/v1/news/featured`: trả envelope Page, tối đa 12 bài.
- `GET /api/v1/news/sources`: trả `Source[]` trực tiếp, không bọc object.

Page gồm `items`, `page`, `size`, `totalElements`, `totalPages`, `lastUpdatedAt`, `refreshing=false`, `sources`. Article gồm `id`, `title`, `summary`, `category`, `region`, `articleUrl`, `sourceName`, `sourceUrl`, `publishedAt`, `fetchedAt`, `locationTags`. Source gồm `id`, `name`, `publisher`, `websiteUrl`, `feedUrl`, `count`, `lastSuccessAt`, `status`. Summary, `publishedAt`, URL nguồn và location tags có thể null theo record/rights. Dataset rỗng trả danh sách rỗng và số lượng bằng 0; không tạo nội dung minh họa.

Public chỉ đọc bài VISIBLE thuộc nguồn enabled + APPROVED có `rightsReference` không rỗng/whitespace. Summary chỉ trả khi rights policy cho phép. Không trả rights reference, revision, ETag, lease, lỗi nội bộ hay stack trace. Trước V28 hoặc schema không hợp lệ, API News trả 503 `NEWS_SCHEMA_UNAVAILABLE`.

Admin API nằm dưới `/api/v1/admin/news/**`, yêu cầu ADMIN và kiểm tra account/session theo security architecture hiện tại. Guest 401; Buyer/Broker 403. Tác vụ sync vẫn bị khóa.

## Lineage và Hibernate

Local history được xác thực theo thứ tự V13 baseline, V14 crawler, V17–V28; mọi missing/duplicate/failed/out-of-order/unknown version và checksum mismatch đều từ chối. Local/Staging target 28; Standard target 23. Flyway runtime chỉ validate; không auto-migrate, baseline, repair hoặc sửa history.

`NewsSchemaCapabilities` xác định capability từ lineage đã validate và metadata schema trước khi Hibernate kiểm tra entity:

- Local V21/V26 read-only Advisor: chỉ lọc ba bảng News chưa tồn tại; entity nghiệp vụ khác vẫn được validate.
- Local V27: News API unavailable; cả ba bảng News đang có vẫn được Hibernate validate; V28 constraint chưa bắt buộc.
- Local/Staging full mode V26/V27 từ chối migration pending.
- Local/Staging V28 hợp lệ: validate toàn bộ News và yêu cầu constraint V28 đúng, enforced.
- Standard V23: News unavailable; filter chỉ hợp lệ khi history/checksum V23 và cả ba bảng News không tồn tại.
- Schema không xác định, sai lineage hoặc partial/broken fail closed.

Verifier V28 yêu cầu đúng database hiện hành, bảng `news_sources`, tên `ck_news_sources_approved_reference`, loại CHECK, ENFORCED và biểu thức invariant chính xác: `rights_review_status <> 'APPROVED' OR (rights_reference IS NOT NULL AND REGEXP_LIKE(rights_reference, '[^[:space:]]'))`. Parser có cấu trúc, giữ nguyên literal và chỉ chuẩn hóa cách viết metadata MySQL đã kiểm chứng.

## Rights và concurrency

Constraint V28 từ chối APPROVED khi reference null, rỗng hoặc chỉ whitespace. Preflight trước migration phải dừng nếu có legacy row vi phạm; không tự sửa.

Admin featured/publication updates dùng targeted SQL, xác nhận affected row count, xóa persistence context rồi đọc lại. Concurrency tests dùng transaction thật, barrier/latch, SQL verification và cả hai thứ tự commit. HIDDEN không xuất hiện ở public listing/featured.

## Fixture safety và build

PR41-specific test profile ở `backend/src/test/resources/application-hybrid-local-existing-v13-pr41-isolated.yml`; không có profile tác giả-specific trong production resources. Test cần manifest do provisioner độc lập tạo, authorization rõ ràng và guard trước Spring/JDBC. Expected identity không lấy từ chính connection đang kiểm tra. Giữ fail-closed boundary, lineage/checksum và Hibernate validation. Shared coordinate test không hardcode UUID, schema hoặc đường dẫn máy tác giả.

Production JAR được clean-package sau khi chuyển profile và được kiểm tra không chứa test profile, test class, manifest, credential hoặc fixture. Không dùng shared `.env`.

## Migration integrity

SQL/checksum V13–V28 giữ nguyên so với reviewed PR41 HEAD. V27 Flyway checksum `-1622560226`; V28 `-1006687404`. Không có V29. Không có sửa Flyway history, repair, shared DB migration, rightsReference giả hoặc source approval.

## Validation và trạng thái

Fresh integrated acceptance đã hoàn tất trên approved frozen baseline: backend640, Standard8, portable47, Google real browser1, WP02 runtime4; Python union1.136PASS/0FAIL/ERROR/1optionalSKIP; model101/101. WP04 ba surfaces298checks và real HTTP157checks; giá44cases không drift. Candidate frontend348, PR37frontend65, News/browser, builds và security đều có fresh evidence.

Official ZIP đạt8/8 integrity, model chạy bằng Python3.12/XGBoost3.4.1 pinned; không đổi artifact/calibration. Fixture marker đã tách để giữ Standard historyV1–V23, không auto-baseline; quyền marker tạm được thu hồi trước runtime. Sáu thay đổi mới chỉ thuộc test runners/fixtures.

Xem [test matrix](SMARTPROP_NEWS_BACKEND_V1_TEST_MATRIX.md), [final report](SMARTPROP_NEWS_BACKEND_V1_FINAL_REPORT.md) và [machine-readable acceptance](pr41-evidence/acceptance.json). Final delivery/remote proof được ghi sau push trong PR41/local final manifest. Không approve, merge hoặc deploy.
