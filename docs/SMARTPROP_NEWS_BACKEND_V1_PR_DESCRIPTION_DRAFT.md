## Summary

**VALIDATION_PARTIAL — local completion changes have not been pushed.**
Live ingestion remains hard locked; real publisher rights approvals remain pending.

```text
identity/reference change -> pending review + disabled -> separate rights review
Standard V23 -> existing Hibernate validation + News503 after authorization
Local history -> strict ordered V26 -> V27; target27, no guard relaxation
```

Local completion merges main1f36205, preserves coordinate/admin409/security behavior,
centralizes rights enforcement, hides historical articles on identity change, and
strengthens lease/revision fencing. Production transport has no package-callable gate bypass.

## Evidence

- **Before:** branch behind main15; loose migration validation; source website/reference
  changes could retain approval; old ingestion tests expected pre-lock behavior.
  **After:** strict ordered history + V26 guard; identity/reference review lifecycle;
  StandardV23 validate/503 coverage; immutable gate tests and fixture-only persistence tests.
- Backend492 PASS (329 unit +163 integration/fixture), StandardV23 runtime2 PASS,
  frontend93 PASS; detached PR37 frontend65 PASS. Builds exit0. Chrome real backend/MySQL
  integration12 groups plus actual outage, no page exceptions at1440/768/390.
- All completion evidence is local until the mandatory gates are satisfied. Remote
  head remains a8107dd; this body does not claim the local code is present in the PR diff.

**Blocked:** no group-lead approval/reservation for forward-only rightsReference DB CHECK
migration; no exact LocalBASELINE13 deployment/runtime validation on approved3311 without
changing main's fixed staging identity guard. No V28, target28, history repair, real-source
approval or live RSS. Synthetic SQL V26->V27/validate/checksum tests PASS but are not an
exact LocalBASELINE13 deployment. Do not merge or mark NEWS_BACKEND_READY.

## Merge Danger

**Door:** two-way for code; schema/data rollback requires separate review.

**Blast Radius:** moderate

News backend, migration validation and StandardV23 compatibility. V13–V27 unchanged;
coordinate provenance/admin behavior retained. No main push, force push, new PR, merge,
approval, DB3306/3307 access or PR37/38/39/WP-01 branch changes.
