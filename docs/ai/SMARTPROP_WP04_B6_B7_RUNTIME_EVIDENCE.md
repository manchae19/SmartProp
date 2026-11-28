# WP-04 B6/B7 — runtime evidence report

Sanitised. No tokens, credentials, protected data or user records.

## 1. Environment

| | |
|---|---|
| Starting HEAD | `a7e02d1` |
| Main baseline | `1c67a27` |
| Runtime services started by this session | FastAPI `127.0.0.1:8000` (uvicorn `main:app`), Vite `127.0.0.1:5199` |
| Services **not** started | Spring Boot + isolated MySQL (see §5) |
| Model | `v1.3`, `model_ready: true`, four pinned artifacts unchanged |

## 2. Real HTTP validation (no mocks)

`frontend/tests/wp04/browser/runtime.mjs` → **149/149 checks passed**.

- Four property types (HOUSE, LAND, APARTMENT, VILLA) submitted as real `POST /predict`.
- Same payloads replayed through the Vite `/api/ai` proxy: identical prediction and byte-identical
  explanation object.
- Per case: positive integer price equal to the pinned fixture (prediction invariance), version
  `1.0`, method `XGBOOST_NATIVE_TREESHAP`, target `ASKING_PRICE_VND`, output space
  `LOG1P_PRICE_VND`, exactly 6 factors, 22 provenance keys, calibration policy `duan_by_band`,
  `adjusted_price_vnd == predicted price`, additivity and grouped totals within `1e-5`.
- Real rejections: `area_sqm = 0` → 4xx; district outside the vocabulary → 4xx.

## 3. Component browser validation

`frontend/tests/wp04/browser/run.mjs` → **484/484 checks passed** across 11 payload cases ×
viewports 320/390/768/1440 with real device metrics. Technical section opened before measuring;
geometry checked with ranges, computed styles and nonzero dimensions; keyboard focus verified via
real Tab navigation.

## 4. Mocked three-surface runner

`frontend/tests/wp04/browser/surfaces.mjs` → **4 passed, 3 skipped, 0 failed**.

Skipped (explicitly *not* reported as passing): standalone form interaction, Advisor explanation
interaction, posting preview interaction — each requires application state (options store, session,
draft) that mock-only fixtures cannot construct.

## 5. Blocked gates

**Spring Boot posting preview** and **Unified Advisor runtime** are blocked. Every committed Spring
profile binds to `127.0.0.1:3306` or `127.0.0.1:3307`, which are protected. Provisioning a throwaway
MySQL instance, applying migrations, seeding synthetic users/properties and driving two
authenticated routes was not completed in this session. These gates remain open and must not be
reported as passing.

## 6. Regression (fresh, this run)

| Suite | Result |
|---|---|
| Frontend `node --test` | 227 passed, 0 failed |
| Vite production build | PASS |
| WP-04 Python (contract + HTTP + matrix parity) | 51 passed |
| Benchmark assertions | 105 cases, 15 extras, self-tests PASS, digest `9eedb3c7c3668f61` (unchanged) |
| Artifact hashes | 4/4 unchanged |

Java, full FastAPI serial and RAG suites were run earlier in this branch session (285 / 1230 / 911)
and were not re-executed in this final pass; they are not claimed as fresh here.

## 7. Rollback

All WP-04 changes are additive: revert the commits on `research/wp04-explainable-ai`, or ignore the
`explanation` object — every legacy field and the authoritative prediction are untouched by design.
No migration, no model change, no data change.

## 8. Deployment restrictions

Not deployed. Production deployment needs separate deployment verification. WP-04 must not change
the V1.3 point prediction, must not enable V6 fallback and must not introduce telemetry.

---

## Final closure pass

### Strict price contract
`normalizeVnd` used `Number()` and accepted `>= 0`. Replaced by:

- `vndDigits(value)` — canonical positive-integer digits for a JSON number **or** a Spring decimal
  string; rejects 0, negatives, fractions, hex, scientific notation, empty strings, objects,
  `NaN`/`Infinity` and anything beyond the JavaScript safe-integer range (kept exact as digits
  instead of being rounded).
- `normalizeVnd(value)` — numeric form, only when exactly representable.
- `sameVnd(a, b)` — exact digit comparison.

The panel now receives the **original** price representation from `PostValuationPanel` and
`AdvisorEvidencePanel` (not a pre-normalised value), so a supplied-but-invalid price is detected.
Consistency is **exact integer equality** against `calibration.adjusted_price_vnd`; the previous
relative tolerance is gone. The approved `1e-5` SHAP reconstruction tolerance is unchanged.

### Corrected runtime harness
`runtime.mjs` now:

- fails closed unless `WP04_AI_BASE` and `WP04_PROXY_BASE` are explicit loopback origins;
- applies bounded timeouts to every request;
- asserts `status === 200` **and** a parsed body (not "body parsed");
- requires documented `4xx` for invalid input — a `5xx` no longer counts as a rejection;
- compares the exact 22 provenance **identities** and validates every provenance state;
- compares decoded JSON structurally and does not claim byte equality.

