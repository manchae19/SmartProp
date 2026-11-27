# PR #41 — Targeted final test matrix

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
