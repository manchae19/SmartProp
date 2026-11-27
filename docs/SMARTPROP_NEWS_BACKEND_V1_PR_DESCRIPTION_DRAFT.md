## Summary

```text
validate ordered lineage, identity and Flyway checksum
  -> inspect actual News tables and V28 rights constraint
  -> configure Hibernate validation for that schema capability
  -> enable News API only for valid Local V28
```

Local V21/V26 can keep the read-only Advisor online while Hibernate filters the three absent News tables. V27 keeps News API unavailable but validates every existing News table. Local/Staging full mode still rejects pending V27/V28, and valid V28 requires the enforced rights constraint.

## Evidence

- **Before:** The Advisor's read-only Local V21/V26/V27 schema could not start because News capability discovery required V28. **After:** `AdvisorReadOnlyRuntimeIT` passes 13/13 with Spring Boot and Hibernate, including Advisor HTTP 200, News HTTP 503 for V21/V26/V27, full-mode pending rejection, invalid lineage/checksum/constraint refusal, broken V27 column and unexpected News view rejection, and pre-connection isolation checks.
- Standard V23 Hibernate/API regression: 2/2 fresh. `ValuationServiceTest`: 12/12 fresh after merging latest `main`.
- MySQL fixture identity, UUID, datadir, owner, process and JDBC URL verified. The test driver recorded only the approved isolated 3311 fixture; ports 3306/3307 were not contacted. Before/after database snapshots matched.
- Frontend PR41 93/93, PR37 65/65, Chrome E2E and production builds are **REUSED_EVIDENCE** because this follow-up changes no frontend/API contract.
- V13–V28 SQL/checksums and Flyway history are unchanged. V27 checksum `-1622560226`; V28 checksum `-1006687404`. `LIVE_INGESTION_DISABLED`; `SOURCE_RIGHTS_APPROVAL_PENDING`.

## Merge Danger

**Door:** two-way application code change; no migration added or edited.

**Blast Radius:** moderate

Hibernate validation selection and News capability discovery. Invalid or unknown lineage remains fail-closed. No live ingestion or source approval is enabled.
