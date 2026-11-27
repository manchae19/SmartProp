# PR #41 — Targeted final test matrix

## Advisor compatibility follow-up after `origin/main` merge

| Suite | Pass | Fail/error/skip | Evidence |
|---|---:|---|---|
| Advisor read-only Local V21/V26/V27 + strict Local/Staging policy simulation + negative lineage/schema/guards |13|0/0/0|**FRESH_PASS** `AdvisorReadOnlyRuntimeIT`; real Spring Boot/Hibernate; JDBC allowlist only authorized port3311 fixture; before/after snapshots equal; an unexpected News view is refused |
| Standard V23 Hibernate/API regression |2|0/0/0|**FRESH_PASS** `NewsStandardV23IT` on isolated Standard fixture at3311 |
| Merged-main valuation regression |12|0/0/0|**FRESH_PASS** `ValuationServiceTest` |
| Frontend PR41/PR37, Chrome E2E, production builds |93/65 + existing E2E/build|—|**REUSED_EVIDENCE** from reviewed PR41 result; this follow-up changes no frontend/API contract |
| MySQL ownership/isolation |—|—|**FRESH_PASS** fixture manifest/config SHA, UUID, datadir, owner, process and JDBC URL verified for3311; no3306/3307 destination in the runtime driver log |
| Migration integrity |—|—|**FRESH_PASS** runtime Flyway validate on Local V21/V26/V27/V28; checksum-negative fixture refused; no V13–V28 source/history edits and no V29 |

The focused follow-up command was `AdvisorReadOnlyRuntimeIT` (13 tests), followed by
`NewsStandardV23IT` (2 tests) and `ValuationServiceTest` (12 tests). The first two used the
test-only independent fixture manifest and explicitly authorized guarded JDBC driver on port
3311; Flyway migration and SQL initialization were disabled. Local/Staging guard behavior used
the test-only profile simulation and actual guard implementation. Native shared-database
profiles were not used. These fresh runs replace no unrelated earlier evidence and do not imply
live-ingestion or native shared-database testing.

Final SHA, commands, per-suite results and exit codes:
`.scratch/evidence/targeted/final-validation.json`. Logs below must be freshly produced
after the final commit. Precommit/red reproduction logs remain separate and are not final PASS.

| Suite | Pass | Fail/error/skip | Evidence |
|---|---:|---|---|
| Backend full unit |337|0/0/0|Included in full-final log |
| Backend full combined |521|0/0/0|`targeted-full-final.log`; all previously required rights/security/fencing/HTTP/Coordinate tests plus Admin concurrency5 and portable guard8 |
| CoordinateProvenanceIT on3311 |39|0/0/0|Included in full combined |
| NewsAdminConcurrentIT |5|0/0/0|Included in full combined; actual targeted SQL, real overlapping transactions, both orders |
| IsolatedDatabaseSafetyIT on3311 |8|0/0/0|Included in full combined |
| Standard runtime matrix |11|0/0/0|`targeted-standard-final.log`; standard-migrations/dev/prod/dev+prod, HTTP auth/503, partial News schema refusal, property smoke |
| Local/staging configuration + broken schemas |5|0/0/0|`targeted-local-staging-final.log`; real Spring/Hibernate; staging file imported under approved strict3311 identity, no3307 connection |
| Portable Coordinate + safety on3312 |47|0/0/0|`targeted/portable-coordinate-final.log`;39 Coordinate +8 safety on a second UUID/datadir/schema/PID |
| Backend production package |—|exit0|`targeted/backend-package-final.log`; test bootstrap/fixtures excluded |
| Migration integrity |—|exit0|Fresh Flyway validate and Git blob comparison V13–V28; DB V27/V28 checksums recorded |
| Frontend PR41 full unit |93|0/0/0|**REUSED_EVIDENCE** from765cc5e |
| Frontend PR37 full unit |65|0/0/0|**REUSED_EVIDENCE**, detached151a07b integration at765cc5e |
| Chrome real E2E + outage |12 groups+outage|0 page exceptions|**REUSED_EVIDENCE** from765cc5e |
| Frontend production builds |—|exit0|**REUSED_EVIDENCE** from765cc5e |
| Native shared DB3306/3307 or live RSS |—|—|**NOT_RUN**, forbidden |

Full backend command uses JDK21, explicit3311 DB_URL, independent fixture manifest and
separate authorization; no shared `.env`:

```powershell
./backend/mvnw.cmd -f backend/pom.xml test '-Dtest=*Test,NewsLocalLineageIT,NewsApiIT,NewsAdminConcurrentIT,NewsConcurrencyIT,NewsFencingIT,NewsSafetyGateIT,NewsReleaseLockIT,NewsLiveIngestionIT,NewsDatabaseConstraintsIT,NewsSourceRightsIT,NewsFeedFetcherIT,NewsBodyTimeoutIT,CoordinateProvenanceIT,IsolatedDatabaseSafetyIT'
# Separate Standard23 process/schema:
./backend/mvnw.cmd -f backend/pom.xml test '-Dtest=NewsStandardV23IT,NewsStandardDevIT,NewsStandardProdIT,NewsStandardCombinedIT,StandardLineageCompatibilityIT,StandardDevCompatibilityIT,StandardProdCompatibilityIT'
# Separate exclusive Local fixture run; negative tests restore DDL in finally:
./backend/mvnw.cmd -f backend/pom.xml test '-Dtest=NewsLocalLineageIT,NewsStagingConfigurationIT,NewsBrokenSchemaRuntimeIT'
# Different allocated fixture, manifest and credentials; no deployment-specific profile:
./backend/mvnw.cmd -f backend/pom.xml test '-Dtest=CoordinateProvenanceIT,IsolatedDatabaseSafetyIT'
```

The actual final runner supplies profile/environment authorization explicitly and records
all command exits. Negative tests only alter owned synthetic schemas, with backups first;
they do not edit migration SQL/history. The existing pending/checksum/strict order tests
are included in the unit run. Fixture provisioning: [guide](testing/ISOLATED_DATABASE_FIXTURES.md).
