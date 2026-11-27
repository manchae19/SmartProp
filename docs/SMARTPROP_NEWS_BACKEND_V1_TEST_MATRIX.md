# PR #41 — Test matrix

Ngày: 2026-11-27. Trạng thái tổng: **READY_FOR_FINAL_REVIEW** (chỉ xác nhận sau khi đối chiếu final manifest).
Các PASS dưới đây có execution mới trong phiên; bản chạy sau commit phải đối chiếu
SHA ở `.scratch/evidence/final-head.txt`, log `*-final.log` và manifest cùng thư mục.
Không dùng kết quả trước 2026-11-27 làm fresh PASS.

| Surface / suite | Pass | Fail | Skip | Status / limitation |
|---|---:|---:|---:|---|
| Full Backend unit (`*Test`) | 337 | 0 | 0 | FRESH_PASS |
| NewsApiIT | 27 | 0 | 0 | FRESH_PASS, MockMvc + real MySQL |
| NewsConcurrencyIT | 19 | 0 | 0 | FRESH_PASS |
| NewsFencingIT | 19 | 0 | 0 | FRESH_PASS, stale timestamp regression included |
| NewsSafetyGateIT | 9 | 0 | 0 | FRESH_PASS |
| NewsReleaseLockIT | 14 | 0 | 0 | FRESH_PASS |
| NewsLiveIngestionIT | 1 | 0 | 0 | FRESH_PASS, asserts hard lock/no interactions; no live RSS |
| NewsDatabaseConstraintsIT | 10 | 0 | 0 | FRESH_PASS, UNIQUE/FK/enum + V28 INSERT/UPDATE/Unicode whitespace |
| NewsSourceRightsIT | 14 | 0 | 0 | FRESH_PASS |
| NewsFeedFetcherIT | 13 | 0 | 0 | FRESH_PASS, local fixture HTTP only |
| NewsBodyTimeoutIT | 5 | 0 | 0 | FRESH_PASS, local fixture HTTP only |
| CoordinateProvenanceIT | 39 | 0 | 0 | FRESH_PASS, includes stale revision/409/admin decisions |
| Combined Backend run above, including NewsLocalLineageIT (1) | 508 | 0 | 0 | FRESH_PASS |
| NewsStandardV23IT + StandardLineageCompatibilityIT | 2 | 0 | 0 | FRESH_PASS, real Hibernate validate + MySQL V23 |
| MigrationLineageConfigurationTest | 32 | 0 | 0 | Included in unit total |
| MigrationLineageStrictTest | 18 | 0 | 0 | Included in unit total |
| PR41 frontend full unit | 93 | 0 | 0 | FRESH_PASS, includes Admin Coordinate Review regression |
| PR37 detached frontend full unit | 65 | 0 | 0 | FRESH_PASS on PR37 SHA 151a07b |
| Backend production package | — | 0 | — | FRESH_PASS, exit 0; tests run separately |
| PR41/PR37 production frontend builds | — | 0 | — | FRESH_PASS, exit 0 each |
| Isolated Local V26 -> V27 -> V28 and V27 -> V28 | — | 0 | — | FRESH_PASS, new BASELINE13 schemas, backups/preflight/validate each step |
| Flyway V28 checksum negative | — | 0 | — | Expected validation exit1 on modified scratch copy; real migration/history unchanged |
| Pr41IsolatedLineageTest | 8 | 0 | 0 | Included in unit total; strict identity and ordered V28 |
| Chrome real integration | 12 groups | 0 | 0 | FRESH_PASS, 1440/768/390; 0 page exceptions |
| Chrome real outage/error state | 1 group | 0 | 0 | FRESH_PASS, actual backend stopped, no mocked API |
| APPROVED nonblank-reference DB CHECK | — | 0 | 0 | FRESH_PASS, SQL3819 and Admin400; no data repair |
| Exact Local BASELINE13 deployment/runtime on3311 | 1 | 0 | 0 | FRESH_PASS, dedicated exact-identity profile; full Hibernate validate |
| Historical live ingestion results | — | — | — | REUSED_EVIDENCE only, not acceptance evidence |
| Live RSS in this run | — | — | — | NOT_RUN, intentionally forbidden by release gate |

## Reproduction commands

Final run logs: `v28-full-final.log`, `v28-standard-final.log`, `v28/*final*.log`;
final SHA and per-command exit codes in `.scratch/evidence/v28/final-validation.json`.

Use JDK21; credentials and JWT secret are process-scoped. DB_URL must point only to
the approved MySQL3311 synthetic schema. Do not load the shared `.env`.

```powershell
./backend/mvnw.cmd -f backend/pom.xml test '-Dtest=*Test,NewsLocalLineageIT,NewsApiIT,NewsConcurrencyIT,NewsFencingIT,NewsSafetyGateIT,NewsReleaseLockIT,NewsLiveIngestionIT,NewsDatabaseConstraintsIT,NewsSourceRightsIT,NewsFeedFetcherIT,NewsBodyTimeoutIT,CoordinateProvenanceIT'
# Separate process: DB_URL=.../pr41_standard, PR38_STANDARD_V23_TEST=true, PR41_STANDARD_V23_TEST=true
./backend/mvnw.cmd -f backend/pom.xml test '-Dtest=StandardLineageCompatibilityIT,NewsStandardV23IT'
./backend/mvnw.cmd -f backend/pom.xml package -DskipTests
npm.cmd test --prefix frontend
npm.cmd run build --prefix frontend
npm.cmd test --prefix .scratch/pr37-integration/frontend
npm.cmd run build --prefix .scratch/pr37-integration/frontend
```

Real integration uses Chrome through Playwright, frontend14137 -> backend18141 ->
MySQL3311. `chrome-real-integration.json` lists scenarios; `chrome-error-state.json`
records real outage. No News API is mocked. Synthetic fixture accounts use actual
registration/login; tokens/passwords are never saved in test reports.

Initial failures are retained in scratch only: missing JWT test configuration,
fixture setup timestamps/automatic role trigger, schema-filter fixture construction,
old scheduler assertion, and MySQL CHECK error translation. They are superseded by
fresh successful runs; no failure is hidden by skipping a test.
