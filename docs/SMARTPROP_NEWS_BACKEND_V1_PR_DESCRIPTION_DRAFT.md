## Summary

News Backend V1 read-only, đồng bộ main và giữ coordinate/Admin409/security regression.

```text
identity/reference change -> pending review + disabled -> separate rights review
Standard V23 -> full existing Hibernate validation -> authorized News503
Local BASELINE13 -> strict V26 -> V27 -> V28 -> nonblank APPROVED rights CHECK
live ingestion -> immutable hard lock
```

V28 được nhóm trưởng phê duyệt; Local/Staging target28, Standard23, V13–V27 nguyên vẹn.
Profile kiểm thử3311 riêng pin exact JDBC/schema/UUID/datadir; guard Local/Staging cũ giữ nguyên.

## Evidence

- **Before:** branch behind main15; identity/reference changes retained approval;
  APPROVED without reference was accepted by DB; mandatory Local validation blocked.
  **After:** main merged, strict ordered lineage, V28 SQL3819 on invalid references,
  Admin400 regressions, separate rights review, full Local Hibernate/Flyway validation.
- Final acceptance requires exact final HEAD manifest: backend508 PASS (337 unit +171
  integration/runtime), separate StandardV23 2 PASS, frontend93 + detached PR37 65 PASS;
  backend and both frontend builds exit0. Real Chrome at1440/768/390 plus actual outage,
  no API mocks or uncaught page exceptions. Independent V26→27→28 and V27→28 schemas,
  backups/preflight, strict checksum validation, integrity/fixture cleanup.
- Full report: `docs/SMARTPROP_NEWS_BACKEND_V1_FINAL_REPORT.md`; local evidence:
  `.scratch/evidence/v28/final-validation.json` and migration/Chrome logs.

`NEWS_BACKEND_READY` / `READY_FOR_FINAL_REVIEW` only after all final checks pass.
`LIVE_INGESTION_DISABLED`; `SOURCE_RIGHTS_APPROVAL_PENDING`. No real press source approved.
DNS rebinding remains a V1 limitation.

## Merge Danger

**Door:** two-way for code; V28 schema rollback requires separate review.

**Blast Radius:** moderate

News rights, migration validation, Standard compatibility. Preflight must stop on invalid
APPROVED rows; no reference fabrication/data repair/history rewrite. No shared DB3306/3307,
main push, force-push, other PR branch changes, approve or merge.
