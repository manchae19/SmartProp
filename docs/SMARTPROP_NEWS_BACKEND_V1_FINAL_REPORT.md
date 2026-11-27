# PR #41 — Targeted final review fixes

## P1 Advisor compatibility addendum

This addendum records the focused follow-up on top of the fetched `origin/main` merge at
`a0e38349807b23fa071d0779d0a6211be9f3fb99`. The resulting code is validated against actual
Local V21, V26, V27 and V28 lineage and schema capability before Hibernate validates the
entity model. V21/V26 omit only the absent News tables from Hibernate validation; V27 validates
all three News tables while News API remains unavailable; only V28 with the enforced rights
constraint enables News API. Unknown Local versions and invalid histories/checksums fail closed.

Fresh evidence on this follow-up: `AdvisorReadOnlyRuntimeIT` 13/13, Standard V23 runtime 2/2,
and `ValuationServiceTest` 12/12. The Advisor suite verifies HTTP 200 for the read-only Advisor,
News API 503 for V21/V26/V27, strict Local/Staging policy-simulation rejection while V27/V28 are pending,
Hibernate rejection of a broken V27 column, V28 availability, checksum/history/constraint
refusal, read-only session behavior, and protected/fallback destination rejection before JDBC.
Database snapshots matched before/after runtime. The test-only guarded driver recorded no
physical destination outside the authorized 3311 fixture. The Spring app booted with a test-only
simulation profile that invokes the real Local/Staging guard against the explicit policy values;
native shared profile endpoints 3306 and 3307 were not contacted.

V13–V28 migration SQL and Flyway history were not changed; V27 checksum remains
`-1622560226` and V28 remains `-1006687404`. This follow-up adds no migration. Frontend PR41
93/93, PR37 65/65, Chrome E2E and production builds remain **REUSED_EVIDENCE** because this
follow-up changes no frontend/API contract. `LIVE_INGESTION_DISABLED` and
`SOURCE_RIGHTS_APPROVAL_PENDING` remain in force.

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
| K. Delivery | Historical delivery evidence above predates the latest main merge and is superseded for this follow-up. Latest `origin/main` is `a0e38349807b23fa071d0779d0a6211be9f3fb99`; PR44's 34 merged files have no overlap with this follow-up's changed files. Final branch/remote verification is recorded after push. |
| L. Limits | LIVE_INGESTION_DISABLED; SOURCE_RIGHTS_APPROVAL_PENDING. DNS rebinding remains V1 limitation;304 logging race stays backlog beforeV1.1. No live RSS or real-source approval. |

The gate list above belongs to the earlier reviewed HEAD and is not evidence for the post-merge
follow-up by itself. For this follow-up, emit only after commit, push and remote readback:
ADVISOR_READ_ONLY_V21_V26_V27_RUNTIME_PASS, HIBERNATE_V27_SCHEMA_VALIDATION_PASS,
LOCAL_STAGING_PENDING_MIGRATION_REFUSAL_PASS, V28_RIGHTS_CONSTRAINT_CAPABILITY_PASS,
FIXTURE_PRECONNECTION_ISOLATION_PASS, MERGED_MAIN_OVERLAP_CHECK_PASS,
REMOTE_HEAD_VERIFIED, READY_FOR_LAST_P1_REVIEW.

See [test matrix](SMARTPROP_NEWS_BACKEND_V1_TEST_MATRIX.md) and
[fixture provisioning](testing/ISOLATED_DATABASE_FIXTURES.md). Raw logs, backups, manifests,
tokens and fixtures stay outside Git. Final evidence distinguishes FRESH_PASS, REUSED_EVIDENCE,
FAIL, BLOCKED and NOT_RUN. The original workspace/main/stashes remain intact.
