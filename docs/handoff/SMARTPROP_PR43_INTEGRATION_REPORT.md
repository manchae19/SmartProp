# SMARTPROP — PR #43 RECOVERY, CURRENT MAIN INTEGRATION & INDEPENDENT REVIEW CLOSURE REPORT

- **Repository**: `https://github.com/manchae19/SmartProp`
- **Pull Request**: `https://github.com/manchae19/SmartProp/pull/43` (kept **Draft**)
- **Branch**: `feature/advisor-land-runtime-20261126`
- **Isolated Worktree**: `F:\SmartProp\.worktrees\pr43-advisor-land-integration`
- **Original PR #43 HEAD**: `f59edf223c98249ee6104c367c34537bd851aea5` (merge-base `bab3d7b5f71287af2de74f26afebb03db72b9bab`)
- **Previously Reviewed HEAD**: `0d95d2c848b27f8166bdb9f4ea886b20aa738568`
- **Integrated Approved `main` Baseline**: `0e9053f0c4085351a7d429f81995f6895ad80e33` (includes PR #48 Google Account Linking)
- **Merge Commit (`--no-ff`)**: `6f4058314002d0600c2b187e52c4902901d38d7d`

---

## 1. Executive Summary

PR #43 (`feature/advisor-land-runtime-20261126`) has been integrated forward onto the new approved `main` baseline `0e9053f0c4085351a7d429f81995f6895ad80e33` (including **PR #48 Google Account Linking**) via a normal `--no-ff` merge without rebase, force-push, migration edits, model artifact modifications, or protected database access, and **all 3 P1 findings and 1 P2 finding from the independent review (`0d95d2c848b27f8166bdb9f4ea886b20aa738568`) have been closed with permanent automated and browser regression coverage**:

1. **Main Integration (`0e9053f0c4085351a7d429f81995f6895ad80e33`) & PR #48 Preservation**:
   - Preserved PR #48 Google Account Linking (`GoogleLinkController`, `GoogleLinkService`, `GoogleLinkFlowStore`, `AccountView.jsx`, `/auth/google/link/complete` -> `GoogleLinkCompleteView.jsx`, `SecurityConfig.java`), PR #49 shared `httpClient.js` session generations, and all PR #38 / #44 / #45 / #46 / #47 contracts alongside `/land/:id` (`LandDetailView.jsx`).
2. **Closed P1 — Buyer and Land Cancellation & State Retirement**:
   - Added `_retire_buyer_and_land(state, *, clear_budget=False)` in `ai-services/app/rag/orchestrator.py` and wired it into `PURCHASE_DECLINED`, `_rental_reply`, `RENTAL -> SALE`, and cross-domain transitions (`AREA_AMENITIES`, `PROPERTY_SEARCH`, `REFINE_SEARCH`).
   - `PURCHASE_DECLINED` explicitly retires `buyerSearch` (`active=False`, `pending=None`, `pagingActive=False`, `visible=[]`, `order=None`, `offset=0`, `seen=[]`, `allowOverBudget=False`), `land` (`lastDomain=None`, `selected=None`, `seen=[]`, `visibleIds=[]`, `projectRows=[]`), and `listOwner`, and sets `purchaseDeclined=True` until an explicit fresh purchase search verb arrives.
   - `_listing_continuation` rejects stale `"Xem kết quả khác"`, `"Tìm lại theo bộ lọc"`, `"Xem thêm"`, `"Tiếp"`, `"Còn nữa"`, `"Còn không"`, `"Còn lô nào khác không"`, and stale bare type/location/budget quick replies with `NO_PENDING_LISTING_STEP` (`0` property cards, `0` land cards, `0` search-tool calls) while preserving PR #45 `RENTAL_BUDGET_NOT_SUPPORTED` when `purpose == "RENTAL"`.
   - Switching from a Hòa Xuân land search to a non-land house/apartment query (`nhà`, `căn hộ`, `chung cư`, `biệt thự`, `nhà phố`, `phòng trọ`, `mặt bằng`) cleanly retires `buyerSearch`/`land` and routes to `HybridRecommendationService` (`POST /api/v1/recommendations`).
3. **Closed P1 — Hard Budget Enforcement**:
   - Removed the automatic `+15%` budget expansion (`ceiling * 115 // 100`) on `MAXIMUM` / below-budget requests in `ai-services/app/rag/buyer_search.py`.
   - Enforced the user's actual ceiling across both SmartProp (`/api/v1/properties`) and Hòa Xuân land candidates (`reference_ceiling = ceiling` unless explicit over-budget consent is given in user text), clamped structured `request.budgetVnd`, fixed the pre-existing `r'gan '` substring bug (which previously matched `"ngan sach"`), and preserved exact-price (`đúng X tỷ`) and explicit range (`từ A đến B tỷ`) semantics.
4. **Closed P1 — Land Data Governance & Fail-Closed Activation**:
   - Changed `ai-services/app/land/paths.py` from `RAG_LAND_ENABLED="auto"` (file-presence auto-activation) to fail-closed `RAG_LAND_ENABLED="false"` + `verify_land_dataset()` checking all 15 required raw files, raw provenance JSONs, and `processed/<version>/manifest.json` version + SHA-256 source hashes + explicit usage governance (`publicApproved=True & containsSyntheticData=False & rightsApprovalRef`, OR explicit `RAG_LAND_DEMO_ENABLED=true & demoApproved=True` for internal/demo synthetic scenarios). Updated `ops/local-runtime.ps1` and `ops/production.env.example` (`RAG_LAND_ENABLED=false`, `RAG_LAND_DEMO_ENABLED=false`).
   - Removed every source-free legal/safety/cadastral/price claim across `demo_documents.py`, `engine.py`, `imported_data.py`, `conversation_router.py`, `land/api.py`, `land_chat.py`, `build_land_demo.py`, `landApi.js`, `LandDetailView.jsx`, `LandResults.jsx`, and `BuyerSearchResults.jsx`:
     - Replaced `"Được cấp sổ đỏ/sổ hồng"` and `"Sổ hồng: Có cấp từng lô"` with explicit synthetic/unverified disclaimers (`"Giả định kịch bản demo (...) — chưa có giấy chứng nhận thực tế được xác minh"` / `"chưa xác minh pháp lý thực tế"`).
     - Replaced `"Không ngập úng — giả định demo"` with `"Chưa có bản ghi ngập trùng tuyến đường nguồn (giả định kịch bản demo — không xác nhận an toàn ngập)"`.
     - Replaced `"Hiện tại chưa nằm trong đất quy hoạch của nhà nước"` with `"Chưa xác minh quy hoạch thu hồi/giải tỏa (giả định kịch bản demo — không xác nhận không vướng quy hoạch)"`.
     - Labeled `PLANNING_CELL` everywhere as a planning polygon (`"Ô quy hoạch tham khảo · không phải thửa địa chính chính thức"`), labeled all synthetic/historical/road/source asking prices as non-market/non-transaction values, stopped `landDisplayValue()` in `landApi.js` from stripping `"giả định demo"`, added a top-level visible `data-land-governance-notice` banner in `LandDetailView.jsx`, and verified zero `app.land` references in Valuation, Comparable, or Market pipelines.
5. **Closed P2 — Reproducible Committed Browser Evidence**:
   - Added committed, sanitized executable runner `frontend/tests/browser/pr43-land-e2e.mjs` (explicitly labeled `BROWSER_EVIDENCE_MODE=MOCKED_HTTP_VITE_BROWSER_E2E`, distinct from full-stack live-DB/Ollama runtime) verifying HTTP request payloads, responses, routes (`/land/:id`, `/land/non-existent-record`, `/advisor/chat`, `/listing/:id`, `/auth/google/link/complete`), multi-turn `PURCHASE_DECLINED` + stale `"Xem kết quả khác"` 0-card rejection, governance banners, and `1440/768/390` responsive layouts with `0` horizontal overflow, `0` uncaught exceptions, and `0` console errors.

---

## 2. Fresh Validation & Regression Evidence

### 2.1 Automated Unit, Security & Integration Suites

| Suite | Command | Result | Details |
|---|---|---|---|
| **Python FastAPI + Full RAG + Land + Security + V1.3** (54 files) | `pytest -rs -q tests` | **PASS** (`Exit 0`) | **`1191 passed`**, `19 skipped`, `0 failed`, `105 subtests passed` (includes `test_pr43_land_and_rag.py` `11/11`, `test_rag_canceled_workflow.py`, `test_rag_address_semantics.py`, `test_security_audit.py`, `test_v1_3_unit.py`). |
| **Spring Boot Backend + PR #48 Google Linking + Security + GIS + WP-02** (54 test classes) | `.\mvnw.cmd -o test` | **PASS** (`Exit 0`) | **`316 passed`**, `0 failed`, `0 errors`, `0 skipped` (includes `GoogleLinkHttpSecurityTest`, `GoogleLinkServiceIntegrationTest`, `GoogleOidcProtocolTest`, `TomcatLoopbackProxyBoundaryTest`, `ResearchAccessHttpSecurityTest`, `Pr43EstimatedOriginSecurityTest`). |
| **Frontend Recursive Unit & Contract** (`src` + `tests`, 28 files) | `node --test <all 28 *.test.mjs/*.test.js>` | **PASS** (`Exit 0`) | **`251 passed`**, `0 failed`, `0 skipped` (includes `pr43LandAndNearbyContract.test.mjs`, `googleLinkSession.test.mjs`, `googleLinkSessionContract.test.mjs`, PR #49 `httpClient` suites). |
| **Vite Production Build & Public Assets Gate** | `npx vite build` | **PASS** (`Exit 0`) | Production bundle built cleanly; `smartprop-approved-public-assets` verified. |
| **Workspace Security & Secret Scan** | `node ops/security-scan.mjs` | **PASS** (`Exit 0`) | `1298` files scanned, `0` tracked executables, `0` findings. |
| **Graphify AST Update** | `.graphify/venv/Scripts/graphify.exe update .` | **PASS** (`Exit 0`) | `11711` nodes, `32071` edges, `505` communities (`AST-only`). |

**Itemized Python Skips (19 total, 0 failures)**:
- `tests/test_api_v6.py` (13 skips): `V6 is no longer the public model; see test_v6_v1_3_contract.py` (expected per PR #44).
- `tests/test_planning_data.py` (1 skip): `Optional offline real dataset is not distributed with application source`.
- `tests/test_vision_detector.py` (5 skips): `yolov8n.pt weights are not present`.

### 2.2 Reproducible Browser E2E Suites (`MOCKED_HTTP_VITE_BROWSER_E2E`)

| Suite | Runner | Result | Details |
|---|---|---|---|
| **PR #43 Committed Land, Chat Cancellation, Hard-Budget & Route E2E** | `node frontend/tests/browser/pr43-land-e2e.mjs` | **PASS** (`Exit 0`) | **5 / 5** suites passed across `1440x900`, `768x1024`, `390x844` (`0` overflow, `0` exceptions, `0` console errors): `/land/:id` governance notice + synthetic disclaimers, `/land/non-existent-record` 404, `/advisor/chat` hard-budget `BUYER_SEARCH` -> `PURCHASE_DECLINED` -> stale `"Xem kết quả khác"` `0`-card rejection, `/listing/:id` PR #43 POIs + estimated-origin + PR #47 comparables, and `/auth/google/link/complete` PR #48 route preservation. |
| **WP-02 Comparable Browser Regression** | `node frontend/tests/browser/wp02-browser.mjs` | **PASS** (`Exit 0`) | **12 / 12** WP-02 Chromium groups passed. |
| **PR #48 Google Account Linking & Session Scope Browser Regression** | `node frontend/tests/browser/pr40-google-link.cjs` & `pr48-session-scope.cjs` | **PASS** (`Exit 0`) | **8 / 8** Google Link scenarios (`1440` & `390` across `success`, `cancel`, `expired`, `conflict`) + **5 / 5** session-scope scenarios passed. |

---

## 3. Truthful Runtime Gate Status & Environmental Boundaries

1. **Caddy Binary Runtime (`NOT_RUN`)**: `Get-Command caddy` confirmed `caddy` is not installed on this Windows host. Static `ops/Caddyfile` structure and embedded Tomcat `RemoteIpValve` / loopback proxy boundaries (`TomcatLoopbackProxyBoundaryTest`, `ResearchAccessHttpSecurityTest`) passed, while live `caddy` binary execution remains `NOT_RUN` (never reported as runtime PASS).
2. **MySQL `LiveIT` (`NOT_RUN`)**: Protected MySQL instances (`127.0.0.1:3306`, `127.0.0.1:3307`) and port `5183` mentor demo were not touched, queried, or migrated; `LiveIT` remains `NOT_RUN`.
3. **Land Dataset Public Rights & Activation (`FAIL_CLOSED`)**: No public redistribution rights approval exists or was fabricated for `HX-LAND-DEMO-20261126`. `land_enabled()` fails closed (`False`) by default (`RAG_LAND_ENABLED=false`) and whenever `publicApproved` is false unless `RAG_LAND_ENABLED=true` AND `RAG_LAND_DEMO_ENABLED=true` are explicitly set alongside a SHA-256-verified `manifest.json`.
4. **V1.3 Model Artifacts & Migrations**: Zero Git diff on `ai-services/artifacts` and `backend/src/main/resources/db/migration`; V1.3 SHA-256 hashes (`model.json`: `3C56B693...`, `feature_schema.json`: `84BE275B...`, `calibration.json`: `17632BDF...`, `artifact_manifest.json`: `419599EC...`) verified unchanged.

---

## 4. Required Closure Gates

- `PR43_CURRENT_MAIN_INTEGRATED`: **PASS** (`origin/main` @ `0e9053f0c4085351a7d429f81995f6895ad80e33` ancestor-verified)
- `PR43_PR48_GOOGLE_LINKING_PRESERVED`: **PASS**
- `PR43_STALE_BUYER_LAND_ACTION_REJECTED`: **PASS**
- `PR43_HARD_BUDGET_ENFORCED`: **PASS**
- `PR43_LAND_DEMO_PROVENANCE_PASS`: **PASS**
- `PR43_LAND_DATA_ACTIVATION_FAIL_CLOSED`: **PASS**
- `PR43_REPRODUCIBLE_BROWSER_EVIDENCE_PASS`: **PASS** (`frontend/tests/browser/pr43-land-e2e.mjs` committed & verified; `BROWSER_WITH_MOCKED_HTTP`)
- `PR43_PR45_RAG_CONTRACT_PRESERVED`: **PASS**
- `PR43_PHASE0_SECURITY_PRESERVED`: **PASS**
- `PR43_FULL_REGRESSION_PASS`: **PASS** (`1191` Python + `316` Java + `251` Frontend unit + `vite build` + `5/5` PR43 E2E + `12/12` WP02 E2E + `13/13` PR48 E2E)
- `PR43_REMOTE_HEAD_VERIFIED`: **PASS** (verified after push)

Status tokens:
- `PR43_READY_FOR_INDEPENDENT_REVIEW`
- `WAITING_FOR_PR43_MERGE_AUTHORIZATION`
