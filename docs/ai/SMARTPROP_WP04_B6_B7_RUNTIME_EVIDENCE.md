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
