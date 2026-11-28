# WP-04 B6 — real runtime validation plan (FastAPI V1.3 → Spring Boot/Tomcat → React)

**Status:** PLAN ONLY. Nothing in this document has been executed. The B6 gate stays open until the
scripted harness below actually runs end to end.

## 1. Why this exists

B1–B5 were verified at three levels: the predictor itself (Python tests, 105-case matrix parity),
the Java passthrough (Jackson round-trip + loopback client), and the React surface (484 true-viewport
browser checks plus component tests). What has **not** been verified is one real request travelling
React → HTTP → Tomcat → FastAPI → back, with real serialisation at every hop. Mocked HTTP fixtures
must not be reported as that evidence.

## 2. Surfaces and their real routing

| Surface | Real route | Path |
|---|---|---|
| Standalone valuation | React → **existing `/api/ai` dev proxy** → FastAPI V1.3 | `ValuationPanel.jsx` → `createValuationClient().predict()` |
| Posting preview | React → **Spring Boot/Tomcat** `POST /api/valuation/preview` → FastAPI `/predict/v1_3_preview` | `PostValuationPanel.jsx` → `ValuationService.preview()` |
| Unified Advisor | React → **Spring Boot/Tomcat** `POST /api/advisor/consult` → `AdvisorValuationAdapter` → FastAPI `/predict` | `AdvisorEvidencePanel.jsx` |

Standalone must keep using the existing proxy route; introducing a new Spring controller for it
would be a behaviour change outside WP-04.

## 3. Harness

```
services (loopback only):
  FastAPI     127.0.0.1:8000  ai-services/.venv, pinned v1_3 artifacts
  Spring Boot 127.0.0.1:8080  backend/mvnw spring-boot:run (isolated profile)
  Vite dev    127.0.0.1:5173  frontend (proxies /api/ai → 8000, /api → 8080)
  MySQL       127.0.0.1:3311  TEMPORARY isolated instance (never 3306/3307/3311 group DB)
```

- Every port is loopback and every database is a throwaway instance created for the run.
- Inputs come from the synthetic fixture set already committed
  (`frontend/tests/wp04/fixtures/explanation-samples.json`) so no research or holdout data is touched.

## 4. Assertions per surface

1. HTTP status 200 and a positive `predicted_asking_price_vnd`.
2. `explanation.status == "AVAILABLE"`, `method`, `target`, `output_space` unchanged end to end.
3. `predicted_margin_log`, `base_value_log`, all `factors[].contribution_log_raw` and
   `other_contribution_log` are **byte-identical** to a direct FastAPI call for the same payload.
4. `grouped_contributions` and `feature_provenance` (22 keys) survive Spring's JSON round trip.
5. Spring `Preview.explanation` and `ValuationEvidence.explanation` are both non-null for the same
   input, with identical content.
6. Legacy path: a response without `explanation` still renders and shows the authoritative price.
7. Invalid explanation (mutated in a proxy shim) → panel shows the unavailable state, price unchanged.
8. FastAPI down → Spring returns its documented unavailable preview, posting still works.
9. Browser: panel rendered, 22 provenance rows, waterfall open, no clipping at 390/1440.
10. WP-02 preservation: `comparableEvidence`, `valuationComparableEvidence`, `featureCoverage` and
    `ComparableListingsCard` still render next to the explanation.
11. Authorization: anonymous SAFE request returns no research fields; a research session is
    exercised only with an approved staging account (never committed).

## 5. Prediction invariance

Capture `predicted_asking_price_vnd` from the direct FastAPI call **before** wiring the full stack,
then compare with each surface. Any difference fails the gate. The model artifact hashes are checked
before and after the run (4/4).

## 6. Out of scope for B6

- No model retraining, no V6 fallback, no migrations.
- No prediction-interval work (WP-05 owns `prediction_interval`; the explanation contract keeps the
  field absent so WP-05 can add it independently).
- No production deployment.

## 7. Definition of done

A single `node frontend/tests/wp04/browser/runtime.mjs` invocation starts nothing itself (services
are started by the operator), asserts items 1–11 above for all three surfaces, writes
`frontend/tests/wp04/browser/reports/wp04-runtime.json`, and exits non-zero on any failure.
Until that file exists and has run, `WP04_REAL_FASTAPI_TOMCAT_RUNTIME_PARITY_PENDING_B6` stays open.
