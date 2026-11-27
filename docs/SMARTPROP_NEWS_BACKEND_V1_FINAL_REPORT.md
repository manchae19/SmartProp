# PR #41 — Final completion report

Ngày: 2026-11-27. **VALIDATION_PARTIAL**.
`LIVE_INGESTION_DISABLED` · `SOURCE_RIGHTS_APPROVAL_PENDING`.
Chưa đủ điều kiện `NEWS_BACKEND_READY` / `READY_FOR_FINAL_REVIEW`; dừng để nhóm trưởng review.

| Mục | Kết quả |
|---|---|
| A. Main synchronization | Merge main 1f36205; giữ provenance, accuracy, GIS eligibility, Admin Coordinate Review, 409 lock và cả coordinate/News routes. |
| B. V27 lineage | Strict order từ main, V27 sau V26; target Local27/Standard23. V13–V27 và identity guard không sửa. 32+18 migration unit tests; real Flyway checksum negative. |
| C. Standard V23 | Hibernate validate giữ nguyên; chỉ loại ba bảng News khỏi Standard validation. Hai runtime/HTTP tests PASS; public/Admin503 và 401/403 đúng auth; property create/detail/search hoạt động. |
| D. Source rights | Identity/reference change mất approval; disabled; bài cũ được giữ nhưng ẩn; central policy, callbacks và SQL từ chối invalid references; summary read/search enforcement. DB CHECK còn BLOCKED. |
| E. Release gate | false compile-time; scheduler dừng trước repository; manual/service/fetcher không fetch. Test-only transport không nằm trong production jar. |
| F. Security | SSRF/XXE/allowlist/timeouts/deadline/size/Retry-After/304 regression PASS. DNS rebinding vẫn là limitation V1. |
| G. Concurrency/fencing | 19 lease/concurrency +19 fencing tests PASS; kiểm tra expiry theo thời gian thực sau row lock; source revision fence cho cả failure metadata. |
| H. Backend | 329 unit +163 integration/fixture =492 PASS, 0 fail/error/skip. Separate Standard run 2 PASS. |
| I. Frontend | PR41:93 PASS; PR37 detached:65 PASS; 0 fail/skip. |
| J. Production build | Backend package, PR41 frontend và PR37 frontend build exit0. |
| K. Public/Admin HTTP | MockMvc + MySQL và real HTTP registration/login; Guest401, Buyer/Broker403, Admin200; manual sync hard locked. |
| L. PR37 integration | Detached SHA151a07b; frontend14137 -> real backend18141 -> MySQL3311; synthetic fixtures only; no PR37 branch writes. |
| M. Chrome E2E | 12 scenario groups + real outage; desktop/tablet/mobile; screenshots; 0 uncaught page exceptions; no mocked News API. |
| N. Database integrity | Own MySQL PID7604/UUID0f29afde-ea54-11f1-bcac-088fc36287dc,3311; backup before migration. Final read-only integrity/lineage evidence in scratch. No3306/3307 access. |
| O. Final commit SHA | `.scratch/evidence/final-head.txt` and final execution manifest record the commit tested after commit; report does not embed its own commit hash. |
| P. GitHub PR | PR41 open, base main unchanged. Remote head remains a8107dd until mandatory validation is unblocked. No push/force-push/merge/approve. |
| Q. Blockers | See below. |
| R. Evidence | `.scratch/evidence/`; `.scratch/mysql-pr41/evidence/`; backup hashes in manifest. Private credentials/dumps/logs/fixtures excluded from Git. |

## Remaining blockers

1. **Database CHECK approval:** group lead has not reserved/approved V28 or a replacement
   version. Main/remote refs including WP-01 `feature/pre-purchase-checks@cbd0032` show no
   V28+, but unpublished work remains unknown. Need official version reservation and
   target/deployment approval before a forward-only constraint can reject APPROVED
   with NULL, empty or whitespace-only rightsReference at the database boundary.
   Do not edit V27, invent rightsReference, or rewrite legacy data/history.
2. **Exact Local deployment validation:** MySQL3311 is approved and isolated, but main's
   Local staging profile is pinned to3307/schema smartprop/datadir mysql-isolated/data.
   No identity guard was loosened and the old instance was not accessed. The successful
   SQL test used a fresh Standard V23 schema plus unchanged V26/V27. An approved way to
   recreate and validate the original Local BASELINE13 lineage on the dedicated test
   instance is still required; this test must not be relabelled as an exact Local deploy.

No press source was approved and no live RSS was requested. Historical live results
are not fresh acceptance evidence. Workspaces/branches PR37/38/39 and WP-01 remain
untouched. Original main workspace stays on its original main HEAD with its untracked
`.tools/` and stash intact.

Full commands and per-suite counts: [test matrix](SMARTPROP_NEWS_BACKEND_V1_TEST_MATRIX.md).
Current architecture/operating limits: [implementation](SMARTPROP_NEWS_BACKEND_V1_IMPLEMENTATION.md).
