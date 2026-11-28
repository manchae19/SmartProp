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

---

## Current-main integration and repaired browser harness

### Main integrated

`origin/main` = `d6be176f6c7fa27a1f33836e627965104f6a8d27` (PR49 merged) was merged into this branch
with a normal merge commit (`48c872a`, then this branch's own commits). No rebase, no force-push.
PR49's shared HTTP client and auth modules are present after the merge; WP-04's explanation
components, `vndDigits` validation and benchmark are unchanged by it.

### Harness defects fixed (from review §3)

- **Authentication**: the app removes legacy `localStorage` token/role, so credentials are no longer
  injected. The runner now drives `/login?next=%2Fpost` with `#email-input` / `#password-input`, a
  real submit, a real `POST /api/v1/auth/login` assertion and an in-UI session confirmation. Fixture
  email/password come from `WP04_FIXTURE_EMAIL` / `WP04_FIXTURE_PASSWORD`; `WP04_APP` and `WP04_API`
  must match `http://127.0.0.1:<port>`. No JWT or password is logged.
- **Advisor route**: `/advisor/analysis` with the heading “Tư vấn bất động sản đa bằng chứng” and the
  real `.advisor-page` form; `/advisor` (legacy) is not used.
- **Valuation inputs**: real category/location options and an area inside 20–1000 m².
- **No swallowed failures**: required fills/selects are no longer wrapped in catch-and-ignore, and
  requests, responses and failures are recorded with event-driven waits instead of fixed sleeps.

### Result: 98/99 checks passed, 1 workflow unreached

| Surface | Result |
|---|---|
| Standalone `/valuation` at 320/390/768/1440 + 1280 | **PASS** — real `POST /api/ai/predict` 200, `model_version=v1.3`, positive integer price, explanation panel AVAILABLE, six factor rows, 22 provenance rows, calibration bridge, no overflow, no page error |
| Unified Advisor `/advisor/analysis` | **PASS** — real `POST /api/v1/advisor/consult` 200, SAFE, recommendations present, valuation explanation AVAILABLE, comparable evidence shown, payload contains no `researchReference:true` / `includeResearch:true` |
| Posting preview `/post` | **NOT REACHED** — after the login the SPA navigation into the posting workflow could not be located (`click` timeout); a full page load to `/post` drops the in-memory token and redirects to `/login`, and refresh restoration is disabled in this fixture (`REFRESH_ENABLED=false`) |

So `WP04_REAL_THREE_SURFACE_BROWSER_PASS` is **not** satisfied: two of three surfaces pass with real
network evidence, the posting workflow does not.

### Predictor-facing facts, unchanged

Producer emits **AVAILABLE** / **UNAVAILABLE** only; `explanation_version=1.0`;
`XGBOOST_NATIVE_TREESHAP`; `ASKING_PRICE_VND`; `LOG1P_PRICE_VND`; 22 feature identities; provenance
states OBSERVED, DERIVED, DEFAULTED, MISSING, MISSING_INVALID, NOT_APPLICABLE, UNKNOWN_CATEGORY,
UNVERIFIED; reconstruction tolerance `1e-5 * max(1, abs(predicted_margin_log))`.

### Posting and Advisor form controls — latest attempt

Navigation now matches the real contract: after a UI login with `?next=%2Fpost`, `LoginView` performs
the SPA `router.replace` and the runner **waits for `/post`** instead of searching for a link (no
localStorage injection, no reload). That part works.

The remaining failure is form-driving, not routing:

- `/post` exposes `#post-transactionType`, `#post-propertyType`, `#post-title`, `#post-area`,
  `#post-price` and buttons “Đăng bán”, “Cho thuê”, “Tiếp tục →”. Selecting
  `#post-transactionType` as an index raises `Element is not a <select> element`, so that control is
  rendered as something other than a native select in this build.
- `/advisor/analysis` renders an `.advisor-page` form whose fields carry **no name or id**
  (a text input, three selects, two text inputs, one number input, one select and three checkboxes)
  and a “Nhận tư vấn AI” submit. Position-based driving failed (`fill` timeout) because the first
  text input is not the budget field.

Those two workflows therefore remain **unverified**. Standalone valuation at 320/390/768/1440/1280
still passes end to end, and the earlier real HTTP checks for preview and Advisor remain valid.

---

## Three real browser workflows — PASS (328/328)

Selectors confirmed by source review (transaction group is a `role="group"` of buttons, the budget
input is identified by `aria-describedby="budget-hint"`, districts by `list="advisor-districts"`)
plus dismissal of the first-run notice that was intercepting clicks.

| Surface | Route | Result |
|---|---|---|
| Standalone valuation | `/valuation` | real `POST /api/ai/predict` 200, `model_version=v1.3`, positive integer price, explanation AVAILABLE |
| Posting preview | `/post` via `?next=%2Fpost` login | real `POST /api/v1/properties/valuation-preview` 200, `available=true`, V1.3 price, AVAILABLE explanation, adjusted price equal |
| Unified Advisor | `/advisor/analysis` | real `POST /api/v1/advisor/consult` 200, SAFE, recommendations, both Comparable evidence sections with `featureCoverage`, `includeResearch=false` |

All three ran at **1280, 320, 390, 768 and 1440 px**: **328 checks, 328 passed, 0 failed**. Each
viewport asserted the authoritative price, six factor rows, 22 provenance identities, grouped
contributions, calibration bridge, waterfall SVG, no horizontal overflow, no page error and no
failed API request. Screenshots: `docs/ai/browser/wp04/real-*.png`.

`/background.mp4` 404 was observed and correctly excluded: static media is not part of the workflow
contract, only `/api/` failures count.

## Fresh regression in this run

| Suite | Result |
|---|---|
| WP-04 component browser (`run.mjs`) | **484/484** |
| Mocked route surfaces (`surfaces.mjs`) | **30 passed, 0 failed, 3 not run** |
| Full frontend recursive | **335 passed, 0 failed** |
| WP-04 Python (contract + HTTP + matrix) | **51 passed** |
| Phase A benchmark | **105 cases, 15 extras**, digest `9eedb3c7c3668f61` unchanged |
| Vite build | PASS |

Not run in this session, therefore not claimed: WP-02's 12 Chromium groups, full FastAPI serial,
full RAG, full Spring Boot, isolated MySQL integration tests, UI failure isolation and browser-level
reactive authorization. `AdvisorControllerLiveIT` remains excluded (legacy V6/TiniX assertions).

---

## Final acceptance regression

### Display finding closed

`priceBlock()` in `ValuationExplanationPanel.js` only accepted JavaScript numbers, so an exact
integer arriving as a string rendered `—` while the assertion still passed. It now resolves the point
price through `vndDigits` (safe integers and canonical digit strings, plus a zero-fraction decimal
string such as `5476531536.00`), formats short values through the existing `formatBillion` and long
values through exact BigInt arithmetic so every digit survives, and renders `—` only when no valid
VND value exists.

Assertions moved with it: the browser check now requires real digits and rejects a placeholder dash,
and six new tests assert the **rendered price element** for a number, a Spring decimal string, a long
canonical string, invalid inputs (0, negative, fractional, `NaN`, text, objects, booleans), a one-VND
mismatch (price still visible, `data-explanation-status="INCONSISTENT"`) and an UNAVAILABLE
explanation with a valid price.

Five obsolete `V6` labels in `UnifiedAdvisorView.jsx` now read `V1.3`; no valuation behaviour changed.

### Results in this session

| Suite | Result |
|---|---|
| WP-04 frontend tests (`tests/wp04/*.test.js`) | **94 passed, 0 failed** |
| Full frontend recursive | **341 passed, 0 failed** |
| Real three-surface browser (1280/320/390/768/1440) | **328/328 passed** |
| Component browser (`run.mjs`) | **484/484 passed** |
| Mocked route surfaces (`surfaces.mjs`) | **30 passed, 0 failed, 3 not run** |
| Spring Boot (`mvnw -o test`) | **285 tests, 0 failures, 0 errors**, BUILD SUCCESS |
| FastAPI serial (full `tests/`) | **1230 passed, 20 skipped, 105 subtests** |
| WP-02 Chromium | **12 groups PASS** |
| WP-04 Python (contract + HTTP + matrix) | **51 passed** |
| Phase A benchmark | **105 + 15 extras**, digest `9eedb3c7c3668f61` unchanged |
| Vite build | PASS |
| V1.3 artifacts | 4/4 unchanged · migrations 0 changes |

### Not run (explicit)

Browser-level failure isolation (missing/UNAVAILABLE/malformed explanation, one-VND mismatch,
reconstruction mismatch, stale response, account lock, account replacement/authTransition,
research revocation, live FastAPI outage through the UI), browser-level reactive authorization, and
the isolated MySQL integration profile. `AdvisorControllerLiveIT` stays excluded: it asserts the
legacy V6 contract and enables TiniX, so it is not a V1.3 acceptance test.

---

## One authoritative VND contract

`vndDigits` now accepts a canonical integer **and** the same integer written with a zero fraction
(`5476531536.00`), normalising both to the same digits. Everything else stays rejected: nonzero
fractions (`5476531536.01`, `.5`), scientific notation, hexadecimal, signs and malformed text, and
unsafe JavaScript numbers (`!Number.isSafeInteger`). `ValuationExplanationPanel` no longer carries its
own normaliser — it uses the same function, so display and validation cannot drift again.

A supplied point price that cannot be normalised is now reported as **not consistent** instead of
silently consistent, because it cannot be verified against the adjusted price.

Tests (98 total in `tests/wp04/*.test.js`): canonical integer → AVAILABLE; zero-fraction decimal →
AVAILABLE with `priceConsistent: true`; one-VND mismatch → INCONSISTENT; invalid adjusted price →
INVALID; UNAVAILABLE explanation with a valid price still renders it; a 19-digit price above
`Number.MAX_SAFE_INTEGER` renders its exact BigInt value (`1234567890,12 tỷ`), not merely digits.

## Fresh regression

| Suite | Result |
|---|---|
| WP-04 frontend | **98 passed, 0 failed** |
| Full frontend recursive | **345 passed, 0 failed** |
| Vite build | PASS |

Reused (paths unchanged by this change, logs and exit codes on record): real three-surface browser
328/328, component browser 484/484, mocked surfaces 30/0/3, Spring 285 with no failures, FastAPI 1230
passed with 20 skipped, WP-02 12 groups, benchmark digest `9eedb3c7c3668f61`, four artifact hashes.

## Still open

Browser-level failure isolation (missing/unavailable/malformed explanation, one-VND mismatch,
reconstruction mismatch, stale response, live FastAPI outage) and browser-level reactive
authorization (account lock, account replacement, `authTransition`, research revocation, stale
restricted responses, SAFE fallback) have not been executed as browser scenarios; the equivalent
logic is covered at component level (484 checks) and in unit tests, but that is not the same gate.
The three mocked route scenarios in `surfaces.mjs` remain NOT_RUN, and the isolated MySQL integration
profile was not executed. `AdvisorControllerLiveIT` stays excluded: legacy V6 assertions and TiniX
enabled. The 20 skipped FastAPI tests are skips in the existing suite (model-artifact or
service-dependent cases), unchanged from the accepted run.

---

## Execution-only closure pass

### Exact secondary VND amount

The secondary amount now formats canonical digits with `Intl.NumberFormat("vi-VN")` on a `BigInt`,
so every digit survives: `5476531536`, `5476531536.00` and `1234567890123456789` render
`5.476.531.536 ₫` and `1.234.567.890.123.456.789 ₫` respectively. Three tests assert the exact
rendered text, and the span carries `data-testid="explanation-price-vnd"` so it can be asserted.

WP-04 frontend: **101 passed, 0 failed**.

### Failure isolation — executed, not passed

`frontend/tests/wp04/browser/failure-isolation.mjs` was written and run against the real stack.
Fixtures are mutations of a live `/predict` response (never hand-written schemas), so the payload
shape is genuine.

Result: **24/35 checks passed**. The baseline predict and the authorization checks pass; every
failure case reports an empty price and a `null` panel status, which means the standalone page does
not expose the panel or `[data-testid="explanation-price"]` when the response is a failure fixture.
The assertion is therefore reading the wrong element for this route, not proving the UI is wrong —
the same states are covered at component level (484 checks, including `unavailable`, `malformed`,
`legacy` and `missing`).

`WP04_RUNTIME_FAILURE_ISOLATION_PASS` is **not** claimed. Next lead: assert the page-level
`[data-testid="estimated-price"]` for the price and treat a missing panel as the expected state for
"no explanation".

### Reactive authorization — partially executed

Against the disposable fixture only, with restore afterwards:

- login through the UI succeeds;
- `UPDATE users SET status='LOCKED'` makes `/api/v1/auth/login` refuse the account;
- after a reload, `/api/v1/users/me` returns 401, so restricted data is not served while locked;
- restoring `status='ACTIVE'` lets the account log in again.

Not covered: `authTransition` UI states, research revocation, stale restricted responses and SAFE
fallback. `WP04_REACTIVE_AUTHORIZATION_PRESERVED` is **not** claimed.

### Fresh after the component change

| Suite | Result |
|---|---|
| Component browser | **484/484** |
| Real three surfaces (1280/320/390/768/1440) | **328/328** |
| Mocked surfaces | **30 passed, 0 failed, 3 not run** |
| Vite build | PASS |

### Remaining evidence gaps

- The three `NOT_RUN` entries in `surfaces.mjs` are still placeholders; they were left untouched
  rather than flipped to PASS.
- Isolated MySQL integration profile: not executed.
- FastAPI: 20 tests are skipped by the suite itself (model-artifact/service-dependent cases); the
  count is unchanged and no skip was introduced here.
- `AdvisorControllerLiveIT` stays excluded (legacy V6 assertions, TiniX enabled).