### Mocked three-surface browser
`surfaces.mjs` no longer builds a one-factor AVAILABLE payload (which violated the six-factor
contract). It mounts the real `AdvisorEvidencePanel` with the committed V1.3 fixtures and asserts:
six contribution rows, 22 provenance rows, calibration bridge, cumulative waterfall SVG, no legacy
SHAP duplication, both Comparable evidence sections, feature coverage, and the unavailable /
malformed / legacy states. Results: **30 passed, 0 failed, 3 NOT_RUN** — the three authenticated
route interactions are recorded as NOT_RUN, never as passes.

### Fresh counts (this pass)

| Suite | Result |
|---|---|
| WP-04 frontend tests (`node --test tests/wp04/*.test.js`) | 85 passed |
| Full frontend recursive (`npm test`) | **239 passed, 0 failed** |
| Component browser (11 cases × 4 viewports) | **484/484** |
| Mocked three-surface browser | 30 passed / 0 failed / 3 not run |
| Real runtime (FastAPI + Vite proxy, 4 property types) | **157/157** |
| Vite production build | PASS |
| Artifacts | 4/4 hashes unchanged |
| `backend/src`, `ai-services`, migrations | 0 changed |

### Remaining blocker
Spring Boot posting-preview and Advisor runtime gates are **BLOCKED**. Prerequisites exist
(`application-standard-migrations.yml`, portable `mysqld`, port 3407 free, no protected port used),
but provisioning a throwaway Standard V23 fixture, seeding synthetic publisher/buyer/ADMIN accounts
and driving two authenticated routes was not completed in this session. No MySQL instance, Tomcat
or Spring process was started, so nothing is left running and no protected database was touched.

---

## Runtime closure session — actual results

### Configuration precedence (correction)

`application.yml` sets `app.valuation: { enabled: false }` as a literal. That does **not** prevent
override: Spring Boot resolves `SPRING_APPLICATION_JSON` / system properties / command-line arguments
above YAML. The earlier claim that the flag "cannot be overridden" was wrong; the successful run used

```
SPRING_PROFILES_ACTIVE=standard-migrations
SPRING_DATASOURCE_URL=jdbc:mysql://127.0.0.1:3407/wp04_runtime_v23?connectionTimeZone=UTC
SPRING_DATASOURCE_USERNAME=wp04_v23   (fixture password from the secure fixture store)
SPRING_APPLICATION_JSON={"app":{"valuation":{"enabled":true,"base-url":"http://127.0.0.1:8000"},
  "advisor":{"valuation-enabled":true,"valuation-base-url":"http://127.0.0.1:8000",
  "allow-research-comparables":false}}}
mvnw -o spring-boot:run
```

Guard stayed intact: one explicit profile, runtime Flyway disabled, `ddl-auto=validate`, SQL init
`never`; Flyway validated the 23 migrations before Tomcat started on 8080.

### Fixture

`data-ok`, UUID `54afb557-eb00-11f1-886b-7085c2fe30d2`, port 3407, schema `wp04_runtime_v23`.
Eight synthetic HOUSE properties seeded (Cẩm Lệ / Hòa Thọ Đông, 78–92 m², 5.15–6.45 B VND, PUBLISHED,
SALE, VND/TOTAL, SRID 4326 points, unique `WP04-HOUSE-N` listing codes, idempotent upsert).
Three synthetic accounts (BROKER, BUYER, ADMIN) authenticate through the real `/auth/login`.

### Actual HTTP evidence

`POST /api/v1/properties/valuation-preview` (BROKER, UTF-8 JSON):

```
available=true  predictedAskingPriceVnd=5749775772
explanation.status=AVAILABLE  factors=6  provenance=22  policy=duan_by_band
direct FastAPI /predict            = 5749775772   (exact parity)
```

`POST /api/v1/advisor/consult` (payload: budget 7.0 B, LIVING, HOUSE, Cẩm Lệ, limit 3,
includeComparables/includeValuation true, research false):

```
mode=SAFE  recommended=3  eligibleCandidateCount=8
valuationEvidence: available=true modelVersion=v1.3 price=4767450210
                   explanation.status=AVAILABLE factors=6 provenance=22
                   policy=duan_by_band adjusted_price_vnd=4767450210  (exact parity)
comparableEvidence:            status=AVAILABLE candidates=3
valuationComparableEvidence:   status=AVAILABLE candidates=3
researchReference=false  source.kind=PROPERTY
```

The Advisor price differs from the posting-preview price because the effective model inputs differ
(different area/category context); each surface is internally exactly consistent.

### Encoding note (harness, not product)

PowerShell mangled Vietnamese district strings in request bodies, producing
`available=false` with "khu vực chưa được hỗ trợ" and HTTP 400s. Writing the JSON as UTF-8 (no BOM)
and posting with `curl.exe --data-binary @file` resolved it. Any future runtime harness must control
encoding explicitly.

### Code change

