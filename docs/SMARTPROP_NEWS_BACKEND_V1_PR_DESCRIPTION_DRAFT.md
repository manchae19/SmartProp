## Summary

```text
validate ordered migration history and independent database identity
  -> verify News schema capability and exact V28 rights constraint
  -> configure Hibernate validation before EntityManagerFactory startup
  -> serve News only for valid Local V28; keep ingestion hard-locked
```

Local V21/V26 read-only Advisor runtime filters only the three missing News tables. V27 continues validating all existing News tables while News API stays unavailable. Full Local/Staging rejects pending migrations; valid V28 requires the enforced constraint. Machine-specific PR41 bootstrap and fixture identity live only in test sources/resources; production guard classes contain no PR41 UUID, path, or 3311 identity, and clean JAR inspection found no test fixture entries.

## Evidence

- **Before:** Advisor could not start on its valid read-only V21/V26 schema because News capability discovery required V28. **After:** fresh Spring Boot/Hibernate Advisor matrix 13/13; Standard V23/dev/prod matrix 8/8; full backend regression 614/614; V28 MySQL verifier suite 19/19; production JAR excludes test bootstrap/fixture resources.
- Isolated MySQL identity/manifest, authorization, owner, datadir, server UUID and JDBC destination verified on port 3311. Ports 3306/3307 were not contacted. No live RSS, fabricated rights reference, or real source approval.
- Frontend PR41 93/93, PR37 65/65, Chrome/browser runs and frontend builds are **REUSED_EVIDENCE** because this change does not alter frontend/API contract.
- Main approved at `0e9053f0c4085351a7d429f81995f6895ad80e33` is integrated. `origin/main` remains `b49a98fc333cbda1ff38d5511259a5329881812e` and overlaps `AdvisorDtos.java`, `AdvisorValuationAdapter.java`, and `ValuationService.java`; no unapproved merge was made. RAG-only regression is **FRESH_PASS 976/976**. Python V1.3 endpoint tests are NOT_RUN because `artifacts/v1_3/model.json` is absent.
- V13–V28 SQL and history unchanged; V27 checksum `-1622560226`; V28 `-1006687404`. `LIVE_INGESTION_DISABLED`; `SOURCE_RIGHTS_APPROVAL_PENDING`.

## Merge Danger

**Door:** two-way application and migration change; no runtime auto-migration.

**Blast Radius:** moderate

Schema capability changes determine which News entities Hibernate validates. Unknown/broken lineage and constraint definitions fail closed. V28 adds the approved rights check. Live ingestion remains disabled, and source approval remains pending.
