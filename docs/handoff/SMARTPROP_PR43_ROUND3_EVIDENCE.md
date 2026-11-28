# SMARTPROP — PR #43 SECOND-REVIEW REMEDIATION EVIDENCE (Round 3)

- Branch: `feature/advisor-land-runtime-20261126`
- Candidate: `51a91f6301652b1af0aa39de31b2cb9c80d554c0`
- Approved baseline merged: `afa56fc2ed09287e1ca2a73677b59dcfc7f9973c` (PR #41 News Backend), merge commit `a377c673`
- Previous candidate: `5aabe81c1f955d71451ce86a26a2b97f10ca77e6`
- Host: Windows 11, MySQL 8.0.46, Caddy v2.11.9, JDK 21, Python 3.14

## 1. P1-01 — strict over-budget consent

Reproduction before the fix (previous candidate):

```
GRANT     | Tìm đất Hòa Xuân dưới 3 tỷ, tôi chưa từng chấp nhận vượt ngân sách
NONE      | Tôi đã từng đồng ý, nhưng bây giờ không
```

After the fix (`ai-services/app/rag/buyer_search.py`):

```
DENY      | Tìm đất Hòa Xuân dưới 3 tỷ, tôi chưa từng chấp nhận vượt ngân sách
DENY      | Tôi không muốn vượt ngân sách
DENY      | Tôi chưa đồng ý vượt ngân sách
DENY      | Tôi chưa bao giờ đồng ý vượt ngân sách
DENY      | Tôi đã từng đồng ý, nhưng bây giờ không
AMBIGUOUS | Nếu tôi đồng ý vượt ngân sách thì sao?
DENY      | Tôi có nên chấp nhận vượt ngân sách không?
AMBIGUOUS | Người khác đồng ý vượt ngân sách, còn tôi thì không
GRANT     | Tôi đồng ý xem nhóm tham khảo vượt ngân sách
DENY      | Rút lại đồng ý vượt ngân sách
```

Design: clause split → negation/withdrawal/contradiction evaluated first and always win;
questions, quotes, hypothetical/conditional wording, third-party statements, past-tense
recollection and hedges never grant; consent bound to the criteria snapshot; pending
confirmation is scope-checked; checkpoint restore always drops consent.

Orchestrator/result regression (`ai-services/tests/test_pr43_land_and_rag.py`,
`test_p1_01_review_round2_strict_consent_matrix_and_state_lifecycle`) asserts every reviewed
phrase returns no listing above the 3B ceiling and `overBudgetVnd == 0`, and that explicit
consent can surface the <=+15% reference band while the saved budget stays 3B.

## 2. P1-02 — demo persistence isolation

- `ai-services/app/rag/checkpoints.py`: `durable_chat(..., allow_demo=True)` no longer reads or
  writes the account checkpoint store; demo turns stay in the process-local demo session store.
- `ai-services/app/rag/orchestrator.py`: demo scope is server-derived (`PUBLIC_DEMO` /
  `ACCOUNT_DEMO:<subject>`); resumed checkpoints drop over-budget consent.
- `backend/.../AdvisorChatController.java`: `AdvisorChatStore.recent/owned` apply a read-only
  `NOT EXISTS` filter over `advisor_chat_turns` (`JSON_SEARCH ... LAND_DATA/LAND_SEARCH/LAND_OVERVIEW`)
  so conversations persisted before the boundary existed cannot appear in account history or be
  resumed. No production row is modified or deleted; owners can still delete their own entry.

Python regression (`test_p1_02_review_round2_demo_persistence_and_scope_isolation`) proves: zero
checkpoint HTTP calls for demo turns, demo id not resumable by a normal account turn, PUBLIC vs
PUBLIC_DEMO and cross-account namespaces separated, and payload scope spoofing rejected.

Real MySQL acceptance (`backend/.../AdvisorChatPersistenceIT`, 6/6): checkpoint persistence across
fresh connections, revision CAS conflict, cross-account 404, legacy demo conversation hidden from
recent/history/checkpoint, failed turn write rolls back the conversation revision, concurrent
commits accept exactly one, and a real `POST /api/v1/advisor/consult` returns 200 SAFE.

## 3. Caddy real runtime (v2.11.9)

Binary: official `caddy_2.11.9_windows_amd64.zip` from the GitHub release,
SHA-256 `2622E239C79DF700B0EB92CBD950D1EDEE365E155A7859F358F0E55F002DF591`.

```
caddy validate --config ops/Caddyfile   -> Valid configuration
caddy run --config ops/Caddyfile        -> serving on :18088 (SMARTPROP_DOMAIN=:18088)
```

Real HTTP matrix through Caddy with recording upstreams on 8080/8082/8001:

```
403  /api/land
403  /api/land/health
403  /api/land/records/DN-QH-0001
403  /api/%6cand/records/DN-QH-0001
403  /api/land;jsessionid=123/health
403  //api//land/records/DN-QH-0001
403  /api/land/../properties/abc
403  /api/%2e%2e/land/records/DN-QH-0001
403  /API/LAND/records/DN-QH-0001
403  /api/land/records/DN-QH-0001 + X-Forwarded-For/Forwarded/X-Real-IP + demo key
200  POST /api/chat (public relay, demo key stripped)
200  GET  /api/v1/properties
land requests reaching upstream: 0
requests carrying X-SmartProp-Demo-Key at upstream: 0
```

`README.md` Caddy sample was synced with `ops/Caddyfile` (land loopback deny, chat health to 8001,
chat relay to 8082, demo-key/Forwarded stripping).

## 4. MySQL isolated fixture (real persistence)

Isolated instance: port **3310**, datadir `.local-run/pr43-mysql/data`, own `my.ini`,
`log_bin_trust_function_creators=1`; protected 3306/3307 and the mentor demo were never touched.

Schemas provisioned from the reviewed migrations only:

| Schema | History | Purpose |
|---|---|---|
| `pr43_fixture_v28` | 13 BASELINE + 14,17,18,19,20,21,22,23,24,25,26,27,28 | full hybrid V28, news enabled |
| `pr41_advisor_v21` | 13 + 14,17..21 | read-only lineage stop |
| `pr41_advisor_v26` | 13 + 14,17..26 | pre-news stop |
| `pr41_advisor_v27` | 13 + 14,17..27 | news tables, no V28 constraint |

Procedure (standard V1..V23 applied, conflicting objects dropped, Flyway `baseline 13` with
description BASELINE13, then `-P hybrid-local-existing-v13 flyway:migrate` to each target). Result
`flyway_schema_history` exactly matches `MigrationLineageConfiguration` expectations, including
crawler14 checksum `-1382804267`; V28 constraint `ck_news_sources_approved_reference` is ENFORCED.

Live acceptance on these fixtures:

```
NewsLocalLineageIT                   1/1 PASS  (full Hibernate validation + /api/v1/news 200 + admin 401)
AdvisorChatPersistenceIT             6/6 PASS  (see section 2)
FIXTURE_PRE_CONNECTION_PASS          jdbc=127.0.0.1:3310/pr43_fixture_v28 nativeSimulation=hybrid-local-existing-v13
```

## 5. Fresh integrated regression on `51a91f63`

| Suite | Result |
|---|---|
| Full Python `pytest -rs -q tests` | **1246 passed, 19 skipped, 0 failed** (105 subtests) |
| PR43 land/RAG file | **15 passed** (was 13) |
| Spring Boot `mvnw -o test` | **440 passed, 0 failed/errors/skipped** |
| Frontend unit/contract (32 files) | **352 passed, 0 failed** |
| Vite production build | **PASS**, `built in 14.52 s` |
| PR43 browser E2E | **6/6 PASS** (public `/api/land` 403, land governance, cancellation, PR47, PR48 route) |
| Security scan | **PASS** (`0` findings; tracked executables `0`) |
| Graphify AST | **13200 nodes / 36132 edges / 557 communities**, built from `a377c673` |
| V1.3 artifacts | **8/8** hash+size checks against `artifacts/v1_3.manifest.json` |
| Migration/artifact integrity | no `V*.sql`, `ai-services/artifacts/**` or `db/migration` delta vs baseline |

Skipped (19, all expected): 13× `test_api_v6` (V6 not public), 1× `test_planning_data` (offline
dataset not distributed), 5× `test_vision_detector` (`yolov8n.pt` absent).

## 6. Not run / blocked (truthful)

1. `AdvisorReadOnlyRuntimeIT` (13 cases) — **NOT_RUN**: the class asserts a provisioner contract that
   is not present in the repository (fixtures on port **3311**, a `pr41_local` completed-V28 schema,
   a `pr41_advisor_gap21` tampered-history schema, and `SMARTPROP_ADVISOR_NEGATIVE_LOCATIONS` for the
   checksum-mismatch case; `@AfterAll` asserts every physical JDBC destination starts with
   `jdbc:mysql://127.0.0.1:3311/`). Building those negative fixtures would require inventing
   provisioning artifacts that do not exist in the reviewed tree.
2. `FastAPI → Spring → MySQL` cross-process run — **NOT_RUN**: a standalone backend cannot bind to
   the hybrid V28 fixture by design (`NewsSchemaCapabilities` requires the reviewed migration
   profile/test-only runtime), so the HTTP boundary is covered by the real-MySQL MockMvc advisor
   call plus the Python orchestrator/checkpoint suites instead of two live processes.
3. Live mentor stack / `127.0.0.1:3306` / `127.0.0.1:3307` — **NOT_TOUCHED**.

## 7. Status

- `PR43_P1_01_STRICT_CONSENT_VERIFIED` — PASS (parser, orchestrator, result-level, no >3B listing without consent)
- `PR43_P1_02_DEMO_ISOLATION_VERIFIED` — PASS (Python scopes + Java persistence boundary + real MySQL)
- `PR43_PR41_BASELINE_INTEGRATED` — PASS (`afa56fc2` ancestor, 440 Java + news schema checks green)
- `PR43_CADDY_REAL_RUNTIME_VERIFIED` — PASS (v2.11.9 validate + HTTP matrix + 0 upstream land hits)
- `PR43_MYSQL_LIVEIT_VERIFIED` — **PARTIAL** (real V28/V21/V26/V27 fixtures, 2 suites green; `AdvisorReadOnlyRuntimeIT` and cross-process FastAPI→Spring→MySQL NOT_RUN)
- `PR43_FRESH_INTEGRATED_REGRESSION_COMPLETE` — PASS for the suites listed in section 5

Conclusion: **NOT_READY_TO_MERGE** while the two NOT_RUN items remain (per the review rule that a
mandatory runtime gate may not be replaced by static or mocked evidence).
