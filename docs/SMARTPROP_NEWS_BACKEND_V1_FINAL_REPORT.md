# PR #41 — Targeted final review fixes

Reviewed starting HEAD: `765cc5e1ea1fc68cc90ea601912c74144731202a`.
Only the requested1 P1 and2 P2 are addressed. Final acceptance is recorded against the
committed HEAD in `.scratch/evidence/targeted/final-validation.json`; never infer a gate
from this report alone. No approve/merge or changes to other branches.

| Item | Result and evidence |
|---|---|
| A. Standard runtime fix | `NewsSchemaCapabilities` validates actual ordered history/checksums and table capability before the Hibernate customizer is created. Standard23 excludes only the3 absent News tables; unknown/partial schema refuses startup. |
| B. Dev/prod | Real Spring/Hibernate matrix: standard-migrations, dev, prod, dev+prod; News public503, Guest401, User/Broker403, valid Admin503. Property create/detail/search smoke under Standard/dev/prod.11 tests,0 failures/skips. |
| C. Local/Staging | Full News validation remains enabled.5 real-runtime tests: Local, staging configuration imported under the strict approved3311 profile, missing table, missing column and disabled CHECK. Native Local3306/Staging3307 identity guards unchanged; no3306/3307 connection. Existing strict/pending V26/V27/V28 regression remains in full unit suite. |
| D. Concurrent decisions | Targeted repository UPDATE writes only featured+updated_at or publication_status+updated_at; affected-row check retains404; clear context and reread prevent stale response. |
| E. Actual SQL/transactions |5 Admin tests: two overlapping real transactions, latches, both commit orders, stale article snapshots and source identity bulk hide; captured SQL and public list/featured exclusion assertions. No arbitrary sleep. |
| F. Portable safety | Independent provisioner manifest authorizes destination, port/schema/UUID/datadir and process ownership/config/start time. Shared Coordinate test has no author paths/UUID/schema. Test-only bootstrap retains strict history/checksum/Hibernate validation. |
| G. Coordinate regression |39/39 on original3311 and39/39 on separately provisioned3312;8 safety tests on each,0 skip. Negative UUID/schema/datadir/destination/owner/authorization/protected-port cases refuse access. |
| H. Backend | Full fresh backend521 tests (337 unit +184 integration/runtime),0 fail/error/skip; separate Standard11, Local/staging5 and portable fixture47. Logs/exit codes and tested final SHA in final manifest. Backend production package checked separately. |
| I. Migration integrity | No migration SQL V13–V28 changes, noV29, no repair/history edits. V27=-1622560226, V28=-1006687404; Flyway validates unchanged resources. An older V27 checksum must stop deployment for review, never repair. |
| J. PR37 compatibility | DTO/frontend/public contract unchanged. Frontend PR41 93/93, PR37 65/65, Chrome real E2E and frontend builds are **REUSED_EVIDENCE** from reviewed HEAD765cc5e, not fresh PASS. |
| K. Delivery | Fetch confirms main1f36205 unchanged. No targeted-file overlap with PR37/44/45 or Research Access. Final local/remote SHA and PR readback are recorded after push in final manifest. |
| L. Limits | LIVE_INGESTION_DISABLED; SOURCE_RIGHTS_APPROVAL_PENDING. DNS rebinding remains V1 limitation;304 logging race stays backlog beforeV1.1. No live RSS or real-source approval. |

Only emit final gates after the corresponding final-HEAD execution and remote readback:
STANDARD_V23_DEV_RUNTIME_PASS, STANDARD_V23_PROD_RUNTIME_PASS,
STANDARD_V23_MIGRATION_PROFILE_PASS, LOCAL_STAGING_V28_STRICT_VALIDATION_PASS,
NEWS_ADMIN_CONCURRENT_UPDATE_PASS, HIDDEN_ARTICLE_PUBLIC_EXCLUSION_PASS,
COORDINATE_IT_PORTABLE_ISOLATION_PASS, COORDINATE_PROVENANCE_REGRESSION_PASS,
MIGRATION_CHECKSUM_INTEGRITY_PASS, REMOTE_HEAD_VERIFIED, READY_FOR_TARGETED_FINAL_REVIEW.

See [test matrix](SMARTPROP_NEWS_BACKEND_V1_TEST_MATRIX.md) and
[fixture provisioning](testing/ISOLATED_DATABASE_FIXTURES.md). Raw logs, backups, manifests,
tokens and fixtures stay outside Git. Final evidence distinguishes FRESH_PASS, REUSED_EVIDENCE,
FAIL, BLOCKED and NOT_RUN. The original workspace/main/stashes remain intact.
