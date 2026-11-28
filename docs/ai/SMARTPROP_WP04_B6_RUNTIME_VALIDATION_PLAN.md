# WP-04 B6 — real runtime validation plan (routes verified from source)

**Status:** partially executed. Real FastAPI standalone path **PASSED** (149/149 checks).
Spring Boot posting and Advisor paths are **BLOCKED** in this session — see §7.

## 1. Verified routing (read from current source, not from old docs)

| Surface | Frontend call | Backend | Verified at |
|---|---|---|---|
| Standalone | `client.predict()` → `/api/ai/predict` (Vite proxy) | FastAPI `POST /predict` | `frontend/src/features/prediction/valuation.js`, runtime test |
| Posting preview | `POST /api/v1/properties/valuation-preview` | Spring `ValuationController` → `ValuationService.preview` → `ValuationClient` → FastAPI `/predict/v1_3_preview` or `/predict` | `ValuationController.java:L20`, `ValuationService.java` |
| Unified Advisor | `POST /api/v1/advisor/consult` | Spring `AdvisorController` → `AdvisorValuationAdapter` → FastAPI `/predict` | `AdvisorController.java:L64`, `AdvisorValuationAdapter.java` |

No new production route is introduced by WP-04.

## 2. Isolated services

```
FastAPI      127.0.0.1:8000   ai-services/.venv, uvicorn main:app, pinned v1_3 artifacts
Vite dev     127.0.0.1:5173   proxies /api/ai → 8000, /api → 8080
Spring Boot  127.0.0.1:8080   backend/mvnw spring-boot:run
MySQL        <free loopback port chosen at run time>
```

Database rules:
- A throwaway data directory created for this run only.
- A synthetic database and a restricted synthetic user.
- Existing migrations applied **only** to that instance; only synthetic fixtures seeded.
- **Never** 3306, 3307, 3311 or 3312. The existing Spring profiles point at 3306/3307, so
  `application.yml` must be overridden with `SPRING_DATASOURCE_URL` before startup.
- Fail closed: if the effective JDBC URL references anything other than the throwaway instance,
  the run aborts.

## 3. Pre-start checks (fail closed)

1. `echo $SPRING_DATASOURCE_URL` shows the throwaway port, database and user.
2. `SPRING_PROFILES_ACTIVE` is the isolated profile, not a shared one.
3. `app.valuation.base-url` is `http://127.0.0.1:8000`.
4. The artifacts directory contains the four pinned files and their hashes match.
5. No process from another agent is bound to the chosen ports.

## 4. Assertions per surface

1. HTTP 200 and a positive authoritative integer `predictedAskingPriceVnd`.
2. Explanation `status/method/target/output_space` unchanged across the hop.
3. `predicted_margin_log`, `base_value_log`, every `contribution_log_raw` and
   `other_contribution_log` equal the direct FastAPI values for the same effective request.
4. `grouped_contributions` and all 22 `feature_provenance` keys survive Spring serialization.
5. Spring `Preview.explanation` / `ValuationEvidence.explanation` are non-null and identical.
6. Legacy response without explanation still renders the authoritative price.
7. Injected malformed explanation → panel shows the unavailable/inconsistent state, price unchanged.
8. FastAPI down → documented unavailable preview; posting still works.
9. Browser: panel, 22 provenance rows, waterfall, calibration; no clipping at 320/390/768/1440.
10. WP-02: `comparableEvidence`, `valuationComparableEvidence`, `featureCoverage`,
    `ComparableListingsCard` still render beside the explanation.
11. Authorization: anonymous SAFE returns no research fields; denied research paths stay denied.

## 5. Failure isolation matrix

| Case | How to produce | Expected |
|---|---|---|
| A AVAILABLE | real FastAPI | full panel |
| B legacy absent | strip `explanation` in a response shim | price + absent state |
| C UNAVAILABLE | force SHAP failure in a shim | price + unavailable state |
| D malformed | corrupt factors in a shim | price, no attribution |
| E price mismatch | shift `adjusted_price_vnd` | price + inconsistent state |
| F bad reconstruction | shift `other_contribution_log` | price, no waterfall |
| G service down | stop FastAPI | documented unavailable preview |
| H unauthorized | omit token | 401/403, no data |
| I input change mid-flight | type then submit twice | only the latest result renders |

## 6. Browser runtime harness

`frontend/tests/wp04/browser/runtime.mjs` — environment-driven (`WP04_AI_BASE`, `WP04_PROXY_BASE`),
readiness-polled, writes `frontend/tests/wp04/browser/reports/wp04-runtime.json`.

## 7. What actually ran, and what is blocked

Executed: real FastAPI up, four property types through the direct service and through the Vite
`/api/ai` proxy, contract + additivity + price invariance checks, now with strict status codes,
documented 4xx rejections and exact provenance identities. **157/157 passed.**

Blocked: Spring Boot posting preview and Advisor. Reason: every committed Spring profile binds to
`127.0.0.1:3306` or `127.0.0.1:3307` (protected group databases). Provisioning a throwaway MySQL
instance, applying migrations, seeding synthetic users and property fixtures, and then driving two
authenticated routes was not completed in this session. Those two gates stay open; they must not be
reported as passing until the isolated instance is actually started.
