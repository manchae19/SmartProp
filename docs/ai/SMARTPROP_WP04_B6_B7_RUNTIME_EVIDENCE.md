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
