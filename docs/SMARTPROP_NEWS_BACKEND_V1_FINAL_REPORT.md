# PR #41 — Final completion report

Ngày: 2026-11-27. **READY_FOR_FINAL_REVIEW**.
`LIVE_INGESTION_DISABLED` · `SOURCE_RIGHTS_APPROVAL_PENDING`.
`NEWS_BACKEND_READY` sau khi final manifest xác nhận toàn bộ mandatory checks trên đúng final HEAD; dừng để nhóm trưởng review.

| Mục | Kết quả |
|---|---|
| A. Main synchronization | Merge main 1f36205; giữ provenance, accuracy, GIS eligibility, Admin Coordinate Review, 409 lock và cả coordinate/News routes. |
| B. V27 lineage | Strict order từ main, V27 sau V26; target Local/Staging28, Standard23. V28 được nhóm trưởng phê duyệt. V13–V27 và identity guard không sửa. 32+18+8 migration/identity unit tests; real Flyway checksum negative. |
| C. Standard V23 | Hibernate validate giữ nguyên; chỉ loại ba bảng News khỏi Standard validation. Hai runtime/HTTP tests PASS; public/Admin503 và 401/403 đúng auth; property create/detail/search hoạt động. |
| D. Source rights | Identity/reference change mất approval; disabled; bài cũ được giữ nhưng ẩn; central policy, callbacks và SQL từ chối invalid references; summary read/search enforcement. V28 DB CHECK chặn NULL/rỗng/Unicode whitespace trên INSERT/UPDATE; Admin regression400. |
| E. Release gate | false compile-time; scheduler dừng trước repository; manual/service/fetcher không fetch. Test-only transport không nằm trong production jar. |
| F. Security | SSRF/XXE/allowlist/timeouts/deadline/size/Retry-After/304 regression PASS. DNS rebinding vẫn là limitation V1. |
| G. Concurrency/fencing | 19 lease/concurrency +19 fencing tests PASS; kiểm tra expiry theo thời gian thực sau row lock; source revision fence cho cả failure metadata. |
| H. Backend | 337 unit +171 integration/fixture/runtime =508 PASS, 0 fail/error/skip. Separate Standard run 2 PASS. |
| I. Frontend | PR41:93 PASS; PR37 detached:65 PASS; 0 fail/skip. |
| J. Production build | Backend package, PR41 frontend và PR37 frontend build exit0. |
| K. Public/Admin HTTP | MockMvc + MySQL và real HTTP registration/login; Guest401, Buyer/Broker403, Admin200; manual sync hard locked. |
| L. PR37 integration | Detached SHA151a07b; frontend14137 -> real backend18141 -> MySQL3311; synthetic fixtures only; no PR37 branch writes. |
| M. Chrome E2E | 12 scenario groups + real outage; desktop/tablet/mobile; screenshots; 0 uncaught page exceptions; no mocked News API. |
| N. Database integrity | Own MySQL PID7804/UUID0f29afde-ea54-11f1-bcac-088fc36287dc,3311; backup before migration. Final read-only integrity/lineage evidence in scratch. No3306/3307 access. |
| O. Final commit SHA | `.scratch/evidence/final-head.txt` and final execution manifest record the commit tested after commit; report does not embed its own commit hash. |
| P. GitHub PR | PR41 open, base main unchanged. Push chỉ feature/news-backend-v1 sau final checks; remote HEAD phải khớp final manifest. Không force-push/merge/approve. |
| Q. Blockers | See below. |
| R. Evidence | `.scratch/evidence/`; `.scratch/mysql-pr41/evidence/`; backup hashes in manifest. Private credentials/dumps/logs/fixtures excluded from Git. |

## Remaining blockers

Không còn blocker phê duyệt V28. Final manifest là điều kiện bắt buộc trước push và
xác nhận READY. Hai schema synthetic mới chạy V26 → V27 → V28 và V27 → V28; Local
BASELINE13 runtime dùng exact-identity profile3311, giữ nguyên guard Local/Staging cũ.
Checksums V13–V27 giữ nguyên. Preflight không có invalid APPROVED rows; không sửa
dữ liệu legacy/history. DB constraint và Admin API từ chối reference không hợp lệ.
DNS rebinding vẫn là limitation V1; live ingestion luôn đóng.

No press source was approved and no live RSS was requested. Historical live results
are not fresh acceptance evidence. Workspaces/branches PR37/38/39 and WP-01 remain
untouched. Original main workspace stays on its original main HEAD with its untracked
`.tools/` and stash intact.

Full commands and per-suite counts: [test matrix](SMARTPROP_NEWS_BACKEND_V1_TEST_MATRIX.md).
Current architecture/operating limits: [implementation](SMARTPROP_NEWS_BACKEND_V1_IMPLEMENTATION.md).
