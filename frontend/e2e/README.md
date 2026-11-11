# Chatbot E2E (Phase 9B.3)

`chatbot.e2e.mjs` exercises the real React chatbot against real RAG/Recommendation/GIS services. It is a plain Playwright script (no test runner dependency) so it can use the Playwright package already present in the workspace.

## Prerequisites

- React dev server: `http://127.0.0.1:5173`
- Spring Boot: `http://127.0.0.1:8080` with `APP_RECOMMENDATION_V11_ENABLED=true`
- RAG: `http://127.0.0.1:8001` (corpus/index valid; `run-chat-local.ps1`)
- For image assertions, `STORAGE_ROOT` must point to the storage containing the seeded property images.
- Playwright installed. Either it resolves normally, or set:
  `$env:PLAYWRIGHT_PATH="F:\SmartProp\frontend\vue.ui\node_modules\playwright"`
- For the private-mode test, provide a **staging** account (never commit credentials):
  `$env:SMARTPROP_CHAT_E2E_EMAIL=...`
  `$env:SMARTPROP_CHAT_E2E_PASSWORD=...`
  `$env:SMARTPROP_CHAT_E2E_BASE=http://127.0.0.1:5173` (optional)

## Run

```powershell
cd F:\SmartProp\.worktrees\integration-tinix\frontend
$env:PLAYWRIGHT_PATH="F:\SmartProp\frontend\vue.ui\node_modules\playwright"
$env:SMARTPROP_CHAT_E2E_EMAIL="<staging user>"
$env:SMARTPROP_CHAT_E2E_PASSWORD="<staging password>"
node e2e\chatbot.e2e.mjs
```

## What is live vs stubbed

- `LIVE` tests use the real React → `/api/chat` → RAG → Spring Boot → MySQL/staging flow. They are the only ones that support a live PASS claim.
- `STUBBED RAG-down` aborts `/api/chat` only to verify the explicit error UI; it is **not** evidence of a live integration PASS.
- No property, POI, image, or AI answer is hardcoded. If an image/POI is unavailable, the tests assert the explicit unavailable state instead of substituting data.

## Valuation E2E (Phase 9E)

`valuation.e2e.mjs` uses real FastAPI V6/V1.3 at `http://127.0.0.1:8000` and React at
`http://127.0.0.1:5173`. It performs no database writes and does not require login.

```powershell
cd F:\SmartProp\.worktrees\integration-tinix\frontend
$env:PLAYWRIGHT_PATH="F:\SmartProp\frontend\vue.ui\node_modules\playwright"
node e2e\valuation.e2e.mjs
```

It also checks the local valuation quick-address parser (district/legacy ward) without
creating coordinates, then asserts V6 price/SHAP, localized raw subtype labels, V1.3
price/band/SHAP, explicit missing features, and the V1.3 adapter's synthetic road/frontage
assumptions; then checks mobile overflow.

## Property Quick Address E2E (Phase 10A)

`post-location.e2e.mjs` uses real Geoapify-backed geocoding and the real posting map on
staging. It does not save a listing or write to MySQL.

```powershell
cd F:\SmartProp\.worktrees\quick-address\frontend
$env:PLAYWRIGHT_PATH="F:\SmartProp\frontend\vue.ui\node_modules\playwright"
$env:SMARTPROP_CHAT_E2E_EMAIL="<staging publisher>"
$env:SMARTPROP_CHAT_E2E_PASSWORD="<staging password>"
# optional edit-hydration fixture:
$env:SMARTPROP_POST_E2E_EDIT_ID="<owned property id>"
node e2e\post-location.e2e.mjs
```

It verifies consent defaults false, search only after explicit consent, candidate
rendering, manual pin confirmation, mobile layout, and (when an edit ID is supplied)
address/pin hydration without losing coordinates.

## Notes

- The private-mode test toggles the chat profile mode off/on and inspects request headers: off must have no `Authorization`, on must have Bearer.
- Chat is public by default; profile/personalization requires an authenticated staging user with consent enabled.
- Tests are sequential because the RAG service is single-runtime (keep-alive 0).
