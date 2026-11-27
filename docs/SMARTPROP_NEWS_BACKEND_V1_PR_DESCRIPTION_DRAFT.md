## Summary

Targeted fixes for1 P1 and2 P2 from review of765cc5e. No News V1 scope expansion.

```text
DB ordered lineage + checksum -> capability -> Hibernate validation/filter -> controlled News503
featured UPDATE -> featured, updated_at -> clear + reread
visibility UPDATE -> publication_status, updated_at -> clear + reread
independent fixture manifest -> owned process + exact identity -> strict Local history/Hibernate
```

## Evidence

- **Before:** Standard23+dev failed on missing news_articles; stale Admin entity save could
  restore HIDDEN to VISIBLE; shared Coordinate test required the author's3311 identity.
  **After:** Standard/dev/prod/dev+prod runtime matrix; actual targeted SQL with two concurrent
  transactions and both commit orders;39 Coordinate tests on each of two independent fixtures.
- Fresh final-HEAD backend521 PASS, Standard matrix11, Local/staging configuration and broken
  schema runtime5, portable Coordinate/safety47;0 fail/error/skip. Backend package and fresh
  migration checksum validation recorded in local final manifest.
- Frontend93/65, Chrome real E2E and frontend builds are **REUSED_EVIDENCE** from765cc5e;
  public DTO/frontend contract unchanged. Staging configuration is tested on approved3311
  identity; native3306/3307 endpoints are never contacted, production guards unchanged.
- Report: `docs/SMARTPROP_NEWS_BACKEND_V1_FINAL_REPORT.md`; fixture guide:
  `docs/testing/ISOLATED_DATABASE_FIXTURES.md`; final SHA/commands/exits/SQL/identity:
  `.scratch/evidence/targeted/final-validation.json`.

Keep LIVE_INGESTION_DISABLED and SOURCE_RIGHTS_APPROVAL_PENDING. DNS rebinding remains
V1 limitation;304 log race stays backlog. No real press-source approvals or live RSS.

## Merge Danger

**Door:** two-way code change; no migration added or edited.

**Blast Radius:** moderate

Hibernate capability selection and News Admin updates; shared Coordinate test bootstrap only.
V13–V28 SQL/checksums unchanged (V27=-1622560226, V28=-1006687404). Older V27 checksum
must stop for review, never repair. No changes to other branches, approve, merge or force-push.