`explanationModel.js` now requires `vndDigits(calibration.adjusted_price_vnd) !== null` before an
AVAILABLE explanation is accepted, so zero, fractional, unsafe, negative, malformed or object
representations cannot make the consistency comparison vacuous. Canonical digit strings are accepted
and compared exactly; one VND apart is still a mismatch. WP-04 frontend tests: **88 pass**, build PASS.

### Still open

Three real browser surfaces (standalone, posting, Advisor) against these services, 320/390/768/1440
responsive checks, failure isolation through the UI, and the full cross-suite regression
(FastAPI serial, RAG, Java, WP-02 ×12 browser groups, Vite, prediction invariance) were **not** run
this session and are not claimed.

### WP06 handoff

- Contract: `explanation_version=1.0`, `status` in {AVAILABLE, PARTIAL, UNAVAILABLE, NOT_SUPPORTED},
  `method=XGBOOST_NATIVE_TREESHAP`, `target=ASKING_PRICE_VND`, `output_space=LOG1P_PRICE_VND`.
- Provenance states: OBSERVED, DERIVED, DEFAULTED, MISSING, MISSING_INVALID, NOT_APPLICABLE,
  UNKNOWN_CATEGORY, UNVERIFIED (22 feature keys).
- Reconstruction tolerance: 1e-5 relative to |predicted_margin_log|.
- Insertion point: `PredictorV1_3.predict()` returns the explanation next to the unchanged point
  prediction; explanation failures downgrade to UNAVAILABLE and never alter the price.
- Known limits: no calibrated confidence, no prediction interval (WP-05), synthetic-fixture runtime
  only. Reviewed commit: `893eeb9` plus the local runtime-fix commit.

---

## Browser runtime session — what actually happened

### Environment reused (verified, owned)

MySQL `data-ok` on 3407 (UUID `54afb557-eb00-11f1-886b-7085c2fe30d2`), FastAPI V1.3 on 8000,
Spring Boot `standard-migrations` on 8080 (Flyway validate 23, Hibernate validate), Vite on 5180.
A real BROKER JWT was obtained from `/api/v1/auth/login`.

### Real browser run: NOT COMPLETED

A Playwright runner (`frontend/tests/wp04/browser/runtime-surfaces.mjs`) was written and executed
against those services with **no response interception**. Result: **2 passed / 13 failed**.

The decisive symptom: after driving the visible form controls and clicking the primary CTAs
(`Ước tính giá rao` on `/valuation`, `Tìm gợi ý phù hợp` on `/advisor`), **no request to
`/api/ai/predict` or `/api/v1/advisor/consult` was emitted at all** — so the explanation panel
never appeared and every dependent assertion timed out. Injecting `localStorage.token/role` did not
make the app treat the session as authenticated (the shell still offered “Đăng nhập”), and
`/post/step-4` cannot render a preview without a persisted draft, so the posting workflow is not
reachable from a cold route.

Conclusion: the three real route workflows are **not** verified. This is a harness/фlow-state gap,
not evidence that the surfaces are broken — the HTTP level already returns real V1.3 predictions
with full explanations (preview `5749775772`, Advisor `4767450210`).

### Fresh regression that did run

| Suite | Result |
|---|---|
| WP-04 Python (contract + HTTP + matrix) | **51 passed**, exit 0 |
| Phase A deterministic benchmark | **105 cases, 15 extras, self-tests PASS**, digest `9eedb3c7c3668f61` unchanged |
| Full frontend recursive `npm test` | **242 passed, 0 failed**, exit 0 |
| Vite production build | PASS |

### Gate status

Passed with evidence: isolated V23 fixture, Hibernate validation, synthetic seed, effective
valuation configuration, real FastAPI standalone/preview/Advisor HTTP, exact price consistency,
prediction invariance, artifact integrity, migrations unchanged, cleanup, docs.

Not passed: `WP04_REAL_THREE_SURFACE_BROWSER_PASS`, `WP04_B5_*_RUNTIME_PASS` (browser level),
`WP04_RUNTIME_FAILURE_ISOLATION_PASS` through the UI, `WP04_REACTIVE_AUTHORIZATION_PRESERVED`
(browser-level revocation), `WP04_WP02_REGRESSION_PASS` (12 Chromium groups), full FastAPI serial,
full RAG, full Spring Boot regression — none were executed in this session.

### WP06 handoff — implemented statuses only

`explanation_v1_3.py` emits **AVAILABLE** and **UNAVAILABLE**. `PARTIAL` and `NOT_SUPPORTED` exist in
the shared contract and are handled by the frontend, but the current producer never emits them.
Version `1.0`; method `XGBOOST_NATIVE_TREESHAP`; target `ASKING_PRICE_VND`; output space
`LOG1P_PRICE_VND`; 22 feature identities; provenance states OBSERVED, DERIVED, DEFAULTED, MISSING,
MISSING_INVALID, NOT_APPLICABLE, UNKNOWN_CATEGORY, UNVERIFIED; reconstruction tolerance
`1e-5 * max(1, abs(predicted_margin_log))`. Explanation generation runs inside `PredictorV1_3.predict`
after the unchanged point prediction; a failure downgrades the explanation and never alters the price.
